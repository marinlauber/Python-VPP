#!/usr/bin/env python3

import argparse
import os, sys
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

sys.path.append(os.path.realpath("."))

from src.YachtMod import Yacht, Keel, Rudder
from src.SailMod import Main, Jib, Kite
from src.VPPMod import VPP, KNOTS_TO_MPS

tws = np.array([3, 4, 5, 6, 7, 8, 10]) # TWS in m/s
data_file = "dat/YD-41/YD41.dat"
bm_dir = "benchmark/dat/"

def load_data(path, set_size = 32):
    if not os.path.exists(path):
        print("Path not found %s" % path)
        sys.exit(1)
    dat = np.genfromtxt(path)
    if dat.size < tws.size * set_size * 2:
        print("Unexpected dataset size, file %s." % path)
        sys.exit(1)

    res = {key: dat[i*set_size:(i+1)*set_size] for i, key in enumerate(tws)}
    for key in res:
        if res[key][0, 0] > res[key][set_size - 1, 0]:
            res[key] = res[key][::-1] # a couple of sets are reversed
    return res

def load_benchmarks():
    return {f: load_data(os.path.join(bm_dir, f)) for f in os.listdir(bm_dir)}

def compute(tws_val, twa_range):
    Keel1 = Keel(Cu=1.00, Cl=0.78, Span=1.90)
    Rudder1 = Rudder(Cu=0.48, Cl=0.22, Span=1.15)

    YD41 = Yacht(
        Name="YD41",
        Lwl=11.90,
        Vol=6.05,
        Bwl=3.18,
        Tc=0.4,
        WSA=28.20,
        Tmax=2.30,
        Amax=1.051,
        Mass=6500,
        Ff=1.5,
        Fa=1.5,
        Boa=4.2,
        Loa=12.5,
        App=[Keel1, Rudder1],
        Sails=[
            Main(P=16.60, E=5.60, Roach=0.1, BAD=1.0),
            Jib(I=16.20, J=5.10, LPG=5.40, HBI=1.8),
            Kite(area=150.0, vce=9.55),
        ],
    )

    vpp = VPP(Yacht=YD41)
    vpp.set_analysis(np.array([tws_val]) / KNOTS_TO_MPS, twa_range / np.pi * 180.0)
    vpp.run()

    res = np.empty([len(twa_range), 2])
    for i, twa in enumerate(twa_range):
        res[i, :] = [twa , max(vpp.store[0, :, 0][i], vpp.store[0, :, 3][i])]
    return res

def vmg_stats(vb):
    proj = np.multiply(vb[:,1], np.cos(vb[:,0]))
    up_idx = np.argmax(proj)
    down_idx = np.argmin(proj)
    return {'up' : proj[up_idx], 'down': proj[down_idx], 'ang_up': vb[up_idx, 0] / np.pi * 180.0, 'ang_down': vb[down_idx, 0] / np.pi * 180.0}

def collect_stats(bm, calc):
    stats = {f: {} for f in bm}
    for f in bm:
        table = ""
        stats[f] = {
            'std':      np.empty(len(tws)),
            'median':   np.empty(len(tws)),
            'mean':     np.empty(len(tws)),
            'variance': np.empty(len(tws)),
            'vmg_up':   np.empty(len(tws)),
            'vmg_down': np.empty(len(tws)),
            'ang_up':   np.empty(len(tws)),
            'ang_down': np.empty(len(tws))
        }
        for i, s in enumerate(tws):
            calc_vmg = vmg_stats(calc[s])
            diff = calc[s][:,1] - bm[f][s][:,1]
            bm_vmg = vmg_stats(bm[f][s])
            stats[f]['std'][i] = np.std(diff, dtype=np.float64)
            stats[f]['median'][i] = np.median(diff)
            stats[f]['mean'][i] = np.mean(diff, dtype=np.float64)
            stats[f]['variance'][i] = np.var(diff, dtype=np.float64)
            stats[f]['vmg_up'][i] = calc_vmg['up'] - bm_vmg['up']
            stats[f]['vmg_down'][i] = calc_vmg['down'] - bm_vmg['down']
            stats[f]['ang_up'][i] = calc_vmg['ang_up'] - bm_vmg['ang_up']
            stats[f]['ang_down'][i] = calc_vmg['ang_down'] - bm_vmg['ang_down']
            if stats[f]['std'][i] < 1e-3 and abs(stats[f]['mean'][i]) < 1e-3:
                continue
            table += "%2d\t% 2.4f\t% 2.4f\t% 2.4f\t% 2.4f\t% 2.4f\t% 2.4f\t% 2.4f\t% 2.4f\n" % (s,
                stats[f]['std'][i], stats[f]['median'][i],
                stats[f]['mean'][i], stats[f]['variance'][i],
                stats[f]['vmg_up'][i], stats[f]['vmg_down'][i],
                stats[f]['ang_up'][i], stats[f]['ang_down'][i])
        if not table:
            print("Calculation results identical with %s" % f)
        else:
            print("Comparison with %s:" % f)
            print("=======================================================================")
            print("TWS\t Std\t Median\t Mean\t Var\t VMG(u)\t VMG(d)\t ANG(u)\t ANG(d)")
            print("-----------------------------------------------------------------------")
            print(table)

    return stats

def plot_polar(bm, calc, stats):
    print("Generating polar plots...")
    for f in bm:
        if all(std < 1e-3 for std in stats[f]['std']):
            continue
        label = os.path.splitext(f)[0]
        for i, s in enumerate(tws):
            if (stats[f]['std'][i] < 1e-3):
                print("Skip graph for TWS %d, %s" % (s, f))
                continue
            _, ax = plt.subplots(1, 1, subplot_kw=dict(polar=True), figsize=(16 / 3, 7.5))
            twa = bm[f][s][:,0]
            ax.plot(
                twa,
                calc[s][:, 1],
                "k",
                lw=1,
                linestyle=(0, ()),
                label="calc",
            )
            ax.plot(
                twa,
                bm[f][s][:, 1],
                "k",
                lw=1,
                linestyle=(0, (1.1, 1.1)),
                label=label,
            )
            ax.set_theta_direction(-1)
            ax.set_theta_offset(np.pi / 2.0)
            ax.set_thetamin(0)
            ax.set_thetamax(180)
            ax.set_xlabel(r"TWA ($^\circ$)")
            ax.set_ylabel(r"$V_B$ (knots)", labelpad=-40)
            ax.legend(title=r"TWS %d m/s" % s,loc=1, bbox_to_anchor=(1.05, 1.05))

            calc_vmg = vmg_stats(calc[s])
            ax.text(0.8, 0.2,
                "  vmg:%1.2f,%1.2f\n$\Delta$vmg:%1.2f,%1.2f\n$\Delta$ang:%1.2f,%1.2f\n$\sigma$:%1.2f\n$\mu_{1/2}$:%1.2f" %
                    (calc_vmg['up'], calc_vmg['down'],
                        stats[f]['vmg_up'][i], stats[f]['vmg_down'][i],
                        stats[f]['ang_up'][i], stats[f]['ang_down'][i],
                        stats[f]['std'][i], stats[f]['median'][i]),
                transform=ax.transAxes, fontsize=12)

            plt.tight_layout()
            plt.savefig("Figure_%s_%02d.png" % (label, s), dpi=500)

def plot_stats(stats):
    print("Generating statistics plots...")
    for f in stats:
        if all(std < 1e-3 for std in stats[f]['std']):
            continue
        label = os.path.splitext(f)[0]
        _, ax = plt.subplots(1, 1, figsize=(16 / 3, 7.5))
        ax.plot(
            tws,
            stats[f]['std'],
            "k",
            lw=1,
            linestyle=(0, ()),
            label="$\sigma$",
        )
        ax.plot(
            tws,
            stats[f]['median'],
            "k",
            lw=1,
            linestyle=(0, (1.1, 1.1)),
            label="$\mu_{1/2}$",
        )
        ax.plot(
            tws,
            stats[f]['mean'],
            "k",
            lw=1,
            linestyle=(0, (2.8, 1.1)),
            label="mean",
        )
        ax.plot(
            tws,
            stats[f]['variance'],
            "k",
            lw=1,
            linestyle=(0, (2.8, 1.1, 1.1, 1.1)),
            label="variance",
        )
        ax.set_xlabel(r"TWS (m/s)")
        ax.legend(title=r"Stats",loc=1, bbox_to_anchor=(1.05, 1.05))

        plt.tight_layout()
        plt.savefig("Figure_%s_stats.png" % (label), dpi=500)

def benchmark(args):
    if args.purge:
        for f in os.listdir(bm_dir):
            os.remove(os.path.join(bm_dir, f))
    bm = load_benchmarks()
    gt = "GT"
    bm[gt] = load_data(data_file)

    # make sure the grid is the same in all files
    for s in tws:
        for i, ang in enumerate(bm[gt][s][:, 0]):
            for f in bm:
                if f == gt:
                    continue
                if abs(ang - bm[f][s][i, 0]) > 1e-10:
                    print("inconsistency found in %s, tws %d, index %d " % (f, s, i))
                    sys.exit(1)
    calc = {}
    for s in tws:
        calc[s] = compute(s, bm[gt][s][:, 0])

    if args.save:
        filepath = os.path.join(bm_dir, args.output)
        output = open(filepath, "w")
        for s in calc:
            output.write("# TWS %d m/s\n" % s)
            np.savetxt(output, calc[s], fmt="%1.12f")
        output.close()

    stats = collect_stats(bm, calc)
    if args.graph:
        plot_polar(bm, calc, stats)
        plot_stats(stats)
    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='VPP benchmark tool')
    parser.add_argument('-p', '--purge', action='store_true', help='purge old benchmark files')
    parser.add_argument('-g', '--graph', action='store_true', help='generate polar graphs')
    parser.add_argument('-s', '--save', action='store_true', help='save the results')
    parser.add_argument('-o', '--output', default="bm_" + datetime.now().strftime("%Y%m%d%H%M%S") + ".dat", help='output file name')

    benchmark(parser.parse_args())
