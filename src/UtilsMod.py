#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt
from scipy import interpolate
import json


KNOTS_TO_MPS = 0.5144
stl = ["-", "--", "-.", ":"]
lab = [r"$V_B$ (knots)", r"Heel $\phi$ ($^\circ$)", r"Leeway $\gamma$ ($^\circ$)"]


def json_read(fname):
    with open(fname+'.json', 'r') as json_file:
        return json.load(json_file)


def json_write(data, fname):
    with open(fname+'.json', 'w') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=2, sort_keys=False)


def build_interp_func(fname, i=1, kind="linear"):
    """
        build interpolatison function and returns it in a list
        """
    a = np.genfromtxt("dat/" + fname + ".dat", delimiter=",", skip_header=1)
    # linear for now, this is not good, might need to polish data outside
    return interpolate.interp1d(a[0, :], a[i, :], kind=kind, fill_value="extrapolate")


def _polar(n):
    fig, ax = plt.subplots(1, n, subplot_kw=dict(polar=True), figsize=(16 / 3 * n, 7.5))
    # allows to simplify polar plot function
    if(n==1): ax = np.array([ax], dtype=object)
    for i in range(n):
        ax[i].set_xticks(np.linspace(0, np.pi, 5,))
        ax[i].set_theta_direction(-1)
        ax[i].set_theta_offset(np.pi / 2.0)
        ax[i].set_thetamin(0)
        ax[i].set_thetamax(180)
        ax[i].set_xlabel(r"TWA ($^\circ$)")
        ax[i].set_ylabel(lab[i], labelpad=-40)
    return fig, ax


def _make_nice(dat, twa_range):
        if(dat.shape[2]==1):
            up = np.argmax( dat[:, 0, 0] * np.cos(twa_range / 180 * np.pi))
            dn = np.argmax(-dat[:, 0, 0] * np.cos(twa_range / 180 * np.pi))
            return np.array([len(dat[:,0,0]), 0]), np.array([up, dn])
        else:
            idx = np.argmin(abs(dat[:, 0, 0] - dat[:, 1, 0]))
            up = np.argmax( dat[:, 0, 0] * np.cos(twa_range / 180 * np.pi))
            dn = np.argmax(-dat[:, 1, 0] * np.cos(twa_range / 180 * np.pi))
            return np.array([idx + 2, idx - 2]), np.array([up, dn])


def polar_plot(VPP, n=1, save=False, awa=False):
        """
        Generate a polar plot of the equilibrium variables.

        Parameters
        ----------
        n
            An integer, number of plots to show, default is 1 (Vb).
        save
            A logical, save figure or not, default is False.

        """
        fig, ax = _polar(n)
        wind = VPP.twa_range
        for i in range(len(VPP.tws_range)):
            idx, vmg = _make_nice(VPP.store[i, :, :, :], VPP.twa_range)
            for j in range(n):
                ax[j].plot(wind[: idx[0]] / 180 * np.pi,VPP.store[i, : idx[0], 0, j],
                            "k",lw=1,linestyle=stl[int(i % 4)],label=f"{VPP.tws_range[i]/KNOTS_TO_MPS:.1f}")
                if VPP.Nsails != 1:
                    ax[j].plot(wind[idx[1] :] / 180 * np.pi,VPP.store[i, idx[1] :, 1, j],
                               "gray",lw=1,linestyle=stl[int(i % 4)])
            # add VMG points
            ax[0].plot(wind[vmg[0]] / 180 * np.pi,VPP.store[i, vmg[0], 0, 0],
                        "ok",lw=1,markersize=4,mfc="None")
            idx2 = np.where(VPP.Nsails==1, 0, 1)
            ax[0].plot(wind[vmg[1]] / 180 * np.pi,VPP.store[i, vmg[1], idx2, 0],
                        "ok",lw=1,markersize=4,mfc="None")
            # add legend only on first axis
            ax[0].legend(title=r"TWS (knots)", loc=1, bbox_to_anchor=(1.05, 1.05))
        plt.tight_layout()
        if save:
            plt.savefig("Figure1.png", dpi=500)
        plt.show()


def sail_chart(VPP, save=False):
    Xtwa, Ytws = np.meshgrid(VPP.twa_range, VPP.tws_range / KNOTS_TO_MPS)
    sails = _get_best_sails(VPP.store)
    p = plt.contourf(Xtwa, Ytws, sails,
                     alpha=0.4, corner_mask=True, levels=VPP.Nsails)
    plt.xlabel(r"TWA ($^\circ$)"); plt.ylabel(r"TWs (Knots)") 
    plt.colorbar(p)
    plt.tight_layout()
    if save:
        plt.savefig("SailChart.png", dpi=500)
    plt.show()


def _get_best_sails(store):
    res = np.zeros(store.shape[:2])
    for i in range(store.shape[0]):
        for j in range(store.shape[1]):
            res[i,j] = store[i,j,:,0].argmax()
    return res


class VPPResults(object):

    def __init__(self, fname):
        self.fname = fname
        self._load_data()

    def _load_data(self):
        self.data = json_read(self.fname); k=1
        self.tws_range = np.array(self.data[0]["tws"])
        self.twa_range = np.array(self.data[0]["twa"])
        self.sails = self.data[0]["Sails"]
        self.Nsails = len(self.sails)
        self.store = np.zeros((len(self.tws_range),
                               len(self.twa_range),
                               self.Nsails,
                               3))
                            
        for i in range(len(self.tws_range)):
            for j in range(len(self.twa_range)):
                for n in range(self.Nsails):
                    self.store[i,j,n,0] = self.data[k]["Speed"]
                    self.store[i,j,n,1] = self.data[k]["Heel"]
                    self.store[i,j,n,2] = self.data[k]["Leeway"]
                    k+=1

    def polar(self, n=1, save=False):
        polar_plot(self, n, save)

    def SailChart(self, save=False):
        sail_chart(self, save)

    def polar_comp(self, other, n=1, save=False):
        """
        Compares polar plot from self to other, where they are both CPPResults

        """
        cols=["r","b"]
        fig, ax = _polar(n)
        for k,itself in enumerate([self, other]):
            wind = itself.twa_range
            for i in range(len(itself.tws_range)):
                idx, vmg = _make_nice(itself.store[i, :, :, :], itself.twa_range)
                for j in range(n):
                    ax[j].plot(wind[: idx[0]] / 180 * np.pi,itself.store[i, : idx[0], 0, j],
                               cols[k],lw=1,linestyle=stl[int(i % 4)],label=f"{itself.tws_range[i]/KNOTS_TO_MPS:.1f}")
                    if itself.Nsails != 1:
                        ax[j].plot(wind[idx[1] :] / 180 * np.pi,itself.store[i, idx[1] :, 1, j],
                                   cols[k],alpha=0.5,lw=1,linestyle=stl[int(i % 4)])
                # add VMG points
                ax[0].plot(wind[vmg[0]] / 180 * np.pi,itself.store[i, vmg[0], 0, 0],
                            "o"+cols[k],lw=1,markersize=4,mfc="None")
                idx2 = np.where(itself.Nsails==1, 0, 1)
                ax[0].plot(wind[vmg[1]] / 180 * np.pi,itself.store[i, vmg[1], idx2, 0],
                            "o"+cols[k],lw=1,markersize=4,mfc="None")
                # add legend only on first axis
                if k==0: ax[0].legend(title=r"TWS (knots)", loc=1, bbox_to_anchor=(1.05, 1.05))
        plt.tight_layout()
        if save:
            plt.savefig("VPP_comparison.png", dpi=500)
        plt.show()



    # def print(self):
    #     print('self.store.shape',self.store.shape); print()
    #     print('self.twa_range', self.twa_range); print()
    #     print('self.tws_range', self.tws_range); print()
    #     print('self.sails', self.sails)
    #     print('self.store', self.store)

    # def test_umod():
    #     res1 = VPPResults("results")
    #     res2 = VPPResults("results")
    #     res2.store *= 1.01
    #     res1.polar_comp(res2, n=1, save=True)
    

