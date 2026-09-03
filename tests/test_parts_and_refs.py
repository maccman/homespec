"""Parts of an opening realize themselves; slab voids may name the entity they follow."""
import math
from typing import ClassVar

from homespec import Assembly, House, Layer, Level, OpeningPart, Pool, Slab, Stair, Wall, Window, element
from homespec import geometry as G
from homespec.model import Context, Realized


def _house():
    house = House("t")
    with house:
        Level("L0", height=3000)
        Level("L1", elevation=3300, height=2800)
        Assembly("stone", layers=[Layer(material="stone", thickness=450)])
    return house


def test_the_sugar_emits_parts_that_build_themselves():
    house = _house()
    with house:
        w = Wall("W", (0, 0), (8000, 0), assembly="stone", level="L0", tags={"external"})
        Window("N", host=w, width=1200, height=1500, sill=900, at=2000, shutters="paint", surround="cut_stone", grille="iron")
    b = house.compile()
    ids = list(b.entities)
    assert ids.index("N") < ids.index("N.surround") < ids.index("N.shutters") < ids.index("N.grille"), "the stone first, then what hangs on it"
    for part in ("N.shutters", "N.surround", "N.grille"):
        assert b[part].level == "L0" and b[part].has("external") and any(r.pred == "part_of" and r.obj == "N" for r in b[part].relations)
    assert G.bbox(b["N.shutters"].solid).max[1] <= -450 - 25 - 15 + 1e-6, "shutters hang clear of the surround, which stands 25 proud of the 450 wall"
    assert b["N.grille"].derived["bars"] >= 2


def test_a_project_can_add_its_own_part():
    @element
    class Pediment(OpeningPart):
        """A triangular cap over an opening: what a project adds without touching the core."""

        kind: ClassVar[str] = "pediment"
        rise: float = 300.0

        def realize(self, ctx: Context) -> Realized:
            geom, wall = self.geometry(ctx)
            z = wall.elevation + geom.sill + geom.height
            cap = G.frame_box(wall.body, geom.from_start - 100, -40, z, (geom.width + 200, 40, self.rise))
            return self.finish(ctx, geom, wall, cap, {"rise": self.rise})

    house = _house()
    with house:
        w = Wall("W", (0, 0), (8000, 0), assembly="stone", level="L0")
        Window("N", host=w, width=1200, height=1500, sill=900, at=2000)
        Pediment("N.cap", opening="N", material="cut_stone")
    b = house.compile()
    cap = b["N.cap"]
    assert list(b.entities).index("N") < list(b.entities).index("N.cap")
    bb = G.bbox(cap.solid)
    assert math.isclose(bb.min[2], 2400) and math.isclose(bb.max[2], 2700) and cap.level == "L0"
    assert cap.has("external") == b["W"].has("external"), "a part is external exactly when its wall is"


def test_a_part_on_an_upper_storey_takes_that_storey():
    house = _house()
    with house:
        w = Wall("T", (0, 0), (8000, 0), assembly="stone", level="L0", height=6000)
        Window("F", host=w, width=1000, height=1200, sill=4400, at=3000, shutters="paint")
    b = house.compile()
    assert b["F"].level == "L1" and b["F.shutters"].level == "L1"


def test_slab_voids_may_name_a_stair_or_a_pool():
    house = _house()
    with house:
        Stair("ST", (1000, 1000), (1, 0), width=1000, rise=3300, level="L0", to_level="L1")
        pool = Pool("P", outline=[(9000, 1000), (12000, 1000), (12000, 3000), (9000, 3000)], level="L0", depth=1400, material="tile")
        Slab("F1", outline=[(0, 0), (14000, 0), (14000, 6000), (0, 6000)], thickness=300, level="L1", voids=["ST", pool])
    b = house.compile()
    f1 = b["F1"]
    ids = list(b.entities)
    assert ids.index("ST") < ids.index("F1") and ids.index("P") < ids.index("F1")
    run = b["ST"].derived["run"]
    expected = 14000 * 6000 - run * 1000 - (3000 + 500) * (2000 + 500)    # the pool's hole is its shell, 250 outside the water each way
    assert math.isclose(G.volume(f1.solid), expected * 300, rel_tol=1e-6) and f1.derived["voids"] == 2
    assert G.polygon_area(b["P"].derived["cut_outline"]) == (3000 + 500) * (2000 + 500)
