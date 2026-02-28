import numpy as np
import pytest
from src.YachtMod import Yacht, Keel, Rudder
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
