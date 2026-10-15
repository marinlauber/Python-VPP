import os

import numpy as np
import pytest

from src.SailMod import Jib, Kite, Main
from src.VPPMod import VPP
from tests.test_utils import return_YD41_particulars


def test_single_sail_set(tmp_path):
    YD41 = return_YD41_particulars()

    YD41_no_kite = YD41
    YD41_no_kite.sails = [
        Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
        Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8)
    ]

    vpp = VPP(Yacht=YD41)

    vpp.set_analysis(
        tws_range=np.arange(4.0, 6.0, 1.0), twa_range=np.linspace(30.0, 180.0, 3)
    )

    vpp.run()
    vpp.write("results")

    polar_path = str(tmp_path / "test_polar.pdf")
    sail_path = str(tmp_path / "test_sail.pdf")
    vpp.polar(3, True, fname=polar_path)
    vpp.SailChart(True, fname=sail_path)
    assert os.path.exists(polar_path), "Polar plot was not created"
    assert os.path.exists(sail_path), "Sail chart was not created"


def test_sail_chart_no_deprecation_warning(tmp_path):
    """Verify sail_chart doesn't use deprecated interp2d."""
    import warnings

    yacht = return_YD41_particulars()
    yacht.sails = [
        Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
        Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8),
    ]
    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(
        tws_range=np.array([6.0, 10.0]),
        twa_range=np.linspace(30.0, 180.0, 16),
    )
    vpp.run(verbose=False)
    fname = str(tmp_path / "test_sailchart.pdf")
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        vpp.SailChart(save=True, fname=fname)
    assert os.path.exists(fname), "Sail chart was not created"


def test_phi_max_configurable():
    yacht = return_YD41_particulars()
    yacht.sails = [Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
                   Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8)]
    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(tws_range=np.array([10.0]),
                     twa_range=np.linspace(30.0, 180.0, 3),
                     phi_max=25.0)
    assert vpp.phi_max == 25.0


def test_run_without_analysis_raises():
    """Issue #46: raise with string literal should be a proper exception."""
    import pytest

    yacht = return_YD41_particulars()
    vpp = VPP(Yacht=yacht)
    with pytest.raises(RuntimeError, match="no analysis set"):
        vpp.run()


def test_set_analysis_empty_tws_raises():
    import pytest

    yacht = return_YD41_particulars()
    vpp = VPP(Yacht=yacht)
    with pytest.raises(ValueError, match="TWS range is empty"):
        vpp.set_analysis(tws_range=np.array([]), twa_range=np.linspace(30, 180, 5))


def test_set_analysis_empty_twa_raises():
    import pytest

    yacht = return_YD41_particulars()
    vpp = VPP(Yacht=yacht)
    with pytest.raises(ValueError, match="TWA range is empty"):
        vpp.set_analysis(tws_range=np.array([6.0, 10.0]), twa_range=np.array([]))


def test_set_analysis_tws_below_minimum_raises():
    import pytest

    yacht = return_YD41_particulars()
    vpp = VPP(Yacht=yacht)
    with pytest.raises(ValueError, match="outside valid bounds"):
        vpp.set_analysis(tws_range=np.array([1.0, 5.0]), twa_range=np.linspace(30, 180, 5))


def test_set_analysis_tws_above_maximum_raises():
    import pytest

    yacht = return_YD41_particulars()
    vpp = VPP(Yacht=yacht)
    with pytest.raises(ValueError, match="outside valid bounds"):
        vpp.set_analysis(tws_range=np.array([10.0, 40.0]), twa_range=np.linspace(30, 180, 5))


def test_set_analysis_twa_out_of_range_raises():
    import pytest

    yacht = return_YD41_particulars()
    vpp = VPP(Yacht=yacht)
    with pytest.raises(ValueError, match="outside valid bounds"):
        vpp.set_analysis(tws_range=np.array([6.0, 10.0]), twa_range=np.array([-5.0, 90.0]))


def test_legacy_method_names_accepted():
    """'iterative' and '5dof' are aliases of the sequential solver."""
    yacht = return_YD41_particulars()
    yacht.sails = [Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
                   Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8)]
    stores = []
    for method in ("sequential", "iterative", "5dof"):
        vpp = VPP(Yacht=yacht)
        vpp.set_analysis(tws_range=np.array([8.0]),
                         twa_range=np.linspace(40.0, 160.0, 4))
        vpp.run(method=method)
        stores.append(vpp.store)
    assert np.all(stores[0][0, :, 0, 0] > 0)
    np.testing.assert_array_equal(stores[0], stores[1])
    np.testing.assert_array_equal(stores[0], stores[2])


def _upwind_vpp(tws_range, twa_range):
    yacht = return_YD41_particulars()
    yacht.sails = [Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
                   Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8)]
    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(tws_range=tws_range, twa_range=twa_range)
    vpp.run()
    return vpp


def test_speed_increases_with_tws_when_depowered():
    """Optimal depowering can never make the boat slower in more wind."""
    vpp = _upwind_vpp(np.array([14.0, 16.0, 18.0, 20.0]), np.array([28.0, 36.0, 44.0, 52.0, 60.0]))
    vb = vpp.store[:, :, 0, 0]
    assert np.all(vb > 0)
    assert np.all(np.diff(vb, axis=0) > -1e-3), f"VB drops with TWS:\n{vb}"
    # heavy air is depowered and held at the heel limit
    assert np.all(vpp.store[-1, :, 0, 1] <= vpp.phi_max + 1e-6)
    assert np.all(vpp.store[-1, :, 0, 3] < 1.0) or np.all(vpp.store[-1, :, 0, 4] < 2.0)


def test_stored_points_are_in_equilibrium():
    """Every stored point satisfies force and moment equilibrium."""
    from src.UtilsMod import KNOTS_TO_MPS
    from src.VPPMod import RESID_TOL

    vpp = _upwind_vpp(np.array([6.0, 20.0]), np.linspace(30.0, 120.0, 4))
    vpp.aero.sails[1] = vpp.yacht.sails[1]
    for i, tws in enumerate(vpp.tws_range):
        for j, twa in enumerate(vpp.twa_range):
            vb, phi, leeway, flat, red = vpp.store[i, j, 0]
            r = vpp.resid([vb * KNOTS_TO_MPS, phi, leeway], twa, tws, flat, red)
            assert np.abs(r).max() < RESID_TOL, f"TWS {tws} TWA {twa}: {r}"


def test_kite_heel_capped():
    """Kites are held to their own heel limit (ORC ~21.5 deg), the jib to phi_max."""
    yacht = return_YD41_particulars()
    yacht.sails = [Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
                   Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8),
                   Kite("A2", area=150.0, vce=9.55)]
    assert yacht.sails[2].max_heel == 21.5
    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(tws_range=np.array([16.0]), twa_range=np.array([60.0, 120.0]))
    vpp.run()
    assert vpp.store[0, 1, 1, 0] > 0
    assert vpp.store[0, 1, 1, 1] <= 21.5 + 1e-6
    assert vpp.store[0, 0, 0, 1] > 21.5  # J1 at 60 deg heels past the kite limit


def test_infeasible_kite_left_unsolved():
    """A kite that cannot be held at the heel limit is stored as 0, not a fake point."""
    from src.UtilsMod import KNOTS_TO_MPS
    from src.VPPMod import RESID_TOL

    yacht = return_YD41_particulars()
    yacht.sails = [Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
                   Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8),
                   Kite("A2", area=150.0, vce=9.55)]
    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(tws_range=np.array([20.0]), twa_range=np.array([80.0, 150.0]))
    vpp.run()
    vpp.aero.sails[1] = vpp.yacht.sails[2]
    vpp.aero.up = False
    assert np.all(vpp.store[0, 0, 1] == 0.0), "A2 at 20 kn/80 deg should be infeasible"
    vb, phi, leeway, flat, red = vpp.store[0, 1, 1]
    assert vb > 0
    r = vpp.resid([vb * KNOTS_TO_MPS, phi, leeway], 150.0, vpp.tws_range[0], flat, red)
    assert np.abs(r).max() < RESID_TOL


def test_invalid_method_raises():
    import pytest

    yacht = return_YD41_particulars()
    yacht.sails = [Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
                   Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8)]
    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(tws_range=np.array([8.0]),
                     twa_range=np.linspace(40.0, 160.0, 3))
    with pytest.raises(ValueError, match="Unknown method"):
        vpp.run(method="bogus")


def test_sail_type_main_low():
    """Main with sail_type='main_low' loads lower CL coefficients."""
    main_hi = Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0)
    main_lo = Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0, sail_type="main_low")
    # At peak CL angle (~28 deg), low should have less lift
    assert main_lo.cl(28) < main_hi.cl(28)


def test_sail_type_jib_low():
    """Jib with sail_type='jib_low' loads lower CL coefficients."""
    jib_hi = Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8)
    jib_lo = Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8, sail_type="jib_low")
    assert jib_lo.cl(27) < jib_hi.cl(27)


def test_sail_type_sym_kite():
    """The default kite is the ORC 2026 symmetric spinnaker (table 5.8)."""
    kite_default = Kite("A2", area=150.0, vce=9.55)
    kite_sym = Kite("A2", area=150.0, vce=9.55, sail_type="sym_kite")
    assert kite_sym.cl(67) == pytest.approx(1.013)
    assert kite_sym.cd(150) == pytest.approx(0.702)
    assert kite_default.cl(67) == pytest.approx(kite_sym.cl(67))


def test_sail_type_asym_kite_variants():
    """Asymmetric spinnakers follow ORC 2026 tables 5.9 and 5.10."""
    kite_cl = Kite("A2", area=150.0, vce=9.55, sail_type="asym_cl_kite")
    kite_pole = Kite("A2", area=150.0, vce=9.55, sail_type="asym_pole_kite")
    # same up to 100 deg AWA ...
    assert kite_cl.cl(67) == pytest.approx(1.125)
    assert kite_pole.cl(67) == pytest.approx(kite_cl.cl(67))
    # ... but a pole keeps the sail working deeper
    assert kite_pole.cl(150) == pytest.approx(0.391)
    assert kite_pole.cl(150) > kite_cl.cl(150)


def test_parallel_matches_sequential():
    """Parallel solver must produce identical results to the sequential one."""
    yacht = return_YD41_particulars()
    yacht.sails = [Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
                   Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8),
                   Kite("A2", area=150.0, vce=9.55)]

    tws_range = np.array([6.0, 10.0])
    twa_range = np.linspace(40.0, 160.0, 5)

    vpp_seq = VPP(Yacht=yacht)
    vpp_seq.set_analysis(tws_range=tws_range, twa_range=twa_range)
    vpp_seq.run(method="sequential")

    vpp_par = VPP(Yacht=yacht)
    vpp_par.set_analysis(tws_range=tws_range, twa_range=twa_range)
    vpp_par.run(method="parallel")

    np.testing.assert_allclose(
        vpp_par.store, vpp_seq.store, atol=1e-6,
        err_msg="Parallel results differ from sequential"
    )


def test_parallel_method_accepted():
    """VPP.run(method='parallel') should not raise."""
    yacht = return_YD41_particulars()
    yacht.sails = [Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
                   Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8)]
    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(tws_range=np.array([8.0]),
                     twa_range=np.linspace(40.0, 160.0, 3))
    vpp.run(method="parallel")
    assert np.any(vpp.store[0, :, 0, 0] > 0)


def test_sym_kite_vpp_runs():
    """VPP runs with symmetric spinnaker coefficients."""
    from src.YachtMod import Keel, Rudder, Yacht
    yacht = Yacht(
        Name="YD41", Lwl=11.90, Vol=6.05, Bwl=3.18, Tc=0.4, WSA=28.20,
        Tmax=2.30, Amax=1.051, Mass=6500, Ff=1.5, Fa=1.5, Boa=4.2, Loa=12.5,
        App=[Keel(Cu=1.00, Cl=0.78, Span=1.90), Rudder(Cu=0.48, Cl=0.22, Span=1.15)],
        Sails=[Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
               Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8),
               Kite("A2", area=150.0, vce=9.55, sail_type="sym_kite")])
    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(tws_range=np.array([10.0]), twa_range=np.linspace(40.0, 160.0, 4))
    vpp.run()
    assert np.any(vpp.store[0, :, :, 0] > 0)
