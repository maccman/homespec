#!/usr/bin/env python3
"""Run one owner-controlled native UE stage, retaining commands and actual receipts.

No shell interpolation is used. --dry-run plans a command without starting UE,
UnrealBuildTool or AutomationTool. Each real invocation gets a unique evidence
directory; old receipts are never accepted as proof of a new invocation.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import platform
import plistlib
import re
import shutil
import struct
import subprocess
import sys
import time
import uuid
import zlib
from datetime import UTC, datetime
from pathlib import Path

UNREAL = Path(__file__).resolve().parents[1]
REPOSITORY = UNREAL.parents[2]
PROJECT = UNREAL / "BastideWalk/BastideWalk.uproject"
OUTPUT = REPOSITORY / "out/unreal"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def parse_render_cvar(value: str) -> str:
    match = re.fullmatch(r"((?:r|sg)\.[A-Za-z][A-Za-z0-9_.]*)=([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)", value)
    if not match or not math.isfinite(float(match[2])):
        raise argparse.ArgumentTypeError("Use a finite numeric r.* or sg.* override, e.g. r.ScreenPercentage=67")
    return f"{match[1]} {match[2]}"


def gameplay_benchmark_receipt(benchmark: dict, route_names: list[str], width: int = 1600, height: int = 900,
                               requested_window_mode: str | None = None) -> dict:
    takes = benchmark.get("routes", [])
    require(benchmark.get("status") == "completed", "Gameplay benchmark did not complete")
    require([take.get("name") for take in takes] == route_names, "Gameplay benchmark does not cover every configured route in order")
    results = []
    for take in takes:
        samples = take.get("raw_frame_ms", [])
        require(isinstance(samples, list) and all(type(v) in {float, int} and math.isfinite(v) and v > 0 for v in samples), "Invalid wall-clock gameplay samples")
        engine_caps_disabled = True
        fullscreen_capacity_evidence = True
        settings_realtime = True
        viewport_matches_requested = True
        window_mode_matches_requested = True
        for key in ("settings_start", "settings_end"):
            settings = take.get(key) or {}
            cvars = settings.get("cvars", {})
            viewport_matches_requested &= (settings.get("viewport_width"), settings.get("viewport_height")) == (width, height)
            window_mode_matches_requested &= requested_window_mode is None or settings.get("window_mode") == requested_window_mode
            engine_caps_disabled &= all(type(cvars.get(name)) in {float, int} and cvars[name] == 0 for name in ("r.VSync", "t.MaxFPS"))
            engine_caps_disabled &= settings.get("engine_smooth_frame_rate") is False
            settings_realtime &= all(settings.get(name) is False for name in ("app_fixed_time_step", "app_benchmarking", "engine_fixed_frame_rate"))
            fullscreen_capacity_evidence &= (settings.get("window_mode") == "Fullscreen"
                                             and settings.get("running_game") is True
                                             and settings.get("editor_process") is False
                                             and settings.get("mac_frame_pacer_enabled") is False
                                             and type(cvars.get("rhi.Metal.NonBlockingPresent")) in {float, int}
                                             and cvars["rhi.Metal.NonBlockingPresent"] == 0)
        engine_caps_disabled &= settings_realtime
        valid = (take.get("valid_take") is True and take.get("warmup_completed") is True
                 and take.get("focus_stable") is True and take.get("assets_stable") is True
                 and take.get("clocks_realtime") is True and take.get("route_passed") is True
                 and len(samples) >= 120 and engine_caps_disabled and settings_realtime
                 and viewport_matches_requested and window_mode_matches_requested)
        mean_fps = 1000 * len(samples) / sum(samples) if samples else None
        ordered = sorted(samples)
        p95 = ordered[math.ceil(len(ordered) * 0.95) - 1] if ordered else None
        results.append({"name": take["name"], "valid_take": valid, "engine_caps_disabled": engine_caps_disabled,
                        "uncapped_render_capacity_verified": valid and fullscreen_capacity_evidence,
                        "settings_realtime": settings_realtime, "sampled_frames": len(samples),
                        "viewport_matches_requested": viewport_matches_requested,
                        "window_mode_matches_requested": window_mode_matches_requested,
                        "actual_viewports": {key: [(take.get(key) or {}).get("viewport_width"), (take.get(key) or {}).get("viewport_height")]
                                             for key in ("settings_start", "settings_end")},
                        "mean_fps": mean_fps, "p95_frame_ms": p95,
                        "mean_60fps_target_met": valid and mean_fps >= 60,
                        "steady_60fps_target_met": valid and mean_fps >= 59.7 and p95 <= 17.5})
    return {"target_fps": 60, "requested_viewport": [width, height], "requested_window_mode": requested_window_mode,
            "engine_caps_disabled": bool(results) and all(r["engine_caps_disabled"] for r in results),
            "uncapped_render_capacity_verified": bool(results) and all(r["uncapped_render_capacity_verified"] for r in results),
            "routes": results, "all_mean_targets_met": bool(results) and all(r["mean_60fps_target_met"] for r in results),
            "all_steady_60_targets_met": bool(results) and all(r["steady_60fps_target_met"] for r in results),
            "steady_60_criterion": {"mean_fps_minimum": 59.7, "p95_frame_ms_maximum": 17.5,
                                    "nominal_refresh_hz": 60, "scope": "Declared nominal 60 Hz timing tolerance; not a guarantee of every frame or rendering headroom."},
            "scope": "Focused wall-clock gameplay after native preparation. Engine caps are checked separately from Mac presentation sync; capacity requires actual fullscreen and disabled Mac pacing, never frame-dropping presentation. Exact averages and p95 are retained."}


def engine_root(requested: Path | None) -> tuple[Path, dict]:
    candidates = [requested] if requested else [Path(os.environ.get("BASTIDE_UNREAL_ENGINE", "/Users/Shared/Epic Games/UE_5.8"))]
    if not requested and not candidates[0].exists():
        candidates = sorted(Path("/Users/Shared/Epic Games").glob("UE_5.*"), reverse=True)
    for candidate in candidates:
        version_path = candidate / "Engine/Build/Build.version"
        if not version_path.is_file():
            continue
        version = json.loads(version_path.read_text())
        if [version.get(k) for k in ["MajorVersion", "MinorVersion", "PatchVersion"]] == [5, 8, 2]:
            return candidate.resolve(), version
    raise RuntimeError("UE 5.8.2 was not found. Pass --engine /path/to/UE_5.8; no engine will be downloaded.")


def snapshot_inputs() -> dict:
    paths = [PROJECT]
    for directory in ["Source", "Config", "Content/Data"]:
        paths += sorted(p for p in (PROJECT.parent / directory).rglob("*") if p.is_file())
    paths += sorted((UNREAL / "tools").glob("*.py"))
    return {str(p.relative_to(UNREAL)): {"bytes": p.stat().st_size, "sha256": sha(p)} for p in paths}


def probe(command: list[str]) -> dict:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return {"command": command, "exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def platform_receipt(engine: Path | None, version: dict | None) -> dict:
    return {
        "engine_root": str(engine) if engine else None,
        "engine_build": version,
        "os": platform.platform(),
        "machine": platform.machine(),
        "free_disk_bytes": shutil.disk_usage(REPOSITORY).free,
        "macos": probe(["/usr/bin/sw_vers"]),
        "physical_memory": probe(["/usr/sbin/sysctl", "-n", "hw.memsize"]),
        "xcode": probe(["/usr/bin/xcodebuild", "-version"]),
        "sdk": probe(["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-version"]),
    }


def packaged_app_files(app: Path) -> dict:
    """Locate self-contained staged content; a compiled target .app is insufficient."""
    info = app / "Contents/Info.plist"
    require(info.is_file(), f"Missing packaged app metadata: {info}")
    with info.open("rb") as stream:
        metadata = plistlib.load(stream)
    name = metadata.get("CFBundleExecutable", "")
    require(isinstance(name, str) and name and Path(name).name == name, f"Invalid executable name in {info}")
    executable = app / "Contents/MacOS" / name
    require(executable.is_file(), f"Missing packaged executable: {executable}")
    archives = sorted(
        p for p in (app / "Contents").rglob("*") if p.is_file() and p.parent.name == "Paks" and p.suffix in {".pak", ".utoc"} and p.stat().st_size > 0
    )
    require(bool(archives), f"App has no cooked Paks/IoStore content: {app}. BuildCookRun must cook, stage, package and archive.")
    for path in archives:
        if path.suffix == ".utoc":
            require(path.with_suffix(".ucas").is_file(), f"IoStore payload missing beside {path}")
    data = {}
    for filename in ["waypoints.json", "walkthrough.json"]:
        matches = sorted(p for p in (app / "Contents").rglob(filename) if p.is_file() and p.parts[-3:] == ("Content", "Data", filename))
        require(len(matches) == 1, f"Expected one staged Content/Data/{filename} inside {app}; found {len(matches)}")
        data[filename] = matches[0]
    return {"executable": executable, "archives": archives, "data": data}


def app_executable(archive: Path, explicit_app: Path | None) -> tuple[Path, Path]:
    apps = [explicit_app] if explicit_app else sorted(archive.rglob("BastideWalk.app")) if archive.exists() else []
    found = []
    rejected = []
    for app in apps:
        try:
            files = packaged_app_files(app)
        except (RuntimeError, OSError, ValueError, plistlib.InvalidFileException) as error:
            rejected.append(str(error))
            continue
        found.append((app.resolve(), files["executable"].resolve()))
    require(len(found) <= 1, "Multiple complete packaged apps found; select one explicitly with --app: " + ", ".join(str(app) for app, _ in found))
    if found:
        return found[0]
    detail = "; ".join(rejected) if rejected else f"No BastideWalk.app in {archive}"
    raise RuntimeError(f"No complete packaged walkthrough found. {detail}. Package the project first, or pass --app.")


def packaged_app_receipt(app: Path) -> dict:
    files = packaged_app_files(app)
    return {
        "path": str(app),
        "executable_sha256": sha(files["executable"]),
        "content_archives": [{"path": str(path.relative_to(app)), "bytes": path.stat().st_size} for path in files["archives"]],
        "staged_data": {name: {"path": str(path.relative_to(app)), "bytes": path.stat().st_size, "sha256": sha(path)} for name, path in files["data"].items()},
    }


def packaged_evidence_directory(app: Path, run_name: str) -> Path:
    """Use the signed app's container without changing its sandbox entitlement."""
    with (app / "Contents/Info.plist").open("rb") as stream:
        identifier = plistlib.load(stream).get("CFBundleIdentifier", "")
    require(isinstance(identifier, str) and re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*", identifier) is not None,
            "Packaged app lacks a safe bundle identifier")
    require(isinstance(run_name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run_name) is not None,
            "Packaged evidence requires a safe run directory name")
    return Path.home() / "Library/Containers" / identifier / "Data/Library/Caches/BastideValidation" / run_name


def copy_native_evidence(native_evidence: Path, evidence: Path) -> list[str]:
    """Retain available output after exit, including interrupted/failed stages."""
    copied = []
    if native_evidence != evidence:
        for name in ("engine.log", "Validation"):
            source = native_evidence / name
            if source.is_dir():
                shutil.copytree(source, evidence / name, dirs_exist_ok=True)
                copied.append(name)
            elif source.is_file():
                shutil.copy2(source, evidence / name)
                copied.append(name)
    return copied


def expected_route_names(path: Path) -> list[str]:
    data = json.loads(path.read_text())
    routes = data.get("routes", [])
    require(isinstance(routes, list) and bool(routes), f"No configured movement routes in {path}")
    require(all(isinstance(route, dict) and isinstance(route.get("name"), str) for route in routes), f"Invalid named route list in {path}")
    return [route["name"] for route in routes]


def capture_expectations(route_path: Path, waypoint_path: Path, width: int, height: int) -> dict:
    route_data = json.loads(route_path.read_text())
    fov = route_data.get("camera_fov_degrees")
    require(isinstance(fov, (int, float)) and math.isfinite(fov) and 1 < fov < 170, "Capture route data lacks a valid camera_fov_degrees")
    waypoints = json.loads(waypoint_path.read_text())
    require(isinstance(waypoints, list) and len(waypoints) == 26, "Capture waypoints must contain all26 source cameras")
    return {"width": width, "height": height, "horizontal_fov_degrees": fov,
            "camera_axis_constraint": "MaintainXFOV", "camera_overrides_axis_constraint": True,
            "waypoints": [{"name": row["name"], "frame": row["frame"]} for row in waypoints],
            "route_data_sha256": sha(route_path), "waypoint_data_sha256": sha(waypoint_path)}


def png_capture_receipt(path: Path, width: int, height: int, started_utc: str) -> dict:
    """Check fresh PNG framing/CRC and dimensions; does not judge image fidelity."""
    stat = path.stat()
    started_ns = int(datetime.fromisoformat(started_utc.replace("Z", "+00:00")).timestamp() * 1_000_000_000)
    require(stat.st_mtime_ns >= started_ns, f"Capture predates this invocation: {path}")
    payload = path.read_bytes()
    require(len(payload) >= 33 and payload[:8] == b"\x89PNG\r\n\x1a\n", f"Invalid PNG signature/header: {path}")
    require(payload[8:16] == b"\x00\x00\x00\x0dIHDR", f"PNG must start with a 13-byte IHDR: {path}")
    actual_width, actual_height = struct.unpack_from(">II", payload, 16)
    require((actual_width, actual_height) == (width, height),
            f"Capture dimensions {actual_width}x{actual_height} differ from requested {width}x{height}: {path}")
    offset, saw_data, saw_end = 8, False, False
    while offset < len(payload):
        require(offset + 12 <= len(payload), f"Truncated PNG chunk: {path}")
        length = struct.unpack_from(">I", payload, offset)[0]
        end = offset + 12 + length
        require(end <= len(payload), f"Truncated PNG chunk payload: {path}")
        kind = payload[offset + 4:offset + 8]
        expected_crc = struct.unpack_from(">I", payload, end - 4)[0]
        require(zlib.crc32(payload[offset + 4:end - 4]) == expected_crc, f"Damaged PNG chunk CRC: {path}")
        require(kind != b"IHDR" or offset == 8, f"Duplicate PNG IHDR: {path}")
        saw_data = saw_data or (kind == b"IDAT" and length > 0)
        offset = end
        if kind == b"IEND":
            require(length == 0 and offset == len(payload), f"Invalid PNG end/trailing data: {path}")
            saw_end = True
            break
    require(saw_data and saw_end, f"PNG has no image data or complete end: {path}")
    return {"bytes": len(payload), "width": actual_width, "height": actual_height,
            "sha256": hashlib.sha256(payload).hexdigest(), "mtime_ns": stat.st_mtime_ns}


def verify_captures(validation: dict, directory: Path, expected: dict, started_utc: str) -> dict:
    require(validation.get("camera_overrides_axis_constraint") is True, "Runtime camera did not override the aspect-ratio axis")
    require(validation.get("camera_axis_constraint") == "MaintainXFOV", "Runtime camera did not maintain horizontal FOV")
    fov = validation.get("comparison_horizontal_fov_degrees")
    require(isinstance(fov, (int, float)) and math.isfinite(fov)
            and abs(fov - expected["horizontal_fov_degrees"]) <= 0.001, "Runtime comparison FOV differs from route data")
    shots = validation.get("source_camera_screenshots", [])
    require(isinstance(shots, list) and len(shots) == len(expected["waypoints"]), "Capture receipt does not cover every source camera")
    verified = []
    for index, (shot, waypoint) in enumerate(zip(shots, expected["waypoints"], strict=True)):
        relative = f"Screenshots/room_{index + 1:02d}_frame_{waypoint['frame']:04d}.png"
        require(shot.get("written") is True and shot.get("index") == index
                and shot.get("name") == waypoint["name"] and shot.get("path") == relative,
                f"Capture identity/path differs from source camera {index}")
        path = directory / relative
        require(path.resolve().is_relative_to(directory.resolve()), "Capture resolves outside this invocation: " + str(path))
        item = png_capture_receipt(path, expected["width"], expected["height"], started_utc)
        require(item["bytes"] == shot.get("bytes"), "Capture byte count differs from native receipt: " + relative)
        verified.append({"index": index, "name": waypoint["name"], "path": relative, **item})
    return {"scope": "Fresh PNG signature, chunk framing/CRC, dimensions, file hashes and reported camera settings; no visual-identity claim",
            "horizontal_fov_degrees": fov, "camera_axis_constraint": "MaintainXFOV",
            "camera_overrides_axis_constraint": True, "files": verified}


def running_editor_processes() -> list[str]:
    result = subprocess.run(["/bin/ps", "-axo", "pid=,comm="], capture_output=True, text=True, check=True)
    matches = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2 and Path(parts[1]).name in {"UnrealEditor", "UnrealEditor-Cmd"}:
            matches.append(line.strip())
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["build", "import", "look", "editor", "play", "package", "validate"])
    parser.add_argument("--engine", type=Path)
    parser.add_argument("--runtime", choices=["editor", "packaged"], default="editor")
    parser.add_argument("--archive", type=Path, default=OUTPUT / "package")
    parser.add_argument("--reuse-cook", action="store_true", help="Package using retained Mac cooked content; suitable only for runtime code/config changes, not content or shader changes")
    parser.add_argument("--app", type=Path)
    parser.add_argument("--manifest", type=Path, default=OUTPUT / "export/manifest.json")
    parser.add_argument("--reuse-receipt", type=Path, help="Reuse completed native assets from a matching import receipt, rechecking the current scene")
    parser.add_argument("--look-config", type=Path, default=UNREAL / "look.daylight.json")
    parser.add_argument("--import-receipt", type=Path, help="Completed native import receipt required by the look stage")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--captures", action="store_true", help="Capture every source camera during validation")
    parser.add_argument("--benchmark", action="store_true", help="Measure gameplay after native asset/focus warmup with engine caps disabled; presentation may remain synchronized")
    parser.add_argument("--fullscreen", action="store_true", help="Request true fullscreen at --width x --height for play/validate; actual viewport mode and dimensions may depend on the display")
    parser.add_argument("--render-cvar", type=parse_render_cvar, action="append", default=[], metavar="NAME=NUMBER",
                        help="Repeatable numeric r.* or sg.* tuning override for play/validate; benchmark caps are forced off afterward")
    parser.add_argument("--survey", action="store_true", help="Run and validate a fresh static floor/capsule survey before movement tests")
    parser.add_argument("--route-data", type=Path, help="Load a separate candidate walkthrough JSON for play/validation without changing shipped data")
    parser.add_argument("--allow-running-editor", action="store_true", help="Owner explicitly accepts another active editor; never closes its scenes")
    parser.add_argument("--min-free-gib", type=float, default=8, help="Minimum free disk before import/package; no data is deleted")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    require(not args.survey or args.stage == "validate", "--survey applies only to the validate stage.")
    require(not args.benchmark or (args.stage == "validate" and not args.captures and not args.survey), "--benchmark requires validate without captures or survey.")
    require(not args.render_cvar or args.stage in {"play", "validate"}, "--render-cvar applies only to play or validate.")
    require(not args.fullscreen or args.stage in {"play", "validate"}, "--fullscreen applies only to play or validate.")
    require(not args.reuse_cook or args.stage == "package", "--reuse-cook applies only to package.")
    require(not args.route_data or args.stage in {"play", "validate"}, "--route-data applies only to play or validate.")
    require(not args.reuse_receipt or args.stage == "import", "--reuse-receipt applies only to import.")
    require(not args.import_receipt or args.stage == "look", "--import-receipt applies only to look.")
    if args.stage == "look":
        require(args.import_receipt and args.import_receipt.is_file(), "Look stage requires a completed --import-receipt file.")
        require(args.look_config.is_file(), f"Missing look configuration: {args.look_config}")
    if args.reuse_receipt:
        require(args.reuse_receipt.is_file(), f"Missing previous import receipt: {args.reuse_receipt}")
    if args.route_data:
        require(args.route_data.is_file(), f"Missing candidate route data: {args.route_data}")
    require(sys.platform == "darwin" and platform.machine() == "arm64", "This native target requires an Apple Silicon Mac.")
    require(PROJECT.is_file(), f"Missing project: {PROJECT}")
    require(args.width >= 640 and args.height >= 360, "Window size must be at least 640x360.")
    packaged_runtime = args.stage in {"play", "validate"} and args.runtime == "packaged"
    engine, version, editor = None, None, None
    if packaged_runtime:
        # The packaged app does not require an installed editor or toolchain.
        with contextlib.suppress(RuntimeError):
            engine, version = engine_root(args.engine)
    else:
        engine, version = engine_root(args.engine)
        editor = engine / "Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
        require(editor.is_file(), f"Missing installed editor executable: {editor}")
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    evidence = OUTPUT / "runs" / f"{run_id}_{args.stage}_{args.runtime}"
    native_evidence = evidence
    native_route_path = args.route_data.resolve() if args.route_data else None
    env = os.environ.copy()
    app: Path | None = None
    route_names: list[str] | None = None
    expected_captures: dict | None = None
    if args.stage == "build":
        command = [
            str(engine / "Engine/Build/BatchFiles/Mac/Build.sh"),
            "BastideWalkEditor",
            "Mac",
            "Development",
            str(PROJECT),
            "-NoHotReloadFromIDE",
            "-MaxParallelActions=3",
        ]
    elif args.stage == "import":
        require(args.manifest.is_file(), f"Missing export manifest: {args.manifest}")
        env.update(
            BASTIDE_EXPORT_MANIFEST=str(args.manifest.resolve()), BASTIDE_IMPORT_RECEIPT=str(evidence / "import-receipt.json"), BASTIDE_QUIT_AFTER_IMPORT="1"
        )
        if args.reuse_receipt:
            env["BASTIDE_REUSE_IMPORT_RECEIPT"] = str(args.reuse_receipt.resolve())
        else:
            env.pop("BASTIDE_REUSE_IMPORT_RECEIPT", None)
        command = [
            str(editor),
            str(PROJECT),
            f"-ExecutePythonScript={UNREAL / 'tools/import_unreal.py'}",
            "-unattended",
            "-NoSplash",
            f"-abslog={evidence / 'engine.log'}",
        ]
    elif args.stage == "look":
        require(args.manifest.is_file(), f"Missing export manifest: {args.manifest}")
        env.update(BASTIDE_EXPORT_MANIFEST=str(args.manifest.resolve()),
                   BASTIDE_LOOK_CONFIG=str(args.look_config.resolve()),
                   BASTIDE_LOOK_IMPORT_RECEIPT=str(args.import_receipt.resolve()),
                   BASTIDE_LOOK_RECEIPT=str(evidence / "look-receipt.json"),
                   BASTIDE_QUIT_AFTER_IMPORT="1")
        command = [str(editor), str(PROJECT),
                   f"-ExecutePythonScript={UNREAL / 'tools/apply_unreal_look.py'}",
                   "-unattended", "-NoSplash", f"-abslog={evidence / 'engine.log'}"]
    elif args.stage == "package":
        require((PROJECT.parent / "Content/Bastide/Maps/Walkthrough.umap").is_file(), "Walkthrough map is missing. Complete import first.")
        if args.reuse_cook:
            require((PROJECT.parent / "Saved/Cooked/Mac/ue.projectstore").is_file(), "--reuse-cook requires retained Saved/Cooked/Mac/ue.projectstore; run a full package first.")
        command = [
            str(engine / "Engine/Build/BatchFiles/RunUAT.sh"),
            "BuildCookRun",
            f"-project={PROJECT}",
            "-noP4",
            "-platform=Mac",
            "-clientconfig=Development",
            "-target=BastideWalk",
            "-specifiedarchitecture=arm64",
            "-clientarchitecture=arm64",
            "-build",
            "-skipcook" if args.reuse_cook else "-cook",
            "-stage",
            "-pak",
            "-nodebuginfo",
            "-package",
            "-archive",
            f"-archivedirectory={args.archive.resolve()}",
            "-unattended",
            "-utf8output",
        ]
    elif args.stage == "editor":
        command = [str(editor), str(PROJECT), "-NoSplash", f"-abslog={evidence / 'engine.log'}"]
    else:
        if args.runtime == "packaged":
            app, executable = app_executable(args.archive, args.app)
            native_evidence = packaged_evidence_directory(app, evidence.name)
            if args.route_data:
                native_route_path = native_evidence / "Input/routes.json"
            command = [str(executable)]
        else:
            require((PROJECT.parent / "Content/Bastide/Maps/Walkthrough.umap").is_file(), "Walkthrough map is missing. Complete import first.")
            command = [str(editor), str(PROJECT), "/Game/Bastide/Maps/Walkthrough", "-game"]
        command += (["-fullscreen", "-ForceRes", f"-Res={args.width}x{args.height}f"] if args.fullscreen
                    else ["-windowed", f"-ResX={args.width}", f"-ResY={args.height}"])
        command += ["-NoSplash", f"-abslog={native_evidence / 'engine.log'}"]
        if args.route_data:
            command.append(f"-BastideRouteData={native_route_path}")
        render_commands = list(args.render_cvar)
        if args.stage == "validate":
            route_path = args.route_data or (packaged_app_files(app)["data"]["walkthrough.json"] if app else PROJECT.parent / "Content/Data/walkthrough.json")
            route_names = expected_route_names(route_path)
            if args.captures:
                waypoint_path = packaged_app_files(app)["data"]["waypoints.json"] if app else PROJECT.parent / "Content/Data/waypoints.json"
                expected_captures = capture_expectations(route_path, waypoint_path, args.width, args.height)
            command += ["-BastideAudit", "-BastideAutoExit", f"-BastideValidationDir={native_evidence / 'Validation'}"]
            if args.benchmark:
                # Unreal's built-in -benchmark enables fixed timestep, so use a
                # project-specific flag and real wall-clock gameplay samples.
                command.append("-BastideBenchmark")
                render_commands += ["r.VSync 0", "t.MaxFPS 0"]
            if args.captures:
                command.append("-BastideCaptureAll")
            if args.survey:
                command.append("-BastideSurvey")
        if render_commands:
            command.append("-ExecCmds=" + ",".join(render_commands))
    if args.dry_run:
        print(json.dumps({"dry_run": True, "command": command, "evidence": str(evidence), "engine_build": version,
                          "reuse_import_receipt": str(args.reuse_receipt.resolve()) if args.reuse_receipt else None}, indent=2))
        return 0
    if args.stage in {"build", "import", "look", "editor", "package"} or args.runtime == "editor":
        running = running_editor_processes()
        require(
            not running or args.allow_running_editor,
            "Another Unreal editor is running; preserve its scenes. Owner can use --allow-running-editor. Processes: " + "; ".join(running),
        )
    if args.stage in {"import", "look", "package"}:
        free = shutil.disk_usage(REPOSITORY).free / 1024**3
        require(free >= args.min_free_gib, f"Only {free:.1f} GiB free, below {args.min_free_gib:.1f} GiB threshold. No source or cache was deleted.")
    evidence.mkdir(parents=True, exist_ok=False)
    if native_evidence != evidence:
        native_evidence.mkdir(parents=True, exist_ok=False)
        if args.route_data:
            native_route_path.parent.mkdir()
            shutil.copy2(args.route_data, native_route_path)
            require(sha(native_route_path) == sha(args.route_data), "Sandbox route input differs from requested data")
    receipt = {
        "schema": "bastide.native-stage.v1",
        "stage": args.stage,
        "runtime": args.runtime,
        "status": "running",
        "command": command,
        "started_utc": datetime.now(UTC).isoformat(),
        "platform": platform_receipt(engine, version),
        "input_files": snapshot_inputs(),
        "evidence_directory": str(evidence),
        "native_evidence_directory": str(native_evidence),
        "capture_requested": args.captures,
        "gameplay_benchmark_requested": args.benchmark,
        "requested_window_mode": ("Fullscreen" if args.fullscreen else "Windowed") if args.stage in {"play", "validate"} else None,
        "render_cvar_overrides": args.render_cvar,
        "survey_requested": args.survey,
        "reused_cook": args.reuse_cook,
    }
    if args.reuse_cook:
        project_store = PROJECT.parent / "Saved/Cooked/Mac/ue.projectstore"
        receipt["retained_project_store"] = {"path": str(project_store), "sha256": sha(project_store)}
    if args.manifest.is_file():
        receipt["export_manifest"] = {"path": str(args.manifest), "sha256": sha(args.manifest)}
    if args.route_data:
        receipt["route_data_override"] = {"path": str(args.route_data.resolve()), "sha256": sha(args.route_data),
                                          "native_path": str(native_route_path)}
    if args.reuse_receipt:
        receipt["reused_import_receipt"] = {"path": str(args.reuse_receipt.resolve()), "sha256": sha(args.reuse_receipt)}
    if args.stage == "look":
        receipt["look_config"] = {"path": str(args.look_config.resolve()), "sha256": sha(args.look_config)}
        receipt["completed_import_receipt"] = {"path": str(args.import_receipt.resolve()), "sha256": sha(args.import_receipt)}
    if app:
        receipt["packaged_app"] = packaged_app_receipt(app)
    if route_names:
        receipt["expected_movement_routes"] = route_names
    if expected_captures:
        receipt["expected_captures"] = expected_captures
    receipt_path = evidence / "stage-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Native {args.stage}; evidence: {evidence}", flush=True)
    started = time.monotonic()
    result_code = 1
    native_output_copied = False
    try:
        with (evidence / "process.log").open("w") as log:
            process = subprocess.Popen(
                command, cwd=engine or UNREAL, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace", bufsize=1
            )
            try:
                for line in process.stdout:
                    log.write(line)
                    log.flush()
                    print(line, end="", flush=True)
                exit_code = process.wait()
            except KeyboardInterrupt:
                process.terminate()
                exit_code = process.wait()
                receipt["process_exit_code"] = exit_code
                raise RuntimeError("Native stage interrupted; inspect retained logs") from None
        receipt["process_exit_code"] = exit_code
        receipt["copied_native_outputs"] = copy_native_evidence(native_evidence, evidence)
        native_output_copied = True
        require(exit_code == 0, f"Native process returned {exit_code}; inspect {evidence / 'process.log'}")
        receipt["status"] = "process_completed"
        if args.stage == "import":
            import_result = json.loads((evidence / "import-receipt.json").read_text())
            require(import_result.get("status") == "complete", "Import receipt does not report completion")
            require(not import_result.get("selection", {}).get("partial", True), "Import contains only a partial selection")
            receipt["import_counts"] = import_result.get("counts")
            receipt["status"] = "import_completed"
        elif args.stage == "look":
            look_result = json.loads((evidence / "look-receipt.json").read_bytes())
            require(look_result.get("status") == "complete", "Look receipt does not report completion")
            receipt["status"] = "look_applied_unreviewed"
            receipt["look_receipt"] = str(evidence / "look-receipt.json")
        elif args.stage == "build":
            target = PROJECT.parent / "Binaries/Mac/BastideWalkEditor.target"
            require(target.is_file(), "Compiler returned zero but project editor target receipt is missing")
            receipt["target_receipt"] = json.loads(target.read_text())
            receipt["status"] = "editor_module_built"
        elif args.stage == "package":
            app, executable = app_executable(args.archive, args.app)
            receipt.update(status="packaged_unplayed", packaged_app=packaged_app_receipt(app))
            for filename, staged in receipt["packaged_app"]["staged_data"].items():
                expected = receipt["input_files"][f"BastideWalk/Content/Data/{filename}"]["sha256"]
                require(staged["sha256"] == expected, f"Packaged {filename} differs from source data at the start of packaging")
            receipt["architecture"] = probe(["/usr/bin/lipo", "-archs", str(executable)])
            receipt["codesign"] = probe(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)])
            require(receipt["codesign"]["exit_code"] == 0, "Packaged app signing verification failed")
            require("arm64" in receipt["architecture"]["stdout"], "Packaged app lacks arm64 executable")
        elif args.stage == "validate":
            validation = json.loads((evidence / "Validation/runtime-audit.json").read_bytes())
            require(validation.get("route_data_loaded") is True, "Runtime did not load a valid route-data JSON")
            if args.route_data:
                require(
                    Path(validation.get("route_data_path", "")).resolve() == native_route_path.resolve(),
                    "Runtime loaded a different route-data JSON from the requested candidates",
                )
            require(len(validation.get("bookmarks", [])) == 26, "Runtime audit did not include all26 source bookmarks")
            require(validation.get("packaged_game") == (args.runtime == "packaged"), "Runtime receipt packaged/editor identity does not match requested test")
            require(validation.get("actual_routes_status", "").startswith("completed"), "Actual route tests did not finish")
            if args.survey:
                survey_path = evidence / "Validation/navigation-survey.json"
                survey = json.loads(survey_path.read_text())
                require(survey.get("schema") == "bastide.navigation-survey.v1", "Unexpected navigation survey schema")
                require(survey.get("status") == "static_probes_completed", "Static navigation survey did not complete")
                require(
                    "static" in survey.get("scope", "").lower() and "not proof" in survey.get("scope", "").lower(),
                    "Survey scope lacks the static-probe limitation",
                )
                require(survey.get("packaged_game") == (args.runtime == "packaged"), "Survey runtime identity differs from requested test")
                require(
                    survey.get("grid_counts_xy") == [111, 164] and survey.get("spacing_cm") == 30,
                    "Survey grid dimensions or spacing differ from configured contract",
                )
                require(survey.get("grid_origin_cm") == [-1100, -3200], "Survey grid origin differs from configured contract")
                levels = survey.get("levels", [])
                require(len(levels) == 2 and [level.get("floor_z") for level in levels] == [0, 330], "Survey did not probe both floor datums")
                require(
                    survey.get("tested_count") == 36408 and sum(level.get("tested_count", 0) for level in levels) == 36408, "Survey has incomplete probe counts"
                )
                for level in levels:
                    cells = level.get("cells", [])
                    require(level.get("tested_count") == 18204, "Survey level has incomplete probe count")
                    require(level.get("clear_count") == len(cells), "Survey clear count differs from emitted cells")
                    require(len({(cell["ix"], cell["iy"]) for cell in cells}) == len(cells), "Survey contains duplicate clear cells")
                    require(
                        sum(level.get(key, 0) for key in ["clear_count", "no_floor_count", "steep_floor_count", "blocked_count"]) == level["tested_count"],
                        "Survey rejection counts do not reconcile",
                    )
                stamp = datetime.fromisoformat(survey["timestamp_utc"].replace("Z", "+00:00"))
                require(stamp >= datetime.fromisoformat(receipt["started_utc"]), "Survey predates this native invocation")
                receipt["navigation_survey"] = {
                    "status": "static_probes_completed",
                    "sha256": sha(survey_path),
                    "tested_count": survey["tested_count"],
                    "clear_counts": [level["clear_count"] for level in levels],
                    "native_connected_route_claim": False,
                }
            if args.captures:
                receipt["capture_verification"] = verify_captures(validation, evidence / "Validation", expected_captures, receipt["started_utc"])
            routes = validation.get("actual_walking_routes", [])
            require([route.get("name") for route in routes] == route_names, "Native movement results do not cover every configured route in order")
            receipt["validation_counts"] = {
                "bookmarks_clear": sum(b["walking_target_clear"] for b in validation["bookmarks"]),
                "routes_passed": sum(r["passed"] for r in routes),
                "routes_total": len(routes),
                "screenshots": len(validation.get("source_camera_screenshots", [])),
            }
            findings = (
                receipt["validation_counts"]["bookmarks_clear"] < 26
                or any(not r["passed"] for r in routes)
                or not validation.get("safe_spawn_supported", False)
                or not validation.get("safe_spawn_clear", False)
            )
            if args.benchmark:
                receipt["gameplay_benchmark"] = gameplay_benchmark_receipt(validation.get("gameplay_performance", {}), route_names,
                                                                          args.width, args.height, "Fullscreen" if args.fullscreen else None)
                findings = findings or not receipt["gameplay_benchmark"]["all_steady_60_targets_met"]
            receipt["status"] = "completed_with_findings" if findings else "configured_runtime_checks_passed"
            result_code = 2 if findings else 0
        if args.stage != "validate":
            result_code = 0
    except Exception as error:
        receipt.update(status="failed", error=str(error))
        print(str(error), file=sys.stderr)
    finally:
        if not native_output_copied:
            try:
                receipt["copied_native_outputs"] = copy_native_evidence(native_evidence, evidence)
            except Exception as error:
                receipt["native_output_copy_error"] = str(error)
                receipt["status"] = "failed"
                result_code = 1
        receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
        receipt["finished_utc"] = datetime.now(UTC).isoformat()
        receipt["free_disk_bytes_after"] = shutil.disk_usage(REPOSITORY).free
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"Stage status: {receipt['status']}. Receipt: {receipt_path}", flush=True)
    return result_code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"Bastide: {error}", file=sys.stderr)
        raise SystemExit(1) from None
