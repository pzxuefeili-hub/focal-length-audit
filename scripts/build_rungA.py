"""
build_rungA.py — procedural rung A ground-truth renders for the focal-length audit.

Run with:
  blender -b -P scripts/build_rungA.py -- --out ../raw/rungA --start 0 --end 70

Design (blueprint §Phase 2, rung A):
  5 simple scenes, each with two IDENTICAL objects (near / far) on a ground plane
  with strong straight-line perspective cues. Rendered at 7 focal lengths
  (16/24/35/50/85/135/200 mm, full-frame 36x24 sensor, vertical fit) under both
  protocols:
    A fixed-position : camera stays at the 24mm position for every focal length
    B fixed-framing  : camera dollies back proportionally to f (d = d0 * f/24)
                       so the near object keeps ~constant image height
  => 5 * 7 * 2 = 70 renders, each with an exact-knowledge JSON sidecar.

Only focal length / camera pose vary; geometry, lighting and materials are frozen.
"""
import bpy
import json
import math
import os
import sys
import argparse


# ---------------- args ----------------
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="../raw/rungA")
ap.add_argument("--start", type=int, default=0)
ap.add_argument("--end", type=int, default=70)
ap.add_argument("--engine", default="BLENDER_EEVEE_NEXT")
args = ap.parse_args(argv)

OUT = os.path.abspath(args.out)
os.makedirs(OUT, exist_ok=True)

FOCALS = [16, 24, 35, 50, 85, 135, 200]
PROTOCOLS = ["fixedpos", "fixedframe"]
SCENES = ["cones", "boxes", "cylinders", "spheres", "trees"]

# frozen global scene parameters
CAM_HEIGHT = 1.2          # m, constant across everything
D0 = 6.0                  # camera-to-near-object distance at 24mm (fixed-position)
FAR_GAP = 8.0             # near -> far object extra depth
SENSOR_W, SENSOR_H = 36.0, 24.0   # full-frame, mm
RES_X, RES_Y = 1024, 683          # 3:2
SEED_NOTE = "geometry-frozen; no randomness"


def nominal_vfov(f):
    return math.degrees(2 * math.atan(SENSOR_H / 2.0 / f))


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, rough=0.9):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    return m


def add_ground(m_ground, m_line):
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0))
    g = bpy.context.active_object
    g.data.materials.append(m_ground)
    # straight white lines running away from the camera + one lateral line
    for x in (-3.0, -1.5, 1.5, 3.0):
        bpy.ops.mesh.primitive_cube_add(location=(x, -8.0, 0.005))
        ln = bpy.context.active_object
        ln.scale = (0.04, 22.0, 0.005)
        ln.data.materials.append(m_line)
    bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0.006))
    lat = bpy.context.active_object
    lat.scale = (8.0, 0.04, 0.005)
    lat.data.materials.append(m_line)
    return g


def add_sun():
    sun = bpy.data.lights.new("sun", type="SUN")
    sun.energy = 3.0
    sun.angle = math.radians(5)
    so = bpy.data.objects.new("sun", sun)
    bpy.context.collection.objects.link(so)
    so.rotation_euler = (math.radians(50), 0, math.radians(30))
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.7, 0.8, 1.0, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    bpy.context.scene.world = world


def build_scene_objects(scene_id, m_obj, m_ground, m_line):
    """Two identical objects, near at y=0, far at y=-FAR_GAP. Returns object spec."""
    add_ground(m_ground, m_line)
    spec = {"scene": scene_id, "objects": []}

    def place(make_fn):
        # lateral offset so the near object never occludes the far one;
        # both remain fully visible and measurable in every frame
        make_fn(-0.55, 0.0)         # near
        make_fn(+0.55, -FAR_GAP)    # far

    if scene_id == "cones":
        def mk(x, y):
            bpy.ops.mesh.primitive_cone_add(radius1=0.3, radius2=0.03, depth=0.76,
                                            location=(x, y, 0.38))
            bpy.context.active_object.data.materials.append(m_obj)
        place(mk); spec["objects"] = [{"type": "cone", "h": 0.76}, {"type": "cone", "h": 0.76}]
    elif scene_id == "boxes":
        def mk(x, y):
            bpy.ops.mesh.primitive_cube_add(size=0.5, location=(x, y, 0.25))
            bpy.context.active_object.data.materials.append(m_obj)
        place(mk); spec["objects"] = [{"type": "cube", "h": 0.5}, {"type": "cube", "h": 0.5}]
    elif scene_id == "cylinders":
        def mk(x, y):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=1.0,
                                                location=(x, y, 0.5))
            bpy.context.active_object.data.materials.append(m_obj)
        place(mk); spec["objects"] = [{"type": "cylinder", "h": 1.0}, {"type": "cylinder", "h": 1.0}]
    elif scene_id == "spheres":
        def mk(x, y):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(x, y, 0.35))
            bpy.context.active_object.data.materials.append(m_obj)
        place(mk); spec["objects"] = [{"type": "sphere", "h": 0.7}, {"type": "sphere", "h": 0.7}]
    elif scene_id == "trees":
        def mk(x, y):
            bpy.ops.mesh.primitive_cone_add(radius1=0.8, radius2=0.05, depth=2.5,
                                            location=(x, y, 1.25))
            bpy.context.active_object.data.materials.append(m_obj)
        place(mk); spec["objects"] = [{"type": "tree", "h": 2.5}, {"type": "tree", "h": 2.5}]
    spec["near_y"], spec["far_y"] = 0.0, -FAR_GAP
    return spec


def add_camera(f_mm, protocol):
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = f_mm
    cam_d.sensor_width = SENSOR_W
    cam_d.sensor_height = SENSOR_H
    cam_d.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new("cam", cam_d)
    bpy.context.collection.objects.link(cam)
    dist = D0 if protocol == "fixedpos" else D0 * f_mm / 24.0
    cam.location = (0.0, dist, CAM_HEIGHT)
    # aim at the near object's vertical center (y=0, near-object mid-height ~0.5)
    target = bpy.data.objects.new("target", None)
    bpy.context.collection.objects.link(target)
    target.location = (0.0, 0.0, 0.5)
    direction = target.location - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam, dist


def render_one(scene_id, f_mm, protocol, idx):
    reset_scene()
    sc = bpy.context.scene
    sc.render.engine = args.engine
    sc.render.resolution_x = RES_X
    sc.render.resolution_y = RES_Y
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "Standard"

    m_ground = mat("ground", (0.35, 0.35, 0.35))
    m_line = mat("line", (0.95, 0.95, 0.95))
    colors = {"cones": (1.0, 0.45, 0.05), "boxes": (0.8, 0.1, 0.1),
              "cylinders": (0.1, 0.2, 0.9), "spheres": (0.6, 0.6, 0.6),
              "trees": (0.15, 0.5, 0.15)}
    m_obj = mat("object", colors[scene_id])
    spec = build_scene_objects(scene_id, m_obj, m_ground, m_line)
    add_sun()
    cam, dist = add_camera(f_mm, protocol)

    stem = f"rungA_{scene_id}_f{f_mm:03d}_{protocol}"
    png = os.path.join(OUT, stem + ".png")
    sc.render.filepath = png
    bpy.ops.render.render(write_still=True)

    meta = {
        "image": stem + ".png",
        "rung": "A",
        "scene": scene_id,
        "protocol": protocol,
        "focal_length_mm": f_mm,
        "nominal_vfov_deg": round(nominal_vfov(f_mm), 3),
        "sensor_mm": [SENSOR_W, SENSOR_H],
        "sensor_fit": "VERTICAL",
        "camera": {"location": [0.0, round(dist, 4), CAM_HEIGHT],
                   "target": [0.0, 0.0, 0.5],
                   "height_m": CAM_HEIGHT},
        "near_y": 0.0, "far_y": -FAR_GAP,
        "resolution": [RES_X, RES_Y],
        "render_engine": args.engine,
        "blender_version": bpy.app.version_string,
        "seed_note": SEED_NOTE,
        **spec,
    }
    with open(os.path.join(OUT, stem + ".json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    print(f"[{idx}] wrote {stem}.png")


jobs = [(s, f, p) for s in SCENES for f in FOCALS for p in PROTOCOLS]
end = min(args.end, len(jobs))
for i in range(args.start, end):
    s, f, p = jobs[i]
    render_one(s, f, p, i)
print(f"DONE {args.start}..{end} of {len(jobs)}")
