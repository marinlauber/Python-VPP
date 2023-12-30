import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def app_test_instance():
    app_test = AppTest.from_file("pages/1_VPP_⛵.py").run()
    return app_test


def test_app_run(app_test_instance):
    assert not app_test_instance.exception


def test_vpp_simulation(app_test_instance):
    app_test_instance.slider[0].set_range(40.0, 44.0)
    app_test_instance.slider[1].set_range(8.0, 10.0)
    app_test_instance.button[0].set_value(True).run()
