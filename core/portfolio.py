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
import pandas as pd
import numpy as np
from core.brokers.base_broker import BaseBroker
from core.gbm_model import GBMSimulator
from core.merton_model import MJDSimulator
from core.ai_review import get_portfolio_analysis
from core.utils import read_json
from core.path_manager import PathManager
from core.logger import app_logger

class PortfolioManager:
    """
    Orchestrates data fetching, risk calculations, and simulation workflows.

    This class relies on an injected `BaseBroker` instance to retrieve account 
    balances and historical pricing. It calculates core financial metrics 
    (drift and volatility) and acts as the bridge connecting the raw brokerage 
    data to the mathematical engines and the AI review module.
    """
    TRADING_DAYS = 252

    def __init__(self, broker: BaseBroker):
        """
        Initializes the PortfolioManager with a specific broker adapter.

        Args:
            broker (BaseBroker): An initialized instance of a broker adapter 
                (e.g., IBKRBroker, AlpacaBroker) that implements the BaseBroker interface.
        """
        self.broker = broker

        self.total_value = 0.0
        self.base_currency = ""
        self.cash_value_base = 0.0
        self.cash_weight = 0.0
        self.sum_risky_weights = 0.0
        self.weights_dict = {}
        
        self.total_portfolio_mu = 0.0
        self.total_portfolio_vol = 0.0

        self.config_rf_rate = float(read_json(PathManager.CONFIG_FILE, "RISK_FREE_RATE") or 0.0)
        self.config_jump_thresh = float(read_json(PathManager.CONFIG_FILE, "JUMP_THRESHOLD") or 3.0)

    # ── DELEGATED BROKER CALLS ──────────────────────────────────
    async def connect(self) -> bool:
        """Delegates the connection request to the active broker."""
        return await self.broker.connect()

    def disconnect(self):
        """Delegates the disconnection request to the active broker."""
        self.broker.disconnect()

    async def fetch_summary_and_positions(self) -> dict:
        """
        Retrieves the account summary from the broker and updates the internal state 
        required for mathematical risk calculations.

        Returns:
            dict: The formatted dictionary containing UI-ready data.
        """
        data = await self.broker.fetch_summary_and_positions()
        
        self.total_value = data['nlv']
        self.cash_value_base = data['cash']
        self.base_currency = data['currency']
        self.weights_dict = data['raw_weights_dict']
        self.sum_risky_weights = data['sum_risky_weights']
        self.cash_weight = data['cash_weight'] / 100.0 
        
        return data

    async def fetch_historical_data(self, **kwargs) -> pd.DataFrame:
        """Delegates the historical data fetching to the active broker."""
        return await self.broker.fetch_historical_data(**kwargs)

    # ── MATHEMATICAL UTILITIES ──────────────────────────────────
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

    # ── RISK AND SIMULATION ENGINES ─────────────────────────
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