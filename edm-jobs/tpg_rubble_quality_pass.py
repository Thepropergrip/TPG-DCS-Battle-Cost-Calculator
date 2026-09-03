import bpy, math, random
from mathutils import Vector, Euler

from tpg_rubble_common import mats, cube, cyl, rebar, cable, ensure_uv, mound_z, irregular_chunk


def _local(center, offset, rot):
    return Vector(center) + Euler(rot, 'XYZ').to_matrix() @ Vector(offset)


def _delete_prefix(prefix):
    for o in list(bpy.context.scene.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)


def _box_uv(o, scale=.62):
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
    # True hollow-core CMU made from five wall pieces, with porous CMU material.
    L, W, H = (.40, .20, .20) if not broken else (.33, .18, .16)
    t = .034
    parts = [
        ((0, +(W-t)/2, 0), (L, t, H)),
        ((0, -(W-t)/2, 0), (L, t, H)),
        ((+(L-t)/2, 0, 0), (t, W-2*t, H)),
        ((-(L-t)/2, 0, 0), (t, W-2*t, H)),
        ((0, 0, 0), (t, W-2*t, H)),
    ]
    for i, (off, dims) in enumerate(parts):
        p = _local(loc, off, rot)
        cube(f'{name}_{i}', p, dims, M['cmu'], rot=rot, bevel=.007)


def _brick(name, loc, rot, M, half=False, chipped=False):
    L=.205 if not half else .105
    W=.095
    H=.060
    if chipped:
        L*=.82
        W*=.88
    cube(name,loc,(L,W,H),M['brick'],rot=rot,bevel=.009 if chipped else .006)


def _ibeam(name, loc, length, rot, mat):
    flange_w, flange_t, web_h, web_t = .24, .040, .24, .038
    parts = [
        ((0, 0, +(web_h-flange_t)/2), (length, flange_w, flange_t)),
        ((0, 0, -(web_h-flange_t)/2), (length, flange_w, flange_t)),
        ((0, 0, 0), (length, web_t, web_h-2*flange_t)),
    ]
    for i, (off, dims) in enumerate(parts):
        cube(f'{name}_{i}', _local(loc, off, rot), dims, mat, rot=rot, bevel=.009)


def _fractured_slab(name, loc, length, width, thick, rot, face_mat, fracture_mat, rng):
    # Jagged slab; broad faces use aged concrete, broken edge ring uses exposed aggregate.
    base = [
        (-.50,-.40),(-.28,-.52),(-.02,-.47),(.22,-.54),(.49,-.32),
        (.54,-.04),(.48,.22),(.31,.49),(.02,.53),(-.27,.47),(-.52,.20),
    ]
    ring = []
    for x,y in base:
        ring.append((
            x*length + rng.uniform(-.050,.050)*length,
            y*width + rng.uniform(-.050,.050)*width,
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
    _box_uv(obj,.72)
    return obj


def _corrugated(name, loc, length, width, rot, mat, bend=.08, ribs=13):
    nx, ny = 5, ribs + 1
    verts = []
    for ix in range(nx):
        u = ix / (nx - 1)
        x = (u - .5) * length
        curve = ((u - .5) ** 2 - .08) * bend
        for iy in range(ny):
            v = iy / (ny - 1)
            y = (v - .5) * width
            z = .020 * math.sin(v * ribs * math.pi * 2) + curve
            # torn-looking edge distortion
            if iy in (0,ny-1):
                z += .018*math.sin(ix*2.7 + iy)
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
    _box_uv(obj, .62)
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


def _add_masonry_field(M, rng, variant, detail):
    # Readable CMU and fired-brick debris, concentrated inside the pile rather than floating at edges.
    cmu_count={2:24,1:10,0:3}[detail]
    for i in range(cmu_count):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.76)*2.35
        x=math.cos(a)*rr
        y=math.sin(a)*rr
        z=max(.02,mound_z(x,y,1.45)*rng.uniform(.18,.64))
        rot=(rng.uniform(-.55,.55),rng.uniform(-.55,.55),rng.uniform(0,math.tau))
        if variant=='destroyed':
            x*=1.06; y*=1.07; z*=.76
        _cmu(f'TPG_RUB_CMU_Q{i}',(x,y,z),rot,M,broken=(i%4==1 or i%7==0))

    brick_count={2:52,1:20,0:6}[detail]
    for i in range(brick_count):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.68)*2.65
        x=math.cos(a)*rr
        y=math.sin(a)*rr
        z=max(-.01,mound_z(x,y,1.38)*rng.uniform(.06,.42))
        rot=(rng.uniform(-.65,.65),rng.uniform(-.65,.65),rng.uniform(0,math.tau))
        if variant=='destroyed':
            x*=1.08; y*=1.08; z*=.72
        _brick(f'TPG_RUB_BRICK_Q{i}',(x,y,z),rot,M,half=(i%3==0),chipped=(i%4==0))

    chip_count={2:70,1:28,0:10}[detail]
    for i in range(chip_count):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.72)*2.90
        x=math.cos(a)*rr
        y=math.sin(a)*rr
        s=rng.uniform(.045,.13)
        z=max(-.04,mound_z(x,y,1.28)*rng.uniform(.02,.22)-s*.20)
        mat=M['brick'] if i%3==0 else (M['cmu'] if i%5==0 else M['aggregate'])
        irregular_chunk(f'TPG_RUB_MASONRY_CHIP_{i}',(x,y,z),(s*1.3,s,s*.65),mat,rng,7)


def _add_fractured_slab_field(M,rng,variant,detail):
    _delete_prefix('TPG_RUB_SLAB_')
    specs=[
        ((-.28,.18,1.02),1.72,1.00,.18,(.19,-.28,.38)),
        ((1.12,-.46,.70),1.34,.82,.16,(-.28,.21,-.76)),
        ((-1.30,.78,.58),1.18,.74,.15,(.27,.16,1.03)),
        ((.22,-1.36,.46),1.05,.68,.14,(-.14,.31,.52)),
        ((.86,.92,.78),1.20,.72,.17,(.34,-.12,1.42)),
        ((-1.58,-.64,.42),.96,.62,.14,(.18,.30,-1.18)),
        ((1.62,.24,.40),.92,.58,.13,(-.30,.25,.21)),
        ((-.62,1.52,.34),.88,.56,.12,(.25,-.18,.82)),
        ((.38,.08,.54),1.10,.68,.15,(-.22,.18,-.30)),
        ((-1.02,-1.28,.30),.84,.55,.12,(.16,.28,.94)),
        ((1.32,-1.30,.28),.78,.50,.11,(-.20,.24,-.56)),
        ((-1.92,.18,.24),.72,.46,.11,(.15,-.21,.18)),
        ((.08,1.86,.24),.70,.44,.10,(-.18,.20,1.10)),
        ((1.88,.90,.20),.66,.42,.10,(.12,.22,-.90)),
        ((-1.55,1.48,.20),.64,.40,.10,(-.20,.15,.44)),
        ((1.72,-.72,.22),.68,.43,.10,(.17,-.16,.66)),
    ]
    if detail==1:
        specs=specs[:8]
    elif detail==0:
        specs=specs[:4]

    for i,(loc,L,W,T,rot) in enumerate(specs):
        if variant=='destroyed':
            loc=(loc[0]*1.07,loc[1]*1.08,loc[2]*.73)
            rot=(rot[0]+.10,rot[1]-.09,rot[2]+.17)
        _fractured_slab(f'TPG_RUB_FRACTURED_SLAB_Q{i}',loc,L,W,T,rot,M['concrete2'],M['aggregate'],rng)

        # Ribbed rebar grows from the broken slab edge; most steel now has an obvious concrete origin.
        bars=4 if detail==2 and i<6 else (2 if detail>=1 else 1)
        for k in range(bars):
            side = 1 if (k%2==0) else -1
            edge_local=(side*L*(.38+rng.uniform(-.04,.06)), W*(-.28+k*.13), rng.uniform(-.02,.04))
            p=_local(loc,edge_local,rot)
            local_end=Vector((side*rng.uniform(.28,.66),rng.uniform(-.14,.14),rng.uniform(.05,.30)))
            q=p + Euler(rot,'XYZ').to_matrix() @ local_end
            rebar(f'TPG_RUB_ANCHOR_REBAR_{i}_{k}',tuple(p),tuple(q),M['rebar'],rng.uniform(.015,.022))


def _add_hero_metal(M,rng,variant,detail):
    _delete_prefix('TPG_RUB_METAL_')
    if detail < 1:
        return
    beams=[
        ((-.10,.10,.88),2.25,(.12,-.30,.36),M['rust']),
        ((.58,-.30,.64),1.74,(-.20,.25,-.94),M['steel']),
        ((-1.10,.66,.48),1.46,(.09,.16,.92),M['rust']),
        ((1.22,.78,.38),1.06,(.18,-.22,.44),M['steel']),
    ]
    for i,(loc,L,rot,mat) in enumerate(beams[:4 if detail==2 else 2]):
        if variant=='destroyed':
            loc=(loc[0]*1.06,loc[1]*1.07,loc[2]*.73)
        _ibeam(f'TPG_RUB_IBEAM_Q{i}',loc,L,rot,mat)

    sheets=[
        ((-1.72,-.92,.28),1.18,.50,(.16,-.39,.34),M['galv']),
        ((1.42,.66,.48),1.02,.45,(-.32,.18,-.69),M['rust']),
        ((.32,-1.30,.36),.88,.40,(.24,.28,1.08),M['galv']),
        ((-1.10,1.30,.32),.82,.38,(-.20,.22,.36),M['rust']),
    ]
    for i,(loc,L,W,rot,mat) in enumerate(sheets[:4 if detail==2 else 2]):
        if variant=='destroyed':
            loc=(loc[0]*1.06,loc[1]*1.08,loc[2]*.74)
        _corrugated(f'TPG_RUB_SHEET_Q{i}',loc,L,W,rot,mat,bend=.10 if i==0 else .07)


def _add_rebar_cages(M,rng,variant,detail):
    if detail < 1:
        return
    cage_z=.40 if variant=='intact' else .28
    # Two collapsed reinforcement mats integrated into the pile.
    for cage in range(2 if detail==2 else 1):
        ox=-.65 + cage*1.15
        oy=-.24 + cage*.58
        angle=.18 if cage==0 else -.42
        for i in range(7 if detail==2 else 4):
            y=-.36+i*.12
            p=Vector((-.72,y,0))
            q=Vector((.72,y+rng.uniform(-.04,.05),rng.uniform(.02,.13)))
            R=Euler((0,0,angle),'XYZ').to_matrix()
            p=R@p + Vector((ox,oy,cage_z))
            q=R@q + Vector((ox,oy,cage_z))
            rebar(f'TPG_RUB_CAGE_{cage}_LONG_{i}',tuple(p),tuple(q),M['rebar'],.017)
        for i in range(5 if detail==2 else 3):
            x=-.58+i*.29
            p=Vector((x,-.44,.03))
            q=Vector((x+rng.uniform(-.03,.04),.44,.10))
            R=Euler((0,0,angle),'XYZ').to_matrix()
            p=R@p + Vector((ox,oy,cage_z))
            q=R@q + Vector((ox,oy,cage_z))
            rebar(f'TPG_RUB_CAGE_{cage}_CROSS_{i}',tuple(p),tuple(q),M['rebar'],.016)


def _add_small_clutter(M,rng,variant,detail):
    if detail != 2:
        return
    # Sparse trash accents only; construction material remains visually dominant.
    for i,loc in enumerate([(-2.30,-1.32,.045),(2.16,-1.15,.045),(-1.82,1.55,.05)]):
        _bag(f'TPG_RUB_BAG_Q{i}',loc,(.17,.12,.06),(rng.uniform(-.4,.4),rng.uniform(-.4,.4),rng.uniform(0,math.tau)),M['black'])
    for i,loc in enumerate([(2.28,.52,.045),(-2.12,.62,.04),(.58,-2.10,.045),(1.66,1.50,.05)]):
        cyl(f'TPG_RUB_CAN_Q{i}',loc,.030,.105,M['white'] if i%2 else M['blue'],
            rot=(rng.uniform(-1.2,1.2),rng.uniform(-1.2,1.2),rng.uniform(0,math.tau)),verts=10)
    cable('TPG_RUB_BLUE_CABLE_Q',[(-1.38,-1.00,.10),(-.70,-1.34,.09),(.02,-1.14,.13),(.74,-1.46,.07)],M['blue'],.012,1)


def quality_pass(variant='intact', detail=2):
    M=mats()
    rng=random.Random(542191 + detail*61 + (777 if variant=='destroyed' else 0))

    _delete_prefix('TPG_RUB_BLOCK_')
    _add_masonry_field(M,rng,variant,detail)
    _add_fractured_slab_field(M,rng,variant,detail)
    _add_hero_metal(M,rng,variant,detail)
    _add_rebar_cages(M,rng,variant,detail)
    _add_small_clutter(M,rng,variant,detail)

    # Apply real box-projected UV coordinates to every mesh before batching.
    for o in list(bpy.context.scene.objects):
        _box_uv(o)

    # Keep the ED scene compact: hundreds of fragments become one draw batch per material.
    _batch_visual_by_material()
    for o in bpy.context.scene.objects:
        ensure_uv(o)

    bpy.context.scene['TPG_quality_pass']='reference-driven-HQ500-v2.0'
    bpy.context.scene['TPG_nominal_footprint_m']='6.10 x 6.10'
    bpy.context.scene['TPG_texture_standard']='2K hero materials / 1K secondary / high-res RoughMet'
