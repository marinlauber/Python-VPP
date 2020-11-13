#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__ = "M.Lauber@soton.ac.uk"

import numpy as np
import matplotlib.pyplot as plt
from scipy import interpolate
from scipy.optimize import root
from tqdm import trange
import warnings

from src.AeroMod import AeroMod
from src.HydroMod import HydroMod
from src.UtilsMod import KNOTS_TO_MPS,polar_plot,sail_chart,json_write

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
        self.yacht = Yacht
        self.aero = AeroMod(self.yacht)
        self.hydro = HydroMod(self.yacht)

        # maximum allows heel angle
        self.phi_max = 25.0

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
            self.tws_range = tws_range * KNOTS_TO_MPS
        else:
            print("Anaylis only valid for TWS range : 2. < TWS < 35. knots.")

        if twa_range.max() <= 180.0 and twa_range.min() >= 0.0:
            self.twa_range = twa_range
        else:
            print("Anaylis only valid for TWA range : 0. < TWA < 180. degrees.")

        # prepare storage array
        self.Nsails = len(self.yacht.sails) - 1  # main not counted
        self.store = np.zeros((len(self.tws_range),
                               len(self.twa_range),
                               self.Nsails,
                               3))

        # tws bounds for downwind/upwind sails
        self.lim_up = 60.0 
        self.lim_dn = 135.0 if (self.Nsails != 1) else 200.

        # flag for later
        self.upToDate = True


    def run(self, verbose=False):
        """
        Run the analysis for the given analysis range.


        Parameters
        ----------
        verbose
            A logical, if True, prints results of equilibrium at each TWA/TWS.

        """

        if not self.upToDate:
            raise "VPP run stop: no analysis set!"

        for i, tws in enumerate(self.tws_range):

            print("Sailing in TWS : %.1f" % (tws / KNOTS_TO_MPS))

            for n in range(self.Nsails):

                self.aero.sails[1] = self.yacht.sails[n + 1]

                print(
                    "Sail Config : ",
                    self.aero.sails[0].name + " + " + self.aero.sails[1].name,
                )

                self.aero.up = self.aero.sails[1].up

                for j in trange(len(self.twa_range)):

                    twa = self.twa_range[j]

                    self.vb0 = 0.8 * tws
                    self.phi0 = 0
                    self.leeway0 = 100.0 / twa if (twa > 1.0 and 100.0 / twa < 2 * tws) else 2 * tws

                    # don't do low twa with downwind sails
                    if (self.aero.up == True) and (twa >= self.lim_dn):
                        continue
                    if (self.aero.up == False) and (twa <= self.lim_up):
                        continue

                    sol = root(self.resid, [self.vb0, self.phi0, self.leeway0],
                               args=(twa, tws), method='lm')
                    self.vb0, self.phi0, self.leeway0 = res = sol.x
                    if verbose and not sol.success:
                        print(sol.message)

                    # store data for later
                    self.store[i, j, n, :] = res[:] * np.array([1.0/KNOTS_TO_MPS, 1, 1])

            print()
        print("Optimization successful.")


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
        phi0 = x0[1] # min(x0[1], self.phi_max)
        leeway = x0[2]  # ; flat=x0[3]

        Fxh, Fyh, Mxh = self.hydro.update(vb0, phi0, leeway)
        Fxa, Fya, Mxa = self.aero.update(vb0, phi0, tws, twa, 1.0, 2.0)

        return [(Fxh - Fxa) ** 2, (Mxh - Mxa) ** 2, (Fyh - Fya) ** 2]


    def results(self):
        """
        Return a dict of the VPP results.
        """
        lab = ["Speed", "Heel", "Leeway"]
        data = [ {"tws": self.tws_range.tolist(),
                  "twa": self.twa_range.tolist(),
                  "Sails":[self.yacht.sails[0].name+" + "
                  +self.yacht.sails[n+1].name for n in range(self.Nsails)]} ]
        for i in range(len(self.tws_range)):
            for j in range(len(self.twa_range)):
                for n in range(self.Nsails):
                    dic={}
                    for k in range(3):
                        dic.update( {lab[k]: self.store[i,j,n,k]} )
                    data.append(dic)
        return data


    def write(self, fname):
        json_write(self.results(), fname)


    def polar(self, n=1, save=False):
        polar_plot(self, n, save)


    def SailChart(self, save=False):
        sail_chart(self, save)
