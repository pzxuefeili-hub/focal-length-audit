# Gap Note — the precise gap this project fills

*Phase 1 deliverable. Synthesis of the 8-paper essential reading shortlist (blueprint §"Essential reading"). One page.*

## Three lines of prior work, and where each stops

**Line 1 — Control: making models obey camera parameters by adding machinery.**
Yuan et al. (*Generative Photography*, CVPR 2025) show off-the-shelf generators cannot produce scene-consistent changes of field of view from focal-length requests, and solve it with dimensionality lifting and differential camera-intrinsics learning on SD 1.5. Fang et al. (*Camera Settings as Tokens*, SIGGRAPH Asia 2024) first diagnose the mechanism — CLIP/OpenCLIP near chance at discriminating numerical camera settings in text — and then fix it with LoRA-embedded camera tokens trained on their CameraSettings20k dataset. Bernal-Berdun et al. (*PreciseCam*, CVPR 2025) control roll/pitch/vFoV/distortion through ControlNet conditioning on SDXL, explicitly surpassing prompt engineering as a baseline. **All three share the same shape: they establish that plain prompting fails, then build a remedy. None stops to measure *how* it fails** — how far off the requested focal length the plain model actually lands, across registers, models, and encoder families.

**Line 2 — Measurement: geometric instruments now exist and are trusted.**
Veicht et al. (*GeoCalib*, CVPR 2024) recast single-image intrinsics estimation as geometric optimization with usable uncertainty. Zhu et al. (*Tame a Wild Camera*, NeurIPS 2023) calibrate 4-DoF intrinsics zero-shot from monocular priors (Apache-2.0 — cleared for this project). Wang/Xu et al. (*GenSpace*, NeurIPS 2025 D&B) demonstrate the credibility template: a pipeline of geometric foundation models (including WildCamera) judged against 900 human labels, agreeing with humans 76% where the best VLM reaches 56%. **But GenSpace benchmarks spatial awareness broadly; no instrument application isolates focal-length language adherence as the quantity of interest.**

**Line 3 — Language: why prompts might fail, and how wording is studied.**
Paiss et al. (*Teaching CLIP to Count to Ten*, ICCV 2023) show numerals are compositional blind spots in CLIP's text space — the natural mechanism hypothesis for focal-length wording, directly inherited by CLIP-encoder models (SDXL). Liu & Chilton (*Design Guidelines for Prompt Engineering T2I Models*, CHI 2022) study prompt wording as a *stylistic* variable for getting desirable images, founding the register tradition: numeric ("24mm"), descriptive ("wide-angle"), genre ("street photography") are different ways users phrase intent — but registers have never been compared as *physical instructions*.

## The gap

**No work quantifies — with a geometrically validated instrument — how faithfully off-the-shelf, unfine-tuned text-to-image models (SDXL / SD3.5 / FLUX.1, spanning CLIP, CLIP+T5, and T5 encoder families) obey numeric, descriptive, and genre focal-length wording.** Prior control work treats prompt failure as motivation; prior measurement work never points the instrument at the language; prior language work never grounds wording in measured geometry. This project occupies the empty intersection: build the ruler (a calibration instrument validated on ground-truth scenes at known focal lengths, rungs A–D), then measure the pre-registered compliance slope β of each register on each model. β ≈ −1 means the model obeys like a lens; β ≈ 0 means the number is decoration.

## References

1. Yuan, Wang, Sheng, Chennuri, Zhang, Chan. *Generative Photography: Scene-Consistent Camera Control for Realistic Text-to-Image Synthesis.* CVPR 2025.
2. Fang, Han, Chen. *Camera Settings as Tokens: Modeling Photography on Latent Diffusion Models.* SIGGRAPH Asia 2024.
3. Bernal-Berdun, Serrano, Masia, Gadelha, Hold-Geoffroy, Sun, Gutierrez. *PreciseCam: Precise Camera Control for Text-to-Image Generation.* CVPR 2025.
4. Veicht, Sarlin, Lindenberger, Pollefeys, Larsson. *GeoCalib: Learning Single-Image Calibration with Geometric Optimization.* CVPR 2024.
5. Zhu, Kumar, Hu, Liu. *Tame a Wild Camera: In-the-Wild Monocular Camera Calibration.* NeurIPS 2023.
6. Xu, Zhang, Pang, Du, Zhao, Zhao et al. *GenSpace: Benchmarking Spatially-Aware Image Generation.* NeurIPS 2025 (Datasets & Benchmarks). *(Blueprint listed this as "Wang et al."; first author is Xu.)*
7. Paiss, Ephrat, Tov, Zada, Mosseri, Irani, Dekel. *Teaching CLIP to Count to Ten.* ICCV 2023.
8. Liu, Chilton. *Design Guidelines for Prompt Engineering Text-to-Image Generative Models.* CHI 2022.
