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

TRADING_DAYS_PER_YEAR = 252

class MJDSimulator:
    """
    Executes Monte Carlo simulations using the Merton Jump-Diffusion Model.
    Extends Geometric Brownian Motion by adding discrete (Poisson) jumps 
    to model price gaps and sudden market crashes.
    """

    def __init__(self, capital: float, mu: float, sigma: float, years: int, simulations: int = 10000,
                 lam: float = 0.0, m: float = 0.0, nu: float = 0.0):
        """
        Initializes the MJD simulator.

        Args:
            capital (float): Initial capital (must be > 0).
            mu (float): Annualized expected return (drift).
            sigma (float): Annualized volatility (of the continuous component).
            years (int): Time horizon in years.
            simulations (int): Number of paths to simulate.
            lam (float): Lambda, expected number of jumps per year (frequency).
            m (float): Mean of the logarithmic jump (average impact).
            nu (float): Standard deviation of the jump size (jump volatility).
        """
        if capital <= 0:
            raise ValueError("Capital must be strictly positive.")
        if sigma < 0:
            raise ValueError("Volatility (sigma) cannot be negative.")
        if years < 0:
            raise ValueError("Years cannot be negative.")
        if simulations <= 0:
            raise ValueError("Number of simulations must be at least 1.")
        if lam < 0 or nu < 0:
            raise ValueError("Lambda and nu cannot be negative.")

        self.capital = capital
        self.mu = mu
        self.sigma = sigma
        self.years = years
        self.simulations = simulations
        self.lam = lam
        self.m = m
        self.nu = nu

    def simulate(self) -> np.ndarray:
        """
        Executes the vectorized simulation by calculating the continuous diffusion 
        and adding the Poisson jumps.

        Returns:
            np.ndarray: A 2D array containing the simulated price paths.
        """
        total_steps = int(self.years * TRADING_DAYS_PER_YEAR)
        dt = 1.0 / TRADING_DAYS_PER_YEAR  
        
        k = np.exp(self.m + (self.nu ** 2) / 2.0) - 1.0
        
        drift = (self.mu - (self.sigma ** 2) / 2.0 - self.lam * k) * dt 
        epsilon = np.random.standard_normal(size=(total_steps, self.simulations)) 
        continuous_shock = self.sigma * np.sqrt(dt) * epsilon 
        
        poisson_rv = np.random.poisson(lam=self.lam * dt, size=(total_steps, self.simulations))
        
        jump_sizes = np.random.normal(
            loc=self.m * poisson_rv, 
            scale=self.nu * np.sqrt(poisson_rv)
        )
        
        daily_multiplier = np.exp(drift + continuous_shock + jump_sizes)
        cumulative_multiplier = np.cumprod(daily_multiplier, axis=0)
        
        day_zero_multiplier = np.ones((1, self.simulations))
        full_multiplier = np.vstack([day_zero_multiplier, cumulative_multiplier])
        simulated_prices = self.capital * full_multiplier
        
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