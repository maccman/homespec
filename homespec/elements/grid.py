"""Named grid lines. Walls and joinery are positioned from these, never from raw numbers twice."""
from __future__ import annotations

from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, Field

from ..geometry import Point
from ..model import Definition, definition, positional


class GridLine(BaseModel):
    """One line of the grid. ``A & one`` is the point where an x line meets a y line."""

    axis: Literal["x", "y"]
    name: str
    at: float

    def __and__(self, other: GridLine) -> Point:
        if self.axis == other.axis:
            raise ValueError(f"grid lines {self.name} and {other.name} are parallel")
        x, y = (self, other) if self.axis == "x" else (other, self)
        return (x.at, y.at)


@definition
class Grid(Definition):
    """The setting-out grid: x lines are usually letters, y lines numbers.

    ::

        g = Grid(x={"A": 0, "B": 8000}, y={"1": 0, "2": 5000})
        A, B, one, two = g.lines("A", "B", "1", "2")
        Wall("W1", A & one, B & one, ...)
    """

    registry: ClassVar[str] = "grid"
    singleton: ClassVar[bool] = True
    id: str = positional(default="grid")
    x: Annotated[dict[str, float], Field(min_length=1)]
    y: Annotated[dict[str, float], Field(min_length=1)]

    def line(self, name: str) -> GridLine:
        if name in self.x:
            return GridLine(axis="x", name=name, at=self.x[name])
        if name in self.y:
            return GridLine(axis="y", name=name, at=self.y[name])
        raise KeyError(f"no grid line {name!r}")

    def lines(self, *names: str) -> tuple[GridLine, ...]:
        return tuple(self.line(n) for n in names)

    def point(self, x: str, y: str) -> Point:
        return self.line(x) & self.line(y)
