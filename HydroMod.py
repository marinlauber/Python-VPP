#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__  = "M.Lauber@soton.ac.uk"

import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt
from YachtMod import Yacht, Appendage

class HydroMod(object):

    def __init__(self, yacht, rho=1025.0, mu=0.00119, g=9.81):

        # physical parameters
        self.rho = rho
        self.mu  = mu
        self.g   = g
        self.nu  = self.mu/self.rho

        # store yacht data
        self.yacht = yacht

        # measure yacht to get dimensions
        self.l,self.vol,self.bwl,self.tc,self.wsa = self.yacht.measure()
        self.lms,self.lvr,self.btr = self.yacht.measureLSM()

        # get resistance surfaces from ORC
        self.__load_data()

        # populate once
        _, _, _ = self.update(0.,0.)


    def __load_data(self):
        '''
        Loads ORC resistance surfaces from file and build interpolation function
        '''
        surf = np.genfromtxt('dat/ORCi_Drag_Surfaces.csv',delimiter=',',skip_header=1)
        surf = surf.reshape((24,43,42))
        # x is Fn := [0.,0.7], y is btr := [2.5,9], z is lvr := [3,9] 
        # we add zero Fn resistance (0.)
        fn = np.hstack((0.0,np.linspace(0.125,0.7,24)))
        btr = surf[0,2:,0]; lvr = surf[0,1,1:]
        # build interpolation function for 3D data
        data = np.zeros(((25,41,41))); data[1:,:,:] = surf[:,2:,1:]
        self._interp_Rr = interpolate.RegularGridInterpolator((fn, btr, lvr), data)
    

    def _init(self, vb0, phi0):
        self.vb = vb0
        self.phi = phi0
        

    def _get_Rr(self):
        """
        Get residuary resistance at this froude number
        """
        fn = max(0.0, (min(self.fn, 0.7)))
        # Note:  To convert to drag in Newtons multiply the values by displacement and 9.81 then divide by 1000.
        Rr = self._interp_Rr((fn,self.btr,self.lvr)) * self.vol * self.rho * self.g * 1e-3
        # for appendages in self.yacht.appendages:
        #     btr = appendages.btr
        #     lvr = appendages.lvr
        #     # for now appendages have no volume (no Rr_app)
        #     Rr += self._interp_Rr((fn,btr,lvr)) * appendages.vol * self.rho * self.g * 1e-3
        return Rr
    

    def _get_Rv(self):
        """
        Get viscous resistance at this froude number
        """
        # length correction and form factor of 1.05
        Rv = 0.5*self.rho*self.wsa*self.vb**2*self._cf(0.85*self.lsm) * 1.05
        for appendages in self.yacht.appendages:
            Rv += 0.5*self.rho*appendages.wsa*self.vb**2*self._cf(appendages.chord)
        return Rv


    def _cf(self, L):
        """
        Flate plate turbulent boudnary layer friction coefficient.
        Take a length scale, such that it can be used for appendags as well
        """
        self.Re = max(1., self.vb*L/self.nu) # prevents dividing by zero
        return 0.066*(np.log10(self.Re)-2.03)**(-2)


    def update(self, vb, phi):

        self.vb = vb
        self.phi = phi
        self.lsm, self.lvr, self.btr = self.yacht.measureLSM()
        self.fn = self.vb / (np.sqrt(self.g*self.lsm))

        # resistance
        self.Fx = self._get_Rr() + self._get_Rv()
        self.Fy = self._get_Ksf()

        # measure righting moment, bounded to 45 degrees of heel
        phi = max(0,min(self.phi,45))
        self.Mx = self.yacht._get_gz(phi)*self.vol*self.rho*self.g + self._rmv(self.vb)

        return self.Fx, self.Fy, self.Mx

    
    def _get_Ksf(self):
        return 0.


     # dynamic RM
    def _rmv(self, vb):
        return (5.955e-5/3.) * self.vol*self.lsm*(1-6.25*(self.bwl/np.sqrt(self.yacht.amax))) \
               *self.phi*self.vb/self.lsm


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


    def show_resistance(self, vb):
        resV,resR = np.empty_like(vb),np.empty_like(vb)
        for i, v in enumerate(vb):
            self.vb = v * 0.5144
            self.phi = 0
            self.lsm, self.lvr, self.btr = self.yacht.measureLSM()
            self.fn = self.vb / (np.sqrt(self.g*self.lsm))
            resR[i] = self._get_Rr()
            resV[i] =  self._get_Rv()
        plt.plot(vb, resR, '-x', lw=1, label='Residuary Resistance')    
        plt.plot(vb, resV, '-.', lw=1, label='Viscous Resistance')
        plt.plot(vb, resV+resR, '->', lw=1, label='Total Resistance')
        plt.xlabel(r'$V_b$ (knots)'); plt.ylabel(r'$R$ (N)')
        plt.legend()
        plt.show()


    def _test_gz(self):
        phi = np.linspace(0,40,64)
        res = np.empty_like(phi)
        for i in range(64):
            res[i] = self.yacht._get_gz(phi[i])
        plt.plot(phi,res)
        plt.show()


    def _test_interp(self):
        print('Check that interpolation correspond at the eight corners of cube')
        print(self._interp_Rr((0.125, 3., 2.5)), 0.0487)
        print(self._interp_Rr((0.125, 3., 9.0)), 0.0487)
        print(self._interp_Rr((0.125, 9., 2.5)), 0.0393)
        print(self._interp_Rr((0.125, 9., 9.0)), 0.0613)
        print(self._interp_Rr((0.700, 3., 2.5)), 357.062)
        print(self._interp_Rr((0.700, 3., 9.0)), 357.062)
        print(self._interp_Rr((0.700, 9., 2.5)), 38.0526)
        print(self._interp_Rr((0.700, 9., 9.0)), 42.2353)


    def print_state(self):
        print('HydroMod state:')
        print(' Lwl is:   %.2f (m)'   % self.l)
        print(' Bwl is:   %.2f (m)'   % self.bwl)
        print(' Tc  is:   %.2f (m)'   % self.tc)
        print(' Vb  is:   %.2f (m/s)' % self.vb)
        print(' Fn  is:   %.2f (-)'   % self.fn)
        print(' BTR is:   %.2f (-)'   % self.btr)
        print(' LVR is:   %.2f (-)'   % self.lvr)
        print(' Rtot is:  %.2f (N)'   % self.Fx)
        print(' KSF is:   %.2f (N)'   % self.Fy)
        print(' RM is:    %.2f (Nm)'  % self.Mx)


if __name__ == "__main__":
    
    # Bare hull (Appendages in intialized as zeros)
    YD41 = HydroMod(Yacht(Lwl=11.90, Vol=6.05, Bwl=3.18, Tc=0.4,
                        WSA=28.20, Tmax=2.30, Amax=1.051,
                        App=[Appendage()]))
    YD41.print_state()
    YD41.show_resistance(np.linspace(0, 12, 24))
