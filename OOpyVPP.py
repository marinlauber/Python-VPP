#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__  = "M.Lauber@soton.ac.uk"

import numpy as np

from src.AeroMod import AeroMod
from src.HydroMod import HydroMod
from src.YachtMod import Yacht, Keel, Rudder
from src.SailMod import Main, Jib
from src.VPPMod import VPP

if __name__ == "__main__":

    # test with YD-41 from Larsson
    Keel  =  Keel(Cu=1.00,Cl=0.78,Span=1.90)
    Rudder = Rudder(Cu=0.48,Cl=0.22,Span=1.15)

    hydro = HydroMod(yacht=Yacht(Lwl=11.90,Vol=6.05,
                                Bwl=3.18,Tc=0.4,
                                WSA=28.20,Tmax=2.30,
                                Amax=1.051,Mass=6500,
                                App=[Keel,Rudder]))
    aero = AeroMod(sails=[Main(P=16.60,E=5.60,Roach=0.1,BAD=1.),
                          Jib(I=16.20,J=5.10,LPG=5.40,HBI=1.8)],
                Ff=1.5, Fa=1.5, B=4.20, L=12.50)

    vpp = VPP(AeroMod=aero, HydroMod=hydro)
    vpp.set_analysis(tws_range=np.array([5.0, 7.0]),
                     twa_range=np.linspace(30.0,140.0,23))
    vpp.run(verbose=True)
    vpp.polar()