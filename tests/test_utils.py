import numpy as np

from src.SailMod import Jib, Kite, Main
from src.UtilsMod import _get_cross
from src.YachtMod import Keel, Rudder, Yacht


def return_YD41_particulars():

    YD41 = Yacht(
        Name="YD41",
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
            Kite("A5", area=75.0, vce=2.75),
        ],
    )
    return YD41


def _cross_store():
    """Store (ntwa=8, nsails=2, nvars=1): sail 1 is skipped (0) at the first 3 TWAs."""
    dat = np.zeros((8, 2, 1))
    dat[:, 0, 0] = [6.0, 7.0, 8.0, 8.0, 7.0, 6.0, 5.0, 4.0]
    dat[:, 1, 0] = [0.0, 0.0, 0.0, 7.5, 7.5, 7.0, 6.0, 5.0]
    return dat


def test_get_cross_pad_skips_unsolved_points():
    """Padding must not extend a sail's range over points it was not solved at."""
    lo, hi = _get_cross(_cross_store(), 1, pad=2)
    assert (lo, hi) == (3, 8)  # fastest from index 4; index 3 is solved, 1-2 are not


def test_get_cross_pad_is_symmetric():
    lo, hi = _get_cross(_cross_store(), 0, pad=2)
    assert (lo, hi) == (0, 6)  # fastest at 0-3, plus two points after


def test_get_cross_no_pad():
    assert tuple(_get_cross(_cross_store(), 1, pad=0)) == (4, 8)
