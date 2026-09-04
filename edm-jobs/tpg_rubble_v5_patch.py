import math, random
import bpy
from mathutils import Vector

import tpg_rubble_common as C

_APPLIED = False


def _mats_v5():
    if C.MATS:
        return C.MATS
    C.MATS.update({
        'fines': C.photo_mat('TPG_CIN5_Mat_RubbleBase','TPG_CIN5_RubbleBase'),
        'aggregate': C.photo_mat('TPG_CIN5_Mat_ConcreteDebris','TPG_CIN5_ConcreteDebris'),
        'concrete': C.photo_mat('TPG_CIN5_Mat_RoughConcrete','TPG_CIN5_RoughConcrete'),
        'concrete2': C.photo_mat('TPG_CIN5_Mat_RoughConcreteLight','TPG_CIN5_RoughConcrete'),
        'cmu': C.photo_mat('TPG_CIN5_Mat_CMU','TPG_CIN5_CMU'),
        'brick': C.photo_mat('TPG_CIN5_Mat_Brick','TPG_CIN5_Brick'),
        'rust': C.photo_mat('TPG_CIN5_Mat_RustMetal','TPG_CIN5_RustMetal'),
        # Warmer oxidized steel so exposed bars read as rusty rebar rather than black rods.
        'rebar': C.proc_mat('TPG_CIN5_RebarOxidized',(.205,.078,.032),.88,.48,'rebar',2048),
        'rust_dark': C.proc_mat('TPG_CIN5_RustDark',(.135,.050,.024),.91,.44,'rebar',2048),
        'steel': C.proc_mat('TPG_CIN5_DullSteel',(.21,.22,.215),.56,.78,'metal',1024),
        'galv': C.proc_mat('TPG_CIN5_Galvanized',(.43,.45,.45),.49,.74,'metal',1024),
        # Pipe has its own textured brown/gray oxidized metal treatment.
        'pipe': C.proc_mat('TPG_CIN5_DirtyPipe',(.175,.125,.083),.80,.42,'rebar',2048),
        'black': C.proc_mat('TPG_CIN5_BlackTrash',(.040,.041,.036),.94,.01,'generic',1024),
        'blue': C.proc_mat('TPG_CIN5_BluePlastic',(.025,.13,.22),.73,.0,'generic',1024),
        'white': C.proc_mat('TPG_CIN5_DirtyWhite',(.58,.57,.52),.90,.0,'generic',1024),
        'yellow': C.proc_mat('TPG_CIN5_FadedYellow',(.40,.28,.04),.82,.01,'generic',1024),
        'wood': C.proc_mat('TPG_CIN5_BrokenWood',(.22,.13,.055),.93,.0,'wood',1024),
        'soot': C.proc_mat('TPG_CIN5_Soot',(.030,.027,.024),.98,.02,'soot',1024),
    })
    return C.MATS


def _mound_z_v5(x,y,peak=1.35):
    # Elliptical collapsed-building mass with broad asymmetric lobes. No radial-sector math.
    nx=x/3.02
    ny=y/2.90
    r=math.sqrt(nx*nx+ny*ny)
    if r>=1.05:
        return .018
    base=peak*(max(0.0,1.0-r**1.72)**1.20)
    # Broad local collapses/bulges keep the crown naturally rounded but non-conical.
    lobes=(
        (.62,.30,.095,.78),
        (-.72,.46,.075,.72),
        (.18,-.74,.070,.64),
        (-.28,-.38,.050,.55),
    )
    for ox,oy,amp,width in lobes:
        d2=((x-ox)/width)**2+((y-oy)/(width*.88))**2
        base += peak*amp*math.exp(-d2)
    # Low-frequency XY breakup; never converges on a center vertex and cannot make spokes.
    base += peak*(.018*math.sin(x*1.73+y*.91)+.013*math.sin(y*2.21-x*.67))*max(0.0,1.0-r)
    return max(.018,base)


def _solid_rubble_mound_v5(M,variant,detail,rng,peak):
    # Cartesian quad grid instead of a polar triangle fan. This permanently removes the
    # top-down radial/starburst artifact seen in Cinematic V4.
    n={2:61,1:45,0:31}[detail]
    rx=3.08 if variant=='intact' else 3.18
    ry=2.94 if variant=='intact' else 3.06
    verts=[]
    for iy in range(n):
        fy=iy/(n-1)
        y=-ry+2*ry*fy
        for ix in range(n):
            fx=ix/(n-1)
            x=-rx+2*rx*fx
            rr=math.sqrt((x/rx)**2+(y/ry)**2)
            if rr>=1.0:
                # Put the square-grid skirt below terrain so only the rounded mound is visible.
                z=-.10-.035*min(1.0,(rr-1.0)/.25)
            else:
                z=_mound_z_v5(x,y,peak)
                # Deterministic micro undulation to avoid a perfectly smooth blanket.
                z += (.020*math.sin(x*3.2+y*1.7)+.013*math.sin(y*4.1-x*2.2))*max(0.0,1.0-rr)
            verts.append((x,y,z))

    faces=[]
    for iy in range(n-1):
        for ix in range(n-1):
            a=iy*n+ix
            faces.append((a,a+1,a+n+1,a+n))

    mesh=bpy.data.meshes.new('TPG_CIN5_SOLID_RUBBLE_CORE_mesh')
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    mesh.uv_layers.new(name='UVMap')
    o=bpy.data.objects.new('TPG_CIN5_SOLID_RUBBLE_CORE',mesh)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(M['fines'])
    return o


def _cyl_v5(name,loc,radius,depth,mat,rot=(0,0,0),verts=14,coll=False):
    # Minimum 36 sides plus smooth normals: pipes/cans stop reading as octagons.
    sides=max(36,int(verts))
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=radius,depth=depth,location=loc,rotation=rot)
    o=bpy.context.object
    o.name=name
    if mat:
        o.data.materials.append(mat)
    C.ensure_uv(o)
    for p in o.data.polygons:
        # Keep end caps flat; smooth only side faces.
        p.use_smooth = abs(p.normal.z) < .95
    if coll:
        C.get_edm_props(o).SPECIAL_TYPE='COLLISION_SHELL'
    return o


def _rebar_v5(name,start,end,mat,r=.019):
    a=Vector(start)
    b=Vector(end)
    d=b-a
    L=d.length
    if L<=.002:
        return None

    sides=16
    ring_step=.040
    rings=max(8,min(64,int(L/ring_step)+2))
    vertices=[]
    for i in range(rings+1):
        z=-L*.5+L*(i/rings)
        phase=i*.16
        # Pronounced alternating transverse ribs plus two longitudinal ribs.
        band=1.0 + (.21 if i%2==0 else .025)
        for j in range(sides):
            ang=2*math.pi*j/sides + phase
            longitudinal=1.0 + (.055 if j in (0,8) else 0.0)
            rr=r*band*longitudinal
            vertices.append((math.cos(ang)*rr,math.sin(ang)*rr,z))

    faces=[]
    for i in range(rings):
        for j in range(sides):
            nj=(j+1)%sides
            faces.append((i*sides+j,i*sides+nj,(i+1)*sides+nj,(i+1)*sides+j))
    faces.append(tuple(range(sides-1,-1,-1)))
    last=rings*sides
    faces.append(tuple(last+j for j in range(sides)))

    mesh=bpy.data.meshes.new(name+'_mesh')
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    uv=mesh.uv_layers.new(name='UVMap')
    # Cylindrical UVs make the oxidized/rib texture actually resolve along the bar.
    for poly in mesh.polygons:
        if len(poly.loop_indices)==4:
            for li in poly.loop_indices:
                vi=mesh.loops[li].vertex_index
                ring=vi//sides
                side=vi%sides
                uv.data[li].uv=(side/sides,(ring/rings)*max(1.0,L/.20))
    o=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(o)
    o.location=(a+b)*.5
    o.rotation_mode='QUATERNION'
    o.rotation_quaternion=d.to_track_quat('Z','Y')
    o.rotation_mode='XYZ'
    o.data.materials.append(mat)
    for p in o.data.polygons:
        p.use_smooth=True
    return o


def _broken_pipe_v5(name,loc,length,radius,mat,rng):
    rot=(rng.uniform(-.9,.9),rng.uniform(-.9,.9),rng.uniform(0,math.tau))
    _cyl_v5(name,loc,radius,length,mat,rot=rot,verts=48)
    axis=C.Euler(rot,'XYZ').to_matrix()@Vector((0,0,1))
    center=Vector(loc)
    for suffix,sign in (('A',1.0),('B',-1.0)):
        p=center+axis*(sign*(length*.5+.002))
        _cyl_v5(name+'_HOLE_'+suffix,tuple(p),radius*.66,.016,_mats_v5()['rust_dark'],rot=rot,verts=48)


def apply():
    global _APPLIED
    if _APPLIED:
        return
    C.MATS.clear()
    C.mats=_mats_v5
    C.mound_z=_mound_z_v5
    C.solid_rubble_mound=_solid_rubble_mound_v5
    C.cyl=_cyl_v5
    C.rebar=_rebar_v5
    C.broken_pipe=_broken_pipe_v5
    _APPLIED=True


def post_quality_pass(variant='intact',detail=2):
    # Add a deliberately visible surface/perimeter debris layer after the original quality pass.
    # The V4 pile had good filler texture but most masonry was buried under it.
    import tpg_rubble_quality_pass as Q
    M=_mats_v5()
    rng=random.Random(15052026 + detail*271 + (913 if variant=='destroyed' else 0))
    peak=1.48 if detail==2 else (1.30 if detail==1 else 1.02)
    if variant=='destroyed':
        peak*=.77

    surf_n={2:150,1:72,0:26}[detail]
    for i in range(surf_n):
        a=rng.uniform(0,math.tau)
        rr=(rng.random()**.58)*3.00
        x=math.cos(a)*rr*rng.uniform(.88,1.05)
        y=math.sin(a)*rr*rng.uniform(.86,1.05)
        s=rng.uniform(.075,.29 if detail==2 else .22)
        z=_mound_z_v5(x,y,peak)+s*rng.uniform(.05,.26)
        mat=rng.choices([M['aggregate'],M['concrete'],M['brick'],M['cmu'],M['fines']],[39,23,16,12,10])[0]
        C.irregular_chunk(f'TPG_CIN5_SURFACE_{i:03d}',(x,y,z),(s*rng.uniform(.85,1.55),s*rng.uniform(.78,1.32),s*rng.uniform(.55,.92)),mat,rng,10 if detail==2 else 8)

    cmu_n={2:34,1:15,0:5}[detail]
    for i in range(cmu_n):
        a=rng.uniform(0,math.tau)
        rr=rng.uniform(1.45,3.02)
        x,y=math.cos(a)*rr,math.sin(a)*rr
        z=_mound_z_v5(x,y,peak)+rng.uniform(.025,.12)
        if rr>2.65:
            z=max(.035,z*.48)
        Q._cmu(f'TPG_CIN5_HERO_CMU_{i}',(x,y,z),(rng.uniform(-.65,.65),rng.uniform(-.65,.65),rng.uniform(0,math.tau)),M,broken=(i%3==0 or i%7==0))

    brick_n={2:104,1:44,0:14}[detail]
    for i in range(brick_n):
        a=rng.uniform(0,math.tau)
        rr=rng.uniform(1.25,3.14)
        x,y=math.cos(a)*rr,math.sin(a)*rr
        z=_mound_z_v5(x,y,peak)+rng.uniform(.015,.075)
        if rr>2.72:
            z=max(.025,z*.42)
        Q._brick(f'TPG_CIN5_HERO_BRICK_{i}',(x,y,z),(rng.uniform(-.85,.85),rng.uniform(-.85,.85),rng.uniform(0,math.tau)),M,half=(i%4==0),chipped=(i%3==0 or i%8==0))

    chip_n={2:90,1:38,0:12}[detail]
    for i in range(chip_n):
        a=rng.uniform(0,math.tau)
        rr=rng.uniform(2.10,3.28)
        x,y=math.cos(a)*rr,math.sin(a)*rr
        s=rng.uniform(.045,.13)
        z=rng.uniform(-.01,.075)
        mat=rng.choices([M['aggregate'],M['brick'],M['cmu']],[58,27,15])[0]
        C.irregular_chunk(f'TPG_CIN5_EDGE_CHIP_{i}',(x,y,z),(s*1.4,s,s*.72),mat,rng,7)

    if detail==2:
        # More readable construction trash around the edge and partially on the mound.
        for i in range(7):
            a=rng.uniform(0,math.tau); rr=rng.uniform(2.15,3.10)
            x,y=math.cos(a)*rr,math.sin(a)*rr
            z=max(.035,_mound_z_v5(x,y,peak)*rng.uniform(.15,.42))
            Q._bag(f'TPG_CIN5_TRASH_BAG_{i}',(x,y,z),(rng.uniform(.14,.22),rng.uniform(.09,.15),rng.uniform(.045,.075)),(rng.uniform(-.5,.5),rng.uniform(-.5,.5),rng.uniform(0,math.tau)),M['black'] if i%3 else M['blue'])
        for i in range(12):
            a=rng.uniform(0,math.tau); rr=rng.uniform(2.0,3.20)
            x,y=math.cos(a)*rr,math.sin(a)*rr
            _cyl_v5(f'TPG_CIN5_TRASH_CAN_{i}',(x,y,rng.uniform(.025,.07)),.026,.105,M['white'] if i%3 else M['blue'],rot=(rng.uniform(-1.2,1.2),rng.uniform(-1.2,1.2),rng.uniform(0,math.tau)),verts=36)
        for i in range(10):
            a=rng.uniform(0,math.tau); rr=rng.uniform(2.0,3.12)
            x,y=math.cos(a)*rr,math.sin(a)*rr
            C.cube(f'TPG_CIN5_TRASH_SCRAP_{i}',(x,y,rng.uniform(.025,.085)),(rng.uniform(.12,.30),rng.uniform(.07,.18),rng.uniform(.012,.025)),M['yellow'] if i%4==0 else (M['blue'] if i%4==1 else M['white']),rot=(rng.uniform(-.3,.3),rng.uniform(-.3,.3),rng.uniform(0,math.tau)),bevel=.004)

    # Re-project UVs for new objects, then re-batch by material to keep draw calls sane.
    for o in list(bpy.context.scene.objects):
        Q._box_uv(o)
    Q._batch_visual_by_material()

    bpy.context.scene['TPG_asset']='TPG Rubble Pile 20ft Cinematic V5'
    bpy.context.scene['TPG_quality_pass']='cinematic-V5-rounded-grid-visible-debris-v1'
    bpy.context.scene['TPG_coexistence_id']='TPG_Rubble_Pile_20ft_Cinematic_V5'
    bpy.context.scene['TPG_v5_fixes']='no radial fan; round textured pipes; oxidized ribbed rebar; visible brick/CMU/trash; rubble texture as interstitial filler'
