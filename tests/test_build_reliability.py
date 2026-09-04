"""Failure injection at the build publication and consumer boundaries."""
from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from homespec import House, pipeline
from homespec import buildstate as state


@pytest.fixture
def project(tmp_path):
    directory = tmp_path / "project"
    directory.mkdir()
    (directory / "project.py").write_text('from homespec import House\ndef build():\n    return House("example")\n')
    (directory / "presentation.py").write_text('def dress(scene):\n    pass\n')
    (directory / "decisions.md").write_text("## Considered and not changed\n\n## Not verified\n")
    return directory


def build(project, root, **options):
    defaults = dict(ifc=False, drawings=False, schedules=False)
    return pipeline.build_project(str(project), str(root), **(defaults | options))


def metadata(root):
    pointer = json.loads((root / "manifest.json").read_text())
    generation = root / pointer["generation"]
    return pointer, generation, json.loads((generation / "build.json").read_text())


def test_published_build_is_complete_and_independently_readable(project, tmp_path):
    root = tmp_path / "out"
    report = build(project, root)
    pointer, generation, record = metadata(root)
    assert report.ok and report.status == pointer["status"] == record["status"] == "passed"
    assert Path(report.out_dir) == state.resolve_build(root) == generation
    assert report.output_root == str(root)
    assert {"ir.json", "checks.json", "checks.md", "report.json"} <= record["artifacts"].keys()
    persisted = pipeline.Report.model_validate_json((generation / "report.json").read_text())
    assert persisted == report
    assert state.resolve_ir_root(root) == str(generation)
    assert not (root / "ir.json").exists()


def test_disabled_exporters_never_expose_previous_artifacts(project, tmp_path, monkeypatch):
    root = tmp_path / "out"

    def export(ir, path):
        Path(path).write_text("IFC")
        return path

    monkeypatch.setattr(pipeline, "export_ifc", export)
    monkeypatch.setattr(pipeline.ids_checks, "validate", lambda *args: [])
    first = build(project, root, ifc=True)
    second = build(project, root)
    assert Path(first.files["ifc"][0]).is_file()
    assert "ifc" not in second.files
    assert not (Path(second.out_dir) / "house.ifc").exists()
    pointer, generation, record = metadata(root)
    assert pointer["previous_successful_generation"] == str(Path(first.out_dir).relative_to(root))
    assert "house.ifc" not in record["artifacts"]
    assert state.resolve_build(root) == generation


def test_interrupted_export_publishes_error_without_destroying_success(project, tmp_path, monkeypatch):
    root = tmp_path / "out"
    first = build(project, root)

    def broken_export(ir, path):
        Path(path).write_text("partial IFC")
        raise RuntimeError("injected exporter failure")

    monkeypatch.setattr(pipeline, "export_ifc", broken_export)
    with pytest.raises(RuntimeError, match="injected exporter"):
        build(project, root, ifc=True)
    pointer, generation, record = metadata(root)
    assert pointer["status"] == record["status"] == "error"
    assert pointer["previous_successful_generation"] == str(Path(first.out_dir).relative_to(root))
    assert "injected exporter failure" in record["error"]
    assert json.loads((generation / "report.json").read_text())["status"] == "error"
    with pytest.raises(state.BuildStateError, match="incomplete or failed"):
        state.resolve_build(root)
    assert state.resolve_build(first.out_dir) == Path(first.out_dir)


def test_failed_manifest_replacement_keeps_old_generation_published(project, tmp_path, monkeypatch):
    root = tmp_path / "out"
    first = build(project, root)
    original = state.atomic_json

    def fail_pointer(path, value):
        if path == root / "manifest.json":
            raise OSError("injected publication failure")
        original(path, value)

    monkeypatch.setattr(state, "atomic_json", fail_pointer)
    with pytest.raises(OSError, match="publication failure"):
        build(project, root)
    assert state.resolve_build(root) == Path(first.out_dir)
    assert len(list((root / "generations").iterdir())) == 2


@pytest.mark.parametrize("action", ["edit", "delete", "add"])
def test_source_membership_and_content_invalidate_build(project, tmp_path, action):
    root = tmp_path / "out"
    build(project, root)
    if action == "edit":
        (project / "project.py").write_text((project / "project.py").read_text() + "# changed\n")
    elif action == "delete":
        (project / "presentation.py").unlink()
    else:
        (project / "helper.py").write_text("VALUE = 1\n")
    with pytest.raises(state.StaleBuildError, match="stale"):
        state.resolve_build(root)


def test_declared_inputs_and_dependencies_invalidate_build(project, tmp_path, monkeypatch):
    root = tmp_path / "out"
    (project / "data.csv").write_text("a,1\n")
    (project / "project.py").write_text('from homespec import House\ndef build():\n    return House("example", inputs=["data.csv"])\n')
    build(project, root)
    (project / "data.csv").write_text("a,2\n")
    with pytest.raises(state.StaleBuildError, match="data.csv"):
        state.resolve_build(root)
    build(project, root)
    monkeypatch.setattr(state.importlib.metadata, "distributions", lambda: [])
    with pytest.raises(state.StaleBuildError, match="dependency versions"):
        state.resolve_build(root)


@pytest.mark.parametrize("directory", [False, True], ids=["file", "directory"])
@pytest.mark.parametrize("absolute", [False, True], ids=["relative", "absolute"])
def test_retargeting_declared_input_symlinks_invalidates_build(project, tmp_path, directory, absolute):
    targets = [tmp_path / "first", tmp_path / "second"]
    for target, name in zip(targets, ("original", "replacement"), strict=True):
        if directory:
            target.mkdir()
        (target / "name.txt" if directory else target).write_text(name)
    link = project / "data"
    link.symlink_to(targets[0], target_is_directory=directory)
    declaration = str(link) if absolute else "data"
    reader = 'Path(__file__).with_name("data")' + (' / "name.txt"' if directory else "")
    (project / "project.py").write_text(
        f'from pathlib import Path\nfrom homespec import House\ndef build():\n'
        f'    return House(({reader}).read_text(), inputs=[{declaration!r}])\n')
    root = tmp_path / "out"
    report = build(project, root)
    assert report.project == "original"
    assert metadata(root)[2]["inputs"]["inputs"] == [declaration]
    link.unlink()
    link.symlink_to(targets[1], target_is_directory=directory)
    assert pipeline.load_house(str(project)).name == "replacement"
    with pytest.raises(state.StaleBuildError, match="stale"):
        state.resolve_build(root)


def test_retargeting_declared_input_during_compile_records_error(project, tmp_path, monkeypatch):
    first, second = tmp_path / "first", tmp_path / "second"
    first.write_text("original")
    second.write_text("replacement")
    link = project / "data"
    link.symlink_to(first)
    (project / "project.py").write_text(
        'from homespec import House\ndef build():\n    return House("example", inputs=["data"])\n')
    original = House.compile

    def retarget(self):
        compiled = original(self)
        link.unlink()
        link.symlink_to(second)
        return compiled

    monkeypatch.setattr(House, "compile", retarget)
    root = tmp_path / "out"
    with pytest.raises(state.StaleBuildError, match="stale"):
        build(project, root)
    assert metadata(root)[2]["status"] == "error"


def test_inputs_cannot_refer_to_outputs(project, tmp_path):
    root = tmp_path / "out"
    root.mkdir()
    with pytest.raises(ValueError, match="must not include build outputs"):
        state.input_snapshot(project, root, [str(root)], {})


def test_changes_during_compile_are_recorded_as_error(project, tmp_path, monkeypatch):
    original = House.compile

    def changed(self):
        compiled = original(self)
        with (project / "project.py").open("a") as stream:
            stream.write("# changed during compilation\n")
        return compiled

    monkeypatch.setattr(House, "compile", changed)
    root = tmp_path / "out"
    with pytest.raises(state.StaleBuildError, match="stale"):
        build(project, root)
    assert metadata(root)[2]["status"] == "error"


@pytest.mark.parametrize("action", ["delete", "corrupt"])
def test_missing_or_corrupted_artifact_blocks_every_consumer(project, tmp_path, monkeypatch, action):
    root = tmp_path / "out"
    report = build(project, root)
    ir = Path(report.out_dir) / "ir.json"
    ir.unlink() if action == "delete" else ir.write_text("corrupted")
    monkeypatch.setattr(pipeline, "_blender", lambda *args: pytest.fail("Blender must not run"))
    for consumer in (lambda: pipeline.render(str(project), str(root), "still", allow_failed_checks=True),
                     lambda: pipeline.audit(str(project), str(root)),
                     lambda: pipeline.views(str(project), str(root)),
                     lambda: pipeline.walk(str(project), str(root), allow_failed_checks=True)):
        with pytest.raises(state.BuildStateError, match="artifact is missing or corrupt"):
            consumer()


def test_failed_checks_and_unchecked_are_explicit_and_render_needs_override(project, tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "_blender", lambda *args: [])
    for checks, expected in ((True, "failed_checks"), (False, "unchecked")):
        (project / "decisions.md").write_text("Missing decision ledgers")
        root = tmp_path / expected
        report = build(project, root, checks=checks)
        assert report.status == expected and not report.ok
        assert state.resolve_build(root) == Path(report.out_dir)
        assert pipeline.audit(str(project), str(root)) == []
        with pytest.raises(state.BuildStateError, match="allow-failed-checks"):
            pipeline.render(str(project), str(root), "still")
        assert pipeline.render(str(project), str(root), "still", allow_failed_checks=True) == 0
        with (project / "project.py").open("a") as stream:
            stream.write("# stale\n")
        with pytest.raises(state.StaleBuildError):
            pipeline.render(str(project), str(root), "still", allow_failed_checks=True)


def test_concurrent_builds_serialize_and_publish_whole_generations(project, tmp_path, monkeypatch):
    root = tmp_path / "out"
    entered, release = threading.Event(), threading.Event()
    original = pipeline.load_house
    calls = []

    def slow_load(path):
        calls.append(path)
        if len(calls) == 1:
            entered.set()
            assert release.wait(10)
        return original(path)

    monkeypatch.setattr(pipeline, "load_house", slow_load)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(build, project, root)
        assert entered.wait(10)
        second_started = threading.Event()

        def second_build():
            second_started.set()
            return build(project, root)

        second = pool.submit(second_build)
        assert second_started.wait(10)
        assert len(calls) == 1
        release.set()
        one, two = first.result(timeout=30), second.result(timeout=30)
    assert one.generation != two.generation
    assert state.resolve_build(root) == Path(two.out_dir)
    assert state.resolve_build(one.out_dir) == Path(one.out_dir)


def test_saved_scene_provenance_and_integrity(project, tmp_path, monkeypatch):
    root = tmp_path / "out"
    report = build(project, root)

    def fake_blender(script, args, env):
        directory = Path(env["HOMESPEC_PRESENTATION_OUT"])
        assert args[0] == report.out_dir
        (directory / "house_walk.blend").write_bytes(b"saved scene")
        return []

    monkeypatch.setattr(pipeline, "_blender", fake_blender)
    pipeline.render(str(project), str(root), "save", device="cpu")
    generation = state.resolve_build(root)
    scene = state.verified_saved_scene(generation, project)
    assert scene.is_relative_to(root / "presentation")
    assert not scene.is_relative_to(generation)
    scene.write_bytes(b"changed scene")
    with pytest.raises(state.BuildStateError, match="stale or corrupt"):
        state.verified_saved_scene(generation, project)


def test_old_saved_scene_cannot_be_reused_after_rebuild(project, tmp_path, monkeypatch):
    root = tmp_path / "out"
    build(project, root)

    def fake_blender(script, args, env):
        (Path(env["HOMESPEC_PRESENTATION_OUT"]) / "house_walk.blend").write_bytes(b"saved")
        return []

    monkeypatch.setattr(pipeline, "_blender", fake_blender)
    pipeline.render(str(project), str(root), "save")
    build(project, root)
    with pytest.raises(state.BuildStateError, match="saved-scene.json"):
        pipeline.walk(str(project), str(root))


def test_blender_python_failure_exit_code_is_enabled(monkeypatch):
    import subprocess

    commands = []

    class FakeProcess:
        stdout = []

        def wait(self):
            return 1

    monkeypatch.setattr(pipeline, "blender_binary", lambda: "blender")
    monkeypatch.setattr(subprocess, "Popen", lambda command, **kwargs: commands.append(command) or FakeProcess())
    with pytest.raises(pipeline.RenderError, match="exited with 1"):
        pipeline._blender("script.py", [])
    assert commands[0][2:4] == ["--python-exit-code", "1"]


def test_rebuild_imports_latest_local_helper_even_with_same_timestamp(project, monkeypatch):
    helper = project / "helper.py"
    helper.write_text('NAME = "first"\n')
    (project / "project.py").write_text('from homespec import House\nfrom helper import NAME\ndef build():\n    return House(NAME)\n')
    assert pipeline.load_house(str(project)).name == "first"
    original = helper.stat()
    helper.write_text('NAME = "other"\n')
    import os
    os.utime(helper, ns=(original.st_atime_ns, original.st_mtime_ns))
    assert pipeline.load_house(str(project)).name == "other"


def test_data_changes_while_project_is_evaluated_cannot_be_published(project, tmp_path, monkeypatch):
    root = tmp_path / "out"
    data = project / "data.txt"
    data.write_text("first")
    (project / "project.py").write_text(
        'from homespec import House\nfrom pathlib import Path\ndef build():\n'
        '    return House(Path(__file__).with_name("data.txt").read_text(), inputs=["data.txt"])\n')
    original = pipeline.load_house
    calls = 0

    def changing_load(path):
        nonlocal calls
        house = original(path)
        calls += 1
        if calls == 2:
            data.write_text("changed after source read")
        return house

    monkeypatch.setattr(pipeline, "load_house", changing_load)
    with pytest.raises(state.StaleBuildError, match="data.txt"):
        build(project, root)
    assert metadata(root)[2]["status"] == "error"


def test_outputs_cannot_hide_project_sources_from_fingerprints(project):
    with pytest.raises(ValueError, match="must not contain the project source"):
        state.input_snapshot(project, project, [], {})


def test_reader_sees_old_complete_generation_while_new_export_runs(project, tmp_path, monkeypatch):
    root = tmp_path / "out"
    first = build(project, root)
    entered, release = threading.Event(), threading.Event()

    def slow_export(ir, path):
        Path(path).write_text("partial")
        entered.set()
        assert release.wait(10)
        Path(path).write_text("complete")
        return path

    monkeypatch.setattr(pipeline, "export_ifc", slow_export)
    monkeypatch.setattr(pipeline.ids_checks, "validate", lambda *args: [])
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(build, project, root, ifc=True)
        assert entered.wait(10)
        assert state.resolve_build(root) == Path(first.out_dir)
        release.set()
        second = pending.result(timeout=30)
    assert state.resolve_build(root) == Path(second.out_dir)
    assert Path(second.files["ifc"][0]).read_text() == "complete"


def test_build_can_recover_damaged_manifest(project, tmp_path):
    root = tmp_path / "out"
    build(project, root)
    (root / "manifest.json").write_text("damaged")
    with pytest.raises(state.BuildStateError, match="Cannot read build metadata"):
        state.resolve_build(root)
    report = build(project, root)
    assert state.resolve_build(root) == Path(report.out_dir)


def test_projects_with_same_helper_name_are_isolated_and_restore_caller_modules(tmp_path, monkeypatch):
    import sys
    from types import ModuleType

    external = ModuleType("helper")
    external.NAME = "caller"
    monkeypatch.setitem(sys.modules, "helper", external)
    projects = []
    for name in ("first", "second"):
        project = tmp_path / name
        project.mkdir()
        (project / "helper.py").write_text(f"NAME = {name!r}\n")
        (project / "project.py").write_text('from homespec import House\nfrom helper import NAME\ndef build():\n    return House(NAME)\n')
        projects.append(project)
    for project in [*projects, projects[0]]:
        assert pipeline.load_house(str(project)).name == project.name
        assert sys.modules["helper"] is external


def test_failed_project_import_restores_caller_modules_and_search_path(project, monkeypatch):
    import sys
    from types import ModuleType

    external = ModuleType("helper")
    monkeypatch.setitem(sys.modules, "helper", external)
    previous = list(sys.path)
    (project / "helper.py").write_text("VALUE = 1\n")
    (project / "project.py").write_text('import helper\nraise RuntimeError("failed import")\n')
    with pytest.raises(RuntimeError, match="failed import"):
        pipeline.load_house(str(project))
    assert sys.modules["helper"] is external
    assert sys.path == previous



@pytest.mark.parametrize("action", ["edit", "add", "delete"])
def test_presentation_fingerprint_tracks_asset_content_and_membership(tmp_path, action):
    project = tmp_path / "projects" / "example"
    project.mkdir(parents=True)
    (project / "presentation.py").write_text("def dress(scene): pass\n")
    assets = tmp_path / "assets" / "textures"
    assets.mkdir(parents=True)
    image = assets / "surface.png"
    image.write_bytes(b"first texture")
    before = state.presentation_snapshot(project)
    if action == "edit":
        image.write_bytes(b"new texture")
    elif action == "add":
        (assets / "new.png").write_bytes(b"new asset")
    else:
        image.unlink()
    assert state.fingerprint(state.presentation_snapshot(project)) != state.fingerprint(before)


def test_presentation_tracks_linked_asset_directories_without_following_cycles(tmp_path):
    project = tmp_path / "projects" / "example"
    project.mkdir(parents=True)
    assets = tmp_path / "assets"
    assets.mkdir()
    shared = tmp_path / "shared-library"
    shared.mkdir()
    image = shared / "texture.png"
    image.write_bytes(b"first")
    (assets / "textures").symlink_to(shared, target_is_directory=True)
    (shared / "loop").symlink_to(assets, target_is_directory=True)
    before = state.presentation_snapshot(project)
    assert str(assets / "textures" / "texture.png") in before
    image.write_bytes(b"changed")
    assert state.presentation_snapshot(project) != before


def _lazy_project(directory, value):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "helper.py").write_text(f"VALUE = {value}\n")
    (directory / "decisions.md").write_text("## Considered and not changed\n\n## Not verified\n")
    (directory / "project.py").write_text('''from typing import ClassVar
from homespec import House, Element, Realized, element
from homespec.model import Analysis

@element
class Local(Element):
    kind: ClassVar[str] = "local"
    physical: ClassVar[bool] = False
    ifc_class: ClassVar[str | None] = None

    def realize(self, ctx):
        from helper import VALUE
        return Realized(derived={"value": VALUE})

    def analyze(self, ctx):
        from helper import VALUE
        return Analysis(derived={"analysis": VALUE + 1})

def build():
    with House("lazy") as house:
        Local("local")
        @house.check
        def check(ir):
            from helper import VALUE
            yield ("lazy", "local", ir.entity("local").derived["value"] == VALUE)
    return house
''')


def test_lazy_element_analysis_and_checks_resolve_project_helpers_after_load(tmp_path, monkeypatch):
    import sys
    from types import ModuleType

    from homespec.checks import run
    from homespec.ir import IRDocument

    external = ModuleType("helper")
    external.VALUE = 99
    monkeypatch.setitem(sys.modules, "helper", external)
    projects = [tmp_path / "first", tmp_path / "second"]
    for i, project in enumerate(projects, 1):
        _lazy_project(project, i)
    houses = [pipeline.load_house(str(project)) for project in projects]
    for i, house in enumerate(houses, 1):
        compiled = house.compile()
        assert compiled["local"].derived == {"value": i, "analysis": i + 1}
        out = tmp_path / f"raw-{i}"
        compiled.write(str(out), [])
        results = run(IRDocument.read(str(out)), extra=house.checks)
        assert all(result.ok for result in results)
        assert next(result for result in results if result.rule == "lazy").ok
        assert sys.modules["helper"] is external


def test_whole_build_keeps_lazy_import_context_through_exporters_and_checks(project, tmp_path, monkeypatch):
    _lazy_project(project, 42)

    def lazy_schedule(ir, out):
        from helper import VALUE
        assert VALUE == ir.entity("local").derived["value"] == 42
        return []

    monkeypatch.setattr(pipeline, "export_schedules", lazy_schedule)
    report = build(project, tmp_path / "out", schedules=True)
    assert report.ok
    assert next(result for result in report.results if result.rule == "lazy").ok


def test_movie_locks_frames_until_encoding_and_preserves_old_movie_until_publish(project, tmp_path, monkeypatch):
    import shutil
    import subprocess
    from contextlib import contextmanager

    root = tmp_path / "out"
    report = build(project, root)
    generation = Path(report.out_dir)
    directory, _ = state.presentation_directory(generation, project)
    frames = directory / "renders" / "anim"
    frames.mkdir(parents=True)
    target = directory / "renders" / "walkthrough.mp4"
    target.write_bytes(b"old movie")
    encoding, release, attempted = threading.Event(), threading.Event(), threading.Event()
    render_calls = []
    original_lock = state.build_lock

    @contextmanager
    def observed_lock(path):
        if threading.current_thread().name.startswith("replacement"):
            attempted.set()
        with original_lock(path):
            yield

    def fake_blender(script, args, env):
        render_calls.append(args[2])
        frames.mkdir(parents=True, exist_ok=True)
        (frames / "frame_0001.png").write_bytes(str(len(render_calls)).encode())
        return []

    def encode(command, **kwargs):
        assert command[-1] != str(target)
        before = (frames / "frame_0001.png").read_bytes()
        encoding.set()
        assert release.wait(10)
        assert (frames / "frame_0001.png").read_bytes() == before
        assert target.read_bytes() == b"old movie"
        Path(command[-1]).write_bytes(b"new movie")

    monkeypatch.setattr(state, "build_lock", observed_lock)
    monkeypatch.setattr(pipeline, "_blender", fake_blender)
    monkeypatch.setattr(shutil, "which", lambda name: "/fake/ffmpeg")
    monkeypatch.setattr(subprocess, "run", encode)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="movie") as movies, ThreadPoolExecutor(max_workers=1, thread_name_prefix="replacement") as renders:
        movie = movies.submit(pipeline.movie, str(project), str(root))
        assert encoding.wait(10)
        replacement = renders.submit(pipeline.render, str(project), str(root), "anim")
        assert attempted.wait(10)
        assert render_calls == ["anim"]
        assert not replacement.done()
        release.set()
        assert movie.result(timeout=20) == str(target)
        assert replacement.result(timeout=20) == 0
    assert target.read_bytes() == b"new movie"
    assert not list(target.parent.glob(".walkthrough.*.mp4"))


def test_failed_movie_encode_keeps_previous_movie_and_removes_temporary_file(project, tmp_path, monkeypatch):
    import shutil
    import subprocess

    root = tmp_path / "out"
    report = build(project, root)
    directory, _ = state.presentation_directory(Path(report.out_dir), project)
    frames = directory / "renders" / "anim"
    frames.mkdir(parents=True)
    target = directory / "renders" / "walkthrough.mp4"
    target.write_bytes(b"old movie")

    def fake_blender(*args):
        frames.mkdir(parents=True, exist_ok=True)
        (frames / "frame_0001.png").write_bytes(b"frame")
        return []

    def broken_encode(command, **kwargs):
        Path(command[-1]).write_bytes(b"partial encode")
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(pipeline, "_blender", fake_blender)
    monkeypatch.setattr(shutil, "which", lambda name: "/fake/ffmpeg")
    monkeypatch.setattr(subprocess, "run", broken_encode)
    with pytest.raises(subprocess.CalledProcessError):
        pipeline.movie(str(project), str(root))
    assert target.read_bytes() == b"old movie"
    assert not list(target.parent.glob(".walkthrough.*.mp4"))


def test_declared_data_snapshot_reimports_discovery_helpers(project, tmp_path, monkeypatch):
    data = project / "data.txt"
    data.write_text("before")
    (project / "helper.py").write_text('from pathlib import Path\nVALUE = Path(__file__).with_name("data.txt").read_text()\n')
    (project / "project.py").write_text('from homespec import House\nfrom helper import VALUE\ndef build():\n    return House(VALUE, inputs=["data.txt"])\n')
    original = pipeline.load_house
    calls = 0

    def changed_after_discovery(path):
        nonlocal calls
        house = original(path)
        calls += 1
        if calls == 1:
            data.write_text("captured")
        return house

    monkeypatch.setattr(pipeline, "load_house", changed_after_discovery)
    report = build(project, tmp_path / "out")
    assert report.ok and report.project == "captured"
