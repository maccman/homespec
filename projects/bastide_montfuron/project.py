"""Bastide de Montfuron: a Provençal stone bastide on a hillside above the Luberon.

Three blocks of pale limestone rubble under low canal-tile roofs with génoise
cornices: a three-storey tower holding the entrance hall and stairs, a
two-storey main wing with an arched glazed door onto the terrace, and a low
kitchen wing. Small-paned windows in dressed-stone surrounds with grey-blue
shutters; a brush-shaded iron pergola along the terrace; stone steps down a
retaining wall to a pool with a travertine edge. Why each choice was made is
in decisions.md.
"""
from homespec import *  # noqa: F403


def build() -> House:
    with House("bastide-montfuron") as house:
        # ---- site: a south-facing hillside, pool terrace two metres below the house terrace
        Site(parcel=[(-40000, -60000), (70000, -60000), (70000, 40000), (-40000, 40000)],
             setbacks=Setbacks(front=10000, side=8000, rear=8000), north=10)
        L0 = Level("L0", elevation=0, height=3200)
        L1 = Level("L1", elevation=3500, height=2900)
        L2 = Level("L2", elevation=6700, height=2600)
        LP = Level("LP", elevation=-2000, height=2200)      # the pool terrace and garden below the retaining wall

        # ---- materials: two addresses each, rendering and buying
        stone = Material("limestone_rubble", texture="polyhaven/coral_stone_wall", product="Local limestone rubble, lime mortar, pointed flush", supplier="Carrières de Provence",
                         finish="brushed, lime wash to soften", render=Render(tile=2.8, value=1.0, tint=(0.97, 0.94, 0.88)))
        cut = Material("cut_stone", texture="polyhaven/beige_wall_001", product="Sawn limestone (pierre de Rognes) 140 mm surrounds, coping and steps", supplier="Carrières de Provence",
                       finish="honed", render=Render(tile=1.0, value=0.95, tint=(0.96, 0.9, 0.78)))
        lime = Material("lime_white", texture="polyhaven/white_stucco", product="Lime plaster, three coats", supplier="TBD", finish="limewash, warm white",
                        render=Render(tile=1.6, value=1.3, tint=(0.99, 0.97, 0.93)))
        tiles = Material("canal_tiles", texture="polyhaven/clay_roof_tiles", product="Reclaimed terracotta canal tiles, mixed batch", supplier="salvage yard, Apt",
                         render=Render(tile=1.1, value=0.85, tint=(0.9, 0.82, 0.74)))
        floor = Material("burgundy_stone", texture="polyhaven/stone_tiles_02", product="Pierre de Bourgogne flagstones 600 x 400, tumbled", supplier="TBD",
                         finish="honed, sealed", render=Render(tile=1.4, value=1.2, tint=(1.0, 0.96, 0.88)))
        beams = Material("oak_beams", texture="polyhaven/oak_wood_planks", product="Reclaimed oak beams, limewashed", supplier="salvage",
                         render=Render(tile=1.6, value=1.15, tint=(1.0, 0.95, 0.88)))
        shutter = Material("shutter_grey", product="Solid pine plank shutters, painted", supplier="local joiner",
                           finish="Farrow and Ball Light Blue, matt", render=Render(color=(0.62, 0.68, 0.72), rough=0.75))
        frame = Material("frame_white", product="Oak windows, painted off-white", supplier="local joiner", render=Render(color=(0.9, 0.88, 0.82), rough=0.5))
        steel = Material("steel_black", product="Thermally broken steel screens, black", supplier="TBD", render=Render(color=(0.05, 0.05, 0.05), rough=0.45, metal=0.7))
        iron = Material("iron", product="Wrought iron posts and railings, wax finish", supplier="local smith", render=Render(color=(0.07, 0.07, 0.07), rough=0.5, metal=0.7))
        Material("glass_double", product="Slim double glazing 4/12/4", render=Render(color=(0.95, 0.98, 1.0), rough=0.02, transmission=1.0))
        Material("door_grey", product="Oak plank doors, painted", render=Render(color=(0.66, 0.68, 0.66), rough=0.7))
        brande = Material("brande", texture="polyhaven/gravel", product="Heather brush (brande) on galvanised mesh", supplier="TBD", render=Render(tile=0.6, value=0.55, tint=(0.55, 0.42, 0.28)))
        Material("travertine", texture="polyhaven/beige_wall_001", product="Travertine coping and pool deck 600 x 400, tumbled", supplier="TBD",
                 render=Render(tile=1.2, value=1.25, tint=(1.0, 0.97, 0.9)))
        Material("pool_tile", product="Pool render, pale grey-green", render=Render(color=(0.55, 0.72, 0.72), rough=0.5))
        Material("pool_water", product="Water", render=Render(color=(0.35, 0.68, 0.78), rough=0.03, transmission=0.9))
        Material("gravel", texture="polyhaven/gravel", product="Crushed limestone gravel 6-14 mm", supplier="local quarry", render=Render(tile=2.5, value=1.4, tint=(1.0, 0.98, 0.92)))
        Material("marble_counter", texture="polyhaven/marble_01", product="Carrara marble 30 mm", supplier="TBD", render=Render(tile=1.0, value=1.1))
        Material("brass", product="Aged brass", render=Render(color=(0.7, 0.55, 0.3), rough=0.4, metal=1.0))
        Material("white", product="White ceramic", render=Render(color=(0.92, 0.92, 0.9), rough=0.4))

        rubble = Assembly("rubble_wall", layers=[Layer(material="limestone_rubble", thickness=500), Layer(material="lime_plaster", thickness=50)], finish_in=lime, finish_out=stone)
        partition = Assembly("partition", layers=[Layer(material="lime_plaster", thickness=15), Layer(material="brick_block", thickness=120), Layer(material="lime_plaster", thickness=15)], finish_in=lime)
        breast = Assembly("chimney_breast", layers=[Layer(material="limestone_rubble", thickness=600)], finish_in=cut)
        garden = Assembly("garden_wall", layers=[Layer(material="limestone_rubble", thickness=500)], finish_in=stone, finish_out=stone)

        # ---- the tower: 6.5 x 6.5 inside, three storeys, walls to the top of L2
        TS = Wall("TS", (500, 500), (7000, 500), assembly=rubble, level=L0, height=9300)
        TE = Wall("TE", (7000, 500), (7000, 7000), assembly=rubble, level=L0, height=9300)
        TN = Wall("TN", (7000, 7000), (500, 7000), assembly=rubble, level=L0, height=9300)
        TW = Wall("TW", (500, 7000), (500, 500), assembly=rubble, level=L0, height=9300)

        # ---- the main wing: 13.5 x 7 inside, two storeys, its west wall is the tower's east wall
        MS = Wall("MS", (7500, 500), (21000, 500), assembly=rubble, level=L0, height=6400)
        ME = Wall("ME", (21000, 500), (21000, 7500), assembly=rubble, level=L0, height=6400)
        MN = Wall("MN", (21000, 7500), (7500, 7500), assembly=rubble, level=L0, height=6400)

        # ---- the kitchen wing: 8.5 x 5 inside, one storey, its west wall is the main wing's east wall
        KS = Wall("KS", (21500, 1500), (30000, 1500), assembly=rubble, level=L0)
        KE = Wall("KE", (30000, 1500), (30000, 6500), assembly=rubble, level=L0)
        KN = Wall("KN", (30000, 6500), (21500, 6500), assembly=rubble, level=L0)

        # ---- the south facade: the arched door with a window each side, three windows above; the tower's glazed screen
        ArchedDoor("D1", host=MS, width=1900, height=2300, at=5800, panes=(1, 5), frame=frame, surround=cut, shutters=shutter, leaves=2)
        Window("N1", host=MS, width=1200, height=1600, sill=800, at=1500, panes=(2, 3), frame=frame, surround=cut, shutters=shutter)
        Window("N2", host=MS, width=1200, height=1600, sill=800, at=10800, panes=(2, 3), frame=frame, surround=cut, shutters=shutter)
        for k, x in enumerate((1500, 6150, 10800), 3):
            Window(f"N{k}", host=MS, width=1200, height=1400, sill=4400, at=x, panes=(2, 3), frame=frame, surround=cut, shutters=shutter)
        Door("D2", host=TS, width=3000, height=2600, at=1750, glazed=True, leaves=2, panes=(3, 5), frame=steel, frame_size=50, bar_size=25)   # the hall's steel screen under the pergola
        Window("N6", host=TS, width=1000, height=1300, sill=4400, at=2750, panes=(2, 3), frame=frame, surround=cut, shutters=shutter)
        Window("N7", host=TS, width=800, height=1000, sill=7500, at=2850, panes=(2, 2), frame=frame, surround=cut, grille=iron)
        # tower west and north
        Window("N8", host=TW, width=1000, height=1400, sill=900, at=2500, panes=(2, 3), frame=frame, surround=cut, shutters=shutter)
        Window("N9", host=TW, width=1000, height=1300, sill=4400, at=2750, panes=(2, 3), frame=frame, surround=cut, shutters=shutter)
        Window("N10", host=TW, width=800, height=1000, sill=7500, at=2850, panes=(2, 2), frame=frame, surround=cut, grille=iron)
        Window("N11", host=TN, width=1000, height=1300, sill=4400, at=2750, panes=(2, 3), frame=frame, surround=cut, shutters=shutter)
        Window("N12", host=TN, width=800, height=1000, sill=7500, at=2850, panes=(2, 2), frame=frame, surround=cut, grille=iron)
        # main wing north: the front door, windows below and above
        Door("D0", host=MN, width=1200, height=2400, at=6150, frame=frame, leaf="door_grey", surround=cut)
        Window("N13", host=MN, width=1200, height=1600, sill=800, at=2000, panes=(2, 3), frame=frame, surround=cut, shutters=shutter)
        Window("N14", host=MN, width=1200, height=1600, sill=800, at=10300, panes=(2, 3), frame=frame, surround=cut, shutters=shutter)
        Window("N15", host=MN, width=800, height=1000, sill=4700, at=3275, panes=(2, 2), frame=frame, surround=cut)      # bath 2
        Window("N16", host=MN, width=1000, height=1300, sill=4400, at=6250, panes=(2, 3), frame=frame, surround=cut, shutters=shutter)   # corridor
        Window("N17", host=MN, width=800, height=1000, sill=4700, at=9500, panes=(2, 2), frame=frame, surround=cut)      # bath 1
        Window("N18", host=ME, width=1000, height=1300, sill=4400, at=3000, panes=(2, 3), frame=frame, surround=cut, shutters=shutter)   # bedroom 3, east
        # kitchen wing: two glazed doors south, a window east and north
        Door("D3", host=KS, width=1850, height=2400, at=1200, glazed=True, leaves=2, panes=(2, 5), frame=frame, surround=cut, shutters=shutter)
        Door("D4", host=KS, width=1850, height=2400, at=5300, glazed=True, leaves=2, panes=(2, 5), frame=frame, surround=cut, shutters=shutter)
        Window("N19", host=KE, width=1000, height=1400, sill=900, at=2000, panes=(2, 3), frame=frame, surround=cut, shutters=shutter)
        Window("N20", host=KN, width=1200, height=1400, sill=1000, at=3650, panes=(2, 3), frame=frame, surround=cut, shutters=shutter)

        # ---- inside, ground floor: hall to living through an arch, living to dining through an arch, dining to kitchen through a door
        Arch("A0", host=TE, width=1600, height=2200, at=2450)
        P1 = Wall("P1", (14575, 500), (14575, 7500), assembly=partition, level=L0, align="center", external=False)
        Arch("A1", host=P1, width=2000, height=2100, at=2500)
        Door("D5", host=ME, width=1000, height=2200, at=2000, frame=frame, leaf="door_grey")
        FP = Wall("FP", (9500, 7500), (11500, 7500), assembly=breast, level=L0, align="right", external=False)
        Arch("FP.hearth", host=FP, width=1200, height=800, at=400)
        Chimney("CH", at=(10500, 7250), size=800, base=6400, height=1700, level=L1, material=stone)

        # ---- stairs in the tower: a flight along the north wall to L1, a flight along the south wall to L2
        Stair("ST1", (1000, 6000), (1, 0), width=1000, rise=3500, going=270, level=L0, to_level=L1, material=cut)
        Stair("ST2", (6000, 1500), (-1, 0), width=1000, rise=3200, going=270, level=L1, to_level=L2, material=cut)

        # ---- inside, first floor: a corridor along the north, three bedrooms south, two bathrooms between them
        PC = Wall("PC", (7500, 6125), (21000, 6125), assembly=partition, level=L1, align="center", external=False)
        PB1 = Wall("PB1", (10275, 500), (10275, 6050), assembly=partition, level=L1, align="center", external=False)
        PB2 = Wall("PB2", (11925, 500), (11925, 6050), assembly=partition, level=L1, align="center", external=False)
        PB3 = Wall("PB3", (16500, 500), (16500, 6050), assembly=partition, level=L1, align="center", external=False)
        PB4 = Wall("PB4", (18150, 500), (18150, 6050), assembly=partition, level=L1, align="center", external=False)
        Door("D6", host=PC, width=950, height=2100, at=1200, frame=frame, leaf="door_grey")      # corridor -> bedroom 1
        Door("D7", host=PC, width=950, height=2100, at=6000, frame=frame, leaf="door_grey")      # corridor -> bedroom 2
        Door("D8", host=PC, width=950, height=2100, at=11525, frame=frame, leaf="door_grey")     # corridor -> bedroom 3
        Door("D9", host=PB1, width=800, height=2100, at=4000, frame=frame, leaf="door_grey")     # bedroom 1 -> bath 1
        Door("D10", host=PB3, width=800, height=2100, at=4000, frame=frame, leaf="door_grey")    # bedroom 2 -> bath 2
        Arch("A2", host=TE, width=1400, height=2100, at=2550, sill=3500)                          # tower landing -> corridor, through the tower wall on L1

        # ---- floors and ceilings
        Slab("F0", outline=[(0, 0), (30500, 0), (30500, 7500), (21500, 7500), (21500, 8000), (7500, 8000), (7500, 7500), (0, 7500)], thickness=250, level=L0, material=floor)
        Slab("F1", outline=[(0, 0), (21500, 0), (21500, 8000), (7500, 8000), (7500, 7500), (0, 7500)], thickness=300, level=L1, material=floor,
             voids=[[(1000, 5900), (6300, 5900), (6300, 7000), (1000, 7000)]])
        Slab("F2", outline=[(0, 0), (7500, 0), (7500, 7500), (0, 7500)], thickness=300, level=L2, material=floor, voids=[[(900, 1400), (6100, 1400), (6100, 2600), (900, 2600)]])
        Ceiling("C0M", outline=[(7500, 500), (21000, 500), (21000, 7500), (7500, 7500)], level=L0, material=lime, thickness=30,
                beams=BeamGrid(width=140, depth=220, spacing=600, along="y", material=beams))
        Ceiling("C0T", outline=[(500, 500), (7000, 500), (7000, 7000), (500, 7000)], level=L0, material=lime, thickness=30,
                beams=BeamGrid(width=140, depth=220, spacing=600, along="x", material=beams))
        Ceiling("C0K", outline=[(21500, 1500), (30000, 1500), (30000, 6500), (21500, 6500)], level=L0, material=lime, thickness=30,
                beams=BeamGrid(width=120, depth=200, spacing=600, along="y", material=beams))
        Ceiling("C1M", outline=[(7500, 500), (21000, 500), (21000, 7500), (7500, 7500)], level=L1, material=lime, thickness=30,
                beams=BeamGrid(width=120, depth=180, spacing=600, along="y", material=beams))
        Ceiling("C1T", outline=[(500, 500), (7000, 500), (7000, 7000), (500, 7000)], level=L1, material=lime, thickness=30)
        Ceiling("C2T", outline=[(500, 500), (7000, 500), (7000, 7000), (500, 7000)], level=L2, material=lime, thickness=30,
                beams=BeamGrid(width=120, depth=180, spacing=600, along="x", material=beams))

        # ---- roofs: hipped tower, gabled main wing, hipped kitchen, all with génoise; the brush pergola along the terrace
        Roof("RT", outline=[(0, 0), (7500, 0), (7500, 7500), (0, 7500)], level=L2, material=tiles, kind_="hip", pitch=28, overhang=450, thickness=220, genoise=2)
        Roof("RM", outline=[(7500, 0), (21500, 0), (21500, 8000), (7500, 8000)], level=L1, material=tiles, kind_="gable", ridge_along="x", pitch=24, overhang=450,
             thickness=220, genoise=3, gable_thickness=550, gable_material=stone)
        Roof("RK", outline=[(21500, 1000), (30500, 1000), (30500, 7000), (21500, 7000)], level=L0, material=tiles, kind_="hip", pitch=22, overhang=450, thickness=220, genoise=2)
        Roof("RP", outline=[(-500, -3500), (14500, -3500), (14500, -100), (-500, -100)], level=L0, material=brande, kind_="flat", eave=2950, thickness=70, overhang=100)
        for k, x in enumerate(range(0, 14001, 3500), 1):
            Column(f"PP{k}", at=(x, -3300), radius=40, height=2880, level=L0, material=iron)
        Beam("PB", (-500, -3300), (14500, -3300), width=80, depth=80, underside=2800, level=L0, material=iron)

        # ---- terraces: the house terrace, the retaining wall, grand steps, the pool and its deck below
        Slab("TR", outline=[(-3000, -5000), (33000, -5000), (33000, 0), (-3000, 0)], thickness=150, level=L0, material=cut)
        Wall("RW1", (13300, -5000), (-3000, -5000), assembly=garden, level=LP, height=2300, align="right")     # retaining walls either side of the steps
        Wall("RW2", (33000, -5000), (15700, -5000), assembly=garden, level=LP, height=2300, align="right")
        Stair("ST0", (15700, -8600), (0, 1), width=2400, rise=2000, going=300, max_riser=170, level=LP, to_level=L0, material=cut)
        Slab("GD", outline=[(-6000, -22000), (36000, -22000), (36000, -5500), (-6000, -5500)], thickness=200, level=LP, material="gravel")
        Slab("PD", outline=[(3500, -18000), (23500, -18000), (23500, -8000), (3500, -8000)], thickness=100, level=LP, material="travertine", top=20)
        Pool("PL", outline=[(6500, -16500), (20500, -16500), (20500, -10000), (6500, -10000)], level=LP, depth=1500, coping=500, material="pool_tile",
             coping_material="travertine", water_material="pool_water", top=20)

        # ---- rooms
        Space("hall", outline=[(500, 500), (7000, 500), (7000, 7000), (500, 7000)], use="hall", level=L0, bounded_by=[TS, TE, TN, TW])
        Space("living", outline=[(7500, 500), (14500, 500), (14500, 7500), (7500, 7500)], use="living", level=L0, bounded_by=[MS, P1, MN, TE], occupancy=8)
        Space("dining", outline=[(14650, 500), (21000, 500), (21000, 7500), (14650, 7500)], use="dining", level=L0, bounded_by=[MS, ME, MN, P1], occupancy=10)
        Space("kitchen", outline=[(21500, 1500), (30000, 1500), (30000, 6500), (21500, 6500)], use="kitchen", level=L0, bounded_by=[KS, KE, KN, ME], occupancy=6)
        Space("landing", outline=[(500, 500), (7000, 500), (7000, 7000), (500, 7000)], use="landing", level=L1, bounded_by=[TS, TE, TN, TW])
        Space("corridor", outline=[(7500, 6200), (21000, 6200), (21000, 7500), (7500, 7500)], use="corridor", level=L1, bounded_by=[PC, ME, MN, TE])
        Space("bed1", outline=[(7500, 500), (10200, 500), (10200, 6050), (7500, 6050)], use="bedroom", level=L1, bounded_by=[MS, PB1, PC, TE], occupancy=2)
        Space("bath1", outline=[(10350, 500), (11850, 500), (11850, 6050), (10350, 6050)], use="bathroom", level=L1, bounded_by=[MS, PB2, PC, PB1])
        Space("bed2", outline=[(12000, 500), (16425, 500), (16425, 6050), (12000, 6050)], use="bedroom", level=L1, bounded_by=[MS, PB3, PC, PB2], occupancy=2)
        Space("bath2", outline=[(16575, 500), (18075, 500), (18075, 6050), (16575, 6050)], use="bathroom", level=L1, bounded_by=[MS, PB4, PC, PB3])
        Space("bed3", outline=[(18225, 500), (21000, 500), (21000, 6050), (18225, 6050)], use="bedroom", level=L1, bounded_by=[MS, ME, PC, PB4], occupancy=2)
        Space("study", outline=[(500, 500), (7000, 500), (7000, 7000), (500, 7000)], use="study", level=L2, bounded_by=[TS, TE, TN, TW])
        Space("terrace", outline=[(-3000, -5000), (33000, -5000), (33000, 0), (-3000, 0)], use="terrace", level=L0, bounded_by=[MS, TS, KS])

        # ---- kitchen along the north wall, under the window
        KitchenRun("K1", on=KN, from_start=1000, length=6500, depth=650, counter_height=900, fronts="door_grey", counter="marble_counter", doors=7, pulls="brass", splash_height=0)

        # ---- services: chandeliers where people gather, lanterns on the terrace posts, downlights in the bathrooms
        Pendant("L1", at=(11000, 4000), drop=1100, level=L0, watts=200)
        Pendant("L2", at=(17800, 4000), drop=1200, level=L0, watts=150)
        Pendant("L3", at=(3750, 3750), drop=900, level=L0, watts=100)
        Pendant("L4", at=(25750, 4000), drop=1100, level=L0, watts=80)
        Pendant("L5", at=(3750, 3750), drop=800, level=L1, watts=60)
        for i, (x, y, lv) in enumerate([(11100, 3000, L1), (17325, 3000, L1), (11100, 5000, L1), (17325, 5000, L1)], 6):
            Downlight(f"L{i}", at=(x, y), level=lv, watts=8, material="white")
        for i, sp in enumerate((MS, MS, MN, TS, KS, KN), 1):
            Outlet(f"S{i}", on=sp, from_start=600 + i * 900, height=300)

        # ---- rules of this house
        @house.check
        def every_bedroom_has_a_window(ir):
            for s in ir.of_kind("space"):
                if s.params["use"] != "bedroom":
                    continue
                walls = set(s.related("bounded_by"))
                z0 = ir.levels[s.level].elevation
                glass = sum(o.derived["glass_area_mm2"] for o in ir.tagged("window")
                            if o.derived["host"] in walls and o.geometry and z0 <= o.geometry.bbox.min[2] < z0 + ir.levels[s.level].height)
                yield ("bedroom_window", s.id, glass > 0.8e6, round(glass / 1e6, 2), 0.8, "m² of glass on the bedroom's own walls", "holiday-let brief")

        @house.check
        def stairs_reach_their_floor(ir):
            for st in ir.of_kind("stair"):
                to = st.params.get("to_level")
                if not to:
                    continue
                expected = ir.levels[to].elevation - ir.levels[st.level].elevation
                yield ("stair_reaches_floor", st.id, abs(st.params["rise"] - expected) < 1, st.params["rise"], expected, f"{st.level} -> {to}")

    return house
