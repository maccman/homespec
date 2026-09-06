"""Photograph-supported corrections to house-adjacent planting only.

Photo46 places slender cypresses at the principal block's southeast and far
corners, with clear side openings. Photo12 has a cypress and tall oleanders
framing the kitchen on its west side. The former cypress at y6.3m stood directly
in front of D_E2; the former three west bushes occupied the kitchen approach.
Groups move as whole plants, including every trunk, core and blossom.
Photographic foreground trees and the courtyard planting border are corrected
scene-wide. An inferred open foreground approach also relocates unsurveyed
woodland scatter to the west grove. Render visibility flags are retained.
"""
from __future__ import annotations

import json
import re

SOURCE = "PHOTOS/VICTOR FITZ/DJI_20231012094055_0813_D.jpg; PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-21.jpg; Final Collection-18.jpg"

# All sizes/positions are photograph-scaled inference, not a landscape survey.
# The anchor is the soil/root point, not the centroid of a foliage object.
CYPRESSES = (
    ("cypress_0", (8.50, .30, -.02), (8.20, -.32, -.022), (.72, .72, 6.6 / 6.5)),
    ("cypress_1", (8.63, 1.15, -.02), (8.40, .75, -.022), (.70, .70, 7.2 / 7.0)),
    ("cypress_2", (8.65, 6.30, -.02), (-5.35, 7.97, -.022), (.70, .70, 6.0 / 6.8)),
    ("cypress_3", (8.60, 9.80, -.02), (8.50, 10.12, -.022), (.70, .70, 6.8 / 6.7)),
)
OLEANDERS = (
    ("white_oleander0", (-4.50, 2.00, -.03), (-6.65, 2.00, -.03), (.95, 1, 1.35)),
    ("white_oleander1", (-4.60, 4.70, -.03), (-6.70, 4.70, -.03), (.95, 1, 1.42)),
    ("white_oleander2", (-4.80, 7.00, -.03), (-6.55, 7.00, -.03), (.95, 1, 1.50)),
    # The inferred parking screen previously crossed the open courtyard seen
    # in photos08/11. Move the whole screen to the north parking boundary.
    ("white_oleander3", (10.70, 15.60, -.03), (13.0, 27.6, -.03), (1, 1, 1)),
    ("white_oleander4", (13.50, 15.70, -.03), (15.7, 27.6, -.03), (1, 1, 1)),
    ("white_oleander5", (16.30, 15.70, -.03), (18.4, 27.6, -.03), (1, 1, 1)),
    ("white_oleander6", (20.40, 15.50, -.03), (21.1, 27.6, -.03), (1, 1, 1)),
)

TREES = (
    # Photo41 retains an olive at the west of the entrance. The former crown
    # extended over the entire kitchen approach in photo12. Position and size
    # remain inferred; complete geometry is retained at the west terrace edge.
    ("old_olive_by_gable", (-3.5, -1.2, -.02), (-6.5, -1.2, -.02), (.82, .82, .82)),
    # Photo46 has the paired foreground pines at the west pool end. The
    # additional unsurveyed eastern pine obscured most of the facade. Retain
    # it at the east garden boundary, outside the open pool garden.
    ("mature_pine2", (21, -12, -.08), (34, -4, -.08), (1, 1, 1)),
)


def _transform(scene, prefix, source, target, scale):
    import bpy
    from mathutils import Matrix, Vector

    objects = [obj for obj in bpy.data.objects if obj.name.startswith(prefix + "_")]
    if not objects:
        raise ValueError(f"Missing complete facade plant group {prefix}")
    delta = Matrix.Translation(Vector(target)) @ Matrix.Diagonal((*scale, 1)) @ Matrix.Translation(-Vector(source))
    for obj in objects:
        # World-space composition handles baked branch vertices and linked leaf
        # meshes identically. Scaling the group about soil keeps its root planted.
        obj.matrix_world = delta @ obj.matrix_world
        obj["exterior_planting_source"] = SOURCE
        obj["exterior_planting_group"] = prefix
        obj["exterior_planting_root_m"] = list(target)
        obj["exterior_planting_inference"] = "Photo-scaled position and crown proportions; all-camera geometry correction"
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(corner) for obj in objects if obj.type == "MESH" for corner in obj.bound_box]
    minimum = [min(p[k] for p in corners) for k in range(3)]
    maximum = [max(p[k] for p in corners) for k in range(3)]
    if minimum[2] > .03:
        raise ValueError(f"Moved facade plant {prefix} floats above its soil: z={minimum[2]:.3f}")
    trunk = next((obj for obj in objects if obj.name == prefix + "_trunk"), None)
    if trunk:
        trunk_base = min((trunk.matrix_world @ Vector(corner)).z for corner in trunk.bound_box)
        if trunk_base > .01:
            raise ValueError(f"Moved cypress trunk {prefix} is not rooted: z={trunk_base:.3f}")
    return {"group": prefix, "source_root_m": source, "root_m": target, "scale": scale,
            "objects": [obj.name for obj in objects], "world_bbox_m": [minimum, maximum]}


def _clear_foreground_scatter(scene):
    """Move complete inferred scatter plants, recording the wider-grove change."""
    import bpy
    from mathutils import Matrix, Vector

    bpy.context.view_layer.update()
    groups = {}
    for obj in bpy.data.objects:
        match = re.match(r"^(wild_woodland\d+)(?:[_.].*)?$", obj.name)
        if match:
            groups.setdefault(match[1], set()).update((obj, *obj.children_recursive))
    delta = Matrix.Translation(Vector((-40, 0, 0)))
    changes = []
    for group, members in sorted(groups.items()):
        objects = sorted(members, key=lambda ob: ob.name)
        source_bounds = {}
        for obj in objects:
            if obj.type != "MESH":
                continue
            corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            source_bounds[obj.name] = [[min(p[k] for p in corners) for k in range(3)],
                                       [max(p[k] for p in corners) for k in range(3)]]
        if not any(lo[0] <= 16 and hi[0] >= -7 and lo[1] <= -8 and hi[1] >= -34
                   for lo, hi in source_bounds.values()):
            continue
        # Snapshot every world matrix before moving parents and children.
        worlds = {obj: obj.matrix_world.copy() for obj in objects}
        def depth(obj, members=members):
            value = 0
            while obj.parent in members:
                value += 1
                obj = obj.parent
            return value
        for obj in sorted(objects, key=depth):
            obj.matrix_world = delta @ worlds[obj]
            obj["exterior_planting_group"] = group
            obj["exterior_planting_inference"] = "Unsurveyed foreground scatter moved intact to west grove; inferred open approach"
            obj["exterior_planting_translation_m"] = (-40, 0, 0)
        changes.append({"group": group, "objects": [obj.name for obj in objects],
                        "source_world_bounds_m": source_bounds, "translation_m": [-40, 0, 0],
                        "wider_grove_changed": True})
    bpy.context.view_layer.update()
    scene.scene["exterior_open_approach_scatter"] = json.dumps({
        "scope": "Inferred open approach x[-7,16], y[-34,-8]; changes wider unsurveyed grove",
        "visibility": "No hiding or deletion; meshes, groups, dimensions and world Z retained",
        "changes": changes})
    return changes


def apply(scene):
    """Apply after exterior/fidelity_vegetation; never hide plants for a camera."""
    if scene.scene.get("exterior_facade_planting"):
        return
    changes = [_transform(scene, *item) for item in (*CYPRESSES, *OLEANDERS, *TREES)]
    scatter = _clear_foreground_scatter(scene)
    scene.scene["exterior_facade_planting"] = json.dumps(changes)
    scene.scene["exterior_planting_observation"] = (
        "Slender principal corner cypresses; former side-door cypress moved to kitchen west flank; "
        "three kitchen-garden oleanders rooted along west border. Photo46/12. "
        "Old olive retained at west terrace edge, inferred east pine moved to garden boundary, courtyard screen moved to north parking boundary. "
        "Unsurveyed foreground woodland moved intact 40m west to establish inferred open approach; wider grove changed; no per-camera visibility changes."
    )
    print(f"FLECHON facade planting: corrected complete facade groups; moved {len(scatter)} inferred foreground scatter groups intact to west grove", flush=True)
