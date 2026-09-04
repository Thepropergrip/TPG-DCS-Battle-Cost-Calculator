import os, math, sys, re
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

# export_job.py executes this file with runpy.run_path(), which does not reliably
# put edm-jobs on sys.path. Bootstrap the generator directory explicitly.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import tpg_rubble_v5_patch as V5

V5.apply()
from tpg_rubble_common import build
import tpg_rubble_quality_pass as Q


SHAPES = {
    "smalllow": {
        "label": "Small Low",
        "asset": "TPG_Rubble_Small_Low",
        "nominal": "12 x 12 ft low pile",
    },
    "pushed": {
        "label": "Tractor Pushed",
        "asset": "TPG_Rubble_Tractor_Pushed",
        "nominal": "18 x 12 ft asymmetrical pushed pile",
    },
    "rectangular": {
        "label": "Long Rectangular",
        "asset": "TPG_Rubble_Long_Rectangular",
        "nominal": "20 x 10 ft elongated rectangular rubble bed",
    },
    "buildingface": {
        "label": "Wall Lean",
        "asset": "TPG_Rubble_Wall_Lean",
        "nominal": "10 ft wall section, straight wall edge, tapered outward toe",
    },
    "ridge": {
        "label": "Long Ridge",
        "asset": "TPG_Rubble_Long_Ridge",
        "nominal": "24 x 8 ft narrow rubble ridge",
    },
    "multihump": {
        "label": "Multi Hump",
        "asset": "TPG_Rubble_Multi_Hump",
        "nominal": "22 x 18 ft multi-hump collapse pile",
    },
}


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def _transform_point(p, key):
    """Map an object's anchor/centroid into the target pile envelope.

    IMPORTANT: for visible discrete debris this mapping is applied ONLY to the
    centroid of a rigid object/assembly. Bricks, CMUs, pipes, rebar, slabs, wood,
    trash and metal are translated, never non-uniformly scaled or vertex-warped.
    """
    x, y, z = p.x, p.y, p.z

    if key == "smalllow":
        return Vector((x * 0.62, y * 0.62, z * 0.52))

    if key == "pushed":
        xn = clamp((x + 3.10) / 6.20)
        x2 = x * (0.86 + 0.10 * xn) - 0.22 * (1.0 - xn) ** 2
        y2 = y * 0.64 + 0.10 * math.sin((x + 0.45) * 1.15)
        if z >= -0.04:
            height = 0.43 + 0.54 * (xn ** 0.72)
            z2 = z * height
            z2 += max(0.0, 0.13 * math.exp(-((x - 1.75) / 0.78) ** 2) * (1.0 - abs(y) / 3.0))
        else:
            z2 = z
        return Vector((x2, y2, z2))

    if key == "rectangular":
        nx = clamp(abs(x) / 3.15)
        shoulder = 1.0 + 0.14 * (1.0 - nx ** 3)
        x2 = x * 1.00
        y2 = y * 0.49 * shoulder
        z2 = z * (0.60 + 0.06 * (1.0 - nx)) if z >= -0.04 else z
        return Vector((x2, y2, z2))

    if key == "buildingface":
        # 10 ft wall-contact edge (~3.05 m) and only ~6 ft depth. The wall side
        # is a long STRAIGHT edge at Y=0, while the outward toe narrows, producing
        # a clear trapezoid/wedge in top view so its orientation is obvious in ME.
        y2 = (y + 3.05) * 0.30
        depth = 1.83
        t = clamp(y2 / depth)
        width_scale = 0.50 * (1.0 - 0.30 * t)
        x2 = x * width_scale
        face_h = 1.70 * ((1.0 - t) ** 1.16)
        if z >= -0.055:
            z2 = max(z * 0.48, face_h + z * 0.19 - 0.06)
            if y2 < 0.18:
                z2 += 0.045 * math.sin(x2 * 5.1 + z2 * 2.8)
        else:
            z2 = z
        return Vector((x2, y2, z2))

    if key == "ridge":
        x2 = x * 1.20
        y2 = y * 0.40 + 0.16 * math.sin(x * 0.95)
        z2 = z * (0.52 + 0.10 * (0.5 + 0.5 * math.sin(x * 1.28 + 0.7))) if z >= -0.04 else z
        return Vector((x2, y2, z2))

    if key == "multihump":
        x2 = x * 1.05
        y2 = y * 0.92
        g1 = math.exp(-(((x + 1.25) / 1.05) ** 2 + ((y + 0.20) / 1.15) ** 2))
        g2 = math.exp(-(((x - 1.10) / 1.00) ** 2 + ((y - 0.55) / 1.00) ** 2))
        g3 = math.exp(-(((x - 0.05) / 0.92) ** 2 + ((y + 1.18) / 0.92) ** 2))
        lobe = max(g1, g2, g3)
        saddle = 0.38 + 0.86 * lobe
        z2 = z * saddle + 0.08 * (g1 + g2 + g3) if z >= -0.04 else z
        return Vector((x2, y2, z2))

    raise RuntimeError(f"Unknown rubble shape: {key}")


def _is_deformable(obj):
    # Only the continuous fines mound and non-visible collision proxies may be
    # geometrically reshaped. Everything the player recognizes as debris stays rigid.
    n = obj.name
    return (
        "SOLID_RUBBLE_CORE" in n
        or n.startswith("TPG_RUBBLE_COLL_")
    )


def _assembly_key(name):
    """Keep multipart real-world items together while repositioning the pile."""
    # Pipe + its two dark end-hole meshes.
    if "_HOLE_" in name:
        return "pipe:" + name.split("_HOLE_", 1)[0]

    # Hollow CMU is made from five cubes; preserve the full block proportions.
    m = re.match(r"(.+CMU_\d+)(?:_\d+)?$", name)
    if m:
        return "cmu:" + m.group(1)

    # I-beams are three pieces.
    m = re.match(r"(.+IBEAM_\d+)(?:_\d+)?$", name)
    if m:
        return "ibeam:" + m.group(1)

    # A fractured slab and all rebar growing from that slab move as one assembly.
    m = re.search(r"FRACTURED_SLAB_(\d+)", name)
    if m:
        return "slab:" + m.group(1)
    m = re.search(r"SLAB_REBAR_(\d+)_", name)
    if m:
        return "slab:" + m.group(1)

    # Rebar cages preserve their spacing instead of being squeezed into the footprint.
    m = re.search(r"CAGE_(\d+)_", name)
    if m:
        return "cage:" + m.group(1)

    # Bent bars are emitted as several straight segments; keep each bent bar rigid.
    m = re.match(r"(.+LOOSE_BAR_\d+)_\d+$", name)
    if m:
        return "bar:" + m.group(1)
    m = re.match(r"(.+REBAR_\d+)_\d+$", name)
    if m and "SLAB_REBAR" not in name:
        return "bar:" + m.group(1)

    return "obj:" + name


def _world_vertices(obj):
    world = obj.matrix_world
    return [world @ v.co for v in obj.data.vertices]


def _bake_world(obj):
    world = obj.matrix_world.copy()
    for v in obj.data.vertices:
        v.co = world @ v.co
    obj.matrix_world = Matrix.Identity(4)
    obj.data.update()


def _warp_deformable(obj, key):
    world = obj.matrix_world.copy()
    for v in obj.data.vertices:
        v.co = _transform_point(world @ v.co, key)
    obj.matrix_world = Matrix.Identity(4)
    obj.data.update()


def _move_rigid_assemblies(key):
    deformable = []
    groups = {}

    for obj in list(bpy.context.scene.objects):
        if obj.type != "MESH":
            continue
        if _is_deformable(obj):
            deformable.append(obj)
        else:
            groups.setdefault(_assembly_key(obj.name), []).append(obj)

    # Continuous fines/collision envelope can change shape.
    for obj in deformable:
        _warp_deformable(obj, key)
        if "SOLID_RUBBLE_CORE" in obj.name:
            # Re-project only the continuous rubble surface after reshaping so the
            # photo PBR texture keeps its physical scale and does not look stretched.
            Q._box_uv(obj, .55)

    # Every visible debris assembly is translated rigidly. No vertex scaling,
    # no brick stretching, no oval pipes, no flattened CMUs/rebar/slabs.
    for objs in groups.values():
        pts = []
        for obj in objs:
            pts.extend(_world_vertices(obj))
        if not pts:
            continue
        center = sum(pts, Vector((0.0, 0.0, 0.0))) / len(pts)
        target = _transform_point(center, key)
        delta = target - center
        for obj in objs:
            _bake_world(obj)
            for v in obj.data.vertices:
                v.co += delta
            obj.data.update()


def _rename_scene_objects(key):
    tag = key.upper()
    for obj in bpy.context.scene.objects:
        if not obj.name.startswith("TPG_RUBBLE_SHAPE_"):
            obj.name = f"TPG_RUBBLE_SHAPE_{tag}_{obj.name}"[:63]


def main():
    key = os.environ.get("TPG_PACK_SHAPE", "").strip().lower()
    state = os.environ.get("TPG_PACK_STATE", "intact").strip().lower()
    detail = int(os.environ.get("TPG_PACK_DETAIL", "2"))
    if key not in SHAPES:
        raise RuntimeError(f"TPG_PACK_SHAPE must be one of {sorted(SHAPES)}; got {key!r}")
    if state not in ("intact", "destroyed"):
        raise RuntimeError(f"TPG_PACK_STATE must be intact/destroyed; got {state!r}")
    if detail not in (0, 1, 2):
        raise RuntimeError(f"TPG_PACK_DETAIL must be 0,1,2; got {detail}")

    source_variant = "destroyed" if state == "destroyed" else "intact"

    # Keep source objects unbatched until after the rigid-layout transform.
    # Otherwise one material batch can contain hundreds of separate bricks/chunks,
    # forcing a whole-batch warp that visibly stretches the debris.
    original_batch = Q._batch_visual_by_material
    Q._batch_visual_by_material = lambda: None
    try:
        build(source_variant, detail)
        Q.quality_pass(source_variant, detail)
        V5.post_quality_pass(source_variant, detail)
        _move_rigid_assemblies(key)
    finally:
        Q._batch_visual_by_material = original_batch

    # Restore V5 draw-call batching only after all debris is correctly repositioned.
    original_batch()
    _rename_scene_objects(key)

    spec = SHAPES[key]
    bpy.context.scene["TPG_asset"] = spec["asset"]
    bpy.context.scene["TPG_pack"] = "TPG Rubble Shape Pack"
    bpy.context.scene["TPG_pack_shape"] = key
    bpy.context.scene["TPG_pack_label"] = spec["label"]
    bpy.context.scene["TPG_pack_state"] = state
    bpy.context.scene["TPG_pack_detail"] = detail
    bpy.context.scene["TPG_nominal_profile"] = spec["nominal"]
    bpy.context.scene["TPG_material_source"] = "Cinematic V5 shared PBR texture/material family"
    bpy.context.scene["TPG_shape_method"] = "rigid debris assemblies + reshaped continuous fines envelope"
    bpy.context.scene["TPG_coexistence"] = "Unique clean DCS identities; original V5 and prior companion pack remain untouched"


main()
