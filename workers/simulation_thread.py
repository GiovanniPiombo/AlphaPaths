import asyncio
from PySide6.QtCore import QThread, Signal
from core.portfolio import PortfolioManager
import numpy as np
from core.montecarlo import MonteCarloSimulator
from core.utils import read_json
from core.path_manager import PathManager

class SimulationWorker(QThread):
    """
    Orchestrates the complete data fetching and initial simulation pipeline.

    This thread bridges the synchronous PySide6 UI with the asynchronous IBKR 
    network calls. It connects to the broker, downloads current portfolio 
    holdings, fetches 5 years of historical pricing, calculates the risk metrics 
    (drift and volatility), and runs the initial Monte Carlo simulation. 
    Finally, it pre-calculates the necessary NumPy arrays for chart rendering 
    to prevent UI freezing.

    Signals:
        progress_update (str): Emitted during state changes to update UI loading text.
        data_fetched (dict, float, float, float, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray): 
            Emitted upon complete success. Payload includes: scenarios, mu, sigma, 
            capital, time_steps, worst_line, median_line, best_line, background_lines.
        error_occurred (str): Emitted if network or calculation errors occur.

    Attributes:
        years (int): The time horizon for the Monte Carlo projection.
        simulations (int): The number of independent price paths to generate.
    """
    progress_update = Signal(str)
    data_fetched = Signal(dict, float, float, float, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray) 
    error_occurred = Signal(str)

    def __init__(self, years: int, simulations: int):
        """
        Initializes the simulation worker.

        Args:
            years (int): The duration of the simulation in years.
            simulations (int): The total number of price paths to compute.
        """
        super().__init__()
        self.years = years
        self.simulations = simulations

    def run(self):
        """
        Entry point for the QThread.

        Wraps the asynchronous `run_simulation_tasks` coroutine in an `asyncio.run()` 
        call, creating an isolated event loop for the network and processing tasks. 
        Catches and emits any unhandled exceptions to prevent application crashes.
        """
        try:
            asyncio.run(self.run_simulation_tasks())
        except Exception as e:
            self.error_occurred.emit(f"Simulation Worker Error: {str(e)}")

    async def run_simulation_tasks(self):
        """
        Executes the sequential phases of data retrieval and calculation.

        Phase 1: Connects to IBKR and fetches current portfolio balances.
        Phase 2: Downloads historical data and computes `mu` and `sigma`.
        Phase 3: Executes the `MonteCarloSimulator` and calculates the 5th, 
            50th, and 95th percentile paths using NumPy vectorized sorting.
        """

        host = read_json(PathManager.CONFIG_FILE, "IBKR_HOST") or '127.0.0.1'
        port = read_json(PathManager.CONFIG_FILE, "IBKR_PORT") or 4001
        client_id = read_json(PathManager.CONFIG_FILE, "IBKR_CLIENT_ID") or 1

        pm = PortfolioManager(host=host, port=port, client_id=client_id)
        
        self.progress_update.emit(f"Connecting to IBKR ({host}:{port})...")
        connected = await pm.connect()
        if not connected:
            self.error_occurred.emit("Failed to connect to IBKR. Is TWS/Gateway running?")
            return

        try:
            # ── PHASE 1 ───────────────────────────────────
            self.progress_update.emit("Fetching current portfolio...")
            await pm.fetch_summary_and_positions()

            # ── PHASE 2 ───────────────────────────────────
            self.progress_update.emit("Downloading historical data for risk metrics...")
            historical_prices = await pm.fetch_historical_data()

            self.progress_update.emit("Calculating risk metrics...")
            mu, sigma = pm.calculate_risk_metrics(historical_prices)
            capital = pm.total_value

            # ── PHASE 3 ───────────────────────────────────
            self.progress_update.emit("Running initial Monte Carlo...")
            scenarios, simulated_prices = pm.run_montecarlo_simulation(
                years=self.years,
                simulations=self.simulations
            )

            sims_transposed = simulated_prices.T
            worst_line = np.percentile(sims_transposed, 5, axis=0)
            median_line = np.percentile(sims_transposed, 50, axis=0)
            best_line = np.percentile(sims_transposed, 95, axis=0)
            time_steps = np.arange(sims_transposed.shape[1])
            background_lines = sims_transposed[:100, :]

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
    A lightweight thread for rapid Monte Carlo recalculations.

    Unlike the `SimulationWorker`, this thread does not make any network calls 
    to IBKR. It utilizes cached portfolio metrics (capital, mu, sigma) to rapidly 
    execute new Monte Carlo simulations when the user changes UI parameters 
    (like 'Years' or 'Simulations'). It offloads the heavy `np.percentile` 
    sorting from the main thread to maintain a 60 FPS UI experience.

    Signals:
        data_calculated (dict, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray):
            Emitted when calculations are done. Payload includes: scenarios, 
            time_steps, worst_line, median_line, best_line, background_lines.
        error_occurred (str): Emitted if mathematical errors or memory issues occur.

    Attributes:
        capital (float): The cached starting portfolio value.
        mu (float): The cached annualized expected return.
        sigma (float): The cached annualized volatility.
        years (int): The new time horizon to simulate.
        simulations (int): The new number of paths to generate.
    """
    data_calculated = Signal(dict, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray)
    error_occurred = Signal(str)

    def __init__(self, capital, mu, sigma, years, simulations):
        """
        Initializes the fast math worker with cached financial metrics.

        Args:
            capital (float): Starting value of the portfolio.
            mu (float): Annualized drift of the portfolio.
            sigma (float): Annualized volatility of the portfolio.
            years (int): Years to project forward.
            simulations (int): Number of paths to simulate.
        """
        super().__init__()
        self.capital = capital
        self.mu = mu
        self.sigma = sigma
        self.years = years
        self.simulations = simulations

    def run(self):
        """
        Executes the mathematical engine and processes the output arrays.

        Instantiates the `MonteCarloSimulator`, generates the raw price paths, 
        and calculates the required percentiles (5%, 50%, 95%) across the entire 
        matrix. It slices the first 100 paths for background visualization 
        before emitting the prepared data back to the UI.
        """
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
            
            worst_line = np.percentile(sims_transposed, 5, axis=0)
            median_line = np.percentile(sims_transposed, 50, axis=0)
            best_line = np.percentile(sims_transposed, 95, axis=0)
            
            time_steps = np.arange(sims_transposed.shape[1])
            
            background_lines = sims_transposed[:100, :]
            
            self.data_calculated.emit(
                scenarios, time_steps, worst_line, median_line, best_line, background_lines
            )
        except Exception as e:
            self.error_occurred.emit(f"Fast Math Error: {str(e)}")