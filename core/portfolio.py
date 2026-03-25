import os
from ib_async import *
import pandas as pd
import numpy as np
import asyncio
from core.gbm_model import GBMSimulator
from core.ai_review import get_portfolio_analysis
from core.utils import read_json, format_json
from core.path_manager import PathManager
from core.merton_model import MJDSimulator
from core.logger import app_logger
from datetime import datetime

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

        self.total_value = 0.0
        self.base_currency = ""
        self.cash_value_base = 0.0
        self.cash_weight = 0.0
        self.sum_risky_weights = 0.0
        self.risky_assets = []
        self.weights_dict = {}
        
        self.total_portfolio_mu = 0.0
        self.total_portfolio_vol = 0.0

        self.config_timeout = float(read_json("config.json", "IBKR_TIMEOUT") or 5.0)
        self.config_lookback = str(read_json(PathManager.CONFIG_FILE, "LOOKBACK_PERIOD") or 5)
        self.config_pacing = int(read_json(PathManager.CONFIG_FILE, "PACING_LIMIT") or 5)
        self.config_rf_rate = float(read_json(PathManager.CONFIG_FILE, "RISK_FREE_RATE") or 0.0)
        self.config_jump_thresh = float(read_json(PathManager.CONFIG_FILE, "JUMP_THRESHOLD") or 3.0)

    # ── CONNECTION AND UTILITIES ──────────────────────────────────
    async def connect(self) -> bool:
        """
        Establishes an asynchronous connection to the IBKR API.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        app_logger.info(f"Attempting to connect to IBKR at {self.host}:{self.port} (Client: {self.client_id})")
        try:
            await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
            
            if self.ib.isConnected():
                app_logger.info("Successfully connected to IBKR.")
                return True
            else:
                app_logger.error("Failed to connect to IBKR: Connection dropped immediately.")
                return False
        except TimeoutError:
            app_logger.error(f"Connection to IBKR timed out after {timeout} seconds. Is TWS/Gateway running?")
            return False
        except ConnectionRefusedError:
            app_logger.error(f"Connection refused by IBKR at {self.host}:{self.port}. Check if the port is correct.")
            return False
        except Exception as e:
            app_logger.error(f"Failed to connect to IBKR due to an unexpected error: {str(e)}")
            return False

    def disconnect(self):
        """
        Safely terminates the connection to the IBKR API if it is currently active.
        """
        if self.ib.isConnected():
            self.ib.disconnect()
            app_logger.info("Disconnected from IBKR.")

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
    def annualize(daily_variance: float, trading_days: int = TRADING_DAYS) -> float:
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
        account_currency = ""
    
        for item in summary:
            if not account_id:
                account_id = item.account 
            
            if item.tag == "NetLiquidation":
                self.total_value = float(item.value)
                account_currency = item.currency
            elif item.tag == "TotalCashValue":
                self.cash_value_base = float(item.value)

        target_currency = str(read_json(PathManager.CONFIG_FILE, "DISPLAY_CURRENCY") or "AUTO")
        target_currency = target_currency.split()[0]
    
        if target_currency != "AUTO" and target_currency != account_currency:
            self.base_currency = target_currency
            fx_rate = await self.get_fx_rate(account_currency, self.base_currency)
            self.total_value *= fx_rate
            self.cash_value_base *= fx_rate
        else:
            self.base_currency = account_currency

        daily_pnl = 0.0
        if account_id:
            pnl_sub = self.ib.reqPnL(account_id)
            
            elapsed = 0.0
            
            try:
                while elapsed < self.config_timeout:
                    await asyncio.sleep(0.2)
                    elapsed += 0.2
                    if pnl_sub and getattr(pnl_sub, 'dailyPnL', None) is not None and not np.isnan(pnl_sub.dailyPnL):
                        await asyncio.sleep(1.5) # This gives IBKR time to send the finalized calculation
                        daily_pnl = float(pnl_sub.dailyPnL)
                        break
            finally:
                self.ib.cancelPnL(account_id)
            
            if elapsed >= self.config_timeout and daily_pnl == 0.0:
                app_logger.warning("Timeout: Valid P&L not received within 5 seconds.")
                
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
    async def fetch_historical_data(self, cache_file: str = "data/historical_prices_cache.parquet") -> pd.DataFrame:
        """
        Downloads daily adjusted closing prices for all risky assets, utilizing local caching 
        to minimize IBKR API requests and prevent pacing violations.

        It checks for a local parquet file. If the portfolio composition has changed, 
        or if no cache exists, it fetches the full lookback period. If the cache is valid, 
        it intelligently fetches only the missing days and merges them.

        Args:
            cache_file (str): The local path where the historical data dataframe is saved.

        Returns:
            pd.DataFrame: A date-indexed DataFrame where each column represents 
                a ticker symbol and rows are daily adjusted close prices.
        """
        all_prices = pd.DataFrame()
        cached_df = pd.DataFrame()
        
        duration_str = f"{self.config_lookback} Y"
        
        current_symbols = [item.contract.symbol for item in self.risky_assets]

        if os.path.exists(cache_file):
            try:
                cached_df = pd.read_parquet(cache_file)
                if not cached_df.empty:
                    cached_symbols = cached_df.columns.tolist()
                    missing_symbols = [sym for sym in current_symbols if sym not in cached_symbols]
                    
                    if missing_symbols:
                        app_logger.info(f"New assets detected: {missing_symbols}. Forcing full historical fetch.")
                        cached_df = pd.DataFrame()
                    else:
                        last_date = cached_df.index.max().date()
                        today = datetime.now().date()
                        days_missing = (today - last_date).days
                        
                        if days_missing <= 0:
                            app_logger.info("Historical data is up to date. Loading entirely from local cache.")
                            return cached_df
                        
                        # Add a 2-day buffer to ensure overlapping and avoid missing any data points
                        duration_str = f"{days_missing + 2} D"
                        app_logger.info(f"Cache found. Fetching only the last {duration_str}")
            except Exception as e:
                app_logger.error(f"Failed to read cache file: {e}. Proceeding with full download.")
                cached_df = pd.DataFrame()

        semaphore = asyncio.Semaphore(self.config_pacing)

        async def fetch_single_asset(item):
            async with semaphore:
                symbol = item.contract.symbol
                await self.ib.qualifyContractsAsync(item.contract)
                
                bars = await self.ib.reqHistoricalDataAsync(
                    item.contract, endDateTime='', durationStr=duration_str,
                    barSizeSetting='1 day', whatToShow='ADJUSTED_LAST', useRTH=True
                )
                
                await asyncio.sleep(0.5)
                
                if bars:
                    df = util.df(bars)
                    df['date'] = pd.to_datetime(df['date']).dt.normalize()
                    df.set_index('date', inplace=True)
                    app_logger.debug(f"Historical data successfully downloaded for {symbol}")
                    return symbol, df['close']
                app_logger.warning(f"No historical data found for {symbol}")
                return symbol, None

        tasks = [fetch_single_asset(item) for item in self.risky_assets]
        results = await asyncio.gather(*tasks)

        valid_series = [
            close_series.rename(symbol) 
            for symbol, close_series in results if close_series is not None
        ]

        if valid_series:
            new_prices = pd.concat(valid_series, axis=1)
    
            if not cached_df.empty:
                all_prices = pd.concat([cached_df, new_prices])
                all_prices = all_prices[~all_prices.index.duplicated(keep='last')]
                all_prices.sort_index(inplace=True)
            else:
                all_prices = new_prices

        if not cached_df.empty and not all_prices.empty:
            all_prices = pd.concat([cached_df, all_prices])
            all_prices = all_prices[~all_prices.index.duplicated(keep='last')]
            all_prices.sort_index(inplace=True)
        elif not cached_df.empty and all_prices.empty:
            all_prices = cached_df

        if not all_prices.empty:
            all_prices.ffill(inplace=True) 
            all_prices.dropna(inplace=True) 
            
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)

            all_prices.to_parquet(cache_file)
            app_logger.info("Historical prices cache updated successfully.")

        return all_prices

    def calculate_risk_metrics(self, all_prices: pd.DataFrame) -> dict:
        """
        Calculates risk and return metrics for both the risky assets and the total portfolio.

        Extracts the covariance matrix, daily returns, and historical jumps from the 
        provided price data. Computes standard metrics (annualized volatility and expected 
        return) and Merton Jump-Diffusion parameters strictly on the at-risk capital, 
        then blends them with risk-free cash rates. 
        It also exports individual asset returns and the covariance matrix for 
        Markowitz Portfolio Optimization.

        Args:
            all_prices (pd.DataFrame): A date-indexed DataFrame containing daily 
                closing prices for the portfolio's risky assets.

        Returns:
            dict: A dictionary of compiled metrics including total portfolio stats, 
                MJD jump parameters, capital allocations, and individual asset 
                metrics ('asset_returns', 'cov_matrix', 'symbols') for optimization.
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
        risky_annual_mu = daily_mu * self.TRADING_DAYS
        
        self.total_portfolio_mu = (risky_annual_mu * self.sum_risky_weights) + (self.config_rf_rate * self.cash_weight) 
        self.total_portfolio_vol = annual_volatility * self.sum_risky_weights 
        
        portfolio_daily_returns = all_returns.dot(normalized_risky_weights)
        daily_vol = portfolio_daily_returns.std()
        

        threshold = self.config_jump_thresh * daily_vol
        jumps = portfolio_daily_returns[abs(portfolio_daily_returns) > threshold]
        
        if len(jumps) > 0:
            lam = (len(jumps) / len(portfolio_daily_returns)) * self.TRADING_DAYS
            m = jumps.mean()
            nu = jumps.std() if len(jumps) > 1 else 0.0
            if np.isnan(nu): nu = 0.0
        else:
            lam, m, nu = 0.0, 0.0, 0.0
            
        annual_asset_returns = mean_daily_returns * self.TRADING_DAYS
        annual_cov_matrix = cov_matrix * self.TRADING_DAYS

        return {
            "total_mu": self.total_portfolio_mu,
            "total_vol": self.total_portfolio_vol,
            "risky_mu": risky_annual_mu,
            "risky_vol": annual_volatility,
            "lam": lam,
            "m": m,
            "nu": nu,
            "risky_capital": self.total_value * self.sum_risky_weights,
            "cash_capital": self.cash_value_base,
            "risk_free_rate": self.config_rf_rate,
            "asset_returns": annual_asset_returns.to_dict(),
            "cov_matrix": annual_cov_matrix.to_dict(),
            "symbols": valid_symbols
        }

    def run_montecarlo_simulation(self, metrics: dict, years: int = 5, simulations: int = 100000) -> dict:
        """
        Executes Monte Carlo simulations by mathematically separating at-risk capital from risk-free cash.

        Runs standard Geometric Brownian Motion (GBM) and Merton Jump-Diffusion models 
        exclusively on the risky capital portion of the portfolio. Simultaneously 
        calculates deterministic growth for the cash allocation, and merges the paths 
        to produce the final total portfolio simulation.

        Args:
            metrics (dict): Risk metrics and capital allocations generated by `calculate_risk_metrics`.
            years (int, optional): The time horizon for the simulation in years. Defaults to 5.
            simulations (int, optional): The number of simulation paths to generate. Defaults to 100000.

        Returns:
            dict: A dictionary containing the computed scenario percentiles and the 
                generated price paths for both 'gbm' and 'merton' models.
        """
        safe_capital = metrics["risky_capital"] if metrics["risky_capital"] > 0 else 1.0
        
        gbm_simulator = GBMSimulator(
            capital=safe_capital, mu=metrics["risky_mu"], sigma=metrics["risky_vol"], 
            years=years, simulations=simulations
        )
        risky_gbm_prices = gbm_simulator.simulate()
        if metrics["risky_capital"] <= 0: risky_gbm_prices *= 0

        merton_simulator = MJDSimulator(
            capital=safe_capital, mu=metrics["risky_mu"], sigma=metrics["risky_vol"], 
            years=years, simulations=simulations,
            lam=metrics["lam"], m=metrics["m"], nu=metrics["nu"]
        )
        risky_merton_prices = merton_simulator.simulate()
        if metrics["risky_capital"] <= 0: risky_merton_prices *= 0

        dt = 1.0 / self.TRADING_DAYS
        steps = int(years * self.TRADING_DAYS)
        cash_growth = np.exp(metrics["risk_free_rate"] * dt * np.arange(steps + 1))
        cash_matrix = (metrics["cash_capital"] * cash_growth).reshape(-1, 1)

        risky_gbm_prices += cash_matrix
        risky_merton_prices += cash_matrix
        
        return {
            "gbm": {
                "scenarios": gbm_simulator.get_scenarios(risky_gbm_prices),
                "prices": risky_gbm_prices
            },
            "merton": {
                "scenarios": merton_simulator.get_scenarios(risky_merton_prices),
                "prices": risky_merton_prices
            }
        }

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