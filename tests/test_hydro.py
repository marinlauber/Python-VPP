"""Tests for HydroMod — roughness and wave resistance."""

import numpy as np

from python_vpp.HydroMod import HydroMod
from python_vpp.SailMod import Jib, Kite, Main
from python_vpp.YachtMod import Keel, Rudder, Yacht


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
        """Zero roughness should give bare Hughes-line Cf (no allowance)."""
        yacht = _make_yacht(roughness=0.0)
        hydro = HydroMod(yacht)
        hydro.vb = 3.0
        cf = hydro._cf(hydro.l)

        # Hughes line only
        Re = 3.0 * hydro.l / hydro.nu
        cf_expected = 0.066 * (np.log10(Re) - 2.03) ** (-2)
        assert abs(cf - cf_expected) < 1e-10

    def test_roughness_adds_allowance(self):
        """150 μm roughness should add positive Cf allowance."""
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

    def test_default_roughness_is_smooth(self):
        """Default hull is smooth (no roughness allowance), as in the ORC VPP."""
        assert _make_yacht().roughness == 0.0

    def test_roughness_allowance_uses_given_length(self):
        """The roughness allowance scales with the length passed in (hull or appendage chord)."""
        yacht = _make_yacht(roughness=150e-6)
        hydro = HydroMod(yacht)
        hydro.vb = 3.0
        smooth = HydroMod(_make_yacht(roughness=0.0))
        smooth.vb = 3.0
        for L in [hydro.l, 1.0]:
            dcf = hydro._cf(L) - smooth._cf(L)
            assert abs(dcf - (105.0 * (150e-6 / L) ** (1.0 / 3.0) - 0.64) * 1e-3) < 1e-12


class TestORCAppendages:
    """ORC 2026 6.1.2 and 6.5: appendage friction, lift drag and induced drag."""

    def test_rudder_lift_ramps_from_zero(self):
        rudder = Rudder(Cu=0.48, Cl=0.22, Span=1.15)
        assert rudder._Ksff(0.0) == 0.0
        assert abs(rudder._Ksff(15.0) - 1.0) < 1e-12
        assert rudder._Ksff(30.0) == 2.0
        assert rudder._Ksff(40.0) == 2.0

    def test_appendage_friction_line(self):
        hydro = HydroMod(_make_yacht())
        hydro.vb = 2e6 * hydro.nu  # Rn = 2e6 on a 1 m chord
        assert 0.0030 < hydro._cf_app(1.0) < 0.0038

    def test_lift_increases_appendage_drag_capped(self):
        hydro = HydroMod(_make_yacht())
        hydro.vb = 3.0
        keel = hydro.yacht.appendages[0]
        q_a = 0.5 * hydro.rho * hydro.vb ** 2 * keel.area
        d0 = hydro._app_cd_area(keel, 0.0)
        d_half = hydro._app_cd_area(keel, 0.5 * q_a)
        assert abs(d_half - d0 - keel.wsa * (0.0016 * 0.5 + 0.0032 * 0.25)) < 1e-12
        assert hydro._app_cd_area(keel, 2.0 * q_a) == d_half  # CL capped at 0.5

    def test_induced_drag_heel_multiplier(self):
        hydro = HydroMod(_make_yacht())
        hydro.phi = 0.0
        assert abs(hydro._di_factor(0.1) - 1.56) < 1e-12
        assert hydro._di_factor(0.5) == 1.0  # off at large drive/side force ratios
        hydro.phi = 20.0
        assert hydro._di_factor(0.1) == 1.0

    def test_span_multiplier(self):
        hydro = HydroMod(_make_yacht())
        hydro.update(3.0, 20.0, 3.0, twa=45.0)
        assert hydro.span_mult == 1.0
        hydro.update(3.0, 20.0, 3.0, twa=45.0, tws=20 * 0.5144)
        assert 0.8 < hydro.span_mult < 1.0
