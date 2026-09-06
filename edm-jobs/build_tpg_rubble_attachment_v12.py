import os, math, sys
from pathlib import Path
import bpy

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import build_tpg_rubble_v5_companion_pack as BASE

SRC = Path(os.environ.get('TPG_ATTACHMENT_SOURCE_DIR', 'edm-source/rubble_attachment')).resolve()
OBJ = SRC / 'attachment_rubble.obj'

SHAPE_COPIES = {
    'smalllow': [(-0.65, -0.30, 0.10, 0.15), (0.75, 0.50, 0.14, -0.35)],
    'pushed': [(-1.70, -0.25, 0.10, -0.15), (-0.25, 0.05, 0.16, 0.15), (1.25, 0.20, 0.22, 0.35), (2.00, -0.20, 0.30, -0.20)],
    'rectangular': [(-2.10, -0.35, 0.08, -0.15), (-0.85, 0.35, 0.12, 0.25), (0.65, -0.25, 0.10, -0.35), (2.05, 0.25, 0.09, 0.20)],
    'buildingface': [(-1.05, 0.20, 0.18, 0.05), (0.05, 0.35, 0.24, -0.12), (1.05, 0.25, 0.16, 0.08)],
    'ridge': [(-2.65, -0.05, 0.10, -0.20), (-1.15, 0.10, 0.15, 0.15), (0.35, -0.05, 0.13, -0.10), (1.85, 0.12, 0.10, 0.20), (2.75, -0.08, 0.08, -0.15)],
    'multihump': [(-1.45, -0.20, 0.18, 0.20), (1.20, 0.55, 0.22, -0.25), (0.10, -1.30, 0.16, 0.05), (0.25, 0.35, 0.28, 0.35)],
}


def _ensure_source():
    if not OBJ.exists():
        raise RuntimeError(f'Missing supplied attachment rubble OBJ: {OBJ}')


def _supplied_material(prefix='TPG_ATTACH_Rubble', name='TPG_ATTACH_Mat_Rubble'):
    return BASE.C.photo_mat(name, prefix)


def _import_obj():
    before = set(bpy.context.scene.objects)
    try:
        bpy.ops.wm.obj_import(filepath=str(OBJ))
    except Exception:
        bpy.ops.import_scene.obj(filepath=str(OBJ))
    after = [o for o in bpy.context.scene.objects if o not in before and o.type == 'MESH']
    if not after:
        raise RuntimeError('Supplied attachment OBJ imported no mesh objects')
    mat = _supplied_material()
    for o in after:
        o.name = 'TPG_ATTACH_RUBBLE_SOURCE_' + o.name[:38]
        o.data.materials.clear()
        o.data.materials.append(mat)
    return after


def _join_objects(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return objs[0]


def _normalize_source(obj):
    xs=[v.co.x for v in obj.data.vertices]; ys=[v.co.y for v in obj.data.vertices]; zs=[v.co.z for v in obj.data.vertices]
    span=max(max(xs)-min(xs),max(ys)-min(ys),max(zs)-min(zs),1e-6)
    s=1.45/span
    obj.scale=(s,s,s)
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    xs=[v.co.x for v in obj.data.vertices]; ys=[v.co.y for v in obj.data.vertices]; zs=[v.co.z for v in obj.data.vertices]
    cx=(min(xs)+max(xs))*0.5; cy=(min(ys)+max(ys))*0.5; z0=min(zs)
    for v in obj.data.vertices:
        v.co.x-=cx; v.co.y-=cy; v.co.z-=z0
    obj.data.update()


def _duplicate_into_shape(source, key):
    for i,(x,y,z,rz) in enumerate(SHAPE_COPIES[key]):
        dup=source.copy(); dup.data=source.data.copy(); bpy.context.collection.objects.link(dup)
        dup.name=f'TPG_ATTACH_RUBBLE_{key.upper()}_{i:02d}'
        dup.location=(x,y,z); dup.rotation_euler[2]=rz; dup.scale=(1.0,1.0,1.0)
    bpy.data.objects.remove(source, do_unlink=True)


def _wall_quad_skin():
    nx, ny = 65, 37
    width, depth = 3.05, 1.90
    verts=[]; faces=[]
    for j in range(ny):
        t=j/(ny-1)
        half=(width*0.5)*(1.0-0.30*t)
        for i in range(nx):
            u=i/(nx-1)
            x=(u*2.0-1.0)*half
            y=t*depth
            face_h=1.58*((1.0-t)**1.22)
            irregular=0.055*math.sin(x*2.6+0.4)*math.sin(t*math.pi)
            z=max(0.015, face_h + irregular)
            verts.append((x,y,z))
    for j in range(ny-1):
        for i in range(nx-1):
            a=j*nx+i; b=a+1; c=a+nx+1; d=a+nx
            faces.append((a,b,c,d))
    mesh=bpy.data.meshes.new('TPG_ATTACH_WALL_QUAD_SKIN_mesh')
    mesh.from_pydata(verts,[],faces); mesh.update()
    obj=bpy.data.objects.new('TPG_ATTACH_WALL_QUAD_SKIN',mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(_supplied_material('TPG_ATTACH_DebrisTile','TPG_ATTACH_Mat_DebrisTile'))
    BASE.Q._box_uv(obj, .48)
    return obj


def main():
    key=os.environ.get('TPG_PACK_SHAPE','').strip().lower()
    state=os.environ.get('TPG_PACK_STATE','intact').strip().lower()
    if key not in BASE.SHAPES:
        raise RuntimeError(f'Unknown shape {key}')

    BASE._clear_scene()

    if state=='collision':
        BASE._build_collision_shell(key)
        bpy.context.scene['TPG_attachment_upgrade']='attachment shape pack collision footprint'
        return

    _ensure_source()
    source_variant='destroyed' if state=='destroyed' else 'intact'
    detail=int(os.environ.get('TPG_PACK_DETAIL','2'))
    original_batch=BASE.Q._batch_visual_by_material
    BASE.Q._batch_visual_by_material=lambda: None
    try:
        BASE.build(source_variant,detail)
        BASE.Q.quality_pass(source_variant,detail)
        BASE.V5.post_quality_pass(source_variant,detail)
        BASE._move_rigid_assemblies(key)
    finally:
        BASE.Q._batch_visual_by_material=original_batch

    imported=_import_obj(); source=_join_objects(imported); _normalize_source(source); _duplicate_into_shape(source,key)
    if key=='buildingface':
        _wall_quad_skin()

    original_batch()
    BASE._rename_scene_objects(key)
    bpy.context.scene['TPG_attachment_upgrade']='actual supplied OBJ + supplied PBR maps'
    bpy.context.scene['TPG_attachment_source']=OBJ.name
    bpy.context.scene['TPG_shape_method']='shape-specific footprint + rigid supplied debris; no recognizable-object stretching'
    bpy.context.scene['TPG_wall_topology']='65x37 Cartesian quad grid; no radial fan topology'

main()
