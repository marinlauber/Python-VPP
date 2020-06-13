#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt
from scipy import interpolate


def build_interp_func(fname, i=1, kind="linear"):
    """
        build interpolatison function and returns it in a list
        """
    a = np.genfromtxt("dat/" + fname + ".dat", delimiter=",", skip_header=1)
    # linear for now, this is not good, might need to polish data outside
    return interpolate.interp1d(a[0, :], a[i, :], kind=kind)


def polar(n):
    stl = ["-", "--", "-.", ":"]
    lab = [r"$V_B$ (knots)", r"Heel $\phi$ ($^\circ$)", r"Leeway $\gamma$ ($^\circ$)"]
    fig, ax = plt.subplots(1, n, subplot_kw=dict(polar=True), figsize=(16 / 3 * n, 7.5))
    if n == 1:
        ax.set_xticks(np.linspace(0, np.pi, 5,))
        ax.set_theta_direction(-1)
        ax.set_theta_offset(np.pi / 2.0)
        ax.set_thetamin(0)
        ax.set_thetamax(180)
        ax.set_xlabel(r"TWA ($^\circ$)")
        ax.set_ylabel(lab[0], labelpad=-40)
    else:
        for i in range(n):
            ax[i].set_xticks(np.linspace(0, np.pi, 5,))
            ax[i].set_theta_direction(-1)
            ax[i].set_theta_offset(np.pi / 2.0)
            ax[i].set_thetamin(0)
            ax[i].set_thetamax(180)
            ax[i].set_xlabel(r"TWA ($^\circ$)")
            ax[i].set_ylabel(lab[i], labelpad=-40)
    return fig, ax, stl
