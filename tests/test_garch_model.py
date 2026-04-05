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
from unittest.mock import patch
import sys
import types

_core = types.ModuleType("core")
_logger_mod = types.ModuleType("core.logger")

class _FakeLogger:
    def error(self, *a, **kw): pass
    def warning(self, *a, **kw): pass
    def info(self, *a, **kw): pass

_logger_mod.app_logger = _FakeLogger()
sys.modules.setdefault("core", _core)
sys.modules.setdefault("core.logger", _logger_mod)

from garch_model import GARCHSimulator, TRADING_DAYS_PER_YEAR


# ── Helpers ────────────────────────────────────────────────────────────────────────────────────
OMEGA   = 1e-6
ALPHA   = 0.05
BETA    = 0.90
INIT_V  = 0.0001   # ~ 1 % daily vol squared
BASE_KW = dict(omega=OMEGA, alpha=ALPHA, beta=BETA, initial_variance=INIT_V)


def make_sim(capital=10_000, mu=0.08, years=1, simulations=500, **kw) -> GARCHSimulator:
    """Convenience factory with sensible defaults."""
    params = {**BASE_KW, **kw}
    return GARCHSimulator(capital=capital, mu=mu, years=years,
                          simulations=simulations, **params)


# ──── 1. Constructor validation ───────────────────────────────────────────────────────────────
class TestConstructorValidation:
    def test_negative_capital_raises(self):
        with pytest.raises(ValueError, match="strictly positive"):
            GARCHSimulator(capital=-1, mu=0.05, years=1, **BASE_KW)

    def test_zero_capital_raises(self):
        with pytest.raises(ValueError, match="strictly positive"):
            GARCHSimulator(capital=0, mu=0.05, years=1, **BASE_KW)

    def test_negative_years_raises(self):
        with pytest.raises(ValueError, match="Years cannot be negative"):
            GARCHSimulator(capital=1000, mu=0.05, years=-1, **BASE_KW)

    def test_zero_simulations_raises(self):
        with pytest.raises(ValueError, match="at least 1"):
            GARCHSimulator(capital=1000, mu=0.05, years=1, simulations=0, **BASE_KW)

    def test_negative_simulations_raises(self):
        with pytest.raises(ValueError, match="at least 1"):
            GARCHSimulator(capital=1000, mu=0.05, years=1, simulations=-5, **BASE_KW)

    def test_valid_parameters_no_exception(self):
        sim = make_sim()
        assert sim.capital == 10_000

    def test_zero_years_is_valid(self):
        """years=0 means 0 trading days; simulate() should still work."""
        sim = make_sim(years=0)
        prices = sim.simulate()
        assert prices.shape[0] == 1

    def test_non_stationary_warning_issued(self):
        """alpha + beta >= 1 should trigger a logger warning (not raise)."""
        with patch.object(_logger_mod.app_logger, "warning") as mock_warn:
            sim = GARCHSimulator(capital=1000, mu=0.05, years=1,
                                 omega=OMEGA, alpha=0.5, beta=0.6,
                                 initial_variance=INIT_V)
            mock_warn.assert_called_once()
        assert sim.alpha + sim.beta == pytest.approx(1.1)

    def test_alpha_plus_beta_exactly_one_warns_not_raises(self):
        with patch.object(_logger_mod.app_logger, "warning"):
            sim = GARCHSimulator(capital=1000, mu=0.05, years=1,
                                 omega=OMEGA, alpha=0.3, beta=0.7,
                                 initial_variance=INIT_V)
        assert sim is not None

    def test_stored_attributes(self):
        sim = make_sim(capital=5000, mu=0.10, years=3, simulations=200)
        assert sim.capital     == 5000
        assert sim.mu          == 0.10
        assert sim.years       == 3
        assert sim.simulations == 200
        assert sim.omega       == OMEGA
        assert sim.alpha       == ALPHA
        assert sim.beta        == BETA
        assert sim.initial_variance == INIT_V

# ──── 2. simulate() – output shape & types ──────────────────────────────────────────────────────────────
class TestSimulateShape:
    def test_output_is_ndarray(self):
        prices = make_sim().simulate()
        assert isinstance(prices, np.ndarray)

    def test_shape_rows(self):
        years, sims = 2, 300
        prices = make_sim(years=years, simulations=sims).simulate()
        expected_rows = int(years * TRADING_DAYS_PER_YEAR) + 1
        assert prices.shape[0] == expected_rows

    def test_shape_cols(self):
        sims = 750
        prices = make_sim(simulations=sims).simulate()
        assert prices.shape[1] == sims

    def test_shape_one_simulation(self):
        prices = make_sim(simulations=1).simulate()
        expected_rows = int(1 * TRADING_DAYS_PER_YEAR) + 1
        assert prices.shape == (expected_rows, 1)

    def test_shape_one_year(self):
        prices = make_sim(years=1, simulations=100).simulate()
        assert prices.shape[0] == TRADING_DAYS_PER_YEAR + 1


# ──── 3. simulate() – initial conditions ──────────────────────────────────────────────────────────────
class TestSimulateInitialConditions:
    def test_first_row_equals_capital(self):
        capital = 12_345.67
        prices = make_sim(capital=capital).simulate()
        np.testing.assert_array_equal(prices[0, :], capital)

    def test_first_row_constant_across_paths(self):
        prices = make_sim(capital=1000, simulations=200).simulate()
        assert np.all(prices[0, :] == prices[0, 0])

# ──── 4. simulate() – value constraints ──────────────────────────────────────────────────────────────
class TestSimulateValueConstraints:
    def test_all_prices_positive(self):
        """Exponential returns guarantee positivity."""
        prices = make_sim(simulations=1000).simulate()
        assert np.all(prices > 0)

    def test_no_nan_or_inf(self):
        prices = make_sim(simulations=1000).simulate()
        assert not np.any(np.isnan(prices))
        assert not np.any(np.isinf(prices))

    def test_zero_drift_median_near_capital(self):
        """With mu=0 and many paths, median final price ≈ initial capital."""
        np.random.seed(42)
        prices = make_sim(mu=0.0, simulations=50_000).simulate()
        final_median = np.median(prices[-1, :])
        assert abs(final_median - 10_000) / 10_000 < 0.15

    def test_positive_drift_raises_median(self):
        """Positive drift should push the median above the starting capital."""
        np.random.seed(0)
        prices = make_sim(mu=0.12, years=5, simulations=10_000).simulate()
        assert np.median(prices[-1, :]) > 10_000

    def test_negative_drift_lowers_median(self):
        """Strong negative drift should push the median below the starting capital."""
        np.random.seed(0)
        prices = make_sim(mu=-0.20, years=5, simulations=10_000).simulate()
        assert np.median(prices[-1, :]) < 10_000

# ─── 5. simulate() – reproducibility with random seeds ──────────────────────────────────────────────
class TestSimulateReproducibility:
    def test_different_seeds_give_different_results(self):
        np.random.seed(1)
        prices_a = make_sim(simulations=100).simulate()
        np.random.seed(2)
        prices_b = make_sim(simulations=100).simulate()
        assert not np.allclose(prices_a, prices_b)

    def test_same_seed_gives_identical_results(self):
        np.random.seed(99)
        prices_a = make_sim(simulations=100).simulate()
        np.random.seed(99)
        prices_b = make_sim(simulations=100).simulate()
        np.testing.assert_array_equal(prices_a, prices_b)

# ──── 6. simulate() – variance clipping ───────────────────────────────────────────────────────────────
class TestVarianceClipping:
    def test_variance_never_drops_to_zero(self):
        """
        With omega=0 / alpha=0 / beta=0, variance would collapse to 0.
        The np.clip(a_min=1e-10) floor must prevent this.
        """
        sim = GARCHSimulator(capital=1000, mu=0.0, years=1, simulations=200,
                             omega=0.0, alpha=0.0, beta=0.0,
                             initial_variance=0.0)
        prices = sim.simulate()
        assert np.all(prices > 0)
        assert not np.any(np.isnan(prices))

    def test_extreme_alpha_beta_no_explosion(self):
        """
        Non-stationary params (alpha+beta > 1) must not produce NaN / Inf
        thanks to np.clip(a_max=1.0).
        """
        with patch.object(_logger_mod.app_logger, "warning"):
            sim = GARCHSimulator(capital=1000, mu=0.0, years=1, simulations=200,
                                 omega=1e-6, alpha=0.6, beta=0.6,
                                 initial_variance=0.0001)
        prices = sim.simulate()
        assert not np.any(np.isnan(prices))
        assert not np.any(np.isinf(prices))

# ──── 7. get_scenarios() ────────────────────────────────────────────────────────────────────────────────
class TestGetScenarios:
    @pytest.fixture
    def scenarios(self):
        np.random.seed(7)
        sim = make_sim(simulations=5000)
        prices = sim.simulate()
        return sim.get_scenarios(prices)

    def test_returns_dict(self, scenarios):
        assert isinstance(scenarios, dict)

    def test_expected_keys(self, scenarios):
        assert set(scenarios.keys()) == {"Worst (5%)", "Median (50%)", "Best (95%)"}

    def test_ordering(self, scenarios):
        assert scenarios["Worst (5%)"] <= scenarios["Median (50%)"] <= scenarios["Best (95%)"]

    def test_all_values_positive(self, scenarios):
        for v in scenarios.values():
            assert v > 0

    def test_percentile_values_correct(self):
        """get_scenarios must match np.percentile on a known array."""
        sim = make_sim(simulations=1)      # shape doesn't matter; we override below
        dummy = np.arange(1, 101, dtype=float).reshape(1, 100)  # 100 "simulations"
        scenarios = sim.get_scenarios(dummy)
        assert scenarios["Worst (5%)"]   == pytest.approx(np.percentile(dummy[-1], 5))
        assert scenarios["Median (50%)"] == pytest.approx(np.percentile(dummy[-1], 50))
        assert scenarios["Best (95%)"]   == pytest.approx(np.percentile(dummy[-1], 95))

    def test_worst_below_capital_with_negative_drift(self):
        np.random.seed(0)
        sim = make_sim(mu=-0.30, years=3, simulations=10_000)
        prices = sim.simulate()
        scenarios = sim.get_scenarios(prices)
        assert scenarios["Worst (5%)"] < sim.capital

    def test_best_above_capital_with_positive_drift(self):
        np.random.seed(0)
        sim = make_sim(mu=0.20, years=3, simulations=10_000)
        prices = sim.simulate()
        scenarios = sim.get_scenarios(prices)
        assert scenarios["Best (95%)"] > sim.capital
