"""make_rungC_crops.py — Rung C exact center-crops (protocol §7 + addendum 2026-10-30).

For each of the 8 rung B scenes:
  - from the fixed-position 24mm frame: center-crops reproducing 35/50/70/105/200mm FoV
  - from the fixed-position 105mm frame: the 200mm sensitivity variant (instructor 2026-09-30)
Total 48 crops. Crop side = short_side * base_f / target_f; Lanczos resize to 1024x1024.
No instrument is run here; this is geometric cropping only (DOI red line untouched).
Inputs : Desktop MANIFEST_80frames.csv + the 8 scene ZIPs (read in place, no extraction).
Outputs: raw/rungC/<scene>__f<target>__from<base>.png + .json sidecar + rungC_manifest.csv
"""
import csv, io, json, hashlib, os, zipfile
from PIL import Image

DESKTOP = r'C:\Users\pzxue\Desktop'
MANIFEST = os.path.join(DESKTOP, 'MANIFEST_80frames.csv')
OUT = r'D:\KimiData\kimi\tasks\2026-09-29\17-25-10-76e8df1f\focal-length-audit\raw\rungC'
TARGETS_FROM_24 = [35, 50, 70, 105, 200]
SIZE = 1024

os.makedirs(OUT, exist_ok=True)
rows = list(csv.DictReader(open(MANIFEST, encoding='utf-8-sig')))
manifest_out = []

def frame_bytes(scene_zip_name, suffix):
    zpath = os.path.join(DESKTOP, scene_zip_name + '.zip')
    if not os.path.exists(zpath):  # scenes split into A/B zips; fixed position is in A组
        zpath = os.path.join(DESKTOP, scene_zip_name + '-A组.zip')
    if not os.path.exists(zpath):  # manifest scene name may carry a CJK suffix the zip lacks
        import re as _re
        zpath = os.path.join(DESKTOP, _re.sub(r'[^\x00-\x7F]', '', scene_zip_name).strip() + '-A组.zip')
    with zipfile.ZipFile(zpath) as z:
        # match by ASCII suffix; Chinese chars in zip member names are GBK-mangled
        for n in z.namelist():
            if n.endswith(suffix):
                return z.read(n)
    raise FileNotFoundError(f'{suffix} not in {zpath}')

count = 0
for scene in sorted({r['场景文件夹'] for r in rows}):
    fixed = [r for r in rows if r['场景文件夹'] == scene and r['协议'] == 'Fixed Position']
    jobs = []
    f24 = next(r for r in fixed if r['焦段'] == '24mm')
    for t in TARGETS_FROM_24:
        jobs.append((f24, 24, t))
    f105 = next(r for r in fixed if r['焦段'] == '105mm')
    jobs.append((f105, 105, 200))  # sensitivity variant

    for rec, base_f, target_f in jobs:
        raw = frame_bytes(scene, f'-A-{base_f}mm-Fixed Position.JPG')
        im = Image.open(io.BytesIO(raw)).convert('RGB')
        w, h = im.size
        side = round(min(w, h) * base_f / target_f)
        cx, cy = w // 2, h // 2
        box = (cx - side // 2, cy - side // 2, cx - side // 2 + side, cy - side // 2 + side)
        crop = im.crop(box).resize((SIZE, SIZE), Image.LANCZOS)

        stem = f'{scene}__f{target_f}__from{base_f}mm'
        png_path = os.path.join(OUT, stem + '.png')
        crop.save(png_path)
        sha = hashlib.sha256(open(png_path, 'rb').read()).hexdigest()

        sidecar = {
            'rung': 'C', 'scene': scene, 'protocol': 'Fixed Position',
            'source_frame': rec['入组文件名'], 'source_sha256': rec['SHA-256'],
            'base_focal_mm': base_f, 'target_focal_mm': target_f,
            'source_size': [w, h], 'crop_box_xyxy': list(box), 'crop_side_px': side,
            'resize': f'Lanczos to {SIZE}x{SIZE}',
            'note': 'exact optical center-crop; truth inherited geometrically; no instrument run',
        }
        with open(os.path.join(OUT, stem + '.json'), 'w', encoding='utf-8') as f:
            json.dump(sidecar, f, ensure_ascii=False, indent=2)

        manifest_out.append([stem + '.png', scene, base_f, target_f, side, sha])
        count += 1

with open(os.path.join(OUT, 'rungC_manifest.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    wcsv = csv.writer(f)
    wcsv.writerow(['file', 'scene', 'base_focal_mm', 'target_focal_mm', 'crop_side_px', 'sha256'])
    wcsv.writerows(manifest_out)

print(f'DONE: {count} crops written to {OUT}')
