#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__ = "M.Lauber@soton.ac.uk"

import numpy as np
from src.HydroMod import HydroMod
from src.YachtMod import Yacht, Keel, Rudder

if __name__ == "__main__":

    # test with YD-41 from Larsson
    Keel = Keel(Cu=1.00, Cl=0.78, Span=1.90)
    Rudder = Rudder(Cu=0.48, Cl=0.22, Span=1.15)

    YD41 = HydroMod(
        Yacht(
            Lwl=11.90,
            Vol=6.05,
            Bwl=3.18,
            Tc=0.4,
            WSA=28.20,
            Tmax=2.30,
            Amax=1.051,
            Mass=6500,
            App=[Keel, Rudder],
        )
    )

    YD41.show_resistance(vb=np.linspace(0, 12, 24))
