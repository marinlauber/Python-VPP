#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import warnings

import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import RegularGridInterpolator

from .UtilsMod import DATA_DIR


class HydroMod(object):
    def __init__(self, Yacht, rho=1025.0, mu=0.00119, g=9.81):
        """
        Hydrodynamic resistance and righting moment model.

        Computes total resistance (viscous + residuary + induced), side force
        from appendage lift, and righting moment using ORC methods and
        interpolated resistance surfaces.

        Parameters
        ----------
        Yacht : Yacht
            Yacht object containing hull geometry and appendage definitions.
        rho : float, optional
            Seawater density (kg/m^3). Default is 1025.0.
        mu : float, optional
            Dynamic viscosity of seawater (Pa.s). Default is 1.19e-3.
        g : float, optional
            Gravitational acceleration (m/s^2). Default is 9.81.
        """

        # physical parameters
        self.rho = rho
        self.mu = mu
        self.g = g
        self.nu = self.mu / self.rho

        # store yacht data
        self.yacht = Yacht
        self.yacht.rho = self.rho
        self.yacht.g = self.g

        # measure yacht to get dimensions
        self.l, self.vol, self.mass, self.bwl, self.tc, self.wsa = self.yacht.measure()
        self.lms, self.lvr, self.btr = self.yacht.measureLSM()

        # get resistance surfaces from ORC
        self.__load_data()

        # print warning if yacht is close to boundaries for Rr
        if (self.btr < 3.0) or (self.btr > 8.5) or (self.lvr < 3.5) or (self.lvr > 8.5):
            warnings.warn(
                "Yacht dimensions are close to boundaries of resistance surfaces, "
                + "extrapolation will be used if values (fn, btr, lvr) are outside of "
                + "range, but resistance might be affected.",
                UserWarning,
                stacklevel=2,
            )

    def __load_data(self):
        """
        Loads ORC resistance surfaces from file and build interpolation function
        """
        surf = np.genfromtxt(DATA_DIR / "ORCi_Drag_Surfaces.csv", delimiter=",", skip_header=1)
        surf = surf.reshape((24, 43, 42))
        # x is Fn := [0.,0.7], y is btr := [2.5,9], z is lvr := [3,9]
        # we add zero Fn resistance (0.)
        fn = np.hstack((0.0, np.linspace(0.125, 0.7, 24)))
        btr = surf[0, 2:, 0]
        lvr = surf[0, 1, 1:]
        # build interpolation function for 3D data
        data = np.zeros(((25, 41, 41)))
        data[1:, :, :] = surf[:, 2:, 1:]
        # extrapolate if outside range
        # https://github.com/scipy/scipy/blob/v0.16.1/scipy/interpolate/interpolate.py#L1528
        self._interp_Rr = RegularGridInterpolator(
            (fn, btr, lvr), data, method="linear", bounds_error=False, fill_value=None
        )

    def _get_Rr(self):
        """
        Get residuary resistance at this froude number
        """
        fn = max(0.0, self.fn)
        # Note:  To convert to drag in Newtons multiply the values by displacement and 9.81/1000.
        Rr = self._interp_Rr((fn, self.btr, self.lvr)) * self.mass * self.g * 1e-3
        for appendage in self.yacht.appendages:
            # for now appendages have no volume (no Rr_app)
            Rr += appendage._cr(fn) * appendage.vol * self.rho * self.g * 1e-3
        # correct for immersed rail
        if self.phi >= 30.0:
            Rr *= 1 + 0.0004 * (self.phi - 30.0) ** 2
        return Rr

    def _get_Rv(self):
        """
        Viscous resistance of the canoe body (ORC 6.1.1) and appendages (6.1.2).
        Needs the appendage side forces, so _get_Ri() is called first.
        """
        q = 0.5 * self.rho * self.vb ** 2
        # length correction and form factor of 1.05
        Rv = q * self.wsa * self._cf(0.85 * self.lsm) * 1.05
        for appendage, side_force in zip(self.yacht.appendages, self.Ksfj[1:]):
            Rv += q * self._app_cd_area(appendage, side_force)
        return Rv

    def _app_cd_area(self, app, side_force):
        """
        Viscous drag area (m^2) of an appendage, ORC 6.1.2: five spanwise strips
        with their local Reynolds number, the ORC friction line (6.3) and form
        factor (6.4, 6.6), plus the lift-dependent drag (6.7) with CL capped at 0.5.
        """
        root = getattr(app, "cu", app.chord)
        tip = getattr(app, "cl", app.chord)
        chords = root + (tip - root) * (np.arange(5) + 0.5) / 5
        if app.type == "bulb":
            tcr = min(app.tc_ratio, 0.25)
            kf = -13.1753 * tcr ** 3 + 9.3842 * tcr ** 2 - 0.7581 * tcr + 0.1442
        elif app.type == "short_keel":
            kf = app.cof - 1  # own form factor for low aspect-ratio keels
        else:
            tcr = min(app.tc_ratio, 0.18)
            kf = 1.75 * tcr + 30 * tcr ** 4
        q = 0.5 * self.rho * self.vb ** 2
        cl = min(abs(side_force) / (q * app.area), 0.5) if q > 0 and app.area > 0 else 0.0
        dcd = 0.0016 * cl + 0.0032 * cl ** 2
        return sum(app.wsa / 5 * (self._cf_app(c) * (1 + kf) + dcd) for c in chords)

    def _get_Ri(self):
        """
        Induced drag of the canoe body and appendages (ORC 6.5), each from its
        share of the side force and its effective span. The appendage spans
        are corrected for the keel root free surface and funsteady (6.5.1), and
        the total by the heel multiplier of Figure 6.10.
        """
        cla = [self.yacht.cla]
        teff = [self.yacht.teff]
        for appendage in self.yacht.appendages:
            cla.append(appendage.cla * appendage._Ksff(self.phi))
            teff.append(appendage.teff * self.span_mult)
        cla, teff = np.array(cla), np.array(teff)

        q = 0.5 * self.rho * self.vb ** 2
        self.Ksfj = q * cla * np.radians(self.leeway)
        self.Ksf = np.sum(self.Ksfj)
        if q == 0.0:
            return 0.0
        lifting = teff > 0
        return np.sum(self.Ksfj[lifting] ** 2 / (q * np.pi * teff[lifting] ** 2))

    def _span_multiplier(self, tws):
        """
        Keel root free surface factor times funsteady on the appendage effective
        span (ORC 6.5.1, 6.39-6.48), both 1 when no TWS is given. TWS enters the
        empirical wave height and funsteady in knots; fact_Fn is taken as Fn.
        """
        if tws is None:
            return 1.0
        tws_kn = tws / 0.5144
        hdyn = -0.087641 * self.lsm * self.fn * np.exp(-0.417 * self.lvr)
        ew = tws_kn * (1 - 0.8375 * 1.174 ** (-0.00248 * tws_kn ** 3.5))
        hw = 0.25 * tws_kn * np.sqrt(2 * ew / (self.rho * self.g))
        beff = 0.0
        # keel root at the canoe body draft, under a wave peak and trough
        for dist in (self.tc + hdyn + 0.5 * hw, self.tc + hdyn - 0.5 * hw):
            tratio = np.clip(2 * dist / (0.15 * self.lsm), 0.0, 0.5)
            beff += 0.5 * (0.5 + 0.5 * np.sin(np.pi * tratio))
        funsteady = max(0.9, 1 - ((tws_kn - 10) / (self.vol + 3)) ** 2 / 200)
        return beff * funsteady

    def _di_factor(self, ratio):
        """
        Heel multiplier of the induced drag (ORC Figure 6.10, fitted as
        1 + 0.56 (1 - phi/16)^2 below 16 deg), fully active upwind and faded
        out as the drive to side force ratio goes from 0.2 to 0.4.
        """
        di = 1 + 0.56 * max(0.0, 1 - self.phi / 16.0) ** 2
        w = 0.5 * (1 + np.cos(np.pi * np.clip((ratio - 0.2) / 0.2, 0.0, 1.0)))
        return 1 + (di - 1) * w

    def _cf(self, L):
        """
        Flat plate turbulent boundary layer friction coefficient (Hughes line,
        as in the ORC VPP since 2013) with optional ITTC 1978 roughness
        allowance. Takes a length scale so it can be used for hull and
        appendages.
        """
        Re = max(
            1e4, self.vb * L / self.nu
        )  # prevents dividing by zero, lowest for turbulence on plate
        cf = 0.066 * (np.log10(Re) - 2.03) ** (-2)
        ks = self.yacht.roughness
        if ks > 0:
            cf += (105.0 * (ks / L) ** (1.0 / 3.0) - 0.64) * 1e-3
        return cf

    def _cf_app(self, L):
        """
        ORC appendage friction line (6.3, the quadratic term read as
        0.0278513 log^2 Rn), with the optional roughness allowance.
        """
        lr = np.log10(max(1e5, self.vb * L / self.nu))
        cf = (0.0000853 * lr ** 4 - 0.0025252 * lr ** 3 + 0.0278513 * lr ** 2
              - 0.1363492 * lr + 0.2539752)
        ks = self.yacht.roughness
        if ks > 0:
            cf += (105.0 * (ks / L) ** (1.0 / 3.0) - 0.64) * 1e-3
        return cf

    def _added_resistance_waves(self, twa):
        """Added resistance in waves (simplified Gerritsma scaling).

        Uses a Bretschneider-type spectrum with hull-form scaling to
        estimate the mean added resistance from ocean waves.

        Parameters
        ----------
        twa : float
            True wind angle (degrees), used as wave encounter angle
            unless ``yacht.wave_direction`` overrides it.

        Returns
        -------
        float
            Added resistance in Newtons. Returns 0 when Hs = 0.
        """
        Hs = self.yacht.Hs
        Ts = self.yacht.Ts
        if Hs <= 0 or Ts <= 0:
            return 0.0

        # wave encounter angle
        if self.yacht.wave_direction is not None:
            mu = np.radians(twa - self.yacht.wave_direction)
        else:
            mu = np.radians(twa)

        # heading correction — full drag head-on, near-zero following
        cos2_mu = np.cos(mu) ** 2

        # hull-form coefficient (empirical, typical displacement hull)
        C_aw = 6.0

        # wave encounter frequency
        omega_0 = 2.0 * np.pi / Ts
        omega_e = abs(omega_0 - omega_0 ** 2 * self.vb * np.cos(mu) / self.g)

        # resonance tuning factor (peak when encounter ≈ hull natural freq)
        omega_n = np.sqrt(self.g / self.l)
        r = omega_e / omega_n if omega_n > 0 else 0.0
        f_omega = r ** 2 * np.exp(1.0 - r ** 2) if r > 0 else 0.0

        Raw = C_aw * (Hs ** 2 / self.l) * (self.bwl ** 2 / self.tc) * f_omega * cos2_mu
        # convert to Newtons (rho * g scaling)
        Raw *= self.rho * self.g / 1000.0

        return max(0.0, Raw)

    def update(self, vb, phi, leeway, twa=0.0, tws=None):
        """
        Update hydrodynamic forces for current sailing state.

        Parameters
        ----------
        vb : float
            Boat speed (m/s).
        phi : float
            Heel angle (degrees).
        leeway : float
            Leeway angle (degrees).
        twa : float, optional
            True wind angle (degrees). Used for wave encounter angle.
        tws : float, optional
            True wind speed (m/s), for the free surface and funsteady
            corrections of the appendage effective span. None skips them.

        Returns
        -------
        tuple of float
            (Fx, Fy, Mx) — total resistance (N), side force (N),
            total righting moment (N.m).
        """

        self.vb = max(0, vb)
        self.phi = max(0, phi)
        self.leeway = leeway
        self.lsm, self.lvr, self.btr = self.yacht.measureLSM()
        self.fn = self.vb / (np.sqrt(self.g * self.lsm))

        # resistance, induced drag first as it sets the appendage lift
        self.span_mult = self._span_multiplier(tws)
        Ri = self._get_Ri()
        self.Fx = self._get_Rr() + self._get_Rv() + self._added_resistance_waves(twa)
        self.Fx += Ri * self._di_factor(self.Fx / max(self.Ksf, 1e-6))

        # keel side force, calculated when _get_Ri() is called
        self.Fy = self.Ksf * np.cos(self.phi / 180.0 * np.pi)

        # measure righting moment
        # self._limit_heel()
        self.Mx = self.yacht._get_RmH(self.phi) + self._get_RmV(self.vb)
        # add crew and keel (lift) contribution
        self.Mx += self.yacht._get_RmC(self.phi) - self.Ksf * self.yacht.Rm4

        return self.Fx, self.Fy, self.Mx

    # def _limit_heel(self):
    #     self.phi = max(0,min(self.phi,self.phi_max))

    def _get_RmV(self, vb):
        """
        Dynamic righting moment (N.m), ORC 2026 eq. 4.32. Negative: stability
        lost with forward speed. Displacement x length gives kg.m, so the
        formula holds in SI with the speed-length ratio in knots/sqrt(ft).
        """
        slr = (vb / 0.5144) / np.sqrt(self.lsm / 0.3048)
        return (
            (5.955e-5 / 3.0)
            * self.mass * self.g
            * self.lsm
            * (1 - 6.25 * self.bwl / np.sqrt(self.yacht.amax) - 2.1)
            * slr
            * self.phi
        )

    # old Delft Method
    # def _get_Rr_Delft(self.)
    #     a = self.get_as(self.fn)s
    #     Rr =  a[1] * (self.lcb_fpp / self.lwl)
    #     Rr += a[2] * self.cp + a[3] * (self.vol**(2./3.) / self.aw)
    #     Rr += a[4] * (self.bwl / self.lwl) + a[5] * (self.lcb_fpp / self.lcf_fpp)
    #     Rr += a[6] * (self.bwl / self.tc) + a[7] * self.cm
    #     Rr *= (self.vol**(1./3.) / self.lwl)
    #     Rr += a[0]
    #     Rr *= (self.displ * self.g)
    #     return Rr
    # def get_as(self, fn):
    #     a = np.empty(len(self.interp_a))
    #     for i in range(len(self.interp_a)):
    #         a[i] = self.interp_a[i](fn)
    #     return a

    def show_resistance(self, vb, file_name="None"):
        resV, resR = np.empty_like(vb), np.empty_like(vb)
        for i, v in enumerate(vb):
            self.vb = v * 0.5144
            self.phi = 0
            self.lsm, self.lvr, self.btr = self.yacht.measureLSM()
            self.fn = self.vb / (np.sqrt(self.g * self.lsm))
            self.leeway, self.span_mult = 0.0, 1.0
            self._get_Ri()  # zero side force, sets the appendage lift
            resR[i] = self._get_Rr()
            resV[i] = self._get_Rv()
        plt.plot(vb, resR, "-x", lw=1, label="Residuary Resistance")
        plt.plot(vb, resV, "-.", lw=1, label="Viscous Resistance")
        plt.plot(vb, resV + resR, "->", lw=1, label="Total Resistance")
        plt.xlabel(r"$V_b$ (knots)")
        plt.ylabel(r"$R$ (N)")
        plt.legend()
        plt.tight_layout()
        if file_name != "None":
            plt.savefig(file_name, dpi=300)
        plt.show()

    def _test_gz(self):
        phi = np.linspace(0, 40, 64)
        res = np.empty_like(phi)
        for i in range(64):
            res[i] = self.yacht._get_gz(phi[i])
        plt.plot(phi, res)
        plt.show()

    def print_state(self):
        self.update(self.vb, self.phi, self.leeway)
        print("HydroMod state :")
        print(" Lwl is :   %.2f (m)" % self.l)
        print(" Bwl is :   %.2f (m)" % self.bwl)
        print(" Tc  is :   %.2f (m)" % self.tc)
        print(" Vb  is :   %.2f (m/s)" % self.vb)
        print(" Fn  is :   %.2f (-)" % self.fn)
        print(" Lway is :  %.2f (-)" % self.leeway)
        print(" BTR is :   %.2f (-)" % self.btr)
        print(" LVR is :   %.2f (-)" % self.lvr)
        print(" Rtot is :  %.2f (N)" % self.Fx)
        print(" KSF is :   %.2f (N)" % self.Fy)
        print(" RM is :    %.2f (Nm)" % self.Mx)
