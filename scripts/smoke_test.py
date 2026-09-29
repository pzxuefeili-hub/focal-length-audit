"""
Smoke test — Phase 1 exit gate (per blueprint: "Run a smoke test that generates
one image per model and calibrates it").

Generates ONE image with each of the three frozen-config generators and runs
GeoCalib on each output:
  1. SDXL base 1.0      — 30 steps, guidance 7.0, fp16,  default scheduler
  2. SD3.5 Medium       — 40 steps, guidance 4.5, bf16
  3. FLUX.1-schnell     —  4 steps, guidance 0.0, bf16, max_sequence_length 256

Run:  python scripts/smoke_test.py
First run downloads ~45GB of weights — start it before you go to sleep.

Device-adaptive: CUDA (RTX 4060) / MPS (Apple M4) / CPU (very slow, still valid).
Each image gets a sidecar JSON recording model, config, GPU, and precision —
the same metadata discipline required for all 5,888 study images.
"""

from __future__ import annotations

import json
import math
import platform
import sys
import time
from pathlib import Path

import torch

OUT_DIR = Path(__file__).resolve().parent.parent / "generated" / "smoke"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SMOKE_SCENE = (
    "A city sidewalk lined with brick buildings, with a red fire hydrant in the "
    "foreground and an identical red fire hydrant farther down the sidewalk"
)
NUMERIC_CLAUSE = ", photographed with a 50mm lens"
PROMPT = SMOKE_SCENE + NUMERIC_CLAUSE
SEED = 0  # study seeds are the integers 0–7; smoke uses 0


def detect_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def device_name() -> str:
    if torch.cuda.is_available():
        p = torch.cuda.get_device_properties(0)
        return f"{torch.cuda.get_device_name(0)} ({p.total_memory / 1e9:.1f} GB)"
    if torch.backends.mps.is_available():
        return "Apple Silicon (MPS)"
    return "CPU"


def release_memory() -> None:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def move(pipe, device: str):
    """CPU-offload on CUDA; plain .to() on MPS/CPU. Don't do both — offload
    manages device placement itself and double-moving wastes 8GB-VRAM headroom."""
    if device == "cuda":
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)
    return pipe


def gen_sdxl(device: str) -> Path:
    from diffusers import StableDiffusionXLPipeline

    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16,
        use_safetensors=True,
    )
    pipe = move(pipe, device)
    generator = torch.Generator(device="cpu").manual_seed(SEED)  # blueprint: CPU generator
    t0 = time.time()
    image = pipe(PROMPT, generator=generator, num_inference_steps=30,
                 guidance_scale=7.0).images[0]
    return save_result(image, "sdxl", device, time.time() - t0,
                       steps=30, guidance=7.0, precision="float16")


def gen_sd35(device: str) -> Path:
    from diffusers import StableDiffusion3Pipeline

    pipe = StableDiffusion3Pipeline.from_pretrained(
        "stabilityai/stable-diffusion-3.5-medium",
        torch_dtype=torch.bfloat16,
    )
    pipe = move(pipe, device)
    generator = torch.Generator(device="cpu").manual_seed(SEED)
    t0 = time.time()
    image = pipe(PROMPT, generator=generator, num_inference_steps=40,
                 guidance_scale=4.5).images[0]
    return save_result(image, "sd35-medium", device, time.time() - t0,
                       steps=40, guidance=4.5, precision="bfloat16")


def gen_flux(device: str) -> Path | None:
    try:
        from diffusers import FluxPipeline
    except ImportError:
        print("      diffusers too old for FluxPipeline — skipping FLUX (fix at pilot).")
        return None
    pipe = FluxPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-schnell",
        torch_dtype=torch.bfloat16,
    )
    pipe = move(pipe, device)
    generator = torch.Generator(device="cpu").manual_seed(SEED)
    t0 = time.time()
    image = pipe(PROMPT, generator=generator, num_inference_steps=4,
                 guidance_scale=0.0, max_sequence_length=256).images[0]
    return save_result(image, "flux1-schnell", device, time.time() - t0,
                       steps=4, guidance=0.0, precision="bfloat16")


def save_result(image, model_tag: str, device: str, dt: float,
                steps: int, guidance: float, precision: str) -> Path:
    img_path = OUT_DIR / f"smoke_{model_tag}_seed{SEED}.png"
    image.save(img_path)
    sidecar = {
        "model": model_tag,
        "prompt": PROMPT,
        "seed": SEED,
        "steps": steps,
        "guidance": guidance,
        "precision": precision,
        "device": device,
        "gpu_type": device_name(),
        "os": platform.platform(),
        "inference_seconds": round(dt, 2),
    }
    (OUT_DIR / f"{img_path.stem}.json").write_text(
        json.dumps(sidecar, indent=2, ensure_ascii=False))
    print(f"      -> {img_path.name}  ({dt:.1f}s)")
    return img_path


def expose_vfov(camera, image) -> float | None:
    """Best-effort vFoV (degrees) extraction across GeoCalib versions."""
    if hasattr(camera, "vfov"):
        v = camera.vfov
        try:
            v = v.item()
        except AttributeError:
            pass
        v = float(v)
        if v < 3.2:  # radians → degrees
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


def calibrate(img_path: Path) -> None:
    try:
        import geocalib
    except ImportError:
        sys.exit("geocalib is not installed — install from the official ECCV 2024 repo:\n"
                 "  pip install git+https://github.com/cvg/GeoCalib#egg=geocalib")

    device = detect_device()
    model = geocalib.GeoCalib(weights="pinhole").to(device)
    image = model.load_image(str(img_path)).to(device)

    # Blueprint: GeoCalib's decoder is stochastic — fix seed 0, median of 3 passes.
    vfovs = []
    for _ in range(3):
        torch.manual_seed(0)
        with torch.no_grad():
            result = model.calibrate(image)
        v = expose_vfov(result["camera"], image)
        if v is None:
            sys.exit("Could not read vFoV from GeoCalib's camera object — "
                     "print result['camera'] and check the attribute name once.")
        vfovs.append(v)
    vfov = sorted(vfovs)[1]
    spread = max(vfovs) - min(vfovs)
    print(f"      vFoV median = {vfov:.2f}°  (3-pass spread {spread:.2f}°)  "
          f"[50mm full-frame expects ≈ 27.0°]")


def main() -> None:
    device = detect_device()
    print(f"Device: {device_name()}\n")

    jobs = [("SDXL base 1.0", gen_sdxl),
            ("SD3.5 Medium", gen_sd35),
            ("FLUX.1-schnell", gen_flux)]
    results = {}
    for name, fn in jobs:
        print(f"[gen] {name}")
        try:
            path = fn(device)
            if path is not None:
                results[name] = path
        except Exception as e:  # noqa: BLE001 — a failed model must not kill the smoke test
            print(f"      FAILED: {type(e).__name__}: {e}")
        release_memory()

    if not results:
        sys.exit("No model generated anything — fix errors above before proceeding.")

    print()
    for name, path in results.items():
        print(f"[calib] {name}")
        calibrate(path)

    print("\nSMOKE TEST PASSED (for every model that generated).")
    print("Phase 1 exit gate also requires: protocol DOI resolves + instructor "
          "sign-off. Record results in docs/protocol.md §Phase-1 record.")


if __name__ == "__main__":
    main()
