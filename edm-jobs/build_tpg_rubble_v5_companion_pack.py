import os, math
import bpy
from mathutils import Vector, Matrix

import tpg_rubble_v5_patch as V5

V5.apply()
from tpg_rubble_common import build
from tpg_rubble_quality_pass import quality_pass


SHAPES = {
    "smalllow": {
        "label": "Small Low",
        "asset": "TPG_Rubble_SmallLow_Cinematic_V5A",
        "nominal": "12 x 12 ft low pile",
    },
    "pushed": {
        "label": "Tractor Pushed",
        "asset": "TPG_Rubble_Pushed_Cinematic_V5B",
        "nominal": "18 x 12 ft asymmetrical pushed pile",
    },
    "rectangular": {
        "label": "Rectangular",
        "asset": "TPG_Rubble_Rectangular_Cinematic_V5C",
        "nominal": "20 x 10 ft elongated rectangular rubble bed",
    },
    "buildingface": {
        "label": "Building Face",
        "asset": "TPG_Rubble_BuildingFace_Cinematic_V5D",
        "nominal": "10 ft wall section with tall rough face and outward slope",
    },
    "ridge": {
        "label": "Long Ridge",
        "asset": "TPG_Rubble_Ridge_Cinematic_V5E",
        "nominal": "24 x 8 ft narrow rubble ridge",
    },
    "multihump": {
        "label": "Multi Hump",
        "asset": "TPG_Rubble_MultiHump_Cinematic_V5F",
        "nominal": "22 x 18 ft multi-hump collapse pile",
    },
}


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def _transform_point(p, key):
    x, y, z = p.x, p.y, p.z

    if key == "smalllow":
        # Compact low mound: roughly 12 x 12 ft and about half V5 height.
        return Vector((x * 0.62, y * 0.62, z * 0.52))

    if key == "pushed":
        # A small-machine pushed pile. Narrower cross-section, dragged tail to -X,
        # compressed/taller push front toward +X, and a slight S-wander through the ridge.
        xn = clamp((x + 3.10) / 6.20)
        x2 = x * (0.86 + 0.10 * xn) - 0.22 * (1.0 - xn) ** 2
        y2 = y * 0.64 + 0.10 * math.sin((x + 0.45) * 1.15)
        if z >= -0.04:
            height = 0.43 + 0.54 * (xn ** 0.72)
            z2 = z * height
            # compressed blade face / nose bulge without a geometric wall
            z2 += max(0.0, 0.13 * math.exp(-((x - 1.75) / 0.78) ** 2) * (1.0 - abs(y) / 3.0))
        else:
            z2 = z
        return Vector((x2, y2, z2))

    if key == "rectangular":
        # Elongated rubble bed with squarer shoulders than a simple ellipse.
        nx = clamp(abs(x) / 3.15)
        shoulder = 1.0 + 0.14 * (1.0 - nx ** 3)
        x2 = x * 1.00
        y2 = y * 0.49 * shoulder
        if z >= -0.04:
            z2 = z * (0.58 + 0.08 * (1.0 - nx))
        else:
            z2 = z
        return Vector((x2, y2, z2))

    if key == "buildingface":
        # Origin is intentionally on the wall-side face. Base V5 Y [-~3,+~3]
        # maps to [0,~3.35m]. The first ~0.15m rises almost vertically, creating
        # a rough 90-degree-ish building-contact face, then slopes away.
        x2 = x * 0.52
        y2 = (y + 3.05) * 0.55
        depth = 3.36
        t = clamp(y2 / depth)
        face_h = 1.68 * ((1.0 - t) ** 1.18)
        if z >= -0.055:
            # Keep original rubble microrelief but drive the envelope from the wall face.
            z2 = max(z * 0.48, face_h + z * 0.20 - 0.06)
            # Roughen the vertical face so it never looks like a clean retaining wall.
            if y2 < 0.22:
                z2 += 0.055 * math.sin(x2 * 5.3 + z2 * 3.1)
        else:
            z2 = z
        return Vector((x2, y2, z2))

    if key == "ridge":
        # Long narrow, slightly snaking rubble windrow. ~24 x 8 ft.
        x2 = x * 1.20
        y2 = y * 0.40 + 0.16 * math.sin(x * 0.95)
        if z >= -0.04:
            z2 = z * (0.52 + 0.10 * (0.5 + 0.5 * math.sin(x * 1.28 + 0.7)))
        else:
            z2 = z
        return Vector((x2, y2, z2))

    if key == "multihump":
        # Three connected collapse lobes with a lower saddle between them.
        x2 = x * 1.05
        y2 = y * 0.92
        g1 = math.exp(-(((x + 1.25) / 1.05) ** 2 + ((y + 0.20) / 1.15) ** 2))
        g2 = math.exp(-(((x - 1.10) / 1.00) ** 2 + ((y - 0.55) / 1.00) ** 2))
        g3 = math.exp(-(((x - 0.05) / 0.92) ** 2 + ((y + 1.18) / 0.92) ** 2))
        lobe = max(g1, g2, g3)
        saddle = 0.38 + 0.86 * lobe
        if z >= -0.04:
            z2 = z * saddle + 0.08 * (g1 + g2 + g3)
        else:
            z2 = z
        return Vector((x2, y2, z2))

    raise RuntimeError(f"Unknown companion shape: {key}")


def _bake_and_warp(key):
    # Bake each object's world transform into its mesh before nonlinear warping.
    # This keeps rotated slabs, pipes, rebar, CMUs, trash and collision shells aligned
    # with the same footprint transform rather than merely scaling object origins.
    for obj in list(bpy.context.scene.objects):
        if obj.type != 'MESH':
            continue
        world = obj.matrix_world.copy()
        mesh = obj.data
        for v in mesh.vertices:
            wp = world @ v.co
            v.co = _transform_point(wp, key)
        obj.matrix_world = Matrix.Identity(4)
        mesh.update()


def _rename_scene_objects(key):
    # DCS-facing EDM name is controlled by the export job output. Internal Blender names
    # get a companion prefix only to keep debugging and saved .blend inspection clear.
    tag = key.upper()
    for obj in bpy.context.scene.objects:
        if not obj.name.startswith('TPG_PACK_'):
            obj.name = f"TPG_PACK_{tag}_{obj.name}"[:63]


def main():
    key = os.environ.get('TPG_PACK_SHAPE', '').strip().lower()
    state = os.environ.get('TPG_PACK_STATE', 'intact').strip().lower()
    detail = int(os.environ.get('TPG_PACK_DETAIL', '2'))
    if key not in SHAPES:
        raise RuntimeError(f"TPG_PACK_SHAPE must be one of {sorted(SHAPES)}; got {key!r}")
    if state not in ('intact', 'destroyed'):
        raise RuntimeError(f"TPG_PACK_STATE must be intact/destroyed; got {state!r}")
    if detail not in (0, 1, 2):
        raise RuntimeError(f"TPG_PACK_DETAIL must be 0,1,2; got {detail}")

    source_variant = 'destroyed' if state == 'destroyed' else 'intact'
    build(source_variant, detail)
    quality_pass(source_variant, detail)
    V5.post_quality_pass(source_variant, detail)

    _bake_and_warp(key)
    _rename_scene_objects(key)

    spec = SHAPES[key]
    bpy.context.scene['TPG_asset'] = spec['asset']
    bpy.context.scene['TPG_pack'] = 'TPG Rubble Companion Pack Cinematic V5'
    bpy.context.scene['TPG_pack_shape'] = key
    bpy.context.scene['TPG_pack_label'] = spec['label']
    bpy.context.scene['TPG_pack_state'] = state
    bpy.context.scene['TPG_pack_detail'] = detail
    bpy.context.scene['TPG_nominal_profile'] = spec['nominal']
    bpy.context.scene['TPG_material_source'] = 'Cinematic V5 identical shared texture/object language'
    bpy.context.scene['TPG_coexistence'] = 'Standalone companion pack; original Cinematic V5 remains untouched'


main()
