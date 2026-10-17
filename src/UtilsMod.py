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


# def write_csv(VPP, fname):
def csv_write(tws_range, twa_range, store, fname):
    import csv
    
    # Init a counter for how many values have been used to average the boat speed for a given wind direction and speed:
    avg_counter = np.zeros((37, 20))

    with open(fname, mode="w", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        # Write header with TWS in knots
        writer.writerow(["TWA\TWS", "2", "4", "6", "8", "10", "12", "14", "16", "18", "20", "22", "24", "26", "28", "30", "32", "34", "36", "38", "40"])
        # Loop through every degree from 0°to 180° in 5° increments
        for angle in range(0, 181, 5):
            # Init row to write
            row = [None] * 21
            # Set angle
            row[0] = angle
            # Go through each TWS and get the corresponding boat speed for the current angle
            for i, tws in enumerate(tws_range):
                # Change tws to knots
                tws = tws / KNOTS_TO_MPS
                for j, twa in enumerate(twa_range):
                    # Get closest wind speed and find column in openCPN. Note we are stuck using these until this issue (https://github.com/rgleason/polar_pi/issues/34) gets dealt with
                    closest_wind_speed_column = round(tws/2)
                    # If closest wind speed column is zero, increment by one so we don't overwrite the angle column.
                    if closest_wind_speed_column == 0:
                        closest_wind_speed_column += 1
                    # Get closest angle and find see if it matches the current angle we are looking for
                    closest_angle = round(twa/5)*5
                    # If the closest_angle matches the angle we're currently working with then get the speeds, otherwise, skip to next entry
                    if closest_angle == angle:
                        # Get boat speed for give wind angle and speed
                        boat_speed = store[i, j, 0, 0]
                        # Get row number
                        row_number = int(angle/5)

                        # Update the row with the boat speed for this angle and wind speed
                        # If there has not been a value used yet, set the value to the boat speed, otherwise, average the current value with the new boat speed
                        if row[closest_wind_speed_column] is None:
                            row[closest_wind_speed_column] = boat_speed
                        else:
                            # Find out how many values have been used to make this average
                            num_values = avg_counter[row_number, closest_wind_speed_column]
                            # Average the current boat speed with the already logged average boat speed
                            row[closest_wind_speed_column] = (row[closest_wind_speed_column] * num_values + boat_speed) / (num_values + 1)

                        # Update the average counter for this angle and wind speed
                        avg_counter[row_number, closest_wind_speed_column] += 1
                        # Print out the speed of the vessel given the angle and wind speed

            # Write the row to the csv file
            writer.writerow(row)


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
