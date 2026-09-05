"""Exact solids made from the same profile for hole, lining and glazing."""
from __future__ import annotations

from typing import Any

from .. import geometry as G
from ..geometry import Frame
from ..profiles import OpeningProfile


def profile_solid(profile: OpeningProfile, width: float, height: float, frame: Frame,
                  x: float, z: float, depth: float, thickness: float,
                  *, inset: float = 0, bottom: float | None = None) -> Any:
    """Extrude a profile along a wall normal; inset is a physical offset.

    ``bottom`` overrides the usual bottom inset, allowing floor-level door
    frames and surrounds to omit a threshold. The curved upper boundary is
    analytic CAD geometry, never a polygonal approximation.
    """
    profile.validate_dimensions(width, height)
    low = inset if bottom is None else bottom
    if width <= 2 * inset or height - inset <= low or thickness <= 0:
        raise ValueError("profile inset leaves no interior")
    if profile.shape == "rectangular":
        return G.frame_box(frame, x + inset, depth, z + low, (width - 2 * inset, thickness, height - inset - low))
    radius, centre_z = profile.circle(width, height)
    if radius <= inset:
        raise ValueError("profile inset consumes the curved radius")
    centre = frame.point(x + width / 2, depth + thickness / 2)
    disc = G.horizontal_cylinder(radius - inset, thickness, (*centre, z + centre_z), frame.angle + 90)
    if profile.shape == "circular":
        return disc
    if centre_z > low:
        base = G.frame_box(frame, x + inset, depth, z + low, (width - 2 * inset, thickness, centre_z - low))
        disc = disc + base
    clip = G.frame_box(frame, x + inset, depth - 1, z + low, (width - 2 * inset, thickness + 2, height - inset - low))
    return disc & clip
