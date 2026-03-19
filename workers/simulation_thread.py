import asyncio
from PySide6.QtCore import QThread, Signal
from core.portfolio import PortfolioManager
import numpy as np
from core.montecarlo import MonteCarloSimulator

class SimulationWorker(QThread):
    """A QThread that handles the entire simulation process, from fetching data to calculating risk metrics and running Monte Carlo simulations."""
    progress_update = Signal(str)
    data_fetched = Signal(dict, float, float, float, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray) 
    error_occurred = Signal(str)

    def __init__(self, years: int, simulations: int):
        """Initializes the worker with the number of years and simulations for the Monte Carlo."""
        super().__init__()
        self.years = years
        self.simulations = simulations

    def run(self):
        """Main method that runs when the thread starts. It orchestrates the entire simulation workflow."""
        try:
            asyncio.run(self.run_simulation_tasks())
        except Exception as e:
            self.error_occurred.emit(f"Simulation Worker Error: {str(e)}")

    async def run_simulation_tasks(self):
        """Asynchronous method that performs the simulation tasks step by step, emitting progress updates and final data."""
        pm = PortfolioManager(host='127.0.0.1', port=4001, client_id=1)
        
        self.progress_update.emit("Connecting to IBKR...")
        connected = await pm.connect()
        if not connected:
            self.error_occurred.emit("Failed to connect to IBKR. Is TWS/Gateway running?")
            return

        try:
            # --- PHASE 1 ---
            self.progress_update.emit("Fetching current portfolio...")
            await pm.fetch_summary_and_positions()

            # --- PHASE 2 ---
            self.progress_update.emit("Downloading historical data for risk metrics...")
            historical_prices = await pm.fetch_historical_data()

            self.progress_update.emit("Calculating risk metrics...")
            mu, sigma = pm.calculate_risk_metrics(historical_prices)
            capital = pm.total_value

            # --- PHASE 3 ---
            self.progress_update.emit("Running initial Monte Carlo...")
            scenarios, simulated_prices = pm.run_montecarlo_simulation(
                years=self.years,
                simulations=self.simulations
            )

            # --- PRE-CALCULATE GRAPH LINES (Just like FastMathWorker) ---
            sims_transposed = simulated_prices.T
            worst_line = np.percentile(sims_transposed, 5, axis=0)
            median_line = np.percentile(sims_transposed, 50, axis=0)
            best_line = np.percentile(sims_transposed, 95, axis=0)
            time_steps = np.arange(sims_transposed.shape[1])
            background_lines = sims_transposed[:100, :]

            # Send the cached variables AND the calculated lines back to the UI
            self.data_fetched.emit(
                scenarios, mu, sigma, capital, 
                time_steps, worst_line, median_line, best_line, background_lines
            )

        except Exception as e:
            self.error_occurred.emit(f"Error during simulation: {str(e)}")
        finally:
            pm.disconnect()

class FastMathWorker(QThread):
    """
    A lightweight thread that calculates both the simulation and the graph lines,
    preventing the UI from freezing due to np.percentile sorting.
    """
    data_calculated = Signal(dict, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray)
    error_occurred = Signal(str)

    def __init__(self, capital, mu, sigma, years, simulations):
        super().__init__()
        self.capital = capital
        self.mu = mu
        self.sigma = sigma
        self.years = years
        self.simulations = simulations

    def run(self):
        try:
            simulator = MonteCarloSimulator(
                capital=self.capital,
                mu=self.mu,
                sigma=self.sigma,
                years=self.years,
                simulations=self.simulations
            )
            simulated_prices = simulator.simulate()
            scenarios = simulator.get_scenarios(simulated_prices)
            
            sims_transposed = simulated_prices.T
            
            # Calculate percentiles across all days
            worst_line = np.percentile(sims_transposed, 5, axis=0)
            median_line = np.percentile(sims_transposed, 50, axis=0)
            best_line = np.percentile(sims_transposed, 95, axis=0)
            
            # X-Axis array (Trading Days)
            time_steps = np.arange(sims_transposed.shape[1])
            
            # Extract only the first 100 simulations for the background visual context
            background_lines = sims_transposed[:100, :]
            
            # Send the results AND the pre-calculated lines back to the UI
            self.data_calculated.emit(
                scenarios, time_steps, worst_line, median_line, best_line, background_lines
            )
        except Exception as e:
            self.error_occurred.emit(f"Fast Math Error: {str(e)}")