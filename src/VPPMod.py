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
# from mpl_toolkits import mplot3d
import warnings
warnings.filterwarnings('ignore', 'The iteration is not making good progress')
plt.style.use('jupyter')

from src.AeroMod import AeroMod
from src.HydroMod import HydroMod

class VPP(object):

    def __init__(self, Yacht):

        # build model
        self.yacht = Yacht
        self.aero = AeroMod(self.yacht)
        self.hydro = HydroMod(self.yacht)

        # maximum allows heel angle
        self.phi_max = 100.0

        # tws bounds for downwind/upwind sails
        self.lim_up = 60.0
        self.lim_dn = 135.0

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
        
        # prepare storage array
        self.Nsails = len(self.yacht.sails) - 1  # main not counted
        self.store = np.zeros((len(self.tws_range),len(self.twa_range),3*self.Nsails))

        if(self.debbug==True):
            for i in range(self.store.shape[0]):
                self.store[i,:,0] = np.ones_like(twa_range)*tws_range[i]

        # flag for later
        self.upToDate = True
    

    def run(self, verbose=False):

        if(not self.upToDate): raise 'VPP run stop: no analysis set!'

        for i,tws in enumerate(self.tws_range):

            print('Sailing in TWS : %.1f' % (tws/0.5144) )
            
            for n in range(self.Nsails):

                self.aero.sails[1] = self.yacht.sails[n+1]

                print('Sail Config : ', self.aero.sails[0].type+' + '+self.aero.sails[1].type)

                self.aero.up = self.aero.sails[1].up

                # reset
                self.vb0 = 0.35*np.sqrt(self.hydro.l*self.hydro.g)
                self.phi0 = 0.
                self.leeway0 = 0.

                for j in trange(len(self.twa_range)):
                    
                    twa = self.twa_range[j]

                    # don't do low twa with downwind sails
                    if((self.aero.up==True) and(twa>=self.lim_dn)): continue
                    if((self.aero.up==False)and(twa<=self.lim_up)): continue

                    res = fsolve(self.resid,[self.vb0,self.phi0,self.leeway0],args=(twa, tws))
                    
                    self.store[i,j,int(3*n):int(3*(n+1))] = res[:]
                    if verbose:
                        print('Running case :     (%.1f,%.2f)' % (twa,tws))
                        print('Initial Guess Vb :        %.3f' % self.vb0)
                        print('Result for Vb :           %.3f' % res[0])
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

        vb0=x0[0]; phi0=x0[1]; leeway=x0[2] #; flat=x0[3]

        Fxh, Fyh, Mxh = self.hydro.update(vb0, phi0, leeway)
        Fxa, Fya, Mxa = self.aero.update(vb0, phi0, tws, twa, 1.0)

        # heel angle penalty
        # dphi = np.where(phi0>=self.phi_max, phi0-self.phi_max, 0.0)

        return [(Fxh - Fxa)**2, (Mxh - Mxa)**2, (Fyh - Fya)**2]

    
    def _get_VMG(self, vb):
        vmg = abs(vb*np.cos(self.twa_range/180*np.pi))
        return np.argmax(vmg)


    def _make_nice(self, dat):
        if self.Nsails==1:
            vb_up = dat[:,0]/0.5144
            vb_dn = vb_up
            twa_up = self.twa_range/180*np.pi
            twa_dn = twa_up
            phi_up = dat[:,1]
            phi_dn = phi_up
            gam_up = dat[:,2]
            gam_dn = gam_up
            up = np.argmax( vb_up*np.cos(twa_up))
            dn = np.argmax(-vb_dn*np.cos(twa_up))
        else:
            idx = np.argmin(abs(dat[:,0]-dat[:,3]))
            # vb_up = dat[:,0]/0.5144
            # vb_dn = dat[:,3]/0.5144
            vb_up = dat[:idx+2,0]/0.5144
            vb_dn = dat[idx-2:,3]/0.5144
            # twa_up = self.twa_range/180*np.pi
            # twa_dn = self.twa_range/180*np.pi
            twa_up = self.twa_range[:idx+2]/180*np.pi
            twa_dn = self.twa_range[idx-2:]/180*np.pi
            # phi_up = dat[:,1]
            # phi_dn = dat[:,4]
            phi_up = dat[:idx+2,1]
            phi_dn = dat[idx-2:,4]
            # gam_up = dat[:,2]
            # gam_dn = dat[:,5]
            gam_up = dat[:idx+2,2]
            gam_dn = dat[idx-2:,5]
            up = np.argmax( vb_up*np.cos(twa_up))
            dn = np.argmax(-vb_dn*np.cos(twa_dn))
        return twa_up,vb_up,phi_up,gam_up,up,twa_dn,vb_dn,phi_dn,gam_dn,dn


    def polar(self):
        stl = ['-','--','-.',':']
        fig = plt.figure(figsize=(16,7.5))
        ax = fig.add_subplot(131, polar=True)
        ax2 = fig.add_subplot(132, polar=True)
        ax3 = fig.add_subplot(133, polar=True)
        for i in range(self.store.shape[0]):
            twa_up,vb_up,phi_up,gam_up,up,twa_dn,vb_dn,phi_dn,gam_dn,dn = self._make_nice(self.store[i,:,:])
            ax.plot(twa_up,vb_up,'k',lw=1,linestyle=stl[int(i%4)],
                    label=f'{self.tws_range[i]/0.5144:.1f}')
            ax.plot(twa_up[up], vb_up[up],
                    'ok',lw=1,markersize=4,mfc='None')
            ax.plot(twa_dn[dn], vb_dn[dn],
                    'ok',lw=1,markersize=4,mfc='None')
            ax2.plot(twa_up,phi_up,'k',lw=1,linestyle=stl[int(i%4)])
            ax3.plot(twa_up,gam_up,'k',lw=1,linestyle=stl[int(i%4)])
            if self.Nsails!=1:
                ax.plot(twa_dn,vb_dn,'gray',lw=1,linestyle=stl[int(i%4)])
                ax2.plot(twa_dn,phi_dn,'gray',lw=1,linestyle=stl[int(i%4)])
                ax3.plot(twa_dn,gam_dn,'gray',lw=1,linestyle=stl[int(i%4)])
        ax.set_xticks(np.linspace(0,np.pi,5,))  
        ax.set_theta_direction(-1)
        ax.set_theta_offset(np.pi/2.0)    
        ax.set_thetamin(0); ax.set_thetamax(180)
        ax.set_xlabel(r'TWA ($^\circ$)'); ax.set_ylabel(r'$V_B$ (knots)',labelpad=-40)
        ax.legend(title=r'TWS (knots)')
        ax2.set_xticks(np.linspace(0,np.pi,5,))  
        ax2.set_theta_direction(-1)
        ax2.set_theta_offset(np.pi/2.0)    
        ax2.set_thetamin(0); ax2.set_thetamax(180)
        ax2.set_xlabel(r'TWA ($^\circ$)'); ax2.set_ylabel(r'Heel $\phi$ ($^\circ$)',labelpad=-40)
        ax3.set_xticks(np.linspace(0,np.pi,5,))  
        ax3.set_theta_direction(-1)
        ax3.set_theta_offset(np.pi/2.0)    
        ax3.set_thetamin(0); ax3.set_thetamax(180)
        ax3.set_xlabel(r'TWA ($^\circ$)'); ax3.set_ylabel(r'Leeway $\gamma$ ($^\circ$)',labelpad=-40)
        plt.tight_layout()
        plt.show()

