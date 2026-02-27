import os

import numpy as np
import pytest
from src.SailMod import Jib, Kite, Main
from src.VPPMod import VPP
from src.YachtMod import Keel, Rudder, Yacht


# Daring GZ curve (estimated for classic 5.5m, ~50% ballast ratio, GM ~0.70m)
DARING_GZ = {
    "Heel": [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
    "GZ":   [0.000, 0.120, 0.230, 0.310, 0.350, 0.330, 0.260],
}


def return_daring():
    """Create Daring yacht with estimated 5.5m class parameters.

    Published values (classicsailboats.org / Cowes Classics):
        LOA=9.90m, LWL=7.01m, Beam=1.98m, Draft=1.35m,
        Displacement=2000kg, Upwind SA=29.73m²

    Estimated values are documented in docs/plans/2026-02-27-daring-vpp.md
    """
    return Yacht(
        Name="Daring",
        Lwl=7.01,
        Vol=1.95,
        Bwl=1.70,
        Tc=0.45,
        WSA=11.5,
        Tmax=1.35,
        Amax=0.38,
        Mass=2000,
        Loa=9.90,
        Boa=1.98,
        Ff=0.75,
        Fa=0.55,
        App=[
            Keel(Cu=0.70, Cl=0.45, Span=0.90),
            Rudder(Cu=0.32, Cl=0.18, Span=0.75),
        ],
        Sails=[
            Main("MN1", P=10.80, E=3.30, Roach=0.1, BAD=0.80),
            Jib("J1", I=8.50, J=2.70, LPG=2.70, HBI=0.50),
            Kite("S1", area=50.0, vce=4.50),
        ],
        GZ=DARING_GZ,
        crew_weight=240.0,
    )


def test_daring_vpp_runs():
    """Daring VPP should solve without errors across a range of conditions."""
    daring = return_daring()
    vpp = VPP(Yacht=daring)
    vpp.set_analysis(
        tws_range=np.arange(6.0, 14.0, 2.0),
        twa_range=np.linspace(35.0, 175.0, 15),
    )
    vpp.run(verbose=False)
    results = vpp.results()
    assert results["name"] == "Daring"
    assert len(results["tws"]) == 4


def test_daring_boat_speed_sanity():
    """Daring should produce reasonable speeds: 3-7 knots in moderate wind."""
    daring = return_daring()
    vpp = VPP(Yacht=daring)
    vpp.set_analysis(
        tws_range=np.array([10.0]),
        twa_range=np.linspace(40.0, 160.0, 13),
    )
    vpp.run(verbose=False)
    results = np.array(vpp.results()["results"])
    max_speed = np.max(results[:, :, :, 0])
    assert 3.0 < max_speed < 7.0, f"Max speed {max_speed:.1f} kts outside expected range"


def test_daring_polars_saved(tmp_path):
    """Daring should produce polar plot and sail chart files."""
    daring = return_daring()
    vpp = VPP(Yacht=daring)
    vpp.set_analysis(
        tws_range=np.arange(6.0, 14.0, 2.0),
        twa_range=np.linspace(35.0, 175.0, 15),
    )
    vpp.run(verbose=False)

    polar_path = str(tmp_path / "daring_polar.png")
    sail_path = str(tmp_path / "daring_sail.png")
    vpp.polar(3, True, fname=polar_path)
    vpp.SailChart(True, fname=sail_path)
    assert os.path.exists(polar_path), "Polar plot was not created"
    assert os.path.exists(sail_path), "Sail chart was not created"
