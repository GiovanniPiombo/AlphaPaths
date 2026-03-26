import os
import json
import pandas as pd
import yfinance as yf
from datetime import datetime

from core.brokers.base_broker import BaseBroker
from core.path_manager import PathManager
from core.logger import app_logger
from core.utils import read_json

class ManualBroker(BaseBroker):
    """
    A 'dummy' broker adapter that reads positions from a local JSON file 
    and uses Yahoo Finance (yfinance) to fetch real-time prices and historical data.
    """

    def __init__(self, portfolio_file="manual_portfolio.json"):
        self.portfolio_file = PathManager.EXTERNAL_DIR / portfolio_file
        self.fx_cache = {}
        
        self.total_value = 0.0
        self.base_currency = "USD"
        self.cash_value_base = 0.0
        self.risky_assets = []
        self.sum_risky_weights = 0.0
        self.weights_dict = {}

    async def connect(self) -> bool:
        """
        Since there is no real broker to connect to, we just verify 
        that the manual portfolio file exists and is readable.
        """
        app_logger.info("ManualBroker: 'Connecting' (Checking local portfolio file)...")
        if not self.portfolio_file.exists():
            app_logger.error(f"ManualBroker: Portfolio file not found at {self.portfolio_file}")
            return False
        return True

    def disconnect(self) -> None:
        """No active connection to close."""
        app_logger.info("ManualBroker: Disconnected.")

    async def get_fx_rate(self, from_currency: str, to_currency: str) -> float:
        """Fetches FX rates using Yahoo Finance if currencies differ."""
        if from_currency == to_currency:
            return 1.0
        
        pair = f"{from_currency}{to_currency}=X"
        if pair in self.fx_cache:
            return self.fx_cache[pair]
            
        try:
            ticker = yf.Ticker(pair)
            price = ticker.fast_info['lastPrice']
            self.fx_cache[pair] = price
            return price
        except Exception as e:
            app_logger.warning(f"Could not fetch FX rate for {pair} via yfinance. Defaulting to 1.0. Error: {e}")
            return 1.0

    async def fetch_summary_and_positions(self) -> dict:
        """
        Reads the local JSON, downloads current prices via yfinance, 
        detects the native currency of each asset, converts it to the 
        base currency (respecting config.json settings), and calculates 
        the portfolio summary.
        """
        
        with open(self.portfolio_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        original_json_currency = data.get("base_currency", "USD")
        raw_cash = float(data.get("cash", 0.0))
            
        target_currency_setting = str(read_json(PathManager.CONFIG_FILE, "DISPLAY_CURRENCY") or "AUTO")
        target_currency = target_currency_setting.split()[0]
        
        if target_currency != "AUTO":
            self.base_currency = target_currency
        else:
            self.base_currency = original_json_currency
            
        if original_json_currency != self.base_currency:
            app_logger.info(f"ManualBroker: Converting cash from {original_json_currency} to {self.base_currency}")
            cash_fx_rate = await self.get_fx_rate(original_json_currency, self.base_currency)
            self.cash_value_base = raw_cash * cash_fx_rate
        else:
            self.cash_value_base = raw_cash
            
        raw_positions = data.get("positions", [])
        self.risky_assets = [p["ticker"] for p in raw_positions]
        positions_for_ui = []
        total_risky_value = 0.0
        
        if self.risky_assets:
            app_logger.info(f"ManualBroker: Fetching current prices from yfinance for {self.risky_assets}")
            yf_data = yf.download(self.risky_assets, period="1d", progress=False)
            
            for pos in raw_positions:
                sym = pos["ticker"]
                qty = float(pos["quantity"])
                
                if len(self.risky_assets) == 1:
                    current_price = float(yf_data['Close'].iloc[-1])
                else:
                    current_price = float(yf_data['Close'][sym].iloc[-1])
                
                asset_info = yf.Ticker(sym).fast_info
                native_currency = getattr(asset_info, 'currency', self.base_currency)
                
                fx_rate = await self.get_fx_rate(native_currency, self.base_currency)
                
                current_price_base = current_price * fx_rate
                market_value = current_price_base * qty
                total_risky_value += market_value
                
                positions_for_ui.append([sym, qty, current_price_base, market_value])

        self.total_value = self.cash_value_base + total_risky_value
        self.weights_dict = {}
        
        for pos in positions_for_ui:
            sym = pos[0]
            mkt_val = pos[3]
            weight = (mkt_val / self.total_value) if self.total_value > 0 else 0
            self.weights_dict[sym] = weight
            
        self.sum_risky_weights = sum(self.weights_dict.values())
        cash_weight = (self.cash_value_base / self.total_value) if self.total_value > 0 else 0

        return {
            "nlv": self.total_value,
            "cash": self.cash_value_base,
            "currency": self.base_currency,
            "pnl": 0.0, 
            "positions": positions_for_ui,
            "risky_weight": self.sum_risky_weights * 100,
            "cash_weight": cash_weight * 100,
            "raw_weights_dict": self.weights_dict,         
            "sum_risky_weights": self.sum_risky_weights    
        }

    async def fetch_historical_data(self, cache_file: str = "data/manual_prices_cache.parquet") -> pd.DataFrame:
        """
        Downloads 5 years of historical data from Yahoo Finance.
        """
        app_logger.info(f"ManualBroker: Downloading historical data for {self.risky_assets}")
        if not self.risky_assets:
            return pd.DataFrame()

        data = yf.download(self.risky_assets, period="5y", progress=False)
        
        if len(self.risky_assets) == 1:
            all_prices = data[['Close']].rename(columns={'Close': self.risky_assets[0]})
        else:
            all_prices = data['Close']
            
        all_prices.ffill(inplace=True)
        all_prices.dropna(inplace=True)
        
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        all_prices.to_parquet(cache_file)
        
        return all_prices