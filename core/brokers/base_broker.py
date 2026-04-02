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
from abc import ABC, abstractmethod
import pandas as pd

class BaseBroker(ABC):
    """
    Abstract Base Class defining the standard interface for all broker integrations.
    
    Any new broker module must inherit from this class 
    and implement all of its abstract methods. This Adapter pattern ensures that 
    the core application logic (Monte Carlo, Markowitz, UI) remains completely 
    decoupled from specific broker APIs.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establishes an asynchronous connection to the broker's API.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Safely terminates the connection to the broker's API.
        """
        pass

    @abstractmethod
    async def fetch_summary_and_positions(self) -> dict:
        """
        Retrieves the account summary, daily P&L, and open positions.

        Returns:
            dict: A standardized dictionary containing exact keys expected by the UI:
                - 'nlv' (float): Net Liquidation Value in base currency.
                - 'cash' (float): Total cash available in base currency.
                - 'currency' (str): The base currency of the account/display.
                - 'pnl' (float): The daily Profit & Loss.
                - 'positions' (list): A list of lists formatted for the UI table:
                                      [[Symbol, Quantity, Current Price, Market Value], ...]
                - 'risky_weight' (float): Percentage of portfolio in risky assets (0-100).
                - 'cash_weight' (float): Percentage of portfolio in cash (0-100).
        """
        pass

    @abstractmethod
    async def fetch_historical_data(self, **kwargs) -> pd.DataFrame:
        """
        Downloads daily adjusted closing prices for all risky assets in the portfolio.

        Args:
            **kwargs: Optional broker-specific parameters (e.g., cache_file path, 
                      lookback periods, pacing limits).

        Returns:
            pd.DataFrame: A date-indexed DataFrame where each column represents 
                a ticker symbol and rows are daily adjusted close prices.
        """
        pass