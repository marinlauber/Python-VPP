import copy
import os
import sys
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from presets import PRESETS
from utils import (
    FIELD_HELP,
    KITE_SAIL_TYPES,
    JIB_SAIL_TYPES,
    MAIN_SAIL_TYPES,
    field_label,
    footer,
    header,
    render_data_source,
    render_environment_inputs,
    render_keel_inputs,
    render_roughness_input,
    render_sail_type,
    render_solver_method,
    run_vpp_direct,
    validate_ranges,
)

sys.path.append(os.path.realpath("."))
from src.UtilsMod import KNOTS_TO_MPS

st.set_page_config(page_title="Compare", page_icon="⚖️", layout="wide")

SECTIONS = [
    ("Yacht", "yacht"),
    ("Keel", "keel"),
    ("Rudder", "rudder"),
    ("Main Sail", "main"),
    ("Jib", "jib"),
    ("Kite", "kite"),
]

SECTION_TITLES = {k: title for title, k in SECTIONS}

# Colours for up to 6 configs (Plotly named colors)
CONFIG_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
]
PLOTLY_DASH = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]


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
                    section[field] = st.text_input(field_label(field), value, key=input_key, help=FIELD_HELP.get(field, ""))

            # Track which fields differ from baseline
            if baseline is not None:
                for field, value in section.items():
                    base_val = str(baseline.get(section_key, {}).get(field, ""))
                    if str(value) != base_val:
                        changed_fields.append((section_key, field, value, base_val))

        config[section_key] = section
    config["_roughness"] = render_roughness_input(key_prefix=key_prefix)
    config["_sail_types"] = sail_types

    if baseline is not None and changed_fields:
        lines = []
        for sec, fld, new_val, old_val in changed_fields:
            section_title = SECTION_TITLES.get(sec, sec)
            label = field_label(fld)
            lines.append(f"- **{section_title}** {label}: `{old_val}` → `{new_val}`")
        changes_md = "\n".join(lines)
        if len(changed_fields) <= 4:
            st.caption("Changes vs Config 1:")
            st.markdown(changes_md)
        else:
            with st.expander(f"Changes vs Config 1 ({len(changed_fields)} fields)"):
                st.markdown(changes_md)

    return config


def plot_comparison_polar(responses: List) -> go.Figure:
    """Overlay N VPP results on the same polar plot with distinct colours."""
    twa = np.array(responses[0]["twa"])
    tws = np.array(responses[0]["tws"])

    fig = go.Figure()
    for ci, resp in enumerate(responses):
        results = np.array(resp["results"])
        name = resp["name"]
        color = CONFIG_COLORS[ci % len(CONFIG_COLORS)]

        for i in range(len(tws)):
            tws_kts = tws[i] / KNOTS_TO_MPS
            speed = np.max(results[i, :, :, 0], axis=1)

            show_legend = i == 0
            fig.add_trace(go.Scatterpolar(
                theta=twa,
                r=speed,
                mode="lines",
                name=f"{name} (#{ci + 1})",
                legendgroup=f"config_{ci}",
                showlegend=show_legend,
                line=dict(
                    color=color,
                    width=2,
                    dash=PLOTLY_DASH[i % len(PLOTLY_DASH)],
                ),
                hovertemplate=(
                    f"<b>{name}</b> TWS={tws_kts:.0f}kts<br>"
                    "TWA=%{theta:.0f}°<br>"
                    "Speed=%{r:.2f}kts<extra></extra>"
                ),
            ))

    fig.update_layout(
        polar=dict(
            angularaxis=dict(
                direction="clockwise",
                rotation=90,
                dtick=15,
                ticksuffix="°",
            ),
            radialaxis=dict(
                angle=90,
                title="Speed (kts)",
            ),
            sector=[-90, 90],
        ),
        legend=dict(title="Configuration"),
        height=600,
    )
    return fig


def build_delta_table(responses: List) -> pd.DataFrame:
    """Build a table showing speed differences vs the first config."""
    twa = np.array(responses[0]["twa"])
    tws = np.array(responses[0]["tws"])
    base_results = np.array(responses[0]["results"])
    base_name = responses[0]["name"]

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
                res = np.array(resp["results"])
                name = resp["name"]
                speed = np.max(res[i, :, :, 0], axis=1)[j]
                delta = speed - speed_base[j]
                pct = (delta / speed_base[j] * 100) if speed_base[j] > 0 else 0.0
                row[f"#{ci} {name} (kts)"] = f"{speed:.2f}"
                row[f"Δ#{ci} (kts)"] = f"{delta:+.2f}"
                row[f"Δ#{ci} (%)"] = f"{pct:+.1f}"
            rows.append(row)
    return pd.DataFrame(rows)


def _build_vmg_section(responses: List, point: str, sign: int) -> pd.DataFrame:
    """Build a VMG table for one point of sail (upwind or downwind)."""
    twa = np.array(responses[0]["twa"])
    tws = np.array(responses[0]["tws"])

    rows = []
    for i, tw in enumerate(tws):
        tws_kts = tw / KNOTS_TO_MPS
        row = {"TWS (kts)": f"{tws_kts:.0f}"}
        base_vmg = None
        for ci, resp in enumerate(responses, start=1):
            res = np.array(resp["results"])
            name = resp["name"]
            speed = np.max(res[i, :, :, 0], axis=1)
            vmg = sign * speed * np.cos(twa / 180 * np.pi)
            idx = np.argmax(vmg)
            row[f"#{ci} {name} TWA"] = f"{twa[idx]:.0f}°"
            row[f"#{ci} {name} VMG (kts)"] = f"{vmg[idx]:.2f}"
            if ci == 1:
                base_vmg = vmg[idx]
            else:
                delta = vmg[idx] - base_vmg
                pct = (delta / base_vmg * 100) if base_vmg > 0 else 0.0
                # seconds per nautical mile difference
                spm_base = (3600.0 / base_vmg) if base_vmg > 0 else 0.0
                spm_new = (3600.0 / vmg[idx]) if vmg[idx] > 0 else 0.0
                delta_spm = spm_new - spm_base
                row[f"Δ#{ci} (kts)"] = f"{delta:+.2f}"
                row[f"Δ#{ci} (%)"] = f"{pct:+.1f}%"
                row[f"Δ#{ci} (s/NM)"] = f"{delta_spm:+.1f}"
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
        failed = False
        with st.status(f"Running {num} VPP simulations...", expanded=True) as status:
            for ci, cfg in enumerate(configs):
                sail_types = cfg.pop("_sail_types", None)
                cfg_roughness = cfg.pop("_roughness", 150e-6)
                cfg_env = dict(env_params, roughness=cfg_roughness)
                cfg_name = cfg.get("yacht", {}).get("Name", f"Config {ci + 1}")
                st.write(f"**{cfg_name}** (config {ci + 1} of {num})")

                def _on_tws(i, tws_kts, n_tws, _name=cfg_name):
                    st.write(f"  {_name}: TWS {tws_kts:.0f} kts complete ({i + 1}/{n_tws})")

                result, error = run_vpp_direct(
                    cfg, tws_range, twa_range, method=solver_method,
                    data_source=data_source, sail_types=sail_types,
                    env_params=cfg_env, progress_callback=_on_tws,
                )
                if error:
                    st.error(f"Config {ci + 1} failed: {error}")
                    failed = True
                    break
                responses.append(result)
            status.update(label="Simulations complete!", state="complete", expanded=False)

        if not failed and len(responses) == num:
            st.subheader("Overlaid polars")
            fig = plot_comparison_polar(responses)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("VMG comparison")
            st.markdown("**Upwind**")
            st.dataframe(_build_vmg_section(responses, "Upwind", 1), use_container_width=True, hide_index=True)
            st.markdown("**Downwind**")
            st.dataframe(_build_vmg_section(responses, "Downwind", -1), use_container_width=True, hide_index=True)

            with st.expander("Full speed delta table"):
                delta_df = build_delta_table(responses)
                st.dataframe(delta_df, use_container_width=True)

footer()
