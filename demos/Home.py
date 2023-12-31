import streamlit as st
from utils import return_footer

st.set_page_config(
    page_title="Home - Yacht VPP",
    page_icon="👋",
)

st.write("# Welcome to Yacht VPP 👋")

st.markdown(
    """
    This is a 3 degree of freedom Yacht [velocity prediction program](https://en.wikipedia.org/wiki/Velocity_prediction_program) (3 D.O.F. Yacht VPP).

    It is based on the [ORC model](https://orc.org/uploads/files/ORC-VPP-Documentation-2023.pdf).

    The source code can be [found here](https://github.com/marinlauber/Python-VPP) and any and all contributions are welcome 😊.

    If you have a question, feature request or perhaps a bug report then please open an issue here or [send me an email](mailto:tajdickson@protonmail.com).
"""
)

return_footer()
