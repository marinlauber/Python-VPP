#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__ = "M.Lauber@soton.ac.uk"

import matplotlib.pyplot as plt
import numpy as np
from scipy import interpolate


SAIL_TYPES = {
    "main": "main",
    "main_low": "main_low",
    "jib": "jib",
    "jib_low": "jib_low",
    "kite": "kite",
    "sym_kite": "sym_kite",
    "asym_cl_kite": "asym_cl_kite",
    "asym_pole_kite": "asym_pole_kite",
}


class Sail(object):
    def __init__(self, name, type, area, vce, up=True, data_source="orc",
                 cl_data=None, cd_data=None, sail_type=None):
        """
        Base sail class.

        Parameters
        ----------
        name : str
            Sail identifier (e.g. "J1", "A2").
        type : str
            Sail type, used to load coefficient data from ``dat/<type>.dat``.
            One of ``"main"``, ``"jib"``, or ``"kite"``.
        area : float
            Sail area (m^2).
        vce : float
            Vertical centre of effort above deck (m).
        up : bool, optional
            Whether this is an upwind sail. Default is True.
        data_source : str, optional
            Coefficient data source directory under ``dat/``. Default "orc".
        cl_data : dict, optional
            User-provided CL data: ``{"awa": [...], "values": [...]}``.
        cd_data : dict, optional
            User-provided CD data: ``{"awa": [...], "values": [...]}``.
        sail_type : str, optional
            Override for the coefficient data file name. E.g. ``"main_low"``,
            ``"sym_kite"``, ``"asym_cl_kite"``, ``"asym_pole_kite"``.
            If None, uses *type*.
        """
        self.name = name
        self.type = type
        self.area = area
        self.vce = vce
        # Determine which data file to load
        coeff_file = sail_type if sail_type is not None else self.type
        # get sails coefficients
        if cl_data is not None and cd_data is not None:
            self._build_interp_func(coeff_file, data_source=data_source)
            self._build_interp_from_arrays(cl_data, cd_data)
        else:
            self._build_interp_func(coeff_file, data_source=data_source)
        self.bk = 1.0  # always valid for main, only AWA<135 for jib
        self.up = up  # is that an upwind sail?


    def _build_interp_func(self, fname, data_source="orc"):
        """Build cubic B-spline interpolation functions for CL and CD.

        Falls back to linear (k=1) if fewer than 4 data points are available.
        Tries ``dat/{data_source}/{fname}.dat`` first, then ``dat/{fname}.dat``.
        """
        import os
        path = os.path.join("dat", data_source, fname + ".dat")
        if not os.path.exists(path):
            path = os.path.join("dat", fname + ".dat")
        a = np.genfromtxt(path, delimiter=",", skip_header=1)
        self.kp = a[0, 0]
        # Filter NaN values (trailing commas in CSV create NaNs)
        mask = ~(np.isnan(a[1, :]) | np.isnan(a[2, :]) | np.isnan(a[3, :]))
        x = a[1, mask]
        cd = a[2, mask]
        cl = a[3, mask]
        k = 3 if len(x) >= 4 else 1
        self.interp_cd = interpolate.make_interp_spline(x, cd, k=k)
        self.interp_cd.extrapolate = True
        self.interp_cl = interpolate.make_interp_spline(x, cl, k=k)
        self.interp_cl.extrapolate = True

    def _build_interp_from_arrays(self, cl_data, cd_data):
        """Build interpolation from user-provided coefficient arrays.

        Parameters
        ----------
        cl_data : dict
            {"awa": [...], "values": [...]} for lift coefficients.
        cd_data : dict
            {"awa": [...], "values": [...]} for drag coefficients.
        """
        cl_awa = np.array(cl_data["awa"])
        cl_vals = np.array(cl_data["values"])
        cd_awa = np.array(cd_data["awa"])
        cd_vals = np.array(cd_data["values"])
        k_cl = 3 if len(cl_awa) >= 4 else 1
        k_cd = 3 if len(cd_awa) >= 4 else 1
        self.interp_cl = interpolate.make_interp_spline(cl_awa, cl_vals, k=k_cl)
        self.interp_cl.extrapolate = True
        self.interp_cd = interpolate.make_interp_spline(cd_awa, cd_vals, k=k_cd)
        self.interp_cd.extrapolate = True

    def cl(self, awa):
        awa = max(0, min(awa, 180))
        return self.interp_cl(awa)

    def cd(self, awa):
        awa = max(0, min(awa, 180))
        return self.interp_cd(awa)

    def measure(self, rfm, ftj):
        """Update sail dimensions for current reef/furl state."""

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
    def __init__(self, name, P, E, Roach, BAD, data_source="orc",
                 cl_data=None, cd_data=None, sail_type=None):
        """
        Initialize mainsail.

        Parameters
        ----------
        name : str
            Sail identifier.
        P : float
            Height of the Mainsail in meters.
        E : float
            Length (Foot) of the Mainsail in meters.
        Roach : float
            Roach factor (Mainsail_area / (P*E/2) - 1).
        BAD : float
            Boom Above Deck in meters.
        data_source : str, optional
            Coefficient data source. Default "orc".
        cl_data : dict, optional
            User-provided CL data.
        cd_data : dict, optional
            User-provided CD data.
        sail_type : str, optional
            Coefficient variant: ``"main"`` (default) or ``"main_low"``.
        """
        self.name = name
        self.type = "main"
        self.P = P
        self.E = E
        self.roach = Roach
        self.BAD = BAD
        self.area0 = 0.5 * P * E * (1 + self.roach)
        self.vce = P / 3.0 * (1 + self.roach) + self.BAD
        super().__init__(self.name, self.type, self.area0, self.vce,
                         data_source=data_source, cl_data=cl_data, cd_data=cd_data,
                         sail_type=sail_type)
        self.measure()

    def measure(self, rfm=1, ftj=1):
        """
        Update mainsail dimensions for reef state.

        Parameters
        ----------
        rfm : float
            Reef factor for mainsail (0 to 1). 1 = fully unreefed.
        ftj : float
            Furl factor for jib (unused for mainsail, present for interface
            compatibility).
        """
        self.P_r = self.P*rfm
        self.vce = self.P_r / 3.0 * (1 + self.roach) + self.BAD
        self.area = self.area0*rfm**2
        self.CE = 1.


class Jib(Sail):
    def __init__(self, name, I, J, LPG, HBI, data_source="orc",
                 cl_data=None, cd_data=None, sail_type=None):
        """
        Headsail (jib/genoa).

        Parameters
        ----------
        name : str
            Sail identifier (e.g. "J1").
        I : float
            Forestay height (m).
        J : float
            Base of the foretriangle (m).
        LPG : float
            Luff perpendicular (m).
        HBI : float
            Height of the jib tack above deck (m).
        data_source : str, optional
            Coefficient data source. Default "orc".
        cl_data : dict, optional
            User-provided CL data.
        cd_data : dict, optional
            User-provided CD data.
        sail_type : str, optional
            Coefficient variant: ``"jib"`` (default) or ``"jib_low"``.
        """
        self.name = name
        self.type = "jib"
        self.I = I
        self.J = J
        self.IG = self.I
        self.LPG = LPG
        self.HBI = HBI
        self.area = 0.5 * I * max(J, LPG)
        self.vce = I / 3.0 + HBI
        super().__init__(self.name, self.type, self.area, self.vce,
                         data_source=data_source, cl_data=cl_data, cd_data=cd_data,
                         sail_type=sail_type)
        self.measure()

    def measure(self, rfm=1, ftj=1):
        """
        Update jib dimensions for furl state.

        Parameters
        ----------
        rfm : float
            Reef factor for mainsail (unused for jib, present for interface
            compatibility).
        ftj : float
            Furl factor for jib (0 to 1). 0 = fully unfurled.
        """
        self.LPG_r = self.LPG*ftj
        self.IG_r = self.IG*ftj
        self.area = 0.5 * self.I * max(self.J, self.LPG_r)


class Kite(Sail):
    def __init__(self, name, area, vce, data_source="orc",
                 cl_data=None, cd_data=None, sail_type=None):
        """
        Spinnaker or asymmetric downwind sail.

        Parameters
        ----------
        name : str
            Sail identifier (e.g. "A2", "A5").
        area : float
            Sail area (m^2).
        vce : float
            Vertical centre of effort above deck (m).
        data_source : str, optional
            Coefficient data source. Default "orc".
        cl_data : dict, optional
            User-provided CL data.
        cd_data : dict, optional
            User-provided CD data.
        sail_type : str, optional
            Coefficient variant: ``"kite"`` (default), ``"sym_kite"``,
            ``"asym_cl_kite"``, or ``"asym_pole_kite"``.
        """
        self.name = name
        self.type = "kite"
        self.area = area
        self.min_area = self.area
        self.vce = vce
        super().__init__(self.name, self.type, self.area, self.vce, up=False,
                         data_source=data_source, cl_data=cl_data, cd_data=cd_data,
                         sail_type=sail_type)
        self.measure()

    def measure(self, rfm=1, ftj=1):
        pass

# class Kite(Sail):
#     def __init__(self, SLU, SLE, SFL, SHW, ISP, J, SPL):
#         self.type = 'kite'
#         area_d = 1.14*np.sqrt(ISP**2+J**2)*max(SPL,J) # only for symm kite
#         self.area = max(area_d, 0.5*(SLU+SLE)*(SFL+4*SHW)/6.)
#         self.vce = 0.565*ISP # above base of I
#         super().__init__(self.type, self.area, self.vce, up=False)

if __name__=="__main__":
    pass
