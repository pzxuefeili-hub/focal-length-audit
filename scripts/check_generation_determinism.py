"""Whole-chain determinism check requested in the 2026-10-30 instructor addendum.

Generate the same prompt twice with the same frozen SDXL configuration and a
fresh CPU generator seeded to 0 for each run. Compare SHA-256 of the PNG bytes.
No calibration instrument is run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import diffusers
import torch

ROOT = Path(__file__).resolve().parents[1]
PROMPT = (
    "An empty concrete parking garage with painted lines, with an orange traffic cone "
    "in the foreground and an identical orange traffic cone farther back, "
    "photographed with a 50mm lens"
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "determinism")
    parser.add_argument("--model", default="stabilityai/stable-diffusion-xl-base-1.0")
    parser.add_argument("--revision", default="4621659")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU required; run this check on the assigned Talon node.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True

    pipe = diffusers.AutoPipelineForText2Image.from_pretrained(
        args.model,
        revision=args.revision,
        torch_dtype=torch.float16,
        variant="fp16",
        use_safetensors=True,
    ).to("cuda")
    pipe.enable_attention_slicing()
    pipe.enable_vae_slicing()

    hashes = []
    paths = []
    for run in (1, 2):
        generator = torch.Generator(device="cpu").manual_seed(args.seed)
        image = pipe(
            prompt=PROMPT,
            num_inference_steps=30,
            guidance_scale=7.0,
            generator=generator,
        ).images[0]
        path = args.output_dir / f"sdxl_seed{args.seed}_run{run}.png"
        image.save(path)
        paths.append(str(path))
        hashes.append(file_sha256(path))
        print(f"run {run}: {path.name} sha256={hashes[-1]}")

    passed = hashes[0] == hashes[1]
    report = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "test": "same prompt + same seed, two complete generations",
        "passed": passed,
        "model": args.model,
        "requested_revision": args.revision,
        "resolved_revision": getattr(pipe, "_commit_hash", None) or args.revision,
        "prompt": PROMPT,
        "seed": args.seed,
        "generator_device": "cpu",
        "steps": 30,
        "guidance_scale": 7.0,
        "precision": "fp16",
        "gpu": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "diffusers": diffusers.__version__,
        "files": paths,
        "sha256": hashes,
        "note": "Generation-chain determinism only; separate from GeoCalib three-pass repeatability.",
    }
    report_path = args.output_dir / "determinism_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"DETERMINISM CHECK {'PASSED' if passed else 'FAILED'}; report: {report_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
