"""
calibrate_rungA.py — run GeoCalib over the 70 rung A renders and tabulate error
against exact ground truth (an early look at instrument behavior before the
formal Phase 3 validation).

GeoCalib protocol per blueprint: seed 0, median of 3 stochastic passes.
Output: measurements/rungA_geocalib.csv  +  console summary per focal length.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import torch

REPO = Path(__file__).resolve().parent.parent
RUNGA = REPO / "raw" / "rungA"
OUT = REPO / "measurements" / "rungA_geocalib.csv"


def expose_vfov(camera, image):
    if hasattr(camera, "vfov"):
        v = camera.vfov
        try:
            v = v.item()
        except AttributeError:
            pass
        v = float(v)
        if v < 3.2:
            v = math.degrees(v)
        return v
    if hasattr(camera, "f") and hasattr(camera, "size"):
        f = camera.f
        try:
            f = f.mean().item()
        except AttributeError:
            f = float(f)
        h = float(image.shape[-2])
        return math.degrees(2 * math.atan(h / (2 * f)))
    return None


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def main():
    import geocalib
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = geocalib.GeoCalib(weights="pinhole").to(device)

    pngs = sorted(RUNGA.glob("rungA_*.png"))
    if not pngs:
        sys.exit(f"no renders found in {RUNGA}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, png in enumerate(pngs):
        meta = json.loads(png.with_suffix(".json").read_text())
        image = model.load_image(str(png)).to(device)
        vfovs = []
        for _ in range(3):
            torch.manual_seed(0)
            with torch.no_grad():
                result = model.calibrate(image)
            vfovs.append(expose_vfov(result["camera"], image))
        est = sorted(vfovs)[1]
        spread = max(vfovs) - min(vfovs)
        truth = meta["nominal_vfov_deg"]
        rows.append({
            "image": png.name, "scene": meta["scene"], "protocol": meta["protocol"],
            "focal_mm": meta["focal_length_mm"], "true_vfov_deg": truth,
            "est_vfov_deg": round(est, 3), "err_deg": round(est - truth, 3),
            "spread_deg": round(spread, 3),
        })
        print(f"[{i+1:2d}/{len(pngs)}] {png.name}: true {truth:6.2f}  est {est:6.2f}  "
              f"err {est-truth:+6.2f}  spread {spread:.2f}")

    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("\n=== summary by focal length (pooled protocols) ===")
    for f in sorted({r["focal_mm"] for r in rows}):
        sub = [r for r in rows if r["focal_mm"] == f]
        mae = sum(abs(r["err_deg"]) for r in sub) / len(sub)
        bias = sum(r["err_deg"] for r in sub) / len(sub)
        print(f"  {f:3d}mm: n={len(sub)}  MAE={mae:5.2f} deg  bias={bias:+5.2f} deg")
    true_all = [r["true_vfov_deg"] for r in rows]
    est_all = [r["est_vfov_deg"] for r in rows]
    print(f"\nSpearman(true, est) over all {len(rows)}: {spearman(true_all, est_all):.4f}")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
