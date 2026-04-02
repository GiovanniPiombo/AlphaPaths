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
import pandas as pd
from datetime import datetime, timezone
import ccxt.async_support as ccxt
import aiohttp

from core.brokers.base_broker import BaseBroker
from core.utils import read_json
from core.path_manager import PathManager
from core.logger import app_logger

class CryptoBroker(BaseBroker):
    """
    CCXT implementation of the BaseBroker interface.
    Allows connection to dozens of exchanges (Binance, Kraken, etc.)
    using a single unified interface.
    """

    # Stablecoins/fiat treated as cash (risk-free)
    CASH_ASSETS = frozenset(["USDT", "USDC", "EUR", "USD", "BUSD", "DAI", "TUSD", "FDUSD", "JPY", "CZK", "TRY", "ZAR", "UAH", "BRL", "PLN", "ARS", "MXN", "COP", "IDR"])

    def __init__(self):
        self.exchange_id = read_json(PathManager.CONFIG_FILE, "CRYPTO_EXCHANGE") or "binance"
        self.api_key = read_json(PathManager.CONFIG_FILE, "CRYPTO_API_KEY")  or ""
        self.secret = read_json(PathManager.CONFIG_FILE, "CRYPTO_SECRET")   or ""
        self.dust_threshold = float(read_json(PathManager.CONFIG_FILE, "CRYPTO_DUST_THRESHOLD") or 0.0001)

        raw_display = str(read_json(PathManager.CONFIG_FILE, "DISPLAY_CURRENCY") or "USDT")
        self.target_currency = raw_display.split()[0]
        self.base_currency = "USDT"

        self.exchange:      ccxt.Exchange | None = None
        self.total_value:   float = 0.0
        self.cash_value_base: float = 0.0
        self.risky_assets:  list[str] = []
        self.weights_dict:  dict[str, float] = {}

    async def connect(self) -> bool:
        """
        Dynamically instantiates the requested CCXT exchange class,
        injects credentials, and verifies the connection by loading markets.
        Includes support for Sandbox/Testnet environments (Paper Trading).
        """
        app_logger.info(f"CryptoBroker: Connecting to {self.exchange_id.upper()}...")
        try:
            exchange_class = getattr(ccxt, self.exchange_id.lower())
            self.exchange = exchange_class({
                "apiKey": self.api_key,
                "secret": self.secret,
                "enableRateLimit": True,
            })
            
            use_testnet = read_json(PathManager.CONFIG_FILE, "USE_TESTNET") or False
            
            if use_testnet:
                self.exchange.set_sandbox_mode(True)
                app_logger.info(f"CryptoBroker: SANDBOX/TESTNET MODE ENABLED FOR {self.exchange_id.upper()}")

            await self.exchange.load_markets()
            app_logger.info(f"CryptoBroker: Connected to {self.exchange_id.upper()}.")
            return True

        except AttributeError:
            app_logger.error(f"CryptoBroker: Exchange '{self.exchange_id}' not supported by CCXT.")
            return False
        except ccxt.AuthenticationError:
            app_logger.error("CryptoBroker: Authentication failed. Check API Key and Secret.")
            return False
        except ccxt.NetworkError as e:
            app_logger.error(f"CryptoBroker: Network error during connection: {e}")
            return False
        except Exception as e:
            app_logger.error(f"CryptoBroker: Unexpected error during connection: {e}")
            return False

    def disconnect(self) -> None:
        """
        Schedules the async CCXT session close on the running event loop.
        Uses ensure_future so it is properly awaited before the loop exits,
        avoiding the fire-and-forget risk of create_task.
        """
        if not self.exchange:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.exchange.close())
            app_logger.info(f"CryptoBroker: Disconnected from {self.exchange_id.upper()}.")
        except RuntimeError:
            asyncio.run(self.exchange.close())
            app_logger.info(f"CryptoBroker: Disconnected from {self.exchange_id.upper()} (sync).")
        except Exception as e:
            app_logger.warning(f"CryptoBroker: Error closing CCXT session: {e}")
        finally:
            self.exchange = None

    def _resolve_price(self, coin: str, tickers: dict) -> float | None:
        """
        Tries to find the price of `coin` in `base_currency`.
        Strategy:
          1. Direct pair:    BTC/USDT
          2. Inverse pair:   USDT/BTC
          3. Cross via USDT: ETH/BTC
        Returns None if no route is found.
        """
        base = self.base_currency

        direct = f"{coin}/{base}"
        if direct in tickers and tickers[direct].get("last"):
            return float(tickers[direct]["last"])

        inverse = f"{base}/{coin}"
        if inverse in tickers and tickers[inverse].get("last"):
            price = tickers[inverse]["last"]
            return 1.0 / float(price) if price else None

        if base != "USDT":
            coin_usdt  = f"{coin}/USDT"
            base_usdt  = f"{base}/USDT"
            if (coin_usdt in tickers and tickers[coin_usdt].get("last") and
                    base_usdt in tickers and tickers[base_usdt].get("last")):
                return float(tickers[coin_usdt]["last"]) / float(tickers[base_usdt]["last"])

        return None

    async def _fetch_daily_pnl(self, tickers: dict) -> float:
        """
        Estimates the daily P&L by comparing yesterday's close to today's
        last price for each risky asset, weighted by current holdings.

        Uses the OHLCV data already fetched for the last 2 days, so no
        extra API calls are needed beyond what fetch_summary_and_positions
        already has.
        """
        total_pnl = 0.0
        async def fetch_single_pnl(pair):
            coin = pair.split("/")[0]
            try:
                ohlcv = await self.exchange.fetch_ohlcv(pair, timeframe="1d", limit=2)
                if len(ohlcv) < 2:
                    return 0.0
                prev_close = ohlcv[-2][4]
                last_price = tickers.get(pair, {}).get("last") or ohlcv[-1][4]

                qty = self.weights_dict.get(coin, 0) * self.total_value / last_price if last_price else 0
                return (last_price - prev_close) * qty
            except Exception as e:
                app_logger.debug(f"CryptoBroker: Could not compute P&L for {pair}: {e}")
                return 0.0

        tasks = [fetch_single_pnl(pair) for pair in self.risky_assets]
        results = await asyncio.gather(*tasks)
    
        return sum(results)

    async def fetch_summary_and_positions(self) -> dict:
        """
        Retrieves balances and tickers, classifies assets as cash or risky,
        resolves cross-pair prices, and computes NLV + daily P&L.

        Handles exchanges that require explicit symbol lists for fetch_tickers()
        via a selective fallback, instead of fetching all tickers at once.
        """
        if not self.exchange:
            raise RuntimeError("Exchange not initialized. Call connect() first.")

        balance = await self.exchange.fetch_balance()

        non_zero = {
            coin: amt
            for coin, amt in balance["total"].items()
            if amt > self.dust_threshold
        }

        candidate_pairs = [
            f"{coin}/{self.base_currency}"
            for coin in non_zero
            if coin != self.base_currency and coin not in self.CASH_ASSETS
        ]

        try:
            tickers = await self.exchange.fetch_tickers()
        except (ccxt.BadRequest, ccxt.NotSupported, ccxt.ArgumentsRequired):
            app_logger.info(
                f"CryptoBroker: {self.exchange_id} requires explicit symbols "
                f"for fetch_tickers(). Falling back to selective fetch."
            )
            tickers = await self.exchange.fetch_tickers(candidate_pairs) if candidate_pairs else {}

        positions_for_ui = []
        self.total_value = 0.0
        self.cash_value_base = 0.0
        self.risky_assets = []

        for coin, amount in non_zero.items():
            if coin == self.base_currency:
                current_price = 1.0
            elif coin in self.CASH_ASSETS:
                current_price = await self.get_fx_rate(coin, self.base_currency)
            else:
                current_price = self._resolve_price(coin, tickers)
                if current_price is None:
                    app_logger.warning(f"CryptoBroker: No price route found for {coin}/{self.base_currency}. Skipping.")
                    continue

            market_value = amount * current_price
            self.total_value += market_value

            if coin in self.CASH_ASSETS or coin == self.base_currency:
                self.cash_value_base += market_value
            else:
                pair_symbol = f"{coin}/{self.base_currency}"
                self.risky_assets.append(pair_symbol)
                positions_for_ui.append([coin, amount, current_price, market_value])

        self.weights_dict = {
            pos[0]: (pos[3] / self.total_value) if self.total_value > 0 else 0.0
            for pos in positions_for_ui
        }
        sum_risky_weights = sum(self.weights_dict.values())
        cash_weight = (self.cash_value_base / self.total_value) if self.total_value > 0 else 0.0

        daily_pnl = 0.0
        try:
            daily_pnl = await self._fetch_daily_pnl(tickers)
        except Exception as e:
            app_logger.warning(f"CryptoBroker: P&L calculation failed: {e}")

        fx_conversion_rate = await self.get_fx_rate("USDT", self.target_currency)
        
        self.total_value *= fx_conversion_rate
        self.cash_value_base *= fx_conversion_rate
        daily_pnl *= fx_conversion_rate
        
        for pos in positions_for_ui:
            pos[2] *= fx_conversion_rate
            pos[3] *= fx_conversion_rate

        return {
            "nlv":               self.total_value,
            "cash":              self.cash_value_base,
            "currency":          self.target_currency,
            "pnl":               daily_pnl,
            "positions":         positions_for_ui,
            "risky_weight":      sum_risky_weights * 100,
            "cash_weight":       cash_weight * 100,
            "raw_weights_dict":  self.weights_dict,
            "sum_risky_weights": sum_risky_weights,
        }
    async def fetch_historical_data(self, cache_file: str = "data/crypto_prices_cache.parquet") -> pd.DataFrame:
        """
        Downloads daily OHLCV candles for all risky assets.
        Implements incremental caching identical in logic to IBKRBroker:
          - On first run: fetches up to `limit` candles (~1000 days).
          - On subsequent runs: fetches only the days missing since last cache date.
          - If new assets are detected: invalidates cache and does a full re-fetch.
        """
        app_logger.info(f"CryptoBroker: Fetching historical data for {self.risky_assets}")

        if not self.risky_assets:
            return pd.DataFrame()

        FULL_LIMIT = 1000
        cached_df = pd.DataFrame()
        since_ms: int | None = None

        if os.path.exists(cache_file):
            try:
                cached_df = pd.read_parquet(cache_file)
                cached_symbols = set(cached_df.columns.tolist())
                current_symbols = {pair.split("/")[0] for pair in self.risky_assets}

                if current_symbols - cached_symbols:
                    new = current_symbols - cached_symbols
                    app_logger.info(f"CryptoBroker: New assets {new} detected — invalidating cache.")
                    cached_df = pd.DataFrame()
                else:
                    last_date = cached_df.index.max()
                    today = pd.Timestamp.now(tz="UTC").normalize()
                    days_missing = (today - last_date).days

                    if days_missing <= 0:
                        app_logger.info("CryptoBroker: Cache is up to date.")
                        return cached_df

                    since_ms = int(last_date.timestamp() * 1000)
                    app_logger.info(f"CryptoBroker: Cache found. Fetching {days_missing} missing day(s).")
            except Exception as e:
                app_logger.error(f"CryptoBroker: Failed to read cache: {e}. Full re-fetch.")
                cached_df = pd.DataFrame()

        async def fetch_single_asset(symbol: str):
            coin = symbol.split("/")[0]
            try:
                kwargs = {"timeframe": "1d", "limit": FULL_LIMIT}
                if since_ms is not None:
                    kwargs["since"] = since_ms
                ohlcv = await self.exchange.fetch_ohlcv(symbol, **kwargs)
                if not ohlcv:
                    app_logger.warning(f"CryptoBroker: No OHLCV data returned for {symbol}.")
                    return coin, None

                df = pd.DataFrame(
                    ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
                )
                df["date"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.normalize()
                df.set_index("date", inplace=True)
                return coin, df["close"]

            except ccxt.BadSymbol:
                app_logger.error(f"CryptoBroker: Symbol {symbol} not available on this exchange.")
            except Exception as e:
                app_logger.error(f"CryptoBroker: Error fetching {symbol}: {e}")
            return coin, None

        tasks   = [fetch_single_asset(sym) for sym in self.risky_assets]
        results = await asyncio.gather(*tasks)

        valid_series = [
            series.rename(coin)
            for coin, series in results
            if series is not None
        ]

        if not valid_series:
            return cached_df if not cached_df.empty else pd.DataFrame()

        new_data = pd.concat(valid_series, axis=1)

        if not cached_df.empty:
            all_prices = pd.concat([cached_df, new_data])
            all_prices = all_prices[~all_prices.index.duplicated(keep="last")]
            all_prices.sort_index(inplace=True)
        else:
            all_prices = new_data

        all_prices.ffill(inplace=True)
        all_prices.dropna(inplace=True)

        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        all_prices.to_parquet(cache_file)
        app_logger.info("CryptoBroker: Historical cache updated.")

        return all_prices
    
    async def get_fx_rate(self, from_currency: str, to_currency: str) -> float:
        """
        Resolves FX rates between fiat/stablecoin currencies.
        Tries the exchange first, then falls back to the Frankfurter API.
        Maps USD-pegged stablecoins to regular USD to prevent 404 errors.
        """
        if from_currency == to_currency:
            return 1.0
        pair = f"{from_currency}/{to_currency}"
        try:
            tickers = await self.exchange.fetch_tickers([pair])
            if pair in tickers and tickers[pair].get("last"):
                return float(tickers[pair]["last"])
        except Exception:
            pass

        try:
            stablecoins = {"USDT", "USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USDP", "RLUSD"}
            
            query_from = "USD" if from_currency in stablecoins else from_currency
            query_to   = "USD" if to_currency in stablecoins else to_currency
            
            if query_from == query_to:
                return 1.0

            async with aiohttp.ClientSession() as session:
                url = f"https://api.frankfurter.app/latest?from={query_from}&to={query_to}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = data.get("rates", {}).get(query_to)
                        if price:
                            app_logger.info(f"CryptoBroker: FX rate {from_currency}->{to_currency} resolved via Frankfurter ({price:.4f}).")
                            return float(price)
                    else:
                        app_logger.warning(f"CryptoBroker: Frankfurter API does not support {from_currency} or {to_currency} (Status: {response.status}).")
        except Exception as e:
            app_logger.warning(f"CryptoBroker: Frankfurter FX fallback failed for {from_currency}/{to_currency}: {e}")

        app_logger.warning(f"CryptoBroker: Could not resolve FX rate {from_currency}->{to_currency}. Defaulting to 1.0.")
        return 1.0