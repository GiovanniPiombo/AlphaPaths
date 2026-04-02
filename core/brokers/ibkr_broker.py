# AlphaPaths - Advanced risk analysis, Monte Carlo simulation, and portfolio optimization.
# Copyright (C) 2026 Giovanni Piombo Nicoli
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import os
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime
from ib_async import IB, Forex, util

from core.brokers.base_broker import BaseBroker
from core.utils import read_json
from core.path_manager import PathManager
from core.logger import app_logger

class IBKRBroker(BaseBroker):
    """
    Interactive Brokers implementation of the BaseBroker interface.

    This class manages the asynchronous connection to Interactive Brokers via 
    the `ib_async` library. It handles account data retrieval, automatic 
    currency conversion (FX), and caching of historical prices, completely 
    shielding the rest of the application from IBKR-specific API quirks.
    """

    def __init__(self, host='127.0.0.1', port=4001, client_id=1):
        """
        Initializes the IBKR client and reads connection settings from the config.
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

        self.config_timeout = float(read_json(PathManager.CONFIG_FILE, "IBKR_TIMEOUT") or 5.0)
        self.config_lookback = str(read_json(PathManager.CONFIG_FILE, "LOOKBACK_PERIOD") or 5)
        self.config_pacing = int(read_json(PathManager.CONFIG_FILE, "PACING_LIMIT") or 5)

    async def connect(self) -> bool:
        """
        Establishes an asynchronous connection to the IBKR Gateway/TWS.
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
            app_logger.error(f"Connection to IBKR timed out after {self.config_timeout} seconds. Is TWS/Gateway running?")
            return False
        except ConnectionRefusedError:
            app_logger.error(f"Connection refused by IBKR at {self.host}:{self.port}. Check if the port is correct.")
            return False
        except Exception as e:
            app_logger.error(f"Failed to connect to IBKR due to an unexpected error: {str(e)}")
            return False

    def disconnect(self) -> None:
        """
        Safely terminates the connection to the IBKR API.
        """
        if self.ib.isConnected():
            self.ib.disconnect()
            app_logger.info("Disconnected from IBKR.")

    async def get_fx_rate(self, from_currency: str, to_currency: str) -> float:
        """
        Retrieves the current exchange rate between two currencies using IBKR data.
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

    async def fetch_summary_and_positions(self) -> dict:
        """
        Retrieves the account summary, daily P&L, and open positions from IBKR.
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
                        await asyncio.sleep(1.5) 
                        daily_pnl = float(pnl_sub.dailyPnL)
                        break
            finally:
                self.ib.cancelPnL(account_id)
            
            if elapsed >= self.config_timeout and daily_pnl == 0.0:
                app_logger.warning("Timeout: Valid P&L not received within configured time.")
                
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
            "cash_weight": self.cash_weight * 100,
            "raw_weights_dict": self.weights_dict,         
            "sum_risky_weights": self.sum_risky_weights    
        }

    async def fetch_historical_data(self, cache_file: str = "data/IBKR_prices_cache.parquet") -> pd.DataFrame:
        """
        Downloads daily adjusted closing prices for all risky assets from IBKR.
        Utilizes local caching to minimize API requests and prevent pacing violations.
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
                
                await asyncio.sleep(0.5) # Prevent pacing violations
                
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