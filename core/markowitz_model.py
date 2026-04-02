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
import pandas as pd
import scipy.optimize as sco

class MarkowitzOptimizer:
    """
    Mathematical engine for Modern Portfolio Theory (MPT) optimization.
    
    This class takes annualized expected returns and a covariance matrix 
    to calculate the Efficient Frontier and identify the Maximum Sharpe 
    Ratio portfolio (Tangency Portfolio). It enforces long-only constraints 
    (no short selling) and requires the weights to sum to 100%.
    """
    
    def __init__(self, asset_returns: dict, cov_matrix: dict, symbols: list, risk_free_rate: float = 0.0):
        """
        Initializes the optimizer with the pre-calculated metrics.
        
        Args:
            asset_returns (dict): Annualized expected returns per ticker.
            cov_matrix (dict): Annualized covariance matrix (nested dictionary).
            symbols (list): The strict order of tickers to maintain matrix alignment.
            risk_free_rate (float, optional): The risk-free rate for Sharpe calculations.
        """
        self.symbols = symbols
        self.num_assets = len(symbols)
        self.risk_free_rate = risk_free_rate
        
        self.returns = np.array([asset_returns[sym] for sym in symbols])
        
        cov_df = pd.DataFrame(cov_matrix)
        self.cov_matrix = cov_df.loc[symbols, symbols].values

    def portfolio_performance(self, weights: np.ndarray) -> tuple:
        """
        Calculates the expected return and volatility for a given set of weights.
        """
        p_return = np.sum(self.returns * weights)
        p_volatility = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
        return p_return, p_volatility

    def negative_sharpe_ratio(self, weights: np.ndarray) -> float:
        """
        The objective function to minimize. 
        Minimizing the negative Sharpe ratio is mathematically equivalent 
        to maximizing the actual Sharpe ratio.
        """
        p_ret, p_vol = self.portfolio_performance(weights)
        if p_vol == 0:
            return 0.0
        return -(p_ret - self.risk_free_rate) / p_vol

    def minimize_volatility(self, weights: np.ndarray) -> float:
        """Objective function to find the absolute minimum variance portfolio."""
        _, p_vol = self.portfolio_performance(weights)
        return p_vol

    def optimize_max_sharpe(self, bounds: tuple = None, initial_guess: np.ndarray = None) -> dict:
        """
        Uses Sequential Least Squares Programming (SLSQP) to find the weights 
        that maximize the Sharpe Ratio, respecting optional constraints.
        """
        if initial_guess is None:
            initial_guess = np.array(self.num_assets * [1. / self.num_assets])
        if bounds is None:
            bounds = tuple((0.0, 1.0) for _ in range(self.num_assets))
            
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        
        result = sco.minimize(
            self.negative_sharpe_ratio, 
            initial_guess, 
            method='SLSQP', 
            bounds=bounds, 
            constraints=constraints
        )
        
        opt_return, opt_vol = self.portfolio_performance(result.x)
        return {
            "weights": np.round(result.x, 4).tolist(),
            "return": opt_return,
            "volatility": opt_vol,
            "sharpe": (opt_return - self.risk_free_rate) / opt_vol if opt_vol > 0 else 0
        }

    def generate_efficient_frontier(self, points: int = 50, bounds: tuple = None, initial_guess: np.ndarray = None) -> list:
        """
        Generates coordinates to plot the Efficient Frontier curve, respecting locked assets.
        """
        if initial_guess is None:
            initial_guess = np.array(self.num_assets * [1. / self.num_assets])
        if bounds is None:
            bounds = tuple((0.0, 1.0) for _ in range(self.num_assets))
            
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        
        min_var_result = sco.minimize(self.minimize_volatility, initial_guess, method='SLSQP', bounds=bounds, constraints=constraints)
        min_ret, _ = self.portfolio_performance(min_var_result.x)
        
        max_ret_result = sco.minimize(lambda x: -self.portfolio_performance(x)[0], initial_guess, method='SLSQP', bounds=bounds, constraints=constraints)
        max_ret, _ = self.portfolio_performance(max_ret_result.x)
        
        if max_ret <= min_ret:
            return [{"volatility": min_var_result.fun, "return": min_ret}]
            
        target_returns = np.linspace(min_ret, max_ret, points)
        frontier_vols = []
        
        for tr in target_returns:
            loop_constraints = (
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                {'type': 'eq', 'fun': lambda x: self.portfolio_performance(x)[0] - tr}
            )
            res = sco.minimize(self.minimize_volatility, initial_guess, method='SLSQP', bounds=bounds, constraints=loop_constraints)
            frontier_vols.append(res.fun)
            
        return [{"volatility": v, "return": r} for v, r in zip(frontier_vols, target_returns)]

    def evaluate_current_portfolio(self, current_weights: dict) -> dict:
        """
        Evaluates the performance of the user's current allocation.
        """
        weights_array = np.array([current_weights.get(sym, 0.0) for sym in self.symbols])
        if np.sum(weights_array) > 0:
            weights_array = weights_array / np.sum(weights_array)
            
        p_ret, p_vol = self.portfolio_performance(weights_array)
        
        return {
            "weights": np.round(weights_array, 4).tolist(),
            "return": p_ret,
            "volatility": p_vol,
            "sharpe": (p_ret - self.risk_free_rate) / p_vol if p_vol > 0 else 0
        }