"""Finish priority survives forward dependencies and typed IR serialization."""
from homespec import Assembly, Beam, House, Layer, Level, Material, RoomFinish, Space, Wall
from homespec.elements.finishes import RoomFinishGeometry
from homespec.ir import IRDocument


def test_later_finish_keeps_priority_when_earlier_finish_waits_for_beam(tmp_path):
    with House("forward finish dependency") as house:
        Level("L0", height=3000)
        for material in ("stone", "red", "blue"):
            Material(material)
        Assembly("wall", layers=[Layer(material="stone", thickness=200)], finish_in="stone")
        outline = [(0, 0), (4000, 0), (4000, 4000), (0, 4000)]
        walls = [Wall(f"W{i}", a, b, assembly="wall", level="L0")
                 for i, (a, b) in enumerate(zip(outline, outline[1:] + outline[:1], strict=True))]
        Space("room", outline=outline, bounded_by=walls, level="L0", use="living")
        RoomFinish("early", room="room", hosts=["W0", "beam"], material="red")
        RoomFinish("later", room="room", hosts=["W0"], material="blue")
        Beam("beam", (0, 100), (4000, 100), width=100, depth=100, underside=2500, level="L0", material="stone")
    build = house.compile()
    assert [b.id for b in build if b.element.kind == "room_finish"] == ["later", "early"]
    early = RoomFinishGeometry.model_validate(build["early"].derived)
    later = RoomFinishGeometry.model_validate(build["later"].derived)
    assert early.declaration_order < later.declaration_order
    assert later.declaration_order == list(house.elements).index("later")
    build.write(str(tmp_path))
    ir = IRDocument.read(str(tmp_path))
    assert ir.entity("early").derived_as(RoomFinishGeometry).declaration_order == early.declaration_order
    assert ir.entity("later").derived_as(RoomFinishGeometry).declaration_order == later.declaration_order
