#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__ = "M.Lauber@soton.ac.uk"

import logging
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.optimize import least_squares, minimize, root
from tqdm import trange

from src.AeroMod import AeroMod
from src.HydroMod import HydroMod
from src.UtilsMod import KNOTS_TO_MPS, json_write, polar_plot, sail_chart
from src.YachtMod import Yacht as YachtClass

logger = logging.getLogger(__name__)
debug_mode = logging.getLogger().getEffectiveLevel() == logging.DEBUG


def _solve_point(yacht, tws, twa, sail_index, phi_max, lim_up, lim_dn):
    """Solve one (tws, twa, sail) grid point independently.

    Creates its own AeroMod/HydroMod so there is no shared mutable state.
    This is a module-level function so it can be pickled by ProcessPoolExecutor.

    Returns
    -------
    tuple
        (i, j, n, result_array) where result_array is [vb_kts, phi, leeway, flat, red],
        or None if the point was skipped.
    """
    i, j, n = sail_index

    aero = AeroMod(yacht)
    hydro = HydroMod(yacht)
    aero.sails[1] = yacht.sails[n + 1]
    aero.up = aero.sails[1].up

    # Skip invalid sail/TWA combinations
    Nsails = len(yacht.sails) - 1
    dn_limit = 135.0 if Nsails != 1 else 200.0
    if aero.up and twa >= dn_limit:
        return None
    if not aero.up and twa <= lim_up:
        return None

    # Initial guesses
    vb0 = 0.8 * tws
    phi0 = 0.0
    leeway0 = 100.0 / twa if (twa > 1.0 and 100.0 / twa < 2 * tws) else 2 * tws

    def resid(x0, twa_, tws_, flat=1.0, red=2.0):
        vb_, phi_, leeway_ = x0
        Fxh, Fyh, Mxh = hydro.update(vb_, phi_, leeway_, twa_)
        Fxa, Fya, Mxa = aero.update(vb_, phi_, tws_, twa_, flat, red)
        return [(Fxh - Fxa) ** 2, (Mxh - Mxa) ** 2, (Fyh - Fya) ** 2]

    flat = 1.0
    red = 2.0

    sol = root(resid, [vb0, phi0, leeway0],
               args=(twa, tws, flat, red), method="lm")
    vb, phi, leeway = sol.x

    if phi <= phi_max:
        res = np.array([vb, phi, leeway, flat, red])
        res[0] /= KNOTS_TO_MPS
        return (i, j, n, res)

    # Depowering: flatten then reef
    lo = [0, 0, -2]
    hi = [np.inf, phi_max, 6]
    margin = phi_max - 1.0

    def _clamp(vb_, phi_, leeway_):
        return [max(vb_, 0), min(max(phi_, 0), phi_max),
                min(max(leeway_, -2), 6)]

    for flat in np.arange(0.98, 0.60, -0.02):
        sol = least_squares(
            resid, _clamp(vb, phi_max, leeway),
            args=(twa, tws, flat, red), bounds=(lo, hi),
        )
        vb, phi, leeway = sol.x
        if phi <= margin:
            res = np.array([vb, phi, leeway, flat, red])
            res[0] /= KNOTS_TO_MPS
            return (i, j, n, res)

    flat = 0.62
    for red in np.arange(1.9, 0.45, -0.1):
        sol = least_squares(
            resid, _clamp(vb, phi_max, leeway),
            args=(twa, tws, flat, red), bounds=(lo, hi),
        )
        vb, phi, leeway = sol.x
        if phi <= margin:
            break

    res = np.array([vb, phi, leeway, flat, red])
    res[0] /= KNOTS_TO_MPS
    return (i, j, n, res)


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

        # debbuging flag
        self.debbug = False
        if not self.debbug:
            warnings.filterwarnings(
                "ignore", "The iteration is not making good progress"
            )
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

        # minimzation bounds
        self.bnds = ((0, None), (0.0, self.phi_max), (-2.0, 6.0), (0.62, 1.0), (0, 2.0))

        # flag for later
        self.upToDate = True

    def run(self, verbose=False, method="iterative", progress_callback=None):
        """
        Run the analysis for the given analysis range.
        Parameters
        ----------
        verbose
            A logical, if True, prints results of equilibrium at each TWA/TWS.
        method
            Solver method: "iterative" (3-DOF sequential with depowering loop),
            "parallel" (same solver, multiprocessing across grid points), or
            "5dof" (scipy SLSQP 5-DOF constrained optimizer).
        progress_callback
            Optional callable(current, total) invoked after each grid point.
        """

        if method == "5dof":
            return self._run_5dof(verbose)
        elif method == "parallel":
            return self._run_parallel()
        elif method != "iterative":
            raise ValueError(f"Unknown method '{method}'. Use 'iterative', 'parallel', or '5dof'.")

        if not self.upToDate:
            raise RuntimeError("VPP run stop: no analysis set!")

        total_points = len(self.tws_range) * self.Nsails * len(self.twa_range)
        current_point = 0

        for i, tws in enumerate(self.tws_range):
            logging.debug("Sailing in TWS : %.1f" % (tws / KNOTS_TO_MPS))

            for n in range(self.Nsails):
                self.aero.sails[1] = self.yacht.sails[n + 1]

                logging.debug(
                    "Sail Config : ",
                    self.aero.sails[0].name + " + " + self.aero.sails[1].name,
                )

                self.aero.up = self.aero.sails[1].up

                for j in trange(len(self.twa_range), disable=not debug_mode):
                    twa = self.twa_range[j]
                    current_point += 1

                    self.vb0 = 0.8 * tws
                    self.phi0 = 0
                    self.leeway0 = (
                        100.0 / twa
                        if (twa > 1.0 and 100.0 / twa < 2 * tws)
                        else 2 * tws
                    )
                    self.flat = 1.0
                    self.red = 2.0

                    # don't do low twa with downwind sails
                    if (self.aero.up == True) and (twa >= self.lim_dn):
                        if progress_callback:
                            progress_callback(current_point, total_points)
                        continue
                    if (self.aero.up == False) and (twa <= self.lim_up):
                        if progress_callback:
                            progress_callback(current_point, total_points)
                        continue

                    vb, phi, leeway, flat, red = self._depower_solve(twa, tws)
                    self.vb0, self.phi0, self.leeway0 = vb, phi, leeway

                    logging.debug(
                        "Equilibrium residuals (Fx, Fy, Mx): ",
                        self.resid([vb, phi, leeway], twa, tws, flat, red),
                    )

                    # store data for later
                    res = np.array([vb, phi, leeway, flat, red])
                    self.store[i, j, n, :] = res * np.array([1.0 / KNOTS_TO_MPS, 1, 1, 1, 1])

                    if progress_callback:
                        progress_callback(current_point, total_points)

        logging.info("Optimization successful.")

    def _run_parallel(self):
        """Run iterative solver in parallel across all grid points."""
        if not self.upToDate:
            raise RuntimeError("VPP run stop: no analysis set!")

        # Build work items: (yacht, tws, twa, (i,j,n), phi_max, lim_up, lim_dn)
        work = []
        for i, tws in enumerate(self.tws_range):
            for n in range(self.Nsails):
                for j, twa in enumerate(self.twa_range):
                    work.append((
                        self.yacht, tws, twa, (i, j, n),
                        self.phi_max, self.lim_up, self.lim_dn
                    ))

        with ProcessPoolExecutor() as pool:
            results = pool.map(_solve_point, *zip(*work))

        for result in results:
            if result is not None:
                i, j, n, res = result
                self.store[i, j, n, :] = res

        logging.info("Parallel optimization successful.")

    def _depower_solve(self, twa, tws):
        """Solve 3-DOF equilibrium, depowering iteratively if heel exceeds phi_max.

        Depowering follows real sailing practice:
        1. Flatten sails (flat: 1.0 -> 0.62)
        2. Reef main / furl jib (RED: 2.0 -> 0.5)

        The bounded solver pins phi at phi_max, so we check for genuine
        margin (1 degree) before accepting a solution — otherwise the boat
        is still overpowered and needs more depowering.
        """
        flat = 1.0
        red = 2.0

        sol = root(self.resid, [self.vb0, self.phi0, self.leeway0],
                   args=(twa, tws, flat, red), method="lm")
        vb, phi, leeway = sol.x

        if phi <= self.phi_max:
            return vb, phi, leeway, flat, red

        # Heel exceeds limit — use bounded solver to enforce phi <= phi_max
        lo = [0, 0, -2]
        hi = [np.inf, self.phi_max, 6]
        margin = self.phi_max - 1.0

        def _clamp_guess(vb_, phi_, leeway_):
            return [max(vb_, 0), min(max(phi_, 0), self.phi_max),
                    min(max(leeway_, -2), 6)]

        # Stage 1: Flatten sails (1.0 -> 0.62)
        for flat in np.arange(0.98, 0.60, -0.02):
            sol = least_squares(
                self.resid, _clamp_guess(vb, self.phi_max, leeway),
                args=(twa, tws, flat, red), bounds=(lo, hi),
            )
            vb, phi, leeway = sol.x
            if phi <= margin:
                return vb, phi, leeway, flat, red

        # Stage 2: Reef main / furl jib (RED: 2.0 -> 0.5)
        flat = 0.62
        for red in np.arange(1.9, 0.45, -0.1):
            sol = least_squares(
                self.resid, _clamp_guess(vb, self.phi_max, leeway),
                args=(twa, tws, flat, red), bounds=(lo, hi),
            )
            vb, phi, leeway = sol.x
            if phi <= margin:
                return vb, phi, leeway, flat, red

        # If still over, return best we got
        return vb, phi, leeway, flat, red

    def _run_5dof(self, verbose=False):
        """Run 5-DOF constrained optimization using scipy SLSQP.

        Simultaneously optimizes [vb, phi, leeway, flat, red] to maximize
        boat speed subject to force/moment equilibrium constraints.
        """
        if not self.upToDate:
            raise RuntimeError("VPP run stop: no analysis set!")

        for i, tws in enumerate(self.tws_range):
            logging.debug("Sailing in TWS : %.1f" % (tws / KNOTS_TO_MPS))

            for n in range(self.Nsails):
                self.aero.sails[1] = self.yacht.sails[n + 1]
                self.aero.up = self.aero.sails[1].up

                for j in trange(len(self.twa_range), disable=not debug_mode):
                    twa = self.twa_range[j]

                    # don't do low twa with downwind sails
                    if (self.aero.up == True) and (twa >= self.lim_dn):
                        continue
                    if (self.aero.up == False) and (twa <= self.lim_up):
                        continue

                    vb_guess = 0.8 * tws
                    leeway_guess = (
                        100.0 / twa
                        if (twa > 1.0 and 100.0 / twa < 2 * tws)
                        else 2 * tws
                    )
                    x0 = np.array([vb_guess, 0.0, leeway_guess, 1.0, 2.0])

                    def _forces(x):
                        vb, phi, leeway, flat, red = x
                        Fxh, Fyh, Mxh = self.hydro.update(vb, phi, leeway, twa)
                        Fxa, Fya, Mxa = self.aero.update(vb, phi, tws, twa, flat, red)
                        return Fxh, Fyh, Mxh, Fxa, Fya, Mxa

                    constraints = [
                        {"type": "eq", "fun": lambda x: _forces(x)[0] - _forces(x)[3]},
                        {"type": "eq", "fun": lambda x: _forces(x)[2] - _forces(x)[5]},
                        {"type": "eq", "fun": lambda x: _forces(x)[1] - _forces(x)[4]},
                    ]

                    # Cache forces to avoid redundant evaluations
                    _cache = {}

                    def _cached_forces(x):
                        key = tuple(x)
                        if key not in _cache:
                            _cache[key] = _forces(x)
                        return _cache[key]

                    constraints = [
                        {"type": "eq", "fun": lambda x: _cached_forces(x)[0] - _cached_forces(x)[3]},
                        {"type": "eq", "fun": lambda x: _cached_forces(x)[2] - _cached_forces(x)[5]},
                        {"type": "eq", "fun": lambda x: _cached_forces(x)[1] - _cached_forces(x)[4]},
                    ]

                    result = minimize(
                        lambda x: -x[0],
                        x0,
                        method="SLSQP",
                        bounds=self.bnds,
                        constraints=constraints,
                        options={"maxiter": 200, "ftol": 1e-8},
                    )

                    _cache.clear()

                    res = result.x
                    self.store[i, j, n, :] = res * np.array(
                        [1.0 / KNOTS_TO_MPS, 1, 1, 1, 1]
                    )

        logging.info("5-DOF optimization successful.")

    def resid(self, x0, twa, tws, flat=1.0, red=2.0):
        """
        Computes the residuals of the force/moment equilibrium at the given state.
        Parameters
        ----------
        x0
            A numpy array of the variables (DOF).
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
            Residuals on each DOF
        """

        vb0 = x0[0]
        phi0 = x0[1]
        leeway = x0[2]

        Fxh, Fyh, Mxh = self.hydro.update(vb0, phi0, leeway, twa)
        Fxa, Fya, Mxa = self.aero.update(vb0, phi0, tws, twa, flat, red)

        return [(Fxh - Fxa) ** 2, (Mxh - Mxa) ** 2, (Fyh - Fya) ** 2]

    @staticmethod
    def objective(x0):
        return -x0[0]

    def Fx(self, x0, twa, tws):
        return self.resid(x0, twa, tws)[0]

    def Fy(self, x0, twa, tws):
        return self.resid(x0, twa, tws)[1]

    def Mx(self, x0, twa, tws):
        return self.resid(x0, twa, tws)[2]

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

    def polar(self, n=1, save=False, fname="Polars.png"):
        polar_plot([self], n, save, fname)

    def SailChart(self, save=False, fname="SailChart.png"):
        sail_chart(self, save, fname)
