#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__  = "M.Lauber@soton.ac.uk"

import numpy as np
from AeroMod import AeroMod
from SailMod import Main, Jib

if __name__ == "__main__":
    
    model = AeroMod(sails=[Main(P=16.60,E=5.60,Roach=0.1,BAD=1.),
                           Jib(I=16.20,J=5.10,LPG=5.40,HBI=1.8)])