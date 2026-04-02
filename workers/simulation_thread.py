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
import numpy as np

from core.portfolio import PortfolioManager
from core.brokers.ibkr_broker import IBKRBroker
from core.gbm_model import GBMSimulator
from core.merton_model import MJDSimulator
from core.path_manager import PathManager
from core.logger import app_logger
from core.brokers.factory import BrokerFactory

class SimulationWorker(QThread):
    """
    A background worker thread for fetching portfolio data from the broker
    and executing full Monte Carlo simulations.

    This thread handles API connections, data fetching, risk metric calculations, 
    and running both Geometric Brownian Motion (GBM) and Merton Jump-Diffusion models 
    to prevent blocking the main UI.

    Attributes:
        progress_update (Signal): Emits string updates about the current execution step.
        data_fetched (Signal): Emits a dictionary containing the final simulation payloads and metrics.
        error_occurred (Signal): Emits a string describing any exceptions caught during execution.
    """

    progress_update = Signal(str)
    data_fetched = Signal(dict) 
    error_occurred = Signal(str)

    def __init__(self, years: int, simulations: int):
        """
        Initializes the simulation worker.

        Args:
            years (int): The time horizon for the simulation in years.
            simulations (int): The number of simulation paths to generate.
        """
        super().__init__()
        self.years = years
        self.simulations = simulations

    def run(self):
        """
        Executes the QThread. 
        
        Sets up the asyncio event loop to run the asynchronous simulation tasks 
        and catches any top-level exceptions to emit via the error signal.
        """
        try:
            asyncio.run(self.run_simulation_tasks())
        except Exception as e:
            app_logger.exception(f"Error during simulation: {str(e)}")
            self.error_occurred.emit(f"Simulation Worker Error: {str(e)}")

    async def run_simulation_tasks(self):
        """
        Asynchronously connects to the IBKR API, retrieves portfolio data, 
        and executes the simulation pipelines.

        Steps performed:
        1. Connects to the Broker.
        2. Fetches current summary, positions, and historical price data.
        3. Calculates risk metrics separating cash and risky assets.
        4. Runs both standard (GBM) and stress-test (Merton) simulations.
        5. Calculates the 5th, 50th, and 95th percentiles for the generated paths.
        6. Emits the formatted payload to the main UI.
        """
        broker = BrokerFactory.get_active_broker()
        pm = PortfolioManager(broker=broker)
        
        self.progress_update.emit("Connecting to Broker ...")
        connected = await pm.connect()
        if not connected:
            self.error_occurred.emit("Failed to connect to Broker. Is the gateway running?")
            return

        try:
            self.progress_update.emit("Fetching current portfolio...")
            await pm.fetch_summary_and_positions()

            self.progress_update.emit("Downloading historical data for risk metrics...")
            historical_prices = await pm.fetch_historical_data()

            self.progress_update.emit("Calculating separated risk metrics...")
            metrics = pm.calculate_risk_metrics(historical_prices)

            self.progress_update.emit("Running GBM and MJD simulations...")
            sim_results = pm.run_montecarlo_simulation(
                metrics=metrics,
                years=self.years,
                simulations=self.simulations
            )

            gbm_t = sim_results["gbm"]["prices"].T
            gbm_data = {
                "scenarios": sim_results["gbm"]["scenarios"],
                "worst": np.percentile(gbm_t, 5, axis=0),
                "median": np.percentile(gbm_t, 50, axis=0),
                "best": np.percentile(gbm_t, 95, axis=0),
                "background": gbm_t[:100, :]
            }

            merton_t = sim_results["merton"]["prices"].T
            merton_data = {
                "scenarios": sim_results["merton"]["scenarios"],
                "worst": np.percentile(merton_t, 5, axis=0),
                "median": np.percentile(merton_t, 50, axis=0),
                "best": np.percentile(merton_t, 95, axis=0),
                "background": merton_t[:100, :]
            }

            payload = {
                "gbm": gbm_data,
                "merton": merton_data,
                "metrics": metrics,
                "time_steps": np.arange(merton_t.shape[1])
            }

            self.data_fetched.emit(payload)

        except Exception as e:
            app_logger.exception(f"Error during simulation: {str(e)}")
            self.error_occurred.emit(f"Error during simulation: {str(e)}")
        finally:
            pm.disconnect()

class FastMathWorker(QThread):
    """
    A lightweight background worker thread for recalculating simulations 
    using pre-existing data.

    Unlike `SimulationWorker`, this thread does not connect to IBKR. It performs 
    fast mathematical recalculations of GBM and Merton models based on provided 
    risk metrics, allowing for quick UI updates when simulation parameters change.

    Attributes:
        data_calculated (Signal): Emits a dictionary containing the updated simulation payloads.
        error_occurred (Signal): Emits a string describing any exceptions caught during calculation.
    """
    data_calculated = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, metrics: dict, years: int, simulations: int):
        """
        Initializes the fast math worker.

        Args:
            metrics (dict): A dictionary containing pre-calculated risk and portfolio metrics.
            years (int): The time horizon for the simulation in years.
            simulations (int): The number of simulation paths to generate.
        """
        super().__init__()
        self.metrics = metrics
        self.years = years
        self.simulations = simulations

    def run(self):
        """
        Executes the QThread.

        Performs the following steps natively in the thread:
        1. Simulates purely risky capital paths using GBM and Merton Jump-Diffusion.
        2. Calculates a deterministic growth matrix for cash/risk-free capital.
        3. Merges the risky paths with the cash matrix.
        4. Calculates percentiles and emits the payload back to the main thread.
        """
        try:
            safe_capital = self.metrics["risky_capital"] if self.metrics["risky_capital"] > 0 else 1.0
            
            gbm_sim = GBMSimulator(safe_capital, self.metrics["risky_mu"], self.metrics["risky_vol"], self.years, self.simulations)
            risky_gbm = gbm_sim.simulate()
            if self.metrics["risky_capital"] <= 0: risky_gbm *= 0
            
            merton_sim = MJDSimulator(
                safe_capital, self.metrics["risky_mu"], self.metrics["risky_vol"], 
                self.years, self.simulations, self.metrics["lam"], self.metrics["m"], self.metrics["nu"]
            )
            risky_merton = merton_sim.simulate()
            if self.metrics["risky_capital"] <= 0: risky_merton *= 0

            dt = 1.0 / 252
            steps = int(self.years * 252)
            cash_growth = np.exp(self.metrics["risk_free_rate"] * dt * np.arange(steps + 1))
            cash_matrix = (self.metrics["cash_capital"] * cash_growth).reshape(-1, 1)

            total_gbm = risky_gbm + cash_matrix
            total_merton = risky_merton + cash_matrix

            gbm_t = total_gbm.T
            gbm_data = {
                "scenarios": gbm_sim.get_scenarios(total_gbm),
                "worst": np.percentile(gbm_t, 5, axis=0),
                "median": np.percentile(gbm_t, 50, axis=0),
                "best": np.percentile(gbm_t, 95, axis=0),
                "background": gbm_t[:100, :]
            }

            merton_t = total_merton.T
            merton_data = {
                "scenarios": merton_sim.get_scenarios(total_merton),
                "worst": np.percentile(merton_t, 5, axis=0),
                "median": np.percentile(merton_t, 50, axis=0),
                "best": np.percentile(merton_t, 95, axis=0),
                "background": merton_t[:100, :]
            }

            payload = {
                "gbm": gbm_data,
                "merton": merton_data,
                "time_steps": np.arange(merton_t.shape[1])
            }
            self.data_calculated.emit(payload)
        except Exception as e:
            app_logger.exception(f"Error during simulation: {str(e)}")
            self.error_occurred.emit(f"Fast Math Error: {str(e)}")