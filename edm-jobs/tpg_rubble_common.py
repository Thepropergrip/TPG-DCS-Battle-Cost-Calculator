import bpy, math, os, random, zlib
from pathlib import Path
from mathutils import Vector, Euler

WORK = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
TEXDIR = WORK / "edm-artifacts" / "Textures"
TEXDIR.mkdir(parents=True, exist_ok=True)

from materials.materials import build_material_descriptions
from materials.material_tools import createEdmNodeGroup
from enums import NodeSocketInDefaultEnum
from objects_custom_props import get_edm_props

MAT_DESCS = build_material_descriptions()
MATS = {}


def _tex(name, base, variation=.06, streak=False, mottled=False, size=512):
    path = TEXDIR / (name + ".png")
    if path.exists(): return path
    img = bpy.data.images.new(name, width=size, height=size, alpha=True)
    seed = zlib.crc32(name.encode("utf-8")) & 0xffffffff
    rng = random.Random(seed)
    is_concrete = ("Concrete" in name or "Aggregate" in name)
    is_aggregate = ("Aggregate" in name)
    is_rust = ("Rust" in name)
    is_soot = ("Soot" in name)
    is_metal = ("Steel" in name or "Galvanized" in name)
    px=[]
    p1=(seed % 997)*.013
    p2=(seed % 571)*.019
    for y in range(size):
        for x in range(size):
            u=x/max(1,size-1); v=y/max(1,size-1)
            fine=(rng.random()-.5)*variation
            low=.018*math.sin(x*.031+p1)+.014*math.sin(y*.027+p2)+.012*math.sin((x+y)*.014+p1*.3)
            n=fine+low
            if streak:
                n += .018*math.sin(y*.12)+.010*math.sin(x*.055+y*.04)
            if mottled:
                n += .025*math.sin(x*.10)*math.sin(y*.075)+.018*math.sin((x+y)*.037)

            r,g,b=base
            if is_concrete:
                # thin branching-looking fracture lines plus dark/light aggregate flecks
                crack=abs(math.sin(x*.041+y*.067+p1)+.58*math.sin(x*.089-y*.033+p2))
                if crack < .030:
                    n -= .105*(1.0-crack/.030)
                speck=rng.random()
                if speck < (.034 if is_aggregate else .018):
                    n += rng.uniform(-.15,.09)
            if is_rust:
                oxide=.045*math.sin(y*.026+x*.009+p2)+.035*math.sin(y*.081+p1)
                r += max(-.015,oxide)
                g -= max(0,oxide)*.48
                b -= max(0,oxide)*.72
                if rng.random()<.012:
                    r += .07; g += .012; b -= .018
            if is_metal:
                brush=.018*math.sin(y*.23+p1)+.010*math.sin(y*.51+x*.012)
                r+=brush; g+=brush; b+=brush
            if is_soot:
                n -= .020*abs(math.sin(x*.035+y*.021+p1))

            px.extend((
                max(0,min(1,r+n)),
                max(0,min(1,g+n)),
                max(0,min(1,b+n)),
                1.0
            ))
    img.pixels=px
    img.filepath_raw=str(path)
    img.file_format='PNG'
    img.save()
    return path


def edm_mat(name,color,rough=.82,metal=.0,variation=.05,streak=False,mottled=False):
    m=bpy.data.materials.new(name); m.use_nodes=True; m.node_tree.nodes.clear()
    group=createEdmNodeGroup("EDM_Default_Material",m)
    group.post_init(MAT_DESCS["EDM_Default_Material"]); group.name="Group"
    tex=m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image=bpy.data.images.load(str(_tex(name,color,variation,streak,mottled)),check_existing=True)
    m.node_tree.links.new(tex.outputs["Color"],group.inputs[NodeSocketInDefaultEnum.BASE_COLOR])
    rmo_path=TEXDIR/(name+"_RoughMet.png")
    if not rmo_path.exists():
        rmo_size=64
        img=bpy.data.images.new(name+"_RoughMet",width=rmo_size,height=rmo_size,alpha=True)
        rr=random.Random((zlib.crc32((name+"_rmo").encode("utf-8")) & 0xffffffff))
        vals=[]
        for _ in range(rmo_size*rmo_size):
            rv=max(0.02,min(0.99,rough+(rr.random()-.5)*.075))
            mv=max(0.0,min(1.0,metal+(rr.random()-.5)*(.055 if metal>0 else .006)))
            vals.extend((1.0,rv,mv,1.0))
        img.pixels=vals
        img.filepath_raw=str(rmo_path)
        img.file_format='PNG'
        img.save()
    rmo=m.node_tree.nodes.new("ShaderNodeTexImage"); rmo.image=bpy.data.images.load(str(rmo_path),check_existing=True)
    rmo.image.colorspace_settings.name='Non-Color'
    m.node_tree.links.new(rmo.outputs['Color'],group.inputs[NodeSocketInDefaultEnum.ROUGH_METAL])
    return m


def mats():
    if MATS: return MATS
    MATS.update({
      'concrete':edm_mat('TPG_RUB100_Concrete',(.43,.42,.39),.94,0,.095,False,True),
      'concrete2':edm_mat('TPG_RUB100_ConcreteLight',(.57,.56,.52),.91,0,.075,False,True),
      'aggregate':edm_mat('TPG_RUB100_Aggregate',(.30,.29,.27),.97,0,.12,False,True),
      'brick':edm_mat('TPG_RUB100_Brick',(.36,.16,.095),.92,0,.07,True,True),
      'rust':edm_mat('TPG_RUB100_RustSteel',(.25,.095,.035),.84,.42,.08,True,True),
      'rust_dark':edm_mat('TPG_RUB100_RustDark',(.12,.045,.018),.88,.35,.07,True,True),
      'steel':edm_mat('TPG_RUB100_DullSteel',(.24,.25,.24),.50,.74,.045,True),
      'galv':edm_mat('TPG_RUB100_Galvanized',(.47,.49,.49),.43,.72,.038,True),
      'pipe':edm_mat('TPG_RUB100_DirtyPipe',(.30,.31,.29),.72,.28,.06,True,True),
      'black':edm_mat('TPG_RUB100_BlackTrash',(.025,.027,.025),.91,.01,.05,True),
      'blue':edm_mat('TPG_RUB100_BluePlastic',(.025,.16,.28),.68,.0,.05,True),
      'white':edm_mat('TPG_RUB100_DirtyWhite',(.67,.65,.59),.86,.0,.07,True,True),
      'yellow':edm_mat('TPG_RUB100_FadedYellow',(.48,.34,.045),.76,.01,.06,True),
      'wood':edm_mat('TPG_RUB100_BrokenWood',(.25,.15,.075),.90,.0,.075,True,True),
      'soot':edm_mat('TPG_RUB100_Soot',(.035,.028,.023),.96,.02,.08,True,True),
    })
    return MATS


def ensure_uv(o):
    if o.type!='MESH': return
    if not o.data.uv_layers: o.data.uv_layers.new(name='UVMap')


def cube(name,loc,scale,mat,rot=(0,0,0),bevel=.03,coll=False):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc,rotation=rot)
    o=bpy.context.object; o.name=name; o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel>0:
        mod=o.modifiers.new('broken_edges','BEVEL'); mod.width=bevel; mod.segments=1
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=mod.name)
    if mat:o.data.materials.append(mat)
    ensure_uv(o)
    if coll:get_edm_props(o).SPECIAL_TYPE='COLLISION_SHELL'
    return o


def cyl(name,loc,radius,depth,mat,rot=(0,0,0),verts=12,coll=False):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=radius,depth=depth,location=loc,rotation=rot)
    o=bpy.context.object;o.name=name
    if mat:o.data.materials.append(mat)
    ensure_uv(o)
    if coll:get_edm_props(o).SPECIAL_TYPE='COLLISION_SHELL'
    return o


def irregular_chunk(name,loc,scale,mat,rng,verts=10):
    # convex jagged rubble stone/concrete chunk
    pts=[]
    sx,sy,sz=scale
    for i in range(verts):
        a=2*math.pi*i/verts
        rr=rng.uniform(.72,1.16)
        pts.append((math.cos(a)*sx*.5*rr,math.sin(a)*sy*.5*rr,rng.uniform(-.22,.18)*sz))
    pts += [(rng.uniform(-.18,.18)*sx,rng.uniform(-.18,.18)*sy,sz*.55),
            (rng.uniform(-.18,.18)*sx,rng.uniform(-.18,.18)*sy,-sz*.45)]
    top=len(pts)-2; bot=len(pts)-1
    faces=[]
    for i in range(verts):
        j=(i+1)%verts; faces += [(top,i,j),(bot,j,i)]
    mesh=bpy.data.meshes.new(name+'_mesh'); mesh.from_pydata(pts,[],faces); mesh.update(); mesh.uv_layers.new(name='UVMap')
    o=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(o); o.location=loc
    o.rotation_euler=(rng.uniform(-.55,.55),rng.uniform(-.55,.55),rng.uniform(0,math.tau))
    o.data.materials.append(mat)
    return o


def cable(name,pts,mat,radius=.018,res=1):
    c=bpy.data.curves.new(name+'_curve','CURVE'); c.dimensions='3D'; c.bevel_depth=radius; c.bevel_resolution=res
    s=c.splines.new('BEZIER'); s.bezier_points.add(len(pts)-1)
    for bp,p in zip(s.bezier_points,pts): bp.co=p; bp.handle_left_type='AUTO'; bp.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o); o.data.materials.append(mat)
    bpy.context.view_layer.objects.active=o; o.select_set(True); bpy.ops.object.convert(target='MESH'); ensure_uv(bpy.context.object)
    return bpy.context.object


def rebar(name,start,end,mat,r=.025):
    a=Vector(start); b=Vector(end); d=b-a; L=d.length
    o=cyl(name,(a+b)/2,r,L,mat,verts=8)
    o.rotation_mode='QUATERNION'; o.rotation_quaternion=d.to_track_quat('Z','Y'); o.rotation_mode='XYZ'
    return o


def broken_pipe(name,loc,length,radius,mat,rng):
    rot=(rng.uniform(-1.0,1.0),rng.uniform(-1.0,1.0),rng.uniform(0,math.tau))
    cyl(name,loc,radius,length,mat,rot=rot,verts=14)
    # True hollow-looking end openings: place dark caps on both actual cylinder ends.
    axis = Euler(rot, 'XYZ').to_matrix() @ Vector((0.0,0.0,1.0))
    center = Vector(loc)
    for suffix,sign in (('A',1.0),('B',-1.0)):
        p = center + axis * (sign * (length*.5 + .002))
        cyl(name+'_HOLE_'+suffix,tuple(p),radius*.68,.014,mats()['black'],rot=rot,verts=14)


def mound_z(x,y,peak=1.35):
    r=math.sqrt((x/3.0)**2+(y/3.0)**2)
    return max(.05,peak*(1-r*r)*.92)


def add_collision(M):
    # Three overlapping low-poly masses approximate the solid rubble mound for gameplay collision.
    cube('TPG_RUBBLE_COLL_CENTER',(0,0,.45),(4.3,4.1,.9),None,bevel=.28,coll=True)
    cube('TPG_RUBBLE_COLL_NORTH',(-.55,.95,.33),(3.2,2.3,.65),None,rot=(0,0,.20),bevel=.25,coll=True)
    cube('TPG_RUBBLE_COLL_SOUTH',(.8,-1.0,.28),(2.8,2.1,.55),None,rot=(0,0,-.28),bevel=.22,coll=True)


def build(variant='intact',detail=2):
    M=mats(); rng=random.Random(100941 + detail*113 + (17 if variant=='destroyed' else 0))
    # No ground plane or raised bed: lowest fragments intentionally penetrate slightly below Z=0 to sit into DCS terrain.
    peak=1.48 if detail>=2 else (1.30 if detail==1 else 1.05)
    count={2:118,1:64,0:28}[detail]
    if variant=='destroyed': peak*=.78
    for i in range(count):
        a=rng.uniform(0,math.tau); rr=(rng.random()**.62)*2.95
        x=math.cos(a)*rr*rng.uniform(.82,1.07); y=math.sin(a)*rr*rng.uniform(.78,1.05)
        z=mound_z(x,y,peak)*rng.uniform(.28,.90)-rng.uniform(.01,.08)
        if variant=='destroyed': x*=rng.uniform(.95,1.18); y*=rng.uniform(.95,1.18)
        s=rng.uniform(.18,.62)*(1.0-.18*min(1,rr/3.0))
        mat=rng.choices([M['concrete'],M['concrete2'],M['aggregate'],M['brick']],[52,19,18,11])[0]
        if variant=='destroyed' and rng.random()<.15: mat=M['soot']
        irregular_chunk(f'TPG_RUB_CHUNK_{i:03d}',(x,y,z),(s*rng.uniform(.75,1.35),s*rng.uniform(.75,1.25),s*rng.uniform(.45,.95)),mat,rng,verts=8 if detail<2 else 10)

    slab_n={2:22,1:12,0:5}[detail]
    for i in range(slab_n):
        a=rng.uniform(0,math.tau); rr=rng.uniform(.2,2.5); x=math.cos(a)*rr; y=math.sin(a)*rr
        z=max(.08,mound_z(x,y,peak)*rng.uniform(.45,.95))
        sx=rng.uniform(.65,1.55); sy=rng.uniform(.35,1.10); sz=rng.uniform(.10,.24)
        cube(f'TPG_RUB_SLAB_{i:02d}',(x,y,z),(sx,sy,sz),M['concrete2'] if i%3 else M['concrete'],
             rot=(rng.uniform(-.35,.35),rng.uniform(-.35,.35),rng.uniform(0,math.tau)),bevel=.035)
        if detail>=1 and rng.random()<.62:
            # exposed bars projecting from shattered slab edge
            for k in range(rng.randint(1,3)):
                p=(x+rng.uniform(-sx*.4,sx*.4),y+rng.uniform(-sy*.4,sy*.4),z+rng.uniform(0,.12))
                q=(p[0]+rng.uniform(-.2,.35),p[1]+rng.uniform(-.2,.35),p[2]+rng.uniform(.18,.65))
                rebar(f'TPG_RUB_SLAB_REBAR_{i}_{k}',p,q,M['rust'],.018)

    if detail>=1:
        # Cinder blocks / masonry fragments
        for i in range(14 if detail==2 else 7):
            x=rng.uniform(-2.4,2.4); y=rng.uniform(-2.4,2.4); z=max(.05,mound_z(x,y,peak)*rng.uniform(.25,.82))
            cube(f'TPG_RUB_BLOCK_{i}',(x,y,z),(rng.uniform(.28,.48),rng.uniform(.16,.28),rng.uniform(.15,.24)),M['concrete'],
                 rot=(rng.uniform(-.5,.5),rng.uniform(-.5,.5),rng.uniform(0,math.tau)),bevel=.025)

    rebar_n={2:44,1:20,0:6}[detail]
    for i in range(rebar_n):
        x=rng.uniform(-2.65,2.65); y=rng.uniform(-2.65,2.65); z=max(.02,mound_z(x,y,peak)*rng.uniform(.15,.88))
        L=rng.uniform(.45,1.55 if detail>=1 else .9); a=rng.uniform(0,math.tau)
        end=(x+math.cos(a)*L,y+math.sin(a)*L,z+rng.uniform(-.15,.55))
        rebar(f'TPG_RUB_REBAR_{i:02d}',(x,y,z),end,M['rust'],rng.uniform(.012,.027))

    pipe_n={2:10,1:5,0:2}[detail]
    for i in range(pipe_n):
        x=rng.uniform(-2.3,2.3); y=rng.uniform(-2.3,2.3); z=max(.05,mound_z(x,y,peak)*rng.uniform(.12,.62))
        broken_pipe(f'TPG_RUB_PIPE_{i}',(x,y,z),rng.uniform(.45,1.25),rng.uniform(.055,.15),M['pipe'] if i%2 else M['rust'],rng)

    if detail>=1:
        # recognizable bent sheet metal / beam debris
        for i in range(9 if detail==2 else 4):
            x=rng.uniform(-2.3,2.3); y=rng.uniform(-2.3,2.3); z=max(.08,mound_z(x,y,peak)*rng.uniform(.35,.88))
            cube(f'TPG_RUB_METAL_{i}',(x,y,z),(rng.uniform(.65,1.5),rng.uniform(.09,.22),rng.uniform(.05,.11)),M['galv'] if i%3 else M['rust'],
                 rot=(rng.uniform(-.5,.5),rng.uniform(-.5,.5),rng.uniform(0,math.tau)),bevel=.02)
        # broken timber
        for i in range(8 if detail==2 else 3):
            x=rng.uniform(-2.4,2.4); y=rng.uniform(-2.4,2.4); z=max(.04,mound_z(x,y,peak)*rng.uniform(.2,.65))
            cube(f'TPG_RUB_WOOD_{i}',(x,y,z),(rng.uniform(.65,1.45),rng.uniform(.07,.13),rng.uniform(.06,.12)),M['wood'],
                 rot=(rng.uniform(-.4,.4),rng.uniform(-.4,.4),rng.uniform(0,math.tau)),bevel=.012)

    if detail==2:
        # loose electrical wires/cables draped through the pile
        for i in range(8):
            x=rng.uniform(-2.1,2.1); y=rng.uniform(-2.1,2.1); z=max(.1,mound_z(x,y,peak)*rng.uniform(.45,.85))
            pts=[(x,y,z),(x+rng.uniform(.25,.6),y+rng.uniform(-.5,.5),z+rng.uniform(-.12,.20)),
                 (x+rng.uniform(.55,1.1),y+rng.uniform(-.7,.7),max(.03,z+rng.uniform(-.35,.08)))]
            cable(f'TPG_RUB_WIRE_{i}',pts,M['black'] if i%3 else M['rust'],rng.uniform(.010,.020),1)
        # scattered trash, sparse enough to read as authentic rather than decorative clutter
        trash_specs=[(M['black'],14),(M['blue'],7),(M['white'],8),(M['yellow'],3)]
        n=0
        for mat,qty in trash_specs:
            for _ in range(qty):
                a=rng.uniform(0,math.tau); rr=rng.uniform(1.0,3.15); x=math.cos(a)*rr; y=math.sin(a)*rr
                z=max(.015,mound_z(x,y,peak)*rng.uniform(.03,.25))
                cube(f'TPG_RUB_TRASH_{n}',(x,y,z),(rng.uniform(.08,.24),rng.uniform(.05,.18),rng.uniform(.012,.045)),mat,
                     rot=(rng.uniform(-.4,.4),rng.uniform(-.4,.4),rng.uniform(0,math.tau)),bevel=.005); n+=1

    if variant=='destroyed' and detail>=1:
        # extra blast-scattered burnt fragments beyond the original footprint
        for i in range(18 if detail==2 else 8):
            a=rng.uniform(0,math.tau); rr=rng.uniform(2.5,3.45); x=math.cos(a)*rr; y=math.sin(a)*rr
            irregular_chunk(f'TPG_RUB_BLAST_{i}',(x,y,rng.uniform(-.02,.12)),(rng.uniform(.16,.42),rng.uniform(.16,.45),rng.uniform(.10,.26)),M['soot'] if i%2 else M['concrete'],rng,8)

    add_collision(M)
    for o in bpy.context.scene.objects: ensure_uv(o)
    bpy.context.scene['TPG_asset']='TPG Rubble Pile 20ft V1'
    bpy.context.scene['TPG_variant']=variant
    bpy.context.scene['TPG_detail']=detail
