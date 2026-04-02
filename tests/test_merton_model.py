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
import pytest
from merton_model import MJDSimulator, TRADING_DAYS_PER_YEAR



# ── Fixtures ────────────────────────────────────────
@pytest.fixture
def base_params():
    return dict(
        capital=100_000.0,
        mu=0.08,
        sigma=0.20,
        years=1,
        simulations=5_000,
        lam=0.0,
        m=0.0,
        nu=0.0,
    )


@pytest.fixture
def mjd_params():
    return dict(
        capital=100_000.0,
        mu=0.08,
        sigma=0.20,
        years=1,
        simulations=5_000,
        lam=5.0,
        m=-0.10,
        nu=0.15,
    )


@pytest.fixture
def gbm_sim(base_params):
    return MJDSimulator(**base_params)


@pytest.fixture
def mjd_sim(mjd_params):
    return MJDSimulator(**mjd_params)



# ── Input validation ────────────────────────────────

class TestInputValidation:

    def test_capital_zero_raises(self, base_params):
        base_params["capital"] = 0.0
        with pytest.raises(ValueError, match="Capital"):
            MJDSimulator(**base_params)

    def test_capital_negative_raises(self, base_params):
        base_params["capital"] = -1.0
        with pytest.raises(ValueError, match="Capital"):
            MJDSimulator(**base_params)

    def test_sigma_negative_raises(self, base_params):
        base_params["sigma"] = -0.1
        with pytest.raises(ValueError, match="[Vv]olatility|sigma"):
            MJDSimulator(**base_params)

    def test_years_negative_raises(self, base_params):
        base_params["years"] = -1
        with pytest.raises(ValueError, match="[Yy]ears"):
            MJDSimulator(**base_params)

    def test_simulations_zero_raises(self, base_params):
        base_params["simulations"] = 0
        with pytest.raises(ValueError, match="[Ss]imulation"):
            MJDSimulator(**base_params)

    def test_simulations_negative_raises(self, base_params):
        base_params["simulations"] = -10
        with pytest.raises(ValueError, match="[Ss]imulation"):
            MJDSimulator(**base_params)

    def test_lambda_negative_raises(self, base_params):
        base_params["lam"] = -1.0
        with pytest.raises(ValueError, match="[Ll]ambda|nu|lam"):
            MJDSimulator(**base_params)

    def test_nu_negative_raises(self, base_params):
        base_params["nu"] = -0.1
        with pytest.raises(ValueError, match="[Ll]ambda|nu"):
            MJDSimulator(**base_params)

    def test_valid_params_no_exception(self, base_params):
        sim = MJDSimulator(**base_params)
        assert sim.capital == base_params["capital"]

    def test_sigma_zero_is_valid(self, base_params):
        base_params["sigma"] = 0.0
        sim = MJDSimulator(**base_params)
        prices = sim.simulate()
        assert prices is not None

    def test_years_zero_is_valid(self, base_params):
        base_params["years"] = 0
        sim = MJDSimulator(**base_params)
        prices = sim.simulate()
        assert prices.shape[0] >= 1


# ── Output structure of simulate() ──────────────────

class TestSimulateOutput:

    def test_returns_ndarray(self, gbm_sim):
        prices = gbm_sim.simulate()
        assert isinstance(prices, np.ndarray)

    def test_shape_rows(self, base_params, gbm_sim):
        prices = gbm_sim.simulate()
        expected_rows = int(base_params["years"] * TRADING_DAYS_PER_YEAR) + 1
        assert prices.shape[0] == expected_rows

    def test_shape_cols(self, base_params, gbm_sim):
        prices = gbm_sim.simulate()
        assert prices.shape[1] == base_params["simulations"]

    def test_first_row_equals_capital(self, base_params, gbm_sim):
        prices = gbm_sim.simulate()
        np.testing.assert_array_equal(prices[0, :], base_params["capital"])

    def test_all_prices_positive(self, gbm_sim):
        prices = gbm_sim.simulate()
        assert np.all(prices > 0), "Non-positive prices found"

    def test_no_nan_or_inf(self, mjd_sim):
        prices = mjd_sim.simulate()
        assert not np.any(np.isnan(prices)), "NaN values found"
        assert not np.any(np.isinf(prices)), "Inf values found"

    def test_multiyear_shape(self, base_params):
        base_params["years"] = 5
        sim = MJDSimulator(**base_params)
        prices = sim.simulate()
        expected_rows = int(5 * TRADING_DAYS_PER_YEAR) + 1
        assert prices.shape[0] == expected_rows



# ── Statistical correctness ─────────────────────────

class TestStatisticalCorrectness:
    N = 50_000
    RTOL = 0.05  # 5% relative tolerance

    @pytest.fixture
    def large_gbm(self):
        return MJDSimulator(
            capital=1.0, mu=0.10, sigma=0.20,
            years=1, simulations=self.N,
            lam=0.0, m=0.0, nu=0.0,
        )

    def test_mean_log_return(self, large_gbm):
        prices = large_gbm.simulate()
        log_returns = np.log(prices[-1, :] / prices[0, :])
        expected_mean = (large_gbm.mu - large_gbm.sigma ** 2 / 2.0) * large_gbm.years
        np.testing.assert_allclose(
            log_returns.mean(), expected_mean, rtol=self.RTOL,
            err_msg="Mean log-return deviates too far from the theoretical value"
        )

    def test_std_log_return(self, large_gbm):
        prices = large_gbm.simulate()
        log_returns = np.log(prices[-1, :] / prices[0, :])
        expected_std = large_gbm.sigma * np.sqrt(large_gbm.years)
        np.testing.assert_allclose(
            log_returns.std(), expected_std, rtol=self.RTOL,
            err_msg="Std of log-return deviates too far from the theoretical value"
        )

    def test_expected_price_gbm(self, large_gbm):
        prices = large_gbm.simulate()
        expected = large_gbm.capital * np.exp(large_gbm.mu * large_gbm.years)
        np.testing.assert_allclose(
            prices[-1, :].mean(), expected, rtol=self.RTOL,
            err_msg="Mean final price deviates too far from the theoretical expected value"
        )


# ── Jump component behaviour ────────────────────────

class TestJumpComponent:

    def test_jump_increases_dispersion(self, base_params):
        np.random.seed(0)
        gbm = MJDSimulator(**base_params)
        p_gbm = gbm.simulate()

        jump_params = dict(base_params, lam=10.0, nu=0.20)
        mjd = MJDSimulator(**jump_params)
        p_mjd = mjd.simulate()

        std_gbm = np.std(np.log(p_gbm[-1] / p_gbm[0]))
        std_mjd = np.std(np.log(p_mjd[-1] / p_mjd[0]))
        assert std_mjd > std_gbm, (
            f"MJD (std={std_mjd:.4f}) should have more dispersion than GBM (std={std_gbm:.4f})"
        )

    def test_negative_jumps_reduce_median(self, base_params):
        np.random.seed(42)
        gbm = MJDSimulator(**base_params)
        p_gbm = gbm.simulate()

        crash_params = dict(base_params, lam=20.0, m=-0.30, nu=0.05)
        crash = MJDSimulator(**crash_params)
        p_crash = crash.simulate()

        median_gbm = np.median(p_gbm[-1])
        median_crash = np.median(p_crash[-1])
        assert median_crash < median_gbm, (
            "Frequent negative jumps should lower the final median price"
        )

    def test_zero_lambda_equals_gbm_structure(self, base_params):
        np.random.seed(7)
        sim = MJDSimulator(**base_params)
        prices = sim.simulate()
        log_ret = np.log(prices[-1] / prices[0])
        upper_bound = sim.sigma * np.sqrt(sim.years) * 1.20
        assert log_ret.std() < upper_bound


# ── get_scenarios() ─────────────────────────────────

class TestGetScenarios:

    def test_returns_dict_with_three_keys(self, gbm_sim):
        prices = gbm_sim.simulate()
        scenarios = gbm_sim.get_scenarios(prices)
        assert set(scenarios.keys()) == {"Worst (5%)", "Median (50%)", "Best (95%)"}

    def test_ordering_worst_median_best(self, gbm_sim):
        prices = gbm_sim.simulate()
        s = gbm_sim.get_scenarios(prices)
        assert s["Worst (5%)"] <= s["Median (50%)"] <= s["Best (95%)"], (
            "Ordering worst ≤ median ≤ best is not satisfied"
        )

    def test_all_scenarios_positive(self, gbm_sim):
        prices = gbm_sim.simulate()
        s = gbm_sim.get_scenarios(prices)
        for key, val in s.items():
            assert val > 0, f"{key} = {val} is not positive"

    def test_median_near_capital_zero_drift_sigma(self, base_params):
        """With mu=0 and very small sigma the final median ≈ initial capital."""
        base_params.update(mu=0.0, sigma=0.001, simulations=10_000)
        sim = MJDSimulator(**base_params)
        prices = sim.simulate()
        s = sim.get_scenarios(prices)
        assert abs(s["Median (50%)"] - base_params["capital"]) / base_params["capital"] < 0.01

    def test_scenarios_with_mjd(self, mjd_sim):
        """get_scenarios works correctly with active jumps."""
        prices = mjd_sim.simulate()
        s = mjd_sim.get_scenarios(prices)
        assert s["Worst (5%)"] < s["Best (95%)"]


# ── Edge cases ──────────────────────────────────────

class TestEdgeCases:

    def test_single_simulation(self, base_params):
        base_params["simulations"] = 1
        sim = MJDSimulator(**base_params)
        prices = sim.simulate()
        assert prices.shape[1] == 1
        assert prices[0, 0] == base_params["capital"]

    def test_single_year_shape(self, base_params):
        base_params["years"] = 1
        sim = MJDSimulator(**base_params)
        prices = sim.simulate()
        assert prices.shape[0] == TRADING_DAYS_PER_YEAR + 1

    def test_large_capital(self, base_params):
        base_params["capital"] = 1e12
        sim = MJDSimulator(**base_params)
        prices = sim.simulate()
        assert np.all(np.isfinite(prices))
        assert prices[0, 0] == 1e12

    def test_very_high_volatility(self, base_params):
        base_params["sigma"] = 2.0
        sim = MJDSimulator(**base_params)
        prices = sim.simulate()
        assert not np.any(np.isnan(prices))
        assert not np.any(np.isinf(prices))
        assert np.all(prices > 0)

    def test_very_high_lambda(self, base_params):
        base_params.update(lam=100.0, m=0.0, nu=0.10)
        sim = MJDSimulator(**base_params)
        prices = sim.simulate()
        assert not np.any(np.isnan(prices))
        assert np.all(prices > 0)

    def test_multiyear_monotonic_path_count(self, base_params):
        for years in [1, 2, 5]:
            base_params["years"] = years
            sim = MJDSimulator(**base_params)
            prices = sim.simulate()
            assert prices.shape[0] == int(years * TRADING_DAYS_PER_YEAR) + 1

# ── Reproducibility ─────────────────────────────────

class TestReproducibility:

    def test_same_seed_same_result(self, base_params):
        np.random.seed(123)
        sim1 = MJDSimulator(**base_params)
        prices1 = sim1.simulate()

        np.random.seed(123)
        sim2 = MJDSimulator(**base_params)
        prices2 = sim2.simulate()

        np.testing.assert_array_equal(prices1, prices2)

    def test_different_seeds_different_results(self, base_params):
        np.random.seed(1)
        prices1 = MJDSimulator(**base_params).simulate()

        np.random.seed(2)
        prices2 = MJDSimulator(**base_params).simulate()

        assert not np.array_equal(prices1, prices2)

# ── Instance attributes ─────────────────────────────

class TestInstanceAttributes:

    def test_attributes_stored_correctly(self, mjd_params):
        sim = MJDSimulator(**mjd_params)
        for attr, val in mjd_params.items():
            assert getattr(sim, attr) == val, f"Attribute '{attr}' not stored correctly"

    def test_trading_days_constant(self):
        assert TRADING_DAYS_PER_YEAR == 252
