"""Definitions: what a house is described in terms of."""
from __future__ import annotations

from typing import Annotated, ClassVar

from pydantic import Field

from ..geometry import Point, polygon_area
from ..model import Definition, NonNegative, Outline, Positive, Ref, definition, positional
from ..validation import FiniteModel


@definition
class Level(Definition):
    """A storey. ``elevation`` is the finished floor; ``height`` is floor to ceiling lining."""

    registry: ClassVar[str] = "levels"
    elevation: float = 0.0
    height: Positive = 2700.0


class Layer(FiniteModel):
    """One layer of a build-up, outside to inside."""

    material: str
    thickness: Positive


@definition
class Assembly(Definition):
    """A wall or floor build-up. Thickness is the sum of its layers; there is no second number to disagree with."""

    registry: ClassVar[str] = "assemblies"
    layers: Annotated[list[Layer], Field(min_length=1)]
    finish_in: Ref | None = None
    finish_out: Ref | None = None

    @property
    def thickness(self) -> float:
        return sum(layer.thickness for layer in self.layers)


class Render(FiniteModel):
    """How a material looks in the walkthrough. Ignored by every other export."""

    tile: float = 1.0
    tint: tuple[float, float, float] = (1.0, 1.0, 1.0)
    value: float = 1.0
    wash: float = 0.0
    rough_mul: float = 1.0
    color: tuple[float, float, float] | None = None
    rough: float = 0.5
    metal: float = 0.0
    emit: float = 0.0
    transmission: float = 0.0
    absorb: float = 0.0
    bump: float = 0.0


@definition
class Material(Definition):
    """A material has two addresses: ``texture`` for rendering, ``product``/``supplier`` for buying."""

    registry: ClassVar[str] = "materials"
    texture: Annotated[str | None, Field(description="Texture set id, e.g. 'polyhaven/oak_veneer_01'.")] = None
    product: str | None = None
    supplier: str | None = None
    finish: str | None = None
    notes: str | None = None
    render: Render = Field(default_factory=Render)


@definition
class Site(Definition):
    """The parcel the house stands on. Plan north is ``north`` degrees clockwise from +y."""

    registry: ClassVar[str] = "site"
    singleton: ClassVar[bool] = True
    id: str = positional(default="site")
    parcel: Outline
    setbacks: NonNegative | list[NonNegative] = 0.0
    north: float = 0.0

    def __post_init__(self) -> None:
        if isinstance(self.setbacks, list) and len(self.setbacks) != len(self.parcel):
            raise ValueError(f"{self.id}: supply one setback per parcel edge ({len(self.parcel)})")
        super().__post_init__()

    @property
    def area_mm2(self) -> float:
        return polygon_area(self.parcel)


__all__ = ["Level", "Layer", "Assembly", "Render", "Material", "Site", "Point"]
