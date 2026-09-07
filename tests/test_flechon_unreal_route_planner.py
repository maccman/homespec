"""Offline route candidates must respect surveyed topology and capsule step limits.

These synthetic checks do not establish native Unreal movement or room access.
"""

from copy import deepcopy

import pytest

from projects.bastide_de_flechon.unreal.tools.plan_survey_routes import (
    GridLevel,
    build_candidates,
    compress_collinear,
)


def grid(cells):
    return GridLevel(floor_z=0.0, origin=(0.0, 0.0), spacing=30.0, cells=cells)


def assert_legal_path(level, path, start, end):
    """Check the public safety contract without fixing A* tie-breaking order."""
    assert path is not None
    assert path[0] == start
    assert path[-1] == end
    assert all(cell in level.cells for cell in path)
    for first, second in zip(path, path[1:], strict=False):
        dx, dy = second[0] - first[0], second[1] - first[1]
        assert max(abs(dx), abs(dy)) == 1
        assert abs(level.cells[first] - level.cells[second]) <= 24.0
        if dx and dy:
            # Capsule clearance at the two diagonal endpoints alone cannot
            # establish safe passage around a wall corner between them.
            sides = [(first[0] + dx, first[1]), (first[0], first[1] + dy)]
            for side in sides:
                assert side in level.cells
                assert abs(level.cells[first] - level.cells[side]) <= 24.0
                assert abs(level.cells[second] - level.cells[side]) <= 24.0


def test_wall_requires_detour_through_the_only_opening():
    cells = {(x, y): 90.5 for x in range(7) for y in range(5) if x != 3 or y == 4}
    level = grid(cells)
    path = level.find_path((1, 1), (5, 1))

    assert_legal_path(level, path, (1, 1), (5, 1))
    assert (3, 4) in path
    assert len(set(level.components().values())) == 1


def test_closed_wall_disconnects_rooms_in_paths_and_components():
    cells = {(x, y): 90.5 for x in range(7) for y in range(5) if x != 3}
    level = grid(cells)

    assert level.find_path((1, 1), (5, 1)) is None
    assert level.find_path((5, 1), (1, 1)) is None
    components = level.components()
    assert set(components) == set(cells)
    assert components[(1, 1)] == components[(2, 4)]
    assert components[(5, 1)] == components[(4, 4)]
    assert components[(1, 1)] != components[(5, 1)]


def test_touching_diagonal_cells_do_not_make_a_passage():
    level = grid({(0, 0): 90.5, (1, 1): 90.5})

    assert level.find_path((0, 0), (1, 1)) is None
    components = level.components()
    assert components[(0, 0)] != components[(1, 1)]


def test_one_clear_side_requires_orthogonal_turn_instead_of_corner_cut():
    level = grid({(0, 0): 90.5, (1, 0): 90.5, (1, 1): 90.5})

    path = level.find_path((0, 0), (1, 1))
    assert_legal_path(level, path, (0, 0), (1, 1))
    assert path == [(0, 0), (1, 0), (1, 1)]


def test_clear_diagonal_is_available_when_both_sides_are_clear():
    level = grid({(x, y): 90.5 for x in range(2) for y in range(2)})

    path = level.find_path((0, 0), (1, 1))
    assert_legal_path(level, path, (0, 0), (1, 1))
    assert path == [(0, 0), (1, 1)]


@pytest.mark.parametrize("height_delta", [24.0, -24.0], ids=["step-up", "step-down"])
def test_twenty_four_centimeter_step_is_traversable(height_delta):
    level = grid({(0, 0): 90.5, (1, 0): 90.5 + height_delta})

    assert_legal_path(level, level.find_path((0, 0), (1, 0)), (0, 0), (1, 0))
    assert_legal_path(level, level.find_path((1, 0), (0, 0)), (1, 0), (0, 0))
    assert len(set(level.components().values())) == 1


@pytest.mark.parametrize("height_delta", [25.0, -25.0], ids=["ledge-up", "ledge-down"])
def test_twenty_five_centimeter_ledge_is_disconnected(height_delta):
    level = grid({(0, 0): 90.5, (1, 0): 90.5 + height_delta})

    assert level.find_path((0, 0), (1, 0)) is None
    assert level.find_path((1, 0), (0, 0)) is None
    assert len(set(level.components().values())) == 2


def test_diagonal_cannot_bridge_unsafe_side_heights():
    level = grid({(0, 0): 90.5, (1, 1): 90.5, (1, 0): 115.5, (0, 1): 115.5})

    assert level.find_path((0, 0), (1, 1)) is None
    assert level.components()[(0, 0)] != level.components()[(1, 1)]


@pytest.mark.parametrize("start,end", [((0, 0), (1, 0)), ((1, 0), (0, 0)), ((1, 0), (1, 0))])
def test_missing_endpoint_is_never_a_route(start, end):
    assert grid({(0, 0): 90.5}).find_path(start, end) is None


def test_occupied_single_cell_route_and_empty_components():
    assert grid({(0, 0): 90.5}).find_path((0, 0), (0, 0)) == [(0, 0)]
    assert grid({}).components() == {}


@pytest.mark.parametrize(
    "points",
    [
        [],
        [[0.0, 0.0, 90.5]],
        [[0.0, 0.0, 90.5], [30.0, 30.0, 100.5]],
    ],
    ids=["empty", "one-point", "endpoints-only"],
)
def test_short_paths_remain_unchanged(points):
    assert compress_collinear(points) == points


def test_compression_removes_only_redundant_vertices_on_same_3d_grade():
    points = [[0.0, 0.0, 90.5], [30.0, 30.0, 100.5], [90.0, 90.0, 120.5], [120.0, 120.0, 130.5]]
    assert compress_collinear(points) == [points[0], points[-1]]


def test_compression_preserves_horizontal_turns_and_grade_changes():
    points = [
        [0.0, 0.0, 90.5],
        [30.0, 0.0, 90.5],
        [60.0, 0.0, 90.5],
        [60.0, 30.0, 100.5],
        [60.0, 60.0, 110.5],
        [60.0, 90.0, 110.5],
    ]

    # Looking only at XY would erase the slope-to-level transition at index 4.
    assert compress_collinear(points) == [points[0], points[2], points[4], points[5]]


def test_compression_preserves_a_collinear_direction_reversal():
    points = [[0.0, 0.0, 90.5], [60.0, 0.0, 90.5], [30.0, 0.0, 90.5]]
    assert compress_collinear(points) == points


def candidate_inputs(cells):
    survey = {
        "schema": "bastide.navigation-survey.v1",
        "status": "static_probes_completed",
        "scope": "Static probes only; not proof of continuous walking",
        "grid_origin_cm": [0.0, 0.0],
        "spacing_cm": 30.0,
        "grid_counts_xy": [3, 1],
        "capsule_radius_cm": 30.0,
        "capsule_half_height_cm": 88.0,
        "levels": [{"floor_z": 0.0, "cells": [{"ix": x, "iy": y, "z_cm": z, "surface_z_cm": 0.0} for (x, y), z in cells.items()]}],
    }
    audit = {
        "schema": "bastide.runtime-audit.v1",
        "capsule_radius_cm": 30.0,
        "capsule_half_height_cm": 88.0,
        "bookmarks": [
            {"index": 4, "name": "Salon", "walking_target_clear": True, "walking_capsule_center_cm": [0.0, 0.0, 90.5]},
            {"index": 6, "name": "Dining", "walking_target_clear": True, "walking_capsule_center_cm": [60.0, 0.0, 90.5]},
        ],
    }
    walkthrough = {
        "schema": "bastide.walkthrough-input.v1",
        "source": {"packed_sha256": "synthetic-frozen-source"},
        "safe_spawn_cm": [0.0, 0.0, 90.5],
        "bookmark_overrides": [{"index": 4, "floor_z_cm": 0.0}, {"index": 6, "floor_z_cm": 0.0}],
        "routes": [
            {
                "name": "ST_HALL ascent",
                "kind": "stair",
                "points_cm": [[0.0, 0.0, 90.5], [0.0, 30.0, 420.5]],
                "entities": ["ST_HALL"],
                "input_status": "unverified_source_derived_candidate",
            }
        ],
    }
    return survey, audit, walkthrough


def test_candidates_preserve_inputs_and_stairs_without_claiming_native_verification():
    inputs = candidate_inputs({(x, 0): 90.5 for x in range(3)})
    original = deepcopy(inputs)

    candidate, report = build_candidates(*inputs)

    assert inputs == original
    assert candidate is not inputs[2]
    for field in ("schema", "source", "safe_spawn_cm", "bookmark_overrides"):
        assert candidate[field] == original[2][field]
    stairs = [route for route in candidate["routes"] if route["kind"] == "stair"]
    assert stairs == original[2]["routes"]
    planned = [route for route in candidate["routes"] if route["kind"] != "stair"]
    assert planned, "The clear Salon-to-Dining pair should produce a candidate route"
    assert all(route["input_status"] == "unverified_static_grid_candidate" for route in planned)
    assert all(route["native_walking_verified"] is False for route in planned)
    assert all(route["anchor_segments_verified"] is False for route in planned)
    assert report["native_walking_verified"] is False

    # Editing the generated file's nested records must not alter the input
    # walkthrough or preserved source-derived stair routes in memory.
    candidate["source"]["packed_sha256"] = "changed-candidate"
    stairs[0]["points_cm"][0][0] = 999.0
    assert inputs == original


def test_disconnected_bookmark_pair_is_reported_without_inventing_a_route():
    inputs = candidate_inputs({(0, 0): 90.5, (2, 0): 90.5})

    # Prevent endpoint snapping across the blocked middle cell from obscuring
    # this fixture's deliberate topology break.
    candidate, report = build_candidates(*inputs, max_anchor_cm=1.0)

    pair = next(pair for pair in report["unreachable"] if (pair["from_index"], pair["to_index"]) == (4, 6))
    assert pair["status"] == "unreachable"
    assert pair["from_component"] != pair["to_component"]
    assert report["native_walking_verified"] is False
    assert candidate["routes"] == inputs[2]["routes"]


@pytest.mark.parametrize("radius,profile", [(28, "current_28cm_radius"), (30, "historical_30cm_radius")])
def test_matching_current_and_historical_capsules_preserve_evidence(radius, profile):
    survey, audit, walkthrough = candidate_inputs({(x, 0): 90.5 for x in range(3)})
    survey["capsule_radius_cm"] = audit["capsule_radius_cm"] = radius

    candidate, report = build_candidates(survey, audit, walkthrough)

    assert candidate["route_planning"]["survey_capsule_radius_cm"] == radius
    assert candidate["route_planning"]["survey_capsule_half_height_cm"] == 88
    assert report["capsule_contract"]["capsule_profile"] == profile
    assert report["capsule_contract"]["paired_runtime_capsule_matches"] is True
    assert "conservative candidates" in report["capsule_contract"]["capsule_scope"]
    assert "fresh native CharacterMovement" in report["capsule_contract"]["capsule_scope"]
    assert report["native_walking_verified"] is False


@pytest.mark.parametrize("survey_radius,audit_radius", [(28, 30), (30, 28)])
def test_mixing_capsule_surveys_and_bookmark_probes_is_rejected(survey_radius, audit_radius):
    survey, audit, walkthrough = candidate_inputs({(0, 0): 90.5})
    survey["capsule_radius_cm"] = survey_radius
    audit["capsule_radius_cm"] = audit_radius
    with pytest.raises(ValueError, match="do not match"):
        build_candidates(survey, audit, walkthrough)


@pytest.mark.parametrize("field", ["capsule_radius_cm", "capsule_half_height_cm"])
@pytest.mark.parametrize("document", [0, 1], ids=["survey", "audit"])
@pytest.mark.parametrize("bad_value", [None, True, "28", float("nan"), float("inf"), {}])
def test_missing_or_invalid_capsule_evidence_is_rejected(field, document, bad_value):
    inputs = candidate_inputs({(0, 0): 90.5})
    if bad_value is None:
        inputs[document].pop(field)
    else:
        inputs[document][field] = bad_value
    with pytest.raises(ValueError, match="finite numeric capsule dimensions"):
        build_candidates(*inputs)


@pytest.mark.parametrize("radius,half_height", [(27, 88), (29, 88), (28, 80), (30, 87)])
def test_unrecognized_person_dimensions_are_not_silently_accepted(radius, half_height):
    survey, audit, walkthrough = candidate_inputs({(0, 0): 90.5})
    for document in (survey, audit):
        document["capsule_radius_cm"] = radius
        document["capsule_half_height_cm"] = half_height
    with pytest.raises(ValueError, match="Supported survey capsules"):
        build_candidates(survey, audit, walkthrough)


def test_matching_radius_does_not_allow_mismatched_height():
    survey, audit, walkthrough = candidate_inputs({(0, 0): 90.5})
    audit["capsule_half_height_cm"] = 86
    with pytest.raises(ValueError, match="do not match"):
        build_candidates(survey, audit, walkthrough)
