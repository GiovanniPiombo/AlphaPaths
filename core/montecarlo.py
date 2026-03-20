import numpy as np

TRADING_DAYS_PER_YEAR = 252

class MonteCarloSimulator:
    """
    Executes Monte Carlo simulations for financial portfolios using Geometric Brownian Motion (GBM).

    This class generates thousands of possible future price paths based on annualized 
    drift ($\mu$) and volatility ($\sigma$). It utilizes highly optimized, vectorized 
    NumPy operations to compute the discrete-time GBM solution:
    $$S_{t+\Delta t} = S_t \exp\left(\left(\mu - \frac{\sigma^2}{2}\right)\Delta t + \sigma \sqrt{\Delta t} Z\right)$$
    where $Z$ is a standard normal random variable.

    Attributes:
        capital (float): The initial investment amount (must be > 0).
        mu (float): Annualized expected return (drift).
        sigma (float): Annualized portfolio volatility (standard deviation).
        years (int): The time horizon for the simulation in years.
        simulations (int): The number of independent price paths to generate.
    """

    def __init__(self, capital: float, mu: float, sigma: float, years: int, simulations: int = 10000):
        """
        Initializes the simulator and validates the input parameters.

        Args:
            capital (float): The starting portfolio value.
            mu (float): The annualized expected return
            sigma (float): The annualized volatility
            years (int): The number of years to project forward.
            simulations (int, optional): The number of paths to generate. Defaults to 10000.

        Raises:
            ValueError: If capital <= 0, sigma < 0, years < 0, or simulations <= 0.
        """
        if capital <= 0:
            raise ValueError("Capital must be strictly positive.")
        if sigma < 0:
            raise ValueError("Volatility (sigma) cannot be negative.")
        if years < 0:
            raise ValueError("Years cannot be negative.")
        if simulations <= 0:
            raise ValueError("Number of simulations must be at least 1.")
        self.capital = capital
        self.mu = mu
        self.sigma = sigma
        self.years = years
        self.simulations = simulations

    def simulate(self) -> np.ndarray: 
        """
        Executes the vectorized Monte Carlo simulation.

        Computes the daily step multiplier matrix using the continuous compounding 
        formula and calculates the cumulative product to generate complete price paths. 
        It prepends the initial capital at Day 0 to ensure all paths originate from 
        the exact starting value.

        Returns:
            np.ndarray: A 2D array of shape `(years * 252 + 1, simulations)` containing 
                the simulated portfolio values. Each column represents an independent 
                simulation path, and each row represents a distinct trading day.
        """
        total_steps = int(self.years * TRADING_DAYS_PER_YEAR)
        dt = 1.0 / TRADING_DAYS_PER_YEAR  
        drift = (self.mu - (self.sigma ** 2) / 2) * dt 
        epsilon = np.random.standard_normal(size=(total_steps, self.simulations)) 
        shock = self.sigma * np.sqrt(dt) * epsilon 
        daily_multiplier = np.exp(drift + shock)
        cumulative_multiplier = np.cumprod(daily_multiplier, axis=0)
        day_zero_multiplier = np.ones((1, self.simulations))
        full_multiplier = np.vstack([day_zero_multiplier, cumulative_multiplier])
        simulated_prices = self.capital * full_multiplier
        return simulated_prices

    def get_scenarios(self, simulated_prices: np.ndarray) -> dict:
        """
        Extracts key probabilistic outcomes from the simulated price paths.

        Evaluates the final row of the simulation matrix (the last day of the 
        time horizon) and calculates the exact portfolio values corresponding 
        to the 5th, 50th, and 95th percentiles.

        Args:
            simulated_prices (np.ndarray): The 2D array of price paths generated 
                by the `simulate` method.

        Returns:
            dict: A dictionary mapping scenario names ("Worst (5%)", "Median (50%)", 
                "Best (95%)") to their corresponding final portfolio values.
        """
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