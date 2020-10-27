#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__  = "M.Lauber@soton.ac.uk"

import numpy as np
from src.utils import build_interp_func

class Appendage(object):

    def __init__(self, type, chord, area, span, vol, ce):
        """
        
        """
        self.type = type
        self.chord = chord
        self.area = area
        self.wsa = 2*self.area
        self.ce = ce
        self.vol = vol
        self.span = span
        self.Ar = self.span / self.area

        #  lift-curve slope and coefficient of lift area
        self.dclda = 2*np.pi/(1.+0.5*self.Ar)
        self.cla = self.dclda * self.area
        self.teff = 1.8*self.span
        # no residuary resistance
        self._interp_cr = lambda fn: 0.
        if self.type=='keel':
            self._interp_cr = build_interp_func('rrk')
        if self.type=='bulb':
            self._interp_cr = build_interp_func('rrk',i=2)


    def _cl(self, leeway):
        return self.dclda * np.radians(leeway)


    def _cr(self, fn):
        return self._interp_cr(max(0.0,min(fn,0.6)))


    def _Ksff(self, phi):
        return 1.0


    def print(self):
        print('Chord root : ', self.cu)
        print('Chord tip : ', self.cu)
        print('Chord avrg : ', self.chord)
        print('Span : ', self.span)
        print('WSA : ', self.wsa)
        print('CE : ', self.ce)

    
class Keel(Appendage):
    def __init__(self, Cu=1, Cl=1, Span=0):
        self.type = 'keel'
        self.cu = Cu
        self.cl = Cl
        self.span = Span
        self.chord = 0.5*(self.cu+self.cl)
        self.area = self.chord*self.span
        self.ce = -self.span*((self.cu+2*self.cl)/(3*(self.cl+self.cu)))
        self.cof = 1.31 # correction coeff for t/c 20%
        self.vol = 0.666*self.chord*1.2*self.span
        super().__init__(self.type, self.chord, self.area, self.span, self.vol, self.ce)

class Rudder(Appendage):
    def __init__(self, Cu=1, Cl=1, Span=0):
        self.type = 'rudder'
        self.cu = Cu
        self.cl = Cl
        self.span = Span
        self.chord = 0.5*(self.cu+self.cl)
        self.area = self.chord*self.span
        self.ce = -self.span*((self.cu+2*self.cl)/(3*(self.cl+self.cu)))
        self.cof = 1.21 # correction coeff for t/c 10%
        self.vol = 0.666*self.chord*1.1*self.span
        super().__init__(self.type, self.chord, self.area, self.span, self.vol, self.ce)

    def _Ksff(self, phi):
        # rudder influence gradually ramped up to twice its area
        return np.where(phi<=30,1+0.5*(1-np.cos(phi/30.*np.pi)),1.)

class Bulb(Appendage):
    def __init__(self, Chord, area, vol, CG):
        self.type = 'bulb'
        self.chord = Chord
        self.area = area
        self.ce = CG
        self.vol = vol
        self.cof = 1.50
        super().__init__(self.type, self.chord, self.area, 0.,self.vol,  self.ce)




class Yacht(object):

    def __init__(self, Lwl, Vol, Bwl, Tc, WSA, Tmax, Amax, Mass,
                Loa, Boa, Ff, Fa, App=[], Sails=[]):
        """
        Lwl : waterline length (m)
        Vol : volume of canoe body (m^3)
        Bwl : waterline beam (m)
        Tc : Caonoe body draft (m)
        WSA : Wtter surface area (m^2)
        Tmax : Maximum draft of yacht (m)
        Amax  : Max section area (m^2)
        Mass : total mass of the yacht (kg)
        App : appendages (Appendages object as list, i.e [Keel(...)] )
        """
        self.g = 9.81

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
        self.bmax = 1.4*self.bwl
        self.bdwt = 89.0 # standard crew weight
        self.Rm4 = 0.43*self.tmax

        # standard crew weight
        self.cw = 25.8*self.l**1.4262
        self.carm = 0.8*self.bmax # must be average of rail where crew sits
        
        # rough estimate of projected area of the hull
        self.area_proj = self.l*self.tc*0.666
        self.cla = self.area_proj * 2*np.pi/(1.+0.5*self.area_proj/self.tc)
        self.teff = 2.07*self.tc

        # appednages object
        self.appendages = App
        self.sails = Sails

        # righting moment interpolation function
        self._interp_rm = build_interp_func('rm')

        # pupulate everything
        self.update()


    def update(self):
        self.lsm = self.l
        self.lvr = self.lsm / self.vol**(1./3.)
        self.btr = self.bwl / self.tc
    

    def measure(self):
        self.update()
        return self.l, self.vol, self.mass, self.bwl, self.tc, self.wsa


    def measureLSM(self):
        self.update()
        return self.lsm, self.lvr, self.btr


    def _get_RmH(self, phi):
        # RM default is equal to RM hyrostatic
        return self._interp_rm(phi)*self.mass*self.g  #+ 1./3.*self.rm_default

    
    def _get_RmC(self, phi):
        RmC =  self.carm*(self.cw+0.7*self.bmax*self.bdwt)*np.cos(np.radians(phi))
        # gradually ramp-up crew Rm from 2.5 to 7.5 degrees of heel.
        return RmC*np.where(phi<=7.5,0.5*(1-np.cos(np.maximum(0,phi-2.5)/5.*np.pi)),1.)


# if __name__ == "__main__":

#     keel = Keel(Cu=1, Cl=1, Span=1)
#     keel.print()
        