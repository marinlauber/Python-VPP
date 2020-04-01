#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__  = "M.Lauber@soton.ac.uk"

import numpy as np
from HydroMod import HydroMod
from YachtMod import Yacht

if __name__ == "__main__":
    
    Vismara = HydroMod(Yacht(Lwl=12.91, Vol=5.521,
                             Bwl=3.050, Tc=0.393,
                             WSA=27.387, Tmax=2.44,
                             Amax=0.831))

    Vismara.show_resistance(np.linspace(0, 12, 24))
