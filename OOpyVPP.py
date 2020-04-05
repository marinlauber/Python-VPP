#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__  = "M.Lauber@soton.ac.uk"

import numpy as np
import matplotlib.pyplot as plt
from scipy import interpolate
from scipy.optimize import fsolve
from mpl_toolkits import mplot3d
import warnings
warnings.filterwarnings('ignore', 'The iteration is not making good progress')


from AeroMod import AeroMod
from HydroMod import HydroMod
from YachtMod import Yacht, Keel, Rudder
from SailMod import Main, Jib

class VPP(object):

    def __init__(self, AeroMod, HydroMod):

        # build model
        self.aero = AeroMod
        self.hydro = HydroMod

        self.twa0 = 30.
        self.tws0 = 5.
        self.phi0= 0.
        self.vb0 = 3.8 # (m/s)
        self.leeway0 = 1.8

        # debbuging flag
        self.debbug = False
    

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
    

    def run(self, verbose=False):

        if(not self.upToDate): raise 'VPP run stop: no analysis set!'

        for i,tws in enumerate(self.tws_range):
            for j,twa in enumerate(self.twa_range):


                res = fsolve(self.resid,[self.vb0,self.phi0,self.leeway0],args=(twa, tws))
                
                self.store[i,j,:] = res[:2]
                
                if verbose:
                    print('Running case : ',twa,tws)
                    print('Initial Guess for boat velocity : %.3f' % self.vb0)
                    print('Result for boat velocity : %.3f' % res[0])
                    print('Lift coefficient :         %.3f' % self.aero.cl)
                    print('Drag coefficient :         %.3f' % self.aero.cd)
                    print()       
                
                self.hydro.update(res[0], res[1], res[2])
                self.aero.update(res[0], res[1], tws, twa)

                # prepare next iteration
                self.vb0 = self.hydro.vb
                self.phi0 = self.hydro.phi
                self.leeway0 = self.hydro.leeway

    
    def resid(self, x0, twa, tws):

        vb0=x0[0]; phi0=x0[1]; leeway=x0[2]

        Fxh, Fyh, Mxh = self.hydro.update(vb0, phi0, leeway)
        Fxa, Fya, Mxa = self.aero.update(vb0, phi0, tws, twa)

        return [(Fxh - Fxa)**2, (Mxh - Mxa)**2, (Fyh - Fya)**2]


    def polar(self):
        ax = plt.subplot(111, polar=True)
        for i in range(self.store.shape[0]):
            ax.plot(np.deg2rad(np.array(self.twa_range)),
                    np.array(self.store[i,:,0])/0.5144,
                    '-ok',lw=1,markersize=4,mfc='None',
                    label=f'{self.tws_range[i]/0.5144:.1f}')
        ax.set_xticks(np.linspace(0,np.pi,5,))  
        ax.set_theta_direction(-1)
        ax.set_theta_offset(np.pi/2.0)    
        ax.set_thetamin(0); ax.set_thetamax(180)
        ax.set_xlabel(r'TWA ($^\circ$)'); ax.set_ylabel(r'$V_B$ (knots)')
        plt.legend(title=r'TWS (knots)')
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":

    # test with YD-41 from Larsson
    Keel  =  Keel(Cu=1.00,Cl=0.78,Span=1.90)
    Rudder = Rudder(Cu=0.48,Cl=0.22,Span=1.15)

    hydro = HydroMod(yacht=Yacht(Lwl=11.90,Vol=6.05,
                                Bwl=3.18,Tc=0.4,
                                WSA=28.20,Tmax=2.30,
                                Amax=1.051,Mass=6500,
                                App=[Keel,Rudder]))
    aero = AeroMod(sails=[Main(P=16.60,E=5.60,Roach=0.1,BAD=1.),
                          Jib(I=16.20,J=5.10,LPG=5.40,HBI=1.8)],
                Ff=1.5, Fa=1.5, B=4.20, L=12.50)

    vpp = VPP(AeroMod=aero, HydroMod=hydro)
    vpp.set_analysis(tws_range=np.array([5.0, 7.0]),
                     twa_range=np.linspace(30.0,140.0,23))
    vpp.run(verbose=True)
    vpp.polar()




      # def _set(self, tws, twa):
    #     vb = 0.35*np.sqrt(self.hydro.l*self.hydro.g)
    #     self.aero._set(vb, 0.0, self.tws, self.twa)
    #     self.hydro._set(vb, 0.0, 0.0)


    # def _find_equlibrium(self, twa, tws):
        
    #     # initial guess is current values
    #     vec0 = [0.35*np.sqrt(self.hydro.l*self.hydro.g),
    #             0.0, 0.0]

    #     # initil gues as previous values
    #     print('Running case: (%.2f, %.2f)' % (twa, tws))
    #     print('Initial Guess for boat velocity: %.3f' % vec0[0])

    #     # solve
    #     res = fsolve(self._residuals,x0=vec0, args=(twa, tws))

    #     self.aero.update(res[0],res[1],tws,twa)
    #     self.hydro.update(res[0],res[1],res[2])

    #     print('     Boat velocity : %.3f' % self.hydro.vb)
    #     print('     Heel angle : %.3f' % self.hydro.phi)
    #     print('     Leeway angle : %.3f' % self.hydro.leeway)
    #     print()


    # This is the cost function we want to minimize
    # def _func(self, X, twa, tws):
    #     vb   = X[0]; phi  = X[1]
    #     lam1 = X[2]; lam2 = X[3]
    #     return vb + lam1*self._res_Fx(vb,phi,twa,tws) + lam2*self._res_Mx(phi,vb,twa,tws)
    # # numercial derivative of the cost function, what we actually solve
    # def _dfunc(self, X, twa, tws):
    #     dLambda = np.zeros(len(X))
    #     h = 1e-3 # this is the step size used in the finite difference.
    #     for i in range(len(X)):
    #         dX = np.zeros(len(X))
    #         dX[i] = h
    #         dLambda[i] = (self._func(X+dX,twa,tws)-self._func(X-dX,twa,tws))/(2*h)
    #     return dLambda
    # def _res_Fx(self, vb, phi, twa, tws):
    #     # update forces for current config
    #     FxA, _, _ = self.aero.update(vb=vb, phi=phi, tws=tws, twa=twa)
    #     FxH, _, _ = self.hydro.update(vb=vb, phi=phi)
    #     # L-2 residuals
    #     return (FxA - FxH)**2
    # def _res_Mx(self, phi, vb, twa, tws):
    #     # update forces for current config
    #     _, _, MxA = self.aero.update(vb=vb, phi=phi, tws=tws, twa=twa)
    #     _, _, MxH = self.hydro.update(vb=vb, phi=phi)
    #     # L-2 residuals
    #     return (MxA - MxH)**2


    # def polar(self):
    #     fig,(ax1,ax2) = plt.subplots(1,2,subplot_kw=dict(projection='polar'))
    #     for i in range(self.store.shape[0]):
    #         ax1.plot(np.deg2rad(self.twa_range),self.store[i,:,0]/0.5144,'-',lw=1)
    #         ax2.plot(np.deg2rad(self.twa_range),self.store[i,:,1],'-',lw=1)

    #     ax1.set_xticks(np.linspace(0,np.pi,7))  
    #     ax1.set_theta_direction(-1)
    #     ax1.set_theta_offset(np.pi/2.0)    
    #     ax1.set_thetamin(0); ax1.set_thetamax(180)
    #     ax1.set_xlabel(r'TWA ($^\circ$)')
    #     ax1.set_ylabel(r'$V_B$ (knots)')

    #     ax2.set_xticks(np.linspace(0,np.pi,7))  
    #     ax2.set_theta_direction(-1)
    #     ax2.set_theta_offset(np.pi/2.0)    
    #     ax2.set_thetamin(0); ax2.set_thetamax(180)
    #     ax2.set_xlabel(r'TWA ($^\circ$)')
    #     ax2.set_ylabel(r'Heel ($\phi$) ($^\circ$)')
    #     plt.tight_layout()
    #     plt.show()



