import numpy as np
from scipy import interpolate

class Yacht(object):

    def __init__(self, L, Vol, Bwl, Tc, WSA):

        self.l = L
        self.vol = Vol
        self.bwl = Bwl
        self.tc = Tc
        self.wsa = WSA

        self._interp_rm = self._build_interp_func('rm')

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


    def _get_rm(self, phi):
        return self._interp_rm(phi)


    def _build_interp_func(self, fname, kind='linear'):
        '''
        build interpolatison function and returns it in a list
        '''
        a = np.genfromtxt('dat/'+fname+'.dat',delimiter=',',skip_header=1)
        # linear for now, this is not good, might need to polish data outside
        return interpolate.interp1d(a[0,:],a[1,:],kind=kind)


if __name__ == "__main__":
    pass
        