import streamlit as st
from utils import footer, header

st.set_page_config(
    page_title="Home - Yacht VPP",
    page_icon="👋",
)

header()

st.write("# Welcome to Yacht VPP 👋")

st.markdown(
    """
    This is a 3 degree of freedom Yacht [velocity prediction program](https://en.wikipedia.org/wiki/Velocity_prediction_program) (3 D.O.F. Yacht VPP).

    It is based on the [ORC model](https://orc.org/uploads/files/ORC-VPP-Documentation-2023.pdf).

    If you have a question, feature request or perhaps a bug report then please open an issue [here](https://github.com/marinlauber/Python-VPP) or [send me an email](mailto:tajdickson@protonmail.com).
"""
)

footer()
