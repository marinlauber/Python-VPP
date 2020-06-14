import requests
import json
import os, sys
import numpy as np

sys.path.append(os.path.realpath("."))


from src.YachtMod import Yacht, Keel, Rudder
from src.SailMod import Main, Jib, Kite
from src.VPPMod import VPP


def test_interaction():
    """Test interaction between api and request by asking to sum arguments."""
    url = "http://0.0.0.0:5000/api/sum/"
    data = [
        [14.34, 1.68, 2.7, 25.0, 98.0, 2.8, 1.31, 0.53, 2.7, 13.0, 0.57, 1.96, 660.0]
    ]
    j_data = json.dumps(data)
    headers = {"content-type": "application/json", "Accept-Charset": "UTF-8"}
    r = requests.post(url, data=j_data, headers=headers)
    print(r, r.text)


def test_local_vpp_solution():
    """
    Return the dictionary produced by the VPP from an API call.
    
    Pass the list of parameters as a dictionary.
    
    Recieve the results as a dictionary.
    """
    Keel1 = Keel(Cu=1.00, Cl=0.78, Span=1.90)
    Rudder1 = Rudder(Cu=0.48, Cl=0.22, Span=1.15)

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
        App=[Keel1, Rudder1],
        Sails=[
            Main(P=16.60, E=5.60, Roach=0.1, BAD=1.0),
            Jib(I=16.20, J=5.10, LPG=5.40, HBI=1.8),
            Kite(area=150.0, vce=9.55),
        ],
    )

    yacht = dict(
        {
            "Name": "YD41",
            "Lwl": 11.90,
            "Vol": 6.05,
            "Bwl": 3.18,
            "Tc": 0.4,
            "WSA": 28.20,
            "Tmax": 2.30,
            "Amax": 1.051,
            "Mass": 6500,
            "Ff": 1.5,
            "Fa": 1.5,
            "Boa": 4.2,
            "Loa": 12.5,
        }
    )
    keel = dict({"Cu": 1.00, "Cl": 0.78, "Span": 1.90})
    rudder = dict({"Cu": 0.48, "Cl": 0.22, "Span": 1.15})
    main = dict({"P": 16.60, "E": 5.60, "Roach": 0.1, "BAD": 1.0})
    jib = dict({"I": 16.20, "J": 5.10, "LPG": 5.40, "HBI": 1.8})
    kite = dict({"area": 150.0, "vce": 9.55})
    tws_range = np.array([10.0]).tolist()
    twa_range = [i for i in np.linspace(30.0, 180.0, 5)]
    d = {
        "name": yacht["Name"],
        "yacht": yacht,
        "keel": keel,
        "rudder": rudder,
        "main": main,
        "jib": jib,
        "kite": kite,
        "tws_range": tws_range,
        "twa_range": twa_range,
    }
    json_string = json.dumps(d)
    url = "http://0.0.0.0:5000/api/vpp/"
    headers = {"content-type": "application/json", "Accept-Charset": "UTF-8"}
    response = requests.post(url, data=json_string, headers=headers).json()

    vpp = VPP(Yacht=YD41)
    vpp.set_analysis(
        tws_range=np.array([10.0]), twa_range=np.linspace(30.0, 180.0, 5),
    )
    vpp.run(verbose=True)
    results = vpp.result()

    print(results["tws"] == response["tws"])
    print(results["twa"] == response["twa"])
    print(
        np.isclose(results["perf"], response["perf"], rtol=0.1)
    )  # the results aren't always repeatable beyond 0.1 d.p.


def test_remote_vpp_solution():
    """
    Return the dictionary produced by the VPP from an API call.
    
    Pass the list of parameters as a dictionary.
    
    Recieve the results as a dictionary.
    """
    Keel1 = Keel(Cu=1.00, Cl=0.78, Span=1.90)
    Rudder1 = Rudder(Cu=0.48, Cl=0.22, Span=1.15)

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
        App=[Keel1, Rudder1],
        Sails=[
            Main(P=16.60, E=5.60, Roach=0.1, BAD=1.0),
            Jib(I=16.20, J=5.10, LPG=5.40, HBI=1.8),
            Kite(area=150.0, vce=9.55),
        ],
    )

    yacht = dict(
        {
            "Name": "YD41",
            "Lwl": 11.90,
            "Vol": 6.05,
            "Bwl": 3.18,
            "Tc": 0.4,
            "WSA": 28.20,
            "Tmax": 2.30,
            "Amax": 1.051,
            "Mass": 6500,
            "Ff": 1.5,
            "Fa": 1.5,
            "Boa": 4.2,
            "Loa": 12.5,
        }
    )
    keel = dict({"Cu": 1.00, "Cl": 0.78, "Span": 1.90})
    rudder = dict({"Cu": 0.48, "Cl": 0.22, "Span": 1.15})
    main = dict({"P": 16.60, "E": 5.60, "Roach": 0.1, "BAD": 1.0})
    jib = dict({"I": 16.20, "J": 5.10, "LPG": 5.40, "HBI": 1.8})
    kite = dict({"area": 150.0, "vce": 9.55})
    tws_range = np.array([10.0]).tolist()
    twa_range = [i for i in np.linspace(30.0, 180.0, 5)]
    d = {
        "name": yacht["Name"],
        "yacht": yacht,
        "keel": keel,
        "rudder": rudder,
        "main": main,
        "jib": jib,
        "kite": kite,
        "tws_range": tws_range,
        "twa_range": twa_range,
    }
    json_string = json.dumps(d)
    url = "http://python-vpp-api.herokuapp.com/api/vpp/"
    headers = {"content-type": "application/json", "Accept-Charset": "UTF-8"}
    response = requests.post(url, data=json_string, headers=headers).json()

    vpp = VPP(Yacht=YD41)
    vpp.set_analysis(
        tws_range=np.array([10.0]), twa_range=np.linspace(30.0, 180.0, 5),
    )
    vpp.run(verbose=True)
    results = vpp.result()

    print(results["tws"] == response["tws"])
    print(results["twa"] == response["twa"])
    print(
        np.isclose(results["perf"], response["perf"], rtol=0.1)
    )  # the results aren't always repeatable beyond 0.1 d.p.


if __name__ == "__main__":
    # test_interaction()
    # test_local_vpp_solution()
    test_remote_vpp_solution()
