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
    """
    Connects to IBKR, fetches the user's portfolio, downloads historical data, 
    calculates risk metrics, and runs a Monte Carlo simulation.
    """
    TRADING_DAYS = 252
    base_currency = ""
    total_value = 0.0

    ib = IB()
    await ib.connectAsync('127.0.0.1', 4002, clientId=1)
    print(f"Connected to IBKR: {ib.isConnected()}\n")

    try:
        # --- 1. Fetch Base Currency, Total Value & Cash ---
        summary = await ib.accountSummaryAsync()
        
        # get total portfolio value and base currency from account summary
        for item in summary:
            if item.tag == "NetLiquidation":
                total_value = float(item.value)
                base_currency = item.currency
            elif item.tag == "TotalCashValue":
                cash_value_base = float(item.value)
                
        print(f"Net Liquidation Value: {total_value} {base_currency}")
        print(f"Total Cash Value: {cash_value_base} {base_currency}\n")

        portfolio_items = ib.portfolio()
        weights_dict = {}
        risky_assets = []

        # --- 2. Filter CASH and Calculate Weights in Base Currency ---
        print("Calculating portfolio weights with FX conversion...")
        for item in portfolio_items:
            if item.contract.secType == 'CASH':
                continue 
                
            risky_assets.append(item)
            symbol = item.contract.symbol
            
            # convert market value to base currency for weight calculation
            fx_rate = await get_fx_rate(ib, item.contract.currency, base_currency)
            market_value_base = item.marketValue * fx_rate
            
            weight = (market_value_base / total_value) if total_value > 0 else 0
            weights_dict[symbol] = weight
            
            print(f"{symbol}: {item.marketValue:.2f} {item.contract.currency} -> {market_value_base:.2f} {base_currency} (Weight: {weight*100:.2f}%)")

        cash_weight = (cash_value_base / total_value) if total_value > 0 else 0
        print(f"\nRisky Assets Weight: {sum(weights_dict.values())*100:.2f}% | Cash Weight: {cash_weight*100:.2f}%\n")

        # --- 3. Download Historical Data (Total Return) ---
        all_prices = pd.DataFrame()
        
        for item in risky_assets:
            symbol = item.contract.symbol
            print(f"Downloading historical data for {symbol}...")
            await ib.qualifyContractsAsync(item.contract)
            
            bars = await ib.reqHistoricalDataAsync(
                item.contract,
                endDateTime='',
                durationStr='5 Y',
                barSizeSetting='1 day',
                whatToShow='ADJUSTED_LAST', 
                useRTH=True
            )
            
            if bars:
                df = util.df(bars)
                # Normalize dates to strip timestamps and avoid timezone misalignments
                df['date'] = pd.to_datetime(df['date']).dt.normalize()
                df.set_index('date', inplace=True) 
                
                # Outer join ensures that days where one exchange is closed (e.g., US holiday) but another is open (e.g., EU) don't break the alignment.
                all_prices = all_prices.join(df['close'].rename(symbol), how='outer')
            else:
                print(f"  -> No historical data for {symbol}, skipping...")
                
            await asyncio.sleep(1) # Pacing to respect IBKR API limits

        # --- 4. Data Cleansing & Alignment ---
        # Forward fill propagates the last known price for days when a specific market was closed.
        all_prices.ffill(inplace=True) 
        all_prices.dropna(inplace=True) # Drop initial rows where some assets didn't exist yet
        
        valid_symbols = all_prices.columns.tolist()
        
        # --- 5. Risk Metrics Calculation (Risky Assets Only) ---
        # Re-normalize weights for the covariance matrix calculation
        sum_risky_weights = sum([weights_dict[sym] for sym in valid_symbols])
        normalized_risky_weights = np.array([weights_dict[sym] / sum_risky_weights for sym in valid_symbols])
        
        all_returns = all_prices.pct_change().dropna()
        cov_matrix = all_returns.cov()
        
        # Calculate daily portfolio variance: w^T * Cov * w
        port_variance = np.dot(normalized_risky_weights.T, np.dot(cov_matrix.values, normalized_risky_weights))
        annual_volatility = get_annual_volatility(annualize(port_variance, TRADING_DAYS))
        
        # Calculate expected daily returns (historical mean)
        mean_daily_returns = all_returns.mean()
        daily_mu = np.dot(normalized_risky_weights, mean_daily_returns.values)
        annual_mu = daily_mu * TRADING_DAYS
        
        # --- 6. Cash Buffer Integration ---
        # Re-apply the dampening effect of cash to the overall portfolio metrics.
        # Assuming a conservative 2% risk-free rate for cash holding.
        risk_free_rate = 0.02
        total_portfolio_mu = (annual_mu * sum_risky_weights) + (risk_free_rate * cash_weight) 
        total_portfolio_vol = annual_volatility * sum_risky_weights 
        
        print("\n--- RESULTS ---")
        print(f"Annualized Expected Return (Mu): {total_portfolio_mu * 100:.2f}%")
        print(f"Annualized Portfolio Volatility (Sigma): {total_portfolio_vol * 100:.2f}%")

        # --- 7. Monte Carlo Execution ---
        print("\nRunning Monte Carlo Simulation...")
        simulator = MonteCarloSimulator(capital=total_value, mu=total_portfolio_mu, sigma=total_portfolio_vol, years=5, simulations=100000)
        simulated_prices = simulator.simulate()
        scenarios = simulator.get_scenarios(simulated_prices)
        
        print(f"\n--- 5-YEAR SIMULATION RESULTS ---")
        for scenario, value in scenarios.items():
            print(f"{scenario} Scenario: {base_currency} {value:,.2f}")

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