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
import pytest
import numpy as np
from gbm_model import GBMSimulator

# We use a fixture to create a baseline simulator to reuse across tests
@pytest.fixture
def default_simulator():
    return GBMSimulator(capital=1000.0, mu=0.05, sigma=0.2, years=2, simulations=100)

# ── Initialization Test ───────────────────────────────────────
def test_initialization(default_simulator):
    assert default_simulator.capital == 1000.0
    assert default_simulator.mu == 0.05
    assert default_simulator.sigma == 0.2
    assert default_simulator.years == 2
    assert default_simulator.simulations == 100

# ── Output Shape Test ─────────────────────────────────────────
def test_simulation_shape(default_simulator):
    prices = default_simulator.simulate()
    expected_days = int(2 * 252) + 1  
    assert prices.shape == (expected_days, 100)

# ── Initial Value Test (Day 0) ────────────────────────────────
def test_day_zero_capital(default_simulator):
    prices = default_simulator.simulate()
    assert np.all(prices[0, :] == 1000.0)

# ── Deterministic Behavior Test ───────────────────────────────
def test_zero_volatility():
    sim = GBMSimulator(capital=1000.0, mu=0.05, sigma=0.0, years=1, simulations=10)
    prices = sim.simulate()
    expected_final_price = 1000.0 * np.exp(0.05 * 1)
    assert np.allclose(prices[-1, :], expected_final_price)

def test_zero_drift_and_volatility():
    sim = GBMSimulator(capital=1000.0, mu=0.0, sigma=0.0, years=1, simulations=10)
    prices = sim.simulate()
    assert np.all(prices == 1000.0)

# ── Scenario Calculation Test ─────────────────────────────────
def test_get_scenarios():
    sim = GBMSimulator(capital=100.0, mu=0.05, sigma=0.2, years=1)
    mock_prices = np.zeros((10, 100))
    mock_prices[-1, :] = np.arange(1, 101) 
    scenarios = sim.get_scenarios(mock_prices)
    assert np.isclose(scenarios["Worst (5%)"], 5.95)
    assert np.isclose(scenarios["Median (50%)"], 50.5)
    assert np.isclose(scenarios["Best (95%)"], 95.05)

# ── Reproducibility Test (SEED) ───────────────────────────────
def test_reproducibility():
    sim = GBMSimulator(capital=1000.0, mu=0.05, sigma=0.2, years=1, simulations=10)

    np.random.seed(42)
    prices_run_1 = sim.simulate()
    
    np.random.seed(42)
    prices_run_2 = sim.simulate()
    
    assert np.array_equal(prices_run_1, prices_run_2)

# ── Invalid Input Tests (Negative Edge Cases) ─────────────────

def test_negative_capital():
    with pytest.raises(ValueError):
        GBMSimulator(capital=-1000.0, mu=0.05, sigma=0.2, years=1)

def test_negative_sigma():
    with pytest.raises(ValueError):
        GBMSimulator(capital=1000.0, mu=0.05, sigma=-0.2, years=1)

def test_negative_years():
    with pytest.raises(ValueError):
        GBMSimulator(capital=1000.0, mu=0.05, sigma=0.2, years=-1)

# ── Boundary / Limit Parameters tests ─────────────────────────

def test_zero_simulations():
    with pytest.raises(ValueError):
        GBMSimulator(capital=1000.0, mu=0.05, sigma=0.2, years=1, simulations=0)

def test_one_simulation():
    sim = GBMSimulator(capital=1000.0, mu=0.05, sigma=0.2, years=1, simulations=1)
    prices = sim.simulate()
    assert prices.shape == (253, 1)

def test_zero_years():
    sim = GBMSimulator(capital=1000.0, mu=0.05, sigma=0.2, years=0, simulations=10)
    prices = sim.simulate()
    
    assert prices.shape == (1, 10)
    assert np.all(prices == 1000.0)

# ── Extreme Values Test ───────────────────────────────────────

def test_extreme_volatility():
    sim = GBMSimulator(capital=1000.0, mu=0.05, sigma=0.8, years=10, simulations=100)
    prices = sim.simulate()
    
    assert not np.isnan(prices).any(), "Simulation contains NaN values."
    assert not np.isinf(prices).any(), "Simulation contains Infinite values."

# ── Statistical Validation Test ───────────────────────────────

def test_statistical_expected_value():
    # The theoretical expected value of Geometric Brownian Motion is E[S_T] = S_0 * exp(mu * T)
    # We use a large number of simulations to satisfy the Law of Large Numbers
    sim = GBMSimulator(capital=1000.0, mu=0.05, sigma=0.2, years=1, simulations=50000)
    
    np.random.seed(42)
    prices = sim.simulate()
    final_prices = prices[-1, :]
    
    theoretical_mean = 1000.0 * np.exp(0.05 * 1)
    empirical_mean = np.mean(final_prices)
    
    assert np.isclose(empirical_mean, theoretical_mean, rtol=0.02)

# ── Percentile Ordering Test ──────────────────────────────────

def test_percentile_ordering(default_simulator):
    prices = default_simulator.simulate()
    scenarios = default_simulator.get_scenarios(prices)
    
    worst = scenarios["Worst (5%)"]
    median = scenarios["Median (50%)"]
    best = scenarios["Best (95%)"]
    
    assert worst <= median
    assert median <= best