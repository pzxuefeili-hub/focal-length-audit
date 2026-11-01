"""Prepare the 80 locked rung B JPEGs and privacy-minimized Zenodo copies.

- Reads the workspace copies of MANIFEST_80frames.csv and the scene ZIPs.
- Verifies every source SHA-256 against the locked manifest.
- Writes analysis originals under raw/rungB (never alters ZIP contents).
- Rewrites JPEG metadata without recompressing the image scan. The SOS-to-EOI
  SHA-256 must be identical between each source and its release copy.
- Keeps only camera/lens, exposure, focal-length and orientation EXIF.
  GPS, serial numbers, owner fields, MakerNote, timestamps, XMP and IPTC are
  not carried into the release copy.
- Creates per-scene contact sheets. Visual face/license-plate review remains
  PENDING until a person actually inspects them; this script never marks it PASS.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT.parent / "_inputs" / "rungB"
RAW_OUT = ROOT / "raw" / "rungB"
RELEASE = ROOT / "release" / "zenodo-rungB"

TOP_LEVEL_KEEP = {271, 272, 274}  # Make, Model, Orientation
EXIF_KEEP = {
    33434, 33437, 34855, 37377, 37378, 37380, 37383, 37385, 37386,
    41989, 42034, 42035, 42036,
}
FORBIDDEN_EXIF = {34853, 37500, 37510, 42032, 42033, 42037}


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def zip_path(scene: str, arm: str) -> Path:
    ascii_scene = re.sub(r'[^\x00-\x7F]', '', scene).strip()
    candidates = [
        INPUT / f"{scene}.zip",  # most scenes have A+B in one archive
        INPUT / f"{scene}-{arm}组.zip",
        INPUT / f"{ascii_scene}-{arm}组.zip",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"No {arm} ZIP found for {scene}: {candidates}")


def clean_exif_bytes(image: Image.Image) -> tuple[bytes, dict]:
    original = image.getexif()
    original_ifd = original.get_ifd(34665)
    clean = Image.Exif()
    for tag in TOP_LEVEL_KEEP:
        if tag in original:
            clean[tag] = original[tag]
    clean_ifd = {tag: original_ifd[tag] for tag in EXIF_KEEP if tag in original_ifd}
    clean[34665] = clean_ifd
    retained = {
        "Make": str(clean.get(271, "")),
        "Model": str(clean.get(272, "")),
        "FocalLength": str(clean_ifd.get(37386, "")),
        "ExposureTime": str(clean_ifd.get(33434, "")),
        "FNumber": str(clean_ifd.get(33437, "")),
        "ISO": str(clean_ifd.get(34855, "")),
        "LensModel": str(clean_ifd.get(42036, "")),
    }
    return clean.tobytes(), retained


def scan_offset(data: bytes) -> int:
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("Not a JPEG (SOI missing)")
    pos = 2
    while pos < len(data):
        if data[pos] != 0xFF:
            raise ValueError(f"Invalid JPEG marker at byte {pos}")
        while pos < len(data) and data[pos] == 0xFF:
            pos += 1
        marker = data[pos]
        if marker == 0xDA:
            return pos - 1
        if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            pos += 1
            continue
        length = int.from_bytes(data[pos + 1:pos + 3], "big")
        pos += 1 + length
    raise ValueError("JPEG SOS not found")


def rewrite_metadata(source: bytes, exif_payload: bytes) -> tuple[bytes, str]:
    """Replace APP1/APP13/COM segments; copy compressed scan byte-for-byte."""
    original_scan = scan_offset(source)
    output = bytearray(source[:2])
    if not exif_payload.startswith(b"Exif\x00\x00"):
        raise ValueError("Unexpected EXIF payload")
    if len(exif_payload) + 2 > 65535:
        raise ValueError("EXIF segment too large")
    output += b"\xff\xe1" + (len(exif_payload) + 2).to_bytes(2, "big") + exif_payload

    pos = 2
    while pos < len(source):
        start = pos
        if source[pos] != 0xFF:
            raise ValueError(f"Invalid JPEG marker at byte {pos}")
        while pos < len(source) and source[pos] == 0xFF:
            pos += 1
        marker = source[pos]
        if marker == 0xDA:
            output += source[start:]
            break
        if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            output += source[start:pos + 1]
            pos += 1
            continue
        length = int.from_bytes(source[pos + 1:pos + 3], "big")
        end = pos + 1 + length
        if marker not in {0xE1, 0xED, 0xFE}:  # drop EXIF/XMP, IPTC and comments
            output += source[start:end]
        pos = end
    else:
        raise ValueError("JPEG SOS not reached")

    result = bytes(output)
    new_scan = scan_offset(result)
    old_scan_hash = digest_bytes(source[original_scan:])
    new_scan_hash = digest_bytes(result[new_scan:])
    if old_scan_hash != new_scan_hash:
        raise AssertionError("Compressed image scan changed during metadata rewrite")
    return result, new_scan_hash


def contact_sheet(scene_id: str, items: list[dict], destination: Path) -> None:
    cell_w, image_h, label_h = 640, 427, 34
    sheet = Image.new("RGB", (cell_w * 2, (image_h + label_h) * 5), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=20)
    for index, item in enumerate(items):
        with Image.open(item["release_path"]) as image:
            image = image.convert("RGB")
            image.thumbnail((cell_w, image_h), Image.Resampling.LANCZOS)
            x = (index % 2) * cell_w + (cell_w - image.width) // 2
            y = (index // 2) * (image_h + label_h) + label_h
            sheet.paste(image, (x, y))
        label = f"{scene_id}  {Path(item['release_file']).stem}  {item['focal_length_mm']}mm  {item['protocol']}"
        draw.text(((index % 2) * cell_w + 8, (index // 2) * (image_h + label_h) + 6), label, fill="black", font=font)
    sheet.save(destination, quality=90)


def main() -> None:
    rows = list(csv.DictReader((INPUT / "MANIFEST_80frames.csv").open(encoding="utf-8-sig")))
    if len(rows) != 80:
        raise SystemExit(f"Expected 80 manifest rows, found {len(rows)}")
    RAW_OUT.mkdir(parents=True, exist_ok=True)
    (RELEASE / "images").mkdir(parents=True, exist_ok=True)
    (RELEASE / "qc").mkdir(parents=True, exist_ok=True)

    scenes = sorted({row["场景文件夹"] for row in rows})
    scene_ids = {scene: f"S{index:02d}" for index, scene in enumerate(scenes, start=1)}
    archives = {
        (scene, arm): zipfile.ZipFile(zip_path(scene, arm))
        for scene in scenes for arm in ("A", "B")
    }
    manifest_out = []
    by_scene = {scene: [] for scene in scenes}

    try:
        for row in rows:
            scene = row["场景文件夹"]
            scene_id = scene_ids[scene]
            focal = int(row["焦段"].removesuffix("mm"))
            arm = "A" if row["协议"] == "Fixed Position" else "B"
            archive = archives[(scene, arm)]
            suffix = f"-{arm}-{focal}mm-{row['协议']}.JPG"
            matches = [name for name in archive.namelist() if name.endswith(suffix)]
            if len(matches) != 1:
                raise RuntimeError(f"{scene}: expected one member ending {suffix}, found {len(matches)}")
            source = archive.read(matches[0])
            source_hash = digest_bytes(source)
            if source_hash != row["SHA-256"]:
                raise RuntimeError(f"Locked SHA mismatch for {scene} {suffix}")

            raw_path = RAW_OUT / f"{scene_id}_{arm}_{focal}mm.JPG"
            raw_path.write_bytes(source)
            release_name = f"{scene_id}_{arm}_{focal}mm.jpg"
            release_path = RELEASE / "images" / release_name

            with Image.open(io.BytesIO(source)) as image:
                exif_payload, retained = clean_exif_bytes(image)
                width, height = image.size
            cleaned, scan_hash = rewrite_metadata(source, exif_payload)
            release_path.write_bytes(cleaned)

            with Image.open(release_path) as check:
                check_exif = check.getexif()
                check_ifd = check_exif.get_ifd(34665)
                forbidden_present = [
                    tag for tag in FORBIDDEN_EXIF if tag in check_exif or tag in check_ifd
                ]
                if forbidden_present:
                    raise RuntimeError(f"Forbidden EXIF remains in {release_name}: {forbidden_present}")
                if check.size != (width, height):
                    raise RuntimeError(f"Dimensions changed in {release_name}")
                focal_check = check_ifd.get(37386)
                if focal_check is None:
                    raise RuntimeError(f"Focal length missing in {release_name}")

            item = {
                "release_file": f"images/{release_name}",
                "release_path": release_path,
                "scene_id": scene_id,
                "scene": scene,
                "rung": "B",
                "protocol": row["协议"],
                "focal_length_mm": focal,
                "source_original": row["原始来源文件"],
                "source_sha256": source_hash,
                "release_sha256": digest_file(release_path),
                "compressed_scan_sha256": scan_hash,
                "width": width,
                "height": height,
                **{f"exif_{key}": value for key, value in retained.items()},
                "metadata_privacy_check": "PASS",
                "visual_face_plate_review": "PENDING",
            }
            manifest_out.append(item)
            by_scene[scene].append(item)
            print(f"{release_name}: metadata PASS, scan unchanged")
    finally:
        for archive in archives.values():
            archive.close()

    fieldnames = [key for key in manifest_out[0] if key != "release_path"]
    with (RELEASE / "dataset_manifest.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: value for key, value in row.items() if key != "release_path"} for row in manifest_out)

    for scene, items in by_scene.items():
        contact_sheet(scene_ids[scene], items, RELEASE / "qc" / f"{scene_ids[scene]}_contact.jpg")

    qc = {
        "images": len(manifest_out),
        "locked_source_sha256_verified": True,
        "compressed_scan_unchanged_for_all_images": True,
        "metadata_privacy_check": "PASS",
        "metadata_removed": ["GPS", "serial numbers", "owner fields", "MakerNote", "timestamps", "XMP", "IPTC", "comments"],
        "metadata_retained": ["camera make/model", "lens", "focal length", "exposure", "orientation"],
        "visual_face_plate_review": "PENDING",
        "release_gate": "DO NOT UPLOAD until every per-scene contact sheet has been visually reviewed and any face/plate issue is resolved.",
    }
    (RELEASE / "qc" / "qc_status.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    (RELEASE / "README.txt").write_text(
        "Rung B locked reference photographs: 8 scenes x 5 focal lengths x 2 protocols = 80 JPEGs.\n"
        "License planned by the project protocol: CC BY 4.0. Confirm author/title before creating the Zenodo record.\n"
        "Metadata privacy rewriting is complete; compressed image data are unchanged.\n"
        "Visual face/license-plate review is PENDING. Do not upload before that review is resolved.\n"
        "See dataset_manifest.csv for provenance, hashes and retained EXIF; qc/ contains review sheets.\n",
        encoding="utf-8",
    )
    print(f"DONE: {len(manifest_out)} release copies in {RELEASE}")
    print("VISUAL REVIEW PENDING: inspect qc/S01..S08_contact.jpg before upload.")


if __name__ == "__main__":
    main()
