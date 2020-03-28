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
            self.tws_range = tws_range
        else:
            print('Anaylis only valid for TWS range : 2. < TWS < 35. knots.')

        if(twa_range.max()<=180. and tws_range.min()>=0.):
            self.twa_range = twa_range
        else:
            print('Anaylis only valid for TWA range : 0. < TWA < 180. degrees.')
        self.store = np.empty((len(self.tws_range),len(self.twa_range)))

        if self.debbug:
            for i in range(self.store.shape[0]):
                self.store[i,:] = np.ones_like(twa_range)*tws_range[i]

        # flag for later
        self.upToDate = True
    

    def run(self):

        if(not self.upToDate): raise 'VPP run stop: no analysis set!'

        for i,tws in enumerate(self.tws_range):
            for j,twa in enumerate(self.twa_range):
                self._find_equlibrium(twa, tws)
                self._measure()
                self._write_csv()


    def _find_equlibrium(self, twa, tws):
        # initil gues as previous values
        vec0 = [self.vb, self.phi]
        # solve
        res = fsolve(self._residuals, x0=vec0, args=(twa, tws))

        # set results
        self.vb = res.x[0]
        self.leeway = res.x[1]
        self.phi = res.x[2]

    
    def _residuals(self, vec, twa, tws):

        [vb, phi] = vec
        # update forces for current config
        FxA, FyA, MxA = self.aero.update(vb=vb, phi=phi, tws=tws, twa=twa)
        FxH, FyH, MxH = self.hydro.update(vb=vb, phi=phi)

        # L-2 residuals
        rFx = (FxA + FxH)**2
        rFy = (FyA + FyH)**2
        rMx = (MxA + MxH)**2

        return np.array([rFx, rFy, rMx])


    def _measure(self):
        pass

    def _write_csv(self):
        pass

    def polar(self):
        ax = plt.subplot(111, polar=True)
        for i in range(self.store.shape[0]):
            ax.plot(np.deg2rad(self.twa_range), self.store[i,:]/0.5144, lw=1)       
        ax.set_xticks(np.linspace(0,np.pi,5,))  
        ax.set_theta_direction(-1)
        ax.set_theta_offset(np.pi/2.0)    
        ax.set_thetamin(0); ax.set_thetamax(180)
        ax.set_xlabel(r'TWA ($^\circ$)'); ax.set_ylabel(r'$V_B$ (knots)')
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":

    solver = VPP(hull=Yacht(L=6.5,
                            Vol=1.0,
                            Bwl=2.1,
                            Tc=0.4,
                            WSA=10.),
                 rig=[Main(24.5,
                           5.5),
                      Jib(17.3,
                          4.4)])

    solver.debbug = True
    solver.set_analysis(tws_range=np.linspace(5, 20, 4),
                        twa_range=np.linspace(30, 180, 32))

    solver.aero.print_state()
    solver.hydro.print_state()

    # solver.run()
    # solver.polar()
