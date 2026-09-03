from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import runpy
import sys
import traceback


def blender_args() -> list[str]:
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1:]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Headless Eagle Dynamics EDM exporter job runner")
    p.add_argument("--job", required=True)
    p.add_argument("--artifact-dir", required=True)
    return p.parse_args(blender_args())


class Reporter:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    def report(self, levels, message: str) -> None:
        levels_out = sorted(str(x) for x in levels)
        self.messages.append({"levels": levels_out, "message": message})
        print(f"[EDM REPORT] {','.join(levels_out)}: {message}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve(base: Path, value: str | None) -> Path | None:
    if not value:
        return None
    p = Path(value)
    if not p.is_absolute():
        p = base / p
    return p.resolve()


def enable_official_exporter():
    import addon_utils
    import bpy

    # ED's official addon uses several top-level imports (for example
    # "from materials...") from inside its own package. Blender's interactive
    # addon loader normally provides that package path. Headless execution can
    # omit it, so add the exact official addon root explicitly without
    # modifying any ED exporter files.
    addon_root = (
        Path(os.environ["BLENDER_USER_SCRIPTS"]).resolve()
        / "addons"
        / "io_scene_edm"
    )
    if not addon_root.exists():
        raise RuntimeError(f"Official ED addon root not found: {addon_root}")
    addon_root_str = str(addon_root)
    if addon_root_str not in sys.path:
        sys.path.insert(0, addon_root_str)
    print(f"[EDM] Python addon root: {addon_root}")

    addon_utils.enable("io_scene_edm", default_set=False, persistent=False)
    if "io_scene_edm" not in sys.modules:
        raise RuntimeError("io_scene_edm did not load.")

    edm = importlib.import_module("io_scene_edm")
    native = bool(getattr(edm, "native_bindings", False))
    if not native:
        raise RuntimeError(
            "Official ED exporter loaded without native bindings. "
            "Refusing dummy/non-Windows EDM export."
        )

    if tuple(bpy.app.version[:3]) != (4, 1, 1):
        raise RuntimeError(f"Expected Blender 4.1.1, got {bpy.app.version_string}.")

    if platform.system() != "Windows":
        raise RuntimeError(f"Expected Windows native exporter host, got {platform.system()}.")

    print(f"[EDM] Blender {bpy.app.version_string}")
    print(f"[EDM] Platform {platform.system()}")
    print(f"[EDM] native_bindings={native}")
    return edm


def clear_scene() -> None:
    import bpy

    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def make_selftest_scene() -> None:
    import bpy

    clear_scene()
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 0.0, 0.0))
    obj = bpy.context.object
    obj.name = "EDM_PIPELINE_SELFTEST_CUBE"
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def main() -> int:
    args = parse_args()
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
    job_path = Path(args.job).resolve()
    artifact_dir = Path(args.artifact_dir).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)

    job = json.loads(job_path.read_text(encoding="utf-8"))
    mode = str(job.get("mode", "selftest")).lower()
    output_name = Path(str(job.get("output", "model.edm"))).name
    if not output_name.lower().endswith(".edm"):
        output_name += ".edm"
    edm_path = artifact_dir / output_name

    import bpy

    edm = enable_official_exporter()

    if mode == "selftest":
        make_selftest_scene()

    elif mode == "script":
        script_path = resolve(workspace, job.get("script"))
        if not script_path or not script_path.exists():
            raise FileNotFoundError(f"Model build script not found: {script_path}")
        clear_scene()
        print(f"[EDM] Running model build script: {script_path}")
        runpy.run_path(str(script_path), run_name="__main__")

    elif mode == "blend":
        blend_path = resolve(workspace, job.get("blend"))
        if not blend_path or not blend_path.exists():
            raise FileNotFoundError(f"Blend file not found: {blend_path}")
        print(f"[EDM] Opening blend: {blend_path}")
        bpy.ops.wm.open_mainfile(filepath=str(blend_path))
        edm = enable_official_exporter()

    else:
        raise ValueError(f"Unsupported EDM job mode: {mode}")

    post_script = resolve(workspace, job.get("post_script"))
    if post_script:
        if not post_script.exists():
            raise FileNotFoundError(f"Post script not found: {post_script}")
        print(f"[EDM] Running post script: {post_script}")
        runpy.run_path(str(post_script), run_name="__main__")

    if len(bpy.context.scene.objects) == 0:
        raise RuntimeError("Scene is empty; refusing to export an empty EDM.")

    save_blend = bool(job.get("save_blend", True))
    blend_out = artifact_dir / (edm_path.stem + ".blend")
    if save_blend or mode != "blend":
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_out))
        print(f"[EDM] Saved build blend: {blend_out}")

    # Headless export path: call Eagle Dynamics' actual model writer directly.
    # io_scene_edm.run_edm_export() calls this same function first, then accesses
    # GUI addon preferences only to decide whether to launch ModelViewer2.
    # That optional GUI preference lookup is unavailable in a transient headless
    # addon session and occurs AFTER a successful EDM save.
    from io_scene_edm import collection_walker
    from logger import log

    reporter = Reporter()
    log.errors = []
    log.warnings = []

    collection_walker._write(bpy.context, str(edm_path))

    if log.errors:
        raise RuntimeError(
            "EDM export errors: " + " | ".join(str(e) for e in log.errors)
        )

    reporter.report({"INFO"}, f"Model successfully exported to {edm_path}.")

    if not edm_path.exists():
        raise RuntimeError("EDM exporter completed but no file exists.")
    if edm_path.stat().st_size <= 0:
        raise RuntimeError("EDM exporter produced an empty file.")

    report = {
        "status": "success",
        "job": str(job_path),
        "mode": mode,
        "blender_version": bpy.app.version_string,
        "platform": platform.system(),
        "native_bindings": bool(getattr(edm, "native_bindings", False)),
        "official_exporter_commit": os.environ.get("EDM_EXPORTER_COMMIT"),
        "output": edm_path.name,
        "bytes": edm_path.stat().st_size,
        "sha256": sha256(edm_path),
        "reporter_messages": reporter.messages,
    }
    (artifact_dir / "edm-build-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print("[EDM] DCS_EDM_EXPORT_SUCCESS")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
