#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__ = "M.Lauber@soton.ac.uk"

import numpy as np
from scipy import interpolate

from src.UtilsMod import build_interp_func, json_read, json_write


def _zero_cr(fn):
    """Zero residuary resistance (for appendages without Cr data)."""
    return 0.0


class Appendage(object):
    def __init__(self, type, chord, area, span, vol, ce):
        """
        Base class for underwater appendages (keels, rudders, bulbs).

        Parameters
        ----------
        type : str
            Appendage type (``"keel"``, ``"rudder"``, or ``"bulb"``).
            Controls residuary resistance coefficient lookup.
        chord : float
            Mean chord length (m).
        area : float
            Planform (wetted) area (m^2).
        span : float
            Appendage span (m). Set to 0 for non-lifting bodies (bulbs).
        vol : float
            Displaced volume (m^3). Used for residuary resistance calculation.
        ce : float
            Centre of effort — depth below waterline (m, positive downward).
        """
        self.type = type
        self.chord = chord
        self.area = area
        self.wsa = 2 * self.area
        self.ce = ce
        self.vol = vol
        self.span = span
        self.Ar = self.span / self.area

        #  lift-curve slope and coefficient of lift area
        self.dclda = 2 * np.pi / (1.0 + 0.5 * self.Ar)
        self.cla = self.dclda * self.area
        self.teff = 1.8 * self.span
        # no residuary resistance
        self._interp_cr = _zero_cr
        if self.type == "keel":
            self._interp_cr = build_interp_func("rrk")
        if self.type == "bulb":
            self._interp_cr = build_interp_func("rrk", i=2)

    def _cr(self, fn):
        return self._interp_cr(max(0.0, min(fn, 0.6)))

    def _Ksff(self, phi):
        return 1.0

    def _print(self):
        print("Chord root : ", self.cu)
        print("Chord tip : ", self.cu)
        print("Chord avrg : ", self.chord)
        print("Span : ", self.span)
        print("WSA : ", self.wsa)
        print("CE : ", self.ce)


class Keel(Appendage):
    def __init__(self, Cu=1, Cl=1, Span=0):
        """
        Trapezoidal keel appendage.

        Computes area, mean chord, span, volume, and centre of effort from
        the root and tip chord lengths assuming a trapezoidal planform.

        Parameters
        ----------
        Cu : float, optional
            Root (upper) chord length (m). Default is 1.
        Cl : float, optional
            Tip (lower) chord length (m). Default is 1.
        Span : float, optional
            Keel span (m). Default is 0.
        """
        self.type = "keel"
        self.cu = Cu
        self.cl = Cl
        self.span = Span
        self.chord = 0.5 * (self.cu + self.cl)
        self.area = self.chord * self.span
        self.ce = -self.span * ((self.cu + 2 * self.cl) / (3 * (self.cl + self.cu)))
        self.cof = 1.31  # correction coeff for t/c 20%
        self.vol = 0.666 * self.chord * 1.2 * self.span
        super().__init__(self.type, self.chord, self.area, self.span, self.vol, self.ce)


class Rudder(Appendage):
    def __init__(self, Cu=1, Cl=1, Span=0):
        """
        Trapezoidal rudder appendage.

        Parameters
        ----------
        Cu : float, optional
            Root (upper) chord length (m). Default is 1.
        Cl : float, optional
            Tip (lower) chord length (m). Default is 1.
        Span : float, optional
            Rudder span (m). Default is 0.
        """
        self.type = "rudder"
        self.cu = Cu
        self.cl = Cl
        self.span = Span
        self.chord = 0.5 * (self.cu + self.cl)
        self.area = self.chord * self.span
        self.ce = -self.span * ((self.cu + 2 * self.cl) / (3 * (self.cl + self.cu)))
        self.cof = 1.21  # correction coeff for t/c 10%
        self.vol = 0.666 * self.chord * 1.1 * self.span
        super().__init__(self.type, self.chord, self.area, self.span, self.vol, self.ce)

    def _Ksff(self, phi):
        # rudder influence gradually ramped up to twice its area
        return np.where(phi <= 30, 1 + 0.5 * (1 - np.cos(phi / 30.0 * np.pi)), 1.0)


class Bulb(Appendage):
    def __init__(self, Chord, area, vol, CG):
        """
        Keel bulb appendage.

        A non-lifting body attached to the keel tip. Contributes wetted
        surface area and residuary resistance but no side force.

        Parameters
        ----------
        Chord : float
            Bulb chord length (m).
        area : float
            Wetted surface area (m^2).
        vol : float
            Displaced volume (m^3).
        CG : float
            Centre of gravity depth below waterline (m).
        """
        self.type = "bulb"
        self.chord = Chord
        self.area = area
        self.ce = CG
        self.vol = vol
        self.cof = 1.50
        super().__init__(self.type, self.chord, self.area, 0.0, self.vol, self.ce)


class ShortKeel(Appendage):
    def __init__(self, Length=1.0, Depth=0.5, Tc_ratio=0.15):
        """
        Short/integrated keel appendage.

        For traditional or hull-integrated keels with low aspect ratio.
        Uses the Jones low-AR lift formula instead of Prandtl correction,
        higher form drag, and zero appendage residuary resistance (hull
        resistance surfaces capture it).

        Parameters
        ----------
        Length : float
            Fore-aft keel length along hull bottom (m).
        Depth : float
            Keel depth below canoe body (m).
        Tc_ratio : float
            Average thickness-to-chord ratio. Default 0.15.
        """
        self.type = "short_keel"
        self.length = Length
        self.depth = Depth
        self.tc_ratio = Tc_ratio
        self.span = Depth
        self.chord = Length
        self.area = Length * Depth
        self.ce = -Depth / 2.0
        self.cof = 1.4 + 0.5 * Tc_ratio
        self.vol = Length * Depth * Length * Tc_ratio * 0.7
        super().__init__(self.type, self.chord, self.area, self.span, self.vol, self.ce)
        # Override Prandtl lift model with Jones low-AR formula
        ar = self.Ar
        self.dclda = np.pi * ar / 2.0
        self.cla = self.dclda * self.area
        self.teff = 1.5 * self.span


class Yacht(object):
    def __init__(self, Name, Lwl, Vol, Bwl, Tc, WSA, Tmax,
                 Amax, Mass, Loa, Boa, Ff, Fa, App=[], Sails=[], GZ=None, crew_weight=None,
                 roughness=150e-6, Hs=0.0, Ts=0.0, wave_direction=None):
        """
        Yacht hull and rig definition.

        Parameters
        ----------
        Name : str
            Name of the yacht design.
        Lwl : float
            Waterline length (m).
        Vol : float
            Displaced volume of the canoe body (m^3).
        Bwl : float
            Waterline beam (m).
        Tc : float
            Canoe body draft (m).
        WSA : float
            Wetted surface area of the canoe body (m^2).
        Tmax : float
            Maximum draft including keel (m).
        Amax : float
            Maximum cross-section area (m^2).
        Mass : float
            Total displacement mass including keel (kg).
        Loa : float
            Length overall (m).
        Boa : float
            Beam overall (m).
        Ff : float
            Freeboard height at the bow (m).
        Fa : float
            Freeboard height at the stern (m).
        App : list of Appendage, optional
            Underwater appendages (keels, rudders, bulbs). Default is [].
        Sails : list of Sail, optional
            Sail inventory. Default is [].
        GZ : dict, optional
            Righting arm curve as ``{"Heel": [...], "GZ": [...]}``.
            Heel in degrees, GZ in metres. If *None*, loads from
            ``righting_moment.json`` (backward compatible).
        crew_weight : float, optional
            Total crew weight (kg). If *None*, uses empirical formula
            ``25.8 * Lwl ** 1.4262``.
        roughness : float, optional
            Mean hull roughness height (m). Default 150e-6 (150 μm,
            new antifouling paint). Set to 0 for a smooth hull.
        Hs : float, optional
            Significant wave height (m). Default 0.0 (flat water).
        Ts : float, optional
            Modal wave period (s). Default 0.0.
        wave_direction : float or None, optional
            Wave direction (degrees). If None, waves align with wind.
        """
        self.g = 9.81
        self.Name = Name
        self.l = Lwl
        self.vol = Vol
        self.bwl = Bwl
        self.tc = Tc
        self.wsa = WSA
        self.tmax = Tmax
        self.amax = Amax
        self.mass = Mass
        self.loa = Loa
        self.boa = Boa
        self.ff = Ff
        self.fa = Fa
        self.bmax = 1.4 * self.bwl
        self.bdwt = 89.0  # standard crew weight
        self.Rm4 = 0.43 * self.tmax

        # standard crew weight
        self.cw = crew_weight if crew_weight is not None else 25.8 * self.l ** 1.4262
        self.carm = 0.8 * self.bmax  # must be average of rail where crew sits

        # rough estimate of projected area of the hull
        self.area_proj = self.l * self.tc * 0.666
        self.cla = self.area_proj * 2 * np.pi / (1.0 + 0.5 * self.area_proj / self.tc)
        self.teff = 2.07 * self.tc

        # hull roughness and wave parameters
        self.roughness = roughness
        self.Hs = Hs
        self.Ts = Ts
        self.wave_direction = wave_direction

        # appendages object
        self.appendages = App
        self.sails = Sails

        # GZ data (righting arm curve)
        self._gz_data = GZ

        # righting moment interpolation function
        self._interp_rm = self._build_rm_interp()

        # populate everything
        self.update()


    def _build_rm_interp(self):
        if self._gz_data is not None:
            a = self._gz_data
        else:
            a = json_read('righting_moment')
        return interpolate.interp1d(np.array(a["Heel"]), np.array(a["GZ"]),
                                    kind="linear", fill_value="extrapolate")


    def update(self):
        self.lsm = self.l
        self.lvr = self.lsm / self.vol ** (1.0 / 3.0)
        self.btr = self.bwl / self.tc


    def measure(self):
        self.update()
        return self.l, self.vol, self.mass, self.bwl, self.tc, self.wsa


    def measureLSM(self):
        self.update()
        return self.lsm, self.lvr, self.btr


    def _get_RmH(self, phi):
        # RM default is equal to RM hydrostatic
        return self._interp_rm(phi) * self.mass * self.g  # + 1./3.*self.rm_default


    def _get_RmC(self, phi):
        RmC =  self.carm*(self.cw+0.7*self.bmax*self.bdwt)*np.cos(np.radians(phi))
        # gradually ramp-up crew Rm from 2.5 to 7.5 degrees of heel.
        return RmC * np.where(
            phi <= 7.5, 0.5 * (1 - np.cos(np.maximum(0, phi - 2.5) / 5.0 * np.pi)), 1.0
        )


    def write(self):
        json_write(self._get_dict(), 'yacht')


    def _get_dict(self):
        dic={}
        for attr, value in self.__dict__.items():
            if(attr not in ["appendages","sails","Name"]) and (not callable(getattr(self, attr))):
                dic.update(dict({attr: value}))
        dic = {self.Name: dic}
        app={}; sails={}
        for appendage in self.appendages:
            vals={}
            for attr, value in appendage.__dict__.items():
                if not callable(getattr(appendage, attr)):
                    vals.update(dict({attr: value}))
            app.update(dict({appendage.type: vals}))
        for sail in self.sails:
            vals={}
            for attr, value in sail.__dict__.items():
                if not callable(getattr(sail, attr)):
                    vals.update(dict({attr: value}))
            sails.update(dict({sail.type: vals}))
        return dic.update(dict({'Appendages': app, 'Sails': sails}))
