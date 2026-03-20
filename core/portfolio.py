from ib_async import *
import pandas as pd
import numpy as np
import asyncio
from core.montecarlo import MonteCarloSimulator
from core.ai_review import get_portfolio_analysis
from core.utils import read_json, format_json

class PortfolioManager:
    """
    Orchestrates data fetching, risk calculations, and simulation workflows.

    This class manages the asynchronous connection to Interactive Brokers (ib_async), 
    retrieves account balances and historical pricing, and calculates core financial 
    metrics (drift and volatility). It also acts as the bridge connecting the raw 
    brokerage data to the Monte Carlo engine and the AI review module.

    Attributes:
        TRADING_DAYS (int): Standard number of trading days in a year (252).
        ib (IB): The ib_async Interactive Brokers client instance.
        host (str): IP address for the IBKR Gateway/TWS.
        port (int): Connection port for the IBKR Gateway/TWS.
        client_id (int): Unique identifier for the API connection.
        fx_cache (dict): In-memory cache for currency exchange rates to minimize API calls.
        total_value (float): Net Liquidation Value in the base currency.
        base_currency (str): The account's primary currency.
        cash_value_base (float): Total cash available in the base currency.
        cash_weight (float): Proportion of the portfolio held in cash (0.0 to 1.0).
        sum_risky_weights (float): Total weight of invested (non-cash) assets.
        risky_assets (list): Collection of ib_async PortfolioItem objects (excluding cash).
        weights_dict (dict): Maps ticker symbols to their portfolio weight.
        total_portfolio_mu (float): Calculated annualized expected return.
        total_portfolio_vol (float): Calculated annualized portfolio volatility.
    """
    TRADING_DAYS = 252

    def __init__(self, host='127.0.0.1', port=4001, client_id=1):
        """
        Initializes the PortfolioManager and its internal state variables.

        Args:
            host (str, optional): The IBKR API host address. Defaults to '127.0.0.1'.
            port (int, optional): The IBKR API port. Defaults to 4001.
            client_id (int, optional): The client ID for the connection. Defaults to 1.
        """
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.fx_cache = {}

        # Portfolio state (populated in fetch_summary_and_positions)
        self.total_value = 0.0
        self.base_currency = ""
        self.cash_value_base = 0.0
        self.cash_weight = 0.0
        self.sum_risky_weights = 0.0
        self.risky_assets = []
        self.weights_dict = {}
        
        # Risk metrics (populated in calculate_risk_metrics)
        self.total_portfolio_mu = 0.0
        self.total_portfolio_vol = 0.0

    # ── CONNECTION AND UTILITIES ──────────────────────────────────
    async def connect(self) -> bool:
        """
        Establishes an asynchronous connection to the IBKR API.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
        return self.ib.isConnected()

    def disconnect(self):
        """
        Safely terminates the connection to the IBKR API if it is currently active.
        """
        if self.ib.isConnected():
            self.ib.disconnect()

    async def get_fx_rate(self, from_currency: str, to_currency: str) -> float:
        """
        Retrieves the current exchange rate between two currencies.

        First checks the internal `fx_cache` to avoid redundant API calls. 
        If not cached, it requests a 1-day historical candle from IBKR to find 
        the midpoint close. Automatically attempts the inverse pair if the 
        direct pair fails.

        Args:
            from_currency (str): The currency to convert from (e.g., 'USD').
            to_currency (str): The target base currency (e.g., 'EUR').

        Returns:
            float: The exchange rate multiplier.

        Raises:
            ValueError: If neither the direct nor the inverse Forex pair can be found.
        """
        if from_currency == to_currency:
            return 1.0
            
        pair = f"{from_currency}{to_currency}"
        if pair in self.fx_cache:
            return self.fx_cache[pair]
            
        contract = Forex(pair)
        bars = await self.ib.reqHistoricalDataAsync(
            contract, endDateTime='', durationStr='1 D',
            barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=False
        )
        
        if bars:
            rate = bars[-1].close
            self.fx_cache[pair] = rate
            return rate
        else:
            inv_pair = f"{to_currency}{from_currency}"
            inv_contract = Forex(inv_pair)
            bars = await self.ib.reqHistoricalDataAsync(
                inv_contract, endDateTime='', durationStr='1 D',
                barSizeSetting='1 day', whatToShow='MIDPOINT', useRTH=False
            )
            if bars:
                rate = 1.0 / bars[-1].close
                self.fx_cache[pair] = rate
                return rate
                
        raise ValueError(f"Exchange rate not found for {pair}")

    @staticmethod
    def annualize(daily_variance: float, trading_days: int = 252) -> float:
        """
        Converts daily variance into annualized variance.

        Args:
            daily_variance (float): The calculated daily variance of the asset/portfolio.
            trading_days (int, optional): Days in a trading year. Defaults to 252.

        Returns:
            float: The annualized variance.
        """
        return daily_variance * trading_days

    @staticmethod
    def get_annual_volatility(annual_variance: float) -> float:
        """
        Calculates the annualized volatility (standard deviation) from annualized variance.

        Args:
            annual_variance (float): The annualized variance.

        Returns:
            float: The annualized volatility.
        """
        return np.sqrt(annual_variance)

    # ── CURRENT BALANCES AND POSITIONS ───────────────────
    async def fetch_summary_and_positions(self) -> dict:
        """
        Retrieves the account summary, daily P&L, and open positions from IBKR.

        This method populates the manager's state variables (weights, base currency, 
        total value). It implements a specific async waiting pattern to ensure 
        the Daily P&L data has "settled" from the broker before returning.

        Returns:
            dict: A formatted dictionary containing 'nlv', 'cash', 'currency', 
                'pnl', 'positions' (formatted for the UI), and calculated weights.
        """
        summary = await self.ib.accountSummaryAsync()
        
        account_id = ""
        for item in summary:
            if not account_id:
                account_id = item.account 
                
            if item.tag == "NetLiquidation":
                self.total_value = float(item.value)
                self.base_currency = item.currency
            elif item.tag == "TotalCashValue":
                self.cash_value_base = float(item.value)

        daily_pnl = 0.0
        if account_id:
            pnl_sub = self.ib.reqPnL(account_id)
            
            timeout = float(read_json("config.json", "IBKR_TIMEOUT") or 5.0)
            elapsed = 0.0
            
            while elapsed < timeout:
                await asyncio.sleep(0.2)
                elapsed += 0.2
                if pnl_sub and pnl_sub.dailyPnL is not None and not np.isnan(pnl_sub.dailyPnL):
                    await asyncio.sleep(1.5) # This gives IBKR time to send the finalized calculation
                    daily_pnl = float(pnl_sub.dailyPnL)
                    print(f"[DEBUG] P&L successfully settled at: {daily_pnl}")
                    break
            
            if elapsed >= timeout and daily_pnl == 0.0:
                print("[WARNING] Timeout: Valid P&L not received within 5 seconds.")
                
            self.ib.cancelPnL(account_id)

        portfolio_items = self.ib.portfolio()
        self.weights_dict = {}
        self.risky_assets = []
        positions_for_ui = []

        for item in portfolio_items:
            if item.contract.secType == 'CASH':
                continue 
                
            self.risky_assets.append(item)
            symbol = item.contract.symbol
            
            fx_rate = await self.get_fx_rate(item.contract.currency, self.base_currency)
            market_value_base = item.marketValue * fx_rate
            
            weight = (market_value_base / self.total_value) if self.total_value > 0 else 0
            self.weights_dict[symbol] = weight
            
            positions_for_ui.append([
                symbol, getattr(item, 'position', 0), 
                getattr(item, 'marketPrice', 0.0), market_value_base
            ])

        self.cash_weight = (self.cash_value_base / self.total_value) if self.total_value > 0 else 0
        self.sum_risky_weights = sum(self.weights_dict.values())

        return {
            "nlv": self.total_value,
            "cash": self.cash_value_base,
            "currency": self.base_currency,
            "pnl": daily_pnl,
            "positions": positions_for_ui,
            "risky_weight": self.sum_risky_weights * 100,
            "cash_weight": self.cash_weight * 100
        }
    
    # ── HISTORICAL DATA AND MATH ─────────────────────────
    async def fetch_historical_data(self) -> pd.DataFrame:
        """
        Downloads 5 years of daily adjusted closing prices for all risky assets.

        Qualifies the contracts with IBKR, fetches the data sequentially (with 
        pacing to respect API rate limits), and aligns everything into a single, 
        forward-filled Pandas DataFrame.

        Returns:
            pd.DataFrame: A date-indexed DataFrame where each column represents 
                a ticker symbol and rows are daily adjusted close prices.
        """
        all_prices = pd.DataFrame()
        
        for item in self.risky_assets:
            symbol = item.contract.symbol
            await self.ib.qualifyContractsAsync(item.contract)
            
            bars = await self.ib.reqHistoricalDataAsync(
                item.contract, endDateTime='', durationStr='5 Y',
                barSizeSetting='1 day', whatToShow='ADJUSTED_LAST', useRTH=True
            )
            
            if bars:
                df = util.df(bars)
                df['date'] = pd.to_datetime(df['date']).dt.normalize()
                df.set_index('date', inplace=True) 
                all_prices = all_prices.join(df['close'].rename(symbol), how='outer')
                
            await asyncio.sleep(1) # Pacing to respect IBKR API limits

        all_prices.ffill(inplace=True) 
        all_prices.dropna(inplace=True) 
        return all_prices

    def calculate_risk_metrics(self, all_prices: pd.DataFrame) -> tuple:
        """
        Calculates the portfolio's expected drift (mu) and volatility (sigma).

        Normalizes the weights of the risky assets, calculates the covariance 
        matrix from daily returns, and computes the annualized metrics. It then 
        adjusts these metrics based on the portfolio's cash buffer and the 
        configured risk-free rate.

        Args:
            all_prices (pd.DataFrame): The historical price matrix generated 
                by `fetch_historical_data`.

        Returns:
            tuple: A tuple containing (total_portfolio_mu, total_portfolio_vol).
        """
        valid_symbols = all_prices.columns.tolist()
        
        normalized_risky_weights = np.array([
            self.weights_dict[sym] / self.sum_risky_weights for sym in valid_symbols
        ])
        
        all_returns = all_prices.pct_change().dropna()
        cov_matrix = all_returns.cov()
        
        port_variance = np.dot(normalized_risky_weights.T, np.dot(cov_matrix.values, normalized_risky_weights))
        annual_volatility = self.get_annual_volatility(self.annualize(port_variance, self.TRADING_DAYS))
        
        mean_daily_returns = all_returns.mean()
        daily_mu = np.dot(normalized_risky_weights, mean_daily_returns.values)
        annual_mu = daily_mu * self.TRADING_DAYS
        
        risk_free_rate = read_json("config.json", "RISK_FREE_RATE")
        self.total_portfolio_mu = (annual_mu * self.sum_risky_weights) + (risk_free_rate * self.cash_weight) 
        self.total_portfolio_vol = annual_volatility * self.sum_risky_weights 
        
        return self.total_portfolio_mu, self.total_portfolio_vol

    # ── SIMULATION AND AI ────────────────────────────────
    def run_montecarlo_simulation(self, years: int = 5, simulations: int = 100000) -> tuple:
        """
        Executes a Monte Carlo simulation using the calculated portfolio metrics.

        Args:
            years (int, optional): The time horizon to simulate. Defaults to 5.
            simulations (int, optional): Number of random paths to generate. 
                Defaults to 100,000.

        Returns:
            tuple: A tuple containing:
                - scenarios (dict): Calculated percentiles (Worst, Median, Best).
                - simulated_prices (np.ndarray): The raw matrix of all simulated paths.
        """
        simulator = MonteCarloSimulator(
            capital=self.total_value, 
            mu=self.total_portfolio_mu, 
            sigma=self.total_portfolio_vol, 
            years=years, 
            simulations=simulations
        )
        simulated_prices = simulator.simulate()
        scenarios = simulator.get_scenarios(simulated_prices)
        
        # Visualization (can be disconnected when you use a Qt canvas)
        #plot_portfolio_montecarlo(simulated_prices)
        
        return scenarios, simulated_prices

    def get_ai_feedback(self, scenarios: dict) -> dict:
        """
        Formats portfolio data and simulation results to request an AI analysis.

        Args:
            scenarios (dict): The percentile outcomes generated by the Monte Carlo simulation.

        Returns:
            dict: The parsed JSON response from the Gemini AI module containing 
                portfolio insights and recommendations.
        """
        
        portfolio_data = {
            "total_value": self.total_value,
            "currency": self.base_currency,
            "risky_weight": self.sum_risky_weights * 100,
            "cash_weight": self.cash_weight * 100,
            "mu": self.total_portfolio_mu * 100,
            "sigma": self.total_portfolio_vol * 100,
            "worst_case": scenarios["Worst (5%)"],
            "median_case": scenarios["Median (50%)"],
            "best_case": scenarios["Best (95%)"]
        }
        
        return get_portfolio_analysis(portfolio_data)