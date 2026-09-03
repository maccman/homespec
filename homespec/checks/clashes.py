"""Solids do not interpenetrate, except where construction requires it.

The compiler records every pair of physical entities that share volume
(:mod:`homespec.clashes`). This rule reads that list from the IR and
decides which overlaps are how a house is built and which are mistakes.
A beam bears into a wall; glass sits in the rebate of its frame; a wall
head is dressed to the slope of the roof it meets; a chimney passes
through the fabric. Everything else is two things in one place, which
a builder cannot do and a quantity survey should not count twice.

Every clash gets a row, allowed or not, so the report says what was
waved through and why. A project extends the policy with
:meth:`homespec.model.House.allow`, which needs a reason.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..clashes import Clash
from ..ir import IRDocument, IREntity
from .base import Result, rule

SKIM = 1.0
"""Millimetres. Thinner than this is how exact solids meet, not an overlap."""

WEDGE = 60.0
"""Millimetres a wall head may run into a roof plane: the sliver a slope leaves before the wall is dressed to it."""

BEARERS = {"beam", "slab", "landing", "ceiling"}
"""Kinds that bear into a wall or gable: pocketed, built in, run to the outside face."""

SUPPORTS = {"wall", "gable"}

FABRIC = {"roof", "ceiling", "beam", "wall", "gable", "slab"}
"""What a chimney passes through."""


def allowance(ir: IRDocument, clash: Clash) -> tuple[str, str] | None:
    """Why a clash is how a house is built, as ``(limit, note)``, or None when it is a mistake."""
    a, b = ir.entity(clash.a), ir.entity(clash.b)
    if clash.depth_mm <= SKIM:
        return f"<= {SKIM:g} mm", "a skim, not an overlap"
    note = _allowed_by_project(a, b)
    if note is not None:
        return "any", f"allowed by the project: {note}"
    for x, y in ((a, b), (b, a)):
        if x.kind == "glazing" and y.id in x.related("part_of"):
            return "any", "glass sits in the rebate of its frame"
        opening = _opening_of(ir, x)
        if opening is not None and y.id in opening.related("hosted_in"):
            return "any", f"a part of {opening.id} bedded in its wall"
        if x.kind in BEARERS and y.kind in SUPPORTS:
            return "any", f"{x.kind} bears into {y.kind}"
        if x.kind == "chimney" and y.kind in FABRIC:
            return "any", "a chimney passes through the fabric"
        if x.has("service") and y.ifc_class == "IfcCovering":
            return "any", f"{x.kind} recessed in a lining"
        if x.kind in SUPPORTS | {"column"} and y.kind == "roof" and clash.depth_mm <= WEDGE and _is_head(x, clash):
            return f"<= {WEDGE:g} mm", f"{x.kind} head dressed to the roof slope"
    return None


def _is_head(wall: IREntity, clash: Clash) -> bool:
    """Whether the overlap reaches the top of the wall: a head in a slope, not a roof running into the wall lower down."""
    return wall.geometry is not None and clash.bbox.max[2] >= wall.geometry.bbox.max[2] - SKIM


def _allowed_by_project(a: IREntity, b: IREntity) -> str | None:
    for x, y in ((a, b), (b, a)):
        for r in x.relations:
            if r.pred == "may_overlap" and r.obj == y.id:
                return r.note
    return None


def _opening_of(ir: IRDocument, e: IREntity) -> IREntity | None:
    """The opening ``e`` is a part of, if it is one: a surround, shutters, a grille, glass, a leaf."""
    for whole in e.related("part_of"):
        parent = ir.entity(whole)
        if parent.has("opening"):
            return parent
    return None


def describe(clash: Clash) -> str:
    litres = clash.volume_mm3 / 1e6
    amount = f"{litres:.1f} L" if litres >= 1 else f"{clash.volume_mm3 / 1e3:.0f} cm³"
    return f"{clash.depth_mm:.0f} mm deep, {amount}"


@rule("no_clash", clause="solids share no volume except where construction requires it")
def no_clash(ir: IRDocument) -> Iterable[Result]:
    if not ir.clashes:
        yield Result(rule="", target="building", ok=True, value="0 pairs share volume", limit="0 mm")
        return
    for c in ir.clashes:
        found = allowance(ir, c)
        kinds = f"{ir.entity(c.a).kind} into {ir.entity(c.b).kind}"
        if found is None:
            yield Result(rule="", target=c.pair, ok=False, value=describe(c), limit="0 mm", note=kinds)
        else:
            limit, note = found
            yield Result(rule="", target=c.pair, ok=True, value=describe(c), limit=limit, note=note)
