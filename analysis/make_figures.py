# -*- coding: utf-8 -*-
"""Regenerate all paper figures from the rung A measurement table.

Source data: measurements/rungA_geocalib_v2.csv (one row per calibrated frame;
produced by scripts/calibrate_rungA.py on the 70 Blender renders in raw/rungA/).

Outputs (analysis/figures/):
  fig1_pipeline.png    measurement-pipeline schematic (static, no data)
  fig2_rungA_vfov.png  true vs GeoCalib-estimated vFoV, per scene, both protocols
  fig3_rungA_error.png mean absolute vFoV error per focal level (min-max whiskers)

Run:  python analysis/make_figures.py
Deps: pandas, numpy, matplotlib (all in requirements.txt). Runtime: < 10 s.
"""
import os

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV = os.path.join(ROOT, "measurements", "rungA_geocalib_v2.csv")
OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

TRUE_VFOV = {16: 73.74, 24: 53.13, 35: 37.849, 50: 26.991,
             85: 16.071, 135: 10.159, 200: 6.867}  # 35mm-equivalent, h=24mm


def fig1_pipeline():
    fig, ax = plt.subplots(figsize=(10, 2.4))
    ax.axis("off")
    boxes = [("Scene text +\ncamera clause\n(3 registers x\n5 focal levels)", 0.02),
             ("Frozen-seed\ngeneration\nSDXL / SD3.5 /\nFLUX.1-schnell", 0.22),
             ("1024x1024\nimage + sidecar\n(seed, model hash,\ndevice)", 0.42),
             ("GeoCalib x3\n(pinhole weights,\ntorch seed 0,\nmedian vFoV)", 0.62),
             ("y = ln tan(vFoV/2)\nvs x = ln(focal)\n-> adherence\nslope beta", 0.82)]
    for text, xc in boxes:
        ax.add_patch(plt.Rectangle((xc, 0.2), 0.15, 0.6, fill=False, lw=1.4))
        ax.text(xc + 0.075, 0.5, text, ha="center", va="center", fontsize=8)
    for x0 in [0.17, 0.37, 0.57, 0.77]:
        ax.annotate("", xy=(x0 + 0.05, 0.5), xytext=(x0, 0.5),
                    arrowprops=dict(arrowstyle="->", lw=1.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title("Measurement pipeline (pre-registered): from language to a physical slope",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig1_pipeline.png"), dpi=200)
    plt.close(fig)


def fig2_vfov(df):
    focals = sorted(df["focal_mm"].unique())
    scenes = sorted(df["scene"].unique())
    colors = plt.cm.tab10(np.linspace(0, 1, len(scenes)))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    for ax, proto, name in zip(axes,
                               ["fixedpos", "fixedframe"],
                               ["Protocol A2: fixed position", "Protocol A1: fixed framing"]):
        ax.plot(focals, [TRUE_VFOV[f] for f in focals], "k--", lw=1.5,
                label="pinhole ground truth")
        for c, s in zip(colors, scenes):
            sub = df[(df.protocol == proto) & (df.scene == s)]
            sub = sub.set_index("focal_mm").reindex(focals)
            ax.plot(focals, sub["est_vfov_deg"], "o-", color=c, ms=4, lw=1, label=s)
        ax.set_xscale("log")
        ax.set_xticks(focals)
        ax.set_xticklabels([int(f) for f in focals])
        ax.set_xlabel("focal length (mm, 35mm-equivalent)")
        ax.set_title(name)
        ax.grid(alpha=.3)
    axes[0].set_ylabel("vertical FoV (degrees)")
    axes[0].legend(fontsize=7, ncol=2)
    fig.suptitle("Rung A: GeoCalib-estimated vFoV vs. ground truth on synthetic "
                 "focal ladder (5 scenes)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig2_rungA_vfov.png"), dpi=200)
    plt.close(fig)


def fig3_error(df):
    focals = sorted(df["focal_mm"].unique())
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    w = 1.8
    for i, (proto, label) in enumerate([("fixedpos", "fixed position"),
                                        ("fixedframe", "fixed framing")]):
        means, mins_, maxs_ = [], [], []
        for f in focals:
            errs = df[(df.protocol == proto) & (df.focal_mm == f)]["err_deg"].abs()
            means.append(errs.mean())
            mins_.append(errs.min())
            maxs_.append(errs.max())
        off = -w / 2 if i == 0 else w / 2
        ax.bar(np.array(focals) + off, means, width=w, label=label)
        ax.errorbar(np.array(focals) + off, means,
                    yerr=[np.array(means) - mins_, np.array(maxs_) - np.array(means)],
                    fmt="none", ecolor="k", elinewidth=.8, capsize=2)
    ax.set_xscale("log")
    ax.set_xticks(focals)
    ax.set_xticklabels([int(f) for f in focals])
    ax.set_xlabel("focal length (mm, 35mm-equivalent)")
    ax.set_ylabel("absolute vFoV error (degrees)")
    ax.set_title("Rung A mean absolute vFoV error (whiskers: min-max, n=5 scenes)",
                 fontsize=10)
    ax.grid(alpha=.3, axis="y")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig3_rungA_error.png"), dpi=200)
    plt.close(fig)


def main():
    df = pd.read_csv(CSV)
    df["err_deg"] = df["est_vfov_deg"] - df["true_vfov_deg"]
    fig1_pipeline()
    fig2_vfov(df)
    fig3_error(df)
    n = len(df)
    mae_pos = df[df.protocol == "fixedpos"]["err_deg"].abs().mean()
    mae_frame = df[df.protocol == "fixedframe"]["err_deg"].abs().mean()
    print(f"figures written to {OUT} (n={n} frames)")
    print(f"  sanity: mean|err| fixedpos={mae_pos:.2f} deg, fixedframe={mae_frame:.2f} deg")


if __name__ == "__main__":
    main()
