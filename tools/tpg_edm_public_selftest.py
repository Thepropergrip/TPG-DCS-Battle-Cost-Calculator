import addon_utils
import bpy
import importlib
import os
import sys
from pathlib import Path

root = Path(os.environ["BLENDER_USER_SCRIPTS"]) / "addons" / "io_scene_edm"
sys.path.insert(0, str(root))
addon_utils.enable("io_scene_edm", default_set=False, persistent=False)
edm = importlib.import_module("io_scene_edm")
if not bool(getattr(edm, "native_bindings", False)):
    raise RuntimeError("ED exporter native_bindings=False")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 0))
bpy.context.object.name = "TPG_EDM_PUBLIC_SELFTEST_CUBE"

from io_scene_edm import collection_walker
from logger import log

log.errors = []
log.warnings = []
out = Path(os.environ["RUNNER_TEMP"]) / "TPG_EDM_PUBLIC_SELFTEST.edm"
collection_walker._write(bpy.context, str(out))
if log.errors:
    raise RuntimeError("EDM exporter errors: " + " | ".join(str(x) for x in log.errors))
if not out.exists() or out.stat().st_size <= 0:
    raise RuntimeError("No valid EDM produced")
print("TPG_EDM_PUBLIC_SELFTEST_OK", out, out.stat().st_size)
