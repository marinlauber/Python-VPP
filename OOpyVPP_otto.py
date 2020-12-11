#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__ = "M.Lauber@soton.ac.uk"

import numpy as np

from src.YachtMod import Yacht, Keel, Rudder
from src.SailMod import Main, Jib, Kite
from src.VPPMod import VPP


if __name__ == "__main__":

    YD41 = Yacht(
        Name="V80",
        Lwl=22.66,
        Vol=33.23,
        Bwl=4.84,
        Tc=0.73,
        WSA=83.11,
        Tmax=4.00,
        Amax=3.25,
        Mass=35250.00,
        Ff=1.83,
        Fa=1.64,
        Boa=5.8,
        Loa=25.92,
        App=[Keel(Cu=1.49, Cl=1.49, Span=2.90),
            Rudder(Cu=0.65, Cl=0.20, Span=2.40)],
        Sails=[Main(P=32.30, E=10.44, Roach=0.1, BAD=2.05),
                Jib(I=31.50, J=9.00, LPG=9.37, HBI=1.94)],
    )

    vpp = VPP(Yacht=YD41)

    vpp.set_analysis(tws_range=np.array([6.0]),
                     twa_range=np.linspace(30.0,180.0,21))

    vpp.run(verbose=True, write="test_file")
    vpp.polar(n=3, save=False)
