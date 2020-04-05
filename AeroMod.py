#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__  = "M.Lauber@soton.ac.uk"

import numpy as np
from scipy.interpolate import interp1d
from scipy.optimize import fsolve
import matplotlib.pyplot as plt
from SailMod import Main, Jib

class AeroMod(object):

    def __init__(self, sails, Ff=1.5, Fa=1.5, B=4.2, L=12.5):
        '''
        Initializes an Aero Model, given a set of sails
        '''
        self.flat = 1.

        # are we upwind?
        self.up = True

        # set sails and measure what is need once
        self.sails = sails
        self._measure_sails()

        # coeffs interp function
        self.fcdmult = self._build_interp_func('fcdmult')
        self.kheff  =  self._build_interp_func('kheff')
        
        # physical params
        self.rho = 1.225
        self.mu = 0.0000181

        # this must be wrapped into a boat!
        self.B = B
        self.L = L
        self.FBAV = 0.625*Ff+0.375*Fa


    def _measure_sails(self):
        self.fractionality = 1.
        for sail in self.sails:
            if sail.type=='main':
                self.fractionality /= (sail.P + sail.BAD)
                b1 = sail.P + sail.BAD
                self.roach = sail.roach
            if sail.type=='jib':
                self.fractionality *= sail.I
                b2 = sail.I
                self.overlap = sail.LPG / sail.J
                self.HBI = sail.HBI
        self.eff_span_corr = 1.1 + 0.08*(self.roach-0.2) + \
                             0.5*(0.68+0.31*self.fractionality+0.0075*self.overlap-1.1)
        self.b = max(b1,b2)
        self.heff_height_max_spi = self.b


    def _set(self, vb, phi, tws, twa):
        self.tws = tws
        self.twa = twa
        self.vb = vb
        self.phi = phi
        
        self._update_windTriangle()


    # prototype top function in hydro mod
    def update(self, vb, phi, tws, twa):
        '''
        Update the aero model for current iter
        '''
        self.vb = max(0, vb)
        self.phi = max(0, phi)
        self.tws = tws
        self.twa = twa

        self._update_windTriangle()
        self._area()
        self._compute_forces()

        return self.Fx, self.Fy, self.Mx


    def _compute_forces(self):
        '''
        Computes forces for equilibrium.
        '''
        # get new coeffs
        self._get_coeffs()

        # instead of writing many time
        awa = self.awa/180.*np.pi

        # lift and drag
        self.lift = 0.5*self.rho*self.aws**2*self.area*self.cl
        self.drag = 0.5*self.rho*self.aws**2*self.area*self.cd + self._get_Rw(awa)

        # project into yacht coordinate system
        self.Fx = self.lift*np.sin(awa) - self.drag*np.cos(awa)
        self.Fy = self.lift*np.cos(awa) + self.drag*np.sin(awa)

        # heeling moment
        self.Mx = self.Fy * self._vce() * np.cos(self.phi/180.*np.pi)

        # side-force is horizontal component of Fh
        self.Fy *= np.cos(np.deg2rad(self.phi))

    
    def _get_Rw(self, awa):
        Rw = 0.5*self.rho*self.aws**2*self._get_Aref(awa)*0.816
        return Rw * np.cos(awa/180.*np.pi)

    
    def _get_Aref(self, awa):
        # only hull part
        d = 0.5*(1-np.cos(awa/90.*np.pi))
        return self.FBAV*((1-d)*self.B + d*self.L)

    
    def _get_coeffs(self):
        '''
        generate sail-set total lift and drag coefficient.
        '''
        # lift (Clmax) and parasitic drag (Cd0max)
        self.cl = 0.; self.cd = 0.; kpp = 0.

        for sail in self.sails:

            self.cl += sail.cl(self.awa) * sail.area * sail.bk
            self.cd += sail.cd(self.awa) * sail.area * sail.bk
            kpp += sail.cl(self.awa)**2 * sail.area * sail.bk * sail.kp

        self.cl /= self.area
        self.cd /= self.area

        # viscous quadratic parasitic drag and induced drag
        self.CE = kpp/(self.area * self.cl**2) + self.area / (np.pi * self._heff(self.awa)**2)
 
        # fraction of parasitic drag due to jib
        for sail in self.sails:
            if sail.type=='jib':
                self.fcdj = sail.bk * sail.cd(self.awa) * sail.area/(self.cd * self.area)

        # final lift and drag
        self.cd = self.cd * (self.flat * self.fcdmult(self.flat) * self.fcdj + (1-self.fcdj)) + \
                  self.CE * self.cl**2 * self.flat**2 * self.fcdmult(self.flat)
        self.cl = self.flat * self.cl


    def _update_windTriangle(self):
        '''
        find AWS and AWA for a given TWS, TWA and VB
        '''
        _awa_ = lambda awa : self.vb*np.sin(awa/180.*np.pi)-self.tws*np.sin((self.twa-awa)/180.*np.pi)
        self.awa = fsolve(_awa_, self.twa)[0]
        self.aws = np.sqrt((self.tws*np.sin(self.twa/180.*np.pi))**2 + \
                           (self.tws*np.cos(self.twa/180.*np.pi) + self.vb)**2)


    def _area(self):
        '''
        Fill sail area variable
        '''
        self.area = 0.
        for sail in self.sails:
            if(sail.up==self.up):
                self.area += sail.area


    def _vce(self):
        '''
        Vectical centre of effort, NOT correct, must be lift/drag weigted
        '''
        sum = 0.
        for sail in self.sails:
            if(sail.up==self.up):
                sum += sail.area*sail.vce*sail.bk
        self._area()
        return sum/self.area*(1-0.203*(1-self.flat)-0.451*(1-self.flat)*(1-self.fractionality))


    def phi_up(self):
        '''
        heel angle correction for AWA and AWS (5.51), this is in Radians!
        '''
        return 0.5*(self.phi+10*(self.phi/30.)**2)/180.*np.pi


    def _heff(self, awa):
        awa = max(0,min(awa, 90))
        if self.up:
            cheff =  self.eff_span_corr * self.kheff(awa)
        else:
            cheff =  1./self.b * self.reef * self.heff_height_max_spi
        return (self.b + self.HBI) * cheff
        
#
# -- utility functions
#
    def _build_interp_func(self, fname, kind='linear'):
        '''
        build interpolatison function and returns it in a list
        '''
        a = np.genfromtxt('dat/'+fname+'.dat',delimiter=',',skip_header=1)
        # linear for now, this is not good, might need to polish data outside
        return interp1d(a[0,:],a[1,:],kind=kind)


    def debbug(self):
        for sail in self.sails:
            sail.debbug_coeffs()
        flat = np.linspace(0,1,64)
        awa = np.linspace(0,90,64)
        res1 = np.empty_like(flat)
        res2 = np.empty_like(awa)
        for i in range(64):
            res1[i] = self.fcdmult(flat[i])
            res2[i] = self.kheff(awa[i])
        plt.plot(flat,res1)
        plt.show()
        plt.plot(awa,res2)
        plt.show()


    def print_state(self):
        self.update(self.vb,self.phi,self.tws,self.twa)
        print('AeroMod state:')
        print(' TWA is :  %.2f (deg)' % self.twa)
        print(' TWS is :  %.2f (m/s)' % self.tws)
        print(' AWA is :  %.2f (deg)' % self.awa)
        print(' AWS is :  %.2f (m/s)' % self.aws)
        print(' Vb is :   %.2f (m/s)' % self.vb)
        print(' Heel is : %.2f (deg)' % self.phi)
        print(' Drive is: %.2f (N)'   % self.Fx)
        print(' SSF is :  %.2f (N)'   % self.Fy)
        print(' HM is :   %.2f (Nm)'  % self.Mx)
        print(' Cl is :   %.2f (-)'   % self.cl)
        print(' Cd is :   %.2f (-)'   % self.cd)
        print(' Sail area:')
        for sail in self.sails:
            print(' - '+sail.type+' : %.2f (m^2)' % sail.area)


# if __name__ == "__main__":
    # aero = AeroMod(sails=[Main(24.5, 5.5),
    #                       Jib(17.3, 4.4)])
    # aero.debbug()
    # aero.print_state()
