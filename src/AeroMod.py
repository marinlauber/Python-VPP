#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__ = "M.Lauber@soton.ac.uk"

import functools

import matplotlib.pyplot as plt
import numpy as np

from src.UtilsMod import build_interp_func


@functools.lru_cache(maxsize=512)
def wind_triangle(tws, twa, vb):
    """Analytical wind triangle: TWS/TWA/VB → (AWA, AWS) in degrees.

    Uses the law of cosines on the velocity triangle formed by the true
    wind, boat speed, and apparent wind vectors.
    """
    twa_rad = np.radians(twa)
    aws = np.sqrt(tws**2 + vb**2 + 2 * tws * vb * np.cos(twa_rad))
    if aws < 1e-12:
        return twa, 0.0
    cos_awa = np.clip((tws * np.cos(twa_rad) + vb) / aws, -1.0, 1.0)
    awa = np.degrees(np.arccos(cos_awa))
    return awa, aws


class AeroMod(object):
    def __init__(self, Yacht, rho=1.225, mu=0.0000181):
        """
        Aerodynamic force model.

        Computes sail drive force, side force, and heeling moment from the
        yacht's sail plan using ORC aerodynamic coefficients.

        Parameters
        ----------
        Yacht : Yacht
            Yacht object containing sail definitions and hull geometry.
        rho : float, optional
            Air density (kg/m^3). Default is 1.225 (ISA sea level).
        mu : float, optional
            Dynamic viscosity of air (Pa.s). Default is 1.81e-5.
        """
        # physical params
        self.rho = rho
        self.mu = mu
        self.flat = 1.0
        self.reef = 1.0
        self.ftj = 1.0
        self.rfm = 1.0

        # set sails and measure what is need once
        self.yacht = Yacht
        self.sails = self.yacht.sails[:2]
        # are we upwind?
        self.up = self.sails[1].up
        self._measure_sails()
        self._measure_windage()

        # coeffs interp function
        self.fcdmult = build_interp_func("fcdmult")
        self.kheff = build_interp_func("kheff")


    def _measure_windage(self):
        self.boa = self.yacht.boa
        self.loa = self.yacht.loa
        self.fbav = 0.625 * self.yacht.ff + 0.375 * self.yacht.fa


    def _measure_sails(self):
        self.fractionality = 1.0; b2=0.
        for sail in self.sails:
            sail.measure(self.rfm, self.ftj)
            if sail.type == "main":
                self.fractionality /= sail.P + sail.BAD
                b1 = sail.P_r + sail.BAD
                self.roach = sail.roach
                tf = (0.16*(sail.CE-0.024)/sail.P+0.94)*sail.P+sail.BAD
            if sail.type == "jib":
                self.fractionality *= sail.IG_r
                b2 = sail.I*sail.IG_r/sail.IG
                self.overlap = sail.LPG_r / sail.J
                self.HBI = sail.HBI
        self.eff_span_corr = (
            1.1
            + 0.08 * (self.roach - 0.2)
            + 0.5 * (0.68 + 0.31 * self.fractionality + 0.0075 * self.overlap - 1.1)
        )
        self.b = max(b1, b2)
        # assumes no mizain mast
        self.heff_height_max_spi = max(tf+self.HBI, 0)


    # prototype top function in hydro mod
    def update(self, vb, phi, tws, twa, flat, RED):
        """
        Update aerodynamic forces for current sailing state.

        Solves the wind triangle, computes sail coefficients, and projects
        forces into the boat reference frame.

        Parameters
        ----------
        vb : float
            Boat speed (m/s).
        phi : float
            Heel angle (degrees).
        tws : float
            True wind speed (m/s).
        twa : float
            True wind angle (degrees).
        flat : float
            Sail flattening factor (0.62 to 1.0). Reduces lift and drag.
        RED : float
            Reef/reduction factor. Values > 1 apply jib furling (ftj = RED - 1),
            values <= 1 apply mainsail reefing (rfm = RED).

        Returns
        -------
        tuple of float
            (Fx, Fy, Mx) — drive force (N), side force (N), heeling moment (N.m).
        """
        self.vb = max(0, vb)
        self.phi = max(0, phi)
        self.tws = tws
        self.twa = twa
        # gradual flattening of the sails with tws increase, min is 0.62 from 17 knots
        self.flat = flat #np.where(tws<2.5, 1, np.where(tws < 8.5, 0.81 + 0.19 * np.cos((tws - 2.5) / 6 * np.pi), 0.62))
        self.ftj = max(RED-1., 0.)
        self.rfm = min(RED, 1.)

        self._measure_sails()
        self._update_windTriangle()
        self._area()
        self._compute_forces()

        return self.Fx, self.Fy, self.Mx

    def _compute_forces(self):
        """
        Computes forces for equilibrium.
        """
        # get new coeffs
        self._get_coeffs()

        # instead of writing many time
        awa = self.awa / 180.0 * np.pi

        # lift and drag
        self.lift = 0.5 * self.rho * self.aws ** 2 * self.area * self.cl
        self.drag = 0.5 * self.rho * self.aws ** 2 * self.area * self.cd + self._get_Rw(awa)

        # project into yacht coordinate system
        self.Fx = self.lift * np.sin(awa) - self.drag * np.cos(awa)
        self.Fy = self.lift * np.cos(awa) + self.drag * np.sin(awa)

        # side-force is horizontal component of Fh
        self.Fy *= np.cos(np.radians(self.phi))

        # heeling moment
        self.Mx = self.Fy * self._vce()


    def _get_Rw(self, awa):
        Rw = 0.5 * self.rho * self.aws ** 2 * self._get_Aref(awa) * 0.816
        return Rw * np.cos(awa / 180.0 * np.pi)


    def _get_Aref(self, awa):
        # only hull part
        d = 0.5 * (1 - np.cos(awa / 90.0 * np.pi))
        return self.fbav * ((1 - d) * self.boa + d * self.loa)


    def _get_coeffs(self):
        """
        generate sail-set total lift and drag coefficient.
        """
        # lift (Clmax) and parasitic drag (Cd0max)
        self.cl = 0.0
        self.cd = 0.0
        kpp = 0.0
        sail_cd = {}

        for sail in self.sails:
            cl_i = sail.cl(self.awa)
            cd_i = sail.cd(self.awa)
            sail_cd[id(sail)] = cd_i
            self.cl += cl_i * sail.area * sail.bk
            self.cd += cd_i * sail.area * sail.bk
            kpp += cl_i ** 2 * sail.area * sail.bk * sail.kp

        self.cl /= self.area
        self.cd /= self.area

        # viscous quadratic parasitic drag and induced drag
        devisor_1 = self.area * self.cl ** 2
        devisor_2 = np.pi * self._heff(self.awa) ** 2
        self.CE = (kpp / devisor_1 if devisor_1 else 0.0) + (self.area / devisor_2 if devisor_2 else 0.0)

        # fraction of parasitic drag due to jib
        self.fcdj = 0.0
        for sail in self.sails:
            if sail.type == "jib":
                self.fcdj = (
                    sail.bk * sail_cd[id(sail)] * sail.area / (self.cd * self.area)
                )

        # final lift and drag
        self.cd = self.cd * (
            self.flat * self.fcdmult(self.flat) * self.fcdj + (1 - self.fcdj)
        ) + self.CE * self.cl ** 2 * self.flat ** 2 * self.fcdmult(self.flat)
        self.cl = self.flat * self.cl


    def _update_windTriangle(self):
        """
        find AWS and AWA for a given TWS, TWA and VB
        """
        self.awa, self.aws = wind_triangle(self.tws, self.twa, self.vb)


    def _area(self):
        """
        Fill sail area variable
        """
        self.area = 0.0
        for sail in self.sails:
            self.area += sail.area


    def _vce(self):
        """
        Vertical centre of effort, lift/drag weighted.
        """
        sum = 0.0
        for sail in self.sails:
            cl2 = sail.cl(self.awa)**2
            cd2 = sail.cd(self.awa)**2
            sum += sail.area * sail.vce * sail.bk * np.sqrt(cl2+cd2)
        self._area()
        deltaCH = 0 if self.sails[1].up!=True else (1-self.ftj)*0.05*self.sails[1].IG
        Zce = sum/(self.area*np.sqrt(self.cl**2+self.cd**2)) - deltaCH
        return (Zce*(1-0.203*(1-self.flat)-0.451*(1-self.flat)*(1-self.fractionality)))


    def phi_up(self):
        """
        heel angle correction for AWA and AWS (5.51), this is in Radians!
        """
        return 0.5 * (self.phi + 10 * (self.phi / 30.0) ** 2) / 180.0 * np.pi


    def _heff(self, awa):
        awa = max(0, min(awa, 90))
        if self.up:
            cheff = self.eff_span_corr * self.kheff(awa)
        else:
            cheff = 1.0 / self.b * self.reef * self.heff_height_max_spi
        return (self.b + self.HBI) * cheff

    #
    # -- utility functions
    #
    def debbug(self):
        for sail in self.yacht.sails:
            sail.debbug_coeffs()
        flat = np.linspace(0, 1, 64)
        awa = np.linspace(0, 90, 64)
        res1 = np.empty_like(flat)
        res2 = np.empty_like(awa)
        for i in range(64):
            res1[i] = self.fcdmult(flat[i])
            res2[i] = self.kheff(awa[i])
        plt.plot(flat, res1)
        plt.show()
        plt.plot(awa, res2)
        plt.show()

    def print_state(self):
        self.update(self.vb, self.phi, self.tws, self.twa, self.twa)
        print("AeroMod state:")
        print(" TWA is :  %.2f (deg)" % self.twa)
        print(" TWS is :  %.2f (m/s)" % self.tws)
        print(" AWA is :  %.2f (deg)" % self.awa)
        print(" AWS is :  %.2f (m/s)" % self.aws)
        print(" Vb is :   %.2f (m/s)" % self.vb)
        print(" Heel is : %.2f (deg)" % self.phi)
        print(" Drive is: %.2f (N)" % self.Fx)
        print(" SSF is :  %.2f (N)" % self.Fy)
        print(" HM is :   %.2f (Nm)" % self.Mx)
        print(" Cl is :   %.2f (-)" % self.cl)
        print(" Cd is :   %.2f (-)" % self.cd)
        print(" Flat is : %.2f (-)" % self.flat)
        print(" Sail area:")
        for sail in self.sails:
            print(" - " + sail.type + " : %.2f (m^2)" % sail.area)


if __name__ == "__main__":
    pass
