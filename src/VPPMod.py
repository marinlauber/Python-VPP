#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.2"
__email__ = "marinlauber@gmail.com"

import logging
import warnings

import numpy as np
from scipy.optimize import root
from tqdm import trange

from src.AeroMod import AeroMod
from src.HydroMod import HydroMod
from src.UtilsMod import KNOTS_TO_MPS, json_write, polar_plot, sail_chart
from src.YachtMod import Yacht as YachtClass

logger = logging.getLogger(__name__)
debug_mode = logging.getLogger().getEffectiveLevel() == logging.DEBUG
info_mode = logging.getLogger().getEffectiveLevel() == logging.INFO

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

        # flag for later
        self.upToDate = False

        # debbuging flag
        self.debbug = False
        if not self.debbug:
            warnings.filterwarnings(
                "ignore", "The iteration is not making good progress"
            )

    def set_analysis(self, tws_range, twa_range):
        """
        Sets the analysis range.
        Parameters
        ----------
        tws_range
            A numpy.array with the different TWS to run the analysis at.
        twa_range
            A numpy.array with the different TWA to run the analysis at.
        """

        if tws_range.max() <= 35.0 and tws_range.min() >= 2.0:
            logging.info("Analysis set for TWS: " + str(tws_range))
            self.tws_range = tws_range * KNOTS_TO_MPS
        else:
            logging.info("Analysis only valid for TWS range : 2. < TWS < 35. knots.")

        if twa_range.max() <= 180.0 and twa_range.min() >= 0.0:
            self.twa_range = twa_range
            logging.info("Analysis set for TWA: " + str(self.twa_range))
        else:
            logging.info(
                "Analysis only valid for TWA range : 0. < TWA < 180. degrees."
            )

        # prepare storage array
        self.Nsails = len(self.yacht.sails) - 1  # main not counted
        self.store = np.zeros(
            (len(self.tws_range), len(self.twa_range), self.Nsails, 5)
        )
        self.sail_name = [
            self.yacht.sails[0].name + " + " + self.yacht.sails[n + 1].name
            for n in range(self.Nsails)
        ]
        logging.info("Using sail quiver " + str(self.sail_name))
        # tws bounds for downwind/upwind sails
        self.lim_up = 60.0
        self.lim_dn = 135.0 if (self.Nsails != 1) else 200.0

        # minimzation bounds
        self.bnds = ((0, None), (0.0, self.phi_max), (-2.0, 6.0), (0.62, 1.0), (0, 2.0))

        # flag for later
        self.upToDate = True

    def Vb(self, x, grad):
        # this should not be used
        if grad.size > 0:
            grad = 0.0
        return self.vb0

    def SumForce(self, res, x, grad, twa_, tws_):
        # this should not be used
        if grad.size > 0:
            grad[:, :] = 0.0

        vb0 = x[0]
        phi0 = x[1]
        leeway = x[2]
        flat = x[3]
        red = x[4]

        Fxh, Fyh, Mxh = self.hydro.update(vb0, phi0, leeway)
        Fxa, Fya, Mxa = self.aero.update(vb0, phi0, tws_, twa_, flat, red)

        res[0] = Fxh - Fxa
        res[1] = Mxh - Mxa
        res[2] = Fyh - Fya

        return None

    def run(self):
        """
        Run the analysis for the given analysis range.
        """

        if not self.upToDate:
            raise AssertionError("VPP run stop: no analysis set!")

        for i, tws in enumerate(self.tws_range):
            logging.info("Sailing in TWS : %.1f" % (tws / KNOTS_TO_MPS))

            for n in range(self.Nsails):
                self.aero.sails[1] = self.yacht.sails[n + 1]

                logging.info(
                    "Sail Config : " + self.aero.sails[0].name + " + " + self.aero.sails[1].name
                )

                self.aero.up = self.aero.sails[1].up

                for j in trange(len(self.twa_range), disable=not info_mode):
                    twa = self.twa_range[j]

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
                        continue
                    if (self.aero.up == False) and (twa <= self.lim_up):
                        continue

                    sol = root(
                        self.resid,
                        [self.vb0, self.phi0, self.leeway0],
                        args=(twa, tws),
                        method="lm",
                    )
                    self.vb0, self.phi0, self.leeway0 = res = sol.x

                    if not sol.success:
                        logger.debug(sol.message)

                    # # contraints
                    # con1 = {'type': 'eq', 'fun': self.Fx, 'args': (twa, tws)}
                    # con2 = {'type': 'eq', 'fun': self.Fy, 'args': (twa, tws)}
                    # con3 = {'type': 'eq', 'fun': self.Mx, 'args': (twa, tws)}
                    # con = (con1, con2, con3)

                    # # initial guess at this twa/tws
                    # x0 = [self.vb0, self.phi0, self.leeway0, self.flat, self.red]

                    # # minimize
                    # sol = minimize(self.objective, args=(twa, tws), x0=x0, method='SLSQP',
                    #                constraints=con, bounds=self.bnds, tol=1e-2,
                    #                options={"maxiter": 100, "disp": debug_mode})

                    # # get result
                    # self.vb0, self.phi0, self.leeway0, self.flat, self.red = res = sol.x

                    # logging.info(
                    #     "Equilibrium residuals (Fx, Fy, Mx): (%.4f, %.4f, %.4f)" % (self.resid(sol.x, twa, tws))
                    # )

                    # store data for later
                    self.store[i, j, n, : len(res)] = (
                        res[:] * np.array([1.0 / KNOTS_TO_MPS, 1, 1, 1, 1])[: len(res)]
                    )

        logging.info("Optimization successful.")

    def resid(self, x0, twa, tws):
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
        Returns
        -------
        Numpy.Array
            Residuals on each DOF
        """

        vb0 = x0[0]
        phi0 = x0[1]  # min(x0[1], self.phi_max)
        leeway = x0[2]
        flat = 1.0  # x0[3]
        red = 1.0  # x0[4]

        Fxh, Fyh, Mxh = self.hydro.update(vb0, phi0, leeway)
        Fxa, Fya, Mxa = self.aero.update(vb0, phi0, tws, twa, flat, 2.0)

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
