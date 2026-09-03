"""Fetch the CC0 assets listed in assets/manifest.json from Poly Haven.

    python -m homespec.assets [--manifest assets/manifest.json] [--dest assets]

Textures land in assets/textures/<id>/{Diffuse,Rough,nor_gl,...}.jpg, models in
assets/models/<id>/ with their glTF and companion files, HDRIs in assets/hdri/.
Existing files are skipped, so re-running is cheap.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import urllib.request

API = "https://api.polyhaven.com"
UA = {"User-Agent": "homespec/0.1 (asset fetch)"}   # Poly Haven returns 403 without a user agent
TEXTURE_MAPS = ("Diffuse", "nor_gl", "Rough", "Displacement", "AO", "arm")
MAX_MODEL_BYTES = 80 * 1024 * 1024   # a scene of instances, not one tree that fills the GPU


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()

def _save(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(_get(url))
    return True

def fetch_texture(tid, spec, dest):
    files = json.loads(_get(f"{API}/files/{tid}"))
    res = spec.get("resolution", "2k")
    got = []
    for key in TEXTURE_MAPS:
        if key not in files:
            continue
        r = res if res in files[key] else sorted(files[key])[0]
        fmt = "jpg" if "jpg" in files[key][r] else sorted(files[key][r])[0]
        _save(files[key][r][fmt]["url"], f"{dest}/textures/{tid}/{key}.{fmt}")
        got.append(key)
    return f"texture {tid}: {', '.join(got)}"

def fetch_model(mid, spec, dest):
    files = json.loads(_get(f"{API}/files/{mid}"))
    if "gltf" not in files:
        return f"model {mid}: no glTF export on Poly Haven, skipped"
    res = spec.get("resolution", "1k")
    r = res if res in files["gltf"] else sorted(files["gltf"])[0]
    g = files["gltf"][r]["gltf"]
    total = g.get("size", 0) + sum(info.get("size", 0) for info in g.get("include", {}).values())
    if total > MAX_MODEL_BYTES:
        return f"model {mid}: {total / 1e6:.0f} MB, over the {MAX_MODEL_BYTES / 1e6:.0f} MB limit, skipped"
    d = f"{dest}/models/{mid}"
    _save(g["url"], f"{d}/{os.path.basename(g['url'])}")
    for rel, info in g.get("include", {}).items():
        _save(info["url"], f"{d}/{rel}")
    return f"model {mid}: {1 + len(g.get('include', {}))} files ({r})"

def fetch_hdri(hid, spec, dest):
    files = json.loads(_get(f"{API}/files/{hid}"))
    res, fmt = spec.get("resolution", "2k"), spec.get("format", "hdr")
    _save(files["hdri"][res][fmt]["url"], f"{dest}/hdri/{hid}_{res}.{fmt}")
    return f"hdri {hid}: {res} {fmt}"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="assets/manifest.json")
    ap.add_argument("--dest", default="assets")
    args = ap.parse_args(argv)
    with open(args.manifest) as f:
        man = json.load(f)
    jobs = ([(fetch_hdri, k, v) for k, v in man.get("hdris", {}).items()]
            + [(fetch_texture, k, v) for k, v in man.get("textures", {}).items()]
            + [(fetch_model, k, v) for k, v in man.get("models", {}).items()])
    with cf.ThreadPoolExecutor(6) as ex:
        for line in ex.map(lambda j: j[0](j[1], j[2], args.dest), jobs):
            print(line, flush=True)


if __name__ == "__main__":
    main()
