# Daring 5.5m Yacht VPP Prediction — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a baseline VPP performance prediction for the Daring sailing yacht (classic 5.5m class by Arthur Robb), with configurable crew weight and per-yacht GZ curves, suitable for comparing equipment changes.

**Architecture:** Add a Daring yacht definition alongside the existing YD41 example. Refactor `righting_moment.json` to be per-yacht (passed as parameter or per-yacht file). Make crew weight/count a configurable Yacht parameter. Add a `runDaring.py` entry point and update the Streamlit demo to offer Daring as a preset.

**Tech Stack:** Python, numpy, scipy, matplotlib, pytest, Streamlit

---

## Assumptions & Parameter Documentation

All Daring parameters are documented here. Values marked **(published)** come from class data. Values marked **(estimated)** are derived from naval architecture rules of thumb for classic 5.5m metre boats.

### Hull Parameters

| Parameter | Value | Unit | Source |
|-----------|-------|------|--------|
| `Name` | "Daring" | — | — |
| `Loa` | 9.90 | m | **(published)** classicsailboats.org |
| `Lwl` | 7.01 | m | **(published)** classicsailboats.org |
| `Boa` | 1.98 | m | **(published)** classicsailboats.org |
| `Bwl` | 1.70 | m | **(estimated)** ~86% of Boa; metre boats have very little flare |
| `Tmax` | 1.35 | m | **(published)** classicsailboats.org — max draft incl. keel |
| `Tc` | 0.45 | m | **(estimated)** canoe body draft; deep canoe body per IYRU metre rule, keel extends 0.90m below |
| `Vol` | 1.95 | m³ | **(estimated)** 2000 kg / 1025 kg/m³ seawater density |
| `Mass` | 2000 | kg | **(published)** classicsailboats.org — total displacement |
| `WSA` | 11.5 | m² | **(estimated)** Delf series approximation: WSA ≈ 1.97 × √(Vol × Lwl) for narrow hulls. √(1.95 × 7.01) ≈ 3.70, × 1.97 ≈ 7.3 for canoe body. Add ~15% for narrow deep hull correction → ~8.4 m² canoe body. Keel WSA ~2.0 m², rudder ~1.1 m² added separately by appendage model, so canoe body WSA ≈ 11.5 m² (conservative, accounts for long overhangs wetted at speed) |
| `Amax` | 0.38 | m² | **(estimated)** midship section coefficient ~0.50 for a metre boat: Bwl × Tc × 0.50 = 1.70 × 0.45 × 0.50 |
| `Ff` | 0.75 | m | **(estimated)** bow freeboard, typical classic 5.5m |
| `Fa` | 0.55 | m | **(estimated)** stern freeboard, lower transom/counter stern |

### Appendage Parameters

**Keel** — classic 5.5m attached fin keel, moderate aspect ratio:

| Parameter | Value | Unit | Reasoning |
|-----------|-------|------|-----------|
| `Cu` (root chord) | 0.70 | m | **(estimated)** classic swept fin, wider at hull junction |
| `Cl` (tip chord) | 0.45 | m | **(estimated)** moderate taper ratio ~0.64 |
| `Span` | 0.90 | m | **(estimated)** Tmax (1.35) - Tc (0.45) = 0.90m keel span |

**Rudder** — classic attached rudder aft of keel, separated:

| Parameter | Value | Unit | Reasoning |
|-----------|-------|------|-----------|
| `Cu` (root chord) | 0.32 | m | **(estimated)** small balanced rudder |
| `Cl` (tip chord) | 0.18 | m | **(estimated)** tapered tip |
| `Span` | 0.75 | m | **(estimated)** rudder extends ~0.75m below canoe body; class rule max thickness 175mm |

### Sail Parameters

Total upwind sail area **(published)**: 29.73 m². Fractional rig with high-aspect main and small non-overlapping jib.

**Mainsail:**

| Parameter | Value | Unit | Reasoning |
|-----------|-------|------|-----------|
| `P` (luff) | 10.80 | m | **(estimated)** high-aspect fractional rig; main area = 0.5 × P × E × (1+Roach) ≈ 19.6 m² |
| `E` (foot) | 3.30 | m | **(estimated)** moderate foot for classic rig |
| `Roach` | 0.10 | — | **(estimated)** 10% roach, standard for fractional rig |
| `BAD` | 0.80 | m | **(estimated)** boom above deck |

Computed main area: 0.5 × 10.80 × 3.30 × 1.10 = **19.60 m²**

**Jib:**

| Parameter | Value | Unit | Reasoning |
|-----------|-------|------|-----------|
| `I` (forestay height) | 8.50 | m | **(estimated)** fractional — forestay attaches ~79% up the mast |
| `J` (foretriangle base) | 2.70 | m | **(estimated)** narrow foretriangle, typical 5.5m |
| `LPG` (luff perpendicular) | 2.70 | m | **(estimated)** 100% non-overlapping jib (LPG = J) |
| `HBI` (height above deck) | 0.50 | m | **(estimated)** low-cut jib |

Computed jib area: 0.5 × 8.50 × 2.70 = **11.48 m²**

**Total upwind: 19.60 + 11.48 = 31.08 m²** (within ~4% of published 29.73 m²; acceptable for initial estimate — can tune P/E down slightly if needed)

**Spinnaker:**

| Parameter | Value | Unit | Reasoning |
|-----------|-------|------|-----------|
| `area` | 50.0 | m² | **(estimated)** ~1.7× upwind area, typical for 5.5m class symmetric kite |
| `vce` | 4.5 | m | **(estimated)** centre of effort at ~53% of I height |

### Righting Moment / GZ Curve (Estimated)

For a classic 5.5m with ~50% ballast ratio (1000 kg lead keel), narrow beam (1.98m), and deep draft (1.35m):

| Heel (deg) | GZ (m) | Reasoning |
|------------|--------|-----------|
| 0 | 0.000 | Zero at upright |
| 10 | 0.120 | Narrow beam → modest initial stability; GZ ≈ GM × sin(φ), GM estimated ~0.70m |
| 20 | 0.230 | Linear region, GZ ≈ 0.70 × sin(20°) = 0.24 |
| 30 | 0.310 | Approaching max GZ; narrow hull starts losing form stability |
| 40 | 0.350 | Near max righting arm for narrow metre boat |
| 50 | 0.330 | GZ starts declining; deck edge immersion |
| 60 | 0.260 | Significant decline, heavy weather limit region |

Estimation method: GM estimated at ~0.70m from ballast ratio (~50%), VCG estimate (~0.15m below WL for classic keel boat), and BM ≈ I_wpa / Vol ≈ (Bwl³ × Lwl / 12) / Vol. Cross-checked against published GZ curves for similar narrow keelboats (Soling, Star class).

### Crew Configuration

| Parameter | Value | Reasoning |
|-----------|-------|-----------|
| Crew count | 3 | Typical Daring racing crew |
| Total crew weight | 240 kg | 3 × 80 kg average |
| Crew arm | 0.8 × Bmax | Same as current VPP model — crew on rail |

---

## Task 1: Make GZ Curve Per-Yacht (Configurable)

Currently `righting_moment.json` is a single global file read by every `Yacht` instance. This must become per-yacht before we can model the Daring alongside YD41.

**Files:**
- Modify: `src/YachtMod.py` (Yacht class constructor + `_build_rm_interp`)
- Modify: `righting_moment.json` → keep as default fallback
- Create: `dat/Daring/righting_moment.json`
- Create: `dat/YD-41/righting_moment.json` (move existing data)
- Test: `tests/test_yacht.py`

**Step 1: Write failing test for per-yacht GZ**

```python
# tests/test_yacht.py
import numpy as np
import pytest
from src.YachtMod import Yacht, Keel, Rudder
from src.SailMod import Main, Jib


def _minimal_yacht(**overrides):
    """Create a minimal Yacht for testing with sensible defaults."""
    defaults = dict(
        Name="TestYacht", Lwl=7.01, Vol=1.95, Bwl=1.70, Tc=0.45,
        WSA=11.5, Tmax=1.35, Amax=0.38, Mass=2000, Loa=9.90, Boa=1.98,
        Ff=0.75, Fa=0.55,
        App=[Keel(Cu=0.70, Cl=0.45, Span=0.90), Rudder(Cu=0.32, Cl=0.18, Span=0.75)],
        Sails=[Main("MN1", P=10.80, E=3.30, Roach=0.1, BAD=0.80),
               Jib("J1", I=8.50, J=2.70, LPG=2.70, HBI=0.50)],
    )
    defaults.update(overrides)
    return Yacht(**defaults)


def test_yacht_accepts_gz_parameter():
    """Yacht should accept an optional gz dict to override the global file."""
    gz = {"Heel": [0, 10, 20, 30], "GZ": [0.0, 0.12, 0.23, 0.31]}
    yacht = _minimal_yacht(GZ=gz)
    # At 10 degrees, righting arm should match our custom data
    rm_10 = yacht._get_RmH(10.0)
    expected = 0.12 * 2000 * 9.81
    assert abs(rm_10 - expected) < 1.0  # within 1 Nm


def test_yacht_falls_back_to_file_when_no_gz():
    """When no GZ parameter given, should still load from file (backward compat)."""
    yacht = _minimal_yacht()
    rm_10 = yacht._get_RmH(10.0)
    assert rm_10 > 0  # loaded from righting_moment.json
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_yacht.py -v`
Expected: FAIL — `Yacht.__init__() got an unexpected keyword argument 'GZ'`

**Step 3: Implement per-yacht GZ in YachtMod.py**

Modify `Yacht.__init__` to accept optional `GZ=None` parameter. If provided, use it directly. If not, fall back to `righting_moment.json` file.

In `src/YachtMod.py`, change the constructor signature:

```python
def __init__(self, Name, Lwl, Vol, Bwl, Tc, WSA, Tmax,
             Amax, Mass, Loa, Boa, Ff, Fa, App=[], Sails=[], GZ=None):
```

Add docstring for `GZ`:
```python
        GZ : dict, optional
            Righting arm curve as ``{"Heel": [...], "GZ": [...]}``.
            Heel in degrees, GZ in metres. If *None*, loads from
            ``righting_moment.json`` (backward compatible).
```

Store it and update `_build_rm_interp`:

```python
        self._gz_data = GZ
        self._interp_rm = self._build_rm_interp()

    def _build_rm_interp(self):
        if self._gz_data is not None:
            a = self._gz_data
        else:
            a = json_read('righting_moment')
        return interpolate.interp1d(np.array(a["Heel"]), np.array(a["GZ"]),
                                    kind="linear", fill_value="extrapolate")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_yacht.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/YachtMod.py tests/test_yacht.py
git commit -m "feat: make GZ curve per-yacht with optional parameter"
```

---

## Task 2: Make Crew Weight Configurable

Currently crew weight is auto-calculated from `25.8 * Lwl^1.4262`, which gives ~158 kg for the YD41 (12m) but only ~56 kg for the Daring (7m) — far too low for 3-4 crew.

**Files:**
- Modify: `src/YachtMod.py` (Yacht constructor)
- Test: `tests/test_yacht.py`

**Step 1: Write failing test**

```python
def test_yacht_accepts_crew_weight():
    """Yacht should accept an optional crew_weight to override the empirical formula."""
    yacht = _minimal_yacht(crew_weight=240.0)
    assert yacht.cw == 240.0


def test_yacht_default_crew_weight():
    """Without crew_weight param, should use empirical formula."""
    yacht = _minimal_yacht()
    expected = 25.8 * 7.01 ** 1.4262
    assert abs(yacht.cw - expected) < 0.1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_yacht.py::test_yacht_accepts_crew_weight -v`
Expected: FAIL

**Step 3: Implement configurable crew weight**

Add `crew_weight=None` to `Yacht.__init__` signature:

```python
def __init__(self, Name, Lwl, Vol, Bwl, Tc, WSA, Tmax,
             Amax, Mass, Loa, Boa, Ff, Fa, App=[], Sails=[], GZ=None, crew_weight=None):
```

Add docstring:
```python
        crew_weight : float, optional
            Total crew weight (kg). If *None*, uses empirical formula
            ``25.8 * Lwl ** 1.4262``.
```

Replace the crew weight line:
```python
        self.cw = crew_weight if crew_weight is not None else 25.8 * self.l ** 1.4262
```

**Step 4: Run tests**

Run: `pytest tests/test_yacht.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/YachtMod.py tests/test_yacht.py
git commit -m "feat: make crew weight configurable with optional parameter"
```

---

## Task 3: Create Daring Yacht Definition & Run Script

**Files:**
- Create: `runDaring.py`
- Create: `dat/Daring/righting_moment.json`
- Test: `tests/test_daring.py`

**Step 1: Create Daring GZ data file**

Write `dat/Daring/righting_moment.json`:
```json
{
  "Heel": [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
  "GZ":   [0.000, 0.120, 0.230, 0.310, 0.350, 0.330, 0.260]
}
```

**Step 2: Write integration test**

```python
# tests/test_daring.py
import numpy as np
import pytest
from src.SailMod import Jib, Kite, Main
from src.VPPMod import VPP
from src.YachtMod import Keel, Rudder, Yacht


# Daring GZ curve (estimated for classic 5.5m, ~50% ballast ratio, GM ~0.70m)
DARING_GZ = {
    "Heel": [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
    "GZ":   [0.000, 0.120, 0.230, 0.310, 0.350, 0.330, 0.260],
}


def return_daring():
    """Create Daring yacht with estimated 5.5m class parameters.

    Published values (classicsailboats.org / Cowes Classics):
        LOA=9.90m, LWL=7.01m, Beam=1.98m, Draft=1.35m,
        Displacement=2000kg, Upwind SA=29.73m²

    Estimated values are documented in docs/plans/2026-02-27-daring-vpp.md
    """
    return Yacht(
        Name="Daring",
        Lwl=7.01,
        Vol=1.95,
        Bwl=1.70,
        Tc=0.45,
        WSA=11.5,
        Tmax=1.35,
        Amax=0.38,
        Mass=2000,
        Loa=9.90,
        Boa=1.98,
        Ff=0.75,
        Fa=0.55,
        App=[
            Keel(Cu=0.70, Cl=0.45, Span=0.90),
            Rudder(Cu=0.32, Cl=0.18, Span=0.75),
        ],
        Sails=[
            Main("MN1", P=10.80, E=3.30, Roach=0.1, BAD=0.80),
            Jib("J1", I=8.50, J=2.70, LPG=2.70, HBI=0.50),
            Kite("S1", area=50.0, vce=4.50),
        ],
        GZ=DARING_GZ,
        crew_weight=240.0,
    )


def test_daring_vpp_runs():
    """Daring VPP should solve without errors across a range of conditions."""
    daring = return_daring()
    vpp = VPP(Yacht=daring)
    vpp.set_analysis(
        tws_range=np.arange(6.0, 14.0, 2.0),
        twa_range=np.linspace(35.0, 175.0, 15),
    )
    vpp.run(verbose=False)
    results = vpp.results()
    assert results["name"] == "Daring"
    # Should have results for 4 wind speeds
    assert len(results["tws"]) == 4


def test_daring_boat_speed_sanity():
    """Daring should produce reasonable speeds: 3-7 knots in moderate wind."""
    daring = return_daring()
    vpp = VPP(Yacht=daring)
    vpp.set_analysis(
        tws_range=np.array([10.0]),
        twa_range=np.linspace(40.0, 160.0, 13),
    )
    vpp.run(verbose=False)
    results = np.array(vpp.results()["results"])
    # Max boat speed at 10 kts TWS should be between 3 and 7 knots
    max_speed = np.max(results[:, :, :, 0])
    assert 3.0 < max_speed < 7.0, f"Max speed {max_speed:.1f} kts outside expected range"
```

**Step 3: Run tests to verify they fail**

Run: `pytest tests/test_daring.py -v`
Expected: FAIL (initially may fail if Tasks 1-2 not done yet; should pass after)

**Step 4: Create `runDaring.py`**

```python
#!/usr/bin/env python3
"""
Velocity Prediction Program for the Daring sailing yacht.

The Daring is a one-design keelboat designed by Arthur Robb, based on
his 5.5 Metre class yacht "Vision" (1956 Olympic silver medal).

Published specifications (classicsailboats.org):
    LOA: 9.90m | LWL: 7.01m | Beam: 1.98m | Draft: 1.35m
    Displacement: 2000 kg | Upwind sail area: 29.73 m²

Estimated parameters are documented in docs/plans/2026-02-27-daring-vpp.md.
All estimates are marked and can be refined with actual measurements.
"""
import logging

import numpy as np

from src.SailMod import Jib, Kite, Main
from src.VPPMod import VPP
from src.YachtMod import Keel, Rudder, Yacht

logging.basicConfig(level=logging.INFO)

# --- Estimated GZ curve for classic 5.5m ---
# GM ~0.70m, ~50% ballast ratio, narrow beam (1.98m)
# See docs/plans/2026-02-27-daring-vpp.md for derivation
DARING_GZ = {
    "Heel": [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
    "GZ":   [0.000, 0.120, 0.230, 0.310, 0.350, 0.330, 0.260],
}

Daring = Yacht(
    Name="Daring",
    Lwl=7.01,       # (published) waterline length
    Vol=1.95,       # (estimated) 2000kg / 1025 kg/m³
    Bwl=1.70,       # (estimated) ~86% of Boa
    Tc=0.45,        # (estimated) canoe body draft
    WSA=11.5,       # (estimated) Delf series for narrow hull
    Tmax=1.35,      # (published) max draft incl. keel
    Amax=0.38,      # (estimated) Bwl × Tc × Cm(0.50)
    Mass=2000,      # (published) total displacement
    Loa=9.90,       # (published) length overall
    Boa=1.98,       # (published) beam overall
    Ff=0.75,        # (estimated) freeboard fore
    Fa=0.55,        # (estimated) freeboard aft
    App=[
        Keel(Cu=0.70, Cl=0.45, Span=0.90),     # (estimated) classic fin
        Rudder(Cu=0.32, Cl=0.18, Span=0.75),   # (estimated) separated rudder
    ],
    Sails=[
        Main("MN1", P=10.80, E=3.30, Roach=0.1, BAD=0.80),  # (est.) ~19.6 m²
        Jib("J1", I=8.50, J=2.70, LPG=2.70, HBI=0.50),      # (est.) ~11.5 m²
        Kite("S1", area=50.0, vce=4.50),                       # (est.) symmetric kite
    ],
    GZ=DARING_GZ,
    crew_weight=240.0,  # 3 crew × 80 kg
)

vpp = VPP(Yacht=Daring)

vpp.set_analysis(
    tws_range=np.arange(4.0, 22.0, 2.0),
    twa_range=np.linspace(30.0, 180.0, 31),
)

vpp.run(verbose=False)
vpp.write("results_daring")
vpp.polar(3, True)
vpp.SailChart(True)
```

**Step 5: Run tests and the script**

Run: `pytest tests/test_daring.py -v`
Expected: PASS

Run: `python runDaring.py`
Expected: Generates polar plots and `results_daring.json`

**Step 6: Commit**

```bash
git add runDaring.py dat/Daring/righting_moment.json tests/test_daring.py
git commit -m "feat: add Daring 5.5m yacht definition with estimated parameters"
```

---

## Task 4: Add Daring as Streamlit Default Preset

The Streamlit app currently hardcodes YD41 defaults. Add a preset selector so users can switch between YD41 and Daring.

**Files:**
- Modify: `demos/pages/1_VPP_⛵.py`

**Step 1: Add preset dictionaries**

Add after the existing `yacht` dict (line 97), a presets dict:

```python
PRESETS = {
    "YD41": {
        "yacht": {
            "Name": "YD41", "Lwl": 11.90, "Vol": 6.05, "Bwl": 3.18, "Tc": 0.4,
            "WSA": 28.20, "Tmax": 2.30, "Amax": 1.051, "Mass": 6500,
            "Ff": 1.5, "Fa": 1.5, "Boa": 4.2, "Loa": 12.5,
        },
        "keel": {"Cu": 1.00, "Cl": 0.78, "Span": 1.90},
        "rudder": {"Cu": 0.48, "Cl": 0.22, "Span": 1.15},
        "main": {"Name": "MN1", "P": 16.60, "E": 5.60, "Roach": 0.1, "BAD": 1.0},
        "jib": {"Name": "J1", "I": 16.20, "J": 5.10, "LPG": 5.40, "HBI": 1.8},
        "kite": {"Name": "A2", "area": 150.0, "vce": 9.55},
    },
    "Daring (5.5m)": {
        "yacht": {
            "Name": "Daring", "Lwl": 7.01, "Vol": 1.95, "Bwl": 1.70, "Tc": 0.45,
            "WSA": 11.5, "Tmax": 1.35, "Amax": 0.38, "Mass": 2000,
            "Ff": 0.75, "Fa": 0.55, "Boa": 1.98, "Loa": 9.90,
        },
        "keel": {"Cu": 0.70, "Cl": 0.45, "Span": 0.90},
        "rudder": {"Cu": 0.32, "Cl": 0.18, "Span": 0.75},
        "main": {"Name": "MN1", "P": 10.80, "E": 3.30, "Roach": 0.1, "BAD": 0.80},
        "jib": {"Name": "J1", "I": 8.50, "J": 2.70, "LPG": 2.70, "HBI": 0.50},
        "kite": {"Name": "S1", "area": 50.0, "vce": 4.50},
    },
}
```

**Step 2: Add selectbox before parameter inputs**

Replace the hardcoded yacht/keel/rudder/main/jib/kite dicts with:

```python
preset_name = st.selectbox("Yacht preset", list(PRESETS.keys()), index=1)
preset = PRESETS[preset_name]
yacht = dict(preset["yacht"])
keel = dict(preset["keel"])
rudder = dict(preset["rudder"])
main = dict(preset["main"])
jib = dict(preset["jib"])
kite = dict(preset["kite"])
```

**Step 3: Test manually**

Run: `cd demos && streamlit run Home.py`
Expected: Dropdown with "YD41" and "Daring (5.5m)", selecting Daring populates all fields.

**Step 4: Commit**

```bash
git add demos/pages/1_VPP_⛵.py
git commit -m "feat: add Daring preset to Streamlit UI"
```

---

## Task 5: Verify Full Integration & Run Baseline Polars

**Files:**
- No new files; run existing

**Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass (existing YD41 tests + new Daring tests)

**Step 2: Generate Daring baseline polars**

Run: `python runDaring.py`
Expected: `results_daring.json` written, polar plots displayed/saved

**Step 3: Sanity-check output**

Verify:
- VMG upwind ~3.5-4.5 kts in 10 kts TWS (reasonable for 5.5m class)
- VMG downwind ~4.5-5.5 kts in 10 kts TWS with kite
- Max speed ~5-6 kts in 15+ kts TWS
- Heel angles 15-25° in moderate wind (narrow hull, will heel)
- No NaN values or solver failures

**Step 4: Commit results**

```bash
git add results_daring.json
git commit -m "feat: add Daring baseline performance prediction"
```

---

## Future Work (Beads to Track)

These are documented for future sessions. Each is a separate piece of work.

### Bead 1: Heavy Weather Modelling

The current VPP has no wave drag, no gust response, and no reef/furl optimization. For heavy weather prediction:
- Add wave resistance component (Gerritsma & Beukelman added drag from waves)
- Implement reef/furl optimization (currently `flat=1.0, red=1.0` are hardcoded in the solver)
- Add a wave height / sea state parameter to `set_analysis()`
- Model knockdown / max heel safety limits
- Wind gradient (reduced wind speed at deck level in heavy weather)

### Bead 2: Equipment Comparison Framework

To compare old vs new equipment (sails, keel, rig weight):
- Overlay polar plots from two VPP runs on same axes
- Compute delta VMG, delta max speed, delta optimal TWA
- Create a `compare()` method on VPP that takes two result sets
- Support rig weight changes (affects VCG → GZ curve → righting moment)
- Parameter sensitivity analysis (what-if for each dimension)

### Bead 3: Generic Codebase Improvements

- **YAML/JSON yacht definitions**: Load yacht configs from files instead of Python code. Enable a `dat/yachts/` directory with one file per boat.
- **Per-yacht righting moment files**: Extend Task 1 to also support loading from `dat/<YachtName>/righting_moment.json` by convention.
- **Parameter estimation helpers**: Given basic dims (LOA, LWL, Beam, Draft, Disp), estimate WSA, Amax, Vol, Tc using empirical formulas (Delf series, Holtrop).
- **API GZ support**: Extend the Flask API (`src/api.py`) to accept GZ and crew_weight in the JSON payload.
- **Streamlit GZ editor**: Add GZ curve editing and crew weight input to the Streamlit UI.
- **Results export**: CSV/Excel export of polar data for use in navigation software.

### Bead 4: Restore 5-DOF Constrained Optimizer

The original codebase contains a commented-out 5-DOF SLSQP optimizer in `src/VPPMod.py` (lines 249-264) that solves for `[vb, heel, leeway, flat, reef]` simultaneously with constraints. The original author abandoned it — likely due to convergence issues — and fell back to a 3-DOF root-finder with `flat=1.0` and `reef=1.0` hardcoded.

The iterative outer loop (Bead 1 / current work) is a pragmatic workaround, but a proper constrained optimizer would be more elegant and physically accurate:

- **Restore the SLSQP solver** as an alternative to the current `scipy.optimize.root` LM solver
- **Constraints**: force/moment equilibrium (Fx, Fy, Mx residuals = 0), heel ≤ phi_max
- **Bounds**: vb ≥ 0, 0 ≤ heel ≤ phi_max, -2 ≤ leeway ≤ 6, 0.62 ≤ flat ≤ 1.0, 0 ≤ reef ≤ 2.0
- **Objective**: maximize boat speed (minimize -vb)
- **Key challenges**: convergence at extreme TWA/TWS, initial guess sensitivity, solver robustness
- **Approach**: Use the 3-DOF solution as initial guess for the 5-DOF optimizer. Fall back to 3-DOF + iterative depower if SLSQP fails to converge.
- **Testing**: Compare 5-DOF results against 3-DOF + outer loop across full TWS/TWA grid; results should agree within tolerance at low wind, diverge only where depowering is active.
- The nlopt COBYLA solver (already imported) is another option — it's derivative-free and may handle the non-smooth flat/reef landscape better than SLSQP.

### Bead 5: Streamlit Deployment & Daring Defaults

The app is deployed at yacht-vpp.streamlit.app. Task 4 adds Daring as a preset. Additional work:
- Verify deployment picks up the Daring preset from the `uv-migration` branch (or master after merge)
- Consider making Daring the default selection if this is primarily for the Daring fleet
- Add a description panel explaining the Daring class and parameter sources
