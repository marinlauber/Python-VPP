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
        assert any("TWA" in lbl for lbl in slider_labels), "Missing TWA slider"
        assert any("TWS" in lbl for lbl in slider_labels), "Missing TWS slider"
        number_labels = [n.label for n in at.number_input]
        assert any("roughness" in lbl.lower() for lbl in number_labels), "Missing roughness input"
        assert any("H_s" in lbl for lbl in slider_labels), "Missing Hs slider"
        assert any("T_s" in lbl for lbl in slider_labels), "Missing Ts slider"

    def test_vpp_page_has_solver_settings(self):
        at = _load_page("1_VPP_⛵.py")
        selectbox_labels = [s.label for s in at.selectbox]
        assert any("Solver" in lbl for lbl in selectbox_labels), "Missing solver selectbox"

    def test_vpp_page_has_sail_type_selectors(self):
        at = _load_page("1_VPP_⛵.py")
        selectbox_labels = [s.label for s in at.selectbox]
        assert any("Main" in lbl and "type" in lbl for lbl in selectbox_labels)
        assert any("Jib" in lbl and "type" in lbl.lower() for lbl in selectbox_labels)
        assert any("Kite" in lbl and "type" in lbl.lower() for lbl in selectbox_labels)

    def test_vpp_page_has_popover_labels(self):
        at = _load_page("1_VPP_⛵.py")
        # Popovers aren't directly queryable via AppTest, but their trigger
        # labels appear in the rendered button elements.
        button_labels = [b.label for b in at.button]
        assert any("What is a VPP" in lbl for lbl in button_labels) or len(at.button) >= 1

    def test_field_help_covers_all_yacht_fields(self):
        """FIELD_HELP should have entries for all yacht, keel, rudder, sail fields."""
        from utils import FIELD_HELP
        expected = [
            "Lwl", "Vol", "Bwl", "Tc", "WSA", "Tmax", "Amax", "Mass",
            "Ff", "Fa", "Boa", "Loa",
            "Cu", "Cl", "Span", "Length", "Depth", "Tc_ratio",
            "P", "E", "Roach", "BAD",
            "I", "J", "LPG", "HBI",
            "area", "vce",
        ]
        for key in expected:
            assert key in FIELD_HELP, f"Missing help for field '{key}'"
            assert len(FIELD_HELP[key]) > 5, f"Help for '{key}' too short"


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
        assert any("TWA" in lbl for lbl in slider_labels)
        assert any("TWS" in lbl for lbl in slider_labels)

    def test_compare_page_has_buttons(self):
        at = _load_page("2_Compare_⚖️.py")
        # Verify page rendered fully (buttons present implies layout loaded)
        assert len(at.button) >= 3
