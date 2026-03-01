# Performance Modelling Improvements + Match Racing Simulation

## Overview

Three performance model improvements (wave resistance, current/tide, surface roughness) and a match racing simulation tab with Monte Carlo wind shifts.

## Part 1: Added Resistance in Waves

### Physics

Added resistance from waves using a simplified Gerritsma-Beukelman approach. The key inputs are significant wave height (Hs) and mean wave period (Ts). Wave encounter angle is derived from the boat heading relative to wave direction.

**Default behaviour**: waves aligned with wind direction (no extra input). Optional `wave_direction` parameter overrides this.

**Formula**:

```
Raw = C_aw * (Hs^2 / Lwl) * (Bwl^2 / Tc) * f(omega_e)
```

Where:
- `C_aw` is a hull-form coefficient (empirical, ~6.0 for typical displacement hulls)
- `omega_e` is the wave encounter frequency: `omega_e = (2*pi/Ts) - (2*pi/Ts)^2 * Vb * cos(mu) / g`
- `mu` is the wave encounter angle (0 = head seas, 180 = following seas)
- Scaling: `Raw *= cos^2(mu)` — full drag head-on, zero beam-on, near-zero following

**Wave encounter angle**:
```
mu = boat_heading - wave_direction
```
If `wave_direction` is not provided, it defaults to `wind_direction` (= 0 in the VPP frame, so mu = TWA effectively).

### Implementation

- `src/HydroMod.py`: Add `_added_resistance_waves(Vb, phi, Hs, Ts, wave_dir, heading)` method. Called from `Rt()`. Returns 0 when Hs=0 (preserves current behaviour).
- `src/YachtMod.py`: Add `Hs`, `Ts`, `wave_direction` optional attributes to `Yacht` (default 0, 0, None).
- `src/VPPMod.py`: Pass wave params through to hydro calculations.
- `src/api.py`: Read `Hs`, `Ts`, `wave_direction` from environment section of payload.
- UI: Add Hs/Ts sliders to environment section with explainer text.

## Part 2: Current/Tide

Current does not change hull forces (which depend on speed-through-water). It changes speed-over-ground and therefore VMG and leg times.

### Implementation

Applied at the **race simulation layer** only, not inside the VPP equilibrium solver.

- `src/RaceMod.py`: Current vector added to SOG when computing leg times.
- UI: Current speed (kts) and direction (degrees) inputs in race simulation tab. Default 0.

For VPP polars display, current is irrelevant (polars show speed-through-water).

## Part 3: Surface Roughness

A multiplier on the ITTC friction coefficient to account for hull fouling.

### Implementation

- `src/HydroMod.py`: In `Rv()`, multiply Cf by `self.roughness_factor`.
- `src/YachtMod.py`: Add `roughness` optional attribute to `Yacht` (default 1.0).
- `src/api.py`: Read `roughness` from payload.
- UI: Roughness slider (0.95 to 1.25, default 1.0) with explainer text.

## Part 4: Match Racing Simulation

### Architecture

Following Philpott, Henderson & Teirney (2004). A time-stepping simulation of two boats racing a windward-leeward course, with stochastic wind shifts and Monte Carlo repetition.

### Course Model

Windward-leeward course:
- Leg distance: user-configurable (default 1.0 NM)
- Number of up/down pairs: user-configurable (default 1 = one beat + one run)
- Windward mark directly upwind of start

### Per-Leg Simulation

For each boat on each leg:

1. **Extract optimal VMG angle** from polar: scan BS(TWS, TWA) * cos(TWA) for upwind (or cos(180-TWA) for downwind).
2. **Compute VMG** at current TWS (which may have shifted).
3. **Time-step** (dt = 1 second): advance distance by VMG*dt.
4. **Tack/gybe at laylines**: when remaining distance can be covered on one tack, execute final approach.
5. **Tack/gybe penalty**: fixed time cost per maneuver (default 10s tack, 6s gybe).
6. **Wind shifts**: at each timestep, wind direction drifts by Brownian motion.

### Wind Model

Brownian motion on wind direction (Dalang et al. 2015):

```
wind_dir(t+dt) = wind_dir(t) + sigma * sqrt(dt) * N(0,1)
```

- `sigma`: wind shift volatility (default 2.0 deg/sqrt(min), typical for sea breeze)
- Wind speed held constant (simplification for v1)
- Mean-reverting variant optional: `wind_dir(t+dt) = wind_dir(t) + theta*(wind_dir_mean - wind_dir(t))*dt + sigma*sqrt(dt)*N(0,1)`

### Monte Carlo

Run N simulations (default 100) with different random seeds. Output:
- **Win probability** for each boat (% of races won)
- **Mean delta** in elapsed time (seconds)
- **Distribution histogram** of time deltas
- **Single example race trace** (plan view of boat tracks)

### New Module: `src/RaceMod.py`

```python
class Race:
    def __init__(self, polar_A, polar_B, tws, leg_distance, n_legs,
                 tack_penalty, gybe_penalty, current_speed, current_dir,
                 wind_sigma):
        ...

    def run_single(self, seed) -> RaceResult:
        """Run one race, return leg times for each boat."""
        ...

    def run_monte_carlo(self, n_runs=100) -> MonteCarloResult:
        """Run n_runs races, return statistics."""
        ...
```

`polar_A` and `polar_B` are 2D interpolation functions (TWS, TWA -> BS), built from VPP results.

### UI: New Streamlit Tab

`demos/pages/3_Match_Race_🏁.py`

Layout:
- Two columns for boat configs (reuse preset/edit pattern)
- Shared environment: TWS, leg distance, n_legs
- Race parameters: tack/gybe penalties, wind shift sigma, n_runs
- "Race!" button
- Results: win probability, mean time delta, histogram, example trace plot

### Explainer Boxes

Add `st.info()` boxes throughout the UI explaining:
- **VPP page**: What a VPP is, what the polar plot shows, what depowering means
- **Compare page**: How to interpret speed deltas
- **Match Race page**: What the simulation does, what wind shifts mean, how to interpret win probability
- **Environment section**: What Hs/Ts mean, what roughness represents

## Files to Modify/Create

| File | Changes |
|------|---------|
| `src/HydroMod.py` | Add `_added_resistance_waves()`, roughness factor in `Rv()` |
| `src/YachtMod.py` | Add `Hs`, `Ts`, `wave_direction`, `roughness` to Yacht |
| `src/VPPMod.py` | Pass wave/roughness params through |
| `src/api.py` | Accept new environment params |
| `src/RaceMod.py` | **New** — Race simulation engine |
| `demos/pages/1_VPP_⛵.py` | Wave/roughness inputs, explainer boxes |
| `demos/pages/2_Compare_⚖️.py` | Explainer boxes |
| `demos/pages/3_Match_Race_🏁.py` | **New** — Match racing tab |
| `demos/utils.py` | Environment input helpers for Hs/Ts/roughness |
| `tests/test_hydro.py` | **New** — Wave resistance, roughness tests |
| `tests/test_race.py` | **New** — Race simulation tests |
| `tests/test_api.py` | API tests for new params |

## Implementation Order

```
1. Surface roughness (simplest, self-contained)
2. Wave resistance (new physics, moderate complexity)
3. Race simulation engine (src/RaceMod.py + tests)
4. Match Race UI tab
5. Explainer boxes across all pages
6. Current/tide in race simulation
```

## Verification

1. `uv run pytest tests/ -v` — all tests pass after each step
2. Roughness factor > 1 produces slower speeds
3. Hs > 0 produces slower speeds, more so upwind than downwind
4. Race simulation: identical boats produce ~50/50 win probability
5. Faster boat wins > 50% of Monte Carlo runs
6. Tack penalty increase reduces win margin for upwind-strong boats
