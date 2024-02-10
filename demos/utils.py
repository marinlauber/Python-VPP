import streamlit as st
import streamlit.components.v1 as components


def header():
    header = """
    <script>
        // Make sure this is *before* you load the count.js script; otherwise
        // the pageview may get sent before this is loaded and this will just
        // overwrite the object.
        window.goatcounter = {allow_local: true}
    </script>
    <script data-goatcounter="https://yacht-vpp.goatcounter.com/count"
            async src="//gc.zgo.at/count.js"></script>
    """
    return components.html(header)


def footer():
    footer = """
        <div style="text-align: center; margin-top: 50px;">
            <hr>
            <p>Yacht VPP</p>
            <p>Contact: <a href="mailto:tajdickson@protonmail.com">tajdickson@protonmail.com</a></p>
            <p style="font-size: 12px; color: gray;">
                This application is provided as is and without warranty. The source code is available on <a href="https://github.com/marinlauber/Python-VPP">GitHub</a>.
                Please file bug reports as an <a href="https://github.com/marinlauber/Python-VPP/issues">issue here</a>.
            </p>
        </div>
    """

    return st.markdown(footer, unsafe_allow_html=True)
