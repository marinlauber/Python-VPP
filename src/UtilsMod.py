#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import Akima1DInterpolator,RectBivariateSpline

KNOTS_TO_MPS = 0.5144
stl = [
    (0, ()),
    (0, (1.1, 1.1)),
    (0, (2.8, 1.1)),
    (0, (2.8, 1.1, 1.1, 1.1)),
    (0, (3, 1, 1, 1, 1, 1)),
    (0, (3, 1, 3, 1, 1, 1, 1, 1)),
    (0, (7, 1, 1, 1, 1, 1)),
]
lab = [
    r"$V_B$ (knots)",
    r"Heel $\phi$ ($^\circ$)",
    r"Leeway $\gamma$ ($^\circ$)",
    r"Flat",
    r"RED",
]
cols = ["C0", "C1", "C2", "C3", "C4", "C5", "C6"]


def json_read(fname):
    with open(fname + ".json", "r") as json_file:
        return json.load(json_file)


def json_write(data, fname):
    with open(fname + ".json", "w") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=2, sort_keys=False)


def build_interp_func(fname, i=1, kind="linear"):
    """
    build interpolatison function and returns it in a list
    """
    a = np.genfromtxt("dat/" + fname + ".dat", delimiter=",", skip_header=1)
    # linear for now, this is not good, might need to polish data outside
    return Akima1DInterpolator(a[0, :], a[i, :], extrapolate=True)


def _polar(n) -> plt.Figure:
    fig, ax = plt.subplots(1, n, subplot_kw=dict(polar=True), figsize=(16 / 3 * n, 7.5))
    # allows to simplify polar plot function
    if n == 1:
        ax = np.array([ax], dtype=object)
    for i in range(n):
        ax[i].set_xticks(
            np.linspace(
                0,
                np.pi,
                5,
            )
        )
        ax[i].set_theta_direction(-1)
        ax[i].set_theta_offset(np.pi / 2.0)
        ax[i].set_thetamin(0)
        ax[i].set_thetamax(180)
        # ax[i].set_rorigin(-1)
        ax[i].set_rmin(0.0)
        ax[i].set_xlabel(r"TWA ($^\circ$)")
        ax[i].set_ylabel(lab[i], labelpad=-40)
    return fig, ax


def _get_vmg(dat, twa_range):
    if dat.shape[1] == 1:  # if only one sails, it has both VMGs
        up = np.argmax(dat[:, 0, 0] * np.cos(twa_range / 180 * np.pi))
        dn = np.argmax(-dat[:, 0, 0] * np.cos(twa_range / 180 * np.pi))
        return np.array([up, dn]), np.array([0, 0])
    else:
        up = np.zeros(dat.shape[1])
        dn = np.zeros(dat.shape[1])
        ix = np.zeros(dat.shape[1])
        iy = np.zeros(dat.shape[1])
        for i in range(dat.shape[1]):
            # get the best upwind downwind vmg for each sail sets
            vmg = dat[:, i, 0] * np.cos(twa_range / 180 * np.pi)
            up[i] = np.max(vmg)
            dn[i] = np.max(-vmg)
            ix[i] = np.nanargmax(vmg)
            iy[i] = np.nanargmax(-vmg)
        # get overall best upwind down wind vmgs
        sup = np.argmax(up)
        sdn = np.argmax(dn)
        # get at what angle they happen
        return np.array([ix[sup], iy[sdn]], dtype=int), np.array([sup, sdn])


def _get_cross(dat, n):
    max_ = np.where(dat[:, n, 0] >= np.max(dat[:, :, 0], axis=1))[0]
    if len(max_) > 0:
        idx = np.array(
            [max(min(max_) - 2, 0), min(max(max_) + 2, len(dat[:, n, 0]))], dtype=int
        )
        return idx
    else:
        return np.array([0, 0])


def polar_plot(VPP_list, n, save, fname="Polars.png") -> None:
    """
    Generate a polar plot of the equilibrium variables.

    Parameters
    ----------
    n
        An integer, number of plots to show, default is 1 (Vb).
    save
        A logical, save figure or not, default is False.

    """
    # if we just want the velocity, we also output the gradient
    fig, ax = _polar(n)
    for l, VPP in enumerate(VPP_list):
        wind = VPP.twa_range
        name = "" if len(VPP_list) == 1 else VPP.name
        for i in range(len(VPP.tws_range)):
            vmg, ids = _get_vmg(VPP.store[i, :, :, :], VPP.twa_range)
            for k in range(VPP.Nsails):
                idx = _get_cross(VPP.store[i, :, :, :], k)
                for j in range(n):
                    lab = "_nolegend_"
                    if k == 0:
                        lab = name + " " + f"{VPP.tws_range[i]/KNOTS_TO_MPS:.1f}"
                    ax[j].plot(
                        wind[idx[0] : idx[1]] / 180 * np.pi,
                        VPP.store[i, idx[0] : idx[1], k, j],
                        color=cols[k % 7],
                        lw=np.where(i < 7, 1.5, 2.5),
                        linestyle=stl[i % 7],
                        label=lab,
                    )
            # add VMG points
            for pts in range(2):
                ax[0].plot(
                    wind[vmg[pts]] / 180 * np.pi,
                    VPP.store[i, vmg[pts], ids[pts], 0],
                    "o",
                    color=cols[ids[pts] % 7],
                    lw=1,
                    markersize=4,
                    mfc="None",
                )
            # add legend only on first axis
            ax[0].legend(title=r"TWS (knots)", loc=1, bbox_to_anchor=(1.05, 1.05))
    plt.tight_layout()
    if save:
        plt.savefig(fname, dpi=96)
    else:
        plt.show()


def sail_chart(VPP, save, fname="SailChart.png"):
    sailset = _get_best_sails(VPP.store)
    print(sailset)
    twa = VPP.twa_range
    tws = VPP.tws_range
    twas = np.hstack((twa[0] - (twa[1] - twa[0]), twa, twa[-1] + (twa[-1] - twa[-2])))
    twss = np.hstack((tws[0] - (tws[1] - tws[0]), tws, tws[-1] + (tws[-1] - tws[-2])))
    xnew = np.linspace(twss[0], twss[-1], 51)
    ynew = np.linspace(twas[0], twas[-1], 51)

    fig, ax = _polar(1)
    ax[0].set_ylabel(r"TWS (Knots)", labelpad=-60)
    h = []
    ntws, ntwa, _, _ = VPP.store.shape
    for id in range(VPP.Nsails):
        sail = np.zeros((ntws+2, ntwa+2))
        for i in range(ntws):
            for j in range(ntwa):
                if sailset[i, j] == id:
                    sail[i+1, j+1] = 1.0
        func = RectBivariateSpline(twss, twas, sail)
        data = func(xnew, ynew)
        data = np.where(data > 1.0, 1.0, data)
        print(data)
        ax[0].contour(
            np.radians(ynew), xnew, data, levels=[0.4], colors=cols[id], alpha=0.8
        )
        c = ax[0].contourf(
            np.radians(ynew), xnew, data, levels=[0.4, 1.0], colors=cols[id], alpha=0.5
        )
        h1, _ = c.legend_elements()
        h.append(h1[0])
    ax[0].legend(h, VPP.sail_name, title=r"Sail Set", loc=1, bbox_to_anchor=(1.05, 0.7))
    plt.tight_layout()
    if save:
        plt.savefig(fname, dpi=96)
    else:
        plt.show()


def _get_best_sails(store):
    res = np.zeros(store.shape[:2])
    for i in range(store.shape[0]):
        for j in range(store.shape[1]):
            res[i, j] = store[i, j, :, 0].argmax()
    return res


class VPPResults(object):
    def __init__(self, *args):
        self.fname = "results"
        for arg in args:
            self.fname = arg
        self._load_data()

    def _load_data(self):
        self.data = json_read(self.fname)
        self.name = self.data["name"]
        self.tws_range = np.array(self.data["tws"])
        self.twa_range = np.array(self.data["twa"])
        self.sail_name = self.data["sails"]
        self.Nsails = len(self.sail_name)
        self.store = np.zeros(
            (len(self.tws_range), len(self.twa_range), self.Nsails, 3)
        )
        # fille the store
        for i in range(len(self.tws_range)):
            for j in range(len(self.twa_range)):
                for n in range(self.Nsails):
                    self.store[i, j, n, 0:2] = self.data["results"][i][j][n][0:2]

    def polar(self, n=1, save=False):
        polar_plot(
            [self],
            n,
            save,
            "Figure.png",
        )

    def SailChart(self, save=False):
        sail_chart(self, save)

    def polar_comp(self, other, n=1, save=False):
        polar_plot([self, other], n, save, "VPP_comparison.png")
