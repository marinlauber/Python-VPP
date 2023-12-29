import json
import logging
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.realpath("."))
from src.api import app
from src.UtilsMod import KNOTS_TO_MPS, _get_cross, _get_vmg

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
    tws_range = [10.0]
    twa_range = [i for i in np.linspace(30.0, 180.0, 5)]

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
