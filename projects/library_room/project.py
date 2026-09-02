"""The library / dining room, as a spec.

Everything a builder needs is here. Nothing here is a cube. Furniture, sky,
and camera live in presentation.py and never reach the contractor.
"""
from homespec.core import Model
from homespec.lib import (Grid, assembly, bookcase, ceiling, kitchen_run, level, light, material, opening,
                       outlet, site, slab, space, wall)


def build() -> Model:
    m = Model("library-room", units="mm")

    # ---- site and levels
    site(m, parcel=[(-12000, -9000), (20000, -9000), (20000, 9000), (-12000, 9000)],
         setbacks={"front": 6000, "side": 1500, "rear": 3000}, north=12)
    level(m, "L0", elevation=0, height=3000)
    G = Grid(x={"A": -4000, "B": 4000}, y={"1": -2500, "2": 2500})
    m.grid = G.as_dict()

    # ---- materials: one address for rendering, one for buying
    material(m, "plaster_warm", texture="polyhaven/painted_plaster_wall", product="Lime plaster, warm white", supplier="TBD",
             finish="RAL 9001 mineral paint", render={"tile": 1.6, "tint": (0.96, 0.95, 0.91), "value": 1.9})
    material(m, "brick_painted", texture="polyhaven/brick_wall_02", product="Reclaimed brick, painted", supplier="TBD",
             finish="limewash", render={"tile": 1.6, "tint": (0.95, 0.9, 0.85), "value": 1.25})
    material(m, "oak_plank_190", texture="polyhaven/wood_floor", product="Engineered oak 190 x 15 mm", supplier="TBD",
             finish="matte hardwax oil", render={"tile": 2.2, "tint": (1.0, 0.92, 0.8), "value": 1.3})
    material(m, "walnut", texture="polyhaven/american_walnut_veneer", product="American walnut veneer on 19 mm ply", supplier="TBD",
             finish="oil", render={"tile": 1.4, "tint": (1.0, 0.86, 0.7), "value": 1.7})
    material(m, "ceiling_oak_tg", texture="polyhaven/oak_veneer_01", product="Oak T&G lining 140 x 20 mm", supplier="TBD",
             finish="clear matte", render={"tile": 0.9, "tint": (0.95, 0.8, 0.62), "value": 0.95})
    material(m, "terrazzo_white", texture="polyhaven/terrazzo_tiles", product="Terrazzo slab 40 mm", supplier="TBD",
             finish="honed", render={"tile": 1.0, "value": 1.15})
    material(m, "steel_black", product="Thermally broken steel frame", supplier="TBD", finish="powder coat RAL 9005",
             render={"color": (0.05, 0.05, 0.05), "rough": 0.4, "metal": 0.8})
    material(m, "glass_double", product="Double glazed low-e, 6/16/6", supplier="TBD",
             render={"color": (0.95, 0.98, 1.0), "rough": 0.02, "transmission": 1.0})
    material(m, "brass", product="Brushed brass", supplier="TBD", render={"color": (0.85, 0.62, 0.28), "rough": 0.28, "metal": 1.0})
    material(m, "white", product="White powder coat", render={"color": (0.9, 0.9, 0.88), "rough": 0.6})
    material(m, "concrete_slab", product="Reinforced concrete slab on ground", render={"color": (0.55, 0.55, 0.52), "rough": 0.9})

    # ---- assemblies
    assembly(m, "ext_wall", 200, [("plaster", 15), ("timber_frame_140", 140), ("sheathing", 30), ("plaster", 15)], finish_in="plaster_warm")
    assembly(m, "slab_on_ground", 200, [("concrete", 185), ("oak_plank_190", 15)])

    # ---- walls, traced counter-clockwise; grid lines are the inside faces
    wall(m, "W1", G("A", "1"), G("B", "1"), "ext_wall", "L0")                          # south: kitchen, window, clerestory
    wall(m, "W2", G("B", "1"), G("B", "2"), "ext_wall", "L0")                          # east: sliding door to courtyard
    wall(m, "W3", G("B", "2"), G("A", "2"), "ext_wall", "L0")                          # north: library wall
    wall(m, "W4", G("A", "2"), G("A", "1"), "ext_wall", "L0", finish="brick_painted")  # west: painted brick

    opening(m, "D1", "W2", "sliding_door", width=3400, height=2700, at="center", leaves=2, open_leaf="end")
    opening(m, "N1", "W1", "window", width=1600, height=1400, sill=900, at=800)
    opening(m, "C1", "W1", "clerestory", width=4600, height=500, sill=2350, at={"from_end": 400}, mullions=3, frame_size=40)

    room = [G("A", "1"), G("B", "1"), G("B", "2"), G("A", "2")]
    slab(m, "S0", [(-4200, -2700), (4200, -2700), (4200, 2700), (-4200, 2700)], 200, "L0", "oak_plank_190")
    ceiling(m, "CL0", room, "L0", lining="ceiling_oak_tg", plank=140,
            beams={"size": (120, 260), "spacing": 1600, "along": "y", "material": "walnut"})
    space(m, "living", "L0", room, "living_dining_kitchen", bounded_by=["W1", "W2", "W3", "W4"], occupancy=6)

    # ---- built-in joinery
    bookcase(m, "BK1", on="W3", from_start=1200, length=6400, height=2700, depth=340, bays=8, shelves=7, material="walnut")
    kitchen_run(m, "K1", on="W1", from_start=2800, length=4600, depth=620, counter_height=900,
                fronts="walnut", counter="terrazzo_white", doors=6, pulls="brass",
                upper={"from_start": 3900, "length": 3000, "depth": 320, "height": 600, "bottom": 1650})

    # ---- services
    for i, (x, y) in enumerate([(-2400, 1600), (-2400, -400), (800, 1600), (800, -400), (2400, 1600), (2400, -400)], 1):
        light(m, f"L{i}", "downlight", at=(x, y), level="L0", watts=8)
    light(m, "L7", "pendant", at=(-1600, -1250), level="L0", drop=950, watts=60)
    outlet(m, "P1", on="W1", from_start=1200, height=300)
    outlet(m, "P2", on="W1", from_start=3600, height=1100, kind="power_double_counter")
    outlet(m, "P3", on="W1", from_start=6200, height=1100, kind="power_double_counter")
    outlet(m, "P4", on="W4", from_start=1800, height=300)
    outlet(m, "P5", on="W3", from_start=600, height=300)

    # ---- project-specific rule: the library wall keeps a clear reading strip in front of it
    @m.check
    def reading_strip(ir):
        bk = ir["_by_id"]["BK1"]["bbox"]
        for e in ir["entities"]:
            if "fixed" in e["tags"] and e.get("bbox") and not e["id"].startswith("BK1") and e["physical"]:
                (x0, y0, _), (x1, y1, _) = e["bbox"]
                if x1 > bk[0][0] and x0 < bk[1][0] and y1 > bk[0][1] - 1200:
                    yield ("reading_strip", e["id"], False, int(bk[0][1] - y1), 1200, "fixed element inside the 1200 strip in front of BK1")
        yield ("reading_strip", "BK1", True, "clear", 1200, "")

    return m
