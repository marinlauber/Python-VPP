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
    # Environment parameters
    roughness = float(data.get("roughness", 150e-6))
    Hs = float(data.get("Hs", 0.0))
    Ts = float(data.get("Ts", 0.0))
    wave_direction = data.get("wave_direction")
    if wave_direction is not None:
        wave_direction = float(wave_direction)

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
        roughness=roughness,
        Hs=Hs,
        Ts=Ts,
        wave_direction=wave_direction,
        App=[keel, rudder],
        Sails=[
            Main(
                name=data["main"]["Name"],
                P=float(data["main"]["P"]),
                E=float(data["main"]["E"]),
                Roach=float(data["main"]["Roach"]),
                BAD=float(data["main"]["BAD"]),
                data_source=data.get("data_source", "orc"),
                cl_data=data["main"].get("cl_data"),
                cd_data=data["main"].get("cd_data"),
                sail_type=data["main"].get("sail_type"),
            ),
            Jib(
                name=data["jib"]["Name"],
                I=float(data["jib"]["I"]),
                J=float(data["jib"]["J"]),
                LPG=float(data["jib"]["LPG"]),
                HBI=float(data["jib"]["HBI"]),
                data_source=data.get("data_source", "orc"),
                cl_data=data["jib"].get("cl_data"),
                cd_data=data["jib"].get("cd_data"),
                sail_type=data["jib"].get("sail_type"),
            ),
            Kite(
                name=data["kite"]["Name"],
                area=float(data["kite"]["area"]),
                vce=float(data["kite"]["vce"]),
                data_source=data.get("data_source", "orc"),
                cl_data=data["kite"].get("cl_data"),
                cd_data=data["kite"].get("cd_data"),
                sail_type=data["kite"].get("sail_type"),
            ),
        ],
    )

    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(
        tws_range=np.array(data["tws_range"]),
        twa_range=np.array(data["twa_range"]),
    )
    return vpp, data.get("method", "iterative")


@app.route("/api/vpp/", methods=["POST"])
def makevppresults():
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    try:
        vpp, method = data_to_vpp(data)
    except (KeyError, TypeError, ValueError) as e:
        logging.warning("Invalid VPP input: %s", e)
        return jsonify({"error": f"Invalid input: {e}"}), 400

    try:
        vpp.run(verbose=True, method=method)
    except Exception as e:
        logging.exception("VPP simulation failed")
        return jsonify({"error": f"Simulation failed: {e}"}), 500

    return jsonify(vpp.results())

if __name__ == "__main__":
    app.run(debug=True)
