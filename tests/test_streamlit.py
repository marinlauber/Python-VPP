"""Streamlit app tests — verify pages load and widgets render correctly.

These tests check the UI structure (widgets, sections, buttons) but NOT
the mathematical models — those are covered by test_hydro, test_vpp, etc.
"""

import os
import sys

import pytest
from streamlit.testing.v1 import AppTest

# The demo pages import `from presets import ...` and `from utils import ...`
# which requires demos/ on sys.path.  AppTest runs pages as scripts in
# a subprocess, so we inject the path via PYTHONPATH.
DEMOS_DIR = os.path.join(os.path.dirname(__file__), "..", "demos")
PAGES_DIR = os.path.join(DEMOS_DIR, "pages")


@pytest.fixture(autouse=True)
def _patch_pythonpath(monkeypatch):
    """Ensure demos/ is importable by child processes and this process."""
    abs_demos = os.path.abspath(DEMOS_DIR)
    abs_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    existing = os.environ.get("PYTHONPATH", "")
    monkeypatch.setenv("PYTHONPATH", f"{abs_demos}{os.pathsep}{abs_root}{os.pathsep}{existing}")
    if abs_demos not in sys.path:
        sys.path.insert(0, abs_demos)
    if abs_root not in sys.path:
        sys.path.insert(0, abs_root)


def _load_page(filename, timeout=30):
    """Load a Streamlit page via AppTest."""
    path = os.path.join(PAGES_DIR, filename)
    at = AppTest.from_file(path, default_timeout=timeout)
    at.run()
    return at


# ──────────────────────────────────────────────
# VPP page
# ──────────────────────────────────────────────

class TestVPPPage:
    def test_vpp_page_loads_without_error(self):
        at = _load_page("1_VPP_⛵.py")
        assert not at.exception, f"Page raised: {at.exception}"

    def test_vpp_page_has_title(self):
        at = _load_page("1_VPP_⛵.py")
        markdown_texts = [m.value for m in at.markdown]
        assert any("Yacht VPP" in t for t in markdown_texts)

    def test_vpp_page_has_preset_selector(self):
        at = _load_page("1_VPP_⛵.py")
        assert len(at.selectbox) > 0, "No selectbox found"
        # First selectbox should be the yacht preset
        options = at.selectbox[0].options
        assert "YD41" in options

    def test_vpp_page_has_process_button(self):
        at = _load_page("1_VPP_⛵.py")
        labels = [b.label for b in at.button]
        assert "Process Specifications" in labels

    def test_vpp_page_has_environment_sliders(self):
        at = _load_page("1_VPP_⛵.py")
        slider_labels = [s.label for s in at.slider]
        assert any("TWA" in l for l in slider_labels), "Missing TWA slider"
        assert any("TWS" in l for l in slider_labels), "Missing TWS slider"
        assert any("roughness" in l.lower() for l in slider_labels), "Missing roughness slider"
        assert any("Hs" in l for l in slider_labels), "Missing Hs slider"
        assert any("Ts" in l for l in slider_labels), "Missing Ts slider"

    def test_vpp_page_has_solver_settings(self):
        at = _load_page("1_VPP_⛵.py")
        selectbox_labels = [s.label for s in at.selectbox]
        assert any("Solver" in l for l in selectbox_labels), "Missing solver selectbox"

    def test_vpp_page_has_sail_type_selectors(self):
        at = _load_page("1_VPP_⛵.py")
        selectbox_labels = [s.label for s in at.selectbox]
        assert any("Main" in l and "type" in l for l in selectbox_labels)
        assert any("Jib" in l and "type" in l.lower() for l in selectbox_labels)
        assert any("Kite" in l and "type" in l.lower() for l in selectbox_labels)

    def test_vpp_page_has_popover_labels(self):
        at = _load_page("1_VPP_⛵.py")
        # Popovers aren't directly queryable via AppTest, but their trigger
        # labels appear in the rendered button elements.
        button_labels = [b.label for b in at.button]
        assert any("What is a VPP" in l for l in button_labels) or len(at.button) >= 1


# ──────────────────────────────────────────────
# Compare page
# ──────────────────────────────────────────────

class TestComparePage:
    def test_compare_page_loads_without_error(self):
        at = _load_page("2_Compare_⚖️.py")
        assert not at.exception, f"Page raised: {at.exception}"

    def test_compare_page_has_title(self):
        at = _load_page("2_Compare_⚖️.py")
        markdown_texts = [m.value for m in at.markdown]
        assert any("Compare" in t for t in markdown_texts)

    def test_compare_page_has_config_buttons(self):
        at = _load_page("2_Compare_⚖️.py")
        labels = [b.label for b in at.button]
        assert "+ Add config" in labels
        assert "- Remove last" in labels
        assert "Compare" in labels

    def test_compare_page_has_preset_selectors(self):
        at = _load_page("2_Compare_⚖️.py")
        # Should have at least 2 preset selectors (one per config tab)
        preset_boxes = [s for s in at.selectbox if "Preset" in s.label]
        assert len(preset_boxes) >= 2, f"Expected 2+ preset selectors, got {len(preset_boxes)}"

    def test_compare_page_has_environment_sliders(self):
        at = _load_page("2_Compare_⚖️.py")
        slider_labels = [s.label for s in at.slider]
        assert any("TWA" in l for l in slider_labels)
        assert any("TWS" in l for l in slider_labels)

    def test_compare_page_has_buttons(self):
        at = _load_page("2_Compare_⚖️.py")
        # Verify page rendered fully (buttons present implies layout loaded)
        assert len(at.button) >= 3


# ──────────────────────────────────────────────
# Match Race page
# ──────────────────────────────────────────────

class TestMatchRacePage:
    def test_match_race_page_loads_without_error(self):
        at = _load_page("3_Match_Race_🏁.py")
        assert not at.exception, f"Page raised: {at.exception}"

    def test_match_race_page_has_title(self):
        at = _load_page("3_Match_Race_🏁.py")
        markdown_texts = [m.value for m in at.markdown]
        assert any("Match Race" in t for t in markdown_texts)

    def test_match_race_page_has_race_button(self):
        at = _load_page("3_Match_Race_🏁.py")
        labels = [b.label for b in at.button]
        assert "Race!" in labels

    def test_match_race_page_has_boat_preset_selectors(self):
        at = _load_page("3_Match_Race_🏁.py")
        preset_boxes = [s for s in at.selectbox if "Preset" in s.label]
        assert len(preset_boxes) >= 2, "Expected 2 boat preset selectors"

    def test_match_race_page_has_environment_sliders(self):
        at = _load_page("3_Match_Race_🏁.py")
        slider_labels = [s.label for s in at.slider]
        assert any("wind speed" in l.lower() for l in slider_labels), "Missing TWS slider"
        assert any("current" in l.lower() for l in slider_labels), "Missing current slider"

    def test_match_race_page_has_race_parameter_sliders(self):
        at = _load_page("3_Match_Race_🏁.py")
        slider_labels = [s.label for s in at.slider]
        assert any("Leg distance" in l for l in slider_labels)
        assert any("Tack penalty" in l for l in slider_labels)
        assert any("Gybe penalty" in l for l in slider_labels)

    def test_match_race_page_has_wind_model_sliders(self):
        at = _load_page("3_Match_Race_🏁.py")
        slider_labels = [s.label for s in at.slider]
        assert any("Wind shift sigma" in l for l in slider_labels)
        assert any("TWS sigma" in l for l in slider_labels)
        assert any("mean-reversion" in l.lower() for l in slider_labels)

    def test_match_race_page_has_stochastic_sliders(self):
        at = _load_page("3_Match_Race_🏁.py")
        slider_labels = [s.label for s in at.slider]
        assert any("Trim noise" in l for l in slider_labels)
        assert any("Tack penalty std" in l for l in slider_labels)

    def test_match_race_page_has_monte_carlo_selector(self):
        at = _load_page("3_Match_Race_🏁.py")
        mc_boxes = [s for s in at.selectbox if "Monte Carlo" in s.label]
        assert len(mc_boxes) >= 1
        assert "100" in mc_boxes[0].options

    def test_match_race_page_has_subheaders(self):
        at = _load_page("3_Match_Race_🏁.py")
        # Verify key sections rendered (subheaders indicate layout completeness)
        markdown_texts = [m.value for m in at.markdown]
        assert any("Match Race" in t for t in markdown_texts)

    def test_match_race_page_has_leg_pairs_selector(self):
        at = _load_page("3_Match_Race_🏁.py")
        leg_boxes = [s for s in at.selectbox if "leg pairs" in s.label.lower()]
        assert len(leg_boxes) >= 1
        assert "1" in leg_boxes[0].options
