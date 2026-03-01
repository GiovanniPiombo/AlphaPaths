from ib_async import *
import pandas as pd
import numpy as np
from montecarlo import MonteCarloSimulator
import asyncio

# Cache dictionary for FX rates to avoid redundant API calls
fx_cache = {}

async def get_fx_rate(ib, from_currency, to_currency) -> float:
    """get the most recent FX rate for the given currency pair, with caching to minimize API calls."""
    if from_currency == to_currency:
        return 1.0
        
    pair = f"{from_currency}{to_currency}"
    if pair in fx_cache:
        return fx_cache[pair]
        
    print(f"get fx rate for {pair}...")
    contract = Forex(pair)
    
    bars = await ib.reqHistoricalDataAsync(
        contract,
        endDateTime='',
        durationStr='1 D',
        barSizeSetting='1 day',
        whatToShow='MIDPOINT',
        useRTH=False
    )
    
    if bars:
        rate = bars[-1].close
        fx_cache[pair] = rate
        return rate
    else:
        inv_pair = f"{to_currency}{from_currency}"
        print(f"  -> {pair} not found, trying inverse pair {inv_pair}...")
        inv_contract = Forex(inv_pair)
        bars = await ib.reqHistoricalDataAsync(
            inv_contract,
            endDateTime='',
            durationStr='1 D',
            barSizeSetting='1 day',
            whatToShow='MIDPOINT',
            useRTH=False
        )
        if bars:
            rate = 1.0 / bars[-1].close
            fx_cache[pair] = rate
            return rate
            
    raise ValueError(f"FX rate not found for {pair}")


async def check_portfolio() -> None:
    TRADING_DAYS = 252
    base_currency = ""
    total_value = 0.0

    ib = IB()
    await ib.connectAsync('127.0.0.1', 4001, clientId=1)  # 4002 for paper trading, 4001 for live accounts using IB Gateway
    print(f"Connected to IBKR: {ib.isConnected()}\n")

    try:
        # get account summary to find base currency and total liquidation value
        summary = await ib.accountSummaryAsync()
        for item in summary:
            if item.tag == "NetLiquidation":
                total_value = float(item.value)
                base_currency = item.currency
                break
                
        print(f"Net Liquidation Value: {total_value} {base_currency}\n")

        # get positions and calculate weights with FX conversion
        portfolio_items = ib.portfolio()
        print("Calculating portfolio weights (with FX conversion to base currency)...")
        
        weights_dict = {} # Map: symbol -> weight
        
        for item in portfolio_items:
            symbol = item.contract.symbol
            asset_currency = item.contract.currency
            market_value_local = item.marketValue
            
            fx_rate = await get_fx_rate(ib, asset_currency, base_currency)
            market_value_base = market_value_local * fx_rate
            
            weight = (market_value_base / total_value) if total_value > 0 else 0
            weights_dict[symbol] = weight
            
            print(f"{symbol}: {market_value_local:.2f} {asset_currency} -> {market_value_base:.2f} {base_currency} (Weight: {weight*100:.2f}%)")

        print(f"\nInvested weight sum: {sum(weights_dict.values())*100:.2f}%\n")

        # Download historical data for all assets in the portfolio
        price_dict = {} # temporary dictionary to hold price series for each symbol
        
        for item in portfolio_items:
            symbol = item.contract.symbol
            print(f"Downloading historical data for {symbol}...")
            await ib.qualifyContractsAsync(item.contract)
            
            bars = await ib.reqHistoricalDataAsync(
                item.contract,
                endDateTime='',
                durationStr='5 Y',
                barSizeSetting='1 day',
                whatToShow='TRADES',
                useRTH=True
            )
            
            if bars:
                df = util.df(bars)
                df.set_index('date', inplace=True) 
                df.index = pd.to_datetime(df.index)
                price_dict[symbol] = df['close']
            else:
                print(f"  -> No historical data for {symbol}, skipping...")
                
            await asyncio.sleep(1) 

        # create a DataFrame with all price series, aligned by date
        all_prices = pd.DataFrame(price_dict)
        
        # Forward fill and dropna
        all_prices.ffill(inplace=True)
        all_prices.dropna(inplace=True)
        
        # pairing weights with the order of columns in the price DataFrame
        valid_symbols = all_prices.columns.tolist()
        weight_array = np.array([weights_dict[sym] for sym in valid_symbols])
        
        print(f"valid assets for covariance matrix: {valid_symbols}")
        
        # calculate daily returns and covariance matrix
        all_returns = all_prices.pct_change().dropna()
        cov_matrix = all_returns.cov()
        
        # Variance: w^T * Cov * w
        port_variance = np.dot(weight_array.T, np.dot(cov_matrix.values, weight_array))
        annual_volatility = get_annual_volatility(annualize(port_variance, TRADING_DAYS))
        
        # calculate mean daily returns for each asset
        mean_daily_returns = all_returns.mean()
        # calculate portfolio expected return as weighted average of mean daily returns
        daily_mu = np.dot(weight_array, mean_daily_returns.values)
        # annualize expected return
        annual_mu = daily_mu * TRADING_DAYS
        
        print("\n--- RESULTS ---")
        print(f"Daily Portfolio Variance: {port_variance:.6f}")
        print(f"Annualized Portfolio Volatility (Sigma): {annual_volatility * 100:.2f}%")
        print(f"Annualized Expected Return (Mu): {annual_mu * 100:.2f}%")

        # Run Monte Carlo Simulation
        print("\nRunning Monte Carlo Simulation...")
        simulator = MonteCarloSimulator(capital=total_value, mu=annual_mu, sigma=annual_volatility, years=5, simulations=100000)
        simulated_prices = simulator.simulate()
        scenarios = simulator.get_scenarios(simulated_prices)
        print(f"\n--- 5-YEAR SIMULATION RESULTS ---")
        for scenario, value in scenarios.items():
            print(f"{scenario} Scenario: € {value:,.2f}")


    finally:
        ib.disconnect()
        print("\nDisconnected from IBKR.")


def annualize(daily_variance, trading_days=252) -> float:
    """Annualizes daily variance by multiplying it with the number of trading days in a year."""
    return daily_variance * trading_days

def get_annual_volatility(annual_variance) -> float:
    """Calculates annual volatility (sigma) as the square root of annual variance."""
    return np.sqrt(annual_variance)

if __name__ == "__main__":
    asyncio.run(check_portfolio())