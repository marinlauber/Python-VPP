from AeroMod import AeroMod
from HydroMod import HydroMod
from YachtMod import YachtMod
from scipy.optimize import fsolve
import numpy as np

class VPP(object):

    def __init__(self, hull, rig):

        # store boat
        self.hull = hull
        self.rig = rig

        # build model
        self.areo = AeroMod(self.rig)
        self.hydro = HydroMod(self.hull)
    

    def set_analysis(self, tws_range, twa_range):

        if(tws_range.max()<=35. and tws_range.min()>=2.):
            self.tws_range = tws_range
        else:
            print('Anaylis only valid for TWS range : 2. < TWS < 35. knots.')

        if(twa_range.max()<=180. and tws_range.min()>=0.):
            self.twa_range = twa_range
        else:
            print('Anaylis only valid for TWA range : 0. < TWA < 180. degrees.')
        
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
        vec0 = [self.vb, self.leeway, self.phi]
        # solve
        res = fsolve(self._residuals, x0=vec0, args=[twa, tws])

        # set results
        self.vb = res.x[0]
        self.leeway = res.x[1]
        self.phi = res.x[2]

    
    def _residuals(self, vec, twa, tws):

        [vb, leeway, phi] = vec
        # update forces for current config
        FxA, FyA, MxA = self.areo.update(vb=vb, phi=phi, tws=tws, twa=twa)
        FxH, FyH, MxH = self.hydro.update(vb=vb, phi=phi, leeway=leeway)

        # L-2 residuals
        rFx = (FxA - FxH)**2
        rFy = (FyA - FyH)**2
        rMx = (MxA - MxH)**2

        return np.array([rFx, rFy, rMx])


    def _measure(self):
        pass

    def _write_csv(self):
        pass
