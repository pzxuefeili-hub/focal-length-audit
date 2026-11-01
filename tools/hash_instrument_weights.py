"""Hash the four instrument-weight families required by the instructor addendum.

Searches common Hugging Face / torch caches and project directories for:
GeoCalib pinhole, WildCamera wild_camera_all.pth, Grounding DINO tiny, and
CLIP ViT-L/14. Writes standard sha256sum-compatible lines plus a JSON coverage
report. Missing families cause a nonzero exit instead of a false PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# GeoCalib v1.0 distributes its pinhole checkpoint as pinhole.tar.
WEIGHT_SUFFIXES = {".safetensors", ".pth", ".pt", ".bin", ".ckpt", ".tar"}
FAMILIES = {
    "geocalib_pinhole": lambda text, name: "geocalib" in text and "pinhole" in text,
    "wildcamera": lambda text, name: name == "wild_camera_all.pth",
    "grounding_dino_tiny": lambda text, name: (
        ("grounding-dino" in text or "groundingdino" in text) and "tiny" in text
    ),
    "clip_vit_l_14": lambda text, name: (
        "clip" in text and (
            "vit-l-14" in text or "vit-l--14" in text or "vit-large-patch14" in text
        )
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    home = Path.home()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots", nargs="*", type=Path,
        default=[home / ".cache" / "huggingface" / "hub", home / ".cache" / "torch", ROOT, home / "work"],
    )
    parser.add_argument("--output", type=Path, default=ROOT / "instrument_weight_hashes.txt")
    parser.add_argument("--report", type=Path, default=ROOT / "instrument_weight_hashes.json")
    args = parser.parse_args()

    candidates: dict[str, Path] = {}
    for root in args.roots:
        root = root.expanduser().resolve()
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in WEIGHT_SUFFIXES:
                continue
            text = str(path).lower().replace("_", "-")
            name = path.name.lower()
            if any(match(text, name) for match in FAMILIES.values()):
                # Keep the logical HF snapshot path for family detection; resolving
                # symlinks here would replace it with an opaque cache blob name.
                candidates[str(path)] = path.resolve()

    entries = []
    coverage = {family: [] for family in FAMILIES}
    for path_string in sorted(candidates):
        path = Path(path_string)
        text = path_string.lower().replace("_", "-")
        name = path.name.lower()
        families = [family for family, match in FAMILIES.items() if match(text, name)]
        digest = sha256(path)
        entries.append({"path": path_string, "sha256": digest, "bytes": path.stat().st_size, "families": families})
        for family in families:
            coverage[family].append(path_string)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries), encoding="utf-8"
    )
    missing = [family for family, paths in coverage.items() if not paths]
    report = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "roots": [str(path.expanduser()) for path in args.roots],
        "entries": entries,
        "coverage": coverage,
        "missing_families": missing,
        "passed": not missing,
    }
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Hashed {len(entries)} files -> {args.output}")
    for family, paths in coverage.items():
        print(f"  {family}: {len(paths)} file(s)")
    if missing:
        print("MISSING: " + ", ".join(missing))
        print("Load/download each missing instrument once, then rerun this script. No PASS was recorded.")
        return 2
    print(f"INSTRUMENT HASH COVERAGE PASSED; report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
