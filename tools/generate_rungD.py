"""Generate rung D with SDXL img2img (protocol section 7).

Rung D = 80 rung B photographs + 48 rung C center crops, transformed once
with prompt "a photograph", strength 0.3, at 1024 x 1024. Each output has a
JSON sidecar and every completed run rewrites rungD_manifest.csv.

This script only generates images. It does not run GeoCalib or any other
measurement instrument, so it does not bypass the protocol tag/DOI gate.

Examples (from the repository root):
  python tools/generate_rungD.py --dry-run
  python tools/generate_rungD.py --low-vram
  python tools/generate_rungD.py --low-vram --limit 2 --output-dir raw/rungD-smoke
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sources(rung_b_dir: Path, rung_c_dir: Path) -> list[dict]:
    rung_b = sorted(
        p for p in rung_b_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )
    rung_c = sorted(rung_c_dir.glob("*.png"))
    rung_c = [p for p in rung_c if not p.name.startswith("_check_")]

    records = []
    for rung, paths in (("B", rung_b), ("C", rung_c)):
        for path in paths:
            records.append({
                "rung": rung,
                "path": path,
                "output_stem": f"rung{rung}__{path.stem}",
            })
    return records


def square_1024(image, already_square: bool):
    """Center-square crop, then Lanczos resize; record the exact geometry."""
    from PIL import Image

    image = image.convert("RGB")
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    box = (left, top, left + side, top + side)
    if (width, height) != (side, side):
        image = image.crop(box)
    if image.size != (1024, 1024):
        image = image.resize((1024, 1024), Image.Resampling.LANCZOS)
    return image, {
        "source_size": [width, height],
        "center_crop_box_xyxy": list(box),
        "resize": "Lanczos to 1024x1024" if (width, height) != (1024, 1024) else "none",
        "already_square_rung_c": already_square,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rung-b-dir", type=Path, default=ROOT / "raw" / "rungB")
    parser.add_argument("--rung-c-dir", type=Path, default=ROOT / "raw" / "rungC")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "raw" / "rungD")
    parser.add_argument("--model", default="stabilityai/stable-diffusion-xl-base-1.0")
    parser.add_argument("--revision", default="4621659", help="Frozen SDXL repo revision")
    parser.add_argument("--seed", type=int, default=0, choices=range(8), metavar="0..7")
    parser.add_argument("--strength", type=float, default=0.3)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--guidance", type=float, default=7.0)
    parser.add_argument("--low-vram", action="store_true", help="Use model CPU offload (recommended for 8GB)")
    parser.add_argument("--limit", type=int, default=None, help="Generate only the first N sources (testing)")
    parser.add_argument("--allow-partial", action="store_true", help="Permit counts other than 80 B + 48 C")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate outputs that already exist")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and exit without loading SDXL")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.strength != 0.3 or args.steps != 30 or args.guidance != 7.0:
        print("WARNING: values differ from the frozen rung D / SDXL configuration.", file=sys.stderr)

    jobs = sources(args.rung_b_dir.resolve(), args.rung_c_dir.resolve())
    count_b = sum(job["rung"] == "B" for job in jobs)
    count_c = sum(job["rung"] == "C" for job in jobs)
    print(f"Discovered: rung B={count_b}, rung C={count_c}, total={len(jobs)}")
    if not args.allow_partial and (count_b, count_c) != (80, 48):
        raise SystemExit(
            "Input check failed: expected exactly 80 rung B images and 48 rung C crops. "
            "Use --dry-run after fixing the folders; --allow-partial is for tests only."
        )
    output_stems = [job["output_stem"] for job in jobs]
    if len(output_stems) != len(set(output_stems)):
        raise SystemExit("Input check failed: duplicate output names; rename duplicate source files.")
    if args.limit is not None:
        if args.limit < 1:
            raise SystemExit("--limit must be positive")
        jobs = jobs[: args.limit]
    if args.dry_run:
        for job in jobs[:5]:
            print(f"  {job['rung']}: {job['path']} -> {job['output_stem']}.png")
        if len(jobs) > 5:
            print(f"  ... and {len(jobs) - 5} more")
        print(f"DRY RUN OK: {len(jobs)} generation jobs; no model loaded, no image written.")
        return 0

    import diffusers
    import torch
    from PIL import Image

    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU not found. CPU generation is intentionally not used for this frozen pipeline.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda")
    dtype = torch.float16
    pipe = diffusers.AutoPipelineForImage2Image.from_pretrained(
        args.model,
        revision=args.revision,
        torch_dtype=dtype,
        variant="fp16",
        use_safetensors=True,
    )
    pipe.enable_attention_slicing()
    pipe.enable_vae_slicing()
    if args.low_vram:
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)
    pipe.set_progress_bar_config(desc="rung D")

    gpu_name = torch.cuda.get_device_name(0)
    resolved_revision = getattr(pipe, "_commit_hash", None) or args.revision
    manifest_rows = []
    completed = 0

    for index, job in enumerate(jobs, start=1):
        source_path = job["path"]
        png_path = args.output_dir / f"{job['output_stem']}.png"
        json_path = args.output_dir / f"{job['output_stem']}.json"
        if png_path.exists() and json_path.exists() and not args.overwrite:
            print(f"[{index}/{len(jobs)}] skip existing {png_path.name}")
            completed += 1
        else:
            with Image.open(source_path) as source_image:
                init_image, preprocessing = square_1024(source_image, job["rung"] == "C")
            # A CPU generator keeps initial noise independent of the CUDA device.
            generator = torch.Generator(device="cpu").manual_seed(args.seed)
            result = pipe(
                prompt="a photograph",
                image=init_image,
                strength=args.strength,
                num_inference_steps=args.steps,
                guidance_scale=args.guidance,
                generator=generator,
            ).images[0]
            if result.size != (1024, 1024):
                raise RuntimeError(f"Unexpected output size {result.size} for {source_path}")
            result.save(png_path)
            sidecar = {
                "rung": "D",
                "source_rung": job["rung"],
                "source_file": str(source_path),
                "source_sha256": sha256(source_path),
                "output_file": png_path.name,
                "output_sha256": sha256(png_path),
                "model": args.model,
                "requested_revision": args.revision,
                "resolved_revision": resolved_revision,
                "pipeline": "SDXL img2img",
                "prompt": "a photograph",
                "negative_prompt": None,
                "strength": args.strength,
                "num_inference_steps": args.steps,
                "guidance_scale": args.guidance,
                "seed": args.seed,
                "generator_device": "cpu",
                "output_size": [1024, 1024],
                "precision": "fp16",
                "low_vram_cpu_offload": args.low_vram,
                "gpu": gpu_name,
                "torch": torch.__version__,
                "diffusers": diffusers.__version__,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "preprocessing": preprocessing,
                "instrument_run": False,
            }
            json_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")
            completed += 1
            print(f"[{index}/{len(jobs)}] wrote {png_path.name}")

        manifest_rows.append({
            "file": png_path.name,
            "source_rung": job["rung"],
            "source_file": str(source_path),
            "source_sha256": sha256(source_path),
            "output_sha256": sha256(png_path),
            "seed": args.seed,
            "strength": args.strength,
        })

    manifest_path = args.output_dir / "rungD_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"DONE: {completed} outputs present; manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
