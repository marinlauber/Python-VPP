import json
import logging
import os
import sys

import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

sys.path.append(os.path.realpath("."))
from src.api import app
from src.UtilsMod import _get_vmg, _get_cross, _polar, KNOTS_TO_MPS, cols, stl

yacht = {
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

keel = {"Cu": 1.00, "Cl": 0.78, "Span": 1.90}
rudder = {"Cu": 0.48, "Cl": 0.22, "Span": 1.15}
main = {"Name": "MN1", "P": 16.60, "E": 5.60, "Roach": 0.1, "BAD": 1.0}
jib = {"Name": "J1", "I": 16.20, "J": 5.10, "LPG": 5.40, "HBI": 1.8}
kite = {"Name": "A2", "area": 150.0, "vce": 9.55}

st.title("Yacht VPP")

st.subheader("Yacht")
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


def process_yacht_specifications(yacht, keel, rudder, main, jib, kite):
    tws_range = [6.0, 10.0]
    twa_range = [i for i in np.linspace(30.0, 180.0, 31)]

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

    json_string = json.dumps(data)
    headers = {"content-type": "application/json", "Accept-Charset": "UTF-8"}

    logging.info("Starting VPP simulation")
    client = app.test_client()
    response = client.post("/api/vpp/", data=json_string, headers=headers)
    logging.info("VPP simulation completed")
    return response


if st.button("Process Specifications"):
    response = process_yacht_specifications(yacht, keel, rudder, main, jib, kite)

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

        # add legend only on first axis
        ax[0].legend(title=r"TWS (knots)", loc=1, bbox_to_anchor=(1.05, 1.05))
    plt.tight_layout()

    st.pyplot(fig)
