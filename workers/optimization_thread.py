from PySide6.QtCore import QThread, Signal
import numpy as np
from core.markowitz_model import MarkowitzOptimizer
from core.logger import app_logger

class OptimizationWorker(QThread):
    """
    A dedicated background thread for running Modern Portfolio Theory optimizations
    with Core-Satellite (locked assets) constraints.

    This worker prevents the PySide6 UI from freezing while SciPy performs 
    complex matrix minimizations. It handles the translation of user-selected 
    "locked" assets into strict mathematical bounds, ensuring the optimizer 
    only reallocates the free "satellite" portion of the portfolio.

    Signals:
        optimization_finished (dict): Emitted upon successful calculation. Contains 
            current stats, optimal stats, frontier points, asset symbols, and weights.
        error_occurred (str): Emitted if an exception is raised during optimization.
        progress_update (str): Emitted at various stages to update UI loading states.
    """
    optimization_finished = Signal(dict)
    error_occurred = Signal(str)
    progress_update = Signal(str)

    def __init__(self, metrics: dict, positions: list, locked_symbols: list):
        """
        Initializes the optimization worker with market data and user constraints.

        Args:
            metrics (dict): The pre-calculated risk metrics exported by PortfolioManager.
                Must contain 'asset_returns', 'cov_matrix', 'symbols', and 'risk_free_rate'.
            positions (list): The list of current holdings formatted for the UI.
                Expected format per item: [Ticker, Quantity, Current Price, Market Value]
            locked_symbols (list): A list of ticker strings (e.g., ['VWCE']) that the 
                user wishes to freeze at their current portfolio weight.
        """
        super().__init__()
        self.metrics = metrics
        self.positions = positions
        self.locked_symbols = locked_symbols

    def run(self):
        """
        Executes the optimization pipeline in a background thread.

        Steps performed:
        1. Extracts pre-calculated returns and covariance from the metrics payload.
        2. Calculates the exact current weight of each asset in the risky portfolio.
        3. Generates the 'bounds' tuple for SciPy: locked assets get min/max bounds 
           equal to their current weight, while free assets get bounds from 0.0 to 1.0.
        4. Evaluates the current portfolio's performance.
        5. Computes the constrained Maximum Sharpe Ratio portfolio.
        6. Generates the constrained Efficient Frontier curve.
        7. Packages and emits the results back to the UI thread.
        """
        try:
            app_logger.debug(f"OptimizationWorker started. Locked assets: {self.locked_symbols}")
            self.progress_update.emit("Initializing Markowitz engine...")
            
            asset_returns = self.metrics.get("asset_returns", {})
            cov_matrix = self.metrics.get("cov_matrix", {})
            symbols = self.metrics.get("symbols", [])
            risk_free = self.metrics.get("risk_free_rate", 0.0)

            if not symbols:
                raise ValueError("No risky assets available for optimization.")

            total_risky_value = sum([pos[3] for pos in self.positions if pos[0] in symbols])
            current_weights = {}
            if total_risky_value > 0:
                for pos in self.positions:
                    if pos[0] in symbols:
                        current_weights[pos[0]] = pos[3] / total_risky_value

            optimizer = MarkowitzOptimizer(asset_returns, cov_matrix, symbols, risk_free)
            self.progress_update.emit("Evaluating current allocation...")
            current_stats = optimizer.evaluate_current_portfolio(current_weights)

            bounds = []
            initial_guess = []
            for sym in symbols:
                cw = current_weights.get(sym, 0.0)
                initial_guess.append(cw)
                
                if sym in self.locked_symbols:
                    bounds.append((cw, cw)) 
                else:
                    bounds.append((0.0, 1.0)) 
            
            bounds_tuple = tuple(bounds)
            initial_array = np.array(initial_guess)

            self.progress_update.emit("Finding optimal Max Sharpe portfolio...")
            app_logger.debug("Starting scipy SLSQP minimization...")
            optimal_stats = optimizer.optimize_max_sharpe(bounds=bounds_tuple, initial_guess=initial_array)

            self.progress_update.emit("Calculating the constrained Efficient Frontier...")
            app_logger.debug("Generating frontier curve points...")
            frontier_points = optimizer.generate_efficient_frontier(points=40, bounds=bounds_tuple, initial_guess=initial_array)

            payload = {
                "current": current_stats,
                "optimal": optimal_stats,
                "frontier": frontier_points,
                "symbols": symbols,
                "current_weights": current_weights
            }

            self.progress_update.emit("Optimization complete!")
            app_logger.info("Optimization Worker finished successfully.")
            self.optimization_finished.emit(payload)

        except Exception as e:
            app_logger.exception(f"Optimization Worker crashed: {str(e)}")
            self.error_occurred.emit(f"Optimization Worker Error: {str(e)}")