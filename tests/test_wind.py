"""Tests for WindMod — pluggable wind models."""

import numpy as np

from src.WindMod import BrownianWind, ConstantWind, MeanRevertingWind


class TestConstantWind:
    def test_constant_wind_never_changes(self):
        model = ConstantWind(tws=10.0, twd=0.0)
        rng = np.random.default_rng(42)
        for _ in range(100):
            tws, twd = model.update(1.0, rng)
        assert tws == 10.0
        assert twd == 0.0

    def test_state_serialisable(self):
        model = ConstantWind(tws=10.0)
        s = model.state()
        assert s["tws"] == 10.0
        assert s["model"] == "ConstantWind"


class TestBrownianWind:
    def test_direction_drifts(self):
        model = BrownianWind(tws=10.0, dir_sigma=5.0)
        rng = np.random.default_rng(42)
        for _ in range(600):
            tws, twd = model.update(1.0, rng)
        assert twd != 0.0, "Direction should have drifted"
        assert tws == 10.0, "Speed should stay constant"

    def test_zero_sigma_no_drift(self):
        model = BrownianWind(tws=10.0, dir_sigma=0.0)
        rng = np.random.default_rng(42)
        for _ in range(100):
            tws, twd = model.update(1.0, rng)
        assert twd == 0.0

    def test_reset(self):
        model = BrownianWind(tws=10.0, dir_sigma=5.0)
        rng = np.random.default_rng(42)
        model.update(1.0, rng)
        model.reset(tws=12.0, twd=0.0)
        assert model.tws == 12.0
        assert model.twd == 0.0


class TestMeanRevertingWind:
    def test_direction_mean_reverts(self):
        """Direction should stay near zero with strong reversion."""
        model = MeanRevertingWind(tws=10.0, dir_sigma=2.0, dir_reversion=1.0)
        rng = np.random.default_rng(42)
        dirs = []
        for _ in range(6000):
            _, twd = model.update(1.0, rng)
            dirs.append(twd)
        # With strong reversion, mean should be near 0
        assert abs(np.mean(dirs)) < 5.0

    def test_speed_varies_when_enabled(self):
        model = MeanRevertingWind(tws=10.0, tws_sigma=1.0, tws_reversion=0.1)
        rng = np.random.default_rng(42)
        speeds = []
        for _ in range(600):
            tws, _ = model.update(1.0, rng)
            speeds.append(tws)
        assert min(speeds) != max(speeds), "TWS should vary"
        # Should stay near 10 kts on average
        assert 8.0 < np.mean(speeds) < 12.0

    def test_speed_constant_when_disabled(self):
        model = MeanRevertingWind(tws=10.0, tws_sigma=0.0)
        rng = np.random.default_rng(42)
        for _ in range(100):
            tws, _ = model.update(1.0, rng)
        assert tws == 10.0
