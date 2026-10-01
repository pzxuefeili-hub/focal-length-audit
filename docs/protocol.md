# Pre-Registered Protocol

## Does the Number Matter? Measuring Whether Text-to-Image Models Treat Focal-Length Language as Physics or as Style

> **STATUS: DRAFT v2 — cross-checked against the instructor's blueprint on 2026-09-29.**
> Freeze procedure: final read-through → commit to GitHub → tag release → Zenodo
> mints DOI → instructor sign-off. After freezing, no silent changes: every
> deviation is reported with its reason and timestamp, and the original
> analysis is still reported alongside.

- Investigator: Tianbo (Max) Zhang — sole investigator
- Supervising instructor: Prof. Mohammed Aledhari
- Project type: computational evaluation study (measurement audit)
- Registration date: _<fill in on freeze>_
- Zenodo DOI: _<fill in>_

---

## 1. Outcome definitions (read this first)

All focal lengths are **35mm-equivalent**.

- Primary outcome: **y = ln(tan(vFoV / 2))**, where vFoV is the estimated vertical field of view.
- Predictor: **x = ln(requested focal length)**.
- Pinhole physics: tan(vFoV/2) = h / (2f), with sensor height h = 24mm under the 35mm-equivalent convention.
  Logging gives a straight line of slope exactly **−1**.
- **Adherence slope β**: slope −1 = the model behaves like a real lens; slope 0 = the number is ignored.
  The slope is invariant to the sensor-size convention (a convention change only shifts the intercept) — this is why β is the robust primary outcome.
- Compression outcome (RQ3): with two identical objects near/far in every ground scene,
  s = (near object image height) / (far object image height); **c = ln(s − 1)**.
  Fixed framing ⇒ slope of c vs ln(focal) = −1; fixed position ⇒ slope = 0.
- Aerial outcome (RQ4): pitch angle estimated by the calibrator; target slope of measured vs requested pitch = +1.

## 2. Research questions, hypotheses, and pre-committed decision rules

### RQ1 (primary). Does numeric focal-length phrasing change measured FoV, and how close to the pinhole prediction?

- **H0:** β (numeric) is practically zero. Smallest effect of interest |β| = 0.15 — "practically zero" means the **90% CI lies entirely inside [−0.15, +0.15]**.
- **H1:** β (numeric) is negative and outside that band.
- **Physical fidelity criterion:** 90% CI of β inside **[−1.15, −0.85]**.
- **Test:** equivalence test (two one-sided tests, α = 0.05) against the ±0.15 band; plus cluster-bootstrap **95% CI** of β per model.
- Falsifies H1: CI inside ±0.15. Falsifies physical fidelity: CI excluding [−1.15, −0.85].

### RQ2 (primary contribution). Register × encoder interaction

- **H0:** register-by-slope interaction is zero for every model.
- **H1:** descriptive slope is more negative than numeric by ≥ 0.20 (smallest effect of interest) in at least one model.
- **Test:** contrasts "descriptive − numeric" and "genre − numeric" per model; cluster-bootstrap CIs; **Holm correction across all six contrasts** (2 registers × 3 models).
- Falsifies H1: every Holm-adjusted "descriptive − numeric" CI includes values smaller in magnitude than 0.20.
- Equal adherence across registers is itself an informative finding.

### RQ3 (secondary). Which physical interpretation do models follow?

- Estimate compression slope per model × register with cluster-bootstrap CIs; classify each model by which physical target its interval includes.
- Confirmatory for slope direction; exploratory for the classification.

### RQ4 (secondary, aerial). Pitch adherence + register pattern at fixed oblique pitch

- Mixed-effects model analogous to RQ1; register contrasts for aerial focal length at fixed oblique pitch.
- Confirmatory for pitch slope; exploratory for aerial-vs-ground comparison.

### RQ5 (exploratory). Mechanism probe

- Ridge decoding of ln(focal) from text embeddings, leave-one-scene-out CV R².
- Spearman between embedding cosine distance and |Δln(focal)| across prompt pairs per scene.
- Exploratory only: describe alignment between representation and behavior; no statistical association claim across three generators.

### Success decision rules (verbatim commitment)

1. Numeric 90% CI inside ±0.15 → report "model ignores numeric focal length".
2. 90% CI inside [−1.15, −0.85] → report "physically faithful adherence".
3. Any other interval → report partial adherence with its estimate.
4. A register effect is claimed only when a Holm-adjusted contrast CI excludes zero AND the point estimate is ≥ 0.20 in magnitude.
5. A compression interpretation is assigned only when the compression-slope interval includes exactly one of the two physical targets.

## 3. Generators and frozen generation configuration

| Generator | Role | Scheduler | Steps | Guidance | Resolution | Precision | Notes |
|---|---|---|---|---|---|---|---|
| SDXL base 1.0 | CLIP-only | pipeline default | 30 | 7.0 | 1024×1024 | fp16 | no negative prompt; also provides img2img for rung D |
| SD3.5 Medium | CLIP + T5-XXL (×2 CLIP + T5) | pipeline default | 40 | 4.5 | 1024×1024 | bf16 | gated download — accept terms in Phase 1 |
| FLUX.1-schnell | T5-dominant (CLIP pooled only) | — | 4 | 0.0 | 1024×1024 | bf16 | distilled, no CFG; **excluded from guidance ablation**; max sequence length 256 |

- **Seeds:** integers 0–7. Noise from a **CPU torch.Generator** seeded per blueprint, so starting noise is identical across GPUs.
- Square output (vFoV = hFoV) simplifies the instrument.
- **Sidecar per image:** model repo name, commit hash, library versions, GPU type, precision, prompt id, register, level, seed.

## 4. Scenes (verbatim, frozen)

Eight ground scenes (two identical objects at different depths, no people):
1. "A city sidewalk lined with brick buildings, with a red fire hydrant in the foreground and an identical red fire hydrant farther down the sidewalk"
2. "An empty train platform with a long yellow safety line, with a yellow bench in the foreground and an identical yellow bench farther along the platform"
3. "A quiet library aisle between tall bookshelves, with a wooden chair in the foreground and an identical wooden chair farther down the aisle"
4. "A straight park path lined with trees, with a green trash bin in the foreground and an identical green trash bin farther along the path"
5. "An empty concrete parking garage with painted lines, with an orange traffic cone in the foreground and an identical orange traffic cone farther back"
6. "A wooden beach boardwalk, with a white beach chair in the foreground and an identical white beach chair farther along the boardwalk"
7. "A long tiled museum hallway, with a marble pedestal in the foreground and an identical marble pedestal farther down the hallway"
8. "A straight country road with a wooden fence, with a white mailbox in the foreground and an identical white mailbox farther down the road"

Six aerial scenes: suburban neighborhood / farmland / parking lot / soccer field / river-bridge / marina — each suffixed "…, seen from a drone".

### Registers (camera clause appended to scene text)

**Focal levels (ground):** 16, 24, 50, 85, 200mm — nominal vFoV 73.7°, 53.1°, 27.0°, 16.1°, 6.9°.

- Numeric: ", photographed with a {16|24|50|85|200}mm lens" (an 85mm / an 200mm per grammar)
- Descriptive: "an ultra-wide-angle lens, dramatic stretched perspective" / "a wide-angle lens, expansive view with pronounced depth" / "a standard lens, natural perspective close to human vision" / "a short telephoto lens, gently compressed perspective" / "a long telephoto lens, strongly compressed flat perspective"
- Genre: "in the style of architectural photography" / "documentary street photography" / "a classic everyday snapshot" / "professional portrait photography" / "wildlife and sports photography"
- **Genre mapping is a stated hypothesis** (Table 1), treated as exploratory; genre phrases can change content → measured by semantic controls.
- **No-clause baseline:** scene text alone, every seed — shows each model's default FoV.

**Aerial:** pitch levels −90°/−60°/−45°/−30°; numeric clause ", camera pointing {N} degrees below the horizon"; descriptive "straight-down top-down view" / "steep high-angle aerial view" / "oblique aerial view" / "low oblique aerial view looking toward the horizon". Aerial focal arm: 24/50/85mm × fixed ", oblique aerial view". Altitude is out of scope.

## 5. Generation matrix

| Block | Models | Scenes | Registers | Levels | Seeds | Images |
|---|---|---|---|---|---|---|
| **Minimum complete: ground focal** | SDXL, FLUX.1-schnell | 8 | numeric, descriptive | 5 | 8 | **1,280** |
| Extension: ground remaining | SD3.5 all registers; genre for SDXL & FLUX | 8 | — | 5 | 8 | 1,600 |
| No-clause baseline | 3 | 8 | none | 1 | 8 | 192 |
| Aerial pitch | 3 | 6 | numeric, descriptive | 4 | 8 | 1,152 |
| Aerial focal (oblique) | 3 | 6 | numeric, descriptive | 3 | 8 | 864 |
| Prompt-position ablation | 3 | 4 (1,3,5,7) | numeric, descriptive | 5 | 4 (0–3) | 480 |
| Guidance ablation | SDXL 5.0/9.0; SD3.5 3.0/6.0 | 4 (1,3,5,7) | numeric | 5 | 4 (0–3) | 320 |
| **Total** | | | | | | **5,888** |

## 6. Measurement instrument

1. **FoV & pitch:** GeoCalib (pinhole weights, release v1.0) on every image; record vFoV, pitch, roll, and reported uncertainty. GeoCalib's decoder is stochastic: fix torch seed 0 before each call, run **three passes per image, record the median**; report run-to-run spread in supplement.
2. **y, c, pitch** computed per definitions in §1.
3. **Paired-object compression:** Grounding DINO **tiny** via transformers library; object phrase from scene text (e.g., "red fire hydrant"); keep two highest-scoring boxes, box threshold 0.35; s = height of lower box ÷ height of higher box (lower = nearer in ground scenes); c = ln(s−1) when s > 1; record <2 detections or s ≤ 1 as compression failures; report failure count per cell.
4. **Semantic control:** CLIPScore (CLIP ViT-L/14) between image and scene text **without** camera clause; published formula 2.5 × max(0, cosine).
5. **Scene-consistency control:** LPIPS (AlexNet) between image and the same model/scene/seed/register at the 50mm level.
6. **Exclusion rule:** exclude an image from slope estimation when its GeoCalib FoV uncertainty exceeds the **95th percentile of uncertainties observed on rung B** (threshold set in Phase 3). Report exclusion counts per cell; repeat every primary analysis with no exclusions as a sensitivity check.

## 7. Validation ladder (Phase 3 gate)

| Rung | Content | n | Ground truth |
|---|---|---|---|
| A | Blender renders, 5 scenes at 16/24/35/50/85/135/200mm, both protocols | 70 | exact |
| B | Real photos, 8 scenes at 24/35/50/70/105mm, both protocols (fixed-position & fixed-framing) | 80 | EXIF focal length |
| C | Center crops of fixed-position 24mm frames reproducing 35/50/70/105/200mm FoV (crop side = 24/f × original; resize to 1024²; shoot B at full resolution — 200mm crop keeps 12% of side). **Sensitivity check (added 2026-09-30 per instructor review):** a second 200mm-equivalent center crop taken from the **105mm frame** instead of the 24mm frame — at 105mm the crop keeps ~53% of the short side, so it is not resolution-starved. Both 200mm variants are pre-registered; primary analysis uses the 24mm-based crop, the 105mm-based crop is the sensitivity analysis. | 48 | exact |
| D | Rungs B+C through SDXL img2img, strength 0.3, prompt "a photograph" | 120 | inherited from source |
| Aerial | Drone photos at gimbal pitch −90/−60/−45/−30° over 6 sites | 24 | flight metadata |

**Instrument gate criteria (committed):**
- Spearman(true y, estimated y) ≥ 0.85 on **rungs B, C, and D**
- Estimated slope on rung D within **[−1.2, −0.8]**
- Median absolute vFoV error on rung D ≤ 1.5 × rung B error
- Compression: c-slope on fixed-framing half of rung B within [−1.3, −0.7]; on fixed-position half within [−0.3, +0.3]

**Switch triggers:** GeoCalib fails rung D while WildCamera passes → switch backbone. Neither passes but ensemble passes → use ensemble (report both components). No FoV instrument passes rung D → **instrument-audit design** (validation ladder + failure analysis becomes the main contribution — a publishable outcome, not a failure).

## 8. Statistical analysis (pre-committed)

- **Primary model:** linear mixed model, formula `y ~ x * register * model`, scene as grouping, random-effects `~x` (random intercept + slope per scene); seed = residual variation. statsmodels.
- **Uncertainty:** cluster bootstrap resampling **scenes with replacement, 2,000 resamples**; percentile 95% CIs (90% for equivalence tests).
- **RQ1:** TOST equivalence at α = 0.05 against ±0.15.
- **RQ2:** six register contrasts, Holm-corrected.
- **Permutation control:** shuffle focal-length labels within each scene+seed, 5,000 permutations, refit numeric slope, compare observed slope to null.
- **Secondary metrics:** compression slope, pitch slope, CorrCoef per scene (for comparability with Generative Photography), median absolute vFoV error vs nominal, CLIPScore/LPIPS controls, decoding R² / ordinal Spearman (RQ5).
- **Content-drift flag:** if a cell's CLIPScore median < 90% of that model+scene's no-clause baseline median → flag; report slopes with and without flagged cells.
- **Nadir case:** if aerial −90° fails Spearman → restrict aerial pitch analysis to the three oblique levels.

## 9. Human validation (Phase 8)

- Raters: investigator + **one** peer rater; independent judgments.
- 240 generated pairs (share model/scene/seed/register; focal gap ≥ 2 levels; stratified equally across models & registers) + 40 catch pairs from rung B real photos (known answers).
- Blinding: random file identifiers, randomized left/right, prompts hidden.
- Question: **"Which image looks like it was taken with the longer lens?"**
- Report: catch-pair accuracy per rater; **Krippendorff's α (nominal), computed with our own NumPy implementation and checked against a hand-worked example**; instrument-vs-rater-consensus concordance with bootstrap 95% CI (2,000 resamples of pairs); fraction of pairs where consensus matches requested order.
- Gate: both raters complete all 280 pairs; catch accuracy ≥ 85% per rater; sub-threshold → retrain with 10 examples, re-rate a fresh sample.
- Raw per-trial records never published nor pasted into AI tools; only aggregates.
- **Ethics:** confirm with instructor whether this rating task needs ethics review; record the answer (in writing) in this protocol before Phase 8.

## 10. Error analysis

Per model × register: sort by absolute residual from fitted slope; inspect top 20; assign each to one of five categories — (1) scene content changed, (2) no perspective cues, (3) calibration failure, (4) stylized/non-photographic rendering, (5) different geometric interpretation. Report category counts in supplement, one example image per category.

## 11. Ablations & sensitivity checks

Camera clause position (start vs end) · guidance scale (SDXL 5.0/9.0, SD3.5 3.0/6.0; FLUX excluded) · instrument backbone swap (GeoCalib vs WildCamera on every image) · with/without uncertainty exclusions · with/without content-drift-flagged cells · with/without nadir aerial level.

## 12. Phase gates (summary)

| Phase | Gate |
|---|---|
| 1 Foundations | one image + one calibration per model; protocol DOI resolves; instructor signs off |
| 2 Reference capture | all 334 reference images with complete ground-truth metadata; script check passes |
| 3 Instrument | GeoCalib, WildCamera, or ensemble meets every FoV criterion; compression criteria met on rung B |
| 4 Pilot | ≥90% usable calibrations; ≥80% two-detection on ground images; identical seeds reproduce identical images |
| 5 Core sweep | every cell ≥90% usable calibrations; analysis script runs end-to-end raw → Table 4 |
| 8 Human | both raters finish 280; catch ≥85% each |
| 11 Release | clean-environment reproduction matches Table 4 (deterministic exactly, resampled within bootstrap noise) |

## 13. Phase 1 checklist (this week)

- [ ] Read the 8-paper shortlist; write a one-page gap note
- [ ] Create GitHub repository (this layout + requirements + README)
- [ ] Accept SD3.5 Medium terms on Hugging Face
- [ ] Download all model weights; record commit hashes
- [x] Confirm WildCamera repository license file (Apache-2.0, verified 2026-09-30; main @ 7aae666)
- [ ] Finalize this protocol; release on GitHub → Zenodo DOI
- [ ] Run smoke test (one image + one calibration per model) — `scripts/smoke_test.py`
- [ ] Email instructor: protocol sign-off + ethics-review question + rater compensation + Talon access (CC major professor per instructor's instruction)

## 14. Phase-1 record

| Machine | Device | Model | Inference (s) | vFoV median (3-pass, °) | Spread (°) | Date |
|---|---|---|---|---|---|---|
| RTX 4060 Laptop (8GB) | cuda | SDXL | 25.9 | 39.78 | 0.00 | 2026-09-29 |
| RTX 4060 Laptop (8GB) | cuda | SD3.5 | OOM at inference (weights downloaded; model exceeds 8GB VRAM even with CPU offload — **fixed device: UNT Talon A100**, assigned 2026-09-30 per instructor review; no CUDA/MPS mixing per model) | — | — | 2026-09-29 |
| RTX 4060 Laptop (8GB) | cuda | FLUX | not run (16GB system RAM exhausted during download; **fixed device: UNT Talon A100**, assigned 2026-09-30 per instructor review) | — | — | 2026-09-29 |
| UNT Talon (A100 40GB) | cuda | SD3.5 | | | | |
| UNT Talon (A100 40GB) | cuda | FLUX | | | | |

Notes: SDXL smoke confirms the full chain (generation → GeoCalib ×3 median). Requested 50mm ⇒ nominal vFoV ≈ 27.0°; measured 39.78° shows the model's loose adherence — expected, and exactly what RQ1 will quantify. GeoCalib weights (pinhole) fetched from official v1.0 release. Hugging Face gated-repo access granted for SD3.5 Medium and FLUX.1-schnell on 2026-09-29.

Weight hashes (Hugging Face repo revisions at download, 2026-09-29):
- SDXL base 1.0: `4621659` · SD3.5 Medium: `b940f67` · FLUX.1-schnell: `741f7c3`
- GeoCalib pinhole weights: release v1.0 · WildCamera: commit 7aae666 (main, Apache-2.0 confirmed)
