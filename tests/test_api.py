import json

import numpy as np

from src.api import app


def test_ping_route():
    client = app.test_client()
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Pong! The server is up and running."


def test_vpp_route():
    yacht = dict(
        {
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
    )
    keel = dict({"Cu": 1.00, "Cl": 0.78, "Span": 1.90})
    rudder = dict({"Cu": 0.48, "Cl": 0.22, "Span": 1.15})
    main = dict({"Name": "MN1", "P": 16.60, "E": 5.60, "Roach": 0.1, "BAD": 1.0})
    jib = dict({"Name": "J1", "I": 16.20, "J": 5.10, "LPG": 5.40, "HBI": 1.8})
    kite = dict({"Name": "A2", "area": 150.0, "vce": 9.55})
    tws_range = np.array([10.0]).tolist()
    twa_range = [i for i in np.linspace(30.0, 180.0, 5)]
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
    json_string = json.dumps(d)
    headers = {"content-type": "application/json", "Accept-Charset": "UTF-8"}

    client = app.test_client()
    response = client.post("/api/vpp/", data=json_string, headers=headers)

    assert response.status_code == 200
