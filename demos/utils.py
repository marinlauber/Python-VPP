import streamlit as st
import streamlit.components.v1 as components
import subprocess

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
        result[field] = st.text_input(f"{field}:", keel.get(field, default), key=input_key)
    result["type"] = keel_type
    return result


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
