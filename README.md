# Do Text-to-Image Models Understand Focal Length?

**A physics-grounded measurement protocol for auditing focal-length prompt adherence in text-to-image diffusion models.**

> Pre-registered measurement study: do models obey "24mm" as a physical instruction,
> or merely as a style keyword? We build and validate a measurement instrument
> (single-image geometric calibration), then quantify adherence with a
> pre-committed compliance slope β across three prompt-register families
> (numeric / descriptive / genre) and three text-encoder families (CLIP / CLIP+T5 / T5).

## Status

| Phase | Content | Status |
|---|---|---|
| Phase 1 | Repo, frozen protocol, Zenodo DOI, smoke tests | 🚧 in progress |
| Phase 2 | Scene acquisition (Blender render + 80 reference photographs) | pending |
| Phase 3 | **Instrument validation (4-rung ladder) — the gate** | pending |
| Phase 4 | Pilot run (80 images) | pending |
| Phase 5 | Core scan (1,280+ images) | pending |
| Phase 8 | Human blind rating (280 pairs, 2 raters) | pending |
| Phase 11 | Report, slides, public release | pending |

## The one-figure summary

*(added after Phase 5 — same prompt, requested focal length 24mm vs 200mm,
side by side, with the measured vertical field of view under each image)*

## Repository layout

```
focal-length-audit/
├── raw/                  # Ground-truth reference photographs (EXIF-verified)
│   ├── rungB/            #   80 multi-focal-length real photographs (Protocol A/B)
│   ├── rungC/            #   40 scripted center-crops from the 24mm frame
│   ├── rungD/            #   120 img2img perturbations (strength 0.3)
│   └── aerial/           #   24 drone frames at known gimbal pitches (stretch)
├── generated/            # AI-generated images + sidecar metadata JSON
├── measurements/         # Tidy measurement tables (one row per image)
├── analysis/
│   ├── figures/          # Publication figures (Figure 1–7)
│   └── tables/           # Statistical tables (Table 3–5)
├── prompts/              # Frozen prompt suites (three registers)
├── scripts/              # Generation / calibration / analysis pipelines
├── docs/
│   ├── protocol.md       # Pre-registered protocol (frozen, DOI on Zenodo)
│   └── AI_USAGE_LOG.md   # Required log of AI assistance
├── requirements.txt
└── README.md
```

## Quick start (smoke test)

Phase 1 exit gate: generates one image per generator with the frozen configurations
(SDXL 30 steps / guidance 7.0 · SD3.5 40 / 4.5 · FLUX.1-schnell 4 / 0.0),
then calibrates each with GeoCalib (three passes, median vFoV).
Device-adaptive (CUDA / Apple MPS / CPU). First run downloads ~45GB of weights.

```bash
pip install -r requirements.txt
python scripts/smoke_test.py
```

## Hardware

- NVIDIA RTX 4060 (8GB) — SDXL generation + measurement pipeline
- Apple M4 Pro — FLUX.1-schnell + SD3.5 generation + Blender rendering
- UNT Talon cluster (NVIDIA A100 40GB, optional accelerator)
- Reference photographs: *<camera body + lens — fill in on arrival, full-frame vs APS-C affects EXIF conversion>*
- Aerial references (stretch): DJI Mini 2 (24mm-equivalent, 83° FoV, gimbal −90°~0°)

## Reproducibility & registration

- Protocol frozen and archived with a citable DOI before any data was inspected (Zenodo + GitHub release).
- Every generated image carries a sidecar JSON: model, prompt id, register, focal length, seed, sampler, steps, guidance, precision, GPU type.
- Decision rules (adherence slope β, equivalence bands, instrument pass thresholds) were committed **before** results were seen. Any post-hoc change is reported explicitly as a deviation with its reason.

## License

- Code: MIT (or Apache-2.0, decide at release)
- Reference photographs: CC BY 4.0
- Generated images: accompanied by the respective model license notes (SDXL — Stability AI Community License terms; FLUX.1-schnell — Apache-2.0; SD3.5 — Stability Community License). Model weights are **not** redistributed; download from Hugging Face under their own terms.
