import numpy as np

TRADING_DAYS_PER_YEAR = 252

class MonteCarloSimulator:
    """
    Monte Carlo simulator for financial portfolios based on Geometric Brownian Motion[cite: 8, 36, 37].
    Calculates price evolution and probabilistic scenarios (Worst, Median, Best).
    """

    def __init__(self, capital: float, mu: float, sigma: float, years: int, simulations: int = 10000):
        self.capital = capital
        self.mu = mu
        self.sigma = sigma
        self.years = years
        self.simulations = simulations

    def simulate(self) -> np.ndarray: 
        """
        Executes the vectorized Monte Carlo simulation with Numpy.
        Returns a matrix with simulated prices (days x simulations), starting from Day 0.
        """
        # 1) Calculate total steps and delta_t (1 trading day as a fraction of a year)
        total_steps = int(self.years * TRADING_DAYS_PER_YEAR)
        dt = 1.0 / TRADING_DAYS_PER_YEAR  
        
        # 2) Drift calculation
        drift = (self.mu - (self.sigma ** 2) / 2) * dt 
        
        # 3) Random number matrix with standard normal distribution
        epsilon = np.random.standard_normal(size=(total_steps, self.simulations)) 
        
        # 4) Calculate exponent for each day
        shock = self.sigma * np.sqrt(dt) * epsilon 
        
        # 5) Transform exponents into daily multipliers
        daily_multiplier = np.exp(drift + shock)
        
        # 6) Cumulative product for the future days
        cumulative_multiplier = np.cumprod(daily_multiplier, axis=0)
        
        # 7) Add Day 0 (initial capital) as the first row of the multiplier matrix
        
        # Create a row of 1s representing the initial multiplier (Day 0)
        day_zero_multiplier = np.ones((1, self.simulations))
        
        # Stack Day 0 on top of the future cumulative multipliers
        full_multiplier = np.vstack([day_zero_multiplier, cumulative_multiplier])
        
        # Calculate final prices: capital * multipliers
        simulated_prices = self.capital * full_multiplier
        return simulated_prices

    def get_scenarios(self, simulated_prices: np.ndarray) -> dict:
        """
        Extracts the final values for the Best (95th percentile), 
        Median (50th percentile) and Worst (5th percentile) cases.
        """
        # Takes only the last row (end of simulation)
        final_prices = simulated_prices[-1, :] 
        
        return {
            "Worst (5%)": np.percentile(final_prices, 5), 
            "Median (50%)": np.percentile(final_prices, 50), 
            "Best (95%)": np.percentile(final_prices, 95)    
        }


if __name__ == "__main__":
    # Test parameters
    capital = 1000000  
    mu = 0.07            
    sigma = 0.3          
    years = 5            

    # Initialization and execution
    simulator = MonteCarloSimulator(capital, mu, sigma, years)
    simulated_prices = simulator.simulate()
    scenarios = simulator.get_scenarios(simulated_prices)
    
    print(f"--- {years}-YEAR SIMULATION RESULTS ---")
    for scenario, value in scenarios.items():
        print(f"{scenario} Scenario: € {value:,.2f}")