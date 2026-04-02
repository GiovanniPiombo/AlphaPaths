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
from core.brokers.ibkr_broker import IBKRBroker
from core.brokers.manual_broker import ManualBroker
from core.brokers.crypto_broker import CryptoBroker
from core.brokers.alpaca_broker import AlpacaBroker
from core.utils import read_json
from core.path_manager import PathManager
from core.logger import app_logger

class BrokerFactory:
    """
    Factory class responsible for instantiating the correct broker adapter
    based on user settings. 
    """
    
    @staticmethod
    def get_active_broker():
        """
        Reads the configuration and returns an initialized instance of a BaseBroker.
        In the future, this will check an "ACTIVE_BROKER" setting in config.json 
        to decide the broker to return.
        Defaults to ManualBroker (Yahoo Finance) if no setting is found.
        """
        active_broker = read_json(PathManager.CONFIG_FILE, "ACTIVE_BROKER") or "Manual (Yahoo Finance)"
        
        if active_broker == "Interactive Brokers":
            app_logger.info("BrokerFactory: Initializing IBKRBroker.")
            host = read_json(PathManager.CONFIG_FILE, "IBKR_HOST") or '127.0.0.1'
            port = read_json(PathManager.CONFIG_FILE, "IBKR_PORT") or 4001
            client_id = read_json(PathManager.CONFIG_FILE, "IBKR_CLIENT_ID") or 1
            return IBKRBroker(host=host, port=port, client_id=client_id)

        elif active_broker == "Alpaca":
            app_logger.info("BrokerFactory: Initializing AlpacaBroker.")
            return AlpacaBroker()
        
        elif active_broker == "Crypto Exchange":
            app_logger.info("BrokerFactory: Initializing CryptoBroker (CCXT).")
            return CryptoBroker()
        
        app_logger.info("BrokerFactory: Initializing ManualBroker (Yahoo Finance) as default.")
        return ManualBroker()