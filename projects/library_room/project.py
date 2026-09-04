"""The library room: a spec.

Everything a builder needs is here and nothing else. Furniture, sky and
camera live in presentation.py and never reach the contractor. Why each
choice was made is in decisions.md.
"""
from homespec import *  # noqa: F403


def build() -> House:
    with House("library-room") as house:
        # ---- site and setting out
        Site(parcel=[(-12000, -9000), (20000, -9000), (20000, 9000), (-12000, 9000)],
             setbacks=[6000, 1500, 3000, 1500], north=12)
        L0 = Level("L0", elevation=0, height=3000)
        grid = Grid(x={"A": -4000, "B": 4000}, y={"1": -2500, "2": 2500})
        A, B, one, two = grid.lines("A", "B", "1", "2")

        # Material definitions include concealed assembly layers.
        Material('plaster', product='Plaster base coats')
        Material('timber_frame_140', product='140 mm timber framing')
        Material('sheathing', product='Structural sheathing')

        # ---- materials: one address for rendering, one for buying
        plaster = Material("plaster_warm", texture="polyhaven/painted_plaster_wall", product="Lime plaster, warm white", supplier="TBD",
                           finish="RAL 9001 mineral paint", render=Render(tile=1.6, tint=(0.96, 0.95, 0.91), value=1.9))
        brick = Material("brick_painted", texture="polyhaven/brick_wall_02", product="Reclaimed brick, painted", supplier="TBD",
                         finish="limewash", render=Render(tile=1.6, tint=(0.95, 0.9, 0.85), value=1.25))
        oak_floor = Material("oak_plank_190", texture="polyhaven/wood_floor", product="Engineered oak 190 x 15 mm", supplier="TBD",
                             finish="matte hardwax oil", render=Render(tile=2.2, tint=(1.0, 0.92, 0.8), value=1.3))
        walnut = Material("walnut", texture="polyhaven/american_walnut_veneer", product="American walnut veneer on 19 mm ply", supplier="TBD",
                          finish="oil", render=Render(tile=1.4, tint=(1.0, 0.86, 0.7), value=1.7))
        oak_lining = Material("ceiling_oak_tg", texture="polyhaven/oak_veneer_01", product="Oak T&G lining 140 x 20 mm", supplier="TBD",
                              finish="clear matte", render=Render(tile=0.9, tint=(0.95, 0.8, 0.62), value=0.95))
        terrazzo = Material("terrazzo_white", texture="polyhaven/terrazzo_tiles", product="Terrazzo slab 40 mm", supplier="TBD",
                            finish="honed", render=Render(tile=1.0, value=1.15))
        Material("steel_black", product="Thermally broken steel frame", supplier="TBD", finish="powder coat RAL 9005",
                 render=Render(color=(0.05, 0.05, 0.05), rough=0.4, metal=0.8))
        Material("glass_double", product="Double glazed low-e, 6/16/6", supplier="TBD",
                 render=Render(color=(0.95, 0.98, 1.0), rough=0.02, transmission=1.0))
        Material("brass", product="Brushed brass", supplier="TBD", render=Render(color=(0.85, 0.62, 0.28), rough=0.28, metal=1.0))
        Material("white", product="White powder coat", render=Render(color=(0.9, 0.9, 0.88), rough=0.6))

        # ---- assemblies
        ext_wall = Assembly("ext_wall", layers=[Layer(material="plaster", thickness=15), Layer(material="timber_frame_140", thickness=140),
                                                Layer(material="sheathing", thickness=30), Layer(material="plaster", thickness=15)], finish_in=plaster)

        # ---- walls, traced counter-clockwise; grid lines are the inside faces
        W1 = Wall("W1", A & one, B & one, assembly=ext_wall, level=L0)                    # south: kitchen, window, clerestory
        W2 = Wall("W2", B & one, B & two, assembly=ext_wall, level=L0)                    # east: sliding door to the courtyard
        W3 = Wall("W3", B & two, A & two, assembly=ext_wall, level=L0)                    # north: the library wall
        W4 = Wall("W4", A & two, A & one, assembly=ext_wall, level=L0, material=brick)    # west: painted brick

        SlidingDoor("D1", host=W2, width=3400, height=2700, at="center", leaves=2, open_leaf="end")
        Window("N1", host=W1, width=1600, height=1400, sill=900, at=800)
        Clerestory("C1", host=W1, width=4600, height=500, sill=2350, at=from_end(400))

        room = [A & one, B & one, B & two, A & two]
        Slab("S0", outline=[(-4200, -2700), (4200, -2700), (4200, 2700), (-4200, 2700)], thickness=200, level=L0, material=oak_floor)
        Ceiling("CL0", outline=room, level=L0, material=oak_lining, plank=140,
                beams=BeamGrid(width=120, depth=260, spacing=1600, along="y", material=walnut))
        Space("living", outline=room, use="living_dining_kitchen", level=L0, bounded_by=[W1, W2, W3, W4], occupancy=6)

        # ---- built-in joinery
        Bookcase("BK1", on=W3, from_start=1200, length=6400, height=2700, depth=340, bays=8, shelves=7, material=walnut)
        KitchenRun("K1", on=W1, from_start=2800, length=4600, depth=620, counter_height=900, fronts=walnut, counter=terrazzo, doors=6,
                   upper=UpperCabinet(from_start=3900, length=3000, depth=320, height=600, bottom=1650))

        # ---- services
        for i, (x, y) in enumerate([(-3200, 1600), (-3200, -400), (0, 1600), (0, -400), (3200, 1600), (3200, -400)], 1):
            Downlight(f"L{i}", at=(x, y), level=L0, watts=8)       # midway between the beams, which sit at 1600 centres from -4000
        Pendant("L7", at=(-1600, -1250), drop=950, level=L0, watts=60)
        Outlet("P1", on=W1, from_start=1200, height=300)
        Outlet("P2", on=W1, from_start=3600, height=1100, variant="double_counter")
        Outlet("P3", on=W1, from_start=6200, height=1100, variant="double_counter")
        Outlet("P4", on=W4, from_start=1800, height=300)
        Outlet("P5", on=W3, from_start=600, height=300)

        # ---- a rule of this house: keep a 1200 reading strip clear in front of the library wall
        @house.check
        def reading_strip(ir):
            bk = ir.entity("BK1").geometry.bbox
            for e in ir.tagged("fixed"):
                if e.geometry and e.physical and not e.id.startswith("BK1"):
                    (x0, _, _), (x1, y1, _) = e.geometry.bbox.min, e.geometry.bbox.max
                    if x1 > bk.min[0] and x0 < bk.max[0] and y1 > bk.min[1] - 1200:
                        yield ("reading_strip", e.id, False, int(bk.min[1] - y1), 1200, "fixed element inside the strip in front of BK1")
            yield ("reading_strip", "BK1", True, "clear", 1200)

    return house
