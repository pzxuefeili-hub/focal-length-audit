"""
build_rungA.py — procedural rung A ground-truth renders for the focal-length audit.

Run with:
  blender -b -P scripts/build_rungA.py -- --out <abs path to raw/rungA> --start 0 --end 70

Design (blueprint Phase 2, rung A):
  5 simple scenes, each with two IDENTICAL objects (near / far) on a textured
  ground plane with strong straight-line perspective cues (white lines, poles,
  distant tree line). Rendered at 7 focal lengths (16/24/35/50/85/135/200 mm,
  full-frame 36x24 sensor, vertical fit) under both protocols:
    fixedpos    : camera stays at the 24mm position for every focal length
    fixedframe  : camera dollies back proportionally to f (d = d0 * f/24)
                  so the near object keeps ~constant image height
  => 5 * 7 * 2 = 70 renders, each with an exact-knowledge JSON sidecar.

v2 (2026-09-30): added procedural textures (asphalt noise), cone stripes,
utility poles, tree line, bushes — preliminary GeoCalib check on v1 showed
prior fallback on featureless synthetic scenes; this version closes the
realism gap while keeping every geometric parameter frozen.
"""
import bpy
import json
import math
import os
import random
import sys
import argparse

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--start", type=int, default=0)
ap.add_argument("--end", type=int, default=70)
ap.add_argument("--engine", default="BLENDER_EEVEE_NEXT")
args = ap.parse_args(argv)

OUT = os.path.abspath(args.out)
os.makedirs(OUT, exist_ok=True)

FOCALS = [16, 24, 35, 50, 85, 135, 200]
PROTOCOLS = ["fixedpos", "fixedframe"]
SCENES = ["cones", "boxes", "cylinders", "spheres", "trees"]

CAM_HEIGHT = 1.2
D0 = 6.0
FAR_GAP = 8.0
SENSOR_W, SENSOR_H = 36.0, 24.0
RES_X, RES_Y = 1024, 683
SEED_NOTE = "geometry-frozen; textures procedural with fixed seed 42"


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


def noise_mat(name, c_dark, c_light, scale=6.0, rough=0.95):
    """Two-color procedural noise material (asphalt / dirt look)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = 4.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c_dark, 1.0)
    ramp.color_ramp.elements[1].color = (*c_light, 1.0)
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    return m


def add_ground(m_ground, m_line):
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
    g = bpy.context.active_object
    g.data.materials.append(m_ground)
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


def add_environment(m_pole, m_trunk, m_leaf, m_rock):
    """Perspective-cue enrichment: utility poles along the lines, a distant
    tree line, scattered rocks/bushes. Deterministic (seed 42)."""
    rng = random.Random(42)
    # utility poles every 8 m out to 64 m — visible even in 200mm frames
    for x in (-3.0, 3.0):
        for i, y in enumerate(range(-4, -65, -8)):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=4.2, location=(x, y, 2.1))
            p = bpy.context.active_object
            p.data.materials.append(m_pole)
    # distant tree line (two staggered rows)
    for row, y in ((0, -46), (1, -58)):
        for k in range(14):
            x = -16 + k * 2.4 + rng.uniform(-0.7, 0.7) + (row * 1.2)
            h = rng.uniform(3.0, 5.5)
            bpy.ops.mesh.primitive_cone_add(radius1=h * 0.42, radius2=0.1, depth=h,
                                            location=(x, y + rng.uniform(-2, 2), h / 2))
            t = bpy.context.active_object
            t.data.materials.append(m_leaf)
            bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=1.0,
                                                location=(x, y, 0.5))
            tr = bpy.context.active_object
            tr.data.materials.append(m_trunk)
    # scattered rocks / bushes near the camera path
    for k in range(10):
        x = rng.choice([-1, 1]) * rng.uniform(1.2, 4.5)
        y = rng.uniform(-16, 3)
        r = rng.uniform(0.08, 0.28)
        bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=1,
                                              location=(x, y, r * 0.6))
        rk = bpy.context.active_object
        rk.scale.z = 0.7
        rk.data.materials.append(m_rock)


def add_sun():
    sun = bpy.data.lights.new("sun", type="SUN")
    sun.energy = 3.5
    sun.angle = math.radians(8)
    so = bpy.data.objects.new("sun", sun)
    bpy.context.collection.objects.link(so)
    so.rotation_euler = (math.radians(55), 0, math.radians(35))
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.7, 0.95, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
    bpy.context.scene.world = world


def build_scene_objects(scene_id, m_obj, m_ground, m_line, m_white):
    add_ground(m_ground, m_line)
    spec = {"scene": scene_id, "objects": []}

    def place(make_fn):
        make_fn(-0.55, 0.0)         # near
        make_fn(+0.55, -FAR_GAP)    # far

    if scene_id == "cones":
        def mk(x, y):
            bpy.ops.mesh.primitive_cone_add(radius1=0.3, radius2=0.03, depth=0.76,
                                            location=(x, y, 0.38))
            bpy.context.active_object.data.materials.append(m_obj)
            # reflective stripe, like a real traffic cone
            bpy.ops.mesh.primitive_cylinder_add(radius=0.20, depth=0.10,
                                                location=(x, y, 0.42))
            bpy.context.active_object.data.materials.append(m_white)
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
            bpy.ops.mesh.primitive_cylinder_add(radius=0.09, depth=0.6,
                                                location=(x, y, 0.3))
            bpy.context.active_object.data.materials.append(m_white)  # trunk color
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

    m_ground = noise_mat("asphalt", (0.28, 0.28, 0.28), (0.48, 0.48, 0.48), scale=7.0)
    m_line = mat("line", (0.92, 0.92, 0.88))
    m_pole = mat("pole", (0.25, 0.22, 0.2))
    m_trunk = mat("trunk", (0.3, 0.2, 0.12))
    m_leaf = noise_mat("leaf", (0.05, 0.22, 0.05), (0.2, 0.42, 0.12), scale=3.0)
    m_rock = noise_mat("rock", (0.3, 0.28, 0.25), (0.5, 0.48, 0.44), scale=5.0)
    m_white = mat("white", (0.95, 0.95, 0.95))
    colors = {"cones": (1.0, 0.45, 0.05), "boxes": (0.8, 0.1, 0.1),
              "cylinders": (0.1, 0.2, 0.9), "spheres": (0.6, 0.6, 0.6),
              "trees": (0.15, 0.5, 0.15)}
    m_obj = mat("object", colors[scene_id])
    spec = build_scene_objects(scene_id, m_obj, m_ground, m_line, m_white)
    add_environment(m_pole, m_trunk, m_leaf, m_rock)
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
        "scene_version": "v2-textured",
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
