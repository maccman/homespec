"""Casale Poggio: a two-bedroom Umbrian farmhouse.

A restored stone casale of the kind let as a holiday house: one long
volume under a terracotta gable roof, thick rubble walls, small shuttered
windows to the north and glazed doors opening south onto a stone loggia,
exposed chestnut beams over terracotta ceilings, cotto floors throughout.
Rooms run in a row: bedroom and bath, entrance hall, living room, kitchen
and dining, second bedroom and bath. Why each choice was made is in
decisions.md.
"""
from homespec import *  # noqa: F403


def build() -> House:
    with House("casale-poggio") as house:
        # ---- site: a gentle south-facing slope, olive grove below, track from the north
        Site(parcel=[(-20000, -30000), (45000, -30000), (45000, 22000), (-20000, 22000)],
             setbacks=[8000, 5000, 5000, 5000], north=20)
        L0 = Level("L0", elevation=0, height=3200)
        grid = Grid(x={"A": 0, "B": 4275, "C": 6425, "D": 12375, "E": 16375, "F": 20000}, y={"1": 0, "2": 4575, "3": 7500})
        A, B, C, D, E, F = grid.lines("A", "B", "C", "D", "E", "F")
        one, two, three = grid.lines("1", "2", "3")

        # Material definitions include concealed assembly layers.
        Material('rubble_stone', product='Rubble masonry core')
        Material('brick_block', product='Clay partition blocks')
        Material('steel_black', product='Black steel cabinet plinth', render=Render(color=(0.05, 0.05, 0.05), metal=0.8))

        # ---- materials
        stone = Material("stone_rubble", texture="polyhaven/rustic_stone_wall", product="Local limestone rubble, lime pointed flush", supplier="local quarry",
                         finish="pointed flush, brushed", render=Render(tile=2.2, value=1.05, tint=(1.0, 0.96, 0.9)))
        lime = Material("lime_plaster", texture="polyhaven/white_stucco", product="Lime plaster, natural", supplier="TBD", finish="limewash, warm white",
                        render=Render(tile=1.5, value=1.15, tint=(0.98, 0.95, 0.88)))
        cotto = Material("cotto", texture="polyhaven/terracotta_floor_tiles", product="Handmade cotto 300 x 300 x 25", supplier="Impruneta", finish="linseed oil and wax",
                         render=Render(tile=1.2, value=1.1, tint=(1.0, 0.9, 0.8)))
        pianelle = Material("pianelle", texture="polyhaven/terracotta_floor_tiles", product="Terracotta pianelle 150 x 300, between rafters", supplier="Impruneta",
                            render=Render(tile=0.45, value=1.0, tint=(1.0, 0.88, 0.76)))
        chestnut = Material("chestnut", texture="polyhaven/dark_wooden_planks", product="Chestnut, sawn and oiled", supplier="TBD", finish="oil",
                            render=Render(tile=1.4, value=0.95, tint=(1.0, 0.86, 0.7)))
        coppi = Material("coppi", texture="polyhaven/clay_roof_tiles_02", product="Reclaimed terracotta coppi tiles on battens", supplier="salvage",
                         render=Render(tile=1.0, value=1.05, tint=(1.0, 0.9, 0.82)))
        pietra = Material("pietra_serena", product="Pietra serena counter 40 mm", supplier="TBD", finish="honed", render=Render(color=(0.42, 0.43, 0.44), rough=0.5))
        iron = Material("iron", product="Wrought iron, wax finish", supplier="local smith", render=Render(color=(0.06, 0.06, 0.06), rough=0.5, metal=0.7))
        Material("glass_single", product="Clear glass 6 mm in iron frames", render=Render(color=(0.95, 0.98, 1.0), rough=0.02, transmission=1.0))
        Material("chestnut_door", texture="polyhaven/dark_wooden_planks", product="Chestnut plank door, iron strap hinges", render=Render(tile=0.8, value=0.85, tint=(1.0, 0.82, 0.66)))
        Material("brass", product="Aged brass", render=Render(color=(0.7, 0.55, 0.3), rough=0.4, metal=1.0))
        Material("white", product="White ceramic", render=Render(color=(0.92, 0.92, 0.9), rough=0.4))

        # ---- assemblies: 500 mm rubble walls outside, 150 mm plastered block partitions inside
        rubble = Assembly("rubble_wall", layers=[Layer(material="rubble_stone", thickness=450), Layer(material="lime_plaster", thickness=50)],
                          finish_in=stone, finish_out=stone)
        partition = Assembly("partition", layers=[Layer(material="lime_plaster", thickness=15), Layer(material="brick_block", thickness=120),
                                                  Layer(material="lime_plaster", thickness=15)], finish_in=lime)
        breast = Assembly("chimney_breast", layers=[Layer(material="rubble_stone", thickness=600)], finish_in=stone)

        # ---- external walls, traced counter-clockwise; grid lines are the inside faces
        W1 = Wall("W1", A & one, F & one, assembly=rubble, level=L0)        # south: the loggia front, glazed doors from every room
        W2 = Wall("W2", F & one, F & three, assembly=rubble, level=L0)      # east: gable end
        W3 = Wall("W3", F & three, A & three, assembly=rubble, level=L0)    # north: courtyard and front door
        W4 = Wall("W4", A & three, A & one, assembly=rubble, level=L0)      # west: gable end

        # ---- partitions, centred on grid lines B, C, D, E and 2
        P1 = Wall("P1", B & one, B & three, assembly=partition, level=L0, align="center", external=False)   # bedroom 1 and bath | hall
        P2 = Wall("P2", C & one, C & three, assembly=partition, level=L0, align="center", external=False)   # hall | living
        P3 = Wall("P3", D & one, D & three, assembly=partition, level=L0, align="center", external=False)   # living | kitchen
        P4 = Wall("P4", E & one, E & three, assembly=partition, level=L0, align="center", external=False)   # kitchen | bedroom 2 and bath
        P5 = Wall("P5", A & two, (4200, 4575), assembly=partition, level=L0, align="center", external=False)  # bedroom 1 | bath 1
        P6 = Wall("P6", (16450, 4575), F & two, assembly=partition, level=L0, align="center", external=False)  # bedroom 2 | bath 2
        FP = Wall("FP", (8200, 7500), (9800, 7500), assembly=breast, level=L0, align="right", external=False)  # chimney breast on the living room's north wall

        # ---- openings. South: glazed iron doors onto the loggia. North and ends: small deep windows with shutters.
        Door("D1", host=W1, width=1200, height=2300, at=1500, glazed=True, frame=iron, glazing="glass_single")       # bedroom 1
        Door("D2", host=W1, width=1200, height=2300, at=4750, glazed=True, frame=iron, glazing="glass_single")       # hall
        Door("D3", host=W1, width=1400, height=2400, at=7300, glazed=True, frame=iron, glazing="glass_single")       # living
        Door("D4", host=W1, width=1400, height=2400, at=10000, glazed=True, frame=iron, glazing="glass_single")      # living
        Door("D5", host=W1, width=1200, height=2300, at=13700, glazed=True, frame=iron, glazing="glass_single")      # kitchen
        Door("D6", host=W1, width=1200, height=2300, at=17700, glazed=True, frame=iron, glazing="glass_single")      # bedroom 2
        Window("N1", host=W2, width=1000, height=1300, sill=1000, at=1500, frame=chestnut, glazing="glass_single")    # bedroom 2, east
        Window("N2", host=W2, width=600, height=800, sill=1600, at=5500, frame=chestnut, glazing="glass_single")      # bath 2, east
        Window("N3", host=W3, width=600, height=800, sill=1600, at=1500, frame=chestnut, glazing="glass_single")      # bath 2, north
        Window("N4", host=W3, width=1200, height=1400, sill=1000, at=5200, frame=chestnut, glazing="glass_single")    # kitchen, over the counter
        Window("N5", host=W3, width=1400, height=1400, sill=1000, at=10600, frame=chestnut, glazing="glass_single")   # living, north light
        Door("D0", host=W3, width=1100, height=2300, at=14150, frame=chestnut, leaf="chestnut_door")                   # front door, into the hall
        Window("N6", host=W3, width=600, height=800, sill=1600, at=17900, frame=chestnut, glazing="glass_single")     # bath 1, north
        Window("N7", host=W4, width=600, height=800, sill=1600, at=1400, frame=chestnut, glazing="glass_single")      # bath 1, west
        Window("N8", host=W4, width=1000, height=1300, sill=1000, at=4750, frame=chestnut, glazing="glass_single")    # bedroom 1, west
        Door("D7", host=P1, width=900, height=2100, at=1000, frame=chestnut, leaf="chestnut_door")                    # hall -> bedroom 1
        Arch("A1", host=P2, width=1500, height=2100, at=2000)                                                        # hall -> living
        Arch("A2", host=P3, width=1800, height=2000, at=2600)                                                        # living -> kitchen
        Door("D8", host=P4, width=900, height=2100, at=1200, frame=chestnut, leaf="chestnut_door")                    # kitchen -> bedroom 2
        Door("D9", host=P5, width=800, height=2100, at=1500, frame=chestnut, leaf="chestnut_door")                    # bedroom 1 -> bath 1
        Door("D10", host=P6, width=800, height=2100, at=800, frame=chestnut, leaf="chestnut_door")                    # bedroom 2 -> bath 2
        Arch("FP.hearth", host=FP, width=1000, height=600, at=300)                                                   # the firebox

        # ---- floors, ceiling, roofs
        Slab("S0", outline=[(-500, -500), (20500, -500), (20500, 8000), (-500, 8000)], thickness=250, level=L0, material=cotto)
        Slab("S1", outline=[(4350, -3000), (16300, -3000), (16300, -500), (4350, -500)], thickness=150, level=L0, material=cotto, top=-20)
        Ceiling("CL0", outline=[A & one, F & one, F & three, A & three], level=L0, material=pianelle, thickness=30,
                beams=BeamGrid(width=120, depth=180, spacing=700, along="y", material=chestnut))
        Roof("R0", outline=[(-500, -500), (20500, -500), (20500, 8000), (-500, 8000)], level=L0, material=coppi,
             shape="gable", ridge_along="x", pitch=22, overhang=500, thickness=250, eave=3300, gable_thickness=500, gable_material=stone)

        # ---- the pergola: stone piers, a chestnut beam, a ledger on the wall, rafters between, vines to come
        for k, x in enumerate((4600, 8500, 12400, 16050), 1):
            Column(f"LP{k}", at=(x, -2750), size=500, height=2200, level=L0, material=stone)
        Beam("LB", (4350, -2750), (16300, -2750), width=250, depth=250, underside=2200, level=L0, material=chestnut)
        Beam("LL", (4350, -625), (16300, -625), width=250, depth=250, underside=2200, level=L0, material=chestnut)
        for k, x in enumerate(range(4500, 16301, 600), 1):
            Beam(f"LR{k}", (x, -3100), (x, -500), width=100, depth=160, underside=2450, level=L0, material=chestnut, tags={"rafter"})

        Chimney("CH", at=(9000, 7300), size=700, base=3000, height=1900, level=L0, material=stone)   # over the living room fire, through the north slope

        # ---- rooms
        Space("bed1", outline=[(0, 0), (4200, 0), (4200, 4500), (0, 4500)], use="bedroom", level=L0, bounded_by=[W1, P1, P5, W4], occupancy=2)
        Space("bath1", outline=[(0, 4650), (4200, 4650), (4200, 7500), (0, 7500)], use="bathroom", level=L0, bounded_by=[P5, P1, W3, W4])
        Space("hall", outline=[(4350, 0), (6350, 0), (6350, 7500), (4350, 7500)], use="hall", level=L0, bounded_by=[W1, P2, W3, P1])
        Space("living", outline=[(6500, 0), (12300, 0), (12300, 7500), (6500, 7500)], use="living", level=L0, bounded_by=[W1, P3, W3, P2], occupancy=6)
        Space("kitchen", outline=[(12450, 0), (16300, 0), (16300, 7500), (12450, 7500)], use="kitchen_dining", level=L0, bounded_by=[W1, P4, W3, P3], occupancy=6)
        Space("bed2", outline=[(16450, 0), (20000, 0), (20000, 4500), (16450, 4500)], use="bedroom", level=L0, bounded_by=[W1, W2, P6, P4], occupancy=2)
        Space("bath2", outline=[(16450, 4650), (20000, 4650), (20000, 7500), (16450, 7500)], use="bathroom", level=L0, bounded_by=[P6, W2, W3, P4])
        Space("loggia", outline=[(4350, -3000), (16300, -3000), (16300, -500), (4350, -500)], use="loggia", level=L0, bounded_by=[W1])

        # ---- kitchen along the north wall, under the window
        KitchenRun("K1", on=W3, from_start=3700, length=3850, depth=650, counter_height=900, fronts=chestnut, counter=pietra, doors=5, pulls="iron", splash_height=0)

        # ---- services: pendants where people sit, downlights where they wash, sockets low on the walls
        Pendant("L1", at=(14800, 3300), drop=895, level=L0, watts=60)        # over the dining table
        Pendant("L2", at=(9400, 3750), drop=900, level=L0, watts=60)          # living
        Pendant("L3", at=(5350, 3750), drop=800, level=L0, watts=40)          # hall
        for i, (x, y) in enumerate([(2100, 6075), (18225, 6075), (2100, 2250), (18225, 2250)], 4):
            Downlight(f"L{i}", at=(x, y), level=L0, watts=8, material="white")
        Outlet("P1s", on=W1, from_start=600, height=300)
        Outlet("P2s", on=W1, from_start=8700, height=300)
        Outlet("P3s", on=W3, from_start=4100, height=1100, variant="double_counter")
        Outlet("P4s", on=W3, from_start=6800, height=1100, variant="double_counter")
        Outlet("P5s", on=W3, from_start=9000, height=300)
        Outlet("P6s", on=W2, from_start=3200, height=300)
        Outlet("P7s", on=W4, from_start=5900, height=300)

        # ---- rules of this house
        @house.check
        def loggia_headroom(ir):
            beam = ir.entity("LB")
            yield ("loggia_headroom", "LB", beam.derived["clear_below"] >= 2100, beam.derived["clear_below"], 2100, "under the loggia beam")

        @house.check
        def every_bedroom_has_a_bath(ir):
            baths = {s.id for s in ir.of_kind("space") if s.params["use"] == "bathroom"}
            for s in ir.of_kind("space"):
                if s.params["use"] != "bedroom":
                    continue
                from homespec.spatial import room_openings

                ways = [o for o, link in room_openings(ir, s.id) if (o.has("door") or o.has("passage")) and link.clear_width > 0]
                shared = sorted({b for o in ways for b in o.related("serves") if b in baths})
                yield ("bedroom_has_bath", s.id, bool(shared), ", ".join(shared) or "none", "an adjoining bathroom", "holiday-let brief")

    return house
