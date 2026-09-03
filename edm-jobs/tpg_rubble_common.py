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


def _new_edm_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    group = createEdmNodeGroup("EDM_Default_Material", m)
    group.post_init(MAT_DESCS["EDM_Default_Material"])
    group.name = "Group"
    return m, group


def _image_node(material, path, noncolor=False):
    if not Path(path).exists():
        raise RuntimeError(f"Required texture missing: {path}")
    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(str(path), check_existing=True)
    if noncolor:
        node.image.colorspace_settings.name = 'Non-Color'
    return node


def photo_mat(name, prefix):
    m, group = _new_edm_material(name)
    diff = TEXDIR / f"{prefix}_diff.png"
    arm = TEXDIR / f"{prefix}_arm.png"
    nor = TEXDIR / f"{prefix}_nor_gl.png"

    d = _image_node(m, diff, False)
    r = _image_node(m, arm, True)
    n = _image_node(m, nor, True)

    m.node_tree.links.new(d.outputs["Color"], group.inputs[NodeSocketInDefaultEnum.BASE_COLOR])
    m.node_tree.links.new(r.outputs["Color"], group.inputs[NodeSocketInDefaultEnum.ROUGH_METAL])
    m.node_tree.links.new(n.outputs["Color"], group.inputs[NodeSocketInDefaultEnum.NORMAL])
    return m


def _proc_albedo(name, base, kind="generic", size=2048):
    path = TEXDIR / f"{name}.png"
    if path.exists():
        return path

    seed = zlib.crc32(name.encode("utf-8")) & 0xffffffff
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    x = xx / max(1.0, float(size-1))
    y = yy / max(1.0, float(size-1))
    noise = (rng.random((size,size), dtype=np.float32)-.5) * .10
    noise += (.020*np.sin(x*37+y*11) + .016*np.sin(y*83-x*17) + .008*np.sin((x+y)*211)).astype(np.float32)

    rgb = np.empty((size,size,3), dtype=np.float32)
    rgb[...,0] = base[0] + noise
    rgb[...,1] = base[1] + noise
    rgb[...,2] = base[2] + noise
    speck = rng.random((size,size), dtype=np.float32)

    if kind == "rebar":
        oxide = (.060*np.maximum(0,np.sin(x*57+y*19)) + .026*np.sin(y*173+x*13)).astype(np.float32)
        rgb[...,0] += oxide
        rgb[...,1] += oxide*.20
        rgb[...,2] -= np.maximum(0,oxide)*.32
        pits = speck < .055
        rgb[pits] *= rng.uniform(.28,.72,size=(int(pits.sum()),1)).astype(np.float32)
    elif kind == "metal":
        brush = (.018*np.sin(y*630+x*9)+.008*np.sin(y*1410)).astype(np.float32)
        rgb += brush[...,None]
    elif kind == "wood":
        grain = (.045*np.sin(y*255+x*8)+.018*np.sin(y*780)).astype(np.float32)
        rgb[...,0] += grain
        rgb[...,1] += grain*.58
        rgb[...,2] += grain*.26
    elif kind == "soot":
        rgb *= (.78 + .22*np.maximum(0,np.sin(x*43+y*29)))[...,None].astype(np.float32)
    else:
        pits = speck < .025
        rgb[pits] *= .65

    np.clip(rgb,0,1,out=rgb)
    rgba=np.ones((size,size,4),dtype=np.float32)
    rgba[...,:3]=rgb
    img=bpy.data.images.new(name,width=size,height=size,alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.update()
    img.filepath_raw=str(path)
    img.file_format='PNG'
    img.save()
    bpy.data.images.remove(img)
    return path


def _proc_normal(name, kind="generic", size=2048):
    path = TEXDIR / f"{name}_Normal.png"
    if path.exists():
        return path

    seed=zlib.crc32((name+"_n").encode("utf-8")) & 0xffffffff
    rng=np.random.default_rng(seed)
    yy,xx=np.mgrid[0:size,0:size].astype(np.float32)
    x=xx/max(1.0,float(size-1))
    y=yy/max(1.0,float(size-1))
    h=(rng.random((size,size),dtype=np.float32)-.5)*.10
    h += (.035*np.sin(x*180+y*29)+.020*np.sin(y*530-x*41)+.010*np.sin((x+y)*1300)).astype(np.float32)

    if kind == "rebar":
        h += (.090*np.maximum(0,np.sin(y*math.pi*46 + x*8)) + .040*np.sin(y*1700)).astype(np.float32)
    elif kind == "wood":
        h += (.060*np.sin(y*250+x*11)+.025*np.sin(y*820)).astype(np.float32)
    elif kind == "metal":
        h += (.018*np.sin(y*1100)+.010*np.sin(x*59+y*340)).astype(np.float32)

    gy,gx=np.gradient(h)
    strength=4.0 if kind=="rebar" else 2.6
    nx=-gx*strength
    ny=-gy*strength
    nz=np.ones_like(nx)
    mag=np.sqrt(nx*nx+ny*ny+nz*nz)
    rgb=np.stack((nx/mag,ny/mag,nz/mag),axis=-1)
    rgb=rgb*.5+.5
    rgba=np.ones((size,size,4),dtype=np.float32)
    rgba[...,:3]=rgb
    img=bpy.data.images.new(name+"_Normal",width=size,height=size,alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.update()
    img.filepath_raw=str(path)
    img.file_format='PNG'
    img.save()
    bpy.data.images.remove(img)
    return path


def _proc_arm(name, rough, metal, size=1024):
    path=TEXDIR/f"{name}_RoughMet.png"
    if path.exists():
        return path
    seed=zlib.crc32((name+"_arm").encode("utf-8")) & 0xffffffff
    rng=np.random.default_rng(seed)
    n=(rng.random((size,size),dtype=np.float32)-.5)
    rgba=np.ones((size,size,4),dtype=np.float32)
    rgba[...,0]=1.0
    rgba[...,1]=np.clip(rough+n*.12,.02,.99)
    rgba[...,2]=np.clip(metal+n*(.06 if metal>0 else .005),0,1)
    img=bpy.data.images.new(name+"_RoughMet",width=size,height=size,alpha=True)
    img.pixels.foreach_set(rgba.ravel())
    img.update()
    img.filepath_raw=str(path)
    img.file_format='PNG'
    img.save()
    bpy.data.images.remove(img)
    return path


def proc_mat(name,color,rough=.8,metal=0.0,kind="generic",size=2048):
    m,group=_new_edm_material(name)
    d=_image_node(m,_proc_albedo(name,color,kind,size),False)
    r=_image_node(m,_proc_arm(name,rough,metal,1024),True)
    n=_image_node(m,_proc_normal(name,kind,size),True)
    m.node_tree.links.new(d.outputs["Color"],group.inputs[NodeSocketInDefaultEnum.BASE_COLOR])
    m.node_tree.links.new(r.outputs["Color"],group.inputs[NodeSocketInDefaultEnum.ROUGH_METAL])
    m.node_tree.links.new(n.outputs["Color"],group.inputs[NodeSocketInDefaultEnum.NORMAL])
    return m


def mats():
    if MATS:
        return MATS
    # Photo-based cinematic PBR hero materials are downloaded from Poly Haven before Blender runs.
    MATS.update({
        'fines': photo_mat('TPG_CIN3_Mat_RubbleBase','TPG_CIN3_RubbleBase'),
        'aggregate': photo_mat('TPG_CIN3_Mat_ConcreteDebris','TPG_CIN3_ConcreteDebris'),
        'concrete': photo_mat('TPG_CIN3_Mat_RoughConcrete','TPG_CIN3_RoughConcrete'),
        'concrete2': photo_mat('TPG_CIN3_Mat_RoughConcreteLight','TPG_CIN3_RoughConcrete'),
        'cmu': photo_mat('TPG_CIN3_Mat_CMU','TPG_CIN3_CMU'),
        'brick': photo_mat('TPG_CIN3_Mat_Brick','TPG_CIN3_Brick'),
        'rust': photo_mat('TPG_CIN3_Mat_RustMetal','TPG_CIN3_RustMetal'),
        'rebar': proc_mat('TPG_CIN3_RebarDarkOxide',(.085,.050,.035),.91,.52,'rebar',2048),
        'rust_dark': proc_mat('TPG_CIN3_RustDark',(.075,.038,.025),.93,.45,'rebar',2048),
        'steel': proc_mat('TPG_CIN3_DullSteel',(.21,.22,.215),.56,.78,'metal',2048),
        'galv': proc_mat('TPG_CIN3_Galvanized',(.43,.45,.45),.49,.74,'metal',2048),
        'pipe': proc_mat('TPG_CIN3_DirtyPipe',(.245,.255,.245),.79,.31,'metal',2048),
        'black': proc_mat('TPG_CIN3_BlackTrash',(.040,.041,.036),.94,.01,'generic',1024),
        'blue': proc_mat('TPG_CIN3_BluePlastic',(.025,.13,.22),.73,.0,'generic',1024),
        'white': proc_mat('TPG_CIN3_DirtyWhite',(.58,.57,.52),.90,.0,'generic',1024),
        'yellow': proc_mat('TPG_CIN3_FadedYellow',(.40,.28,.04),.82,.01,'generic',1024),
        'wood': proc_mat('TPG_CIN3_BrokenWood',(.22,.13,.055),.93,.0,'wood',2048),
        'soot': proc_mat('TPG_CIN3_Soot',(.030,.027,.024),.98,.02,'soot',1024),
    })
    return MATS


def ensure_uv(o):
    if o.type != 'MESH':
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
        mod=o.modifiers.new('chipped_edges','BEVEL')
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


def cyl(name,loc,radius,depth,mat,rot=(0,0,0),verts=14,coll=False):
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
    # Icosphere-derived fractured chunk: much less "pyramid rock" than the earlier fan geometry.
    subdiv=2 if verts>=9 else 1
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv,radius=1.0,location=loc)
    o=bpy.context.object
    o.name=name
    sx,sy,sz=scale
    o.scale=(sx*.5,sy*.5,sz*.5)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for v in o.data.vertices:
        f=rng.uniform(.76,1.18)
        v.co.x*=f*rng.uniform(.93,1.07)
        v.co.y*=f*rng.uniform(.93,1.07)
        v.co.z*=rng.uniform(.82,1.10)
        # A few chipped/sheared faces make the piece read like concrete rather than a rounded rock.
        if v.co.z > sz*.16 and rng.random()<.22:
            v.co.z*=rng.uniform(.72,.90)
    o.rotation_euler=(rng.uniform(-.62,.62),rng.uniform(-.62,.62),rng.uniform(0,math.tau))
    o.data.materials.append(mat)
    ensure_uv(o)
    return o


def cable(name,pts,mat,radius=.014,res=1):
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
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    ensure_uv(bpy.context.object)
    return bpy.context.object


def rebar(name,start,end,mat,r=.019):
    a=Vector(start)
    b=Vector(end)
    d=b-a
    L=d.length
    if L<=.002:
        return None

    sides=12
    ring_step=.055
    rings=max(6,min(42,int(L/ring_step)+2))
    vertices=[]
    for i in range(rings+1):
        z=-L*.5+L*(i/rings)
        phase=i*.22
        # Real geometry ribs: alternating raised bands with slight helical phase.
        band=1.0 + (.16 if i%2==0 else .015)
        for j in range(sides):
            ang=2*math.pi*j/sides + phase
            longitudinal=1.0 + (.035 if j in (0,6) else 0.0)
            rr=r*band*longitudinal
            vertices.append((math.cos(ang)*rr,math.sin(ang)*rr,z))

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
    mesh.from_pydata(vertices,[],faces)
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


def bent_rebar(name,pts,mat,r=.019):
    for i in range(len(pts)-1):
        rebar(f"{name}_{i}",pts[i],pts[i+1],mat,r)


def broken_pipe(name,loc,length,radius,mat,rng):
    rot=(rng.uniform(-.9,.9),rng.uniform(-.9,.9),rng.uniform(0,math.tau))
    cyl(name,loc,radius,length,mat,rot=rot,verts=18)
    axis=Euler(rot,'XYZ').to_matrix()@Vector((0,0,1))
    center=Vector(loc)
    for suffix,sign in (('A',1.0),('B',-1.0)):
        p=center+axis*(sign*(length*.5+.002))
        cyl(name+'_HOLE_'+suffix,tuple(p),radius*.64,.014,mats()['black'],rot=rot,verts=18)


def mound_z(x,y,peak=1.35):
    r=math.sqrt((x/3.0)**2+(y/2.9)**2)
    return max(.02,peak*max(0.0,1-r**1.65)**1.22)


def solid_rubble_mound(M,variant,detail,rng,peak):
    rings={2:18,1:12,0:8}[detail]
    sectors={2:80,1:56,0:36}[detail]
    rx=3.02 if variant=='intact' else 3.14
    ry=2.88 if variant=='intact' else 3.02

    verts=[(0,0,peak*.90)]
    ring_starts=[]
    for ri in range(1,rings+1):
        t=ri/rings
        ring_starts.append(len(verts))
        for s in range(sectors):
            a=2*math.pi*s/sectors
            edge_noise=1.0+.035*math.sin(a*5.0+ri*.7)+.022*math.sin(a*11.0-ri*.4)
            x=math.cos(a)*rx*t*edge_noise
            y=math.sin(a)*ry*t*(1.0+.028*math.sin(a*7.0+1.3))
            fall=max(0.0,1.0-t**1.68)
            z=peak*(fall**1.18)
            z += (.070*math.sin(a*3.0+ri*.73)+.035*math.sin(a*9.0-ri*.38))*fall
            z += rng.uniform(-.018,.018)
            if ri==rings:
                z=rng.uniform(-.13,-.055)
            verts.append((x,y,z))

    faces=[]
    first=ring_starts[0]
    for s in range(sectors):
        faces.append((0,first+s,first+(s+1)%sectors))
    for ri in range(1,rings):
        prev=ring_starts[ri-1]
        cur=ring_starts[ri]
        for s in range(sectors):
            sn=(s+1)%sectors
            faces.append((prev+s,cur+s,cur+sn,prev+sn))

    bottom=len(verts)
    verts.append((0,0,-.20))
    outer=ring_starts[-1]
    for s in range(sectors):
        faces.append((bottom,outer+(s+1)%sectors,outer+s))

    mesh=bpy.data.meshes.new('TPG_CIN3_SOLID_RUBBLE_CORE_mesh')
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    mesh.uv_layers.new(name='UVMap')
    o=bpy.data.objects.new('TPG_CIN3_SOLID_RUBBLE_CORE',mesh)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(M['fines'])
    return o


def add_dense_core(M,detail,variant,rng,peak):
    core_count={2:86,1:42,0:18}[detail]
    for i in range(core_count):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.86)*2.35
        x=math.cos(a)*rr*rng.uniform(.82,1.06)
        y=math.sin(a)*rr*rng.uniform(.80,1.06)
        surf=mound_z(x,y,peak)
        sx=rng.uniform(.48,1.05)
        sy=rng.uniform(.42,.96)
        sz=rng.uniform(.28,.62)
        z=max(-.12,surf*rng.uniform(.18,.48)-sz*.20)
        if variant=='destroyed':
            x*=1.05
            y*=1.07
            z*=.75
        mat=rng.choices([M['fines'],M['aggregate'],M['concrete']],[46,34,20])[0]
        irregular_chunk(f'TPG_CIN3_CORE_{i:03d}',(x,y,z),(sx,sy,sz),mat,rng,11 if detail==2 else 8)


def add_fill(M,detail,variant,rng,peak):
    count={2:540,1:230,0:82}[detail]
    for i in range(count):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.64)*3.08
        x=math.cos(a)*rr*rng.uniform(.82,1.06)
        y=math.sin(a)*rr*rng.uniform(.80,1.06)
        s=rng.uniform(.055,.21)*(1.0-.18*min(1,rr/3.0))
        sz=s*rng.uniform(.50,.90)
        z=max(-.085,mound_z(x,y,peak)*rng.uniform(.02,.30)-sz*.30)
        if variant=='destroyed':
            x*=rng.uniform(1.0,1.09)
            y*=rng.uniform(1.0,1.09)
        mat=rng.choices([M['fines'],M['aggregate'],M['concrete'],M['brick'],M['cmu']],[42,28,15,9,6])[0]
        irregular_chunk(f'TPG_CIN3_FILL_{i:03d}',(x,y,z),(s*rng.uniform(.78,1.35),s*rng.uniform(.76,1.25),sz),mat,rng,7)


def add_collision(M):
    cube('TPG_RUBBLE_COLL_CENTER',(0,0,.42),(4.55,4.35,.84),None,bevel=.30,coll=True)
    cube('TPG_RUBBLE_COLL_NORTH',(-.58,.96,.30),(3.30,2.42,.61),None,rot=(0,0,.18),bevel=.26,coll=True)
    cube('TPG_RUBBLE_COLL_SOUTH',(.84,-1.02,.26),(2.95,2.18,.52),None,rot=(0,0,-.26),bevel=.23,coll=True)


def build(variant='intact',detail=2):
    M=mats()
    rng=random.Random(830941+detail*149+(31 if variant=='destroyed' else 0))
    peak=1.48 if detail==2 else (1.30 if detail==1 else 1.02)
    if variant=='destroyed':
        peak*=.77

    solid_rubble_mound(M,variant,detail,rng,peak)
    add_dense_core(M,detail,variant,rng,peak)
    add_fill(M,detail,variant,rng,peak)

    main_count={2:430,1:180,0:62}[detail]
    for i in range(main_count):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.66)*2.90
        x=math.cos(a)*rr*rng.uniform(.83,1.06)
        y=math.sin(a)*rr*rng.uniform(.80,1.05)
        if variant=='destroyed':
            x*=rng.uniform(.98,1.12)
            y*=rng.uniform(.98,1.12)
        s=rng.uniform(.11,.42)*(1.0-.16*min(1,rr/3.0))
        sz=s*rng.uniform(.48,.90)
        z=max(-.05,mound_z(x,y,peak)*rng.uniform(.22,.76)-sz*.08)
        mat=rng.choices([M['concrete'],M['aggregate'],M['fines'],M['brick'],M['cmu']],[36,28,18,11,7])[0]
        if variant=='destroyed' and rng.random()<.08:
            mat=M['soot']
        irregular_chunk(f'TPG_CIN3_CHUNK_{i:03d}',(x,y,z),(s*rng.uniform(.76,1.40),s*rng.uniform(.75,1.28),sz),mat,rng,10 if detail==2 else 8)

    # Only a few temporary slabs; HQ pass replaces them with detailed fractured plates.
    for i in range({2:8,1:5,0:3}[detail]):
        x=rng.uniform(-1.8,1.8)
        y=rng.uniform(-1.7,1.7)
        z=max(.04,mound_z(x,y,peak)*rng.uniform(.25,.55))
        cube(f'TPG_RUB_SLAB_{i:02d}',(x,y,z),(rng.uniform(.48,.90),rng.uniform(.28,.58),rng.uniform(.10,.18)),M['concrete'],
             rot=(rng.uniform(-.34,.34),rng.uniform(-.34,.34),rng.uniform(0,math.tau)),bevel=.030)

    # Loose rebar stays near the pile; most visible steel is integrated into slabs/cages in the HQ pass.
    for i in range({2:22,1:10,0:4}[detail]):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.76)*2.35
        x=math.cos(a)*rr
        y=math.sin(a)*rr
        z=max(.015,mound_z(x,y,peak)*rng.uniform(.16,.58))
        L=rng.uniform(.30,.85)
        ang=rng.uniform(0,math.tau)
        mid=(x+math.cos(ang)*L*.52,y+math.sin(ang)*L*.52,z+rng.uniform(-.03,.18))
        end=(x+math.cos(ang)*L,y+math.sin(ang)*L,z+rng.uniform(-.08,.28))
        bent_rebar(f'TPG_CIN3_REBAR_{i:02d}',[(x,y,z),mid,end],M['rebar'],rng.uniform(.014,.021))

    for i in range({2:12,1:6,0:2}[detail]):
        x=rng.uniform(-2.18,2.18)
        y=rng.uniform(-2.10,2.10)
        z=max(.025,mound_z(x,y,peak)*rng.uniform(.08,.44))
        broken_pipe(f'TPG_CIN3_PIPE_{i}',(x,y,z),rng.uniform(.38,.96),rng.uniform(.050,.13),M['pipe'] if i%2 else M['rust'],rng)

    if detail>=1:
        for i in range(8 if detail==2 else 4):
            x=rng.uniform(-2.05,2.05)
            y=rng.uniform(-2.0,2.0)
            z=max(.04,mound_z(x,y,peak)*rng.uniform(.20,.55))
            cube(f'TPG_RUB_METAL_{i}',(x,y,z),(rng.uniform(.48,1.0),rng.uniform(.07,.16),rng.uniform(.04,.085)),
                 M['galv'] if i%3 else M['rust'],
                 rot=(rng.uniform(-.42,.42),rng.uniform(-.42,.42),rng.uniform(0,math.tau)),bevel=.014)
        for i in range(10 if detail==2 else 4):
            x=rng.uniform(-2.15,2.15)
            y=rng.uniform(-2.10,2.10)
            z=max(.025,mound_z(x,y,peak)*rng.uniform(.10,.40))
            cube(f'TPG_CIN3_WOOD_{i}',(x,y,z),(rng.uniform(.42,.92),rng.uniform(.055,.11),rng.uniform(.05,.095)),M['wood'],
                 rot=(rng.uniform(-.36,.36),rng.uniform(-.36,.36),rng.uniform(0,math.tau)),bevel=.009)

    if detail==2:
        for i in range(12):
            x=rng.uniform(-1.85,1.85)
            y=rng.uniform(-1.85,1.85)
            z=max(.07,mound_z(x,y,peak)*rng.uniform(.28,.58))
            pts=[
                (x,y,z),
                (x+rng.uniform(.18,.46),y+rng.uniform(-.36,.36),z+rng.uniform(-.08,.14)),
                (x+rng.uniform(.40,.78),y+rng.uniform(-.48,.48),max(.02,z+rng.uniform(-.22,.05)))
            ]
            cable(f'TPG_CIN3_WIRE_{i}',pts,M['black'] if i%4 else M['rebar'],rng.uniform(.008,.014),1)

    if variant=='destroyed' and detail>=1:
        for i in range(26 if detail==2 else 10):
            a=rng.uniform(0,math.tau)
            rr=rng.uniform(2.55,3.48)
            x=math.cos(a)*rr
            y=math.sin(a)*rr
            irregular_chunk(f'TPG_CIN3_BLAST_{i}',(x,y,rng.uniform(-.035,.075)),
                            (rng.uniform(.12,.32),rng.uniform(.12,.34),rng.uniform(.08,.20)),
                            M['soot'] if i%3==0 else M['aggregate'],rng,7)

    add_collision(M)
    for o in bpy.context.scene.objects:
        ensure_uv(o)

    bpy.context.scene['TPG_asset']='TPG Rubble Pile 20ft Cinematic V3'
    bpy.context.scene['TPG_variant']=variant
    bpy.context.scene['TPG_detail']=detail
    bpy.context.scene['TPG_render_target']='cinematic PBR rubble / DCS optimized'
