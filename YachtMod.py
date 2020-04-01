#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Marin Lauber"
__copyright__ = "Copyright 2020, Marin Lauber"
__license__ = "GPL"
__version__ = "1.0.1"
__email__  = "M.Lauber@soton.ac.uk"

import numpy as np
from scipy import interpolate


class Appendage(object):

    def __init__(self, Cu=1, Cl=1, Span=0):
        """
        Cu : uppder (root) chord of the appendage
        Cl : lower (tip) chord of the appendage
        Span : span of the appendage
        """
        self.cu = Cu
        self.cl = Cl
        self.span = Span
        self.chord = 0.5*(self.cu+self.cl)
        self.wsa = 2*self.chord*self.span
        self.ce = -self.span*((self.cu+2*self.cl)/(3*(self.cl+self.cu)))
        self.btr = 2.5
        self.lvr = 3.0
        self.vol = 0.


    def print(self):
        print('Chord root : ', self.cu)
        print('Chord tip : ', self.cu)
        print('Chord avrg : ', self.chord)
        print('Span : ', self.span)
        print('WSA : ', self.wsa)
        print('CE : ', self.ce)


class Yacht(object):

    def __init__(self, Lwl, Vol, Bwl, Tc, WSA, Tmax, Amax, App=[]):
        """
        Lwl : waterline length (m)
        Vol : volume of diaplcement (m^3)
        Bwl : waterline beam (m)
        Tc : Caonoe body draft (m)
        Tmax : Maximum draft of yacht (m)
        Amax  : Max section area (m^2)
        App : appendages (Appendages object as list, i.e [Keel(...)] )
        """
        self.l = Lwl
        self.vol = Vol
        self.bwl = Bwl
        self.tc = Tc
        self.wsa = WSA
        self.tmax = Tmax
        self.RM4 = 0.43*self.tmax
        self.amax = Amax

        # standard crew weight
        # self.cw = 25.8*self.LSM0**1.4262
        
        # appednages object
        self.appendages = App

        # righting moment interpolation function
        self._interp_rm = self._build_interp_func('rm')

        # pupulate everything
        self.update()


    def update(self):
        self.lsm = self.l
        self.lvr = self.lsm / self.vol**(1./3.)
        self.btr = self.bwl / self.tc
    

    def measure(self):
        self.update()
        return self.l, self.vol, self.bwl, self.tc, self.wsa


    def measureLSM(self):
        self.update()
        return self.lsm, self.lvr, self.btr


    def _get_gz(self, phi):
        return self._interp_rm(phi) #+ 1./3.*self.rm_default


    def _build_interp_func(self, fname, kind='linear'):
        '''
        build interpolatison function and returns it in a list
        '''
        a = np.genfromtxt('dat/'+fname+'.dat',delimiter=',',skip_header=1)
        # linear for now, this is not good, might need to polish data outside
        return interpolate.interp1d(a[0,:],a[1,:],kind=kind)


if __name__ == "__main__":

    keel = Appendage(Cu=1, Cl=1, Span=1)
    keel.print()
        