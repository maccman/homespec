"""The standard vocabulary.

Every class here is an ordinary :class:`~homespec.model.Element` or
:class:`~homespec.model.Definition`. Nothing is privileged by the core; a
project can add its own classes alongside these.
"""
from .columns import Chimney, Column
from .definitions import Assembly, Layer, Level, Material, Render, Setbacks, Site
from .floors import Beam, BeamGrid, Ceiling, Slab
from .grid import Grid, GridLine
from .joinery import Bookcase, Covering, KitchenRun, Part, UpperCabinet
from .landscape import Coping, Pool, PoolWater
from .roof import Cornice, Gable, Roof, WallToRoofInfill, WallToRoofInfillGeometry
from .services import Downlight, Outlet, Pendant
from .spaces import Space
from .stairs import Landing, Stair
from .walls import (
                    Arch,
                    ArchedDoor,
                    ArchVoid,
                    Clerestory,
                    Door,
                    FromEnd,
                    Glazing,
                    Grille,
                    Leaf,
                    Opening,
                    OpeningGeometry,
                    OpeningPart,
                    Shutters,
                    SlidingDoor,
                    Surround,
                    Wall,
                    WallGeometry,
                    Window,
                    from_end,
)

__all__ = [
    "Assembly", "Layer", "Level", "Material", "Render", "Setbacks", "Site",
    "Beam", "BeamGrid", "Ceiling", "Slab",
    "Grid", "GridLine",
    "Bookcase", "Covering", "KitchenRun", "Part", "UpperCabinet",
    "Downlight", "Outlet", "Pendant",
    "Space",
    "Column", "Chimney", "Roof", "Gable", "Cornice", "WallToRoofInfill", "WallToRoofInfillGeometry", "Arch", "ArchVoid", "ArchedDoor", "OpeningPart", "Shutters", "Surround", "Grille",
    "Stair", "Landing", "Pool", "PoolWater", "Coping",
    "Clerestory", "Door", "FromEnd", "Glazing", "Leaf", "Opening", "OpeningGeometry", "SlidingDoor", "Wall", "WallGeometry", "Window", "from_end",
]
