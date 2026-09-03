import bpy, math, os, random, zlib
from pathlib import Path
from mathutils import Vector, Euler
import numpy as np

WORK = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
TEXDIR = WORK / "edm-artifacts" / "Textures"
TEXDIR.mkdir(parents=True, exist_ok=True)

from materials.materials import build_material_descriptions
from materials.material_tools import createEdmNodeGroup
from enums import NodeSocketInDefaultEnum
from objects_custom_props import get_edm_props

MAT_DESCS = build_material_descriptions()
MATS = {}


def _tex(name, base, variation=.06, streak=False, mottled=False, size=1024, kind="generic"):
    path = TEXDIR / (name + ".png")
    if path.exists():
        return path

    seed = zlib.crc32(name.encode("utf-8")) & 0xffffffff
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    x = xx / max(1.0, float(size - 1))
    y = yy / max(1.0, float(size - 1))

    fine = (rng.random((size, size)).astype(np.float32) - .5) * variation
    low = (
        .025*np.sin(x*31.0 + (seed % 37)) +
        .020*np.sin(y*23.0 + (seed % 53)) +
        .014*np.sin((x+y)*47.0 + (seed % 19))
    ).astype(np.float32)
    n = fine + low

    if streak:
        n += (.020*np.sin(y*180.0 + x*11.0) + .009*np.sin(y*430.0 + x*29.0)).astype(np.float32)
    if mottled:
        n += (.028*np.sin(x*71.0)*np.sin(y*57.0) + .018*np.sin((x+y)*93.0)).astype(np.float32)

    rgb = np.empty((size, size, 3), dtype=np.float32)
    rgb[..., 0] = base[0] + n
    rgb[..., 1] = base[1] + n
    rgb[..., 2] = base[2] + n

    speck = rng.random((size, size)).astype(np.float32)

    if kind in ("concrete", "fracture"):
        pores = speck < (.026 if kind == "concrete" else .050)
        chips = (speck >= .050) & (speck < (.073 if kind == "fracture" else .060))
        rgb[pores] *= rng.uniform(.38, .72, size=(int(pores.sum()), 1)).astype(np.float32)
        if chips.any():
            chip_shift = rng.uniform(-.14, .12, size=(int(chips.sum()), 1)).astype(np.float32)
            rgb[chips] += chip_shift
        crack_field = np.abs(
            np.sin(x*39.0 + y*61.0 + (seed % 17)) +
            .62*np.sin(x*83.0 - y*31.0 + (seed % 29))
        )
        cracks = crack_field < (.026 if kind == "concrete" else .040)
        rgb[cracks] *= .58
        if kind == "fracture":
            stones = rng.random((size, size))
            dark = stones < .035
            light = (stones >= .035) & (stones < .065)
            rgb[dark] = rgb[dark]*.45 + np.array([.10,.095,.085], dtype=np.float32)
            rgb[light] = rgb[light]*.55 + np.array([.34,.33,.29], dtype=np.float32)

    elif kind == "cmu":
        pores = speck < .090
        pinholes = (speck >= .090) & (speck < .125)
        rgb[pores] *= rng.uniform(.28, .64, size=(int(pores.sum()), 1)).astype(np.float32)
        rgb[pinholes] += rng.uniform(.035, .12, size=(int(pinholes.sum()), 1)).astype(np.float32)
        aggregate = .035*np.sin(x*560.0 + y*90.0) * np.sin(y*430.0)
        rgb += aggregate[...,None].astype(np.float32)

    elif kind == "brick":
        clay = (.050*np.sin(x*47.0) + .025*np.sin(y*137.0+x*19.0)).astype(np.float32)
        rgb[...,0] += clay
        rgb[...,1] += clay*.38
        rgb[...,2] += clay*.20
        pits = speck < .060
        pale = (speck >= .060) & (speck < .078)
        rgb[pits] *= rng.uniform(.34,.70,size=(int(pits.sum()),1)).astype(np.float32)
        rgb[pale] += np.array([.10,.075,.055],dtype=np.float32)

    elif kind == "rebar":
        # Dark oxidized steel: nearly black iron base with brown/red oxidation,
        # longitudinal weathering and small pits. Never flat pure black.
        longitudinal = (.028*np.sin(y*260.0 + x*9.0) + .014*np.sin(y*710.0)).astype(np.float32)
        rgb += longitudinal[...,None]
        oxide = (np.maximum(0, np.sin(x*63.0 + y*17.0))*0.055).astype(np.float32)
        rgb[...,0] += oxide
        rgb[...,1] += oxide*.26
        rgb[...,2] -= oxide*.22
        pits = speck < .055
        rgb[pits] *= rng.uniform(.28,.65,size=(int(pits.sum()),1)).astype(np.float32)

    elif kind == "fines":
        grains = speck
        dark = grains < .090
        light = (grains >= .090) & (grains < .145)
        rgb[dark] *= rng.uniform(.42,.76,size=(int(dark.sum()),1)).astype(np.float32)
        rgb[light] += rng.uniform(.03,.11,size=(int(light.sum()),1)).astype(np.float32)

    elif kind == "metal":
        brushed = (.020*np.sin(y*520.0) + .010*np.sin(y*1030.0 + x*17.0)).astype(np.float32)
        rgb += brushed[...,None]

    elif kind == "rust":
        oxide = (.055*np.maximum(0,np.sin(y*47.0+x*13.0)) + .030*np.sin(y*137.0)).astype(np.float32)
        rgb[...,0] += oxide
        rgb[...,1] -= np.maximum(0,oxide)*.45
        rgb[...,2] -= np.maximum(0,oxide)*.72
        pits = speck < .045
        rgb[pits] *= rng.uniform(.30,.72,size=(int(pits.sum()),1)).astype(np.float32)

    elif kind == "wood":
        grain = (.040*np.sin(y*230.0+x*9.0) + .018*np.sin(y*770.0)).astype(np.float32)
        rgb[...,0] += grain
        rgb[...,1] += grain*.62
        rgb[...,2] += grain*.30

    elif kind == "soot":
        rgb *= (.80 + .20*np.maximum(0,np.sin(x*41.0+y*23.0)))[...,None].astype(np.float32)

    np.clip(rgb, 0.0, 1.0, out=rgb)
    rgba = np.empty((size, size, 4), dtype=np.float32)
    rgba[..., :3] = rgb
    rgba[..., 3] = 1.0

    img = bpy.data.images.new(name, width=size, height=size, alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.update()
    img.filepath_raw = str(path)
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    return path


def _roughmet(name, rough, metal, size):
    path = TEXDIR / (name + "_RoughMet.png")
    if path.exists():
        return path
    rm_size = 1024 if size >= 2048 else 512
    seed = zlib.crc32((name+"_rmo").encode("utf-8")) & 0xffffffff
    rng = np.random.default_rng(seed)
    rnoise = (rng.random((rm_size,rm_size)).astype(np.float32)-.5)
    rough_map = np.clip(rough + rnoise*.12, .02, .99)
    metal_map = np.clip(metal + rnoise*(.055 if metal > 0 else .008), 0.0, 1.0)
    rgba = np.ones((rm_size,rm_size,4),dtype=np.float32)
    rgba[...,0] = 1.0
    rgba[...,1] = rough_map
    rgba[...,2] = metal_map
    img=bpy.data.images.new(name+"_RoughMet",width=rm_size,height=rm_size,alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.update()
    img.filepath_raw=str(path)
    img.file_format='PNG'
    img.save()
    bpy.data.images.remove(img)
    return path


def edm_mat(name,color,rough=.82,metal=.0,variation=.05,streak=False,mottled=False,size=1024,kind="generic"):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    m.node_tree.nodes.clear()
    group=createEdmNodeGroup("EDM_Default_Material",m)
    group.post_init(MAT_DESCS["EDM_Default_Material"])
    group.name="Group"

    albedo=_tex(name,color,variation,streak,mottled,size,kind)
    tex=m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image=bpy.data.images.load(str(albedo),check_existing=True)
    m.node_tree.links.new(tex.outputs["Color"],group.inputs[NodeSocketInDefaultEnum.BASE_COLOR])

    rmo_path=_roughmet(name,rough,metal,size)
    rmo=m.node_tree.nodes.new("ShaderNodeTexImage")
    rmo.image=bpy.data.images.load(str(rmo_path),check_existing=True)
    rmo.image.colorspace_settings.name='Non-Color'
    m.node_tree.links.new(rmo.outputs['Color'],group.inputs[NodeSocketInDefaultEnum.ROUGH_METAL])
    return m


def mats():
    if MATS:
        return MATS
    MATS.update({
      'concrete':edm_mat('TPG_RUB500_Concrete',(.41,.40,.37),.95,0,.115,False,True,2048,'concrete'),
      'concrete2':edm_mat('TPG_RUB500_ConcreteLight',(.54,.53,.49),.93,0,.095,False,True,2048,'concrete'),
      'aggregate':edm_mat('TPG_RUB500_FractureAggregate',(.28,.275,.255),.98,0,.145,False,True,2048,'fracture'),
      'cmu':edm_mat('TPG_RUB500_CMU',(.47,.465,.43),.97,0,.12,False,True,2048,'cmu'),
      'brick':edm_mat('TPG_RUB500_Brick',(.39,.145,.075),.94,0,.10,True,True,2048,'brick'),
      'fines':edm_mat('TPG_RUB500_DebrisFines',(.225,.21,.185),.99,0,.15,False,True,2048,'fines'),
      'rebar':edm_mat('TPG_RUB500_RebarDarkRust',(.095,.050,.032),.89,.48,.09,True,True,2048,'rebar'),
      'rust':edm_mat('TPG_RUB500_RustSteel',(.205,.070,.027),.87,.42,.10,True,True,1024,'rust'),
      'rust_dark':edm_mat('TPG_RUB500_RustDark',(.085,.042,.026),.91,.39,.09,True,True,1024,'rebar'),
      'steel':edm_mat('TPG_RUB500_DullSteel',(.22,.225,.215),.55,.76,.055,True,False,1024,'metal'),
      'galv':edm_mat('TPG_RUB500_Galvanized',(.45,.47,.47),.46,.72,.055,True,False,1024,'metal'),
      'pipe':edm_mat('TPG_RUB500_DirtyPipe',(.265,.275,.255),.78,.30,.075,True,True,1024,'metal'),
      'black':edm_mat('TPG_RUB500_BlackTrash',(.035,.037,.032),.92,.01,.07,True,False,1024,'generic'),
      'blue':edm_mat('TPG_RUB500_BluePlastic',(.025,.145,.255),.72,.0,.065,True,False,1024,'generic'),
      'white':edm_mat('TPG_RUB500_DirtyWhite',(.62,.60,.54),.89,.0,.085,True,True,1024,'generic'),
      'yellow':edm_mat('TPG_RUB500_FadedYellow',(.43,.30,.040),.80,.01,.07,True,False,1024,'generic'),
      'wood':edm_mat('TPG_RUB500_BrokenWood',(.235,.135,.060),.93,.0,.10,True,True,1024,'wood'),
      'soot':edm_mat('TPG_RUB500_Soot',(.030,.026,.022),.98,.02,.09,True,True,1024,'soot'),
    })
    return MATS


def ensure_uv(o):
    if o.type!='MESH':
        return
    if not o.data.uv_layers:
        o.data.uv_layers.new(name='UVMap')


def cube(name,loc,scale,mat,rot=(0,0,0),bevel=.03,coll=False):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc,rotation=rot)
    o=bpy.context.object
    o.name=name
    o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel>0:
        mod=o.modifiers.new('broken_edges','BEVEL')
        mod.width=bevel
        mod.segments=1
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if mat:
        o.data.materials.append(mat)
    ensure_uv(o)
    if coll:
        get_edm_props(o).SPECIAL_TYPE='COLLISION_SHELL'
    return o


def cyl(name,loc,radius,depth,mat,rot=(0,0,0),verts=12,coll=False):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=radius,depth=depth,location=loc,rotation=rot)
    o=bpy.context.object
    o.name=name
    if mat:
        o.data.materials.append(mat)
    ensure_uv(o)
    if coll:
        get_edm_props(o).SPECIAL_TYPE='COLLISION_SHELL'
    return o


def irregular_chunk(name,loc,scale,mat,rng,verts=10):
    pts=[]
    sx,sy,sz=scale
    for i in range(verts):
        a=2*math.pi*i/verts
        rr=rng.uniform(.68,1.18)
        pts.append((math.cos(a)*sx*.5*rr,math.sin(a)*sy*.5*rr,rng.uniform(-.28,.22)*sz))
    pts += [
        (rng.uniform(-.20,.20)*sx,rng.uniform(-.20,.20)*sy,sz*.56),
        (rng.uniform(-.20,.20)*sx,rng.uniform(-.20,.20)*sy,-sz*.46)
    ]
    top=len(pts)-2
    bot=len(pts)-1
    faces=[]
    for i in range(verts):
        j=(i+1)%verts
        faces += [(top,i,j),(bot,j,i)]
    mesh=bpy.data.meshes.new(name+'_mesh')
    mesh.from_pydata(pts,[],faces)
    mesh.update()
    mesh.uv_layers.new(name='UVMap')
    o=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(o)
    o.location=loc
    o.rotation_euler=(rng.uniform(-.58,.58),rng.uniform(-.58,.58),rng.uniform(0,math.tau))
    o.data.materials.append(mat)
    return o


def cable(name,pts,mat,radius=.018,res=1):
    c=bpy.data.curves.new(name+'_curve','CURVE')
    c.dimensions='3D'
    c.bevel_depth=radius
    c.bevel_resolution=res
    s=c.splines.new('BEZIER')
    s.bezier_points.add(len(pts)-1)
    for bp,p in zip(s.bezier_points,pts):
        bp.co=p
        bp.handle_left_type='AUTO'
        bp.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,c)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    bpy.context.view_layer.objects.active=o
    o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    ensure_uv(bpy.context.object)
    return bpy.context.object


def rebar(name,start,end,mat,r=.021):
    # Single ribbed rebar mesh: actual raised ribs and a subtle helical phase.
    a=Vector(start)
    b=Vector(end)
    d=b-a
    L=d.length
    if L <= .001:
        return None
    sides=10
    rings=max(6,min(30,int(L/.065)+2))
    verts=[]
    for i in range(rings+1):
        z=-L*.5 + L*(i/rings)
        rib=1.0 + (.14 if i%2==0 else 0.0)
        phase=i*.19
        for j in range(sides):
            ang=2*math.pi*j/sides + phase
            rr=r*rib
            verts.append((math.cos(ang)*rr,math.sin(ang)*rr,z))
    faces=[]
    for i in range(rings):
        for j in range(sides):
            nj=(j+1)%sides
            a0=i*sides+j
            a1=i*sides+nj
            b1=(i+1)*sides+nj
            b0=(i+1)*sides+j
            faces.append((a0,a1,b1,b0))
    faces.append(tuple(range(sides-1,-1,-1)))
    last=rings*sides
    faces.append(tuple(last+j for j in range(sides)))
    mesh=bpy.data.meshes.new(name+'_mesh')
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    mesh.uv_layers.new(name='UVMap')
    o=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(o)
    o.location=(a+b)*.5
    o.rotation_mode='QUATERNION'
    o.rotation_quaternion=d.to_track_quat('Z','Y')
    o.rotation_mode='XYZ'
    o.data.materials.append(mat)
    return o


def broken_pipe(name,loc,length,radius,mat,rng):
    rot=(rng.uniform(-1.0,1.0),rng.uniform(-1.0,1.0),rng.uniform(0,math.tau))
    cyl(name,loc,radius,length,mat,rot=rot,verts=16)
    axis = Euler(rot, 'XYZ').to_matrix() @ Vector((0.0,0.0,1.0))
    center = Vector(loc)
    for suffix,sign in (('A',1.0),('B',-1.0)):
        p = center + axis * (sign * (length*.5 + .002))
        cyl(name+'_HOLE_'+suffix,tuple(p),radius*.66,.016,mats()['black'],rot=rot,verts=16)


def mound_z(x,y,peak=1.35):
    r=math.sqrt((x/3.0)**2+(y/3.0)**2)
    return max(.04,peak*(1-r*r)*.92)


def add_dense_core(M, detail, variant, rng, peak):
    # Overlapping, partially buried mass. This is rubble/fines geometry, not a pad.
    core_count={2:34,1:20,0:10}[detail]
    for i in range(core_count):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.85)*2.25
        x=math.cos(a)*rr*rng.uniform(.78,1.08)
        y=math.sin(a)*rr*rng.uniform(.75,1.08)
        sx=rng.uniform(.72,1.42)
        sy=rng.uniform(.62,1.30)
        sz=rng.uniform(.34,.72)
        surf=mound_z(x,y,peak)
        z=max(-.16,surf*rng.uniform(.22,.52)-sz*.26)
        if variant=='destroyed':
            x*=1.05
            y*=1.06
            z*=.78
        mat=rng.choices([M['fines'],M['aggregate'],M['concrete']],[58,25,17])[0]
        irregular_chunk(f'TPG_RUB_CORE_{i:03d}',(x,y,z),(sx,sy,sz),mat,rng,verts=12)

    # Dense low rubble matrix and skirt fills visible voids while keeping an irregular terrain edge.
    small_count={2:190,1:92,0:42}[detail]
    for i in range(small_count):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.66)*3.05
        x=math.cos(a)*rr*rng.uniform(.82,1.05)
        y=math.sin(a)*rr*rng.uniform(.80,1.06)
        s=rng.uniform(.07,.24) * (1.0-.18*min(1,rr/3.0))
        sz=s*rng.uniform(.50,.90)
        z=max(-.09,mound_z(x,y,peak)*rng.uniform(.05,.34)-sz*.22)
        mat=rng.choices([M['fines'],M['aggregate'],M['concrete'],M['brick'],M['cmu']],[45,25,14,9,7])[0]
        irregular_chunk(f'TPG_RUB_FILL_{i:03d}',(x,y,z),(s*rng.uniform(.8,1.35),s*rng.uniform(.75,1.25),sz),mat,rng,verts=8)


def add_collision(M):
    cube('TPG_RUBBLE_COLL_CENTER',(0,0,.43),(4.45,4.30,.86),None,bevel=.28,coll=True)
    cube('TPG_RUBBLE_COLL_NORTH',(-.55,.95,.31),(3.25,2.35,.62),None,rot=(0,0,.20),bevel=.25,coll=True)
    cube('TPG_RUBBLE_COLL_SOUTH',(.8,-1.0,.27),(2.9,2.15,.54),None,rot=(0,0,-.28),bevel=.22,coll=True)


def build(variant='intact',detail=2):
    M=mats()
    rng=random.Random(500941 + detail*113 + (17 if variant=='destroyed' else 0))
    peak=1.56 if detail>=2 else (1.34 if detail==1 else 1.05)
    if variant=='destroyed':
        peak*=.78

    add_dense_core(M,detail,variant,rng,peak)

    count={2:260,1:120,0:46}[detail]
    for i in range(count):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.64)*2.95
        x=math.cos(a)*rr*rng.uniform(.82,1.07)
        y=math.sin(a)*rr*rng.uniform(.78,1.05)
        if variant=='destroyed':
            x*=rng.uniform(.96,1.14)
            y*=rng.uniform(.96,1.14)
        s=rng.uniform(.13,.48)*(1.0-.18*min(1,rr/3.0))
        sz=s*rng.uniform(.48,.92)
        z=max(-.07,mound_z(x,y,peak)*rng.uniform(.24,.82)-sz*.10)
        mat=rng.choices([M['concrete'],M['concrete2'],M['aggregate'],M['brick'],M['cmu']],[42,17,22,11,8])[0]
        if variant=='destroyed' and rng.random()<.12:
            mat=M['soot']
        irregular_chunk(
            f'TPG_RUB_CHUNK_{i:03d}',(x,y,z),
            (s*rng.uniform(.75,1.35),s*rng.uniform(.75,1.25),sz),
            mat,rng,verts=9 if detail<2 else 11
        )

    # Temporary slab set; the HQ pass replaces these with irregular fractured plates.
    slab_n={2:14,1:7,0:4}[detail]
    for i in range(slab_n):
        a=rng.uniform(0,math.tau)
        rr=rng.uniform(.15,2.15)
        x=math.cos(a)*rr
        y=math.sin(a)*rr
        z=max(.05,mound_z(x,y,peak)*rng.uniform(.38,.76))
        sx=rng.uniform(.60,1.30)
        sy=rng.uniform(.32,.86)
        sz=rng.uniform(.11,.21)
        cube(f'TPG_RUB_SLAB_{i:02d}',(x,y,z),(sx,sy,sz),M['concrete2'],
             rot=(rng.uniform(-.32,.32),rng.uniform(-.32,.32),rng.uniform(0,math.tau)),bevel=.035)

    # Loose rebar is kept mostly inside the mass; hero rebar is embedded in slabs in the HQ pass.
    rebar_n={2:28,1:13,0:5}[detail]
    for i in range(rebar_n):
        a0=rng.uniform(0,math.tau)
        rr=(rng.random()**.78)*2.35
        x=math.cos(a0)*rr
        y=math.sin(a0)*rr
        z=max(.02,mound_z(x,y,peak)*rng.uniform(.18,.66))
        L=rng.uniform(.35,1.05 if detail>=1 else .70)
        a=rng.uniform(0,math.tau)
        end=(x+math.cos(a)*L,y+math.sin(a)*L,z+rng.uniform(-.10,.34))
        rebar(f'TPG_RUB_REBAR_{i:02d}',(x,y,z),end,M['rebar'],rng.uniform(.014,.022))

    pipe_n={2:10,1:5,0:2}[detail]
    for i in range(pipe_n):
        x=rng.uniform(-2.15,2.15)
        y=rng.uniform(-2.15,2.15)
        z=max(.035,mound_z(x,y,peak)*rng.uniform(.12,.52))
        broken_pipe(f'TPG_RUB_PIPE_{i}',(x,y,z),rng.uniform(.42,1.05),rng.uniform(.055,.14),M['pipe'] if i%2 else M['rust'],rng)

    if detail>=1:
        for i in range(8 if detail==2 else 4):
            x=rng.uniform(-2.1,2.1)
            y=rng.uniform(-2.1,2.1)
            z=max(.06,mound_z(x,y,peak)*rng.uniform(.30,.72))
            cube(f'TPG_RUB_METAL_{i}',(x,y,z),(rng.uniform(.55,1.25),rng.uniform(.08,.18),rng.uniform(.045,.09)),M['galv'] if i%3 else M['rust'],
                 rot=(rng.uniform(-.45,.45),rng.uniform(-.45,.45),rng.uniform(0,math.tau)),bevel=.015)
        for i in range(8 if detail==2 else 3):
            x=rng.uniform(-2.2,2.2)
            y=rng.uniform(-2.2,2.2)
            z=max(.035,mound_z(x,y,peak)*rng.uniform(.16,.50))
            cube(f'TPG_RUB_WOOD_{i}',(x,y,z),(rng.uniform(.55,1.15),rng.uniform(.065,.12),rng.uniform(.055,.105)),M['wood'],
                 rot=(rng.uniform(-.38,.38),rng.uniform(-.38,.38),rng.uniform(0,math.tau)),bevel=.010)

    if detail==2:
        for i in range(10):
            x=rng.uniform(-1.95,1.95)
            y=rng.uniform(-1.95,1.95)
            z=max(.08,mound_z(x,y,peak)*rng.uniform(.36,.68))
            pts=[
                (x,y,z),
                (x+rng.uniform(.22,.55),y+rng.uniform(-.42,.42),z+rng.uniform(-.10,.15)),
                (x+rng.uniform(.48,.90),y+rng.uniform(-.58,.58),max(.025,z+rng.uniform(-.28,.06)))
            ]
            cable(f'TPG_RUB_WIRE_{i}',pts,M['black'] if i%3 else M['rebar'],rng.uniform(.009,.016),1)

    if variant=='destroyed' and detail>=1:
        for i in range(20 if detail==2 else 9):
            a=rng.uniform(0,math.tau)
            rr=rng.uniform(2.45,3.40)
            x=math.cos(a)*rr
            y=math.sin(a)*rr
            irregular_chunk(
                f'TPG_RUB_BLAST_{i}',(x,y,rng.uniform(-.03,.09)),
                (rng.uniform(.14,.36),rng.uniform(.14,.38),rng.uniform(.09,.22)),
                M['soot'] if i%2 else M['concrete'],rng,8
            )

    add_collision(M)
    for o in bpy.context.scene.objects:
        ensure_uv(o)
    bpy.context.scene['TPG_asset']='TPG Rubble Pile 20ft V1 HQ500'
    bpy.context.scene['TPG_variant']=variant
    bpy.context.scene['TPG_detail']=detail
