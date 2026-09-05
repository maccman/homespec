"""Typed asset channels, provenance and physical-response contract boundaries."""
from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from homespec import House
from homespec.elements import AssetProvenance, AssetSource, Material, Render, SurfaceDetail, TextureAsset, TextureAssets, TextureMapping
from homespec.ir import IRMaterial, write_ir

DIGEST = hashlib.sha256(b"test asset").hexdigest()


def asset(**kwargs):
    return TextureAsset(path="textures/pigment.png", sha256=DIGEST, **kwargs)


def test_pigment_defaults_and_ir_provenance(tmp_path):
    source = AssetSource(identity="photos/original.png", sha256=DIGEST, kind="photo", evidence="observed")
    render = Render(assets=TextureAssets(channels=[asset()], mapping=TextureMapping(repeat_m=(2, .3, .3)),
                    provenance=AssetProvenance(sources=[source], generation_prompt="Neutral color sample", assumptions=["Roughness inferred"],
                                              limitations=["No measured displacement"])), rough=.72,
                    detail=[SurfaceDetail(wavelength_m=(.15, .002, .002), amplitude_m=.0003)])
    with House("Independent material fixture") as house:
        Material("timber", render=render)
    ir = write_ir(house.compile(), str(tmp_path))
    actual = Render.model_validate(ir.materials["timber"].render)
    assert actual == render
    assert actual.assets.channels[0].role == "base_color"
    assert actual.assets.provenance.generation_model is None
    assert actual.detail[0].amplitude_m == .0003
    assert json.loads(ir.model_dump_json())["materials"]["timber"]["render"]["assets"]["channels"][0]["sha256"] == DIGEST


@pytest.mark.parametrize("path", ["/absolute.png", "../escape.png", "textures/../../escape.png", "https://example.com/image.png", "C:\\image.png", "textures/\x00.png"])
def test_local_texture_paths(path):
    with pytest.raises(ValidationError):
        TextureAsset(path=path, sha256=DIGEST)


@pytest.mark.parametrize("digest", ["a" * 63, "F" * 64, "not-a-hash"])
def test_content_identity(digest):
    with pytest.raises(ValidationError):
        TextureAsset(path="image.png", sha256=digest)


@pytest.mark.parametrize("factory", [
    lambda: TextureMapping(repeat_m=(1, 0, 1)),
    lambda: TextureMapping(repeat_m=(1, float("nan"), 1)),
    lambda: TextureMapping(mode="member", uv_extent_m=(2, 1)),
    lambda: TextureMapping(grain_axis="v"),
    lambda: TextureAssets(channels=[asset(), asset()]),
    lambda: TextureAssets(channels=[asset(role="normal")]),
    lambda: TextureAssets(channels=[asset(role="height")]),
    lambda: TextureAssets(channels=[asset(role="height")], height_m=.03),
    lambda: SurfaceDetail(amplitude_m=.021),
    lambda: SurfaceDetail(strength=1.01),
    lambda: SurfaceDetail(wavelength_m=(.1, -.1, .1)),
    lambda: Render(rough_range=(.9, .2)),
    lambda: Render(assets=TextureAssets(channels=[asset(role="roughness")]), rough_range=(.5, .7)),
    lambda: Render(assets=TextureAssets(channels=[asset()]), bump=.2),
])
def test_invalid_material_contracts(factory):
    with pytest.raises(ValidationError):
        factory()


def test_explicit_channels_are_independent_and_valid():
    assets = TextureAssets(channels=[asset(), asset(role="normal"), asset(role="roughness"), asset(role="height")],
                           mapping=TextureMapping(mode="uv", uv_extent_m=(1.2, .8)), height_m=.0004)
    assert len(assets.channels) == 4
    assert assets.height_m == .0004


def test_ir_rejects_damaged_asset_mapping():
    value = Render(assets=TextureAssets(channels=[asset()])).model_dump()
    value["assets"]["mapping"]["repeat_m"] = [1, 0, 1]
    with pytest.raises(ValidationError):
        IRMaterial(render=value)


def test_ambiguous_material_texture_sources_fail_before_registration():
    with House("Ambiguous sources") as house, pytest.raises(ValidationError, match="choose legacy texture"):
        Material("ambiguous", texture="polyhaven/oak", render=Render(assets=TextureAssets(channels=[asset()])))
    assert not house.materials
