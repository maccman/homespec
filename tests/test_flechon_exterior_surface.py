"""Verify surface math without launching or importing Blender."""

import ast
import math
from pathlib import Path

import pytest
from shapely.geometry import Polygon, box
from shapely.ops import triangulate, unary_union

from projects.bastide_de_flechon.rooms import exterior_geometry


@pytest.fixture(scope="module")
def helpers():
    path = Path(__file__).parents[1] / "projects/bastide_de_flechon/rooms/exterior_envelope.py"
    tree = ast.parse(path.read_text())
    names = {"host_local_vertices", "clipped_stone_face", "dressed_rubble_faces"}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"math": math, "G": exterior_geometry}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


@pytest.mark.parametrize("angle", (0, 83.2, -18.9, 90, 180))
@pytest.mark.parametrize("handedness", (-1, 1))
def test_host_frame_preserves_every_world_vertex(helpers, angle, handedness):
    a = math.radians(angle)
    u, n = (math.cos(a), math.sin(a)), (-math.sin(a) * handedness, math.cos(a) * handedness)
    origin = (-5.413, 28.77)
    world = [(-9.3, 29.11, 6.7), (-.12, 18.6, .41), (8.3, 5.18, 8.2)]
    local = helpers["host_local_vertices"](world, origin, u, n)
    recovered = [(origin[0] + u[0] * x + n[0] * y, origin[1] + u[1] * x + n[1] * y, z) for x, y, z in local]
    assert max(math.dist(a, b) for a, b in zip(world, recovered, strict=True)) < 1e-8


def test_stones_have_physical_relief_and_worn_shoulders_without_leaving_joint(helpers):
    faces = helpers["dressed_rubble_faces"]([(0, 0), (.34, 0), (.38, .16), (.25, .24), (0, .21)], 71)
    points = [p for face in faces for p in face]
    boundary = Polygon([(0, 0), (.34, 0), (.38, .16), (.25, .24), (0, .21)])
    assert min(p[2] for p in points) == pytest.approx(-.008)
    assert .022 < max(p[2] for p in points) < .043
    assert len({round(p[2], 5) for p in points}) > 20
    projected = unary_union([Polygon([(p[0], p[1]) for p in face]) for face in faces])
    assert projected.difference(boundary).area < 1e-12
    assert .75 < projected.area / boundary.area < 1


def test_rough_face_clipping_preserves_opening_and_interpolated_relief(helpers):
    stone = [(0, 0), (.4, 0), (.4, .3), (0, .3)]
    rough = helpers["dressed_rubble_faces"](stone, 42)
    opening = box(.16, 0, .25, .19)
    facade = box(0, 0, .4, .3).difference(opening)
    triangles = [t for t in triangulate(facade) if facade.covers(t)]
    pieces = []
    for face in rough:
        for triangle in triangles:
            clipped = helpers["clipped_stone_face"](face, list(triangle.exterior.coords)[:-1])
            if len(clipped) >= 3:
                assert min(p[2] for p in face) - 1e-12 <= min(p[2] for p in clipped)
                assert max(p[2] for p in clipped) <= max(p[2] for p in face) + 1e-12
                polygon = Polygon([(p[0], p[1]) for p in clipped])
                if polygon.area > 1e-12:
                    pieces.append(polygon)
    result = unary_union(pieces)
    assert result.intersection(opening).area < 1e-12
    assert result.difference(facade).area < 1e-12
    assert result.area > .065
