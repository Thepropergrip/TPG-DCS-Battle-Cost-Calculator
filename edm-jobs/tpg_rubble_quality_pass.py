import bpy, math, random
from mathutils import Vector, Euler

from tpg_rubble_common import (
    mats, cube, cyl, rebar, bent_rebar, cable, ensure_uv, mound_z, irregular_chunk
)


def _local(center, offset, rot):
    return Vector(center) + Euler(rot, 'XYZ').to_matrix() @ Vector(offset)


def _delete_prefix(prefix):
    for o in list(bpy.context.scene.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)


def _uv_scale_for(o):
    if o.type!='MESH' or not o.data.materials:
        return .56
    names=" ".join(m.name for m in o.data.materials if m)
    if "Brick" in names:
        return 4.4
    if "CMU" in names:
        return 2.8
    if "Rebar" in names or "RustDark" in names:
        return 3.4
    if "RoughConcrete" in names:
        return .72
    if "ConcreteDebris" in names or "RubbleBase" in names:
        return .55
    if "RustMetal" in names or "DullSteel" in names or "Galvanized" in names:
        return 1.25
    if "BrokenWood" in names:
        return 1.6
    return .72


def _box_uv(o, scale=None):
    if o.type!='MESH':
        return
    if scale is None:
        scale=_uv_scale_for(o)
    mesh=o.data
    uv=mesh.uv_layers.active or mesh.uv_layers.new(name='UVMap')
    mesh.update()
    for poly in mesh.polygons:
        n=poly.normal
        ax,ay,az=abs(n.x),abs(n.y),abs(n.z)
        for li in poly.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co
            if az>=ax and az>=ay:
                uv.data[li].uv=(co.x*scale,co.y*scale)
            elif ay>=ax:
                uv.data[li].uv=(co.x*scale,co.z*scale)
            else:
                uv.data[li].uv=(co.y*scale,co.z*scale)


def _cmu(name,loc,rot,M,broken=False):
    # Real hollow-core CMU geometry with open voids and thin webs.
    L,W,H=(.40,.20,.20) if not broken else (.31,.17,.16)
    t=.032
    parts=[
        ((0, +(W-t)/2, 0),(L,t,H)),
        ((0, -(W-t)/2, 0),(L,t,H)),
        ((+(L-t)/2,0,0),(t,W-2*t,H)),
        ((-(L-t)/2,0,0),(t,W-2*t,H)),
        ((0,0,0),(t,W-2*t,H)),
    ]
    for i,(off,dims) in enumerate(parts):
        p=_local(loc,off,rot)
        cube(f'{name}_{i}',p,dims,M['cmu'],rot=rot,bevel=.006)


def _brick(name,loc,rot,M,half=False,chipped=False):
    L=.203 if not half else .103
    W=.095
    H=.060
    if chipped:
        L*=.80
        W*=.86
    cube(name,loc,(L,W,H),M['brick'],rot=rot,bevel=.006 if not chipped else .010)


def _ibeam(name,loc,length,rot,mat):
    fw,ft,wh,wt=.22,.036,.22,.034
    parts=[
        ((0,0, +(wh-ft)/2),(length,fw,ft)),
        ((0,0, -(wh-ft)/2),(length,fw,ft)),
        ((0,0,0),(length,wt,wh-2*ft)),
    ]
    for i,(off,dims) in enumerate(parts):
        cube(f'{name}_{i}',_local(loc,off,rot),dims,mat,rot=rot,bevel=.008)


def _fractured_slab(name,loc,length,width,thick,rot,face_mat,fracture_mat,rng):
    # Non-rectangular, asymmetric fracture outline with separate aggregate edge material.
    points=12
    ring=[]
    for i in range(points):
        a=2*math.pi*i/points
        # Slightly rectangular bias without clean straight construction edges.
        ca=math.cos(a)
        sa=math.sin(a)
        denom=max(abs(ca)/.50,abs(sa)/.46,1e-5)
        rr=1.0/denom
        x=ca*rr*length*.50*rng.uniform(.83,1.12)
        y=sa*rr*width*.50*rng.uniform(.82,1.13)
        ring.append((x,y))

    n=len(ring)
    verts=[(x,y,+thick*.5) for x,y in ring]+[(x,y,-thick*.5) for x,y in ring]
    faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
    for i in range(n):
        j=(i+1)%n
        faces.append((i,j,n+j,n+i))

    mesh=bpy.data.meshes.new(name+'_mesh')
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    mesh.materials.append(face_mat)
    mesh.materials.append(fracture_mat)
    for idx,p in enumerate(mesh.polygons):
        p.material_index=0 if idx<2 else 1

    o=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(o)
    o.location=loc
    o.rotation_euler=rot
    _box_uv(o,.74)
    return o


def _corrugated(name,loc,length,width,rot,mat,bend=.08,ribs=15):
    nx=6
    ny=ribs+1
    verts=[]
    for ix in range(nx):
        u=ix/(nx-1)
        x=(u-.5)*length
        arc=((u-.5)**2-.08)*bend
        for iy in range(ny):
            v=iy/(ny-1)
            y=(v-.5)*width
            z=.017*math.sin(v*ribs*math.pi*2)+arc
            if iy in (0,ny-1):
                z += .018*math.sin(ix*2.9+iy*.6)
            verts.append((x,y,z))
    faces=[]
    for ix in range(nx-1):
        for iy in range(ny-1):
            a=ix*ny+iy
            faces.append((a,a+1,(ix+1)*ny+iy+1,(ix+1)*ny+iy))
    mesh=bpy.data.meshes.new(name+'_mesh')
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    o=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(o)
    o.location=loc
    o.rotation_euler=rot
    o.data.materials.append(mat)
    _box_uv(o,1.2)

    bpy.context.view_layer.objects.active=o
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    sol=o.modifiers.new('sheet_thickness','SOLIDIFY')
    sol.thickness=.010
    sol.offset=0
    bpy.ops.object.modifier_apply(modifier=sol.name)
    return o


def _bag(name,loc,scale,rot,mat):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1.0,location=loc,rotation=rot)
    o=bpy.context.object
    o.name=name
    o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    # Crush the bag silhouette so it reads as discarded construction trash.
    for v in o.data.vertices:
        if v.co.z>0:
            v.co.z*=.72
    o.data.materials.append(mat)
    _box_uv(o,1.8)
    return o


def _batch_visual_by_material():
    groups={}
    for o in list(bpy.context.scene.objects):
        if o.type!='MESH' or o.name.startswith('TPG_RUBBLE_COLL_'):
            continue
        if len(o.data.materials)!=1 or o.data.materials[0] is None:
            continue
        groups.setdefault(o.data.materials[0].name,[]).append(o)

    for mat_name,objs in groups.items():
        if len(objs)<2:
            continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active=objs[0]
        bpy.ops.object.join()
        joined=bpy.context.object
        safe=''.join(c if c.isalnum() else '_' for c in mat_name)
        joined.name='TPG_CIN4_BATCH_'+safe[-46:]
        ensure_uv(joined)


def _add_masonry(M,rng,variant,detail):
    cmu_n={2:48,1:20,0:6}[detail]
    for i in range(cmu_n):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.76)*2.38
        x=math.cos(a)*rr
        y=math.sin(a)*rr
        z=max(.00,mound_z(x,y,1.42)*rng.uniform(.12,.52))
        if variant=='destroyed':
            x*=1.06
            y*=1.08
            z*=.74
        rot=(rng.uniform(-.64,.64),rng.uniform(-.64,.64),rng.uniform(0,math.tau))
        _cmu(f'TPG_CIN4_CMU_{i}',(x,y,z),rot,M,broken=(i%4==1 or i%7==0 or i%11==0))

    brick_n={2:138,1:55,0:16}[detail]
    for i in range(brick_n):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.68)*2.72
        x=math.cos(a)*rr
        y=math.sin(a)*rr
        z=max(-.025,mound_z(x,y,1.34)*rng.uniform(.025,.34))
        if variant=='destroyed':
            x*=1.08
            y*=1.08
            z*=.72
        rot=(rng.uniform(-.75,.75),rng.uniform(-.75,.75),rng.uniform(0,math.tau))
        _brick(f'TPG_CIN4_BRICK_{i}',(x,y,z),rot,M,half=(i%3==0),chipped=(i%4==0 or i%9==0))

    chip_n={2:210,1:82,0:24}[detail]
    for i in range(chip_n):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.69)*2.95
        x=math.cos(a)*rr
        y=math.sin(a)*rr
        s=rng.uniform(.035,.115)
        z=max(-.05,mound_z(x,y,1.25)*rng.uniform(.01,.18)-s*.28)
        mat=rng.choices([M['aggregate'],M['brick'],M['cmu'],M['fines']],[55,22,12,11])[0]
        irregular_chunk(f'TPG_CIN4_MASONRY_CHIP_{i}',(x,y,z),(s*1.35,s,s*.66),mat,rng,7)


def _add_fractured_slabs(M,rng,variant,detail):
    _delete_prefix('TPG_RUB_SLAB_')
    count={2:30,1:13,0:5}[detail]
    for i in range(count):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.77)*2.20
        x=math.cos(a)*rr
        y=math.sin(a)*rr
        z=max(.08,mound_z(x,y,1.42)*rng.uniform(.25,.68))
        # Smaller than V2's large plates; many interlocked pieces make a denser collapsed structure.
        L=rng.uniform(.48,1.18 if detail==2 else .92)
        W=rng.uniform(.28,.72 if detail==2 else .58)
        T=rng.uniform(.10,.18)
        rot=(rng.uniform(-.42,.42),rng.uniform(-.42,.42),rng.uniform(0,math.tau))
        if variant=='destroyed':
            x*=1.06
            y*=1.08
            z*=.72
            rot=(rot[0]+.10,rot[1]-.08,rot[2]+.16)
        loc=(x,y,z)
        _fractured_slab(f'TPG_CIN4_FRACTURED_SLAB_{i}',loc,L,W,T,rot,M['concrete'],M['aggregate'],rng)

        bars=4 if detail==2 and i<16 else (2 if detail>=1 else 1)
        for k in range(bars):
            side=1 if k%2==0 else -1
            edge_local=(side*L*(.39+rng.uniform(-.04,.05)),
                        W*rng.uniform(-.34,.34),
                        rng.uniform(-.02,.04))
            p=_local(loc,edge_local,rot)
            R=Euler(rot,'XYZ').to_matrix()
            q1=p+R@Vector((side*rng.uniform(.16,.30),rng.uniform(-.08,.08),rng.uniform(.02,.12)))
            q2=q1+R@Vector((side*rng.uniform(.16,.36),rng.uniform(-.10,.10),rng.uniform(-.03,.16)))
            bent_rebar(f'TPG_CIN4_SLAB_REBAR_{i}_{k}',[tuple(p),tuple(q1),tuple(q2)],M['rebar'],rng.uniform(.014,.020))


def _add_reinforcement(M,rng,variant,detail):
    if detail<1:
        return
    cages=3 if detail==2 else 1
    for cage in range(cages):
        ox=(-.95,.20,.86)[cage]
        oy=(-.28,.62,-.82)[cage]
        oz=(.34,.46,.27)[cage] if variant=='intact' else (.25,.32,.20)[cage]
        angle=(.22,-.48,.71)[cage]

        longitudinal=8 if detail==2 else 5
        cross=6 if detail==2 else 4
        for i in range(longitudinal):
            y=-.40+i*(.80/max(1,longitudinal-1))
            R=Euler((0,0,angle),'XYZ').to_matrix()
            p=R@Vector((-.66,y,0))+Vector((ox,oy,oz))
            q=R@Vector((.66,y+rng.uniform(-.035,.035),rng.uniform(.02,.11)))+Vector((ox,oy,oz))
            rebar(f'TPG_CIN4_CAGE_{cage}_L_{i}',tuple(p),tuple(q),M['rebar'],.016)
        for i in range(cross):
            x=-.56+i*(1.12/max(1,cross-1))
            R=Euler((0,0,angle),'XYZ').to_matrix()
            p=R@Vector((x,-.46,.02))+Vector((ox,oy,oz))
            q=R@Vector((x+rng.uniform(-.03,.03),.46,.08))+Vector((ox,oy,oz))
            rebar(f'TPG_CIN4_CAGE_{cage}_X_{i}',tuple(p),tuple(q),M['rebar'],.015)

    # Short bent loose bars; no more long black "spider legs" radiating metres outside the pile.
    loose=24 if detail==2 else 10
    for i in range(loose):
        a=rng.uniform(0,math.tau)
        rr=rng.uniform(.55,2.30)
        x=math.cos(a)*rr
        y=math.sin(a)*rr
        z=max(.04,mound_z(x,y,1.35)*rng.uniform(.16,.48))
        ang=rng.uniform(0,math.tau)
        L=rng.uniform(.34,.78)
        p=(x,y,z)
        q=(x+math.cos(ang)*L*.55,y+math.sin(ang)*L*.55,z+rng.uniform(-.04,.16))
        r=(x+math.cos(ang+.18)*L,y+math.sin(ang+.18)*L,z+rng.uniform(-.06,.24))
        bent_rebar(f'TPG_CIN4_LOOSE_BAR_{i}',[p,q,r],M['rebar'],rng.uniform(.014,.020))


def _add_hero_metal(M,rng,variant,detail):
    _delete_prefix('TPG_RUB_METAL_')
    if detail<1:
        return

    beams=[
        ((-.22,.10,.72),1.72,(.12,-.26,.34),M['rust']),
        ((.62,-.36,.56),1.48,(-.18,.24,-.88),M['steel']),
        ((-1.10,.68,.42),1.28,(.09,.16,.91),M['rust']),
        ((1.08,.72,.34),1.02,(.17,-.20,.42),M['steel']),
        ((-.70,-1.10,.29),.96,(-.15,.24,-.38),M['rust']),
        ((1.42,-.42,.26),.88,(.21,.18,1.18),M['steel']),
    ]
    for i,(loc,L,rot,mat) in enumerate(beams[:6 if detail==2 else 3]):
        if variant=='destroyed':
            loc=(loc[0]*1.07,loc[1]*1.08,loc[2]*.72)
        _ibeam(f'TPG_CIN4_IBEAM_{i}',loc,L,rot,mat)

    sheets=[
        ((-1.56,-.88,.25),1.02,.46,(.15,-.36,.32),M['galv']),
        ((1.32,.62,.40),.92,.42,(-.29,.16,-.66),M['rust']),
        ((.34,-1.22,.31),.78,.38,(.22,.26,1.04),M['galv']),
        ((-1.08,1.22,.28),.76,.35,(-.18,.20,.34),M['rust']),
        ((1.58,-.82,.20),.70,.33,(.25,-.13,.82),M['galv']),
        ((.58,1.52,.22),.68,.32,(-.20,.17,-.44),M['rust']),
    ]
    for i,(loc,L,W,rot,mat) in enumerate(sheets[:6 if detail==2 else 3]):
        if variant=='destroyed':
            loc=(loc[0]*1.07,loc[1]*1.08,loc[2]*.72)
        _corrugated(f'TPG_CIN4_SHEET_{i}',loc,L,W,rot,mat,bend=.085 if i%2==0 else .060)


def _add_clutter(M,rng,detail):
    if detail!=2:
        return
    for i,loc in enumerate([(-2.22,-1.28,.04),(2.08,-1.10,.04),(-1.78,1.48,.045)]):
        _bag(f'TPG_CIN4_BAG_{i}',loc,(.16,.11,.055),
             (rng.uniform(-.4,.4),rng.uniform(-.4,.4),rng.uniform(0,math.tau)),M['black'])

    for i,loc in enumerate([(2.18,.50,.04),(-2.06,.59,.035),(.58,-2.02,.04),(1.58,1.42,.045),(-.22,2.02,.04)]):
        cyl(f'TPG_CIN4_CAN_{i}',loc,.028,.098,M['white'] if i%2 else M['blue'],
            rot=(rng.uniform(-1.1,1.1),rng.uniform(-1.1,1.1),rng.uniform(0,math.tau)),verts=12)

    cable('TPG_CIN4_BLUE_CABLE',
          [(-1.30,-.96,.10),(-.66,-1.28,.08),(.02,-1.08,.12),(.68,-1.36,.065)],
          M['blue'],.011,1)


def quality_pass(variant='intact',detail=2):
    M=mats()
    rng=random.Random(9542191+detail*71+(811 if variant=='destroyed' else 0))

    _delete_prefix('TPG_RUB_BLOCK_')
    _add_masonry(M,rng,variant,detail)
    _add_fractured_slabs(M,rng,variant,detail)
    _add_reinforcement(M,rng,variant,detail)
    _add_hero_metal(M,rng,variant,detail)
    _add_clutter(M,rng,detail)

    # Explicit box/projected UVs at physically useful scales for photo-based PBR.
    for o in list(bpy.context.scene.objects):
        _box_uv(o)

    # Draw-call reduction after the detail pass: keep multi-material fractured slabs separate,
    # batch all single-material rubble by material.
    _batch_visual_by_material()
    for o in bpy.context.scene.objects:
        ensure_uv(o)

    bpy.context.scene['TPG_quality_pass']='cinematic-V4-photoPBR-v1'
    bpy.context.scene['TPG_nominal_footprint_m']='6.10 x 6.10'
    bpy.context.scene['TPG_material_stack']='8K hero albedo + 4K hero normals + 4K secondary albedo + BC7 DDS/mips'
    bpy.context.scene['TPG_coexistence_id']='TPG_Rubble_Pile_20ft_Cinematic_V4'
