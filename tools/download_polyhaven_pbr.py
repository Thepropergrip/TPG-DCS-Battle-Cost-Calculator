#!/usr/bin/env python3
import argparse, json, os, shutil, sys
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

UA = "TPG-DCS-RubbleBuilder/3.0 (+https://github.com/Thepropergrip/TPG-DCS-Battle-Cost-Calculator)"
ASSETS = {
    "rubble": ("TPG_CIN3_RubbleBase", "8k"),
    "concrete_debris": ("TPG_CIN3_ConcreteDebris", "8k"),
    "rough_concrete": ("TPG_CIN3_RoughConcrete", "4k"),
    "concrete_block_wall_03": ("TPG_CIN3_CMU", "4k"),
    "red_bricks_02": ("TPG_CIN3_Brick", "4k"),
    "rusty_metal_sheet": ("TPG_CIN3_RustMetal", "4k"),
}
MAPS = ("diff", "arm", "nor_gl")

def get_json(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=120) as r:
        return json.load(r)

def iter_urls(obj):
    if isinstance(obj, dict):
        u = obj.get("url")
        if isinstance(u, str):
            yield u
        for v in obj.values():
            yield from iter_urls(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_urls(v)

def choose_url(urls, slug, res, map_key):
    candidates = []
    for url in urls:
        fn = unquote(Path(urlparse(url).path).name).lower()
        if not fn.endswith(".png"):
            continue
        if res not in fn:
            continue
        if f"_{map_key}_" in fn or fn.endswith(f"_{map_key}.png") or f"_{map_key}{res}" in fn:
            candidates.append(url)
    if not candidates:
        # Flexible fallback for future naming changes.
        for url in urls:
            fn = unquote(Path(urlparse(url).path).name).lower()
            if fn.endswith(".png") and res in fn and map_key in fn:
                candidates.append(url)
    if not candidates:
        raise RuntimeError(f"No {res} PNG map '{map_key}' found for Poly Haven asset '{slug}'")
    candidates.sort(key=lambda u: len(u))
    return candidates[0]

def download(url, dst):
    req = Request(url, headers={"User-Agent": UA})
    tmp = dst.with_suffix(dst.suffix + ".part")
    with urlopen(req, timeout=300) as src, open(tmp, "wb") as out:
        shutil.copyfileobj(src, out, length=1024*1024)
    tmp.replace(dst)
    if dst.stat().st_size < 65536:
        raise RuntimeError(f"Downloaded texture is suspiciously small: {dst} ({dst.stat().st_size} bytes)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    manifest = {
        "credit": "Powered by Poly Haven",
        "api": "https://api.polyhaven.com",
        "assets": {}
    }

    for slug, (prefix, res) in ASSETS.items():
        print(f"[Poly Haven] resolving {slug} @ {res}", flush=True)
        data = get_json(f"https://api.polyhaven.com/files/{slug}")
        urls = list(iter_urls(data))
        if not urls:
            raise RuntimeError(f"No downloadable files returned for {slug}")

        manifest["assets"][slug] = {"resolution": res, "maps": {}}
        for map_key in MAPS:
            url = choose_url(urls, slug, res, map_key)
            dst = out / f"{prefix}_{map_key}.png"
            print(f"[Poly Haven] {slug}:{map_key} -> {dst.name}", flush=True)
            download(url, dst)
            manifest["assets"][slug]["maps"][map_key] = {
                "source_url": url,
                "file": dst.name,
                "bytes": dst.stat().st_size,
            }

    (out / "TPG_CIN3_PolyHaven_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print("[Poly Haven] cinematic PBR set ready", flush=True)

if __name__ == "__main__":
    main()
