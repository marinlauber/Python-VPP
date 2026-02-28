"""
API for calling VPPMod

"""
import logging
import os
import sys
from typing import Any, Dict

import numpy as np
from flask import Flask, jsonify, request

sys.path.append(os.path.realpath("."))
from src.SailMod import Jib, Kite, Main
from src.VPPMod import VPP
from src.YachtMod import Keel, Rudder, ShortKeel, Yacht

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)


@app.route("/ping")
def ping():
    logging.info("Ping route hit successfully.")
    return "Pong! The server is up and running."


def data_to_vpp(data: Dict[str, Any]) -> VPP:

    keel_data = data["keel"]
    keel_type = keel_data.get("type", "fin")
    # Also detect from keys if type is missing or inconsistent
    if keel_type == "short" or "Length" in keel_data:
        keel = ShortKeel(
            Length=float(keel_data["Length"]),
            Depth=float(keel_data["Depth"]),
            Tc_ratio=float(keel_data.get("Tc_ratio", 0.15)),
        )
    else:
        keel = Keel(
            Cu=float(keel_data["Cu"]),
            Cl=float(keel_data["Cl"]),
            Span=float(keel_data["Span"]),
        )
    rudder = Rudder(
        Cu=float(data["rudder"]["Cu"]),
        Cl=float(data["rudder"]["Cu"]),
        Span=float(data["rudder"]["Span"])
    )
    yacht = Yacht(
        Name=data["yacht"]["Name"],
        Lwl=float(data["yacht"]["Lwl"]),
        Vol=float(data["yacht"]["Vol"]),
        Bwl=float(data["yacht"]["Bwl"]),
        Tc=float(data["yacht"]["Tc"]),
        WSA=float(data["yacht"]["WSA"]),
        Tmax=float(data["yacht"]["Tmax"]),
        Amax=float(data["yacht"]["Amax"]),
        Mass=float(data["yacht"]["Mass"]),
        Ff=float(data["yacht"]["Ff"]),
        Fa=float(data["yacht"]["Fa"]),
        Boa=float(data["yacht"]["Boa"]),
        Loa=float(data["yacht"]["Loa"]),
        App=[keel, rudder],
        Sails=[
            Main(
                name=data["main"]["Name"],
                P=float(data["main"]["P"]),
                E=float(data["main"]["E"]),
                Roach=float(data["main"]["Roach"]),
                BAD=float(data["main"]["BAD"]),
            ),
            Jib(
                name=data["jib"]["Name"],
                I=float(data["jib"]["I"]),
                J=float(data["jib"]["J"]),
                LPG=float(data["jib"]["LPG"]),
                HBI=float(data["jib"]["HBI"]),
            ),
            Kite(
                name=data["kite"]["Name"],
                area=float(data["kite"]["area"]),
                vce=float(data["kite"]["vce"]),
            ),
        ],
    )

    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(
        tws_range=np.array(data["tws_range"]),
        twa_range=np.array(data["twa_range"]),
    )
    return vpp


@app.route("/api/vpp/", methods=["POST"])
def makevppresults():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    try:
        vpp = data_to_vpp(data)
    except (KeyError, TypeError, ValueError) as e:
        logging.warning("Invalid VPP input: %s", e)
        return jsonify({"error": f"Invalid input: {e}"}), 400

    try:
        vpp.run(verbose=True)
    except Exception as e:
        logging.exception("VPP simulation failed")
        return jsonify({"error": f"Simulation failed: {e}"}), 500

    return jsonify(vpp.results())

if __name__ == "__main__":
    app.run(debug=True)
