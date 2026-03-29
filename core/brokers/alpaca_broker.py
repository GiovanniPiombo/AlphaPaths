import os
import asyncio
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame

from core.brokers.base_broker import BaseBroker
from core.utils import read_json
from core.path_manager import PathManager
from core.logger import app_logger

class AlpacaBroker(BaseBroker):
    """
    Alpaca API implementation of the BaseBroker interface.
    Supports both Stocks and Crypto by utilizing a fallback mechanism.
    """

    def __init__(self):
        self.api_key = read_json(PathManager.CONFIG_FILE, "ALPACA_API_KEY") or ""
        self.secret_key = read_json(PathManager.CONFIG_FILE, "ALPACA_SECRET_KEY") or ""
        self.use_paper = read_json(PathManager.CONFIG_FILE, "USE_TESTNET") or True
        
        raw_display = str(read_json(PathManager.CONFIG_FILE, "DISPLAY_CURRENCY") or "USD")
        self.base_currency = raw_display.split()[0]
        self.native_currency = "USD" # Alpaca balances and positions are natively in USD
        
        self.config_lookback_years = int(read_json(PathManager.CONFIG_FILE, "LOOKBACK_PERIOD") or 5)
        
        self.trading_client: TradingClient | None = None
        self.stock_client: StockHistoricalDataClient | None = None
        self.crypto_client: CryptoHistoricalDataClient | None = None
        self.fx_cache: dict[str, float] = {}
        
        self.total_value: float = 0.0
        self.cash_value_base: float = 0.0
        self.risky_assets: list[str] = []
        self.weights_dict: dict[str, float] = {}

    async def connect(self) -> bool:
        """
        Initializes Alpaca REST clients (Trading, Stock Data, Crypto Data) 
        and verifies the connection by fetching account details.
        """
        app_logger.info("AlpacaBroker: Initializing connection...")
        try:
            self.trading_client = TradingClient(self.api_key, self.secret_key, paper=self.use_paper)
            self.stock_client = StockHistoricalDataClient(self.api_key, self.secret_key)
            self.crypto_client = CryptoHistoricalDataClient(self.api_key, self.secret_key)
            
            account = await asyncio.to_thread(self.trading_client.get_account)
            
            if account.account_blocked:
                app_logger.error("AlpacaBroker: The Alpaca account is currently blocked.")
                return False
                
            mode_str = "PAPER" if self.use_paper else "LIVE"
            app_logger.info(f"AlpacaBroker: Successfully connected in {mode_str} mode.")
            return True
            
        except Exception as e:
            app_logger.error(f"AlpacaBroker: Connection error: {e}")
            return False

    def disconnect(self) -> None:
        """
        Clears the REST client instances.
        """
        self.trading_client = None
        self.stock_client = None
        self.crypto_client = None
        app_logger.info("AlpacaBroker: Disconnected (REST clients destroyed).")

    async def get_fx_rate(self, from_currency: str, to_currency: str) -> float:
        """
        Fetches FX rates using Yahoo Finance if the target currency differs from USD.
        """
        if from_currency == to_currency:
            return 1.0
        
        pair = f"{from_currency}{to_currency}=X"
        if pair in self.fx_cache:
            return self.fx_cache[pair]
            
        try:
            ticker = yf.Ticker(pair)
            price = float(ticker.fast_info['lastPrice'])
            self.fx_cache[pair] = price
            return price
        except Exception as e:
            app_logger.warning(f"AlpacaBroker: Could not fetch FX rate for {pair}. Defaulting to 1.0. Error: {e}")
            return 1.0

    async def fetch_summary_and_positions(self) -> dict:
        """
        Retrieves account summary and open positions, converting USD values to base_currency.
        """
        if not self.trading_client:
            raise RuntimeError("Alpaca client not initialized. Call connect() first.")

        account = await asyncio.to_thread(self.trading_client.get_account)
        positions = await asyncio.to_thread(self.trading_client.get_all_positions)

        fx_rate = await self.get_fx_rate(self.native_currency, self.base_currency)

        self.total_value = float(account.equity) * fx_rate
        self.cash_value_base = float(account.cash) * fx_rate
        
        last_equity_base = float(account.last_equity) * fx_rate
        daily_pnl = self.total_value - last_equity_base

        positions_for_ui = []
        self.risky_assets = []
        self.weights_dict = {}

        for pos in positions:
            symbol = pos.symbol
            qty = float(pos.qty)
            
            current_price_base = float(pos.current_price) * fx_rate
            market_value_base = float(pos.market_value) * fx_rate
            
            self.risky_assets.append(symbol)
            positions_for_ui.append([symbol, qty, current_price_base, market_value_base])
            
            weight = (market_value_base / self.total_value) if self.total_value > 0 else 0.0
            self.weights_dict[symbol] = weight

        sum_risky_weights = sum(self.weights_dict.values())
        cash_weight = (self.cash_value_base / self.total_value) if self.total_value > 0 else 0.0

        return {
            "nlv":               self.total_value,
            "cash":              self.cash_value_base,
            "currency":          self.base_currency,
            "pnl":               daily_pnl,
            "positions":         positions_for_ui,
            "risky_weight":      sum_risky_weights * 100,
            "cash_weight":       cash_weight * 100,
            "raw_weights_dict":  self.weights_dict,
            "sum_risky_weights": sum_risky_weights,
        }

    async def fetch_historical_data(self, cache_file: str = "data/alpaca_prices_cache.parquet") -> pd.DataFrame:
        """
        Downloads daily historical data. Implements a Stock -> Crypto fallback mechanism.
        """
        app_logger.info(f"AlpacaBroker: Fetching historical data for {self.risky_assets}")

        if not self.risky_assets:
            return pd.DataFrame()

        cached_df = pd.DataFrame()
        start_date = datetime.now() - timedelta(days=self.config_lookback_years * 365)

        if os.path.exists(cache_file):
            try:
                cached_df = pd.read_parquet(cache_file)
                cached_symbols = set(cached_df.columns.tolist())
                current_symbols = set(self.risky_assets)

                if current_symbols - cached_symbols:
                    new = current_symbols - cached_symbols
                    app_logger.info(f"AlpacaBroker: New assets {new} detected — invalidating cache.")
                    cached_df = pd.DataFrame()
                else:
                    last_date = cached_df.index.max()
                    today = pd.Timestamp.now(tz="UTC").normalize()
                    days_missing = (today - last_date).days

                    if days_missing <= 0:
                        app_logger.info("AlpacaBroker: Historical cache is up to date.")
                        return cached_df

                    start_date = last_date.to_pydatetime() - timedelta(days=1)
                    app_logger.info(f"AlpacaBroker: Cache found. Fetching the last {days_missing} days.")
            except Exception as e:
                app_logger.error(f"AlpacaBroker: Failed to read cache: {e}. Executing a full re-fetch.")
                cached_df = pd.DataFrame()

        stock_prices = pd.DataFrame()
        crypto_prices = pd.DataFrame()
        found_stocks = set()

        try:
            stock_request = StockBarsRequest(
                symbol_or_symbols=self.risky_assets,
                timeframe=TimeFrame.Day,
                start=start_date
            )
            stock_bars = await asyncio.to_thread(self.stock_client.get_stock_bars, stock_request)
            
            if stock_bars and not stock_bars.df.empty:
                stock_df = stock_bars.df.reset_index()
                stock_df['date'] = pd.to_datetime(stock_df['timestamp']).dt.normalize().dt.tz_localize(None)
                stock_prices = stock_df.pivot(index='date', columns='symbol', values='close')
                found_stocks = set(stock_prices.columns)
        except Exception as e:
            app_logger.warning(f"AlpacaBroker: Stock fetch pass skipped or failed: {e}")

        missing_symbols = list(set(self.risky_assets) - found_stocks)
        
        if missing_symbols:
            app_logger.info(f"AlpacaBroker: Fallback - Attempting to fetch {missing_symbols} as Crypto.")
            
            crypto_symbol_map = {}
            for sym in missing_symbols:
                if sym.endswith('USD') and '/' not in sym:
                    crypto_symbol_map[sym[:-3] + '/USD'] = sym
                else:
                    crypto_symbol_map[sym] = sym
                    
            try:
                crypto_request = CryptoBarsRequest(
                    symbol_or_symbols=list(crypto_symbol_map.keys()),
                    timeframe=TimeFrame.Day,
                    start=start_date
                )
                crypto_bars = await asyncio.to_thread(self.crypto_client.get_crypto_bars, crypto_request)
                
                if crypto_bars and not crypto_bars.df.empty:
                    crypto_df = crypto_bars.df.reset_index()
                    crypto_df['date'] = pd.to_datetime(crypto_df['timestamp']).dt.normalize().dt.tz_localize(None)
                    
                    crypto_df['symbol'] = crypto_df['symbol'].map(crypto_symbol_map)
                    crypto_prices = crypto_df.pivot(index='date', columns='symbol', values='close')
            except Exception as e:
                app_logger.warning(f"AlpacaBroker: Crypto fetch fallback failed: {e}")

        if not stock_prices.empty and not crypto_prices.empty:
            new_prices = pd.concat([stock_prices, crypto_prices], axis=1)
        elif not stock_prices.empty:
            new_prices = stock_prices
        elif not crypto_prices.empty:
            new_prices = crypto_prices
        else:
            app_logger.warning("AlpacaBroker: No historical data returned from both Stock and Crypto APIs.")
            return cached_df if not cached_df.empty else pd.DataFrame()

        if not cached_df.empty:
            if cached_df.index.tz is not None:
                cached_df.index = cached_df.index.tz_localize(None)
                
            all_prices = pd.concat([cached_df, new_prices])
            all_prices = all_prices[~all_prices.index.duplicated(keep="last")]
            all_prices.sort_index(inplace=True)
        else:
            all_prices = new_prices

        all_prices.ffill(inplace=True)
        all_prices.dropna(inplace=True)

        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        all_prices.to_parquet(cache_file)
        app_logger.info("AlpacaBroker: Historical cache successfully updated.")

        return all_prices