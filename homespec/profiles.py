"""Typed opening outlines, independent of the CAD and rendering consumers."""
from __future__ import annotations

import math
from typing import Literal, Self

from pydantic import Field, model_validator

from .validation import FiniteModel


class OpeningProfile(FiniteModel):
    """An opening's outer outline; ``height`` is the overall height.

    A segmental head uses its explicit rise. A semicircular head rises by
    half the width. A circular opening requires equal width and height.
    Insets retain the same circle centre and reduce its radius, so glass,
    frame and stone can share a true concentric boundary.
    """

    shape: Literal["rectangular", "semicircular", "segmental", "circular"] = "rectangular"
    rise: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _rise(self) -> Self:
        if (self.shape == "segmental") != (self.rise is not None):
            raise ValueError("rise is required only for a segmental profile")
        return self

    def validate_dimensions(self, width: float, height: float) -> None:
        if not all(math.isfinite(v) and v > 0 for v in (width, height)):
            raise ValueError("profile width and height must be positive and finite")
        if self.shape == "circular" and not math.isclose(width, height, abs_tol=1e-7):
            raise ValueError("a circular opening requires equal width and height")
        if self.shape == "segmental" and self.head_rise(width) > width / 2:
            raise ValueError("a segmental rise cannot exceed half the width; use a semicircle")
        if self.shape in ("semicircular", "segmental") and height < self.head_rise(width):
            raise ValueError("profile height must contain its curved head")

    def head_rise(self, width: float) -> float:
        if self.shape == "segmental":
            assert self.rise is not None
            return self.rise
        return width / 2 if self.shape in ("semicircular", "circular") else 0.0

    def circle(self, width: float, height: float) -> tuple[float, float]:
        """Radius and centre elevation relative to the bottom of the opening."""
        rise = self.head_rise(width)
        if not rise:
            raise ValueError("a rectangular profile has no circle")
        radius = ((width / 2) ** 2 + rise**2) / (2 * rise)
        return radius, height - radius


class DoorComposition(FiniteModel):
    """Central clear passage with fixed sidelights and an optional transom.

    Width and height describe the unobstructed central passage, measured
    inside its posts and under its transom. Both leaves are operable; there
    is no permanent central mullion. ``Door.glazed`` controls central leaves,
    while sidelights and the transom are always fixed glass.
    """

    passage_width: float = Field(gt=0)
    passage_height: float = Field(gt=0)
    leaves: Literal[1, 2] = 2
