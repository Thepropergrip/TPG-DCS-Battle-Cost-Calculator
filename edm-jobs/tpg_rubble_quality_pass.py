import bpy, math, random
from mathutils import Vector, Euler

from tpg_rubble_common import mats, cube, cyl, rebar, cable, ensure_uv, mound_z


def _local(center, offset, rot):
    return Vector(center) + Euler(rot, 'XYZ').to_matrix() @ Vector(offset)


def _delete_prefix(prefix):
    for o in list(bpy.context.scene.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)


def _box_uv(o, scale=.48):
    if o.type != 'MESH':
        return
    mesh = o.data
    uv = mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap')
    mesh.update()
    for poly in mesh.polygons:
        n = poly.normal
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            if az >= ax and az >= ay:
                uv.data[li].uv = (co.x * scale, co.y * scale)
            elif ay >= ax:
                uv.data[li].uv = (co.x * scale, co.z * scale)
            else:
                uv.data[li].uv = (co.y * scale, co.z * scale)


def _cmu(name, loc, rot, M, broken=False):
    L, W, H = (.40, .20, .20) if not broken else (.34, .18, .17)
    t = .036
    parts = [
        ((0, +(W-t)/2, 0), (L, t, H)),
        ((0, -(W-t)/2, 0), (L, t, H)),
        ((+(L-t)/2, 0, 0), (t, W-2*t, H)),
        ((-(L-t)/2, 0, 0), (t, W-2*t, H)),
        ((0, 0, 0), (t, W-2*t, H)),
    ]
    for i, (off, dims) in enumerate(parts):
        p = _local(loc, off, rot)
        cube(f'{name}_{i}', p, dims, M['concrete2'], rot=rot, bevel=.008)


def _ibeam(name, loc, length, rot, mat):
    flange_w, flange_t, web_h, web_t = .24, .040, .24, .038
    parts = [
        ((0, 0, +(web_h-flange_t)/2), (length, flange_w, flange_t)),
        ((0, 0, -(web_h-flange_t)/2), (length, flange_w, flange_t)),
        ((0, 0, 0), (length, web_t, web_h-2*flange_t)),
    ]
    for i, (off, dims) in enumerate(parts):
        cube(f'{name}_{i}', _local(loc, off, rot), dims, mat, rot=rot, bevel=.010)


def _fractured_slab(name, loc, length, width, thick, rot, face_mat, fracture_mat, rng):
    # Jagged reinforced-concrete slab with distinct exposed-aggregate fracture faces.
    base = [
        (-.50,-.42),(-.18,-.53),(.18,-.48),(.50,-.34),
        (.54,.04),(.42,.46),(.05,.53),(-.34,.45),(-.53,.15),
    ]
    ring = []
    for x,y in base:
        ring.append((
            x*length + rng.uniform(-.045,.045)*length,
            y*width + rng.uniform(-.045,.045)*width,
        ))
    n = len(ring)
    verts = [(x,y,+thick*.5) for x,y in ring] + [(x,y,-thick*.5) for x,y in ring]
    faces = [tuple(range(n)), tuple(reversed(range(n,2*n)))]
    for i in range(n):
        j=(i+1)%n
        faces.append((i,j,n+j,n+i))
    mesh=bpy.data.meshes.new(name+'_mesh')
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    mesh.materials.append(face_mat)
    mesh.materials.append(fracture_mat)
    for idx,p in enumerate(mesh.polygons):
        p.material_index = 0 if idx < 2 else 1
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    obj.location=loc
    obj.rotation_euler=rot
    _box_uv(obj,.62)
    return obj


def _corrugated(name, loc, length, width, rot, mat, bend=.08, ribs=11):
    nx, ny = 4, ribs + 1
    verts = []
    for ix in range(nx):
        u = ix / (nx - 1)
        x = (u - .5) * length
        curve = ((u - .5) ** 2 - .08) * bend
        for iy in range(ny):
            v = iy / (ny - 1)
            y = (v - .5) * width
            z = .018 * math.sin(v * ribs * math.pi * 2) + curve
            verts.append((x, y, z))
    faces = []
    for ix in range(nx - 1):
        for iy in range(ny - 1):
            a = ix * ny + iy
            faces.append((a, a+1, (ix+1)*ny+iy+1, (ix+1)*ny+iy))
    mesh = bpy.data.meshes.new(name+'_mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rot
    obj.data.materials.append(mat)
    _box_uv(obj, .55)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    sol = obj.modifiers.new('torn_sheet_thickness', 'SOLIDIFY')
    sol.thickness = .012
    sol.offset = 0
    bpy.ops.object.modifier_apply(modifier=sol.name)
    return obj


def _bag(name, loc, scale, rot, mat):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1.0, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    _box_uv(o)
    return o


def _batch_visual_by_material():
    groups = {}
    for o in list(bpy.context.scene.objects):
        if o.type != 'MESH' or o.name.startswith('TPG_RUBBLE_COLL_'):
            continue
        if len(o.data.materials) != 1 or o.data.materials[0] is None:
            continue
        groups.setdefault(o.data.materials[0].name, []).append(o)
    for mat_name, objs in groups.items():
        if len(objs) < 2:
            continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.join()
        joined = bpy.context.object
        safe = ''.join(c if c.isalnum() else '_' for c in mat_name)
        joined.name = 'TPG_RUBBLE_BATCH_' + safe[-42:]
        ensure_uv(joined)


def quality_pass(variant='intact', detail=2):
    M = mats()
    rng = random.Random(42191 + detail*61 + (777 if variant == 'destroyed' else 0))

    _delete_prefix('TPG_RUB_BLOCK_')
    if detail >= 1:
        cmus = [
            (-2.05, -.45, .22, (.15, -.30, .28)),
            (-1.55, .28, .48, (-.32, .18, 1.02)),
            (-.70, -1.45, .35, (.22, .30, -.72)),
            (.25, 1.45, .58, (-.26, -.24, .50)),
            (.95, .95, .72, (.34, .08, 1.25)),
            (1.62, -.15, .40, (-.40, .18, -.25)),
            (1.92, -.92, .18, (.08, .35, .88)),
            (.75, -1.62, .30, (.28, -.20, 1.62)),
            (-1.12, 1.25, .42, (-.18, .26, -1.10)),
            (1.10, .10, .82, (.26, .12, .15)),
        ]
        if detail == 1:
            cmus = cmus[:6]
        for i, (x,y,z,rot) in enumerate(cmus):
            if variant == 'destroyed':
                x *= 1.07; y *= 1.08; z *= .78
                rot = (rot[0]+.12, rot[1]-.10, rot[2]+.20)
            _cmu(f'TPG_RUB_CMU_Q{i}', (x,y,z), rot, M, broken=(i in (2,6,8)))

    if detail >= 1:
        anchor_slabs = [
            ((-.35,.20,1.08), 1.70,1.05,.18, (.22,-.30,.40)),
            ((1.18,-.48,.68), 1.35,.82,.16, (-.32,.24,-.82)),
            ((-1.42,.82,.54), 1.12,.76,.15, (.28,.18,1.08)),
            ((.32,-1.45,.40), .95,.66,.14, (-.16,.34,.55)),
        ]
        if detail == 1:
            anchor_slabs = anchor_slabs[:2]
        for i,(loc,L,W,T,rot) in enumerate(anchor_slabs):
            if variant == 'destroyed':
                loc=(loc[0]*1.06,loc[1]*1.08,loc[2]*.74)
                rot=(rot[0]+.12,rot[1]-.10,rot[2]+.18)
            _fractured_slab(f'TPG_RUB_FRACTURED_SLAB_Q{i}',loc,L,W,T,rot,M['concrete2'],M['aggregate'],rng)
            # Rebar emerges from the broken edge, visually tying the steel to concrete.
            bars = 3 if detail == 2 and i < 2 else 1
            for k in range(bars):
                edge_local=(L*(.40+rng.uniform(-.05,.05)), W*(-.22+k*.18), rng.uniform(-.015,.045))
                p=_local(loc,edge_local,rot)
                qend=p + Euler(rot,'XYZ').to_matrix() @ Vector((rng.uniform(.28,.58),rng.uniform(-.12,.12),rng.uniform(.08,.32)))
                rebar(f'TPG_RUB_ANCHOR_REBAR_{i}_{k}',tuple(p),tuple(qend),M['rust'],rng.uniform(.016,.023))

    _delete_prefix('TPG_RUB_METAL_')
    if detail >= 1:
        beams = [
            ((-.10,.10,.94), 2.55, (.14,-.34,.38), M['rust']),
            ((.55,-.35,.68), 1.95, (-.22,.28,-1.00), M['steel']),
            ((-1.15,.70,.50), 1.55, (.10,.18,.95), M['rust']),
        ]
        for i,(loc,L,rot,mat) in enumerate(beams[:3 if detail==2 else 2]):
            if variant == 'destroyed':
                loc = (loc[0]*1.06, loc[1]*1.08, loc[2]*.74)
            _ibeam(f'TPG_RUB_IBEAM_Q{i}', loc, L, rot, mat)

        sheets = [
            ((-1.75,-.95,.30), 1.25,.52,(.18,-.42,.35),M['galv']),
            ((1.45,.68,.52), 1.05,.46,(-.35,.20,-.72),M['rust']),
            ((.30,-1.35,.38), .92,.42,(.26,.30,1.10),M['galv']),
        ]
        for i,(loc,L,W,rot,mat) in enumerate(sheets[:3 if detail==2 else 2]):
            if variant == 'destroyed':
                loc = (loc[0]*1.06, loc[1]*1.08, loc[2]*.75)
            _corrugated(f'TPG_RUB_SHEET_Q{i}', loc, L, W, rot, mat, bend=.10 if i==0 else .07)

    if detail >= 1:
        cage_z = .44 if variant == 'intact' else .31
        for i in range(6 if detail==2 else 3):
            y = -.38 + i*.13
            rebar(f'TPG_RUB_CAGE_LONG_{i}', (-.88,y,cage_z), (.82,y+.08,cage_z+rng.uniform(.04,.17)), M['rust'], .018)
        if detail == 2:
            for i in range(4):
                x = -.62 + i*.38
                rebar(f'TPG_RUB_CAGE_CROSS_{i}', (x,-.55,cage_z+.03), (x+.05,.42,cage_z+.12), M['rust_dark'], .017)

    if detail == 2:
        _delete_prefix('TPG_RUB_TRASH_')
        for i, loc in enumerate([(-2.35,-1.35,.06),(2.20,-1.20,.05),(-1.90,1.58,.07)]):
            _bag(f'TPG_RUB_BAG_Q{i}', loc, (.18,.13,.07), (rng.uniform(-.4,.4),rng.uniform(-.4,.4),rng.uniform(0,math.tau)), M['black'])
        for i, loc in enumerate([(2.35,.55,.06),(-2.20,.65,.05),(.55,-2.18,.06),(1.72,1.55,.07)]):
            cyl(f'TPG_RUB_CAN_Q{i}', loc, .032, .12, M['white'] if i%2 else M['blue'],
                rot=(rng.uniform(-1.2,1.2),rng.uniform(-1.2,1.2),rng.uniform(0,math.tau)), verts=8)
        cable('TPG_RUB_BLUE_CABLE_Q', [(-1.45,-1.05,.12),(-.75,-1.42,.10),(.05,-1.20,.16),(.80,-1.55,.08)], M['blue'], .014, 1)

    for o in list(bpy.context.scene.objects):
        _box_uv(o)
    _batch_visual_by_material()
    for o in bpy.context.scene.objects:
        ensure_uv(o)

    bpy.context.scene['TPG_quality_pass'] = 'reference-driven-v1.2'
    bpy.context.scene['TPG_nominal_footprint_m'] = '6.10 x 6.10'
