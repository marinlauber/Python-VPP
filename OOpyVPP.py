from scipy.optimize import fsolve
import numpy as np
import matplotlib.pyplot as plt
from AeroMod import AeroMod
from HydroMod import HydroMod
from YachtMod import Yacht
from SailMod import Main, Jib

class VPP(object):

    def __init__(self, hull, rig):

        self.vb = 0.
        self.phi = 0.
        self.awa = 0.
        self.twa = 0.
        self.tws = 0.
        self.aws = 0.

        self.debbug = False

        # build model
        self.hydro = HydroMod(hull)
        self.aero =  AeroMod(rig)
    

    def set_analysis(self, tws_range, twa_range):
        
        if(tws_range.max()<=35. and tws_range.min()>=2.):
            self.tws_range = tws_range*0.5144
        else:
            print('Anaylis only valid for TWS range : 2. < TWS < 35. knots.')
        
        if(twa_range.max()<=180. and twa_range.min()>=0.):
            self.twa_range = twa_range
        else:
            print('Anaylis only valid for TWA range : 0. < TWA < 180. degrees.')
        self.store = np.empty((len(self.tws_range),len(self.twa_range)))

        if(self.debbug==True):
            for i in range(self.store.shape[0]):
                self.store[i,:] = np.ones_like(twa_range)*tws_range[i]

        # flag for later
        self.upToDate = True
    

    def run(self):

        if(not self.upToDate): raise 'VPP run stop: no analysis set!'

        for i,tws in enumerate(self.tws_range):
            for j,twa in enumerate(self.twa_range):
               
                self.tws=tws
                self.twa=twa

                self._set_models(tws, twa)

                self._find_equlibrium(twa, tws)
                self._measure(i,j)
                # self._write_csv()

    
    def _set_models(self, tws, twa):
        vb0 = 0.3*np.sqrt(self.hydro.l*self.hydro.g)
        self.vb = vb0
        phi0 = 0.
        self.phi = phi0
        self.aero._set(self.tws, self.twa, vb0, phi0)
        self.hydro._set(self.vb, self.phi)


    def _find_equlibrium(self, twa, tws):
        # initil gues as previous values
        # vec0 = [0.3*np.sqrt(self.hydro.l*9.81), self.phi]
        
        print('Running case: (%.2f, %.2f)' % (twa, tws))
        print('Initial Guess for boat velocity: %.3f' % self.vb)

        # solve
        # res = fsolve(self._residuals, x0=vec0, args=(twa, tws), xtol=1e-06, maxfev=100)
        for i in range(5):
            res = fsolve(self._res_Fx,x0=self.vb, args=(self.phi, twa, tws), xtol=1e-06, maxfev=10)
            self.vb = res
            res = fsolve(self._res_Mx,x0=self.phi, args=(self.vb, twa, tws), xtol=1e-06, maxfev=10)
            self.phi = res

        print('Result for boat velocity: %.3f' % self.vb)
        print('Lift coefficient:         %.3f' % self.aero.cl)
        print('Drag coefficient:         %.3f' % self.aero.cd)
        # print('Residuals       :         %.3f' % sum(self._residuals([res[0],res[1]], twa, tws)))
        print('Residuals Fx    :         %.3f' % self._res_Fx(self.vb, self.phi, twa, tws))
        print('Residuals Mx    :         %.3f' % self._res_Mx(self.phi, self.vb, twa, tws))


    def _residuals(self, vec, twa, tws):

        [vb, phi] = vec
        # update forces for current config
        FxA, _, MxA = self.aero.update(vb=vb, phi=phi, tws=tws, twa=twa)
        FxH, _, MxH = self.hydro.update(vb=vb, phi=phi)

        # L-2 residuals
        rFx = (FxA - FxH)**2
        # rFy = (FyA - FyH)**2
        rMx = (MxA - MxH)**2

        return [rFx, rMx]


    def _res_Fx(self, vb, phi, twa, tws):
        # update forces for current config
        FxA, _, _ = self.aero.update(vb=vb, phi=phi, tws=tws, twa=twa)
        FxH, _, _ = self.hydro.update(vb=vb, phi=phi)
        # L-2 residuals
        return (FxA - FxH)**2
    def _res_Mx(self, phi, vb, twa, tws):
        # update forces for current config
        _, _, MxA = self.aero.update(vb=vb, phi=phi, tws=tws, twa=twa)
        _, _, MxH = self.hydro.update(vb=vb, phi=phi)
        # L-2 residuals
        return (MxA - MxH)**2


    def _measure(self, i, j):
        self.store[i,j] = self.vb/0.5144

    def _write_csv(self):
        pass

    def polar(self):
        ax = plt.subplot(111, polar=True)
        for i in range(self.store.shape[0]):
            ax.plot(np.deg2rad(self.twa_range),self.store[i,:],'-',lw=1)       
        ax.set_xticks(np.linspace(0,np.pi,5,))  
        ax.set_theta_direction(-1)
        ax.set_theta_offset(np.pi/2.0)    
        ax.set_thetamin(0); ax.set_thetamax(180)
        ax.set_xlabel(r'TWA ($^\circ$)'); ax.set_ylabel(r'$V_B$ (knots)')
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":

    solver = VPP(hull=Yacht(L=8.5,
                            Vol=1.0,
                            Bwl=2.1,
                            Tc=0.4,
                            WSA=13.),
                 rig=[Main(24.5,
                           5.5),
                      Jib(17.3,
                          4.4)])

    solver.set_analysis(tws_range=np.array([8.0, 12.0, 16.0]),
                        twa_range=np.linspace(20, 135, 16))

    # solver.aero.print_state()
    # solver.hydro.print_state()

    solver.run()
    solver.polar()

