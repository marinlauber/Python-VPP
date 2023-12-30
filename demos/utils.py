import streamlit as st


def return_footer():
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
