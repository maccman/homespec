"""Small boundary validators shared by declarations and serialized models."""
from __future__ import annotations

import math
from dataclasses import fields, is_dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict
from shapely.geometry import Polygon
from shapely.validation import explain_validity


class FiniteModel(BaseModel):
    """A nested vocabulary value whose numeric fields stay finite after assignment."""

    model_config = ConfigDict(allow_inf_nan=False, validate_assignment=True)


def identifier(value: str) -> str:
    if not value.strip() or value in {".", ".."} or any(c in value for c in '/\\\x00') or any(ord(c) < 32 for c in value):
        raise ValueError(f"unsafe identifier {value!r}")
    return value


def outline(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not all(math.isfinite(v) for p in points for v in p):
        raise ValueError("outline coordinates must be finite")
    polygon = Polygon(points)
    if not polygon.is_valid or polygon.area <= 0:
        raise ValueError(f"invalid outline: {explain_validity(polygon)}")
    return points[:-1] if points[0] == points[-1] else points


def finite_tree(value: Any, path: str = "model") -> None:
    """Reject NaN/Infinity inside declarations, nested values, and extension dictionaries."""
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path}: number must be finite")
    if isinstance(value, BaseModel):
        for key in type(value).model_fields:
            finite_tree(getattr(value, key), f"{path}.{key}")
    elif is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            finite_tree(getattr(value, field.name), f"{path}.{field.name}")
    elif isinstance(value, dict):
        for key, item in value.items():
            finite_tree(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple, set, frozenset)):
        for index, item in enumerate(value):
            finite_tree(item, f"{path}[{index}]")
