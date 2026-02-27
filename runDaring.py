#!/usr/bin/env python3
"""
Velocity Prediction Program for the Daring sailing yacht.

The Daring is a one-design keelboat designed by Arthur Robb, based on
his 5.5 Metre class yacht "Vision" (1956 Olympic silver medal).

Published specifications (classicsailboats.org):
    LOA: 9.90m | LWL: 7.01m | Beam: 1.98m | Draft: 1.35m
    Displacement: 2000 kg | Upwind sail area: 29.73 m²

Estimated parameters are documented in docs/plans/2026-02-27-daring-vpp.md.
All estimates are marked and can be refined with actual measurements.
"""
import logging

import numpy as np

from src.SailMod import Jib, Kite, Main
from src.VPPMod import VPP
from src.YachtMod import Keel, Rudder, Yacht

logging.basicConfig(level=logging.INFO)

# --- Estimated GZ curve for classic 5.5m ---
# GM ~0.70m, ~50% ballast ratio, narrow beam (1.98m)
# See docs/plans/2026-02-27-daring-vpp.md for derivation
DARING_GZ = {
    "Heel": [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
    "GZ":   [0.000, 0.120, 0.230, 0.310, 0.350, 0.330, 0.260],
}

Daring = Yacht(
    Name="Daring",
    Lwl=7.01,       # (published) waterline length
    Vol=1.95,       # (estimated) 2000kg / 1025 kg/m³
    Bwl=1.70,       # (estimated) ~86% of Boa
    Tc=0.45,        # (estimated) canoe body draft
    WSA=11.5,       # (estimated) Delf series for narrow hull
    Tmax=1.35,      # (published) max draft incl. keel
    Amax=0.38,      # (estimated) Bwl × Tc × Cm(0.50)
    Mass=2000,      # (published) total displacement
    Loa=9.90,       # (published) length overall
    Boa=1.98,       # (published) beam overall
    Ff=0.75,        # (estimated) freeboard fore
    Fa=0.55,        # (estimated) freeboard aft
    App=[
        Keel(Cu=0.70, Cl=0.45, Span=0.90),     # (estimated) classic fin
        Rudder(Cu=0.32, Cl=0.18, Span=0.75),   # (estimated) separated rudder
    ],
    Sails=[
        Main("MN1", P=10.80, E=3.30, Roach=0.1, BAD=0.80),  # (est.) ~19.6 m²
        Jib("J1", I=8.50, J=2.70, LPG=2.70, HBI=0.50),      # (est.) ~11.5 m²
        Kite("S1", area=50.0, vce=4.50),                       # (est.) symmetric kite
    ],
    GZ=DARING_GZ,
    crew_weight=240.0,  # 3 crew × 80 kg
)

vpp = VPP(Yacht=Daring)

vpp.set_analysis(
    tws_range=np.arange(4.0, 22.0, 2.0),
    twa_range=np.linspace(30.0, 180.0, 31),
)

vpp.run(verbose=False)
vpp.write("results_daring")
vpp.polar(3, True)
vpp.SailChart(True)
