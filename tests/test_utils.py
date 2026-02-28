from src.SailMod import Jib, Kite, Main
from src.YachtMod import Keel, Rudder, Yacht

def return_YD41_particulars():

    YD41 = Yacht(
        Name="YD41",
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
        App=[Keel(Cu=1.00, Cl=0.78, Span=1.90), Rudder(Cu=0.48, Cl=0.22, Span=1.15)],
        Sails=[
            Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0),
            Jib("J1", I=16.20, J=5.10, LPG=5.40, HBI=1.8),
            Kite("A2", area=150.0, vce=9.55),
            Kite("A5", area=75.0, vce=2.75),
        ],
    )
    return YD41