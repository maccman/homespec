"""Rotated rooms must retain the same collision/clearance policy as axis-aligned ones."""
import importlib.util
import math
from pathlib import Path

import pytest

_PATH = Path(__file__).parents[1] / 'homespec' / 'blender' / 'audit_geometry.py'
_SPEC = importlib.util.spec_from_file_location('audit_geometry', _PATH)
G = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(G)


def wall(angle=0):
    a = math.radians(angle)
    return G.extrusion_prism({'origin': [0, 0, 0], 'u': [math.cos(a), math.sin(a)],
                             'n': [-math.sin(a), math.cos(a)], 'length': 6000, 'thickness': 200, 'height': 3000})


def box(center, size, angle=0):
    a = math.radians(angle)
    axes = ((math.cos(a), math.sin(a), 0), (-math.sin(a), math.cos(a), 0), (0, 0, 1))
    corners = [tuple(center[j] + sum(signs[i] * size[i] / 2 * axes[i][j] for i in range(3)) for j in range(3))
               for signs in ((x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1))]
    return corners, axes


def rotated(p, angle):
    a = math.radians(angle)
    return (p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a), p[2])


def test_diagonal_wall_bbox_does_not_count_as_the_wall():
    wall_points, _ = wall(45)
    furniture = box((1.0, 3.0, .5), (.6, .6, 1.0))
    # This is deep within the wall's AABB, but over a metre off its actual face.
    for i in range(3):
        assert min(p[i] for p in wall_points) <= min(p[i] for p in furniture[0])
        assert max(p[i] for p in furniture[0]) <= max(p[i] for p in wall_points)
    assert G.obb_overlap(*furniture, *wall(45)) < 0


@pytest.mark.parametrize('angle', [0, 18, 45, 72, -106])
@pytest.mark.parametrize('penetration', [.04, .06, .08])
def test_rotating_the_entire_scene_preserves_the_60mm_policy(angle, penetration):
    # A 600mm-deep piece reaches exactly penetration metres through the inside face.
    furniture = box(rotated((3, -.30 + penetration, .5), angle), (.8, .6, 1.0), angle)
    depth = G.obb_overlap(*furniture, *wall(angle))
    assert depth == pytest.approx(penetration, abs=1e-10)
    assert (depth > .06000001) == (penetration > .06)


def test_rotated_furniture_corner_is_checked_in_its_own_frame():
    # Axis-aligned bounding boxes overlap, but the rotated narrow piece is clear.
    furniture = box((6.15, -.15, .5), (1.0, .10, 1.0), 45)
    assert G.obb_overlap(*furniture, *wall()) < 0
    penetrating = box((5.85, .05, .5), (1.0, .10, 1.0), 45)
    assert G.obb_overlap(*penetrating, *wall()) > .06


def test_route_anchor_is_checked_against_oriented_wall():
    assert G.prism_contains(rotated((3, .10, .5), 45), *wall(45))
    assert not G.prism_contains((1, 3, .5), *wall(45))
    assert not G.prism_contains(rotated((3, -.01, .5), 45), *wall(45))


def test_objects_on_another_storey_do_not_intersect():
    assert G.obb_overlap(*box((3, .10, 4), (1, 1, 1), 35), *wall()) < 0


@pytest.mark.parametrize('angle', [0, 18, 72, -106])
@pytest.mark.parametrize('overlap', [.14, .15, .16])
def test_route_overlap_retains_150mm_xy_tolerance_when_rotated(angle, overlap):
    route = box(rotated((0, 0, 1), angle), (1, 2, 2), angle)
    furniture = box(rotated((.5 + .4 - overlap, 0, 1.99), angle), (.8, .6, .3), angle)
    # Shallow Z intersection must not change the independent XY measurement.
    assert G.footprint_overlap(furniture[0], route[0]) == pytest.approx(overlap)


def test_diagonal_route_aabb_does_not_block_nearby_furniture():
    route = box((0, 0, 1), (1, 3, 2), 45)
    furniture = box((1.3, 1.3, .4), (.3, .3, .8), 45)
    assert G.footprint_overlap(furniture[0], route[0]) < 0
