from streamlit.testing.v1 import AppTest

def test_app_run():
    at = AppTest.from_file("vpp.py").run()
    assert not at.exception
        

def test_vpp_simulation():
    at = AppTest.from_file("vpp.py").run()
    at.slider[0].set_range(40.0, 44.0)
    at.slider[1].set_range(8.0, 10.0)
    at.button[0].set_value(True).run()