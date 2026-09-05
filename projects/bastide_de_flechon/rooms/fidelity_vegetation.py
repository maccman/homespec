"""Keep the inferred background woodland outside the real house envelope.

The estate's radial scatter was centred on the salon and could put distant
crowns and pine trunks inside the northern guest wing. Remove only colliding
background trees, retaining the deliberately placed garden planting.
"""

import bpy
from mathutils import Vector


def overlaps(a, b):
    """Separating-axis test for the convex roof footprints and world XY boxes."""
    for polygon in (a, b):
        for i, p in enumerate(polygon):
            q = polygon[(i + 1) % len(polygon)]
            nx, ny = p[1] - q[1], q[0] - p[0]
            aa = [x * nx + y * ny for x, y in a]
            bb = [x * nx + y * ny for x, y in b]
            if max(aa) < min(bb) or max(bb) < min(aa):
                return False
    return True


def apply(scene, _):
    footprints = []
    for eid in ("R_MAIN", "R_K", "R_H", "R_A"):
        roof = scene.entity(eid)
        footprints.append([(x / 1000, y / 1000) for x, y in roof["params"]["outline"]])
    bpy.context.view_layer.update()
    rejected, pine_ids = [], set()
    for ob in list(bpy.data.objects):
        if ob.type != "MESH" or not ob.name.startswith(("wild_woodland", "wild_pine_needles", "background_pine_")):
            continue
        corners = [ob.matrix_world @ Vector(v) for v in ob.bound_box]
        if min(v.z for v in corners) > 8.4 or max(v.z for v in corners) < -0.1:
            continue
        xmin, xmax = min(v.x for v in corners) - 0.25, max(v.x for v in corners) + 0.25
        ymin, ymax = min(v.y for v in corners) - 0.25, max(v.y for v in corners) + 0.25
        box = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        if any(overlaps(box, footprint) for footprint in footprints):
            rejected.append(ob)
            if ob.name.startswith("background_pine_trunk"):
                pine_ids.add(ob.name.removeprefix("background_pine_trunk"))
    # A rejected trunk takes its corresponding upper boughs with it.
    for ob in list(bpy.data.objects):
        if any(ob.name.startswith("background_pine_bough" + index + "_") for index in pine_ids) and ob not in rejected:
            rejected.append(ob)
    names = [ob.name for ob in rejected]
    for ob in rejected:
        bpy.data.objects.remove(ob, do_unlink=True)
    scene.scene["flechon_background_tree_clearance"] = ", ".join(names)
    print(f"FLECHON background woodland: removed {len(names)} colliding scatter objects: {names}", flush=True)
