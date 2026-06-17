import os

import numpy as np

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

    vpp.run(verbose=False)
    vpp.write("results")

    polar_path = str(tmp_path / "test_polar.png")
    sail_path = str(tmp_path / "test_sail.png")
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
    fname = str(tmp_path / "test_sailchart.png")
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


def test_5dof_solver_runs():
    """5-DOF solver produces non-zero speeds."""
    yacht = return_YD41_particulars()
    yacht.sails = [Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
                   Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8)]
    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(tws_range=np.array([8.0]),
                     twa_range=np.linspace(40.0, 160.0, 4))
    vpp.run(method="5dof")
    speeds = vpp.store[0, :, 0, 0]
    assert np.any(speeds > 0), "5-DOF solver should produce non-zero speeds"


def test_5dof_vs_iterative_comparable():
    """5-DOF and iterative solvers should produce speeds within 15%."""
    yacht = return_YD41_particulars()
    yacht.sails = [Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
                   Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8)]

    vpp_iter = VPP(Yacht=yacht)
    vpp_iter.set_analysis(tws_range=np.array([8.0]),
                          twa_range=np.linspace(40.0, 160.0, 4))
    vpp_iter.run(method="iterative")

    vpp_5dof = VPP(Yacht=yacht)
    vpp_5dof.set_analysis(tws_range=np.array([8.0]),
                          twa_range=np.linspace(40.0, 160.0, 4))
    vpp_5dof.run(method="5dof")

    speeds_iter = vpp_iter.store[0, :, 0, 0]
    speeds_5dof = vpp_5dof.store[0, :, 0, 0]

    # Compare only non-zero entries
    mask = speeds_iter > 0.1
    if np.any(mask):
        ratio = speeds_5dof[mask] / speeds_iter[mask]
        assert np.all(ratio > 0.85) and np.all(ratio < 1.15), (
            f"5-DOF vs iterative speed ratio out of 15% band: {ratio}"
        )


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
    """Symmetric spinnaker has higher CL than the default kite."""
    kite_default = Kite("A2", area=150.0, vce=9.55)
    kite_sym = Kite("A2", area=150.0, vce=9.55, sail_type="sym_kite")
    # ORC symmetric spinnaker has peak CL ~1.456 vs default ~1.08
    assert kite_sym.cl(67) > kite_default.cl(67)


def test_sail_type_asym_kite_variants():
    """Asymmetric spinnaker variants load and produce different coefficients."""
    kite_cl = Kite("A2", area=150.0, vce=9.55, sail_type="asym_cl_kite")
    kite_pole = Kite("A2", area=150.0, vce=9.55, sail_type="asym_pole_kite")
    # Both should produce non-zero CL at 67 deg
    assert kite_cl.cl(67) > 1.0
    assert kite_pole.cl(67) > 1.0
    # Pole tack has slightly higher peak CL than centerline
    assert kite_pole.cl(67) > kite_cl.cl(67)


def test_parallel_matches_iterative():
    """Parallel solver must produce identical results to sequential iterative."""
    yacht = return_YD41_particulars()
    yacht.sails = [Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
                   Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8),
                   Kite("A2", area=150.0, vce=9.55)]

    tws_range = np.array([6.0, 10.0])
    twa_range = np.linspace(40.0, 160.0, 5)

    vpp_seq = VPP(Yacht=yacht)
    vpp_seq.set_analysis(tws_range=tws_range, twa_range=twa_range)
    vpp_seq.run(method="iterative")

    vpp_par = VPP(Yacht=yacht)
    vpp_par.set_analysis(tws_range=tws_range, twa_range=twa_range)
    vpp_par.run(method="parallel")

    np.testing.assert_allclose(
        vpp_par.store, vpp_seq.store, atol=1e-6,
        err_msg="Parallel results differ from sequential iterative"
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
