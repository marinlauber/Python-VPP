import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt

class HydroMod(object):

    def __init__(self, L, Vol, Bwl, Tc):

        self.L = L
        self.Vol = Vol
        self.Bwl = Bwl
        self.Tc = Tc
        self.lvr = self.L / self.Vol**(1./3.)
        self.btr = self.Bwl / self.Tc

        # get resistance surfaces from ORC
        self.__load_data()
        

    def update(self, vb, phi, leeway)


    def __load_data(self):
        '''
        Loads ORC resistance surfaces from file and build interpolation function
        '''
        data = np.genfromtxt('dat/ORCi_Rr2013_Drag_Surfaces.csv',delimiter=',',skip_header=1)
        data = data.reshape((24,43,42))
        # y is btr := [2.5,9], z is lvr := [3,9] and x is Fn := [0.125,0.7]
        x = np.arange(0.125,0.725,0.025)
        y = data[0,2:,0]; z = data[0,1,1:]
        # print(x)
        # print(y)
        # print(z)
        # build interpolation function for 3D data
        dat = data[:,2:,1:]
        # self._interp_Rr = interpolate.RegularGridInterpolator((x, y, z), dat)
        self._interp_Rr = interpolate.RegularGridInterpolator((x, y, z), dat)
    

    def _get_Rr(self, fn):
        """
        Get residuary resistance at this froude number
        """
        return self._interp_Rr((self.btr,self.lvr,fn))
    

    def _get_Rv(self, fn):
        """
        Get viscous resistance at this froude number
        """
        return 0.


    def get_Resistance(self, fn):
        return self._get_Rr(fn) + self._get_Rv(fn)


    def print(self):
        print(self.__dict__)


if __name__ == "__main__":
    hydro = HydroMod(L=3.0,Vol=1.0,Bwl=2.5,Tc=1.0)
    # hydro.get_Resistance(fn)
    hydro.print()
