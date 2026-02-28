import json

import numpy as np

from src.api import app

HEADERS = {"content-type": "application/json", "Accept-Charset": "UTF-8"}


def test_ping_route():
    client = app.test_client()
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Pong! The server is up and running."


def make_yd41(**overrides):
    yacht = {
        "Name": "YD41",
        "Lwl": 11.90,
        "Vol": 6.05,
        "Bwl": 3.18,
        "Tc": 0.4,
        "WSA": 28.20,
        "Tmax": 2.30,
        "Amax": 1.051,
        "Mass": 6500,
        "Ff": 1.5,
        "Fa": 1.5,
        "Boa": 4.2,
        "Loa": 12.5,
    }
    keel = {"Cu": 1.00, "Cl": 0.78, "Span": 1.90}
    rudder = {"Cu": 0.48, "Cl": 0.22, "Span": 1.15}
    main = {"Name": "MN1", "P": 16.60, "E": 5.60, "Roach": 0.1, "BAD": 1.0}
    jib = {"Name": "J1", "I": 16.20, "J": 5.10, "LPG": 5.40, "HBI": 1.8}
    kite = {"Name": "A2", "area": 150.0, "vce": 9.55}
    tws_range = np.arange(4.0, 7.0, 2.0).tolist()
    twa_range = np.linspace(30.0, 180.0, 5).tolist()

    d = {
        "name": yacht["Name"],
        "yacht": yacht,
        "keel": keel,
        "rudder": rudder,
        "main": main,
        "jib": jib,
        "kite": kite,
        "tws_range": tws_range,
        "twa_range": twa_range,
    }
    d.update(overrides)
    return d


def post_vpp(data):
    client = app.test_client()
    return client.post("/api/vpp/", data=json.dumps(data), headers=HEADERS)


def test_vpp_simulation():
    d = make_yd41()
    response = post_vpp(d)
    assert response.status_code == 200


def test_empty_tws_range_returns_400():
    d = make_yd41(tws_range=[])
    response = post_vpp(d)
    assert response.status_code == 400
    assert "empty" in response.json["error"].lower()


def test_empty_twa_range_returns_400():
    d = make_yd41(twa_range=[])
    response = post_vpp(d)
    assert response.status_code == 400
    assert "empty" in response.json["error"].lower()


def test_tws_out_of_range_returns_400():
    d = make_yd41(tws_range=[1.0, 5.0])
    response = post_vpp(d)
    assert response.status_code == 400
    assert "outside valid bounds" in response.json["error"]


def test_tws_above_range_returns_400():
    d = make_yd41(tws_range=[10.0, 40.0])
    response = post_vpp(d)
    assert response.status_code == 400
    assert "outside valid bounds" in response.json["error"]


def test_twa_out_of_range_returns_400():
    d = make_yd41(twa_range=[-10.0, 90.0])
    response = post_vpp(d)
    assert response.status_code == 400
    assert "outside valid bounds" in response.json["error"]


def test_missing_field_returns_400():
    d = make_yd41()
    del d["keel"]
    response = post_vpp(d)
    assert response.status_code == 400
    assert "error" in response.json


def test_invalid_json_returns_400():
    client = app.test_client()
    response = client.post("/api/vpp/", data="not json", headers=HEADERS)
    assert response.status_code == 400

