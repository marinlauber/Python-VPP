import numpy as np
import pytest
from src.YachtMod import Yacht, Keel, Rudder, ShortKeel
from src.SailMod import Main, Jib


def _minimal_yacht(**overrides):
    """Create a minimal Yacht for testing with sensible defaults."""
    defaults = dict(
        Name="TestYacht", Lwl=7.01, Vol=1.95, Bwl=1.70, Tc=0.45,
        WSA=11.5, Tmax=1.35, Amax=0.38, Mass=2000, Loa=9.90, Boa=1.98,
        Ff=0.75, Fa=0.55,
        App=[Keel(Cu=0.70, Cl=0.45, Span=0.90), Rudder(Cu=0.32, Cl=0.18, Span=0.75)],
        Sails=[Main("MN1", P=10.80, E=3.30, Roach=0.1, BAD=0.80),
               Jib("J1", I=8.50, J=2.70, LPG=2.70, HBI=0.50)],
    )
    defaults.update(overrides)
    return Yacht(**defaults)


def test_yacht_accepts_gz_parameter():
    """Yacht should accept an optional gz dict to override the global file."""
    gz = {"Heel": [0, 10, 20, 30], "GZ": [0.0, 0.12, 0.23, 0.31]}
    yacht = _minimal_yacht(GZ=gz)
    rm_10 = yacht._get_RmH(10.0)
    expected = 0.12 * 2000 * 9.81
    assert abs(rm_10 - expected) < 1.0


def test_yacht_falls_back_to_file_when_no_gz():
    """When no GZ parameter given, should still load from file (backward compat)."""
    yacht = _minimal_yacht()
    rm_10 = yacht._get_RmH(10.0)
    assert rm_10 > 0


def test_yacht_accepts_crew_weight():
    """Yacht should accept an optional crew_weight to override the empirical formula."""
    yacht = _minimal_yacht(crew_weight=240.0)
    assert yacht.cw == 240.0


def test_yacht_default_crew_weight():
    """Without crew_weight param, should use empirical formula."""
    yacht = _minimal_yacht()
    expected = 25.8 * 7.01 ** 1.4262
    assert abs(yacht.cw - expected) < 0.1


# --- ShortKeel-specific unit tests ---

def test_short_keel_jones_lift_formula():
    """ShortKeel dclda should match Jones low-AR formula: pi*AR/2."""
    sk = ShortKeel(Length=1.2, Depth=0.90, Tc_ratio=0.15)
    ar = sk.span / sk.area  # = 0.90 / (1.2 * 0.90)
    expected = np.pi * ar / 2.0
    assert abs(sk.dclda - expected) < 1e-10, f"dclda={sk.dclda}, expected={expected}"


def test_short_keel_no_appendage_residuary():
    """ShortKeel should return zero appendage residuary resistance."""
    sk = ShortKeel(Length=1.2, Depth=0.90, Tc_ratio=0.15)
    for fn in [0.0, 0.2, 0.4, 0.6]:
        assert sk._cr(fn) == 0.0, f"_cr({fn}) should be 0.0 for short_keel"


def test_short_keel_lower_lift_than_fin():
    """A ShortKeel with equivalent area should produce less lift than a fin Keel."""
    sk = ShortKeel(Length=1.2, Depth=0.90, Tc_ratio=0.15)
    # Fin keel with similar area: chord ~0.575, span 0.90 -> area ~0.5175
    # Use root/tip that give similar area to short keel
    fk = Keel(Cu=1.40, Cl=1.00, Span=0.90)  # area = 1.08, same span
    # At the same leeway, short keel should generate less lift coefficient
    leeway_rad = np.radians(5.0)
    cl_short = sk.dclda * leeway_rad
    cl_fin = fk.dclda * leeway_rad
    assert cl_short < cl_fin, (
        f"ShortKeel cl={cl_short:.4f} should be less than Keel cl={cl_fin:.4f}"
    )
