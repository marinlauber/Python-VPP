import copy
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

# Colours and markers for up to 6 configs
CONFIG_COLORS = ["C0", "C1", "C2", "C3", "C4", "C5"]
CONFIG_MARKERS = ["o", "s", "^", "D", "v", "P"]


def render_config_tab(key_prefix: str, default_index: int = 1, baseline: Dict = None):
    """Render preset selector and editable fields. Returns config dict.

    If baseline is provided, fields that differ from the baseline are
    highlighted with a coloured background via custom CSS.
    """
    preset_name = st.selectbox(
        "Preset", list(PRESETS.keys()), index=default_index, key=f"{key_prefix}_preset"
    )
    preset = PRESETS[preset_name]
    config = {}
    changed_fields = []

    sail_type_options = {"main": MAIN_SAIL_TYPES, "jib": JIB_SAIL_TYPES, "kite": KITE_SAIL_TYPES}
    sail_types = {}
    for title, section_key in SECTIONS:
        section = copy.deepcopy(preset[section_key])
        with st.expander(title, expanded=False):
            if section_key == "keel":
                section = render_keel_inputs(section, key_prefix=key_prefix)
            else:
                if section_key in sail_type_options:
                    sail_types[section_key] = render_sail_type(
                        title, sail_type_options[section_key],
                        key_prefix=f"{key_prefix}_{section_key}",
                    )
                for field, value in section.items():
                    input_key = f"{key_prefix}_{section_key}_{field}"
                    section[field] = st.text_input(f"{field}:", value, key=input_key, help=FIELD_HELP.get(field, ""))

            # Track which fields differ from baseline
            if baseline is not None:
                for field, value in section.items():
                    base_val = str(baseline.get(section_key, {}).get(field, ""))
                    if str(value) != base_val:
                        changed_fields.append((section_key, field, value, base_val))

        config[section_key] = section
    config["_sail_types"] = sail_types

    if baseline is not None and changed_fields:
        st.caption("Changes vs Config 1:")
        for sec, fld, new_val, old_val in changed_fields:
            st.markdown(
                f"- **{sec}.{fld}**: `{old_val}` → `{new_val}`"
            )

    return config


def plot_comparison_polar(responses: List) -> plt.Figure:
    """Overlay N VPP results on the same polar plot with distinct colours/markers."""
    twa = np.array(responses[0].json["twa"])
    tws = np.array(responses[0].json["tws"])

    fig, ax = _polar(1)
    for ci, resp in enumerate(responses):
        results = np.array(resp.json["results"])
        name = resp.json["name"]
        color = CONFIG_COLORS[ci % len(CONFIG_COLORS)]
        marker = CONFIG_MARKERS[ci % len(CONFIG_MARKERS)]

        for i in range(len(tws)):
            tws_kts = tws[i] / KNOTS_TO_MPS
            speed = np.max(results[i, :, :, 0], axis=1)

            # Only first TWS gets a legend entry per config
            label = f"{name} (#{ci + 1})" if i == 0 else "_nolegend_"

            ax[0].plot(
                twa / 180 * np.pi,
                speed,
                color=color,
                lw=np.where(i < 7, 1.5, 2.5),
                linestyle=stl[i % 7],
                marker=marker,
                markevery=10,
                markersize=4,
                label=label,
            )

    ax[0].legend(title=r"TWS (kts)", loc=1, bbox_to_anchor=(1.05, 1.05))
    plt.tight_layout()
    return fig


def build_delta_table(responses: List) -> pd.DataFrame:
    """Build a table showing speed differences vs the first config."""
    twa = np.array(responses[0].json["twa"])
    tws = np.array(responses[0].json["tws"])
    base_results = np.array(responses[0].json["results"])
    base_name = responses[0].json["name"]

    rows = []
    for i, tw in enumerate(tws):
        tws_kts = tw / KNOTS_TO_MPS
        speed_base = np.max(base_results[i, :, :, 0], axis=1)
        for j, angle in enumerate(twa):
            row = {
                "TWS (kts)": f"{tws_kts:.0f}",
                "TWA (°)": f"{angle:.0f}",
                f"#{1} {base_name} (kts)": f"{speed_base[j]:.2f}",
            }
            for ci, resp in enumerate(responses[1:], start=2):
                res = np.array(resp.json["results"])
                name = resp.json["name"]
                speed = np.max(res[i, :, :, 0], axis=1)[j]
                delta = speed - speed_base[j]
                pct = (delta / speed_base[j] * 100) if speed_base[j] > 0 else 0.0
                row[f"#{ci} {name} (kts)"] = f"{speed:.2f}"
                row[f"Δ#{ci} (kts)"] = f"{delta:+.2f}"
                row[f"Δ#{ci} (%)"] = f"{pct:+.1f}"
            rows.append(row)
    return pd.DataFrame(rows)


def build_vmg_table(responses: List) -> pd.DataFrame:
    """Compare best VMG angles and speeds across all configs."""
    twa = np.array(responses[0].json["twa"])
    tws = np.array(responses[0].json["tws"])

    rows = []
    for i, tw in enumerate(tws):
        tws_kts = tw / KNOTS_TO_MPS
        for point, sign in [("Upwind", 1), ("Downwind", -1)]:
            row = {"TWS (kts)": f"{tws_kts:.0f}", "Point of sail": point}
            base_vmg = None
            for ci, resp in enumerate(responses, start=1):
                res = np.array(resp.json["results"])
                name = resp.json["name"]
                speed = np.max(res[i, :, :, 0], axis=1)
                vmg = sign * speed * np.cos(twa / 180 * np.pi)
                idx = np.argmax(vmg)
                row[f"#{ci} TWA"] = f"{twa[idx]:.0f}°"
                row[f"#{ci} VMG"] = f"{vmg[idx]:.2f}"
                if ci == 1:
                    base_vmg = vmg[idx]
                else:
                    row[f"Δ#{ci} VMG"] = f"{vmg[idx] - base_vmg:+.2f}"
            rows.append(row)
    return pd.DataFrame(rows)


# --- Session state for dynamic tabs ---

if "num_configs" not in st.session_state:
    st.session_state.num_configs = 2


# --- Page layout ---

header()

st.markdown(
    """
    # Compare Configurations

    Set up multiple configurations and compare their performance.
    Change any parameter — sail dimensions, keel shape, crew weight — and
    see the effect on boat speed and VMG. Fields that differ from Config 1
    are listed below each tab.
"""
)

with st.popover("ℹ️ How to use"):
    st.markdown(
        "Set up two or more configurations with different "
        "parameters (e.g. different keel shapes, sail areas, or hull dimensions). "
        "The comparison overlay shows all polars on the same plot, and the delta "
        "table quantifies speed differences at each TWS/TWA point."
    )

# Add / remove config buttons
btn_cols = st.columns([1, 1, 6])
with btn_cols[0]:
    if st.button("+ Add config"):
        if st.session_state.num_configs < 6:
            st.session_state.num_configs += 1
            st.rerun()
with btn_cols[1]:
    if st.button("- Remove last"):
        if st.session_state.num_configs > 2:
            st.session_state.num_configs -= 1
            st.rerun()

num = st.session_state.num_configs
tab_labels = [f"Config {i + 1}" for i in range(num)]
tabs = st.tabs(tab_labels)

configs = []
for idx, tab in enumerate(tabs):
    with tab:
        # First config has no baseline; others compare against Config 1
        if idx == 0:
            cfg = render_config_tab(f"cfg{idx}", default_index=1)
        else:
            cfg = render_config_tab(
                f"cfg{idx}", default_index=1, baseline=configs[0] if configs else None
            )
        configs.append(cfg)

tws_range, twa_range, env_params = render_environment_inputs(key_prefix="cmp")

st.subheader("Solver Settings")
solver_method = render_solver_method(key_prefix="cmp")
data_source = render_data_source(key_prefix="cmp")

if st.button("Compare"):
    if validate_ranges(tws_range, twa_range):
        responses = []
        with st.spinner(f"Running {num} VPP simulations..."):
            for cfg in configs:
                sail_types = cfg.pop("_sail_types", None)
                resp = run_vpp(cfg, tws_range, twa_range, method=solver_method, data_source=data_source, sail_types=sail_types, env_params=env_params)
                if resp.status_code != 200:
                    st.error("A simulation failed. Check your inputs.")
                    break
                responses.append(resp)

        if len(responses) == num:
            st.subheader("Overlaid polars")
            fig = plot_comparison_polar(responses)
            st.pyplot(fig)

            st.subheader("VMG comparison")
            vmg_df = build_vmg_table(responses)
            st.dataframe(vmg_df, use_container_width=True)

            with st.expander("Full speed delta table"):
                delta_df = build_delta_table(responses)
                st.dataframe(delta_df, use_container_width=True)

footer()
