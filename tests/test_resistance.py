import numpy.testing as np_testing

from src.HydroMod import HydroMod
from src.YachtMod import Keel, Rudder, Yacht


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
