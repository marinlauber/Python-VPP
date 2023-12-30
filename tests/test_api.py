import io
import json
import os
import tempfile
import zipfile

import numpy as np
import pytest
from PIL import Image

from src.api import app


def test_ping_route():
    client = app.test_client()
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.data.decode("utf-8") == "Pong! The server is up and running."


def make_yd41():
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
    return d


def test_vpp_simulation():
    d = make_yd41()

    json_string = json.dumps(d)
    headers = {"content-type": "application/json", "Accept-Charset": "UTF-8"}

    client = app.test_client()
    response = client.post("/api/vpp/", data=json_string, headers=headers)

    assert response.status_code == 200


def check_image_file(image_path):
    assert os.path.isfile(image_path), f"Image file not found: {image_path}"

    try:
        with Image.open(image_path) as img:
            assert img.width > 0, "Image width is not greater than 0"
            assert img.height > 0, "Image height is not greater than 0"

    except Exception as e:
        pytest.fail(f"Failed to load the image: {e}")


def test_vpp_graphs():
    d = make_yd41()

    json_string = json.dumps(d)
    headers = {"content-type": "application/json", "Accept-Charset": "UTF-8"}

    client = app.test_client()
    response = client.post("/api/vpp/plots", data=json_string, headers=headers)

    assert response.status_code == 200

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_content = io.BytesIO(response.data)

        with zipfile.ZipFile(zip_content, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        polars_path = os.path.join(temp_dir, "polars.png")
        check_image_file(polars_path)

        sailchart_path = os.path.join(temp_dir, "sail_chart.png")
        check_image_file(sailchart_path)
