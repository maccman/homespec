"""Native-process ownership regressions; no Unreal process is launched."""

import argparse
import copy
import hashlib
import json
import os
import plistlib
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from projects.bastide_de_flechon.unreal.tools import run_unreal


def test_editor_services_helper_does_not_block_native_stage(monkeypatch):
    output = " 95824 /Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditorServices.app/Contents/MacOS/UnrealEditorServices\n"
    monkeypatch.setattr(run_unreal.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=output))
    assert run_unreal.running_editor_processes() == []


def test_real_editor_and_commandlet_processes_are_still_protected(monkeypatch):
    output = (
        " 101 /Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor\n"
        " 102 /Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd\n"
        " 103 /Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/ShaderCompileWorker\n"
        " 104 /Applications/UnrealEditorServices.app/Contents/MacOS/UnrealEditorServices\n"
    )
    monkeypatch.setattr(run_unreal.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=output))
    matches = run_unreal.running_editor_processes()
    assert [line.split(maxsplit=1)[0] for line in matches] == ["101", "102"]


def make_app(path, *, cooked=True, room_data=True, iostore=False):
    """Synthetic filesystem contract, not an executable or native build."""
    (path / "Contents/MacOS").mkdir(parents=True)
    (path / "Contents/MacOS/BastideWalk").write_bytes(b"synthetic executable placeholder")
    with (path / "Contents/Info.plist").open("wb") as stream:
        plistlib.dump({"CFBundleExecutable": "BastideWalk", "CFBundleIdentifier": "com.synthetic.BastideWalk"}, stream)
    content = path / "Contents/UE/BastideWalk/Content"
    if cooked:
        (content / "Paks").mkdir(parents=True)
        (content / "Paks" / ("pakchunk0.utoc" if iostore else "pakchunk0.pak")).write_bytes(b"synthetic archive placeholder")
    if room_data:
        (content / "Data").mkdir(parents=True)
        (content / "Data/waypoints.json").write_text("[]")
        (content / "Data/walkthrough.json").write_text(json.dumps({"routes": [{"name": "default stair", "points_cm": [[0, 0, 90.5], [30, 0, 90.5]]}]}))
    return path


def test_compiled_app_is_not_mistaken_for_packaged_walkthrough(tmp_path):
    compiled = make_app(tmp_path / "BastideWalk.app", cooked=False)
    with pytest.raises(RuntimeError, match="no cooked"):
        run_unreal.app_executable(tmp_path, compiled)


def test_discovery_skips_nested_incomplete_target_bundle(tmp_path):
    complete = make_app(tmp_path / "Mac/BastideWalk.app")
    make_app(tmp_path / "Mac/BastideWalk/Binaries/Mac/BastideWalk.app", cooked=False)
    app, executable = run_unreal.app_executable(tmp_path, None)
    assert app == complete.resolve()
    assert executable == complete.resolve() / "Contents/MacOS/BastideWalk"


def test_packaged_app_requires_staged_room_data(tmp_path):
    incomplete = make_app(tmp_path / "BastideWalk.app", room_data=False)
    with pytest.raises(RuntimeError, match="Content/Data/waypoints.json"):
        run_unreal.packaged_app_files(incomplete)


def test_iostore_index_requires_payload(tmp_path):
    incomplete = make_app(tmp_path / "BastideWalk.app", iostore=True)
    with pytest.raises(RuntimeError, match="IoStore payload missing"):
        run_unreal.packaged_app_files(incomplete)


def test_multiple_complete_archives_require_explicit_selection(tmp_path):
    first = make_app(tmp_path / "first/BastideWalk.app")
    make_app(tmp_path / "second/BastideWalk.app")
    with pytest.raises(RuntimeError, match="Multiple complete packaged apps"):
        run_unreal.app_executable(tmp_path, None)
    assert run_unreal.app_executable(tmp_path, first)[0] == first.resolve()


def test_packaged_candidate_validation_keeps_path_with_spaces_and_needs_no_engine(tmp_path, monkeypatch, capsys):
    app = make_app(tmp_path / "archive with spaces/BastideWalk.app")
    project = tmp_path / "Project/BastideWalk.uproject"
    project.parent.mkdir()
    project.write_text("{}")
    routes = tmp_path / "candidate routes.json"
    routes.write_text(json.dumps({"routes": [{"name": "continuous surveyed chain", "points_cm": [[0, 0, 90.5], [60, 0, 90.5]]}]}))
    monkeypatch.setattr(run_unreal, "PROJECT", project)
    monkeypatch.setattr(run_unreal.sys, "platform", "darwin")
    monkeypatch.setattr(run_unreal.platform, "machine", lambda: "arm64")

    def no_engine(*args):
        raise RuntimeError("Synthetic test has no installed Unreal editor")

    def no_process(*args, **kwargs):
        raise AssertionError("Dry-run must not launch any native process")

    monkeypatch.setattr(run_unreal, "engine_root", no_engine)
    monkeypatch.setattr(run_unreal.subprocess, "Popen", no_process)
    monkeypatch.setattr(
        sys, "argv", ["run_unreal.py", "validate", "--runtime", "packaged", "--app", str(app), "--route-data", str(routes), "--survey", "--dry-run"]
    )
    assert run_unreal.main() == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["command"][0] == str(app / "Contents/MacOS/BastideWalk")
    native = run_unreal.packaged_evidence_directory(app, Path(plan["evidence"]).name)
    assert f"-BastideRouteData={native / 'Input/routes.json'}" in plan["command"]
    assert f"-abslog={native / 'engine.log'}" in plan["command"]
    assert f"-BastideValidationDir={native / 'Validation'}" in plan["command"]
    assert not native.exists(), "Dry-run must not stage files or create the container directory"
    assert "-BastideSurvey" in plan["command"]
    assert "-BastideAudit" in plan["command"]
    assert "-BastideAutoExit" in plan["command"]
    assert plan["engine_build"] is None


@pytest.mark.skipif(sys.platform != "darwin", reason="Finder launcher uses native macOS PlistBuddy")
def test_finder_launcher_resolves_complete_app_without_launching(tmp_path):
    app = make_app(tmp_path / "package with spaces/Mac/BastideWalk.app")
    make_app(tmp_path / "package with spaces/Mac/BastideWalk/Binaries/Mac/BastideWalk.app", cooked=False)
    launcher = Path(run_unreal.__file__).resolve().parents[1] / "Launch Walkthrough.command"
    env = {**os.environ, "BASTIDE_PACKAGE_ARCHIVE": str(tmp_path / "package with spaces")}
    env.pop("BASTIDE_WALKTHROUGH_APP", None)
    result = subprocess.run(["/bin/zsh", str(launcher), "--resolve-only"], env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.strip() == str(app)


@pytest.mark.skipif(sys.platform != "darwin", reason="Finder launcher uses native macOS PlistBuddy")
def test_finder_launcher_rejects_compiled_app_without_hanging(tmp_path):
    make_app(tmp_path / "BastideWalk.app", cooked=False)
    launcher = Path(run_unreal.__file__).resolve().parents[1] / "Launch Walkthrough.command"
    env = {**os.environ, "BASTIDE_PACKAGE_ARCHIVE": str(tmp_path)}
    env.pop("BASTIDE_WALKTHROUGH_APP", None)
    result = subprocess.run(["/bin/zsh", str(launcher), "--resolve-only"], env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "No complete packaged" in result.stdout


def make_png(width=4, height=3):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    rows = b"".join(b"\x00" + bytes([30, 90, 150]) * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


CAPTURE_START = "2023-11-14T22:13:20+00:00"
CAPTURE_FRESH_NS = 1_700_000_010_000_000_000


def write_capture(path, payload=None, mtime_ns=CAPTURE_FRESH_NS):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(make_png() if payload is None else payload)
    os.utime(path, ns=(mtime_ns, mtime_ns))
    return path


def test_png_receipt_hashes_actual_fresh_content_and_dimensions(tmp_path):
    path = write_capture(tmp_path / "image.png")
    receipt = run_unreal.png_capture_receipt(path, 4, 3, CAPTURE_START)
    assert receipt == {"bytes": len(make_png()), "width": 4, "height": 3,
                       "sha256": hashlib.sha256(make_png()).hexdigest(), "mtime_ns": CAPTURE_FRESH_NS}


@pytest.mark.parametrize("payload", [b"not a PNG", make_png()[:25], make_png()[:-12],
                                     make_png()[:45] + bytes([make_png()[45] ^ 1]) + make_png()[46:]])
def test_damaged_or_incomplete_png_is_rejected(tmp_path, payload):
    path = write_capture(tmp_path / "damaged.png", payload)
    with pytest.raises(RuntimeError, match="PNG"):
        run_unreal.png_capture_receipt(path, 4, 3, CAPTURE_START)


def test_wrong_screenshot_dimensions_and_stale_files_are_rejected(tmp_path):
    path = write_capture(tmp_path / "image.png")
    with pytest.raises(RuntimeError, match="dimensions"):
        run_unreal.png_capture_receipt(path, 16, 10, CAPTURE_START)
    write_capture(path, mtime_ns=1_699_999_999_000_000_000)
    with pytest.raises(RuntimeError, match="predates"):
        run_unreal.png_capture_receipt(path, 4, 3, CAPTURE_START)


def capture_case(tmp_path):
    expected = {"width": 4, "height": 3, "horizontal_fov_degrees": 73.739795,
                "waypoints": [{"name": "Garden", "frame": 1}, {"name": "Salon", "frame": 97}]}
    validation = {"camera_overrides_axis_constraint": True, "camera_axis_constraint": "MaintainXFOV",
                  "comparison_horizontal_fov_degrees": 73.73979187011719, "source_camera_screenshots": []}
    for index, waypoint in enumerate(expected["waypoints"]):
        relative = f"Screenshots/room_{index + 1:02d}_frame_{waypoint['frame']:04d}.png"
        path = write_capture(tmp_path / relative)
        validation["source_camera_screenshots"].append(
            {"index": index, "name": waypoint["name"], "path": relative, "bytes": path.stat().st_size, "written": True})
    return expected, validation


def test_verified_captures_retain_individual_file_hashes_and_camera_evidence(tmp_path):
    expected, validation = capture_case(tmp_path)
    receipt = run_unreal.verify_captures(validation, tmp_path, expected, CAPTURE_START)
    assert receipt["camera_axis_constraint"] == "MaintainXFOV"
    assert receipt["camera_overrides_axis_constraint"] is True
    assert len(receipt["files"]) == 2
    assert all(row["sha256"] == hashlib.sha256(make_png()).hexdigest() for row in receipt["files"])
    assert [row["name"] for row in receipt["files"]] == ["Garden", "Salon"]


@pytest.mark.parametrize("change", [{"camera_overrides_axis_constraint": False}, {"camera_axis_constraint": "MaintainYFOV"},
                                     {"comparison_horizontal_fov_degrees": 68.0387}, {"comparison_horizontal_fov_degrees": float("nan")}])
def test_camera_constraint_and_horizontal_fov_must_match_capture_contract(tmp_path, change):
    expected, validation = capture_case(tmp_path)
    validation.update(change)
    with pytest.raises(RuntimeError, match="camera|FOV"):
        run_unreal.verify_captures(validation, tmp_path, expected, CAPTURE_START)


def test_written_flags_cannot_hide_missing_duplicate_or_misreported_captures(tmp_path):
    expected, original = capture_case(tmp_path)
    for change in (lambda shots: shots.pop(), lambda shots: shots.__setitem__(1, shots[0]),
                   lambda shots: shots[0].update(bytes=1), lambda shots: shots[0].update(path="../stale.png")):
        validation = copy.deepcopy(original)
        change(validation["source_camera_screenshots"])
        with pytest.raises(RuntimeError):
            run_unreal.verify_captures(validation, tmp_path, expected, CAPTURE_START)
    (tmp_path / original["source_camera_screenshots"][0]["path"]).unlink()
    with pytest.raises(FileNotFoundError):
        run_unreal.verify_captures(original, tmp_path, expected, CAPTURE_START)


def test_capture_expectations_freeze_route_fov_and_source_camera_data(tmp_path):
    routes = tmp_path / "walkthrough.json"
    points = tmp_path / "waypoints.json"
    routes.write_text(json.dumps({"camera_fov_degrees": 73.739795}))
    points.write_text(json.dumps([{"name": f"Room {index}", "frame": 1 + index * 96} for index in range(26)]))
    expected = run_unreal.capture_expectations(routes, points, 1600, 1000)
    routes.write_text(json.dumps({"camera_fov_degrees": 50}))
    assert expected["horizontal_fov_degrees"] == 73.739795
    assert expected["route_data_sha256"] != hashlib.sha256(routes.read_bytes()).hexdigest()
    assert (expected["width"], expected["height"]) == (1600, 1000)
    assert len(expected["waypoints"]) == 26


@pytest.mark.parametrize(("value", "command"), [("r.ScreenPercentage=67", "r.ScreenPercentage 67"),
                                               ("sg.ShadowQuality=0", "sg.ShadowQuality 0"),
                                               ("r.Test=-1.25e-2", "r.Test -1.25e-2"),
                                               ("r.Test=+.5", "r.Test +.5")])
def test_render_overrides_accept_only_numeric_console_arguments(value, command):
    assert run_unreal.parse_render_cvar(value) == command


@pytest.mark.parametrize("value", ["t.MaxFPS=30", "foo.Bar=1", "r.Test=nan", "r.Test=inf", "r.Test=1e999",
                                   "r.Test=true", "r.Test=1,quit", "r.Test=1;quit", "r.Test=1\nquit",
                                   "r.Test 1=0", "r.Test=1 2", "r.Test=0=1", "r.=1", "r.Test="])
def test_render_overrides_reject_nonfinite_nonrender_and_command_injection(value):
    with pytest.raises(argparse.ArgumentTypeError):
        run_unreal.parse_render_cvar(value)


@pytest.mark.parametrize("stage", ["build", "import", "look", "editor", "package"])
def test_render_overrides_are_rejected_before_other_stage_work(stage, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_unreal.py", stage, "--render-cvar", "r.ShadowQuality=0", "--dry-run"])
    with pytest.raises(RuntimeError, match="only to play or validate"):
        run_unreal.main()


@pytest.mark.parametrize("fullscreen", [False, True])
@pytest.mark.parametrize(("stage", "benchmark"), [("play", False), ("validate", False), ("validate", True)])
def test_packaged_render_overrides_use_one_exec_argument_and_benchmark_caps_last(tmp_path, monkeypatch, capsys, stage, benchmark, fullscreen):
    app = make_app(tmp_path / "BastideWalk.app")
    project = tmp_path / "BastideWalk.uproject"
    project.write_text("{}")
    monkeypatch.setattr(run_unreal, "PROJECT", project)
    monkeypatch.setattr(run_unreal.sys, "platform", "darwin")
    monkeypatch.setattr(run_unreal.platform, "machine", lambda: "arm64")

    def no_engine(*args):
        raise RuntimeError("No engine required for this packaged dry-run")

    def no_process(*args, **kwargs):
        raise AssertionError("Dry-run launched a process")

    monkeypatch.setattr(run_unreal, "engine_root", no_engine)
    monkeypatch.setattr(run_unreal.subprocess, "Popen", no_process)
    args = ["run_unreal.py", stage, "--runtime", "packaged", "--app", str(app), "--dry-run",
            "--render-cvar", "sg.ShadowQuality=1", "--render-cvar", "sg.ShadowQuality=0",
            "--render-cvar", "r.ScreenPercentage=67", "--render-cvar", "r.VSync=1"]
    if benchmark:
        args.append("--benchmark")
    if fullscreen:
        args.append("--fullscreen")
    monkeypatch.setattr(sys, "argv", args)
    assert run_unreal.main() == 0
    command = json.loads(capsys.readouterr().out)["command"]
    expected = "-ExecCmds=sg.ShadowQuality 1,sg.ShadowQuality 0,r.ScreenPercentage 67,r.VSync 1"
    if benchmark:
        expected += ",r.VSync 0,t.MaxFPS 0"
    assert [arg for arg in command if arg.startswith("-ExecCmds=")] == [expected]
    assert ("-BastideBenchmark" in command) is benchmark
    if fullscreen:
        assert "-fullscreen" in command and "-Res=1600x900f" in command
        assert "-ForceRes" in command
        assert "-windowed" not in command
        assert not any(arg.startswith(("-ResX=", "-ResY=")) for arg in command)
    else:
        assert "-windowed" in command and "-ResX=1600" in command and "-ResY=900" in command
        assert "-fullscreen" not in command


def benchmark_case():
    settings = {"app_fixed_time_step": False, "app_benchmarking": False, "engine_fixed_frame_rate": False,
                "engine_smooth_frame_rate": False, "viewport_width": 1600, "viewport_height": 900,
                "cvars": {"r.VSync": 0, "t.MaxFPS": 0}}
    take = {"name": "Interior", "valid_take": True, "warmup_completed": True, "focus_stable": True,
            "assets_stable": True, "clocks_realtime": True, "route_passed": True,
            "raw_frame_ms": [i / 10 for i in range(1, 121)],
            "settings_start": copy.deepcopy(settings), "settings_end": copy.deepcopy(settings)}
    return {"status": "completed", "routes": [take]}


def test_benchmark_recomputes_nearest_rank_and_checks_effective_caps():
    result = run_unreal.gameplay_benchmark_receipt(benchmark_case(), ["Interior"])
    assert result["engine_caps_disabled"] is True
    assert "uncapped" not in result
    assert result["uncapped_render_capacity_verified"] is False
    assert result["all_mean_targets_met"] is True
    assert result["all_steady_60_targets_met"] is True
    assert result["routes"][0]["p95_frame_ms"] == 11.4
    assert result["routes"][0]["mean_fps"] == pytest.approx(1000 / 6.05)


@pytest.mark.parametrize("side", ["settings_start", "settings_end"])
@pytest.mark.parametrize("mutation", ["vsync", "fps_cap", "missing", "fixed", "smooth"])
def test_benchmark_intent_cannot_hide_applied_caps_or_missing_settings(side, mutation):
    document = benchmark_case()
    settings = document["routes"][0][side]
    if mutation == "vsync":
        settings["cvars"]["r.VSync"] = 1
    elif mutation == "fps_cap":
        settings["cvars"]["t.MaxFPS"] = 60
    elif mutation == "missing":
        del document["routes"][0][side]
    elif mutation == "fixed":
        settings["engine_fixed_frame_rate"] = True
    else:
        settings["engine_smooth_frame_rate"] = True
    result = run_unreal.gameplay_benchmark_receipt(document, ["Interior"])
    assert result["engine_caps_disabled"] is False
    assert result["uncapped_render_capacity_verified"] is False
    assert result["all_mean_targets_met"] is False
    assert result["routes"][0]["valid_take"] is False


@pytest.mark.parametrize(("samples", "strict", "steady"), [
    ([1000 / 59.9] * 120, False, True),
    ([1000 / 59.69] * 120, False, False),
    ([10] * 109 + [20] * 11, True, False),
    ([10] * 109 + [17.5] * 11, True, True),
])
def test_steady_nominal_60_requires_both_average_and_tail(samples, strict, steady):
    document = benchmark_case()
    document["routes"][0]["raw_frame_ms"] = samples
    result = run_unreal.gameplay_benchmark_receipt(document, ["Interior"])
    assert result["routes"][0]["valid_take"] is True
    assert result["all_mean_targets_met"] is strict
    assert result["all_steady_60_targets_met"] is steady
    assert result["routes"][0]["mean_fps"] == 1000 * len(samples) / sum(samples)
    assert result["steady_60_criterion"]["mean_fps_minimum"] == 59.7
    assert result["steady_60_criterion"]["p95_frame_ms_maximum"] == 17.5


@pytest.mark.parametrize("side", ["settings_start", "settings_end"])
@pytest.mark.parametrize("mutation", ["size", "missing", "mode"])
def test_fast_benchmark_at_wrong_or_unverified_requested_viewport_is_invalid(side, mutation):
    document = benchmark_case()
    for key in ("settings_start", "settings_end"):
        document["routes"][0][key].update(window_mode="Fullscreen", viewport_width=1280, viewport_height=720)
    settings = document["routes"][0][side]
    if mutation == "size":
        settings.update(viewport_width=800, viewport_height=600)
    elif mutation == "missing":
        del settings["viewport_height"]
    else:
        settings["window_mode"] = "WindowedFullscreen"
    result = run_unreal.gameplay_benchmark_receipt(document, ["Interior"], 1280, 720, "Fullscreen")
    assert result["routes"][0]["mean_fps"] > 60
    assert result["engine_caps_disabled"] is True
    assert result["routes"][0]["valid_take"] is False
    assert result["all_steady_60_targets_met"] is False
    assert result["all_mean_targets_met"] is False


@pytest.mark.parametrize("side", ["settings_start", "settings_end"])
@pytest.mark.parametrize("mutation", [None, "windowed", "borderless", "missing", "pacer", "editor", "not_game", "dropping"])
def test_uncapped_capacity_needs_actual_fullscreen_non_dropping_mac_evidence(side, mutation):
    document = benchmark_case()
    take = document["routes"][0]
    for key in ("settings_start", "settings_end"):
        take[key].update(window_mode="Fullscreen", running_game=True, editor_process=False, mac_frame_pacer_enabled=False)
        take[key]["cvars"]["rhi.Metal.NonBlockingPresent"] = 0
    settings = take[side]
    if mutation == "windowed":
        settings["window_mode"] = "Windowed"
    elif mutation == "borderless":
        settings["window_mode"] = "WindowedFullscreen"
    elif mutation == "missing":
        del settings["mac_frame_pacer_enabled"]
    elif mutation == "pacer":
        settings["mac_frame_pacer_enabled"] = True
    elif mutation == "editor":
        settings["editor_process"] = True
    elif mutation == "not_game":
        settings["running_game"] = False
    elif mutation == "dropping":
        settings["cvars"]["rhi.Metal.NonBlockingPresent"] = 1
    result = run_unreal.gameplay_benchmark_receipt(document, ["Interior"])
    assert result["engine_caps_disabled"] is True
    assert result["all_steady_60_targets_met"] is True
    assert result["uncapped_render_capacity_verified"] is (mutation is None)


@pytest.mark.parametrize("stage", ["build", "import", "look", "editor", "package"])
def test_fullscreen_rejected_outside_runtime(stage, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_unreal.py", stage, "--fullscreen", "--dry-run"])
    with pytest.raises(RuntimeError, match="--fullscreen applies only"):
        run_unreal.main()


@pytest.mark.parametrize("stage", ["build", "import", "look", "editor", "play", "validate"])
def test_reuse_cook_rejected_outside_package(stage, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_unreal.py", stage, "--reuse-cook", "--dry-run"])
    with pytest.raises(RuntimeError, match="--reuse-cook applies only"):
        run_unreal.main()


@pytest.mark.parametrize(("reuse", "retained"), [(False, False), (True, False), (True, True)])
def test_reuse_cook_requires_project_store_and_preserves_build_and_fresh_stage(tmp_path, monkeypatch, capsys, reuse, retained):
    project = tmp_path / "Project/BastideWalk.uproject"
    project.parent.mkdir()
    project.write_text("{}")
    map_path = project.parent / "Content/Bastide/Maps/Walkthrough.umap"
    map_path.parent.mkdir(parents=True)
    map_path.write_bytes(b"synthetic map")
    if retained:
        store = project.parent / "Saved/Cooked/Mac/ue.projectstore"
        store.parent.mkdir(parents=True)
        store.write_bytes(b"synthetic retained store")
    engine = tmp_path / "Engine install"
    editor = engine / "Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor"
    editor.parent.mkdir(parents=True)
    editor.write_bytes(b"synthetic executable placeholder")
    monkeypatch.setattr(run_unreal, "PROJECT", project)
    monkeypatch.setattr(run_unreal, "engine_root", lambda *args: (engine, {}))
    monkeypatch.setattr(run_unreal.sys, "platform", "darwin")
    monkeypatch.setattr(run_unreal.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(run_unreal.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("Dry-run launched a process"))
    args = ["run_unreal.py", "package", "--dry-run"] + (["--reuse-cook"] if reuse else [])
    monkeypatch.setattr(sys, "argv", args)
    if reuse and not retained:
        with pytest.raises(RuntimeError, match="requires retained Saved/Cooked/Mac/ue.projectstore"):
            run_unreal.main()
        return
    assert run_unreal.main() == 0
    command = json.loads(capsys.readouterr().out)["command"]
    assert ("-skipcook" in command) is reuse
    assert ("-cook" in command) is not reuse
    assert {"-build", "-stage", "-pak", "-package", "-archive", "-nodebuginfo", "-platform=Mac",
            "-clientconfig=Development", "-specifiedarchitecture=arm64"} <= set(command)
    assert "-skipstage" not in command and "-skippak" not in command


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), -1, 0])
def test_benchmark_rejects_invalid_raw_samples(bad):
    document = benchmark_case()
    document["routes"][0]["raw_frame_ms"][0] = bad
    with pytest.raises(RuntimeError, match="Invalid wall-clock"):
        run_unreal.gameplay_benchmark_receipt(document, ["Interior"])


@pytest.mark.parametrize("identifier", ["", ".", "..", "...", ".com.example", "com.example.", "com..example",
                                        "../other", "com/example", "com\\example", "com example", None, 123])
def test_packaged_container_rejects_unsafe_bundle_identifiers(tmp_path, identifier):
    app = make_app(tmp_path / "BastideWalk.app")
    with (app / "Contents/Info.plist").open("wb") as stream:
        metadata = {"CFBundleExecutable": "BastideWalk"}
        if identifier is not None:
            metadata["CFBundleIdentifier"] = identifier
        plistlib.dump(metadata, stream)
    with pytest.raises(RuntimeError, match="safe bundle identifier"):
        run_unreal.packaged_evidence_directory(app, "20260907T010000Z_fixture_validate_packaged")


@pytest.mark.parametrize("run_name", ["", ".", "..", "../escape", "/absolute", "nested/run", "two words"])
def test_packaged_container_rejects_unsafe_run_names(tmp_path, run_name):
    app = make_app(tmp_path / "BastideWalk.app")
    with pytest.raises(RuntimeError, match="safe run directory"):
        run_unreal.packaged_evidence_directory(app, run_name)


def test_packaged_container_uses_exact_bundle_and_host_home(tmp_path, monkeypatch):
    app = make_app(tmp_path / "App with spaces/BastideWalk.app")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "Test Home"))
    actual = run_unreal.packaged_evidence_directory(app, "20260907T010000Z_fixture_validate_packaged")
    assert actual == tmp_path / "Test Home/Library/Containers/com.synthetic.BastideWalk/Data/Library/Caches/BastideValidation/20260907T010000Z_fixture_validate_packaged"
    assert not actual.exists()


def test_native_output_copy_retains_partial_output_and_is_idempotent(tmp_path):
    native, evidence = tmp_path / "container", tmp_path / "evidence"
    (native / "Validation").mkdir(parents=True)
    evidence.mkdir()
    (native / "engine.log").write_bytes(b"partial native log\n")
    (native / "Validation/runtime-audit.json").write_bytes(b'{"status":"running"}')
    (native / "Input").mkdir()
    (native / "Input/routes.json").write_bytes(b"private staged route input")
    for _ in range(2):
        assert run_unreal.copy_native_evidence(native, evidence) == ["engine.log", "Validation"]
        assert (evidence / "engine.log").read_bytes() == (native / "engine.log").read_bytes()
        assert (evidence / "Validation/runtime-audit.json").read_bytes() == (native / "Validation/runtime-audit.json").read_bytes()
    assert not (evidence / "Input").exists()
    assert run_unreal.copy_native_evidence(evidence, evidence) == []


@pytest.mark.parametrize("interrupted", [False, True])
def test_failed_packaged_run_stages_route_and_copies_native_evidence_even_on_interrupt(tmp_path, monkeypatch, interrupted):
    app = make_app(tmp_path / "BastideWalk.app")
    project = tmp_path / "BastideWalk.uproject"
    project.write_text("{}")
    routes = tmp_path / "external routes with spaces.json"
    routes.write_bytes(b'{"routes":[{"name":"Room route","points_cm":[[0,0,90.5],[60,0,90.5]]}]}')
    monkeypatch.setattr(run_unreal, "PROJECT", project)
    monkeypatch.setattr(run_unreal, "OUTPUT", tmp_path / "out")
    monkeypatch.setattr(run_unreal, "REPOSITORY", tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.setattr(run_unreal.sys, "platform", "darwin")
    monkeypatch.setattr(run_unreal.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(run_unreal, "platform_receipt", lambda *args: {})
    monkeypatch.setattr(run_unreal, "snapshot_inputs", dict)

    def no_engine(*args):
        raise RuntimeError("No installed engine in synthetic packaged test")

    monkeypatch.setattr(run_unreal, "engine_root", no_engine)
    terminated = []

    def fake_native(command, **kwargs):
        native_log = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("-abslog=")))
        native_routes = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("-BastideRouteData=")))
        validation = Path(next(arg.split("=", 1)[1] for arg in command if arg.startswith("-BastideValidationDir=")))
        assert native_routes == native_log.parent / "Input/routes.json"
        assert native_routes.read_bytes() == routes.read_bytes()
        assert native_routes != routes
        validation.mkdir()
        (validation / "runtime-audit.json").write_bytes(b'{"unfinished":true}')
        native_log.write_bytes(b"native failure diagnostic\n")

        def output():
            yield "synthetic native output\n"
            if interrupted:
                raise KeyboardInterrupt

        return SimpleNamespace(stdout=output(), terminate=lambda: terminated.append(True), wait=lambda: -15 if interrupted else 42)

    monkeypatch.setattr(run_unreal.subprocess, "Popen", fake_native)
    monkeypatch.setattr(sys, "argv", ["run_unreal.py", "validate", "--runtime", "packaged", "--app", str(app), "--route-data", str(routes)])
    assert run_unreal.main() == 1
    evidence = next((tmp_path / "out/runs").iterdir())
    receipt = json.loads((evidence / "stage-receipt.json").read_text())
    assert receipt["status"] == "failed"
    assert receipt["process_exit_code"] == (-15 if interrupted else 42)
    assert receipt["copied_native_outputs"] == ["engine.log", "Validation"]
    assert (evidence / "engine.log").read_bytes() == b"native failure diagnostic\n"
    assert (evidence / "Validation/runtime-audit.json").read_bytes() == b'{"unfinished":true}'
    staged = Path(receipt["route_data_override"]["native_path"])
    assert staged.read_bytes() == routes.read_bytes()
    assert receipt["route_data_override"]["sha256"] == hashlib.sha256(staged.read_bytes()).hexdigest()
    assert terminated == ([True] if interrupted else [])
