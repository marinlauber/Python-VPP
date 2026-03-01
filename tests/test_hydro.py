"""Tests for HydroMod — roughness and wave resistance."""

import numpy as np

from src.HydroMod import HydroMod
from src.SailMod import Jib, Kite, Main
from src.YachtMod import Keel, Rudder, Yacht


def _make_yacht(**kwargs):
    """Create a YD41-like yacht with optional overrides."""
    defaults = dict(
        Name="TestYacht",
        Lwl=11.90,
        Vol=6.05,
        Bwl=3.18,
        Tc=0.4,
        WSA=28.20,
        Tmax=2.30,
        Amax=1.051,
        Mass=6500,
        Ff=1.5,
        Fa=1.5,
        Boa=4.2,
        Loa=12.5,
        App=[Keel(Cu=1.00, Cl=0.78, Span=1.90), Rudder(Cu=0.48, Cl=0.22, Span=1.15)],
        Sails=[
            Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
            Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8),
            Kite("A2", area=150.0, vce=9.55),
        ],
    )
    defaults.update(kwargs)
    return Yacht(**defaults)


class TestRoughness:
    def test_roughness_increases_resistance(self):
        """Higher roughness should increase total resistance."""
        yacht_smooth = _make_yacht(roughness=0.0)
        yacht_rough = _make_yacht(roughness=300e-6)

        hydro_smooth = HydroMod(yacht_smooth)
        hydro_rough = HydroMod(yacht_rough)

        Fx_smooth, _, _ = hydro_smooth.update(3.0, 5.0, 2.0)
        Fx_rough, _, _ = hydro_rough.update(3.0, 5.0, 2.0)

        assert Fx_rough > Fx_smooth, "Rough hull should have more resistance"

    def test_zero_roughness_gives_smooth_cf(self):
        """Zero roughness should give bare ITTC 1957 Cf (no allowance)."""
        yacht = _make_yacht(roughness=0.0)
        hydro = HydroMod(yacht)
        hydro.vb = 3.0
        cf = hydro._cf(hydro.l)

        # ITTC 1957 only
        Re = 3.0 * hydro.l / hydro.nu
        cf_expected = 0.066 * (np.log10(Re) - 2.03) ** (-2)
        assert abs(cf - cf_expected) < 1e-10

    def test_default_roughness_adds_allowance(self):
        """Default 150 μm roughness should add positive Cf allowance."""
        yacht = _make_yacht(roughness=150e-6)
        hydro = HydroMod(yacht)
        hydro.vb = 3.0
        cf_rough = hydro._cf(hydro.l)

        yacht_smooth = _make_yacht(roughness=0.0)
        hydro_smooth = HydroMod(yacht_smooth)
        hydro_smooth.vb = 3.0
        cf_smooth = hydro_smooth._cf(hydro_smooth.l)

        assert cf_rough > cf_smooth


class TestWaveResistance:
    def test_no_waves_zero_resistance(self):
        """Hs=0 should add zero wave resistance."""
        yacht = _make_yacht(Hs=0.0, Ts=0.0)
        hydro = HydroMod(yacht)
        raw = hydro._added_resistance_waves(90.0)
        assert raw == 0.0

    def test_waves_add_resistance(self):
        """Hs > 0 should produce positive added resistance upwind."""
        yacht = _make_yacht(Hs=1.0, Ts=6.0)
        hydro = HydroMod(yacht)
        hydro.vb = 3.0
        raw = hydro._added_resistance_waves(45.0)
        assert raw > 0.0, "Waves should add resistance upwind"

    def test_wave_resistance_increases_with_Hs(self):
        """Larger waves should produce more resistance."""
        yacht_small = _make_yacht(Hs=0.5, Ts=6.0)
        yacht_large = _make_yacht(Hs=1.5, Ts=6.0)

        hydro_small = HydroMod(yacht_small)
        hydro_large = HydroMod(yacht_large)
        hydro_small.vb = 3.0
        hydro_large.vb = 3.0

        raw_small = hydro_small._added_resistance_waves(45.0)
        raw_large = hydro_large._added_resistance_waves(45.0)

        assert raw_large > raw_small

    def test_wave_resistance_higher_upwind(self):
        """Upwind wave resistance should exceed downwind."""
        yacht = _make_yacht(Hs=1.0, Ts=6.0)
        hydro = HydroMod(yacht)
        hydro.vb = 3.0

        raw_upwind = hydro._added_resistance_waves(30.0)
        raw_downwind = hydro._added_resistance_waves(150.0)

        assert raw_upwind > raw_downwind

    def test_flat_water_unchanged(self):
        """VPP output with Hs=0 should match no-wave behaviour."""
        yacht = _make_yacht(Hs=0.0, Ts=0.0)
        hydro = HydroMod(yacht)

        Fx_flat, Fy_flat, Mx_flat = hydro.update(3.0, 5.0, 2.0, twa=45.0)
        Fx_no_twa, Fy_no_twa, Mx_no_twa = hydro.update(3.0, 5.0, 2.0, twa=0.0)

        # With no waves, twa shouldn't matter for resistance
        assert abs(Fx_flat - Fx_no_twa) < 1e-6
