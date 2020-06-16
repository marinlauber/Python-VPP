import numpy as np
import matplotlib.pyplot as plt

try:
    plt.style.use("mystyle")
except OSError:
    print("Using default style")

stl = [
    (0, ()),
    (0, (1.1, 1.1)),
    (0, (2.8, 1.1)),
    (0, (2.8, 1.1, 1.1, 1.1)),
    (0, (3, 1, 1, 1, 1, 1)),
    (0, (3, 1, 3, 1, 1, 1, 1, 1)),
    (0, (10, 1, 5, 1)),
]

# get data
dat = np.genfromtxt("YD41.dat")

# polar plot
fig, ax = plt.subplots(1, 1, subplot_kw=dict(polar=True), figsize=(16 / 3, 7.5))

# data is store for 32 TWS, for each TWS
for i, tws in enumerate(np.array([3, 4, 5, 6, 7, 8, 10]) / 0.5144):
    ax.plot(
        dat[int(32 * i) : int(i * 32 + 32), 0],
        dat[int(32 * i) : int(i * 32 + 32), 1],
        "k",
        ls=stl[i],
        label=rf"${tws:.1f}$",
    )
    ax.plot(
        dat[int(32 * i + 1), 0],
        dat[int(32 * i + 1), 1],
        "ok",
        lw=1,
        markersize=4,
        mfc="None",
    )
    ax.plot(
        dat[int(32 * i + 31), 0],
        dat[int(32 * i + 31), 1],
        "ok",
        lw=1,
        markersize=4,
        mfc="None",
    )
# set polar plot to 1/2 plot
ax.set_theta_direction(-1)
ax.set_theta_offset(np.pi / 2.0)
ax.set_thetamin(0)
ax.set_thetamax(180)
ax.set_xlabel(r"TWA ($^\circ$)")
ax.set_ylabel(r"$V_B$ (knots)", labelpad=-40)
ax.legend(title=r"TWS (knots)", loc=1, bbox_to_anchor=(1.05, 1.05))
plt.tight_layout()
plt.savefig("Figure.png", dpi=500)
plt.show()
