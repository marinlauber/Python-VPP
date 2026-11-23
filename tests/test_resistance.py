import numpy.testing as np_testing

from python_vpp.HydroMod import HydroMod
from python_vpp.YachtMod import Keel, Rudder, Yacht


def generate_YD41():
    """
    Return particulars of the YD-41 Yacht from Larsson.
    """
    YD41_Keel = Keel(Cu=1.00, Cl=0.78, Span=1.90)
    YD41_Rudder = Rudder(Cu=0.48, Cl=0.22, Span=1.15)

    YD41 = HydroMod(
        Yacht(
            Name="YD41",
            Loa=12.5,
            Boa=3.5,
            Ff=2.5,
            Fa=2.0,
            Lwl=11.90,
            Vol=6.05,
            Bwl=3.18,
            Tc=0.4,
            WSA=28.20,
            Tmax=2.30,
            Amax=1.051,
            Mass=6500,
            App=[YD41_Keel, YD41_Rudder],
        )
    )
    return YD41



def test_Rr_interpolation():
    YD41 = generate_YD41()
    np_testing.assert_approx_equal(YD41._interp_Rr((0.125, 3.0, 2.5)), 0.0487, 4)
    np_testing.assert_approx_equal(YD41._interp_Rr((0.125, 3.0, 9.0)), 0.0487, 4)
    np_testing.assert_approx_equal(YD41._interp_Rr((0.125, 9.0, 2.5)), 0.0393, 4)
    np_testing.assert_approx_equal(YD41._interp_Rr((0.125, 9.0, 9.0)), 0.0613, 4)
    np_testing.assert_approx_equal(YD41._interp_Rr((0.700, 3.0, 2.5)), 357.062, 4)
    np_testing.assert_approx_equal(YD41._interp_Rr((0.700, 3.0, 9.0)), 357.062, 4)
    np_testing.assert_approx_equal(YD41._interp_Rr((0.700, 9.0, 2.5)), 38.0526, 4)
    np_testing.assert_approx_equal(YD41._interp_Rr((0.700, 9.0, 9.0)), 42.2353, 4)


def test_Rr_axes_lvr_btr():
    """ORC table is RRmult(lvr_i, btr_j): rows are LVR [3, 9], columns BTR [2.5, 9] (issue #70)."""
    YD41 = generate_YD41()
    fn_grid, lvr_grid, btr_grid = YD41._interp_Rr.grid
    np_testing.assert_approx_equal(lvr_grid[0], 3.0)
    np_testing.assert_approx_equal(btr_grid[0], 2.5)
    # residuary resistance drops strongly with slenderness (LVR) at high Fn
    assert YD41._interp_Rr((0.5, 9.0, 4.0)) < 0.5 * YD41._interp_Rr((0.5, 4.0, 4.0))
    # _get_Rr must evaluate the surface at (fn, lvr, btr)
    YD41.fn, YD41.phi = 0.4, 0.0
    YD41.yacht.appendages, appendages = [], YD41.yacht.appendages
    expected = YD41._interp_Rr((0.4, YD41.lvr, YD41.btr)) * YD41.mass * YD41.g * 1e-3
    YD41.yacht.appendages = appendages
    Rr_app = sum(a._cr(0.4) * a.vol * YD41.rho * YD41.g * 1e-3 for a in appendages)
    np_testing.assert_allclose(YD41._get_Rr(), expected + Rr_app)


def test_build_interp_func_no_deprecation():
    """Verify build_interp_func doesn't use deprecated interp1d."""
    import warnings

    from python_vpp.UtilsMod import build_interp_func
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        func = build_interp_func("main", i=1)
        result = func(30.0)
        assert isinstance(float(result), float)
