# UV Migration & Repository Improvements Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate Python-VPP from setup.py + requirements.txt to uv with pyproject.toml, fix open bugs, modernize CI/CD, and fix README errors.

**Architecture:** Replace the legacy setuptools/pip build chain with uv-managed pyproject.toml. Keep the existing `src/` flat package layout. Modernize CI to use uv for dependency installation and test running. Fix the string-raise bug and README typo reported in open issues.

**Tech Stack:** uv, pyproject.toml (PEP 621), GitHub Actions, pytest

---

## Task 1: Create pyproject.toml and remove setup.py + requirements.txt

This is the core migration. We replace `setup.py` and `requirements.txt` with a single `pyproject.toml` using PEP 621 metadata.

**Files:**
- Create: `pyproject.toml`
- Delete: `setup.py`
- Delete: `requirements.txt`

**Step 1: Create pyproject.toml**

Create `pyproject.toml` in the repo root with the following content:

```toml
[project]
name = "python-vpp"
version = "0.0.2"
description = "OOP Velocity Prediction Program"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    { name = "Marin Lauber", email = "M.Lauber@soton.ac.uk" },
    { name = "Otto Villani" },
    { name = "Thomas Dickson" },
]
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
dependencies = [
    "numpy>=1.26",
    "matplotlib>=3.8",
    "scipy>=1.12",
    "nlopt>=2.7",
    "tqdm>=4.66",
]

[project.optional-dependencies]
api = ["flask"]
demo = ["streamlit>=1.37"]
dev = [
    "pytest",
    "ruff",
    "mypy",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
```

Key decisions:
- Runtime deps are unpinned lower bounds (flexible for users)
- `streamlit` and `flask` are optional extras, not core deps
- Replaced `black` + `isort` with `ruff` (faster, single tool)
- `hatchling` build backend (modern, fast, no setup.py needed)
- `packages = ["src"]` tells hatch where the code lives

**Step 2: Delete setup.py and requirements.txt**

```bash
git rm setup.py requirements.txt
```

**Step 3: Generate uv.lock**

```bash
uv lock
```

This creates `uv.lock` with pinned versions for reproducible installs.

**Step 4: Add uv.lock to git and update .gitignore**

Add `uv.lock` to version control (uv recommends this). Update `.gitignore` to include `__pycache__` patterns consistently and remove stale entries:

Replace `.gitignore` contents with:

```
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/

# Environments
.venv/
venv/

# IDE
.vscode/
.idea/

# Sphinx
sphinx/_build/

# pytest
.pytest_cache/

# Project
ORC_VPP_2019.pdf
dev.py
```

**Step 5: Verify install works**

```bash
uv sync --all-extras
uv run pytest -vv
```

Expected: All existing tests pass.

**Step 6: Commit**

```bash
git add pyproject.toml uv.lock .gitignore
git commit -m "build: migrate from setup.py/requirements.txt to uv + pyproject.toml

Replace legacy setuptools build with hatchling + PEP 621 metadata.
Add uv.lock for reproducible installs. Replace black+isort with ruff.
Move streamlit/flask to optional dependency groups."
```

---

## Task 2: Update CI workflow to use uv

Replace pip-based CI with uv. Also bump action versions and test on multiple Python versions.

**Files:**
- Modify: `.github/workflows/test.yml`

**Step 1: Rewrite test.yml**

Replace the entire file with:

```yaml
name: Run tests

on:
  push:
    branches: [master, main]
  pull_request:
    branches: [master, main]

jobs:
  test:
    name: Test (Python ${{ matrix.python-version }}, ${{ matrix.os }})
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest]
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: uv sync --extra dev
      - name: Run tests
        run: uv run pytest -vv
```

**Step 2: Commit**

```bash
git add .github/workflows/test.yml
git commit -m "ci: migrate test workflow from pip to uv

Test on Python 3.10-3.12. Use astral-sh/setup-uv action.
Bump actions/checkout to v4."
```

---

## Task 3: Update publish workflow for uv + trusted publishers

Modernize the PyPI publish workflow. Replace the legacy `setup.py sdist` + twine approach with `uv build` and PyPI trusted publishers (OIDC, no secrets needed).

**Files:**
- Modify: `.github/workflows/python-publish.yml`

**Step 1: Rewrite python-publish.yml**

Replace the entire file with:

```yaml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Build package
        run: uv build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

Note: The repo owner will need to configure trusted publishers on PyPI for this to work. The old `TWINE_USERNAME`/`TWINE_PASSWORD` secrets can be removed once configured.

**Step 2: Commit**

```bash
git add .github/workflows/python-publish.yml
git commit -m "ci: modernize publish workflow with uv build + trusted publishers

Replace setup.py/twine with uv build and PyPI OIDC trusted publishers.
Run on ubuntu-latest instead of self-hosted."
```

---

## Task 4: Fix string raise bug (Issue #46)

`VPPMod.py` lines 128 and 203 use `raise "string"` which is invalid in Python 3 — it raises a `TypeError` instead of the intended error.

**Files:**
- Modify: `src/VPPMod.py:128` and `src/VPPMod.py:203`
- Test: `tests/test_vpp.py`

**Step 1: Write the failing test**

Add to `tests/test_vpp.py`:

```python
def test_run_without_analysis_raises():
    """Issue #46: raise with string literal should be a proper exception."""
    from src.VPPMod import VPP
    from tests.test_utils import return_YD41_particulars
    yacht = return_YD41_particulars()
    vpp = VPP(Yacht=yacht)
    # run() without calling set_analysis() first should raise RuntimeError
    import pytest
    with pytest.raises(RuntimeError, match="no analysis set"):
        vpp.run()
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_vpp.py::test_run_without_analysis_raises -v
```

Expected: FAIL — currently raises `TypeError` because `raise "string"` is invalid.

**Step 3: Fix the bug in VPPMod.py**

In `src/VPPMod.py`, change line 128:
```python
# Before:
raise "VPP run stop: no analysis set!"
# After:
raise RuntimeError("VPP run stop: no analysis set!")
```

And line 203:
```python
# Before:
raise "VPP run stop: no analysis set!"
# After:
raise RuntimeError("VPP run stop: no analysis set!")
```

Also, the guard logic is inverted. `self.upToDate` is set to `True` in `set_analysis()`, and the check is `if not self.upToDate`. This means after calling `set_analysis()`, `upToDate=True`, so `not True = False`, so the raise is skipped — correct. But if `set_analysis()` was never called, `self.upToDate` doesn't exist at all, causing an `AttributeError`, not the intended guard.

Fix: initialize `self.upToDate = False` in `__init__` (before `set_analysis` is called):

In `src/VPPMod.py` `__init__`, after line 51, add:

```python
self.upToDate = False
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_vpp.py::test_run_without_analysis_raises -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/VPPMod.py tests/test_vpp.py
git commit -m "fix: raise proper RuntimeError instead of string literal (fixes #46)

String raises are invalid in Python 3 and caused TypeError.
Also initialize self.upToDate = False in __init__ so the guard
works when set_analysis() hasn't been called."
```

---

## Task 5: Fix README pip install instructions (Issue #43)

The README has an incorrect pip install command.

**Files:**
- Modify: `README.md:69`

**Step 1: Fix the pip command and add uv instructions**

In `README.md`, replace the Contributing > Install dependencies section (lines 65-78) with:

```markdown
### Install dependencies

Install the project using [uv](https://docs.astral.sh/uv/):

```bash
uv sync --extra dev
```

If using `pip`:

```bash
pip install -e ".[dev]"
```
```

This fixes issue #43 (`pip install requirements.txt` -> correct command) and adds uv as the primary method.

**Step 2: Update the shebang in runVPP.py**

Replace line 1 of `runVPP.py`:
```python
# Before:
#!/opt/miniconda3/bin/python
# After:
#!/usr/bin/env python3
```

This removes the hardcoded miniconda path that only works on the original developer's machine.

**Step 3: Commit**

```bash
git add README.md runVPP.py
git commit -m "docs: fix install instructions and add uv as primary method (fixes #43)

Replace incorrect 'pip install requirements.txt' with correct commands.
Add uv as the recommended install method.
Fix hardcoded shebang in runVPP.py."
```

---

## Task 6: Fix deprecated scipy.interpolate.interp2d usage

`scipy.interpolate.interp2d` was deprecated in scipy 1.10 and removed in scipy 1.14. The code in `UtilsMod.py:181` still uses it. PR #51 partially addresses this but hasn't been merged.

**Files:**
- Modify: `src/UtilsMod.py:181`

**Step 1: Write the failing test**

Add to `tests/test_vpp.py`:

```python
def test_sail_chart_no_deprecation_warning():
    """Verify sail_chart doesn't use deprecated interp2d."""
    import warnings
    from tests.test_utils import return_YD41_particulars
    from src.VPPMod import VPP
    import numpy as np

    yacht = return_YD41_particulars()
    vpp = VPP(Yacht=yacht)
    vpp.set_analysis(
        tws_range=np.array([6.0, 10.0]),
        twa_range=np.linspace(30.0, 180.0, 16),
    )
    vpp.run(verbose=False)
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        vpp.SailChart(save=True, fname="test_sailchart.png")
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_vpp.py::test_sail_chart_no_deprecation_warning -v
```

Expected: FAIL with DeprecationWarning about interp2d (on scipy < 1.14) or ImportError (on scipy >= 1.14).

**Step 3: Replace interp2d with RegularGridInterpolator in sail_chart**

In `src/UtilsMod.py`, replace the `sail_chart` function's interpolation logic. Change:

```python
from scipy import interpolate
```

to:

```python
from scipy import interpolate
from scipy.interpolate import RegularGridInterpolator
```

Then in the `sail_chart` function, replace lines 181-183:

```python
        func = interpolate.interp2d(twas, twss, sail, kind="cubic")
        data = func(xnew, ynew)
        data = np.where(data > 1.0, 1.0, data)
```

with:

```python
        func = RegularGridInterpolator(
            (twss, twas), sail, method="cubic", bounds_error=False, fill_value=0.0
        )
        yy, xx = np.meshgrid(ynew, xnew, indexing="ij")
        data = func((yy, xx))
        data = np.clip(data, 0.0, 1.0)
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_vpp.py -v
```

Expected: All tests pass, no deprecation warnings.

**Step 5: Clean up test artifact and commit**

```bash
rm -f test_sailchart.png
git add src/UtilsMod.py tests/test_vpp.py
git commit -m "fix: replace deprecated scipy interp2d with RegularGridInterpolator

interp2d was deprecated in scipy 1.10 and removed in 1.14.
Use RegularGridInterpolator for sail chart interpolation."
```

---

## Task 7: Replace deprecated scipy.interpolate.interp1d

`interp1d` is also deprecated (scipy 1.10+). It's used in `UtilsMod.py:46` via `build_interp_func` and called from `SailMod.py` and `HydroMod.py`.

**Files:**
- Modify: `src/UtilsMod.py:40-46`

**Step 1: Write a test for the interpolation function**

Add to `tests/test_resistance.py` (or a new test file):

```python
def test_build_interp_func_no_deprecation():
    """Verify build_interp_func doesn't use deprecated interp1d."""
    import warnings
    from src.UtilsMod import build_interp_func
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        func = build_interp_func("main", i=1)
        # Should return a callable that produces a float
        result = func(30.0)
        assert isinstance(float(result), float)
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_resistance.py::test_build_interp_func_no_deprecation -v
```

Expected: FAIL with DeprecationWarning about interp1d.

**Step 3: Replace interp1d with make_interp_spline**

In `src/UtilsMod.py`, replace `build_interp_func`:

```python
def build_interp_func(fname, i=1, kind="linear"):
    """
    build interpolation function and returns it in a list
    """
    a = np.genfromtxt("dat/" + fname + ".dat", delimiter=",", skip_header=1)
    k = {"linear": 1, "quadratic": 2, "cubic": 3}.get(kind, 1)
    spline = interpolate.make_interp_spline(a[0, :], a[i, :], k=k)
    spline.extrapolate = True
    return spline
```

`make_interp_spline` is the recommended replacement per scipy docs. It returns a `BSpline` object that is callable just like the old `interp1d`.

**Step 4: Run all tests to verify nothing breaks**

```bash
uv run pytest -vv
```

Expected: All tests pass.

**Step 5: Commit**

```bash
git add src/UtilsMod.py tests/test_resistance.py
git commit -m "fix: replace deprecated scipy interp1d with make_interp_spline

interp1d was deprecated in scipy 1.10. Use make_interp_spline
which returns a BSpline with the same callable interface."
```

---

## Task 8: Run full test suite and verify

Final verification that everything works together.

**Files:** None (verification only)

**Step 1: Full test run**

```bash
uv run pytest -vv
```

Expected: All tests pass.

**Step 2: Verify the VPP runs end-to-end**

```bash
uv run python runVPP.py
```

Expected: Produces `results.json`, `Polars.png`, `SailChart.png` without errors or deprecation warnings.

**Step 3: Verify ruff passes**

```bash
uv run ruff check src/ tests/
```

If there are lint errors, fix them.

**Step 4: Final commit if any cleanup needed**

---

## Summary of Issues Addressed

| Issue | Status | Action |
|-------|--------|--------|
| #46 - String raise bug | Fixed in Task 4 |
| #43 - Incorrect pip install | Fixed in Task 5 |
| #36 - Update dependencies | Fixed in Task 1 (unpinned lower bounds + uv.lock) |
| #25 - Python package release | Enabled by Task 1 + Task 3 (proper pyproject.toml + publish workflow) |
| #21 - Refactor into package | Partially addressed by Task 1 (proper packaging) |
| #24 - Project roadmap CI items | Addressed by Task 2 (CI) + Task 1 (ruff replaces black+isort) |
| #53 - Parameter docs | Out of scope for this PR (documentation content, not build) |
| #54 - IG attribute bug | Out of scope (unsupported rig type per maintainer) |
| #45 - OpenCPN export | Out of scope (separate PR #52 pending) |
| #40 - Ship type question | Informational, no code change needed |
| #31 - To do list | Tracking issue, no code change needed |
| PR #51 - Dep updates | Superseded by this work |
| PR #41 - Dep updates | Superseded by this work |

## Notes for Reviewer

- The `src/` directory is kept as-is (not moved to a nested package like `python_vpp/`). Issue #21 proposes a deeper refactor but that's a larger scope change best done separately.
- `scipy.interpolate.interp2d` replacement in Task 6 changes the interpolation method. The output should be visually similar but may differ slightly at boundaries. Manual visual inspection of `SailChart.png` is recommended.
- The `interp1d` -> `make_interp_spline` replacement in Task 7 should be numerically equivalent for linear interpolation but the extrapolation behavior may differ slightly at the edges of the data range.
