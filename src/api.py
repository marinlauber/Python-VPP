"""
API for calling VPPMod

"""
import logging
import os
import sys
import tempfile
import zipfile
from typing import Any, Dict

import numpy as np
from flask import Flask, jsonify, request, send_file

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


def data_to_vpp(data: Dict[str, Any]) -> VPP:
    
    keel = Keel(
        Cu=float(data["keel"]["Cu"]), 
        Cl=float(data["keel"]["Cl"]), 
        Span=float(data["keel"]["Span"])
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

    # TODO: Support multiple implementations of different sails: require API design
    # TODO: Error handling incorrect ranges

    vpp = data_to_vpp(data)
    vpp.run(verbose=True)

    return jsonify(vpp.results())

# TODO: Remove this - it can't actually send large files
@app.route("/api/vpp/plots", methods=["POST"])
def make_vpp_plots():
    data = request.get_json()

    vpp: VPP = data_to_vpp(data)
    vpp.run(verbose=True)

    with tempfile.TemporaryDirectory() as temp_dir:

        polars_path = os.path.join(temp_dir, 'polars.png')
        sailchart_path = os.path.join(temp_dir, 'sail_chart.png')

        vpp.polar(3, True, polars_path)
        vpp.SailChart(True, sailchart_path)

        zipf_name = f'{data["yacht"]["Name"]}.zip'
        zipf_path = os.path.join(temp_dir, zipf_name)

        with zipfile.ZipFile(zipf_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    zipf.write(os.path.join(temp_dir, file), arcname=file)
                zipf.close()
        
        return send_file(zipf_path,
            mimetype='application/zip',
            download_name=zipf_name,
            as_attachment = True,
            conditional=True,
        )

if __name__ == "__main__":
    app.run(debug=True)
