import json
import logging
import os
import sys
from typing import Dict, List, Tuple

import numpy as np
import streamlit as st
import streamlit.components.v1 as components
import subprocess

sys.path.append(os.path.realpath("."))
from src.api import app

def get_git_hash():
    try:
        git_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).strip().decode('utf-8')
        return git_hash
    except subprocess.CalledProcessError:
        return None


def header():
    header = """
    <script>
        window.goatcounter = {no_onload: true}

        window.addEventListener('hashchange', function(e) {
            window.goatcounter.count({
                path: location.pathname + location.search + location.hash,
            })
        })
    </script>
    <script data-goatcounter="https://yacht-vpp.goatcounter.com/count"
            async src="//gc.zgo.at/count.js"></script>
    """
    return components.html(header)


FIN_KEEL_DEFAULTS = {"Cu": 1.00, "Cl": 0.78, "Span": 1.90}
SHORT_KEEL_DEFAULTS = {"Length": 1.2, "Depth": 0.90, "Tc_ratio": 0.15}


def render_keel_inputs(keel: dict, key_prefix: str = "") -> dict:
    """Render keel type selector and matching parameter inputs.

    Pops the ``type`` key from *keel*, shows a selectbox, then renders
    only the fields appropriate for that keel type.  Returns a new dict
    with the selected type and parameter values.
    """
    keel_type = keel.pop("type", "fin")
    keel_type = st.selectbox(
        "Keel type",
        ["fin", "short"],
        index=["fin", "short"].index(keel_type),
        key=f"{key_prefix}_keel_type",
    )
    defaults = SHORT_KEEL_DEFAULTS if keel_type == "short" else FIN_KEEL_DEFAULTS
    result = {}
    for field, default in defaults.items():
        input_key = f"{key_prefix}_keel_{field}"
        result[field] = st.text_input(field_label(field), keel.get(field, default), key=input_key, help=FIELD_HELP.get(field, ""))
    result["type"] = keel_type
    return result


def render_solver_method(key_prefix: str = "") -> str:
    """Render solver method selectbox, return selected method string."""
    return st.selectbox(
        "Solver method",
        ["iterative", "5dof"],
        index=0,
        key=f"{key_prefix}_solver_method",
        help="'iterative' = 3-DOF with depowering loop; '5dof' = scipy SLSQP 5-DOF optimizer",
    )


def render_data_source(key_prefix: str = "") -> str:
    """Render data source selectbox, return selected data source string."""
    return st.selectbox(
        "Sail coefficient data source",
        ["orc"],
        index=0,
        key=f"{key_prefix}_data_source",
        help="Coefficient data directory under dat/",
    )


FIELD_HELP = {
    # Yacht hull
    "Name": "Yacht design name (label only).",
    "Lwl": "Waterline length (m). Longer = faster hull speed.",
    "Vol": "Displaced volume of the canoe body (m³).",
    "Bwl": "Waterline beam (m). Wider = more initial stability.",
    "Tc": "Canoe body draft (m). Depth of hull excluding keel.",
    "WSA": "Wetted surface area of the canoe body (m²). Drives viscous drag.",
    "Tmax": "Maximum draft including keel (m).",
    "Amax": "Maximum cross-section area (m²).",
    "Mass": "Total displacement mass including keel (kg).",
    "Ff": "Freeboard height at the bow (m).",
    "Fa": "Freeboard height at the stern (m).",
    "Boa": "Beam overall (m).",
    "Loa": "Length overall (m).",
    # Fin keel
    "Cu": "Root (upper) chord length (m).",
    "Cl": "Tip (lower) chord length (m).",
    "Span": "Appendage span / depth (m).",
    # Short keel
    "Length": "Fore-aft keel length along hull bottom (m).",
    "Depth": "Keel depth below canoe body (m).",
    "Tc_ratio": "Thickness-to-chord ratio (e.g. 0.15 = 15%).",
    # Main sail
    "P": "Luff length / mast height above boom (m).",
    "E": "Foot length along the boom (m).",
    "Roach": "Sail roach as fraction of triangle area (0.0–0.3).",
    "BAD": "Boom above deck height (m).",
    # Jib
    "I": "Forestay height above deck (m).",
    "J": "Base of foretriangle — mast to forestay at deck (m).",
    "LPG": "Longest perpendicular of genoa/jib (m). Larger = more overlap.",
    "HBI": "Height of jib tack above deck (m).",
    # Kite
    "area": "Spinnaker sail area (m²).",
    "vce": "Vertical centre of effort above deck (m).",
}

FIELD_LABELS = {
    # Yacht hull
    "Name": "Name",
    "Lwl": r"$L_{wl}$ (m)",
    "Vol": r"$\nabla$ (m³)",
    "Bwl": r"$B_{wl}$ (m)",
    "Tc": r"$T_c$ (m)",
    "WSA": r"$S_{wet}$ (m²)",
    "Tmax": r"$T_{max}$ (m)",
    "Amax": r"$A_{max}$ (m²)",
    "Mass": r"$\Delta m$ (kg)",
    "Ff": r"$F_f$ (m)",
    "Fa": r"$F_a$ (m)",
    "Boa": r"$B_{oa}$ (m)",
    "Loa": r"$L_{oa}$ (m)",
    # Fin keel
    "Cu": r"$C_u$ (m)",
    "Cl": r"$C_l$ (m)",
    "Span": r"$b$ (m)",
    # Short keel
    "Length": r"$L_{keel}$ (m)",
    "Depth": r"$D_{keel}$ (m)",
    "Tc_ratio": r"$t/c$",
    # Main sail
    "P": r"$P$ (m)",
    "E": r"$E$ (m)",
    "Roach": "Roach",
    "BAD": r"$BAD$ (m)",
    # Jib
    "I": r"$I$ (m)",
    "J": r"$J$ (m)",
    "LPG": r"$LPG$ (m)",
    "HBI": r"$HBI$ (m)",
    # Kite
    "area": r"$A_{kite}$ (m²)",
    "vce": r"$VCE$ (m)",
}


def field_label(key: str) -> str:
    """Return the mathematical display label for a field, falling back to the key."""
    return FIELD_LABELS.get(key, key)


MAIN_SAIL_TYPES = ["main", "main_low"]
JIB_SAIL_TYPES = ["jib", "jib_low"]
KITE_SAIL_TYPES = ["kite", "sym_kite", "asym_cl_kite", "asym_pole_kite"]

SAIL_TYPE_HELP = {
    "main": "ORC high-performance mainsail",
    "main_low": "ORC low-performance mainsail (lower CL)",
    "jib": "ORC high-performance jib",
    "jib_low": "ORC low-performance jib (lower CL)",
    "kite": "Default asymmetric spinnaker",
    "sym_kite": "ORC symmetric spinnaker (higher CL)",
    "asym_cl_kite": "ORC asymmetric spinnaker, centerline tack",
    "asym_pole_kite": "ORC asymmetric spinnaker, pole tack",
}


def render_sail_type(label: str, options: list, key_prefix: str = "") -> str:
    """Render a sail type selectbox and return the selected type."""
    return st.selectbox(
        f"{label} type",
        options,
        index=0,
        key=f"{key_prefix}_sail_type",
        help=", ".join(f"{o}: {SAIL_TYPE_HELP[o]}" for o in options),
    )


def run_vpp(
    config: Dict,
    tws_range: List[float],
    twa_range: List[float],
    method: str = "iterative",
    data_source: str = "orc",
    sail_types: Dict[str, str] = None,
    env_params: Dict = None,
):
    """Post a yacht configuration to the VPP API and return the response.

    Parameters
    ----------
    sail_types : dict, optional
        Mapping of sail section to sail_type, e.g.
        ``{"main": "main_low", "jib": "jib", "kite": "sym_kite"}``.
    env_params : dict, optional
        Environment parameters (roughness, Hs, Ts).
    """
    data = _build_vpp_data(config, tws_range, twa_range, method, data_source, sail_types, env_params)
    logging.info("Starting VPP simulation")
    json_string = json.dumps(data)
    headers = {"content-type": "application/json", "Accept-Charset": "UTF-8"}
    client = app.test_client()
    response = client.post("/api/vpp/", data=json_string, headers=headers)
    logging.info("VPP simulation completed")
    return response


def _build_vpp_data(
    config: Dict,
    tws_range: List[float],
    twa_range: List[float],
    method: str = "iterative",
    data_source: str = "orc",
    sail_types: Dict[str, str] = None,
    env_params: Dict = None,
) -> Dict:
    """Build the VPP request data dict from a config."""
    main = dict(config["main"])
    jib = dict(config["jib"])
    kite = dict(config["kite"])
    if sail_types:
        if "main" in sail_types:
            main["sail_type"] = sail_types["main"]
        if "jib" in sail_types:
            jib["sail_type"] = sail_types["jib"]
        if "kite" in sail_types:
            kite["sail_type"] = sail_types["kite"]
    data = {
        "name": config["yacht"]["Name"],
        "yacht": config["yacht"],
        "keel": config["keel"],
        "rudder": config["rudder"],
        "main": main,
        "jib": jib,
        "kite": kite,
        "tws_range": tws_range,
        "twa_range": twa_range,
        "method": method,
        "data_source": data_source,
    }
    if env_params:
        data.update(env_params)
    return data


def run_vpp_direct(
    config: Dict,
    tws_range: List[float],
    twa_range: List[float],
    method: str = "iterative",
    data_source: str = "orc",
    sail_types: Dict[str, str] = None,
    env_params: Dict = None,
):
    """Run VPP directly (bypassing Flask).

    Returns (result_dict, error_string). result_dict has keys:
    name, tws, twa, sails, results. On error, result_dict is None.
    """
    from src.api import data_to_vpp

    data = _build_vpp_data(config, tws_range, twa_range, method, data_source, sail_types, env_params)

    try:
        vpp, method = data_to_vpp(data)
    except (KeyError, TypeError, ValueError) as e:
        logging.warning("Invalid VPP input: %s", e)
        return None, str(e)

    try:
        vpp.run(verbose=True, method=method)
    except Exception as e:
        logging.exception("VPP simulation failed")
        return None, str(e)

    return vpp.results(), None


def render_roughness_input(key_prefix: str = "") -> float:
    """Render hull roughness number input. Returns roughness in metres."""
    roughness_um = st.number_input(
        r"Hull roughness $k_s$ ($\mu m$)",
        min_value=0,
        max_value=1000,
        value=150,
        step=10,
        key=f"{key_prefix}_roughness",
        help=(
            "Mean hull roughness height in micrometres. "
            "Typical values: **0** = hydraulically smooth, "
            "**50** = racing finish, "
            "**150** = new antifouling paint, "
            "**300** = 1-year fouled hull, "
            "**500+** = heavily fouled."
        ),
    )
    return roughness_um * 1e-6


def render_environment_inputs(key_prefix: str = "") -> Tuple[List[float], List[float], Dict]:
    """Render TWA/TWS/wave sliders.

    Returns (tws_range, twa_range, env_params) where env_params is a dict
    with keys ``Hs``, ``Ts``.
    """
    st.subheader("Environment")
    twa_slider = st.slider(
        r"True wind angle $\theta_{tw}$ (TWA) range",
        35.0, 175.0, (35.0, 175.0), step=1.0,
        key=f"{key_prefix}_twa",
    )
    twa_range = np.arange(twa_slider[0], twa_slider[1], 1.0).tolist()

    tws_slider = st.slider(
        r"True wind speed $V_{tw}$ (TWS) range",
        2.0, 25.0, (8.0, 12.0), step=1.0,
        key=f"{key_prefix}_tws",
    )
    tws_range = np.arange(tws_slider[0], tws_slider[1], 1.0).tolist()

    Hs = st.slider(
        r"Significant wave height $H_s$ (m)",
        0.0, 3.0, 0.0, step=0.1,
        key=f"{key_prefix}_Hs",
        help="Wave height. 0 = flat water. Typical coastal: 0.5–1.5 m.",
    )

    Ts = st.slider(
        r"Modal wave period $T_s$ (s)",
        0.0, 12.0, 0.0 if Hs == 0 else 5.0, step=0.5,
        key=f"{key_prefix}_Ts",
        help="Peak wave period. Typical: 4–8 s for wind waves, 8–12 s for swell.",
    )

    env_params = {
        "Hs": Hs,
        "Ts": Ts,
    }
    return tws_range, twa_range, env_params


def validate_ranges(tws_range: List[float], twa_range: List[float]) -> bool:
    """Show error messages if ranges are empty. Returns True if valid."""
    if not tws_range:
        st.error("TWS range is empty. Make sure the min and max wind speeds are not equal.")
        return False
    if not twa_range:
        st.error("TWA range is empty. Make sure the min and max wind angles are not equal.")
        return False
    return True


def footer():
    git_hash = get_git_hash()
    footer = f"""
        <div style="text-align: center; margin-top: 50px;">
            <hr>
            <p>Yacht VPP</p>
            <p style="font-size: 12px; color: gray;">
                This application is provided as is and without warranty. 
                The source code is available on <a href="https://github.com/marinlauber/Python-VPP">GitHub</a>.
                Please file bug reports as an <a href="https://github.com/marinlauber/Python-VPP/issues">issue here</a>.
            </p>
            <p style="font-size: 12px; color: gray;">Version {git_hash}</p>
        </div>
    """

    return st.markdown(footer, unsafe_allow_html=True)
