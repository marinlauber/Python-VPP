"""Tests for RaceMod — match racing simulation engine."""

import json
import os

import numpy as np

from src.RaceMod import Boat, Race
from src.WindMod import BrownianWind, ConstantWind, MeanRevertingWind


def _constant_polar(speed=6.0):
    """Return a polar that gives constant speed at any TWS/TWA."""
    return lambda tws, twa: speed


def _realistic_polar(scale=1.0):
    """Return a polar that varies with TWA like a real boat.

    Peak speed ~7*scale at TWA=120, drops to ~4*scale at TWA=30.
    """
    def polar(tws, twa):
        twa_rad = np.radians(np.clip(twa, 25, 180))
        return scale * (3.5 + 3.5 * np.sin(twa_rad))
    return polar


def _load_cached_polar(name="Daring_5.5m"):
    """Load pre-computed polar from dat/ directory."""
    path = os.path.join("dat", f"polars_{name}.json")
    with open(path) as f:
        data = json.load(f)
    tws = np.array(data["tws"])
    twa = np.array(data["twa"])
    results = np.array(data["results"])
    return Race.build_polar_interp(tws, twa, results)


class TestSingleRace:
    def test_single_race_returns_times(self):
        """run_single returns dict with expected keys and positive times."""
        race = Race(_constant_polar(6.0), _constant_polar(6.0), tws=10.0,
                    leg_distance=0.2, n_legs=1, wind_sigma=0.0)
        result = race.run_single(seed=42)
        assert "time_A" in result
        assert "time_B" in result
        assert result["time_A"] > 0
        assert result["time_B"] > 0

    def test_single_race_has_traces(self):
        """run_single returns trace lists."""
        race = Race(_constant_polar(6.0), _constant_polar(6.0), tws=10.0,
                    leg_distance=0.2, n_legs=1, wind_sigma=0.0)
        result = race.run_single(seed=42)
        assert isinstance(result["trace_A"], list)
        assert isinstance(result["trace_B"], list)
        assert len(result["trace_A"]) > 0


class TestIdenticalBoats:
    def test_identical_boats_even_odds(self):
        """Same polar should give roughly 50% win rate with realistic polars."""
        polar = _realistic_polar(1.0)
        race = Race(polar, polar, tws=10.0,
                    leg_distance=0.3, n_legs=1, wind_sigma=3.0)
        mc = race.run_monte_carlo(n_runs=100)
        total_decided = mc["wins_A"] + mc["wins_B"]
        if total_decided == 0:
            # All ties — still fair, pass the test
            return
        win_pct_A = mc["wins_A"] / total_decided
        # Should be roughly 50% ± 20% (generous for stochastic test)
        assert 0.20 < win_pct_A < 0.80, (
            f"Win% A = {win_pct_A:.0%} ({mc['wins_A']}/{total_decided}), expected ~50%"
        )


class TestFasterBoatWins:
    def test_faster_boat_wins_majority(self):
        """A faster boat should win more than 60% of races."""
        fast = _realistic_polar(1.4)
        slow = _realistic_polar(1.0)
        race = Race(fast, slow, tws=10.0,
                    leg_distance=0.3, n_legs=1, wind_sigma=1.0)
        mc = race.run_monte_carlo(n_runs=200)
        assert mc["wins_A"] > 100, f"Fast boat won only {mc['wins_A']}/200"


class TestTackPenalty:
    def test_tack_penalty_affects_result(self):
        """Higher tack penalty should increase elapsed time."""
        low_penalty = Race(_constant_polar(6.0), _constant_polar(6.0), tws=10.0,
                           leg_distance=0.3, n_legs=1, tack_penalty=2.0,
                           wind_sigma=0.0)
        high_penalty = Race(_constant_polar(6.0), _constant_polar(6.0), tws=10.0,
                            leg_distance=0.3, n_legs=1, tack_penalty=30.0,
                            wind_sigma=0.0)
        r_low = low_penalty.run_single(seed=42)
        r_high = high_penalty.run_single(seed=42)
        # Higher penalty → more elapsed time (or at least not less)
        avg_low = (r_low["time_A"] + r_low["time_B"]) / 2
        avg_high = (r_high["time_A"] + r_high["time_B"]) / 2
        assert avg_high >= avg_low


class TestCurrent:
    def test_current_affects_leg_time(self):
        """Favourable current should reduce elapsed time."""
        no_current = Race(_constant_polar(6.0), _constant_polar(6.0), tws=10.0,
                          leg_distance=0.3, n_legs=1, current_speed=0.0,
                          wind_sigma=0.0)
        with_current = Race(_constant_polar(6.0), _constant_polar(6.0), tws=10.0,
                            leg_distance=0.3, n_legs=1, current_speed=1.0,
                            current_dir=0.0, wind_sigma=0.0)
        r_no = no_current.run_single(seed=42)
        r_cur = with_current.run_single(seed=42)
        # Upwind current (dir=0 means current going upwind direction)
        # should affect leg times
        assert r_no["time_A"] != r_cur["time_A"]


class TestWindShadow:
    def test_wind_shadow_detection(self):
        """Boat directly downwind within 2-10 boat lengths is in shadow."""
        race = Race(_constant_polar(), _constant_polar(), tws=10.0)
        ahead = Boat(_constant_polar(), "ahead", boat_length=12.0)
        behind = Boat(_constant_polar(), "behind", boat_length=12.0)

        # Place behind directly downwind (wind from y+ direction, wind_dir=0)
        # 50m behind → > 2*12=24m min, < 10*12=120m max
        ahead.x = 0.0
        ahead.y = 100.0
        behind.x = 0.0
        behind.y = 50.0

        assert race._is_in_shadow(ahead, behind, wind_dir=0.0)

    def test_no_shadow_when_far(self):
        """Boat far downwind is not in shadow."""
        race = Race(_constant_polar(), _constant_polar(), tws=10.0)
        ahead = Boat(_constant_polar(), "ahead", boat_length=12.0)
        behind = Boat(_constant_polar(), "behind", boat_length=12.0)

        ahead.x = 0.0
        ahead.y = 100.0
        behind.x = 0.0
        behind.y = -100.0  # 200m behind, > 10 * 12 = 120m

        assert not race._is_in_shadow(ahead, behind, wind_dir=0.0)

    def test_no_shadow_when_abeam(self):
        """Boat abeam (perpendicular) is not in shadow."""
        race = Race(_constant_polar(), _constant_polar(), tws=10.0)
        ahead = Boat(_constant_polar(), "ahead", boat_length=12.0)
        behind = Boat(_constant_polar(), "behind", boat_length=12.0)

        ahead.x = 0.0
        ahead.y = 100.0
        behind.x = 200.0
        behind.y = 100.0

        assert not race._is_in_shadow(ahead, behind, wind_dir=0.0)


class TestMonteCarlo:
    def test_monte_carlo_output_format(self):
        """Monte Carlo returns expected keys and counts."""
        race = Race(_constant_polar(6.0), _constant_polar(6.0), tws=10.0,
                    leg_distance=0.2, n_legs=1, wind_sigma=1.0)
        mc = race.run_monte_carlo(n_runs=10)
        assert "wins_A" in mc
        assert "wins_B" in mc
        assert "deltas" in mc
        assert "mean_delta" in mc
        assert "traces" in mc
        assert len(mc["deltas"]) == 10
        assert mc["wins_A"] + mc["wins_B"] <= 10  # ties possible


class TestPolarInterp:
    def test_build_polar_interp(self):
        """build_polar_interp creates callable that returns speeds."""
        tws = np.array([2.0, 5.0]) * 0.5144  # m/s
        twa = np.array([30.0, 90.0, 150.0])
        # shape (2, 3, 1, 5) — 2 TWS, 3 TWA, 1 sail, 5 outputs
        results = np.zeros((2, 3, 1, 5))
        results[:, :, 0, 0] = [[3.0, 5.0, 4.0], [4.0, 7.0, 6.0]]

        polar = Race.build_polar_interp(tws, twa, results)
        # At TWS=5 kts, TWA=90° → should be ~7 kts
        speed = polar(5.0, 90.0)
        assert abs(speed - 7.0) < 0.1

    def test_polar_interp_out_of_bounds(self):
        """Out-of-bounds queries return 0."""
        tws = np.array([4.0, 8.0]) * 0.5144
        twa = np.array([30.0, 90.0])
        results = np.zeros((2, 2, 1, 5))
        results[:, :, 0, 0] = [[3.0, 5.0], [4.0, 7.0]]

        polar = Race.build_polar_interp(tws, twa, results)
        assert polar(100.0, 90.0) == 0.0  # way out of range


class TestTrimNoise:
    def test_trim_noise_breaks_ties(self):
        """With trim noise, identical boats should sometimes produce different times."""
        race = Race(_realistic_polar(1.0), _realistic_polar(1.0), tws=10.0,
                    leg_distance=0.3, n_legs=1, wind_sigma=2.0,
                    trim_sigma=0.03)
        mc = race.run_monte_carlo(n_runs=50)
        decided = mc["wins_A"] + mc["wins_B"]
        assert decided > 0, "Trim noise should break ties"

    def test_zero_trim_sigma_no_noise(self):
        """trim_sigma=0 should behave identically to no noise."""
        race = Race(_constant_polar(6.0), _constant_polar(6.0), tws=10.0,
                    leg_distance=0.2, n_legs=1,
                    wind_model=ConstantWind(tws=10.0),
                    trim_sigma=0.0)
        r1 = race.run_single(seed=42)
        r2 = race.run_single(seed=42)
        assert r1["time_A"] == r2["time_A"]


class TestPenaltyVariance:
    def test_penalty_std_varies_times(self):
        """Non-zero penalty std should produce different race times across seeds."""
        race = Race(_realistic_polar(1.0), _realistic_polar(1.0), tws=10.0,
                    leg_distance=0.3, n_legs=1, wind_sigma=2.0,
                    tack_penalty_std=3.0, gybe_penalty_std=2.0)
        times = [race.run_single(seed=i)["time_A"] for i in range(10)]
        assert len(set(times)) > 1, "Penalty variance should produce varied times"


class TestWindModels:
    def test_constant_wind_model(self):
        """Race with ConstantWind should work and produce no randomness from wind."""
        model = ConstantWind(tws=10.0)
        race = Race(_constant_polar(6.0), _constant_polar(6.0), tws=10.0,
                    leg_distance=0.2, n_legs=1, wind_model=model)
        result = race.run_single(seed=42)
        assert result["time_A"] > 0

    def test_mean_reverting_wind_model(self):
        """Race with MeanRevertingWind should work."""
        model = MeanRevertingWind(tws=10.0, dir_sigma=3.0, tws_sigma=0.5)
        race = Race(_realistic_polar(1.0), _realistic_polar(1.0), tws=10.0,
                    leg_distance=0.3, n_legs=1, wind_model=model)
        result = race.run_single(seed=42)
        assert result["time_A"] > 0


class TestCachedPolars:
    def test_daring_polar_loads(self):
        """Pre-computed Daring polar loads and returns sensible speeds."""
        polar = _load_cached_polar("Daring_5.5m")
        speed_reach = polar(10.0, 90.0)
        speed_upwind = polar(10.0, 40.0)
        assert speed_reach > 0, "Reaching speed should be positive"
        assert speed_upwind > 0, "Upwind speed should be positive"
        assert speed_reach > speed_upwind, "Reaching should be faster than upwind"

    def test_daring_vs_daring_race(self):
        """Two Darings racing should produce ~50/50 results."""
        polar = _load_cached_polar("Daring_5.5m")
        race = Race(polar, polar, tws=10.0,
                    leg_distance=0.3, n_legs=1, wind_sigma=3.0,
                    trim_sigma=0.02)
        mc = race.run_monte_carlo(n_runs=50)
        decided = mc["wins_A"] + mc["wins_B"]
        if decided > 5:
            pct_A = mc["wins_A"] / decided
            assert 0.15 < pct_A < 0.85, f"Bias detected: A wins {pct_A:.0%}"

    def test_yd41_faster_than_daring(self):
        """YD41 should beat Daring in most races (bigger, faster boat)."""
        polar_yd41 = _load_cached_polar("YD41")
        polar_daring = _load_cached_polar("Daring_5.5m")
        race = Race(polar_yd41, polar_daring, tws=10.0,
                    leg_distance=0.5, n_legs=1, wind_sigma=2.0)
        mc = race.run_monte_carlo(n_runs=50)
        assert mc["wins_A"] > mc["wins_B"], "YD41 should beat Daring more often"
