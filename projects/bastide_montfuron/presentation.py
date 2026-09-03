"""How the bastide looks: garden, pool life, furniture, lighting, the summer light.

Runs inside Blender through homespec/blender/scene.py. Positions are metres
in the spec's frame: the tower is x 0..7.5, the main wing 7.5..21.5, the
kitchen 21.5..30.5, all y 0..8; the terrace is y -5..0; the pool garden
lies two metres lower, south of y = -5.

Each room is dressed by its own module in ``rooms/``: ``dress(scene, M)``
adds its furniture, plants and lights, ``SHOTS`` lists its camera views as
``(location, look_direction, exposure)`` and ``PENDANTS`` maps the spec's
pendant ids in that room to an asset and a wattage. This file builds the
shared materials, calls every room, and strings the shots into one route
at four seconds each. ``HOMESPEC_ROOM=living`` in the environment keeps only
that room's shots, so its views are frames 1, 97, 193 and so on.
"""
import os
import sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from rooms import bedrooms, dining, exterior, hall, kitchen, living, tower  # noqa: E402

HDRI = os.path.join(HERE, "..", "..", "assets", "hdri", "qwantani_puresky_2k.hdr")
ROOMS = [("exterior", exterior), ("hall", hall), ("living", living), ("dining", dining), ("kitchen", kitchen), ("bedrooms", bedrooms), ("tower", tower)]
SECONDS_PER_SHOT = 4.0
FPS = 24


def materials(scene) -> SimpleNamespace:
    """Every material the rooms share, by name. A room may add its own with ``scene.pbr`` or ``scene.flat``."""
    M = SimpleNamespace()
    M.gravel = scene.pbr("p_gravel", "gravel", tile=2.5, value=1.45, tint=(1.0, 0.98, 0.9))
    M.earth = scene.flat("p_earth", (0.44, 0.42, 0.28), rough=1.0)
    M.hill = scene.flat("p_hill", (0.32, 0.36, 0.26), rough=1.0)
    M.rug_red = scene.pbr("p_rug_red", "quatrefoil_jacquard_fabric", tile=1.2, value=0.7, tint=(0.75, 0.3, 0.25))
    M.rug_jute = scene.pbr("p_rug_jute", "rough_linen", tile=0.6, value=0.9, tint=(0.8, 0.7, 0.52))
    M.brass = scene.flat("p_brass", (0.8, 0.62, 0.3), rough=0.35, metal=1.0)
    M.shade = scene.flat("p_shade", (0.96, 0.9, 0.78), rough=0.9, emit=1.4)
    M.copper = scene.flat("p_copper", (0.85, 0.45, 0.3), rough=0.3, metal=1.0)
    M.straw = scene.flat("p_straw", (0.62, 0.45, 0.24), rough=0.9, bump=0.7)
    M.charcoal = scene.flat("p_charcoal", (0.16, 0.17, 0.17), rough=0.6)
    M.white_linen = scene.flat("p_white_linen", (0.9, 0.84, 0.74), rough=0.95, bump=0.4)
    M.taupe_linen = scene.flat("p_taupe_linen", (0.5, 0.42, 0.34), rough=0.95, bump=0.4)
    M.cut_stone = scene.pbr("p_cut_stone", "beige_wall_001", tile=1.0, value=0.95, tint=(0.96, 0.9, 0.78))
    M.linen = scene.pbr("p_linen", "rough_linen", tile=0.5, value=1.25, tint=(0.94, 0.92, 0.86))
    M.grey_linen = scene.pbr("p_grey_linen", "rough_linen", tile=0.5, value=0.8, tint=(0.62, 0.58, 0.52))
    M.wicker = scene.pbr("p_wicker", "rough_linen", tile=0.12, value=1.0, tint=(0.78, 0.62, 0.4))
    M.oak = scene.pbr("p_oak", "oak_wood_planks", tile=1.2, value=1.1, tint=(1.0, 0.92, 0.8))
    M.iron = scene.flat("p_iron", (0.06, 0.06, 0.06), rough=0.5, metal=0.7)
    M.box_leaf = scene.flat("p_box_leaf", (0.08, 0.17, 0.06), rough=0.85)
    M.box_core = scene.flat("p_box_core", (0.03, 0.06, 0.02), rough=1.0)
    M.lavender = scene.flat("p_lavender", (0.5, 0.46, 0.66), rough=1.0)
    M.lavender_leaf = scene.flat("p_lavender_leaf", (0.36, 0.42, 0.34), rough=1.0)
    M.oleander = scene.flat("p_oleander", (0.14, 0.28, 0.12), rough=1.0)
    M.pink = scene.flat("p_pink", (0.92, 0.5, 0.65), rough=0.9)
    M.cypress = scene.flat("p_cypress", (0.09, 0.17, 0.09), rough=0.95)
    M.pine = scene.flat("p_pine", (0.10, 0.20, 0.09), rough=1.0)
    M.trunk = scene.flat("p_trunk", (0.28, 0.22, 0.16), rough=0.9)
    M.vine = scene.flat("p_vine", (0.08, 0.2, 0.07), rough=1.0, bump=0.6)
    return M


def dress(scene):
    M = materials(scene)
    for _name, room in ROOMS:
        room.dress(scene, M)
        for eid, (asset, energy) in getattr(room, "PENDANTS", {}).items():   # chandeliers hang from the spec's pendants
            c = scene.center(eid)
            z = 2.2 if c.z < 4.0 else c.z - 0.9
            scene.model(asset, (c.x, c.y, z), scale=1.0)
            scene.point_light(f"{eid}_light", (c.x, c.y, z + 0.4), energy, radius=0.25)
    for e in scene.ir["entities"]:
        if e["kind"] == "downlight":
            c = scene.center(e["id"])
            scene.point_light(f"{e['id']}_light", (c.x, c.y, c.z - 0.05), 12, radius=0.05)

    # ---- the summer light: a high sun from the south-west
    scene.world_hdri(HDRI, rotation_deg=160, strength=0.9)
    scene.sun((0.45, 0.55, -0.7), energy=5.0, angle=0.7)
    scene.hide("D1.glass")

    # ---- the route: every room's shots in order, four seconds apart; HOMESPEC_ROOM keeps one room's
    only = os.environ.get("HOMESPEC_ROOM")
    shots, t = [], 0.0
    for name, room in ROOMS:
        if only and name != only:
            continue
        for loc, look, ev in room.SHOTS:
            shots.append((t, loc, look, ev))
            t += SECONDS_PER_SHOT
    scene.path([(t, loc, look) for t, loc, look, _ in shots], fps=FPS, lens=26, fstop=8.0, focus=6.0)
    scene.exposure([(t, ev) for t, _, _, ev in shots], fps=FPS)
    scene.render_settings(rx=1600, ry=900, samples=128, exposure=0.0, adaptive=0.08)
