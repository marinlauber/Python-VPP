#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from scipy import interpolate
from scipy.interpolate import RegularGridInterpolator

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


def csv_write(VPP, tws_range=None, twa_range=None, fname="polar.csv"):
    """
    Export the best boat speed (knots) to a polar csv file (TWA rows, TWS
    columns, ";" separated), the format read by routing software such as OpenCPN.

    Parameters
    ----------
    VPP
        A VPP (after run) or VPPResults object.
    tws_range
        Optional TWS (knots) to write. Default: the TWS of the VPP analysis.
    twa_range
        Optional TWA (degrees) to write. Default: the TWA of the VPP analysis.
    fname
        Name of the csv file, default "polar.csv".

    If tws_range or twa_range is given, the VPP results are linearly
    interpolated onto it; points outside the analysed range, or where no sail
    set can be carried, are written as 0.
    """
    if not hasattr(VPP, "store"):
        raise ValueError("VPP object must have a 'store' attribute to export to csv.")
    import csv

    # best boat speed over the sail sets, the store already holds knots
    vpp_tws = np.asarray(VPP.tws_range) / KNOTS_TO_MPS
    vpp_twa = np.asarray(VPP.twa_range)
    speed = np.max(np.asarray(VPP.store)[:, :, :, 0], axis=2)
    tws = vpp_tws if tws_range is None else np.asarray(tws_range, dtype=float)
    twa = vpp_twa if twa_range is None else np.asarray(twa_range, dtype=float)
    if tws_range is not None or twa_range is not None:
        func = RegularGridInterpolator(
            (vpp_tws, vpp_twa), speed, bounds_error=False, fill_value=0.0
        )
        grid = np.stack(np.meshgrid(tws, twa, indexing="ij"), axis=-1)
        speed = func(grid)

    with open(fname, mode="w", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        # header with TWS in knots
        writer.writerow(["TWA\\TWS"] + [f"{round(ws, 2):g}" for ws in tws])
        for j, angle in enumerate(twa):
            writer.writerow(
                [f"{round(angle, 2):g}"] + [f"{speed[i, j]:.2f}" for i in range(len(tws))]
            )


def build_interp_func(fname, i=1, kind="linear"):
    """
    build interpolation function and returns it in a list
    """
    a = np.genfromtxt("dat/" + fname + ".dat", delimiter=",", skip_header=1)
    # Filter out NaN values for make_interp_spline compatibility
    mask = ~(np.isnan(a[0, :]) | np.isnan(a[i, :]))
    x = a[0, mask]
    y = a[i, mask]
    k = {"linear": 1, "quadratic": 2, "cubic": 3}.get(kind, 1)
    spline = interpolate.make_interp_spline(x, y, k=k)
    spline.extrapolate = True
    return spline


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


def _get_cross(dat, n, pad=2):
    """Return [start, end) TWA indices where sail *n* is fastest.

    Parameters
    ----------
    dat : ndarray
        Shape ``(ntwa, nsails, nvars)``.
    n : int
        Sail index.
    pad : int
        Number of extra TWA indices to include on each side for visual
        overlap.  Use 0 for a tight (no-overlap) range.
    """
    max_ = np.where(dat[:, n, 0] >= np.max(dat[:, :, 0], axis=1))[0]
    if len(max_) > 0:
        lo, hi = min(max_), max(max_) + 1
        # only pad over points that were solved for this sail (skipped ones are 0)
        for _ in range(pad):
            if lo > 0 and dat[lo - 1, n, 0] > 0:
                lo -= 1
            if hi < len(dat) and dat[hi, n, 0] > 0:
                hi += 1
        return np.array([lo, hi], dtype=int)
    else:
        return np.array([0, 0])


def polar_plot(VPP_list, n, save, fname="Polars.pdf") -> None:
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
    tws_handles = []
    for VPP in VPP_list:
        wind = VPP.twa_range
        name = "" if len(VPP_list) == 1 else VPP.name
        for i in range(len(VPP.tws_range)):
            vmg, ids = _get_vmg(VPP.store[i, :, :, :], VPP.twa_range)
            for k in range(VPP.Nsails):
                for j in range(n):
                    # Speed plot (j=0) uses overlap padding so sail curves
                    # connect visually; heel/leeway (j>0) use tight range
                    # to avoid discontinuities at sail crossover points.
                    pad = 2 if j == 0 else 0
                    idx = _get_cross(VPP.store[i, :, :, :], k, pad=pad)
                    ax[j].plot(
                        wind[idx[0] : idx[1]] / 180 * np.pi,
                        VPP.store[i, idx[0] : idx[1], k, j],
                        color=cols[k % 7],
                        lw=np.where(i < 7, 1.5, 2.5),
                        linestyle=stl[i % 7],
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
            # TWS legend entry in black, colours are reserved for sail sets
            tws_handles.append(Line2D(
                [0], [0], color="k", lw=np.where(i < 7, 1.5, 2.5), linestyle=stl[i % 7],
                label=name + " " + f"{VPP.tws_range[i]/KNOTS_TO_MPS:.1f}",
            ))

    # TWS legend on every axis
    for j in range(n):
        ax[j].legend(handles=tws_handles, title=r"TWS (knots)", loc=1,
                     bbox_to_anchor=(1.05, 1.05))

    # Sail colour legend along the bottom of the figure
    VPP = VPP_list[-1]
    sail_handles = [
        Line2D([0], [0], color=cols[k % 7], lw=2, label=VPP.sail_name[k])
        for k in range(VPP.Nsails)
    ]
    fig.legend(
        handles=sail_handles, title="Sail set",
        loc="lower center", ncol=VPP.Nsails, frameon=True,
    )
    plt.tight_layout()
    fig.subplots_adjust(bottom=0.12)
    if save:
        plt.savefig(fname)
    else:
        plt.show()


def sail_chart(VPP, save, fname="SailChart.pdf"):
    sailset = _get_best_sails(VPP.store)

    twa = VPP.twa_range
    tws = VPP.tws_range / KNOTS_TO_MPS  # stored in m/s, plotted in knots
    twas = np.hstack((twa[0] - (twa[1] - twa[0]), twa, twa[-1] + (twa[-1] - twa[-2])))
    twss = np.hstack((tws[0] - (tws[1] - tws[0]), tws, tws[-1] + (tws[-1] - tws[-2])))
    xnew = np.linspace(twas[0], twas[-1], 101)
    ynew = np.linspace(twss[0], twss[-1], 51)

    fig, ax = _polar(1)
    ax[0].set_ylabel(r"TWS (Knots)", labelpad=-60)
    h = []
    ntws, ntwa, _, _ = VPP.store.shape
    for id in range(VPP.Nsails):
        sail = np.zeros((ntws + 2, ntwa + 2))
        for i in range(ntws):
            for j in range(ntwa):
                if sailset[i, j] == id:
                    sail[i + 1, j + 1] = 1.0
        func = RegularGridInterpolator(
            (twss, twas), sail, method="cubic", bounds_error=False, fill_value=0.0
        )
        yy, xx = np.meshgrid(ynew, xnew, indexing="ij")
        data = func((yy, xx))
        data = np.clip(data, 0.0, 1.0)
        ax[0].contour(
            np.radians(xnew), ynew, data, levels=[0.4], colors=cols[id], alpha=0.8
        )
        c = ax[0].contourf(
            np.radians(xnew), ynew, data, levels=[0.4, 1.0], colors=cols[id], alpha=0.5
        )
        h1, _ = c.legend_elements()
        h.append(h1[0])
    ax[0].legend(h, VPP.sail_name, title=r"Sail Set", loc=1, bbox_to_anchor=(1.05, 0.7))
    plt.tight_layout()
    if save:
        plt.savefig(fname)
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
            "Figure.pdf",
        )

    def SailChart(self, save=False):
        sail_chart(self, save)

    def polar_comp(self, other, n=1, save=False):
        polar_plot([self, other], n, save, "VPP_comparison.pdf")
