#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import Akima1DInterpolator

class Sail(object):
    def __init__(self, name, type, area, vce, up=True):

        self.name = name
        self.type = type
        self.area = area
        self.vce = vce
        # get sails coefficients
        self._build_interp_func(self.type)
        self.bk = 1.0  # always valid for main, only AWA<135 for jib
        self.up = up  # is that an upwind sail?


    def _build_interp_func(self, fname):
        """
        build interpolation function and returns it in a list
        """
        a = np.genfromtxt("dat/" + fname + ".dat", delimiter=",", skip_header=1)
        self.kp = a[0, 0]
        # linear for now, this is not good, might need to polish data outside
        self.interp_cd = Akima1DInterpolator(a[1, :], a[2, :])
        self.interp_cl = Akima1DInterpolator(a[1, :], a[3, :])

    def cl(self, awa):
        awa = max(0, min(awa, 180))
        return self.interp_cl(awa)

    def cd(self, awa):
        awa = max(0, min(awa, 180))
        return self.interp_cd(awa)

    def debbug_coeffs(self, N=256):
        awa = np.linspace(0, 180, N)
        coeffs = np.empty((N, 2))
        for i, a in enumerate(awa):
            coeffs[i, 0] = self.cd(a)
            coeffs[i, 1] = self.cl(a)
        plt.plot(awa, coeffs[:, 0], awa, coeffs[:, 1])
        plt.title(self.type + str(self.kp))
        plt.legend(["CD", "CL"])
        plt.show()


class Main(Sail):
    def __init__(self, name, P, E, Roach, BAD):
        """
        Initialize mainsail

        This function initializes an object of class Main which inherits the class Sail.
        It calculates the area, the Vertical Center of Effort (vce),
        sets CE = 1 and calls the super class constructor.

        Parameters
        ----------
        name : string
            Of the sail

        P : Float
            Height of the Mainsail  in meters

        E: Float
            Length (Foot) of the Mainsail  in meters

        Roach: Float
            Percentage by which the triangular area is increased in order to obtain the mainsail area.
            This is area behind the line from clew to head.
            To get this number you have to calculate  Mainsail_area / (P*E/2) -1

        BAD: Float
            Boom Above Deck: Distance between boom and Deck  in meters

        Returns
        -------
        Main
            Object of type Main( Sail )

        See Also
        --------
        Jib( Sail )

        Examples
        --------
        >>> Main("MN1", P=16.60, E=5.60, Roach=0.1, BAD=1.0)
        <src.SailMod.Main object at 0xFFFFFFFFF>
        """
        self.name = name
        self.type = "main"
        self.P = P
        self.E = E
        self.roach = Roach
        self.BAD = BAD
        self.area0 = 0.5 * P * E * (1 + self.roach)
        self.vce = P / 3.0 * (1 + self.roach) + self.BAD
        super().__init__(self.name, self.type, self.area0, self.vce)
        self.measure()

    def measure(self, rfm=1, ftj=1):
        self.P_r = self.P*rfm
        self.vce = self.P_r / 3.0 * (1 + self.roach) + self.BAD
        self.area = self.area0*rfm**2
        self.CE = 1.


class Jib(Sail):
    def __init__(self, name, I, J, LPG, HBI):
        self.name = name
        self.type = "jib"
        self.I = I
        self.J = J
        self.IG = self.I
        self.LPG = LPG
        self.HBI = HBI
        self.area = 0.5 * I * max(J, LPG)
        self.vce = I / 3.0 + HBI
        super().__init__(self.name, self.type, self.area, self.vce)
        self.measure()

    def measure(self, rfm=1, ftj=1):
        self.LPG_r = self.LPG*ftj
        self.IG_r = self.IG*ftj
        self.area = 0.5 * self.I * max(self.J, self.LPG_r)


class Kite(Sail):
    def __init__(self, name, area, vce):
        self.name = name
        self.type = "kite"
        self.area = area
        self.min_area = self.area
        self.vce = vce
        super().__init__(self.name, self.type, self.area, self.vce, up=False)
        self.measure()

    def measure(self, rfm=1, ftj=1):
        pass

if __name__=="__main__":
    pass
