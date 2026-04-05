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

import numpy as np
from core.logger import app_logger

TRADING_DAYS_PER_YEAR = 252

class GARCHSimulator:
    """
    Executes Monte Carlo simulations using a GARCH(1,1) model.
    Unlike standard GBM (which uses constant volatility), this model 
    dynamically updates volatility at each time step, capturing the 
    "volatility clustering" phenomenon typical of real financial markets.
    """

    def __init__(self, capital: float, mu: float, years: int, simulations: int = 10000,
                 omega: float = 0.0, alpha: float = 0.0, beta: float = 0.0, 
                 initial_variance: float = 0.0):
        """
        Initializes the GARCH(1,1) simulator.

        Args:
            capital (float): Initial capital (must be > 0).
            mu (float): Annualized expected return (drift).
            years (int): Time horizon in years.
            simulations (int): Number of paths to simulate.
            omega (float): Base constant of the GARCH model (long-term weight).
            alpha (float): ARCH coefficient (reaction to recent market shocks).
            beta (float): GARCH coefficient (persistence of past volatility).
            initial_variance (float): The starting daily variance for the simulation.
        """
        if capital <= 0:
            app_logger.error("Invalid capital value. Capital must be strictly positive.")
            raise ValueError("Capital must be strictly positive.")
        if years < 0:
            app_logger.error("Invalid years value. Years cannot be negative.")
            raise ValueError("Years cannot be negative.")
        if simulations <= 0:
            app_logger.error("Invalid simulations value. Number of simulations must be at least 1.")
            raise ValueError("Number of simulations must be at least 1.")
        
        # In a stationary GARCH model, alpha + beta should be < 1
        if alpha + beta >= 1.0:
            app_logger.warning("GARCH model may be non-stationary (alpha + beta >= 1). Simulations might produce extreme volatility.")
            pass

        self.capital = capital
        self.mu = mu
        self.years = years
        self.simulations = simulations
        self.omega = omega
        self.alpha = alpha
        self.beta = beta
        self.initial_variance = initial_variance

    def simulate(self) -> np.ndarray:
        """
        Executes the Monte Carlo simulation. Vectorized across simulation paths, 
        but iterative over time to respect the GARCH autoregressive property.

        Returns:
            np.ndarray: A 2D array containing the simulated price paths.
        """
        total_steps = int(self.years * TRADING_DAYS_PER_YEAR)
        dt = 1.0 / TRADING_DAYS_PER_YEAR
        
        simulated_prices = np.zeros((total_steps + 1, self.simulations))
        simulated_prices[0, :] = self.capital
        current_var = np.full(self.simulations, self.initial_variance)
        daily_drift = self.mu * dt
        
        for t in range(1, total_steps + 1):
            Z = np.random.standard_normal(self.simulations)
            current_vol = np.sqrt(current_var)
            epsilon = current_vol * Z
            step_return = (daily_drift - 0.5 * current_var) + epsilon
            simulated_prices[t, :] = simulated_prices[t - 1, :] * np.exp(step_return)
            current_var = self.omega + self.alpha * (epsilon ** 2) + self.beta * current_var
            current_var = np.clip(current_var, a_min=1e-10, a_max=1.0)
        return simulated_prices

    def get_scenarios(self, simulated_prices: np.ndarray) -> dict:
        """
        Extracts key percentiles from the final day of the simulation.

        Args:
            simulated_prices (np.ndarray): The matrix of simulated paths.

        Returns:
            dict: A dictionary containing the portfolio values at the 5th, 50th, and 95th percentiles.
        """
        final_prices = simulated_prices[-1, :]
        return {
            "Worst (5%)": np.percentile(final_prices, 5), 
            "Median (50%)": np.percentile(final_prices, 50), 
            "Best (95%)": np.percentile(final_prices, 95)    
        }