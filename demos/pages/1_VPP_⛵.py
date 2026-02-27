import json
import logging
import os
import sys
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from utils import footer, header

sys.path.append(os.path.realpath("."))
from src.api import app
from src.UtilsMod import KNOTS_TO_MPS, _get_cross, _get_vmg, _polar, cols, stl

st.set_page_config(page_title="VPP", page_icon="⛵")


def process_yacht_specifications(
    tws_range: List[int],
    twa_range: List[int],
    yacht: Dict,
    keel: Dict,
    rudder: Dict,
    main: Dict,
    jib: Dict,
    kite: Dict,
):
    data = {
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

    logging.info("Starting VPP simulation")
    json_string = json.dumps(data)
    headers = {"content-type": "application/json", "Accept-Charset": "UTF-8"}
    client = app.test_client()
    response = client.post("/api/vpp/", data=json_string, headers=headers)

    logging.info("VPP simulation completed")
    return response


def plot_single_polar(response: Dict[str, Any]) -> plt.Figure:
    name = response.json["name"]
    sails = response.json["sails"]
    twa_range = np.array(response.json["twa"])
    tws_range = np.array(response.json["tws"])
    results = np.array(response.json["results"])

    n = 1

    # polar plot
    fig, ax = _polar(n)
    for i in range(len(tws_range)):
        vmg, ids = _get_vmg(results[i, :, :, :], twa_range)
        for k in range(len(sails)):
            idx = _get_cross(results[i, :, :, :], k)
            for j in range(n):
                lab = "_nolegend_"
                if k == 0:
                    lab = name + " " + f"{tws_range[i]/KNOTS_TO_MPS:.1f}"

                ax[j].plot(
                    twa_range[idx[0] : idx[1]] / 180 * np.pi,
                    results[i, idx[0] : idx[1], k, j],
                    color=cols[k % 7],
                    lw=np.where(i < 7, 1.5, 2.5),
                    linestyle=stl[i % 7],
                    label=lab,
                )

        # add VMG points
        for pts in range(2):
            ax[0].plot(
                twa_range[vmg[pts]] / 180 * np.pi,
                results[i, vmg[pts], ids[pts], 0],
                "o",
                color=cols[ids[pts] % 7],
                lw=1,
                markersize=4,
                mfc="None",
            )

        ax[0].legend(title=r"TWS (knots)", loc=1, bbox_to_anchor=(1.05, 1.05))
    plt.tight_layout()
    return fig


PRESETS = {
    "YD41": {
        "yacht": {
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
        },
        "keel": {"Cu": 1.00, "Cl": 0.78, "Span": 1.90},
        "rudder": {"Cu": 0.48, "Cl": 0.22, "Span": 1.15},
        "main": {"Name": "MN1", "P": 16.60, "E": 5.60, "Roach": 0.1, "BAD": 1.0},
        "jib": {"Name": "J1", "I": 16.20, "J": 5.10, "LPG": 5.40, "HBI": 1.8},
        "kite": {"Name": "A2", "area": 150.0, "vce": 9.55},
    },
    "Daring (5.5m)": {
        "yacht": {
            "Name": "Daring",
            "Lwl": 7.01,
            "Vol": 1.95,
            "Bwl": 1.70,
            "Tc": 0.45,
            "WSA": 11.5,
            "Tmax": 1.35,
            "Amax": 0.38,
            "Mass": 2000,
            "Ff": 0.75,
            "Fa": 0.55,
            "Boa": 1.98,
            "Loa": 9.90,
        },
        "keel": {"Cu": 0.70, "Cl": 0.45, "Span": 0.90},
        "rudder": {"Cu": 0.32, "Cl": 0.18, "Span": 0.75},
        "main": {"Name": "MN1", "P": 10.80, "E": 3.30, "Roach": 0.1, "BAD": 0.80},
        "jib": {"Name": "J1", "I": 8.50, "J": 2.70, "LPG": 2.70, "HBI": 0.50},
        "kite": {"Name": "S1", "area": 50.0, "vce": 4.50},
    },
}

header()

st.markdown(
    """
    # Yacht VPP

    This is a 3 D.O.F. VPP for a mono hull displacement sailing yacht.

    The default parameters are pre-set particulars for the YD-41 yacht.

"""
)

preset_name = st.selectbox("Yacht preset", list(PRESETS.keys()), index=1)
preset = PRESETS[preset_name]
yacht = dict(preset["yacht"])
keel = dict(preset["keel"])
rudder = dict(preset["rudder"])
main = dict(preset["main"])
jib = dict(preset["jib"])
kite = dict(preset["kite"])

st.subheader("Yacht particulars")
for key, value in yacht.items():
    yacht[key] = st.text_input(f"{key}:", value)

st.subheader("Keel")
for key, value in keel.items():
    keel[key] = st.text_input(f"{key}:", value)

st.subheader("Rudder")
for key, value in rudder.items():
    rudder[key] = st.text_input(f"{key}:", value)

st.subheader("Main Sail")
for key, value in main.items():
    main[key] = st.text_input(f"{key}:", value)

st.subheader("Jib")
for key, value in jib.items():
    jib[key] = st.text_input(f"{key}:", value)

st.subheader("Kite (Spinnaker)")
for key, value in kite.items():
    kite[key] = st.text_input(f"{key}:", value)

st.subheader("Environment")
twa_slider = st.slider(
    "True wind angle (TWA) range", 35.0, 175.0, (35.0, 175.0), step=2.0
)
twa_range = np.arange(twa_slider[0], twa_slider[1], 2.0).tolist()

tws_slider = st.slider("True wind speed (TWS) range", 2.0, 25.0, (8.0, 12.0), step=2.0)
tws_range = np.arange(tws_slider[0], tws_slider[1], 2.0).tolist()

if st.button("Process Specifications"):
    with st.spinner("Running optimisation, this can take a minute or two."):
        response = process_yacht_specifications(
            tws_range, twa_range, yacht, keel, rudder, main, jib, kite
        )
        fig = plot_single_polar(response)
        st.pyplot(fig)

footer()
