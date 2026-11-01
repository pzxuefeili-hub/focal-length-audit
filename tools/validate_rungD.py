"""Validate the locked 128-image rung D generation batch without running instruments."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "raw" / "rungD"
SUFFIXES = {".jpg", ".jpeg", ".png"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    sources_b = sorted(p for p in (ROOT / "raw" / "rungB").rglob("*")
                       if p.is_file() and p.suffix.lower() in SUFFIXES)
    sources_c = sorted(p for p in (ROOT / "raw" / "rungC").glob("*.png")
                       if not p.name.startswith("_check_"))
    assert (len(sources_b), len(sources_c)) == (80, 48), "Source counts changed"
    jobs = [("B", p) for p in sources_b] + [("C", p) for p in sources_c]

    expected = {f"rung{rung}__{source.stem}" for rung, source in jobs}
    actual_png = {p.stem for p in OUT.glob("*.png")}
    actual_json = {p.stem for p in OUT.glob("*.json")}
    assert actual_png == expected, f"PNG set mismatch: {sorted(expected ^ actual_png)}"
    assert actual_json == expected, f"JSON set mismatch: {sorted(expected ^ actual_json)}"

    output_hashes = {}
    for rung, source in jobs:
        stem = f"rung{rung}__{source.stem}"
        png_path = OUT / f"{stem}.png"
        sidecar_path = OUT / f"{stem}.json"
        with Image.open(png_path) as image:
            image.load()
            assert image.size == (1024, 1024), f"Bad size: {png_path.name}"
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        assert sidecar["rung"] == "D" and sidecar["source_rung"] == rung
        assert sidecar["source_file"] == str(source)
        assert sidecar["source_sha256"] == sha256(source), f"Source hash: {stem}"
        assert sidecar["output_sha256"] == sha256(png_path), f"Output hash: {stem}"
        assert sidecar["model"] == "stabilityai/stable-diffusion-xl-base-1.0"
        assert sidecar["requested_revision"] == sidecar["resolved_revision"] == "4621659"
        assert sidecar["pipeline"] == "SDXL img2img"
        assert sidecar["prompt"] == "a photograph" and sidecar["negative_prompt"] is None
        assert sidecar["strength"] == 0.3 and sidecar["num_inference_steps"] == 30
        assert sidecar["guidance_scale"] == 7.0 and sidecar["seed"] == 0
        assert sidecar["generator_device"] == "cpu" and sidecar["precision"] == "fp16"
        assert sidecar["output_size"] == [1024, 1024]
        assert "4060" in sidecar["gpu"], f"Unexpected GPU: {sidecar['gpu']}"
        assert sidecar["instrument_run"] is False
        output_hashes[png_path.name] = sidecar["output_sha256"]

    with (OUT / "rungD_manifest.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 128, f"Manifest rows: {len(rows)}"
    assert {row["file"] for row in rows} == set(output_hashes)
    for row in rows:
        assert row["output_sha256"] == output_hashes[row["file"]], f"Manifest hash: {row['file']}"
        assert row["seed"] == "0" and row["strength"] == "0.3"

    # A lightweight visual-QC contact sheet, kept outside the locked output folder.
    selected = jobs[::8]
    sheet = Image.new("RGB", (1000, 1080), "white")
    draw = ImageDraw.Draw(sheet)
    for tile, (rung, source) in enumerate(selected):
        index = tile * 8
        stem = f"rung{rung}__{source.stem}"
        with Image.open(OUT / f"{stem}.png") as image:
            thumb = image.convert("RGB")
            thumb.thumbnail((240, 240))
            x, y = (tile % 4) * 250, (tile // 4) * 270
            sheet.paste(thumb, (x + 5, y + 25))
            draw.text((x + 8, y + 7), f"{index + 1:03d} / rung {rung}", fill="black")
    sheet.save(ROOT / "raw" / "rungD-qc-contact.jpg", quality=88)
    print("RUNG D VALIDATION PASSED: 128/128 (80 B + 48 C)")
    print("All images open at 1024x1024; sidecars, parameters, source/output hashes, and manifest agree.")
    print("No measurement instrument was run. Contact sheet: raw/rungD-qc-contact.jpg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
