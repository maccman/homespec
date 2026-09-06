"""Definitions: what a house is described in terms of."""
from __future__ import annotations

from typing import Annotated, ClassVar, Literal, Self

from pydantic import Field, field_validator, model_validator

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


UnitInterval = Annotated[float, Field(ge=0, le=1)]
SHA256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class AssetSource(FiniteModel):
    """An evidence identity, retaining what is known and what was inferred."""

    identity: str = Field(min_length=1)
    sha256: SHA256 | None = None
    kind: Literal["photo", "plan", "generated", "procedural", "other"] = "other"
    evidence: Literal["observed", "plan_derived", "inferred", "unverified"] = "unverified"


class AssetProvenance(FiniteModel):
    """Color evidence does not establish measured reflectance or relief."""

    sources: list[AssetSource] = Field(default_factory=list)
    generation_prompt: str | None = None
    generation_model: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class TextureAsset(FiniteModel):
    """A project-relative local image, verified against its original bytes.

    Generated images default to pigment/Base Color. A normal map must use the
    OpenGL tangent convention; height images drive bounded bump, never geometry.
    """

    path: str
    sha256: SHA256
    role: Literal["base_color", "roughness", "normal", "height"] = "base_color"

    @field_validator("path")
    @classmethod
    def local_path(cls, value: str) -> str:
        from pathlib import PurePosixPath
        path = PurePosixPath(value)
        if not value or path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value or any(ord(c) < 32 for c in value):
            raise ValueError("texture path must be relative to its declared local root, without traversal")
        return value


class TextureMapping(FiniteModel):
    """Physical repeat dimensions in metres, independent of object scale.

    UVs are metric unless ``uv_extent_m`` explicitly scales a normalized UV
    rectangle. Member UVs are derived from the published member frame.
    ``object`` retains local coordinates for deliberately object-bound patterns.
    """

    mode: Literal["world", "object", "uv", "member"] = "world"
    repeat_m: tuple[Positive, Positive, Positive] = (1, 1, 1)
    uv_extent_m: tuple[Positive, Positive] | None = None
    uv_layer: str | None = None
    grain_axis: Literal["u", "v"] = "u"
    rotation_degrees: float = 0
    offset_m: tuple[float, float, float] = (0, 0, 0)
    random_offset: bool = False
    blend: UnitInterval = .15

    @model_validator(mode="after")
    def metric_member(self) -> Self:
        if self.mode != "uv" and self.uv_extent_m is not None:
            raise ValueError("uv_extent_m is only valid for normalized UV mapping; member coordinates are already metric")
        if self.mode not in {"uv", "member"} and self.grain_axis != "u":
            raise ValueError("grain_axis requires UV or member coordinates")
        return self


class TextureAssets(FiniteModel):
    """An explicit channel set with one common physical coordinate system."""

    channels: list[TextureAsset] = Field(min_length=1)
    mapping: TextureMapping = Field(default_factory=TextureMapping)
    provenance: AssetProvenance = Field(default_factory=AssetProvenance)
    normal_strength: UnitInterval = .6
    height_m: Annotated[float, Field(ge=0, le=.02)] = 0

    @model_validator(mode="after")
    def channel_contract(self) -> Self:
        roles = [channel.role for channel in self.channels]
        if len(roles) != len(set(roles)):
            raise ValueError("supply at most one image for each texture channel role")
        if "normal" in roles and self.mapping.mode not in {"uv", "member"}:
            raise ValueError("tangent normal maps require UV or member mapping; box projection has no consistent tangent basis")
        if "normal" in roles and (self.mapping.rotation_degrees % 360 != 0 or self.mapping.grain_axis != "u"):
            raise ValueError("rotated tangent normal maps need a rotated tangent basis; supply an unrotated UV layout")
        if "height" in roles and self.height_m <= 0:
            raise ValueError("a height channel requires an explicit positive height_m bump bound")
        return self


class SurfaceDetail(FiniteModel):
    """Independent bounded shader bump; silhouettes and joints stay geometry."""

    kind: Literal["noise", "weave"] = "noise"
    wavelength_m: tuple[Positive, Positive, Positive] = (.01, .01, .01)
    amplitude_m: Annotated[float, Field(ge=0, le=.02)] = .00015
    strength: UnitInterval = .18
    detail: Annotated[float, Field(ge=0, le=8)] = 2
    coordinates: Literal["world", "object", "uv", "member"] = "world"


class Render(FiniteModel):
    """Material appearance; metric assets and surface response stay independent."""

    tile: Positive = 1.0
    tint: tuple[float, float, float] = (1.0, 1.0, 1.0)
    value: NonNegative = 1.0
    saturation: NonNegative = 1.0
    wash: UnitInterval = 0.0
    rough_mul: NonNegative = 1.0
    color: tuple[float, float, float] | None = None
    rough: UnitInterval = 0.5
    metal: UnitInterval = 0.0
    emit: NonNegative = 0.0
    transmission: UnitInterval = 0.0
    absorb: NonNegative = 0.0
    bump: NonNegative = 0.0
    ior: Annotated[float, Field(ge=1, le=4)] = 1.46
    sheen: UnitInterval = 0
    rough_range: tuple[UnitInterval, UnitInterval] | None = None
    rough_repeat_m: Positive = 1 / 45
    assets: TextureAssets | None = None
    detail: list[SurfaceDetail] = Field(default_factory=list)

    @model_validator(mode="after")
    def response_contract(self) -> Self:
        if self.rough_range is not None and self.rough_range[0] > self.rough_range[1]:
            raise ValueError("rough_range must be ordered from minimum to maximum")
        if self.assets and any(asset.role == "roughness" for asset in self.assets.channels) and self.rough_range:
            raise ValueError("choose an explicit roughness channel or a procedural rough_range")
        if self.assets and self.bump:
            raise ValueError("local assets use metric SurfaceDetail; legacy bump cannot be combined")
        return self


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

    def __post_init__(self) -> None:
        if self.texture and (self.render.assets or self.render.detail or self.render.rough_range):
            raise ValueError("choose legacy texture hints or explicit local assets/detail for a material")
        super().__post_init__()


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


__all__ = ["Level", "Layer", "Assembly", "Render", "Material", "Site", "Point", "AssetSource", "AssetProvenance", "TextureAsset", "TextureMapping", "TextureAssets", "SurfaceDetail"]
