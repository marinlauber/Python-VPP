"""Match racing simulation engine.

Simulates two boats racing a windward-leeward course with stochastic
wind shifts and tactical interactions.  Based on Philpott, Henderson &
Teirney (2004).
"""

from __future__ import annotations

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from src.WindMod import BrownianWind, WindModel


class Boat:
    """State of one boat during a race."""

    def __init__(self, polar, name, boat_length=12.0):
        self.polar = polar
        self.name = name
        self.boat_length = boat_length
        self.x = 0.0
        self.y = 0.0
        self.tack = 1  # +1 = starboard, -1 = port
        self.speed = 0.0
        self.elapsed = 0.0
        self.tack_count = 0
        self.gybe_count = 0
        self.penalty_remaining = 0.0
        self._just_tacked = False
        self._tack_cooldown = 0.0

    def reset(self):
        self.x = 0.0
        self.y = 0.0
        self.tack = 1
        self.speed = 0.0
        self.elapsed = 0.0
        self.tack_count = 0
        self.gybe_count = 0
        self.penalty_remaining = 0.0
        self._just_tacked = False
        self._tack_cooldown = 0.0


class Race:
    """Windward-leeward match race simulation.

    Parameters
    ----------
    polar_A, polar_B : callable
        callable(tws, twa) -> boat_speed in knots.
    tws : float
        True wind speed (knots).
    leg_distance : float
        Leg distance in nautical miles. Default 1.0.
    n_legs : int
        Number of upwind/downwind leg pairs. Default 1.
    tack_penalty : float
        Time penalty per tack (seconds). Default 10.0.
    gybe_penalty : float
        Time penalty per gybe (seconds). Default 6.0.
    wind_model : WindModel or None
        Pluggable wind model.  If *None*, a :class:`BrownianWind` is
        created from *tws* and *wind_sigma*.
    wind_sigma : float
        Wind shift volatility (deg/sqrt(min)).  Only used when
        *wind_model* is None.  Default 2.0.
    current_speed : float
        Current speed (knots). Default 0.0.
    current_dir : float
        Current direction (degrees, 0 = upwind). Default 0.0.
    corridor_width : float
        Course corridor half-width (metres). Default 200.0.
    boat_length : float
        Boat length (metres) for wind shadow. Default 12.0.
    trim_sigma : float
        Trim/crew noise — fractional std-dev on boat speed.
        0 = perfect trim, 0.03 = 3 % noise.  Default 0.0.
    tack_penalty_std : float
        Std-dev on tack penalty (seconds). Default 0.0 (fixed).
    gybe_penalty_std : float
        Std-dev on gybe penalty (seconds). Default 0.0 (fixed).
    """

    NM_TO_M = 1852.0
    KTS_TO_MS = 0.5144

    def __init__(self, polar_A, polar_B, tws, leg_distance=1.0, n_legs=1,
                 tack_penalty=10.0, gybe_penalty=6.0,
                 wind_model: WindModel | None = None, wind_sigma=2.0,
                 current_speed=0.0, current_dir=0.0, corridor_width=200.0,
                 boat_length=12.0,
                 trim_sigma=0.0, tack_penalty_std=0.0, gybe_penalty_std=0.0):
        self.polar_A = polar_A
        self.polar_B = polar_B
        self.tws = tws
        self.leg_distance_m = leg_distance * self.NM_TO_M
        self.n_legs = n_legs
        self.tack_penalty = tack_penalty
        self.gybe_penalty = gybe_penalty
        self.current_speed = current_speed * self.KTS_TO_MS
        self.current_dir_rad = np.radians(current_dir)
        self.corridor_width = corridor_width
        self.boat_length = boat_length
        self.trim_sigma = trim_sigma
        self.tack_penalty_std = tack_penalty_std
        self.gybe_penalty_std = gybe_penalty_std

        # Wind model — default to simple Brownian direction shifts
        if wind_model is not None:
            self.wind_model = wind_model
        else:
            self.wind_model = BrownianWind(tws=tws, twd=0.0, dir_sigma=wind_sigma)

    def _optimal_vmg_angle(self, polar, tws, upwind=True):
        """Find TWA that maximises VMG from a polar lookup."""
        if upwind:
            angles = np.arange(25.0, 75.0, 1.0)
        else:
            angles = np.arange(120.0, 180.0, 1.0)

        best_vmg = -1e9
        best_twa = angles[0]
        for twa in angles:
            bs = polar(tws, twa)
            if upwind:
                vmg = bs * np.cos(np.radians(twa))
            else:
                vmg = bs * np.cos(np.radians(180.0 - twa))
            if vmg > best_vmg:
                best_vmg = vmg
                best_twa = twa
        return best_twa

    def _is_in_shadow(self, boat_ahead, boat_behind, wind_dir):
        """Check if boat_behind is in boat_ahead's dirty air zone.

        Requires at least 2 boat lengths of downwind separation.
        """
        dx = boat_behind.x - boat_ahead.x
        dy = boat_behind.y - boat_ahead.y

        wind_rad = np.radians(wind_dir)
        downwind_dist = -dy * np.cos(wind_rad) - dx * np.sin(wind_rad)
        cross_dist = abs(-dy * np.sin(wind_rad) + dx * np.cos(wind_rad))

        min_dist = 2 * boat_ahead.boat_length
        max_dist = 10 * boat_ahead.boat_length
        if downwind_dist < min_dist or downwind_dist > max_dist:
            return False
        shadow_width = downwind_dist * np.tan(np.radians(30))
        return cross_dist < shadow_width

    def _should_tack(self, boat, opponent, twa_opt, upwind, wind_dir, rng):
        """Evaluate tactical rules — return True if boat should tack/gybe."""
        if boat._tack_cooldown > 0:
            return False

        # Rule 1: Layline — only tack if sailing AWAY from mark
        if upwind:
            remaining = self.leg_distance_m - boat.y
            if remaining > 0 and abs(boat.x) > 10:
                bearing = np.degrees(np.arctan2(abs(boat.x), remaining))
                sailing_away = (boat.x * boat.tack > 0)
                if bearing <= twa_opt and sailing_away:
                    return True
        else:
            remaining = boat.y
            if remaining > 0 and abs(boat.x) > 10:
                bearing = np.degrees(np.arctan2(abs(boat.x), remaining))
                sailing_away = (boat.x * boat.tack > 0)
                if bearing <= (180.0 - twa_opt) and sailing_away:
                    return True

        # Rule 2: Course boundary
        if abs(boat.x) > self.corridor_width / 2:
            return True

        separation = abs(boat.y - opponent.y)
        min_sep = 3.0 * boat.boat_length

        # Rule 3: In dirty air — tack to escape
        if self._is_in_shadow(opponent, boat, wind_dir):
            return True

        # Rule 4: Leading + opponent tacked → cover
        if separation > min_sep and boat.y > opponent.y and opponent._just_tacked:
            if boat.tack == opponent.tack:
                return True

        # Rule 5: Trailing + same tack as leader → split (70%)
        if separation > min_sep and boat.y < opponent.y and boat.tack == opponent.tack:
            if rng.random() < 0.70:
                return True

        return False

    def _sample_penalty(self, mean, std, rng):
        """Draw a tack/gybe penalty from N(mean, std), floored at 1s."""
        if std <= 0:
            return mean
        return max(1.0, mean + std * rng.standard_normal())

    def _apply_trim_noise(self, bs, rng):
        """Apply crew/trim noise to boat speed."""
        if self.trim_sigma <= 0:
            return bs
        return bs * max(0.0, 1.0 - self.trim_sigma * abs(rng.standard_normal()))

    def _run_leg(self, boat_A, boat_B, upwind, rng, dt=1.0):
        """Simulate a single leg. Returns (trace_A, trace_B)."""
        trace_A = []
        trace_B = []

        # Recompute optimal angles from current wind speed
        tws = self.wind_model.tws
        twa_opt_A = self._optimal_vmg_angle(boat_A.polar, tws, upwind)
        twa_opt_B = self._optimal_vmg_angle(boat_B.polar, tws, upwind)

        # Current vector (m/s)
        cur_x = self.current_speed * np.sin(self.current_dir_rad)
        cur_y = self.current_speed * np.cos(self.current_dir_rad)

        cooldown_time = max(self.tack_penalty, self.gybe_penalty) + 5.0

        max_steps = int(3600 * 4 / dt)
        for step in range(max_steps):
            if upwind:
                if boat_A.y >= self.leg_distance_m and boat_B.y >= self.leg_distance_m:
                    break
            else:
                if boat_A.y <= 0 and boat_B.y <= 0:
                    break

            # Advance wind model
            tws, wind_dir = self.wind_model.update(dt, rng)

            # Re-derive optimal VMG if wind speed changed significantly
            # (only worth it for models that vary TWS)
            # For now, keep twa_opt fixed per leg for performance

            # Randomize processing order
            if rng.random() < 0.5:
                order = [boat_A, boat_B]
                opt_angles = [twa_opt_A, twa_opt_B]
            else:
                order = [boat_B, boat_A]
                opt_angles = [twa_opt_B, twa_opt_A]

            for idx, (boat, twa_opt) in enumerate(zip(order, opt_angles)):
                opponent = order[1 - idx]

                if upwind and boat.y >= self.leg_distance_m:
                    continue
                if not upwind and boat.y <= 0:
                    continue

                boat._just_tacked = False
                if boat._tack_cooldown > 0:
                    boat._tack_cooldown -= dt

                if boat.penalty_remaining > 0:
                    boat.penalty_remaining -= dt
                    boat.elapsed += dt
                    continue

                if self._should_tack(boat, opponent, twa_opt, upwind, wind_dir, rng):
                    boat.tack *= -1
                    boat._just_tacked = True
                    boat._tack_cooldown = cooldown_time
                    if upwind:
                        boat.penalty_remaining = self._sample_penalty(
                            self.tack_penalty, self.tack_penalty_std, rng)
                        boat.tack_count += 1
                    else:
                        boat.penalty_remaining = self._sample_penalty(
                            self.gybe_penalty, self.gybe_penalty_std, rng)
                        boat.gybe_count += 1
                    boat.elapsed += dt
                    continue

                # Speed with shadow + trim noise
                effective_tws = tws
                if self._is_in_shadow(opponent, boat, wind_dir):
                    effective_tws *= 0.90

                bs_kts = boat.polar(effective_tws, twa_opt)
                bs_kts = self._apply_trim_noise(bs_kts, rng)
                bs = bs_kts * self.KTS_TO_MS

                if upwind:
                    heading_rad = np.radians(wind_dir + boat.tack * twa_opt)
                else:
                    heading_rad = np.radians(wind_dir + 180.0 + boat.tack * (180.0 - twa_opt))

                dx = bs * np.sin(heading_rad) * dt + cur_x * dt
                dy = bs * np.cos(heading_rad) * dt + cur_y * dt

                # Interpolate exact crossing time when boat reaches mark
                prev_y = boat.y
                boat.x += dx
                boat.y += dy
                boat.speed = bs

                crossed = (upwind and boat.y >= self.leg_distance_m and prev_y < self.leg_distance_m) or \
                          (not upwind and boat.y <= 0 and prev_y > 0)
                if crossed and abs(dy) > 1e-9:
                    target = self.leg_distance_m if upwind else 0.0
                    frac = (target - prev_y) / dy
                    boat.elapsed += frac * dt
                else:
                    boat.elapsed += dt

            if step % 5 == 0:
                trace_A.append((boat_A.x, boat_A.y))
                trace_B.append((boat_B.x, boat_B.y))

        return trace_A, trace_B

    def run_single(self, seed=None):
        """Run one race.

        Returns
        -------
        dict with keys: time_A, time_B, tack_count_A, tack_count_B,
            gybe_count_A, gybe_count_B, trace_A, trace_B
        """
        rng = np.random.default_rng(seed)
        boat_A = Boat(self.polar_A, "A", self.boat_length)
        boat_B = Boat(self.polar_B, "B", self.boat_length)

        # Random start-line offset — one boat wins the pin (0.5–2 boat
        # lengths of lateral separation, slight y jitter).  This breaks
        # perfect symmetry just as a real start does.
        pin_offset = (0.5 + 1.5 * rng.random()) * self.boat_length
        if rng.random() < 0.5:
            boat_A.x = pin_offset / 2
            boat_B.x = -pin_offset / 2
        else:
            boat_A.x = -pin_offset / 2
            boat_B.x = pin_offset / 2
        # Small along-course jitter (0–0.5 boat lengths) models timing
        # differences at the start gun.
        boat_A.y = rng.random() * 0.5 * self.boat_length
        boat_B.y = rng.random() * 0.5 * self.boat_length

        self.wind_model.reset(tws=self.tws, twd=0.0)

        all_trace_A = []
        all_trace_B = []

        for leg_idx in range(self.n_legs * 2):
            upwind = (leg_idx % 2 == 0)

            if not upwind:
                boat_A.y = self.leg_distance_m
                boat_B.y = self.leg_distance_m

            tA, tB = self._run_leg(boat_A, boat_B, upwind, rng)
            all_trace_A.extend(tA)
            all_trace_B.extend(tB)

            boat_A.x = 0.0
            boat_B.x = 0.0

        return {
            "time_A": boat_A.elapsed,
            "time_B": boat_B.elapsed,
            "tack_count_A": boat_A.tack_count,
            "tack_count_B": boat_B.tack_count,
            "gybe_count_A": boat_A.gybe_count,
            "gybe_count_B": boat_B.gybe_count,
            "trace_A": all_trace_A,
            "trace_B": all_trace_B,
        }

    def run_monte_carlo(self, n_runs=100):
        """Run N races with different random seeds.

        Returns
        -------
        dict with keys:
            wins_A, wins_B : int
            deltas : list of float (time_A - time_B in seconds)
            mean_delta : float
            traces : tuple (trace_A, trace_B) from first run
            results : list of single-race result dicts
        """
        deltas = []
        wins_A = 0
        wins_B = 0
        first_traces = None
        all_results = []

        for i in range(n_runs):
            result = self.run_single(seed=i)
            all_results.append(result)
            delta = result["time_A"] - result["time_B"]
            deltas.append(delta)
            if result["time_A"] < result["time_B"]:
                wins_A += 1
            elif result["time_B"] < result["time_A"]:
                wins_B += 1
            if first_traces is None:
                first_traces = (result["trace_A"], result["trace_B"])

        return {
            "wins_A": wins_A,
            "wins_B": wins_B,
            "deltas": deltas,
            "mean_delta": float(np.mean(deltas)),
            "traces": first_traces,
            "results": all_results,
        }

    @staticmethod
    def build_polar_interp(tws_array, twa_array, results_4d):
        """Build callable polar from VPP results.

        Parameters
        ----------
        tws_array : array
            TWS values (m/s).
        twa_array : array
            TWA values (degrees).
        results_4d : array, shape (n_tws, n_twa, n_sails, 5)

        Returns
        -------
        callable(tws_kts, twa_deg) -> boat_speed_kts
        """
        best_speed = np.max(results_4d[:, :, :, 0], axis=2)
        tws_kts = tws_array / 0.5144
        interp = RegularGridInterpolator(
            (tws_kts, twa_array), best_speed,
            bounds_error=False, fill_value=0.0,
        )
        return lambda tws, twa: float(np.clip(interp((tws, twa)), 0.0, None))
