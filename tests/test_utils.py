from types import SimpleNamespace

import numpy as np

from src.SailMod import Jib, Kite, Main
from src.UtilsMod import KNOTS_TO_MPS, _get_cross, csv_write
from src.VPPMod import VPP
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
            Kite("A5", area=110.0, vce=9.0),
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


def _fake_vpp():
    """2 TWS x 3 TWA x 2 sails; the store holds boat speed in knots, TWS in m/s."""
    store = np.zeros((2, 3, 2, 5))
    store[:, :, 0, 0] = [[5.0, 6.0, 0.0], [7.0, 8.0, 0.0]]  # jib, not set downwind
    store[:, :, 1, 0] = [[0.0, 5.5, 6.5], [0.0, 8.5, 9.5]]  # kite
    return SimpleNamespace(
        tws_range=np.array([6.0, 10.0]) * KNOTS_TO_MPS,
        twa_range=np.array([40.0, 90.0, 150.0]),
        store=store,
    )


def _read_csv(path):
    rows = [line.split(";") for line in path.read_text().splitlines()]
    return rows[0], {float(r[0]): [float(v) for v in r[1:]] for r in rows[1:]}


def test_csv_write_default_grid(tmp_path):
    fname = tmp_path / "polar.csv"
    csv_write(_fake_vpp(), fname=fname)
    header, rows = _read_csv(fname)
    assert header == ["TWA\\TWS", "6", "10"]
    # best sail at each point, in knots (no second unit conversion)
    assert rows == {40.0: [5.0, 7.0], 90.0: [6.0, 8.5], 150.0: [6.5, 9.5]}


def test_csv_write_interpolates_custom_grid(tmp_path):
    fname = tmp_path / "polar.csv"
    csv_write(_fake_vpp(), tws_range=[6.0, 8.0, 12.0], twa_range=[40.0, 65.0], fname=fname)
    header, rows = _read_csv(fname)
    assert header == ["TWA\\TWS", "6", "8", "12"]
    assert rows[40.0] == [5.0, 6.0, 0.0]  # 12 kn is outside the analysis: 0
    assert np.allclose(rows[65.0], [5.5, 6.625, 0.0], atol=0.006)  # halfway 40-90 deg


def test_vpp_write_csv(tmp_path):
    vpp = VPP(Yacht=return_YD41_particulars())
    vpp.set_analysis(tws_range=np.array([8.0]), twa_range=np.array([45.0, 90.0]))
    vpp.run()
    fname = tmp_path / "polar.csv"
    vpp.write_csv(fname)
    header, rows = _read_csv(fname)
    assert header == ["TWA\\TWS", "8"]
    best = vpp.store[0, :, :, 0].max(axis=1)
    assert np.allclose([rows[45.0][0], rows[90.0][0]], best, atol=0.006)
    assert all(v > 0 for r in rows.values() for v in r)
