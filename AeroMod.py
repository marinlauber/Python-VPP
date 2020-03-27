import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt
from SailMod import Main,Jib

class AeroMod(object):

    def __init__(self, sails):
        '''
        Initializes an Aero Model, given a set of sails
        '''
        # minimal init ALL units in m/s, kg, degrees
        self.tws = 12.*0.5144
        self.twa = 40.
        self.vb = 5.06*0.5144
        self.phi = 20.
        self.flat = 1.
        self.b = 11.53
        self.HBI = 1.

        # are we upwind?
        self.up = True

        # set sails
        self.sails = sails

        fractionality = 0.92 #I_current / (P + BAS)
        overlap = 0.93 #LGP_current / J
        roach = 0.94
        self.eff_span_corr = 1.1*0.8*(roach-0.2)+0.5*(0.68+0.31*fractionality+0.0075*overlap-1.1)


        # coeffs interp function
        self.fcdmult = self._build_interp_func('fcdmult')
        self.kheff  =  self._build_interp_func('kheff')
        
        # physical params
        self.rho = 1.225
        self.mu = 0.0000181

        # basic forces
        self._update_windTriangle()
        self._area()
        self._compute_forces()


    # prototype top function in hydro mod
    def update(self, vb, phi, tws, twa):
        '''
        Update the aero model for current iter
        '''
        self.vb = vb
        self.phi = phi
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

        # lift and drag
        self.lift = 0.5*self.rho*self.aws**2*self.area*self.cl
        self.drag = 0.5*self.rho*self.aws**2*self.area*self.cd

        # instead of writing many time
        twa = np.deg2rad(self.twa)
        # project into yacht coordinate system
        self.Fx = self.lift*np.sin(twa) - self.drag*np.cos(twa)
        self.Fy = self.lift*np.cos(twa) + self.drag*np.sin(twa)
        # heeling moment
        self.Mx = self.Fy * self._vce() * np.cos(np.deg2rad(self.phi_up()))

    
    def _get_coeffs(self):
        '''
        generate sail-set total lift and drag coefficient.
        '''
        # lift (Clmax) and parasitic drag (Cd0max)
        self.cl = 0.; self.cd = 0.; par = 0.
        for sail in self.sails:
            self.cl += sail.cl(self.awa) * sail.area * sail.bk
            self.cd += sail.cd(self.awa) * sail.area * sail.bk
            par += sail.cl(self.awa)**2 * sail.area * sail.bk * sail.kp
        self.cl /= self.area; self.cd /= self.area

        # viscous quadratic parasitic drag and induced drag
        self.CE = par/(self.area * self.cl**2) + self.area / (np.pi * self.heff(self.awa)**2)

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
        a = self.tws*np.sin(np.deg2rad(self.twa))*np.cos(np.deg2rad(self.phi_up()))
        b = self.tws*np.cos(np.deg2rad(self.twa))+self.vb
        self.awa = np.rad2deg(np.arctan(a/b))
        self.aws = np.sqrt(a**2 + b**2)


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
        return sum / self.area


    def phi_up(self):
        '''
        heel angle correction for AWA and AWS (5.51)
        '''
        return 0.5*(self.phi+10*(self.phi/30.)**2)


    def heff(self, awa):
        return (self.b + self.HBI) * self.eff_span_corr * self.kheff(awa)
#
# -- utility functions
#
    def _build_interp_func(self, fname, kind='linear'):
        '''
        build interpolatison function and returns it in a list
        '''
        a = np.genfromtxt('dat/'+fname+'.dat',delimiter=',',skip_header=1)
        # linear for now, this is not good, might need to polish data outside
        return interpolate.interp1d(a[0,:],a[1,:],kind=kind)

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
        print('AeroMod state:')
        print(' TWA is:   %.2f' % self.twa)
        print(' TWS is:   %.2f' % self.tws)
        print(' AWA is:   %.2f' % self.awa)
        print(' AWS is:   %.2f' % self.aws)
        print(' VB is :   %.2f' % self.vb)
        print(' Heel is   %.2f' % self.phi)
        print(' SSF is:   %.2f' % self.Fy)
        print(' Drive is: %.2f' % self.Fx)
        print(' HeelM is: %.2f' % self.Mx)
        print(' Lift is : %.2f' % self.cl)
        print(' Drag is : %.2f' % self.cd)


if __name__ == "__main__":
    aero = AeroMod(sails=[Main(24.5, 5.5),
                          Jib(17.3, 4.4)])
    aero.debbug()
    aero.print_state()
