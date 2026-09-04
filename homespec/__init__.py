"""homespec: a house as source code.

::

    from homespec import *

    def build() -> House:
        with House("cabin") as house:
            L0 = Level("L0", height=2700)
            ...
        return house

The public API is the :class:`House`, the vocabulary in :mod:`homespec.elements`,
the unit helpers, and :func:`homespec.pipeline.build_project`.
"""
from .elements import (
    Arch,
    ArchedDoor,
    ArchVoid,
    Assembly,
    Beam,
    BeamGrid,
    Bookcase,
    Ceiling,
    Chimney,
    Clerestory,
    Column,
    Coping,
    Cornice,
    Covering,
    Door,
    Downlight,
    FromEnd,
    Gable,
    Glazing,
    Grid,
    GridLine,
    Grille,
    KitchenRun,
    Landing,
    Layer,
    Leaf,
    Level,
    Material,
    Opening,
    OpeningGeometry,
    OpeningPart,
    Outlet,
    Part,
    Pendant,
    Pool,
    PoolWater,
    Render,
    Roof,
    Shutters,
    Site,
    Slab,
    SlidingDoor,
    Space,
    Stair,
    Surround,
    UpperCabinet,
    Wall,
    WallGeometry,
    WallToRoofInfill,
    WallToRoofInfillGeometry,
    Window,
    from_end,
)
from .model import (
    Analysis,
    AnalysisContext,
    Build,
    Context,
    Definition,
    Element,
    Extrusion,
    House,
    NonNegative,
    Outline,
    Positive,
    Realized,
    Ref,
    Relation,
    definition,
    element,
    positional,
)
from .units import cm, m, mm, to_m

__version__ = "0.1.0"

__all__ = [
    "House", "Element", "Definition", "Context", "Realized", "Analysis", "AnalysisContext", "Build", "Ref", "Relation", "Extrusion",
    "element", "definition", "positional", "Positive", "NonNegative", "Outline",
    "mm", "cm", "m", "to_m",
    "Assembly", "Layer", "Level", "Material", "Render", "Site",
    "Beam", "BeamGrid", "Ceiling", "Slab",
    "Grid", "GridLine",
    "Bookcase", "Covering", "KitchenRun", "Part", "UpperCabinet",
    "Downlight", "Outlet", "Pendant",
    "Space",
    "Column", "Chimney", "Roof", "Gable", "Cornice", "WallToRoofInfill", "WallToRoofInfillGeometry", "Arch", "ArchVoid", "ArchedDoor", "OpeningPart", "Shutters", "Surround", "Grille",
    "Stair", "Landing", "Pool", "PoolWater", "Coping",
    "Clerestory", "Door", "FromEnd", "Glazing", "Leaf", "Opening", "OpeningGeometry", "SlidingDoor", "Wall", "WallGeometry", "Window", "from_end",
]
