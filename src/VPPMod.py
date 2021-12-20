#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__ = "M.Lauber@soton.ac.uk"

import nlopt
import numpy as np
import matplotlib.pyplot as plt
from scipy import interpolate
from scipy.optimize import root, minimize
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
        self.phi_max = 35.0

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
            print("Analysis set for TWS: ", tws_range)
            self.tws_range = tws_range * KNOTS_TO_MPS
        else:
            print("Anaylis only valid for TWS range : 2. < TWS < 35. knots.")

        if twa_range.max() <= 180.0 and twa_range.min() >= 0.0:
            self.twa_range = twa_range
            print("Analysis set for TWA: ", self.twa_range)
        else:
            print("Anaylis only valid for TWA range : 0. < TWA < 180. degrees.")

        # prepare storage array
        self.Nsails = len(self.yacht.sails) - 1  # main not counted
        self.store = np.zeros((len(self.tws_range),
                               len(self.twa_range),
                               self.Nsails,
                               5))
        self.sail_name = [self.yacht.sails[0].name+" + "+
                          self.yacht.sails[n+1].name for n in range(self.Nsails)]
        print("Using sail quiver ", self.sail_name)
        # tws bounds for downwind/upwind sails
        self.lim_up = 60.0 
        self.lim_dn = 135.0 if (self.Nsails != 1) else 200.

        # minimzation bounds
        self.bnds = ((0,None),(0.0,self.phi_max),(-2.,6.),(0.62,1.),(0,2.))

        # flag for later
        self.upToDate = True
        

    def Vb(self, x, grad):
        # this should not be used
        if(grad.size > 0):
            grad =  0.0
        return self.vb0


    def SumForce(self, res, x, grad, twa_, tws_):
        # this should not be used
        if(grad.size > 0):
            grad[:,:] =  0.0

        vb0 = x[0]
        phi0 = x[1]
        leeway = x[2] 
        flat=x[3]
        red =x[4]

        Fxh, Fyh, Mxh = self.hydro.update(vb0, phi0, leeway)
        Fxa, Fya, Mxa = self.aero.update(vb0, phi0, tws_, twa_, flat, red)

        res[0] = Fxh - Fxa
        res[1] = Mxh - Mxa
        res[2] = Fyh - Fya
        
        return None


    def run_NLopt(self, verbose=False):

        if not self.upToDate:
            raise "VPP run stop: no analysis set!"

        # gradient-free optimization because the gradient of our 
        # objective function cannot be evaluated
        opt = nlopt.opt(nlopt.LN_COBYLA, 5)

        # out three parameters are x = [v_b, hell, leeway, flat, red]
        opt.set_lower_bounds([0.          ,0.          ,0., 0., 0.])
        opt.set_upper_bounds([float('inf'),self.phi_max,6., 1., 2.])

        # the function we want to maximise
        opt.set_max_objective(self.Vb)

        # set solver tolerance
        opt.set_xtol_rel(1e-6)

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
                    
                    # vector-valued constraint
                    constrain = lambda res, x, grad: self.SumForce(res, x, grad, twa_=twa, tws_=tws)
                    opt.add_equality_mconstraint(constrain, np.full(5,1e-8))

                    x0 = np.array([self.vb0, self.phi0, self.leeway0, 1., 2.])
                    res = opt.optimize(x0)

                    # store data for later
                    self.store[i, j, n, :] = res[:] * np.array([1.0/KNOTS_TO_MPS, 1, 1, 1, 1])

                    # clean up
                    opt.remove_equality_constraints()

            print()
        print("Optimization successful.")


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
                    self.flat = 1.0
                    self.red = 2.0

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
                    #                options={"maxiter": 100, "disp": verbose})

                    # # get result
                    # self.vb0, self.phi0, self.leeway0, self.flat, self.red = res = sol.x

                    # display the residual
                    if verbose:
                        print("Equilibrium residuals (Fx, Fy, Mx): ", self.resid(sol.x, twa, tws))

                    # store data for later
                    self.store[i, j, n, :len(res)] = res[:] * np.array([1.0/KNOTS_TO_MPS, 1, 1, 1, 1])[:len(res)]

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
        leeway = x0[2]
        flat = 1. #x0[3]
        red = 1. #x0[4]

        Fxh, Fyh, Mxh = self.hydro.update(vb0, phi0, leeway)
        Fxa, Fya, Mxa = self.aero.update(vb0, phi0, tws, twa, flat, 2.0)

        return [(Fxh - Fxa) ** 2, (Mxh - Mxa) ** 2, (Fyh - Fya) ** 2]

    def objective(self, x0, twa, tws):
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
        lab = ["Speed", "Heel", "Leeway", "flat", "RED"]
        data = [ {"name": self.yacht.Name,
                  "tws": self.tws_range.tolist(),
                  "twa": self.twa_range.tolist(),
                  "Sails":self.sail_name} ]
        for i in range(len(self.tws_range)):
            for j in range(len(self.twa_range)):
                for n in range(self.Nsails):
                    dic={}
                    for k in range(5):
                        dic.update( {lab[k]: self.store[i,j,n,k]} )
                    data.append(dic)
        return data


    def write(self, fname):
        json_write(self.results(), fname)


    def polar(self, n=1, save=False):
        polar_plot([self], n, save, "Figure.png")


    def SailChart(self, save=False):
        sail_chart(self, save)
