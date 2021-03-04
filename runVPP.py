#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np

from src.YachtMod import Yacht, Keel, Rudder
from src.SailMod import Main, Jib, Kite
from src.VPPMod import VPP
from src.UtilsMod import VPPResults

for i,mast_length in enumerate([16.60, 17.00]):
      YD41 = Yacht(Name="YD41",
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
                  App=[Keel(Cu=1.00, Cl=0.78, Span=1.90),
                        Rudder(Cu=0.48, Cl=0.22, Span=1.15),],
                  Sails=[Main("MN1", P=mast_length, E=5.60, Roach=0.1, BAD=1.0),
                        Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8),
                        Kite("A2", area=150.0, vce=9.55)]
            )

      vpp = VPP(Yacht=YD41)

      vpp.set_analysis(tws_range=np.arange(4.0,18.0,4.0),
                       twa_range=np.linspace(30.0,180.0,34))

      vpp.run(verbose=False)
      vpp.write('results_'+str(i+1))

boat1 = VPPResults("results_1")
boat2 = VPPResults("results_2")

boat1.polar_comp(boat2, n=3, save=True)
