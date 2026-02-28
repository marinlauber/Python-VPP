import copy
import json
import logging
import os
import sys
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from presets import PRESETS
from utils import footer, header

sys.path.append(os.path.realpath("."))
from src.api import app
from src.UtilsMod import KNOTS_TO_MPS, _get_cross, _get_vmg, _polar, cols, stl

st.set_page_config(page_title="Compare", page_icon="⚖️", layout="wide")

SECTIONS = [
    ("Yacht", "yacht"),
    ("Keel", "keel"),
    ("Rudder", "rudder"),
    ("Main Sail", "main"),
    ("Jib", "jib"),
    ("Kite", "kite"),
]


def run_vpp(
    tws_range: List[float],
    twa_range: List[float],
    yacht: Dict,
    keel: Dict,
    rudder: Dict,
    main: Dict,
    jib: Dict,
    kite: Dict,
) -> Dict[str, Any]:
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
    client = app.test_client()
    response = client.post("/api/vpp/", data=json_string, headers=headers)
    return response


def config_column(label: str, key_prefix: str, default_index: int = 0):
    """Render a preset selector and editable fields, return the config dicts."""
    preset_name = st.selectbox(
        "Preset", list(PRESETS.keys()), index=default_index, key=f"{key_prefix}_preset"
    )
    preset = PRESETS[preset_name]
    config = {}
    for title, section_key in SECTIONS:
        section = copy.deepcopy(preset[section_key])
        with st.expander(title, expanded=(section_key == "yacht")):
            for field, value in section.items():
                section[field] = st.text_input(
                    f"{field}:", value, key=f"{key_prefix}_{section_key}_{field}"
                )
        config[section_key] = section
    return config


def best_speed(results: np.ndarray) -> np.ndarray:
    """Return best boat speed across all sails for each TWS/TWA."""
    return np.max(results[:, :, :, 0], axis=2)


def plot_comparison_polar(resp_a, resp_b) -> plt.Figure:
    """Overlay two VPP results on the same polar plot."""
    twa = np.array(resp_a.json["twa"])
    tws = np.array(resp_a.json["tws"])
    res_a = np.array(resp_a.json["results"])
    res_b = np.array(resp_b.json["results"])
    name_a = resp_a.json["name"]
    name_b = resp_b.json["name"]

    fig, ax = _polar(1)
    for i in range(len(tws)):
        tws_kts = tws[i] / KNOTS_TO_MPS

        # Config A — solid lines
        speed_a = np.max(res_a[i, :, :, 0], axis=1)
        ax[0].plot(
            twa / 180 * np.pi,
            speed_a,
            color="C0",
            lw=np.where(i < 7, 1.5, 2.5),
            linestyle=stl[i % 7],
            label=f"{name_a} {tws_kts:.0f}" if i == 0 else f"_a_{tws_kts:.0f}",
        )

        # Config B — dashed-marker lines
        speed_b = np.max(res_b[i, :, :, 0], axis=1)
        ax[0].plot(
            twa / 180 * np.pi,
            speed_b,
            color="C1",
            lw=np.where(i < 7, 1.5, 2.5),
            linestyle=stl[i % 7],
            label=f"{name_b} {tws_kts:.0f}" if i == 0 else f"_b_{tws_kts:.0f}",
        )

    ax[0].legend(title=r"TWS (kts)", loc=1, bbox_to_anchor=(1.05, 1.05))
    plt.tight_layout()
    return fig


def build_delta_table(resp_a, resp_b) -> pd.DataFrame:
    """Build a table showing speed differences between configs."""
    twa = np.array(resp_a.json["twa"])
    tws = np.array(resp_a.json["tws"])
    res_a = np.array(resp_a.json["results"])
    res_b = np.array(resp_b.json["results"])
    name_a = resp_a.json["name"]
    name_b = resp_b.json["name"]

    rows = []
    for i, tw in enumerate(tws):
        tws_kts = tw / KNOTS_TO_MPS
        speed_a = np.max(res_a[i, :, :, 0], axis=1)
        speed_b = np.max(res_b[i, :, :, 0], axis=1)
        for j, angle in enumerate(twa):
            va = speed_a[j]
            vb = speed_b[j]
            delta = vb - va
            pct = (delta / va * 100) if va > 0 else 0.0
            rows.append(
                {
                    "TWS (kts)": f"{tws_kts:.0f}",
                    "TWA (°)": f"{angle:.0f}",
                    f"{name_a} (kts)": f"{va:.2f}",
                    f"{name_b} (kts)": f"{vb:.2f}",
                    "Δ (kts)": f"{delta:+.2f}",
                    "Δ (%)": f"{pct:+.1f}",
                }
            )
    return pd.DataFrame(rows)


def build_vmg_table(resp_a, resp_b) -> pd.DataFrame:
    """Compare best VMG angles and speeds between configs."""
    twa = np.array(resp_a.json["twa"])
    tws = np.array(resp_a.json["tws"])
    res_a = np.array(resp_a.json["results"])
    res_b = np.array(resp_b.json["results"])
    name_a = resp_a.json["name"]
    name_b = resp_b.json["name"]

    rows = []
    for i, tw in enumerate(tws):
        tws_kts = tw / KNOTS_TO_MPS
        for label, sign in [("Upwind", 1), ("Downwind", -1)]:
            vmg_a = sign * np.max(res_a[i, :, :, 0], axis=1) * np.cos(twa / 180 * np.pi)
            vmg_b = sign * np.max(res_b[i, :, :, 0], axis=1) * np.cos(twa / 180 * np.pi)
            idx_a = np.argmax(vmg_a)
            idx_b = np.argmax(vmg_b)
            rows.append(
                {
                    "TWS (kts)": f"{tws_kts:.0f}",
                    "Point of sail": label,
                    f"{name_a} TWA": f"{twa[idx_a]:.0f}°",
                    f"{name_a} VMG": f"{vmg_a[idx_a]:.2f}",
                    f"{name_b} TWA": f"{twa[idx_b]:.0f}°",
                    f"{name_b} VMG": f"{vmg_b[idx_b]:.2f}",
                    "Δ VMG": f"{vmg_b[idx_b] - vmg_a[idx_a]:+.2f}",
                }
            )
    return pd.DataFrame(rows)


# --- Page layout ---

header()

st.markdown(
    """
    # Compare Configurations

    Set up two configurations side by side, then compare their performance.
    Change any parameter — sail dimensions, keel shape, crew weight — and
    see the effect on boat speed, VMG and depowering.
"""
)

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Configuration A")
    config_a = config_column("A", "a", default_index=1)

with col_b:
    st.subheader("Configuration B")
    config_b = config_column("B", "b", default_index=1)

st.subheader("Environment")
twa_slider = st.slider(
    "True wind angle (TWA) range", 35.0, 175.0, (35.0, 175.0), step=2.0, key="cmp_twa"
)
twa_range = np.arange(twa_slider[0], twa_slider[1], 2.0).tolist()

tws_slider = st.slider(
    "True wind speed (TWS) range", 2.0, 25.0, (8.0, 12.0), step=2.0, key="cmp_tws"
)
tws_range = np.arange(tws_slider[0], tws_slider[1], 2.0).tolist()

if st.button("Compare"):
    if not tws_range:
        st.error("TWS range is empty. Make sure the min and max wind speeds are not equal.")
    elif not twa_range:
        st.error("TWA range is empty. Make sure the min and max wind angles are not equal.")
    else:
        with st.spinner("Running both VPP simulations..."):
            resp_a = run_vpp(
                tws_range, twa_range,
                config_a["yacht"], config_a["keel"], config_a["rudder"],
                config_a["main"], config_a["jib"], config_a["kite"],
            )
            resp_b = run_vpp(
                tws_range, twa_range,
                config_b["yacht"], config_b["keel"], config_b["rudder"],
                config_b["main"], config_b["jib"], config_b["kite"],
            )

        if resp_a.status_code != 200 or resp_b.status_code != 200:
            st.error("One or both simulations failed. Check your inputs.")
        else:
            st.subheader("Overlaid polars")
            fig = plot_comparison_polar(resp_a, resp_b)
            st.pyplot(fig)

            st.subheader("VMG comparison")
            vmg_df = build_vmg_table(resp_a, resp_b)
            st.dataframe(vmg_df, use_container_width=True)

            with st.expander("Full speed delta table"):
                delta_df = build_delta_table(resp_a, resp_b)
                st.dataframe(delta_df, use_container_width=True)

footer()
