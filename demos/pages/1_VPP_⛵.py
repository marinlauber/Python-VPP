import logging
import os
import sys
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from presets import PRESETS
from utils import (
    FIELD_HELP,
    KITE_SAIL_TYPES,
    JIB_SAIL_TYPES,
    MAIN_SAIL_TYPES,
    footer,
    header,
    render_data_source,
    render_environment_inputs,
    render_keel_inputs,
    render_sail_type,
    render_solver_method,
    run_vpp,
    validate_ranges,
)

sys.path.append(os.path.realpath("."))
from src.UtilsMod import KNOTS_TO_MPS, _get_cross, _get_vmg, _polar, cols, lab, stl

st.set_page_config(page_title="VPP", page_icon="⛵")


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
                    lab = f"{tws_range[i]/KNOTS_TO_MPS:.1f}"

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


def plot_depowering_polar(response: Dict[str, Any]) -> plt.Figure:
    """Plot flat and red depowering values on polar axes."""
    name = response.json["name"]
    sails = response.json["sails"]
    twa_range = np.array(response.json["twa"])
    tws_range = np.array(response.json["tws"])
    results = np.array(response.json["results"])

    fig, axes = plt.subplots(1, 2, subplot_kw=dict(polar=True), figsize=(12, 6))
    for ax_i, (idx, title) in enumerate([(3, "Flat"), (4, "RED")]):
        ax = axes[ax_i]
        ax.set_xticks(np.linspace(0, np.pi, 5))
        ax.set_theta_direction(-1)
        ax.set_theta_offset(np.pi / 2.0)
        ax.set_thetamin(0)
        ax.set_thetamax(180)
        ax.set_rmin(0.0)
        ax.set_xlabel(r"TWA ($^\circ$)")
        ax.set_ylabel(title, labelpad=-40)

        for i in range(len(tws_range)):
            for k in range(len(sails)):
                cross = _get_cross(results[i, :, :, :], k)
                label = "_nolegend_"
                if k == 0:
                    label = f"{tws_range[i]/KNOTS_TO_MPS:.1f}"
                ax.plot(
                    twa_range[cross[0] : cross[1]] / 180 * np.pi,
                    results[i, cross[0] : cross[1], k, idx],
                    color=cols[k % 7],
                    lw=np.where(i < 7, 1.5, 2.5),
                    linestyle=stl[i % 7],
                    label=label,
                )
        if ax_i == 0:
            ax.legend(title=r"TWS (kts)", loc=1, bbox_to_anchor=(1.05, 1.05))
    plt.tight_layout()
    return fig


def build_depowering_table(response: Dict[str, Any]) -> pd.DataFrame:
    """Build a table of depowering values for the best sail at each TWS/TWA."""
    sails = response.json["sails"]
    twa_range = np.array(response.json["twa"])
    tws_range = np.array(response.json["tws"])
    results = np.array(response.json["results"])

    rows = []
    for i, tws in enumerate(tws_range):
        tws_kts = tws / KNOTS_TO_MPS
        for j, twa in enumerate(twa_range):
            best_sail = int(np.argmax(results[i, j, :, 0]))
            vb = results[i, j, best_sail, 0]
            flat = results[i, j, best_sail, 3]
            red = results[i, j, best_sail, 4]
            if flat < 1.0 or red < 2.0:
                rows.append(
                    {
                        "TWS (kts)": f"{tws_kts:.0f}",
                        "TWA (°)": f"{twa:.0f}",
                        "Sail": sails[best_sail],
                        "Vb (kts)": f"{vb:.2f}",
                        "Flat": f"{flat:.2f}",
                        "RED": f"{red:.2f}",
                    }
                )
    if not rows:
        return pd.DataFrame({"Info": ["No depowering applied at these wind speeds"]})
    return pd.DataFrame(rows)


header()

st.markdown(
    """
    # Yacht VPP

    This is a 3 D.O.F. VPP for a mono hull displacement sailing yacht.
    The performance model is based on the
    [ORC VPP documentation](https://www.orc.org/rules/ORC%20VPP%20Documentation%202024.pdf).

"""
)

with st.popover("ℹ️ What is a VPP?"):
    st.markdown(
        "A Velocity Prediction Program computes the "
        "equilibrium speed of a sailing yacht at each combination of true "
        "wind speed (TWS) and true wind angle (TWA). It balances "
        "aerodynamic driving force against hydrodynamic resistance, side "
        "force against keel lift, and heeling moment against righting moment."
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
    yacht[key] = st.text_input(f"{key}:", value, help=FIELD_HELP.get(key, ""))

st.subheader("Keel")
keel = render_keel_inputs(keel, key_prefix="vpp")

st.subheader("Rudder")
for key, value in rudder.items():
    rudder[key] = st.text_input(f"{key}:", value, help=FIELD_HELP.get(key, ""))

st.subheader("Main Sail")
main_sail_type = render_sail_type("Main sail", MAIN_SAIL_TYPES, key_prefix="vpp_main")
for key, value in main.items():
    main[key] = st.text_input(f"{key}:", value, help=FIELD_HELP.get(key, ""))

st.subheader("Jib")
jib_sail_type = render_sail_type("Jib", JIB_SAIL_TYPES, key_prefix="vpp_jib")
for key, value in jib.items():
    jib[key] = st.text_input(f"{key}:", value, help=FIELD_HELP.get(key, ""))

st.subheader("Kite (Spinnaker)")
kite_sail_type = render_sail_type("Kite", KITE_SAIL_TYPES, key_prefix="vpp_kite")
for key, value in kite.items():
    kite[key] = st.text_input(f"{key}:", value, help=FIELD_HELP.get(key, ""))

tws_range, twa_range, env_params = render_environment_inputs(key_prefix="vpp")

st.subheader("Solver Settings")
solver_method = render_solver_method(key_prefix="vpp")
data_source = render_data_source(key_prefix="vpp")

if st.button("Process Specifications"):
    if validate_ranges(tws_range, twa_range):
        config = {"yacht": yacht, "keel": keel, "rudder": rudder, "main": main, "jib": jib, "kite": kite}
        with st.spinner("Running optimisation, this can take a minute or two."):
            sail_types = {"main": main_sail_type, "jib": jib_sail_type, "kite": kite_sail_type}
            response = run_vpp(config, tws_range, twa_range, method=solver_method, data_source=data_source, sail_types=sail_types, env_params=env_params)
            if response.status_code != 200:
                error_msg = response.json.get("error", "Unknown error") if response.json else "Unknown error"
                st.error(f"Simulation failed: {error_msg}")
                logging.error("VPP API returned %d: %s", response.status_code, error_msg)
            else:
                with st.popover("ℹ️ What is a polar plot?"):
                    st.markdown(
                        "The polar plot shows boat speed (radial "
                        "axis) vs true wind angle. Each curve is a different wind "
                        "speed. Dots mark the best VMG (velocity made good) angles "
                        "upwind and downwind."
                    )
                fig = plot_single_polar(response)
                st.pyplot(fig)

                st.subheader("Depowering (Flat & RED)")
                with st.popover("ℹ️ What is depowering?"):
                    st.markdown(
                        "*Flat* controls how much the sails are "
                        "flattened (1.0 = full power, 0.62 = maximum depower). "
                        "*RED* is the reef/reduction factor (2.0 = full sail, "
                        "lower = reefed). The VPP depowers automatically when "
                        "heel exceeds the limit."
                    )
                dep_fig = plot_depowering_polar(response)
                st.pyplot(dep_fig)

                with st.expander("Depowering data table"):
                    df = build_depowering_table(response)
                    st.dataframe(df, use_container_width=True)

footer()
