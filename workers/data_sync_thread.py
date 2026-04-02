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
import asyncio
from PySide6.QtCore import QThread, Signal
from core.portfolio import PortfolioManager
from core.brokers.ibkr_broker import IBKRBroker
from core.utils import read_json
from core.path_manager import PathManager
from core.logger import app_logger
from core.brokers.factory import BrokerFactory

class DataSyncWorker(QThread):
    """
    A dedicated background thread for fetching portfolio data without freezing the UI.
    Now utilizes the Dependency Injection pattern to supply the PortfolioManager 
    with the required Broker adapter.
    """
    data_fetched = Signal(dict)
    error_occurred = Signal(str)
    progress_update = Signal(str)

    def run(self):
        app_logger.debug("THREAD STARTED: Creating asyncio event loop for Broker sync...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            app_logger.debug("THREAD: Starting fetch_data_from_manager...")
            data = loop.run_until_complete(self.fetch_data_from_manager())
            
            app_logger.info("THREAD: Data successfully fetched, emitting signal...")
            self.data_fetched.emit(data)
        except Exception as e:
            app_logger.critical(f"CRITICAL THREAD ERROR IN BROKER SYNC: {e}")
            self.error_occurred.emit(str(e))
        finally:
            loop.close()
            app_logger.debug("THREAD FINISHED: Broker loop closed.")

    async def fetch_data_from_manager(self):
        broker = BrokerFactory.get_active_broker()
        manager = PortfolioManager(broker=broker)
        
        self.progress_update.emit("Connecting to Broker...")
        await manager.connect()
        app_logger.info("Broker: Connected successfully!")
        
        try:
            self.progress_update.emit("Analyzing assets and converting currencies (FX)...")
            
            portfolio_data = await manager.fetch_summary_and_positions()
            
            app_logger.debug("Broker: Returning formatted data for the UI...")
            
            # Temporary placeholders until Monte Carlo runs
            portfolio_data["mu"] = 0.05
            portfolio_data["sigma"] = 0.15
            
            self.progress_update.emit("Operation completed successfully!")
            return portfolio_data

        finally:
            app_logger.info("Broker: Disconnecting manager.")
            manager.disconnect()