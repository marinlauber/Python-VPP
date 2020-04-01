#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__  = "M.Lauber@soton.ac.uk"

from scipy.optimize import fsolve
import numpy as np
import matplotlib.pyplot as plt
from AeroMod import AeroMod
from HydroMod import HydroMod
from YachtMod import Yacht, Appendage
from SailMod import Main, Jib

class VPP(object):

    def __init__(self, hull, rig):

        # all variables
        self.vb = 0.
        self.phi = 0.
        self.awa = 0.
        self.twa = 0.
        self.tws = 0.
        self.aws = 0.

        # debbuging flag
        self.debbug = False

        # build model
        self.hydro = HydroMod(hull)
        self.aero =  AeroMod(rig)
    

    def set_analysis(self, tws_range, twa_range):
        
        if(tws_range.max()<=35. and tws_range.min()>=2.):
            self.tws_range = tws_range*0.5144
        else:
            print('Anaylis only valid for TWS range : 2. < TWS < 35. knots.')
        
        if(twa_range.max()<=180. and twa_range.min()>=0.):
            self.twa_range = twa_range
        else:
            print('Anaylis only valid for TWA range : 0. < TWA < 180. degrees.')
        self.store = np.empty((len(self.tws_range),len(self.twa_range),2))

        if(self.debbug==True):
            for i in range(self.store.shape[0]):
                self.store[i,:,0] = np.ones_like(twa_range)*tws_range[i]

        # flag for later
        self.upToDate = True
    

    def run(self):

        if(not self.upToDate): raise 'VPP run stop: no analysis set!'

        for i,tws in enumerate(self.tws_range):
            for j,twa in enumerate(self.twa_range):
               
                self.tws=tws
                self.twa=twa

                self._init(tws, twa)

                self._find_equlibrium(twa, tws)
               
                self.store[i,j,0] = self.vb/0.5144
                self.store[i,j,1] = self.phi

                # self._write_csv()

    
    def _init(self, tws, twa):
        vb0 = 0.3*np.sqrt(self.hydro.l*self.hydro.g)
        self.vb = vb0
        phi0 = 0.
        self.phi = phi0
        self.aero._init(self.tws, self.twa, vb0, phi0)
        self.hydro._init(self.vb, self.phi)


    def _find_equlibrium(self, twa, tws):

        # initil gues as previous values
        print('Running case: (%.2f, %.2f)' % (twa, tws))
        print('Initial Guess for boat velocity: %.3f' % self.vb)

        # solve
        # res = fsolve(self._residuals, x0=vec0, args=(twa, tws), xtol=1e-06, maxfev=100)
        for i in range(5):
            res = fsolve(self._res_Fx,x0=self.vb, args=(self.phi, twa, tws), xtol=1e-06, maxfev=100)
            self.vb = res
            res = fsolve(self._res_Mx,x0=self.phi, args=(self.vb, twa, tws), xtol=1e-06, maxfev=100)
            self.phi = res

        print('Result for boat velocity: %.3f' % self.vb)
        print('Heel angle at equilibrium: %.3f' % self.phi)
        print('Lift coefficient:         %.3f' % self.aero.cl)
        print('Drag coefficient:         %.3f' % self.aero.cd)
        # print('Residuals       :         %.3f' % sum(self._residuals([res[0],res[1]], twa, tws)))
        print('Residuals Fx    :         %.3f' % self._res_Fx(self.vb, self.phi, twa, tws))
        print('Residuals Mx    :         %.3f' % self._res_Mx(self.phi, self.vb, twa, tws))
        print()


    def _residuals(self, vec, twa, tws):

        [vb, phi] = vec
        # update forces for current config
        FxA, _, MxA = self.aero.update(vb=vb, phi=phi, tws=tws, twa=twa)
        FxH, _, MxH = self.hydro.update(vb=vb, phi=phi)

        # L-2 residuals
        rFx = (FxA - FxH)**2
        # rFy = (FyA - FyH)**2
        rMx = (MxA - MxH)**2

        return [rFx, rMx]


    def _res_Fx(self, vb, phi, twa, tws):
        # update forces for current config
        FxA, _, _ = self.aero.update(vb=vb, phi=phi, tws=tws, twa=twa)
        FxH, _, _ = self.hydro.update(vb=vb, phi=phi)
        # L-2 residuals
        return (FxA - FxH)**2
    def _res_Mx(self, phi, vb, twa, tws):
        # update forces for current config
        _, _, MxA = self.aero.update(vb=vb, phi=phi, tws=tws, twa=twa)
        _, _, MxH = self.hydro.update(vb=vb, phi=phi)
        # L-2 residuals
        return (MxA - MxH)**2


    def _write_csv(self):
        pass


    def polar(self):
        fig,(ax1,ax2) = plt.subplots(1,2,subplot_kw=dict(projection='polar'))
        for i in range(self.store.shape[0]):
            ax1.plot(np.deg2rad(self.twa_range),self.store[i,:,0],'-',lw=1)
            ax2.plot(np.deg2rad(self.twa_range),self.store[i,:,1],'-',lw=1)

        ax1.set_xticks(np.linspace(0,np.pi,7))  
        ax1.set_theta_direction(-1)
        ax1.set_theta_offset(np.pi/2.0)    
        ax1.set_thetamin(0); ax1.set_thetamax(180)
        ax1.set_xlabel(r'TWA ($^\circ$)')
        ax1.set_ylabel(r'$V_B$ (knots)')

        ax2.set_xticks(np.linspace(0,np.pi,7))  
        ax2.set_theta_direction(-1)
        ax2.set_theta_offset(np.pi/2.0)    
        ax2.set_thetamin(0); ax2.set_thetamax(180)
        ax2.set_xlabel(r'TWA ($^\circ$)')
        ax2.set_ylabel(r'Heel ($\phi$) ($^\circ$)')
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":

    # test with YD-41 from Larsson
    Keel  =  Appendage(Cu=1.00,Cl=0.78,Span=1.90)
    Rudder = Appendage(Cu=0.48,Cl=0.22,Span=1.15)

    # set-up yhe yacht
    YD41 = Yacht(Lwl=11.90,Vol=6.05,
                 Bwl=3.18,Tc=0.4,
                 WSA=28.20,Tmax=2.30,
                 Amax=1.051,
                 App=[Keel,Rudder])

    # build the vpp model
    vpp = VPP(hull=YD41,
              rig=[Main(P=16.60,E=5.60,Roach=0.1,BAD=1.),
                   Jib(I=16.20,J=5.10,LPG=5.40,HBI=1.8)])

    # prepare analysis
    vpp.set_analysis(tws_range=np.array([8.0, 10.0, 12.0]),
                     twa_range=np.linspace(30, 115, 24))

    # useless comment
    vpp.run()
    vpp.polar()
