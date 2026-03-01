import copy
import json
import os
import sys
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from presets import PRESETS
from utils import (
    KITE_SAIL_TYPES,
    JIB_SAIL_TYPES,
    MAIN_SAIL_TYPES,
    footer,
    header,
    render_data_source,
    render_keel_inputs,
    render_sail_type,
    render_solver_method,
    run_vpp,
)

sys.path.append(os.path.realpath("."))
from src.RaceMod import Race
from src.WindMod import BrownianWind, ConstantWind, MeanRevertingWind

st.set_page_config(page_title="Match Race", page_icon="🏁", layout="wide")

SECTIONS = [
    ("Yacht", "yacht"),
    ("Keel", "keel"),
    ("Rudder", "rudder"),
    ("Main Sail", "main"),
    ("Jib", "jib"),
    ("Kite", "kite"),
]


def render_boat_config(key_prefix: str, default_index: int = 1) -> Dict:
    """Render preset selector + editable fields for one boat."""
    preset_name = st.selectbox(
        "Preset", list(PRESETS.keys()), index=default_index, key=f"{key_prefix}_preset"
    )
    preset = PRESETS[preset_name]
    config = {}
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
                    section[field] = st.text_input(f"{field}:", value, key=input_key)
        config[section_key] = section
    config["_sail_types"] = sail_types
    config["_preset_name"] = preset_name
    return config


def get_or_compute_polar(config: Dict, tws_range: List[float], twa_range: List[float],
                         method: str, data_source: str) -> callable:
    """Get polar interpolator — use cached file if preset matches, else compute."""
    preset_name = config.get("_preset_name", "")

    # Check for cached polar
    safe_name = preset_name.replace(" ", "_").replace("(", "").replace(")", "")
    cache_path = os.path.join("dat", f"polars_{safe_name}.json")
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            data = json.load(f)
        tws = np.array(data["tws"])
        twa = np.array(data["twa"])
        results = np.array(data["results"])
        return Race.build_polar_interp(tws, twa, results), data.get("name", preset_name)

    # Compute from scratch
    sail_types = config.pop("_sail_types", None)
    config.pop("_preset_name", None)
    response = run_vpp(config, tws_range, twa_range, method=method, data_source=data_source,
                       sail_types=sail_types)
    if response.status_code != 200:
        return None, None
    data = response.json
    tws = np.array(data["tws"])
    twa = np.array(data["twa"])
    results = np.array(data["results"])
    return Race.build_polar_interp(tws, twa, results), data["name"]


def plot_win_probability(mc: Dict, name_A: str, name_B: str) -> plt.Figure:
    """Horizontal stacked bar showing win probability."""
    total = mc["wins_A"] + mc["wins_B"]
    ties = len(mc["deltas"]) - total
    fig, ax = plt.subplots(figsize=(8, 1.2))
    n = len(mc["deltas"])
    pct_A = mc["wins_A"] / n * 100
    pct_B = mc["wins_B"] / n * 100
    pct_tie = ties / n * 100

    ax.barh(0, pct_A, color="C0", label=f"{name_A}: {pct_A:.0f}%")
    ax.barh(0, pct_tie, left=pct_A, color="lightgray", label=f"Tie: {pct_tie:.0f}%")
    ax.barh(0, pct_B, left=pct_A + pct_tie, color="C1", label=f"{name_B}: {pct_B:.0f}%")
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.set_xlabel("Win probability (%)")
    ax.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.6))
    plt.tight_layout()
    return fig


def plot_delta_histogram(mc: Dict, name_A: str, name_B: str) -> plt.Figure:
    """Histogram of time deltas across Monte Carlo runs."""
    fig, ax = plt.subplots(figsize=(8, 4))
    deltas = np.array(mc["deltas"])
    ax.hist(deltas, bins=30, color="C2", edgecolor="white", alpha=0.8)
    ax.axvline(0, color="black", linestyle="--", lw=1)
    ax.axvline(mc["mean_delta"], color="C3", linestyle="-", lw=2, label=f"Mean: {mc['mean_delta']:.1f}s")
    ax.set_xlabel(f"Time delta (s)  ← {name_A} faster | {name_B} faster →")
    ax.set_ylabel("Count")
    ax.legend()
    plt.tight_layout()
    return fig


def plot_course_trace(mc: Dict, name_A: str, name_B: str) -> plt.Figure:
    """Bird's eye view of both boats' tracks from the first race."""
    fig, ax = plt.subplots(figsize=(8, 10))
    trace_A, trace_B = mc["traces"]
    if trace_A:
        xA, yA = zip(*trace_A)
        ax.plot(xA, yA, "C0-", lw=1, alpha=0.7, label=name_A)
    if trace_B:
        xB, yB = zip(*trace_B)
        ax.plot(xB, yB, "C1-", lw=1, alpha=0.7, label=name_B)
    ax.set_xlabel("Cross-course (m)")
    ax.set_ylabel("Upwind distance (m)")
    ax.legend()
    ax.set_aspect("equal")
    plt.tight_layout()
    return fig


def build_race_stats_table(mc: Dict, name_A: str, name_B: str):
    """Build summary stats from Monte Carlo results."""
    results = mc["results"]
    times_A = [r["time_A"] for r in results]
    times_B = [r["time_B"] for r in results]
    tacks_A = [r["tack_count_A"] for r in results]
    tacks_B = [r["tack_count_B"] for r in results]
    gybes_A = [r["gybe_count_A"] for r in results]
    gybes_B = [r["gybe_count_B"] for r in results]
    deltas = np.array(mc["deltas"])

    return {
        "Metric": [
            "Mean elapsed (s)", "Std elapsed (s)",
            "Mean tacks", "Mean gybes",
            "Mean delta (s)", "Std delta (s)",
            "Best race (s)", "Worst race (s)",
        ],
        name_A: [
            f"{np.mean(times_A):.0f}", f"{np.std(times_A):.0f}",
            f"{np.mean(tacks_A):.1f}", f"{np.mean(gybes_A):.1f}",
            f"{mc['mean_delta']:.1f}", f"{np.std(deltas):.1f}",
            f"{min(times_A):.0f}", f"{max(times_A):.0f}",
        ],
        name_B: [
            f"{np.mean(times_B):.0f}", f"{np.std(times_B):.0f}",
            f"{np.mean(tacks_B):.1f}", f"{np.mean(gybes_B):.1f}",
            "", "",
            f"{min(times_B):.0f}", f"{max(times_B):.0f}",
        ],
    }


# --- Page layout ---

header()

st.markdown("""
# Match Race Simulation

This simulation races two boat configurations around a windward-leeward
course with random wind shifts.  Each race is run many times (Monte Carlo)
to estimate which boat has a statistical advantage.
""")

with st.popover("ℹ️ How it works"):
    st.markdown(
        "Both boats sail optimal VMG angles with tactical "
        "rules (layline tacking, covering, splitting, dirty air avoidance). "
        "Wind direction shifts randomly each second. Results show win "
        "probability, time deltas, and an example race trace."
    )

# --- Boat configs ---
st.subheader("Boat configurations")
col_A, col_B = st.columns(2)
with col_A:
    st.markdown("### Boat A")
    config_A = render_boat_config("race_A", default_index=1)
with col_B:
    st.markdown("### Boat B")
    config_B = render_boat_config("race_B", default_index=0)

# --- Environment ---
st.subheader("Environment")
env_col1, env_col2 = st.columns(2)
with env_col1:
    race_tws = st.slider("True wind speed (knots)", 4.0, 25.0, 10.0, step=1.0,
                          key="race_tws")
    current_speed = st.slider("Current speed (knots)", 0.0, 3.0, 0.0, step=0.1,
                              key="race_current_speed",
                              help="Constant current applied to both boats.")
with env_col2:
    current_dir = st.slider("Current direction (degrees, 0 = upwind)", 0.0, 360.0, 0.0,
                            step=5.0, key="race_current_dir")

# --- Race parameters ---
st.subheader("Race parameters")
race_col1, race_col2, race_col3 = st.columns(3)
with race_col1:
    leg_distance = st.slider("Leg distance (NM)", 0.3, 3.0, 1.0, step=0.1,
                             key="race_leg_dist")
    n_legs = st.selectbox("Up/down leg pairs", [1, 2, 3], index=0,
                          key="race_n_legs")
with race_col2:
    tack_penalty = st.slider("Tack penalty (s)", 3.0, 20.0, 10.0, step=1.0,
                             key="race_tack_penalty",
                             help="Time the boat is stationary during a tack.")
    gybe_penalty = st.slider("Gybe penalty (s)", 2.0, 15.0, 6.0, step=1.0,
                             key="race_gybe_penalty")
with race_col3:
    n_runs = st.selectbox("Monte Carlo runs", [50, 100, 200, 500], index=1,
                          key="race_n_runs")

# --- Wind model ---
st.subheader("Wind model")
with st.popover("ℹ️ Wind model parameters"):
    st.markdown(
        "**Wind shift sigma** controls how much the wind direction wanders. "
        "2 deg/sqrt(min) is typical for a sea breeze. Higher values mean more "
        "tactical variability. **TWS sigma** varies the wind speed around the "
        "mean (0 = constant speed)."
    )
wind_col1, wind_col2 = st.columns(2)
with wind_col1:
    wind_sigma = st.slider("Wind shift sigma (deg/sqrt(min))", 0.0, 8.0, 2.0,
                           step=0.5, key="race_wind_sigma")
    tws_sigma = st.slider("TWS sigma (kts/sqrt(min))", 0.0, 3.0, 0.0,
                          step=0.1, key="race_tws_sigma",
                          help="0 = constant wind speed. >0 adds speed variation.")
with wind_col2:
    dir_reversion = st.slider("Direction mean-reversion (1/min)", 0.0, 1.0, 0.05,
                              step=0.01, key="race_dir_reversion",
                              help="How quickly wind direction returns to mean. 0 = pure random walk.")
    tws_reversion = st.slider("TWS mean-reversion (1/min)", 0.0, 1.0, 0.1,
                              step=0.01, key="race_tws_reversion")

# --- Stochastic effects ---
st.subheader("Stochastic effects")
with st.popover("ℹ️ Stochastic effects"):
    st.markdown(
        "**Trim noise** simulates imperfect sail trim — each boat gets random "
        "speed variations each second. **Penalty std** makes tack/gybe times "
        "variable (better crews are more consistent)."
    )
stoch_col1, stoch_col2 = st.columns(2)
with stoch_col1:
    trim_sigma = st.slider("Trim noise (fractional std)", 0.00, 0.10, 0.00,
                           step=0.01, key="race_trim_sigma",
                           help="0 = perfect trim. 0.03 = 3% speed noise.")
with stoch_col2:
    tack_penalty_std = st.slider("Tack penalty std (s)", 0.0, 5.0, 0.0,
                                 step=0.5, key="race_tack_std")
    gybe_penalty_std = st.slider("Gybe penalty std (s)", 0.0, 5.0, 0.0,
                                 step=0.5, key="race_gybe_std")

# --- Solver settings ---
with st.expander("Solver settings (for computing polars)"):
    solver_method = render_solver_method(key_prefix="race")
    data_source = render_data_source(key_prefix="race")

# --- Run ---
if st.button("Race!", type="primary"):
    # TWA/TWS range for polar computation (if needed)
    tws_range = np.arange(4.0, 22.0, 2.0).tolist()
    twa_range = np.linspace(28.0, 180.0, 39).tolist()

    with st.spinner("Computing polars for Boat A..."):
        polar_A, name_A = get_or_compute_polar(
            copy.deepcopy(config_A), tws_range, twa_range, solver_method, data_source)
    if polar_A is None:
        st.error("Failed to compute polars for Boat A.")
        st.stop()

    with st.spinner("Computing polars for Boat B..."):
        polar_B, name_B = get_or_compute_polar(
            copy.deepcopy(config_B), tws_range, twa_range, solver_method, data_source)
    if polar_B is None:
        st.error("Failed to compute polars for Boat B.")
        st.stop()

    # Build wind model
    if tws_sigma > 0 or dir_reversion > 0:
        wind_model = MeanRevertingWind(
            tws=race_tws, dir_sigma=wind_sigma,
            dir_reversion=dir_reversion,
            tws_sigma=tws_sigma, tws_reversion=tws_reversion,
        )
    elif wind_sigma > 0:
        wind_model = BrownianWind(tws=race_tws, dir_sigma=wind_sigma)
    else:
        wind_model = ConstantWind(tws=race_tws)

    race = Race(
        polar_A, polar_B, tws=race_tws,
        leg_distance=leg_distance, n_legs=n_legs,
        tack_penalty=tack_penalty, gybe_penalty=gybe_penalty,
        wind_model=wind_model,
        current_speed=current_speed, current_dir=current_dir,
        trim_sigma=trim_sigma,
        tack_penalty_std=tack_penalty_std,
        gybe_penalty_std=gybe_penalty_std,
    )

    with st.spinner(f"Running {n_runs} races..."):
        mc = race.run_monte_carlo(n_runs=n_runs)

    # Results
    st.subheader("Results")

    # Win probability bar
    st.markdown("#### Win probability")
    fig_win = plot_win_probability(mc, name_A, name_B)
    st.pyplot(fig_win)

    # Mean delta
    ci = 1.96 * np.std(mc["deltas"]) / np.sqrt(len(mc["deltas"]))
    st.metric(
        "Mean time delta",
        f"{mc['mean_delta']:.1f}s",
        delta=f"95% CI: ±{ci:.1f}s",
    )

    # Histogram and trace side by side
    res_col1, res_col2 = st.columns(2)
    with res_col1:
        st.markdown("#### Time delta distribution")
        fig_hist = plot_delta_histogram(mc, name_A, name_B)
        st.pyplot(fig_hist)
    with res_col2:
        st.markdown("#### Example race trace")
        fig_trace = plot_course_trace(mc, name_A, name_B)
        st.pyplot(fig_trace)

    # Stats table
    with st.expander("Race statistics"):
        stats = build_race_stats_table(mc, name_A, name_B)
        st.dataframe(stats, use_container_width=True)

footer()
