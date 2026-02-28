
import numpy as np

from tests.test_utils import return_YD41_particulars
from src.VPPMod import VPP
from src.SailMod import Jib, Main

def test_single_sail_set():
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
    vpp.polar(3, False)
    vpp.SailChart(False)
