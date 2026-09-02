import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY_ROOM = os.path.join(ROOT, "projects", "library_room")


@pytest.fixture(scope="session")
def library_room_report(tmp_path_factory):
    """One full build of the example project, shared by every test that reads outputs."""
    from homespec.pipeline import build_project

    out = str(tmp_path_factory.mktemp("library_room"))
    return build_project(LIBRARY_ROOM, out)


@pytest.fixture(scope="session")
def library_room_ir(library_room_report):
    from homespec.ir import IRDocument

    return IRDocument.read(library_room_report.out_dir)
