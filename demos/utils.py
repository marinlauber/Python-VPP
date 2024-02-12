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
