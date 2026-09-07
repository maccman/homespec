"""Appearance configuration/probe rejection tests; no Blender or Unreal import."""

import ast
import copy
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/apply_unreal_look.py"


def contract():
    tree = ast.parse(SCRIPT.read_text())
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name in {"require", "validate_config", "validate_source_properties", "direction_error_degrees"}]
    namespace = {"math": math}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(SCRIPT), "exec"), namespace)
    return namespace


class LightDirectionTests(unittest.TestCase):
    def setUp(self):
        self.error = contract()["direction_error_degrees"]

    def test_scaled_equivalent_directions_are_equal(self):
        # A pose comparison must depend on direction, not vector normalization
        # or the particular Euler representation used to produce the vector.
        self.assertAlmostEqual(self.error([0, -2, 0], [0, -1, 0]), 0)
        self.assertAlmostEqual(self.error([1, 2, 3], [10, 20, 30]), 0)

    def test_opposite_and_perpendicular_lights_are_not_equivalent(self):
        self.assertAlmostEqual(self.error([0, 0, -1], [0, 0, 1]), 180)
        self.assertAlmostEqual(self.error([0, 0, -1], [0, 1, 0]), 90)

    def test_missing_light_direction_is_rejected_on_either_side(self):
        for actual, expected in (([0, 0, 0], [0, 0, 1]), ([0, 0, 1], [0, 0, 0])):
            with self.subTest(actual=actual, expected=expected), self.assertRaises(RuntimeError):
                self.error(actual, expected)


class LookConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.api = contract()
        self.config = json.loads((ROOT / "look.daylight.json").read_text())

    def reject(self, key, value):
        config = copy.deepcopy(self.config)
        config[key] = value
        with self.assertRaises(RuntimeError):
            self.api["validate_config"](config)

    def test_current_config_and_allowed_boundary_values(self):
        self.api["validate_config"](self.config)
        config = copy.deepcopy(self.config)
        config.update(glass_opacity=0, water_opacity=1, glass_roughness=1,
                      glass_tint=[0, 1, 0.5], water_tint=[1, 0, 1],
                      bloom_intensity=0, white_temp_kelvin=None)
        self.api["validate_config"](config)

    def test_missing_required_keys_rejected(self):
        optional = {"description", "source_render_properties", "white_temp_kelvin"}
        for key in self.config.keys() - optional:
            with self.subTest(key=key):
                config = copy.deepcopy(self.config)
                del config[key]
                with self.assertRaises(RuntimeError):
                    self.api["validate_config"](config)

    def test_positive_fields_reject_nonfinite_zero_negative_boolean_and_strings(self):
        keys = ("source_lumens_per_watt", "aperture_attenuation_radius_m", "practical_attenuation_radius_m",
                "sun_lux", "sky_intensity", "exposure_speed_up", "exposure_speed_down")
        for key in keys:
            for value in (float("nan"), float("inf"), -float("inf"), 0, -1, True, "2"):
                with self.subTest(key=key, value=value):
                    self.reject(key, value)

    def test_exposure_values_and_order_rejected(self):
        for key in ("exposure_min_ev100", "exposure_max_ev100", "exposure_compensation"):
            for value in (float("nan"), float("inf"), True, "4"):
                with self.subTest(key=key, value=value):
                    self.reject(key, value)
        self.reject("exposure_min_ev100", self.config["exposure_max_ev100"])
        self.reject("exposure_max_ev100", self.config["exposure_min_ev100"] - 1)

    def test_opacity_roughness_and_tints_reject_invalid_channels(self):
        for key in ("glass_opacity", "glass_roughness", "water_opacity"):
            for value in (float("nan"), float("inf"), -0.001, 1.001, True, "0.5"):
                with self.subTest(key=key, value=value):
                    self.reject(key, value)
        for key in ("glass_tint", "water_tint"):
            for value in ([1, 1], [1, 1, 1, 1], [float("nan"), 0, 0], [1.01, 0, 0], [-0.01, 0, 0], [True, 0, 0], "white"):
                with self.subTest(key=key, value=value):
                    self.reject(key, value)

    def test_white_temperature_bloom_and_selection_types_rejected(self):
        for value in (1499, 15001, float("nan"), float("inf"), "5500"):
            self.reject("white_temp_kelvin", value)
        for value in (-1, float("nan"), float("inf"), True):
            self.reject("bloom_intensity", value)
        for key in ("include_source_aperture_fills", "glass_surface_forward_shading", "two_sided_inventory_plants", "two_sided_shadows"):
            self.reject(key, 1)
        for value in ("plant", [None], [1]):
            self.reject("two_sided_source_objects", value)


class SourceRenderPropertyTests(unittest.TestCase):
    def setUp(self):
        self.api = contract()
        self.source = {"name": "Lamp", "type": "POINT", "energy": 12.0, "color": [1, 0.78, 0.55],
                       "matrix4x4": [[1, 0, 0, 2], [0, 1, 0, 3], [0, 0, 1, 4], [0, 0, 0, 1]]}
        self.manifest = {"source": "/fixture/frozen.blend", "source_sha256": "fixture-sha", "lights": [self.source]}
        light = {"name": "Lamp", "type": "POINT", "energy": 12.0, "color": [1, 0.78, 0.55],
                 "location": [2, 3, 4], "shadow_soft_size": 0.065}
        self.probe = {"source": self.manifest["source"], "source_sha256": "fixture-sha",
                      "source_sha256_before": "fixture-sha", "source_sha256_after": "fixture-sha",
                      "status": "verified_read_only_render_properties",
                      "frames": {str(frame): {"lights": [copy.deepcopy(light)], "exposure": 0} for frame in (1, 385, 1249)}}

    def validate(self, probe):
        return self.api["validate_source_properties"](probe, self.manifest)

    def test_complete_static_source_probe_accepted(self):
        self.assertEqual(set(self.validate(self.probe)), {"Lamp"})

    def test_source_identity_and_completion_rejected(self):
        for key in ("source", "source_sha256", "source_sha256_before", "source_sha256_after", "status"):
            with self.subTest(key=key):
                probe = copy.deepcopy(self.probe)
                probe[key] = "different"
                with self.assertRaises(RuntimeError):
                    self.validate(probe)

    def test_changed_light_energy_color_or_position_rejected(self):
        for key, value in (("energy", 24), ("type", "SUN"), ("color", [1, 1, 1]), ("location", [2, 3, 4.1])):
            with self.subTest(key=key):
                probe = copy.deepcopy(self.probe)
                for frame in probe["frames"].values():
                    frame["lights"][0][key] = value
                with self.assertRaises(RuntimeError):
                    self.validate(probe)

    def test_animated_softness_rejected(self):
        probe = copy.deepcopy(self.probe)
        probe["frames"]["385"]["lights"][0]["shadow_soft_size"] = 0.2
        with self.assertRaises(RuntimeError):
            self.validate(probe)

    def test_missing_animation_sample_rejected(self):
        for frame in ("1", "385", "1249"):
            with self.subTest(frame=frame):
                probe = copy.deepcopy(self.probe)
                del probe["frames"][frame]
                with self.assertRaises(RuntimeError):
                    self.validate(probe)

    def test_duplicate_or_missing_light_in_any_frame_rejected(self):
        for key in ("1", "385", "1249"):
            for duplicate in (False, True):
                with self.subTest(frame=key, duplicate=duplicate):
                    probe = copy.deepcopy(self.probe)
                    rows = probe["frames"][key]["lights"]
                    if duplicate:
                        rows.append(copy.deepcopy(rows[0]))
                    else:
                        rows.clear()
                    with self.assertRaises(RuntimeError):
                        self.validate(probe)


if __name__ == "__main__":
    unittest.main()
