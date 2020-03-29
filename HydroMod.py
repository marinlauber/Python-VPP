import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt
from YachtMod import Yacht

class HydroMod(object):

    def __init__(self, yacht):

        self.yacht = yacht

        # measure yacht to get dimensions
        self.l,self.vol,self.bwl,self.tc,self.wsa = self.yacht.measure()
        self.lms,self.lvr,self.btr = self.yacht.measureLSM()
        self.area_rudder = 1.
        self.area_keel = 1.
        self.area_bulb = 1.


        # get resistance surfaces from ORC
        self.__load_data()

        # physical parameters
        self.rho = 1025.0
        self.mu = 0.00119
        self.nu = self.mu/self.rho
        self.g   = 9.81

        self.update(1.,10.)

    
    def _set(self, vb, phi):
        self.yacht.vb = vb
        self.yacht.phi = phi


    def __load_data(self):
        '''
        Loads ORC resistance surfaces from file and build interpolation function
        '''
        surf = np.genfromtxt('dat/ORCi_Drag_Surfaces.csv',delimiter=',',skip_header=1)
        surf = surf.reshape((24,43,42))
        # x is Fn := [0.125,0.7], y is btr := [2.5,9], z is lvr := [3,9] 
        fn = np.linspace(0.125,0.7,24)
        btr = surf[0,2:,0]; lvr = surf[0,1,1:]
        # build interpolation function for 3D data
        surf = surf[:,2:,1:]
        self._interp_Rr = interpolate.RegularGridInterpolator((fn, btr, lvr), surf)
    

    def _get_Rr(self):
        """
        Get residuary resistance at this froude number
        """
        fn = max(0.125,(min(self.fn,0.7)))
        return self._interp_Rr((fn,self.btr,self.lvr))*self.vol*self.rho
    

    def _get_Rv(self):
        """
        Get viscous resistance at this froude number
        """
        return 0.5*self.rho*self.wsa*self.vb**2*self._cf()*1.05


    def _cf(self):
        self.Re = 0.85*self.vb*self.lsm/self.nu
        return 0.066*(np.log10(self.Re)-2.03)**(-2)


    def _get_fn(self):
        self.fn = self.vb / (np.sqrt(self.g*self.lsm))


    def update(self, vb, phi):

        self.vb = vb
        self.phi = phi
        self.lsm, self.lvr, self.btr = self.yacht.measureLSM()
        self._get_fn()

        # resistance
        self.Fx = self._get_Rr() + self._get_Rv()
        self.Fy = 0.

        # measure righting moment, bounded to 45 degrees of heel
        phi = max(0,min(self.phi,45))
        self.Mx = self.yacht._get_rm(phi)*self.vol*self.rho*self.g

        return self.Fx, self.Fy, self.Mx


    def debbug(self):
        phi = np.linspace(0,40,64)
        res = np.empty_like(phi)
        for i in range(64):
            res[i] = self.yacht._get_rm(phi[i])
        plt.plot(phi,res)
        plt.show()

    def debbug_interp(self):
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


# if __name__ == "__main__":
    
#     hydro = HydroMod(Yacht(L=6.5,Vol=1.0,Bwl=2.1,Tc=0.4,WSA=10.))
#     hydro.print_state()
#     hydro.debbug()
#     hydro.debbug_interp()
