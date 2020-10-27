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
from tqdm import trange
import warnings
plt.style.use('jupyter')

from src.AeroMod import AeroMod
from src.HydroMod import HydroMod
from src.utils import polar


class VPP(object):
    """A VPP Class that run an analysis on a given Yacht."""

    def __init__(self, Yacht):
        """
        Initializes the VPP model

        Parameters
        ----------
        Yacht
            A Yacht object with Appendages and Sails

        """
        # build model
        self.yacht = Yacht
        self.aero = AeroMod(self.yacht)
        self.hydro = HydroMod(self.yacht)

        # maximum allows heel angle
        self.phi_max = 135.0

        # tws bounds for downwind/upwind sails
        self.lim_up = 60.0
        self.lim_dn = 135.0

        # debbuging flag
        self.debbug = False
        if not self.debbug:
            warnings.filterwarnings('ignore','The iteration is not making good progress')
    

    def set_analysis(self, tws_range, twa_range):
        """
        Sets the analysis range.

        Parameters
        ----------
        tws_range
            A numpy.array with the different TWS to run the analysis at.
        twa_range
            A numpy.array with the different TWA to run the analysis at.

        """
        
        if(tws_range.max()<=35. and tws_range.min()>=2.):
            self.tws_range = tws_range*0.5144
        else:
            print('Anaylis only valid for TWS range : 2. < TWS < 35. knots.')
        
        if(twa_range.max()<=180. and twa_range.min()>=0.):
            self.twa_range = twa_range
        else:
            print('Anaylis only valid for TWA range : 0. < TWA < 180. degrees.')
        
        # prepare storage array
        self.Nsails = len(self.yacht.sails) - 1  # main not counted
        self.store = np.zeros((len(self.tws_range),len(self.twa_range),3*self.Nsails))

        # flag for later
        self.upToDate = True
    

    def run(self, verbose=False):
        """
        Run the analysis for the given analysis range.


        Parameters
        ----------
        verbose
            A logical, if True, prints results of equilibrium at each TWA/TWS.
    
        """

        if(not self.upToDate): raise 'VPP run stop: no analysis set!'

        for i,tws in enumerate(self.tws_range):

            print('Sailing in TWS : %.1f' % (tws/0.5144) )
            
            for n in range(self.Nsails):

                self.aero.sails[1] = self.yacht.sails[n+1]

                print('Sail Config : ', self.aero.sails[0].type+' + '+self.aero.sails[1].type)

                self.aero.up = self.aero.sails[1].up

                # reset at every sail change
                self.vb0 = 0.35*np.sqrt(self.hydro.l*self.hydro.g)
                self.phi0 = 0.
                self.leeway0 = 0.

                for j in trange(len(self.twa_range)):
                    
                    twa = self.twa_range[j]

                    # don't do low twa with downwind sails
                    if((self.aero.up==True) and(twa>=self.lim_dn)): continue
                    if((self.aero.up==False)and(twa<=self.lim_up)): continue

                    self.iter = 0

                    while (True and (self.iter<10)):

                        res = fsolve(self.resid,[self.vb0,self.phi0,self.leeway0],args=(twa, tws))
                    
                        # is that a valid equilibrium?
                        if res[1]<=self.phi_max:
                            break
                        
                        # reduce sail area if heel is too much
                        if(self.aero.up==True):
                            if self.aero.sails[1].area!=self.aero.sails[1].min_area:
                                self.aero.sails[1].area = max(self.aero.sails[1].area*0.8, self.aero.sails[1].min_area)
                            else:
                                self.aero.sails[0].area = max(self.aero.sails[0].area*0.8, self.aero.sails[0].min_area)
                        self.iter +=1


                    self.store[i,j,int(3*n):int(3*(n+1))] = res[:]*np.array([1./0.5144,1,1])
                    if verbose:
                        print('Running case :     (%.1f,%.2f)' % (twa,tws))
                        print('Initial Guess Vb :        %.3f' % (self.vb0/0.5144))
                        print('Result for Vb :           %.3f' % (res[0]/0.5144))
                        print('Lift coefficient :        %.3f' % self.aero.cl)
                        print('Drag coefficient :        %.3f' % self.aero.cd)
                        print('Flatener coefficient :    %.3f' % self.aero.flat)
                        print()       
                    
                    self.hydro.update(res[0], res[1], res[2])
                    self.aero.update(res[0], res[1], tws, twa, 1.0)

                    # prepare next iteration
                    self.vb0 = self.hydro.vb
                    self.phi0 = self.hydro.phi
                    self.leeway0 = self.hydro.leeway
                
            print()
        print('Optimization succesfull.')

    
    def resid(self, x0, twa, tws):
        """
        Computes the residuals of the force/moment equilibrium at the given state.

        Parameters
        ----------
        x0
            A numpy array of the variables (DOF).
        twa
            A float of the TWA at which to compute the residuals.
        tws
            A float of the TWs at which to compute the residuals.

        Returns
        -------
        Numpy.Array
            Residuals on each DOF

        """

        vb0=x0[0]; phi0=x0[1]; leeway=x0[2] #; flat=x0[3]

        Fxh, Fyh, Mxh = self.hydro.update(vb0, phi0, leeway)
        Fxa, Fya, Mxa = self.aero.update(vb0, phi0, tws, twa, 1.0)

        return [(Fxh - Fxa)**2, (Mxh - Mxa)**2, (Fyh - Fya)**2]


    def write(self, fname):
        pass


    def _make_nice(self, dat):
        if self.Nsails==1:
            up = np.argmax( dat[:,0]*np.cos(self.twa_range/180*np.pi))
            dn = np.argmax(-dat[:,0]*np.cos(self.twa_range/180*np.pi))
            return np.array([-1,0]), np.array([up, dn])
        else:
            idx = np.argmin(abs(dat[:,0]-dat[:,3]))
            up = np.argmax( dat[:,0]*np.cos(self.twa_range/180*np.pi))
            dn = np.argmax(-dat[:,3]*np.cos(self.twa_range/180*np.pi))
            return np.array([idx+2, idx-2]), np.array([up, dn])


    def polar(self, n=1, save=False):
        """
        Generate a polar plot of the equilibrium variables.

        Parameters
        ----------
        n
            An integer, number of plots to show, default is 1 (Vb).
        save
            A logical, save figure or not, default is False.

        """
        fig, ax, stl = polar(n)
        for i in range(len(self.tws_range)):
            idx, vmg = self._make_nice(self.store[i,:,:])
            if n==1:
                ax.plot(np.radians(self.twa_range[:idx[0]]),self.store[i,:idx[0],0],
                        'k',lw=1,linestyle=stl[int(i%4)],
                        label=f'{self.tws_range[i]/0.5144:.1f}')
                ax.plot(np.radians(self.twa_range[vmg[0]]), self.store[i,vmg[0],0],
                        'ok',lw=1,markersize=4,mfc='None')
                idx2 = np.where(self.Nsails==1,0,3)
                ax.plot(np.radians(self.twa_range[vmg[1]]), self.store[i,vmg[1],idx2],
                        'ok',lw=1,markersize=4,mfc='None')
                if self.Nsails!=1:
                    ax.plot(np.radians(self.twa_range[idx[1]:]),self.store[i,idx[1]:,3],
                           'gray',lw=1,linestyle=stl[int(i%4)])
                ax.legend(title=r'TWS (knots)',loc=1,bbox_to_anchor=(1.05,1.05))
            else:
                for j in range(n):
                    ax[j].plot(np.radians(self.twa_range[:idx[0]]),self.store[i,:idx[0],j],
                            'k',lw=1,linestyle=stl[int(i%4)],
                            label=f'{self.tws_range[i]/0.5144:.1f}')
                    if j == 0:
                        ax[j].plot(np.radians(self.twa_range[vmg[0]]), self.store[i,vmg[0],j],
                                'ok',lw=1,markersize=4,mfc='None')
                        idx2 = np.where(self.Nsails==1,j,int(j+3))
                        ax[j].plot(np.radians(self.twa_range[vmg[1]]), self.store[i,vmg[1],idx2],
                                'ok',lw=1,markersize=4,mfc='None')
                    if self.Nsails!=1:
                        ax[j].plot(np.radians(self.twa_range[idx[1]:]),self.store[i,idx[1]:,int(j+3)],
                                'gray',lw=1,linestyle=stl[int(i%4)])
                ax[0].legend(title=r'TWS (knots)',loc=1,bbox_to_anchor=(1.05,1.05))
        plt.tight_layout()
        if save: plt.savefig('Figure.png',dpi=500)
        plt.show()
