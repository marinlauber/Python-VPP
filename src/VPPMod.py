#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.optimize import minimize

from src.AeroMod import AeroMod
from src.HydroMod import HydroMod
from src.UtilsMod import KNOTS_TO_MPS, json_write, polar_plot, sail_chart
from src.YachtMod import Yacht as YachtClass

logger = logging.getLogger(__name__)


# Residual scales (N, N, N.m) so the three equilibrium equations have similar magnitude
RESID_SCALE = np.array([1e3, 1e3, 1e4])
# Tolerance on the scaled residuals for a point to count as an equilibrium
RESID_TOL = 1e-4
# Minimum flat (ORC 2026, 5.1.3)
FLAT_MIN = 0.53


def _equilibrium(x, aero, hydro, tws, twa):
    """Scaled force/moment imbalance (Fx, Fy, Mx) at state x = [vb, phi, leeway, flat, red]."""
    vb, phi, leeway, flat, red = x
    Fxh, Fyh, Mxh = hydro.update(vb, phi, leeway, twa, tws)
    Fxa, Fya, Mxa = aero.update(vb, phi, tws, twa, flat, red)
    return np.array([Fxh - Fxa, Fyh - Fya, Mxh - Mxa]) / RESID_SCALE


def _solve_point(aero, hydro, tws, twa, phi_max, guesses, fallbacks=(), red_bounds=(0.5, 2.0)):
    """Find the fastest equilibrium at one (tws, twa) for the current sail set.

    Maximises boat speed over [vb, phi, leeway, flat, red] subject to force and
    moment equilibrium, with heel bounded by phi_max. Sails are flattened
    (flat: 1.0 -> FLAT_MIN) and reefed (red within red_bounds) only as much
    as is fast.
    Every guess is tried and the fastest converged solution is kept; the
    fallback guesses are only tried if none of them converge.

    Returns
    -------
    ndarray or None
        [vb (m/s), phi, leeway, flat, red], or None if no equilibrium exists
        (e.g. a kite that cannot be carried at this heel limit).
    """
    bounds = [(0.0, None), (0.0, phi_max), (-2.0, 6.0), (FLAT_MIN, 1.0), red_bounds]
    lo = np.array([b[0] for b in bounds], dtype=float)
    hi = np.array([np.inf if b[1] is None else b[1] for b in bounds])
    best = None
    for k, x0 in enumerate([*guesses, *fallbacks]):
        x0 = np.clip(x0, lo, hi)
        if k >= len(guesses) and best is not None:
            break
        sol = minimize(
            lambda x: -x[0], x0, method="SLSQP", bounds=bounds,
            constraints={"type": "eq", "fun": _equilibrium, "args": (aero, hydro, tws, twa)},
            options={"maxiter": 300, "ftol": 1e-10},
        )
        if not sol.success:
            continue
        if np.abs(_equilibrium(sol.x, aero, hydro, tws, twa)).max() > RESID_TOL:
            continue
        if best is None or sol.x[0] > best[0]:
            best = sol.x
    return best


def _solve_row(yacht, tws, twa_range, n, phi_max, lim_up, lim_dn):
    """Solve all TWAs for one TWS and sail set, warm-starting from the previous TWA.

    Creates its own AeroMod/HydroMod so there is no shared mutable state.
    This is a module-level function so it can be pickled by ProcessPoolExecutor.

    Returns
    -------
    ndarray
        Shape (len(twa_range), 5), rows [vb_kts, phi, leeway, flat, red];
        skipped or infeasible points are left at 0.
    """
    aero = AeroMod(yacht)
    hydro = HydroMod(yacht)
    sail = yacht.sails[n + 1]
    aero.sails[1] = sail
    aero.up = sail.up
    # upwind: RED 2 -> 1 reduces the jib, 1 -> 0.5 reefs the main;
    # downwind: RED is the kite reef factor
    red_bounds = (0.5, 2.0) if sail.up else (getattr(sail, "min_reef", 0.85), 1.0)
    # kites carry their own (lower) heel limit, ORC ~21.5 deg
    phi_max = min(phi_max, getattr(sail, "max_heel", phi_max))

    row = np.zeros((len(twa_range), 5))
    prev = None
    for j, twa in enumerate(twa_range):
        # don't do low twa with downwind sails (and vice versa)
        if aero.up and twa >= lim_dn:
            continue
        if not aero.up and twa <= lim_up:
            continue

        guesses = [np.array([0.6 * tws, 10.0, 3.0, 1.0, 2.0])]
        if prev is not None:
            guesses.insert(0, prev)
        fallbacks = [np.array([3.5, 20.0, 3.0, 1.0, 2.0]), np.array([0.4 * tws, 5.0, 3.0, 1.0, 2.0])]

        x = _solve_point(aero, hydro, tws, twa, phi_max, guesses, fallbacks, red_bounds)
        if x is None:
            logger.debug("No equilibrium for %s at TWS %.1f TWA %.1f",
                         sail.name, tws / KNOTS_TO_MPS, twa)
            continue
        prev = x
        row[j] = x * np.array([1.0 / KNOTS_TO_MPS, 1, 1, 1, 1])
    return row


class VPP(object):
    """A VPP Class that run an analysis on a given Yacht."""

    def __init__(self, Yacht):
        """
        Initializes the VPP model
        Parameters
        ----------
        Yacht
            A Yacht object with Appendages and Sails
        """
        # build model
        self.yacht: YachtClass = Yacht
        self.aero = AeroMod(self.yacht)
        self.hydro = HydroMod(self.yacht)

        # maximum allows heel angle
        self.phi_max = 35.0

        self.upToDate = False

    def set_analysis(self, tws_range, twa_range, phi_max=35.0):
        """
        Sets the analysis range.
        Parameters
        ----------
        tws_range
            A numpy.array with the different TWS to run the analysis at.
        twa_range
            A numpy.array with the different TWA to run the analysis at.
        """

        self.phi_max = phi_max

        if tws_range.size == 0:
            raise ValueError("TWS range is empty. Ensure min and max TWS are not equal.")
        if twa_range.size == 0:
            raise ValueError("TWA range is empty. Ensure min and max TWA are not equal.")

        if tws_range.min() < 2.0 or tws_range.max() > 35.0:
            raise ValueError(
                f"TWS range [{tws_range.min():.1f}, {tws_range.max():.1f}] "
                f"is outside valid bounds [2.0, 35.0] knots."
            )
        self.tws_range = tws_range * KNOTS_TO_MPS
        logger.debug("Analysis set for TWS: %s", tws_range)

        if twa_range.min() < 0.0 or twa_range.max() > 180.0:
            raise ValueError(
                f"TWA range [{twa_range.min():.1f}, {twa_range.max():.1f}] "
                f"is outside valid bounds [0.0, 180.0] degrees."
            )
        self.twa_range = twa_range
        logger.debug("Analysis set for TWA: %s", self.twa_range)

        # prepare storage array
        self.Nsails = len(self.yacht.sails) - 1  # main not counted
        self.store = np.zeros(
            (len(self.tws_range), len(self.twa_range), self.Nsails, 5)
        )
        self.sail_name = [
            self.yacht.sails[0].name + " + " + self.yacht.sails[n + 1].name
            for n in range(self.Nsails)
        ]
        logging.debug("Using sail quiver ", self.sail_name)
        # tws bounds for downwind/upwind sails
        self.lim_up = 60.0
        self.lim_dn = 135.0 if (self.Nsails != 1) else 200.0

        # flag for later
        self.upToDate = True

    def run(self, method="sequential", progress_callback=None):
        """
        Run the analysis for the given analysis range.

        At each point the boat speed is maximised over [vb, phi, leeway, flat, red]
        subject to force/moment equilibrium and phi <= phi_max. Points where no
        equilibrium exists (e.g. a kite that cannot be carried) are left at 0.

        Parameters
        ----------
        method
            "sequential" (default) or "parallel" (multiprocessing across TWS and
            sail sets, identical results). "iterative" and "5dof" are accepted
            as aliases of "sequential" for backward compatibility.
        progress_callback
            Optional callable(tws_index, tws_kts, n_tws) invoked after each
            TWS wind speed is completed (sequential only).
        """
        if method in ("iterative", "5dof"):
            method = "sequential"
        if method not in ("sequential", "parallel"):
            raise ValueError(f"Unknown method '{method}'. Use 'sequential' or 'parallel'.")

        if not self.upToDate:
            raise RuntimeError("VPP run stop: no analysis set!")

        if method == "parallel":
            return self._run_parallel()

        n_tws = len(self.tws_range)
        for i, tws in enumerate(self.tws_range):
            logging.debug("Sailing in TWS : %.1f" % (tws / KNOTS_TO_MPS))
            for n in range(self.Nsails):
                self.store[i, :, n, :] = _solve_row(
                    self.yacht, tws, self.twa_range, n,
                    self.phi_max, self.lim_up, self.lim_dn,
                )
            if progress_callback:
                progress_callback(i, tws / KNOTS_TO_MPS, n_tws)

        logging.info("Optimization successful.")

    def _run_parallel(self):
        """Run the row solver in parallel across TWS and sail sets."""
        work = [(i, n) for i in range(len(self.tws_range)) for n in range(self.Nsails)]
        with ProcessPoolExecutor() as pool:
            rows = pool.map(
                _solve_row,
                *zip(*[(self.yacht, self.tws_range[i], self.twa_range, n,
                        self.phi_max, self.lim_up, self.lim_dn) for i, n in work])
            )
            for (i, n), row in zip(work, rows):
                self.store[i, :, n, :] = row

        logging.info("Parallel optimization successful.")

    def resid(self, x0, twa, tws, flat=1.0, red=2.0):
        """
        Computes the residuals of the force/moment equilibrium at the given state.
        Parameters
        ----------
        x0
            A numpy array of the variables (DOF): vb (m/s), phi, leeway.
        twa
            A float of the TWA at which to compute the residuals.
        tws
            A float of the TWs at which to compute the residuals.
        flat
            Sail flattening factor (0.62 to 1.0). Default 1.0 (no flattening).
        red
            Reef/reduction factor. Default 2.0 (full sails, no reef/furl).
        Returns
        -------
        Numpy.Array
            Scaled (Fx, Fy, Mx) imbalance, see RESID_SCALE.
        """
        return _equilibrium([x0[0], x0[1], x0[2], flat, red], self.aero, self.hydro, tws, twa)

    def results(self):
        """
        Return a dict of the VPP results.
        """
        return {
            "name": self.yacht.Name,
            "tws": self.tws_range.tolist(),
            "twa": self.twa_range.tolist(),
            "sails": self.sail_name,
            "results": self.store.tolist(),
        }

    def write(self, fname):
        json_write(self.results(), fname)

    def polar(self, n=1, save=False, fname="Polars.pdf"):
        polar_plot([self], n, save, fname)

    def SailChart(self, save=False, fname="SailChart.pdf"):
        sail_chart(self, save, fname)
