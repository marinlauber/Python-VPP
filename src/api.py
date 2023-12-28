"""
API for calling VPPMod

"""
import logging
import os
import sys

import numpy as np
from flask import Flask, jsonify, request

sys.path.append(os.path.realpath("."))
from src.SailMod import Jib, Kite, Main
from src.VPPMod import VPP
from src.YachtMod import Keel, Rudder, Yacht

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)


@app.route("/ping")
def ping():
    logging.info("Ping route hit successfully.")
    return "Pong! The server is up and running."


@app.route("/api/vpp/", methods=["POST"])
def makevppresults():
    data = request.get_json()

    # TODO: Support multiple implementations of different sails: require API design

    keel = Keel(Cu=data["keel"]["Cu"], Cl=data["keel"]["Cl"], Span=data["keel"]["Span"])
    rudder = Rudder(
        Cu=data["rudder"]["Cu"], Cl=data["rudder"]["Cu"], Span=data["rudder"]["Cu"]
    )
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
                name=data["main"]["Name"],
                P=data["main"]["P"],
                E=data["main"]["E"],
                Roach=data["main"]["Roach"],
                BAD=data["main"]["BAD"],
            ),
            Jib(
                name=data["jib"]["Name"],
                I=data["jib"]["I"],
                J=data["jib"]["J"],
                LPG=data["jib"]["LPG"],
                HBI=data["jib"]["HBI"],
            ),
            Kite(
                name=data["kite"]["Name"],
                area=data["kite"]["area"],
                vce=data["kite"]["vce"],
            ),
        ],
    )
    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(
        tws_range=np.array(data["tws_range"]),
        twa_range=np.array(data["twa_range"]),
    )

    vpp.run(verbose=True)
    return jsonify(vpp.results())


if __name__ == "__main__":
    app.run(debug=True)
