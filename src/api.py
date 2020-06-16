"""
API for calling VPPMod

"""
from flask import Flask, request, redirect, url_for, flash, jsonify
import numpy as np
import json
import sys, os

sys.path.append(os.path.realpath("."))
from src.YachtMod import Yacht, Keel, Rudder
from src.SailMod import Main, Jib, Kite
from src.VPPMod import VPP

app = Flask(__name__)


@app.route("/api/sum/", methods=["POST"])
def makecalc():
    data = request.get_json()
    prediction = np.array2string(np.sum(data))
    return jsonify(prediction)


@app.route("/api/vpp/", methods=["POST"])
def makevppresults():
    data = request.get_json()
    keel = Keel(Cu=data["keel"]["Cu"], Cl=data["keel"]["Cl"], Span=data["keel"]["Span"])
    rudder = Rudder(
        Cu=data["rudder"]["Cu"], Cl=data["rudder"]["Cu"], Span=data["rudder"]["Cu"]
    )
    main = (
        Main(
            P=data["main"]["P"],
            E=data["main"]["E"],
            Roach=data["main"]["Roach"],
            BAD=data["main"]["BAD"],
        ),
    )
    jib = (
        Jib(
            I=data["jib"]["I"],
            J=data["jib"]["J"],
            LPG=data["jib"]["LPG"],
            HBI=data["jib"]["HBI"],
        ),
    )
    kite = (Kite(area=data["kite"]["area"], vce=data["kite"]["vce"]),)
    yacht = Yacht(
        Name=data["yacht"]["Name"],
        Lwl=data["yacht"]["Lwl"],
        Vol=data["yacht"]["Vol"],
        Bwl=data["yacht"]["Bwl"],
        Tc=data["yacht"]["Tc"],
        WSA=data["yacht"]["WSA"],
        Tmax=data["yacht"]["Tmax"],
        Amax=data["yacht"]["Amax"],
        Mass=data["yacht"]["Mass"],
        Ff=data["yacht"]["Ff"],
        Fa=data["yacht"]["Fa"],
        Boa=data["yacht"]["Boa"],
        Loa=data["yacht"]["Loa"],
        App=[keel, rudder],
        Sails=[
            Main(
                P=data["main"]["P"],
                E=data["main"]["E"],
                Roach=data["main"]["Roach"],
                BAD=data["main"]["BAD"],
            ),
            Jib(
                I=data["jib"]["I"],
                J=data["jib"]["J"],
                LPG=data["jib"]["LPG"],
                HBI=data["jib"]["HBI"],
            ),
            Kite(area=data["kite"]["area"], vce=data["kite"]["vce"]),
        ],
    )
    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(
        tws_range=np.array(data["tws_range"]), twa_range=np.array(data["twa_range"]),
    )

    vpp.run(verbose=True)
    res = vpp.result()  # compare this result to the result given by the request
    return jsonify(res)


if __name__ == "__main__":
    app.run()
