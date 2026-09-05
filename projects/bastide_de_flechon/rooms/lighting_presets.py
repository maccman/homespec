"""Reproducible lighting studies, distinct from the coherent walking state.

Photographic values are visual estimates, not recovered capture metadata or
solar measurements. Directions use the house's model axes. The HDRI is a
sun-free sky; one explicit sun produces the directional shadows.
"""

PRESETS = {
    "walk": {
        "reference": "All rooms; coherent shared daylight interpretation",
        "sun_direction": (0.72, 0.62, -0.31), "sun_energy": 2.6,
        "sun_angle": 0.80, "sun_color": (1.0, 0.91, 0.77),
        "sky_rotation": 115, "sky_strength": 1.65,
        "supplemental_window_fraction": 0.2, "window_color": (1.0, 0.96, 0.90),
        "exposure": 1.9, "white_balance_kelvin": 5500, "white_balance_tint": 0,
        "interior_exposure_offset": 1.25,
        "exposure_offset_exempt": ("Garden bedroom one bathroom", "Garden bedroom two bathroom",
                                  "Laundry · plan-derived fittings", "Guest WC · plan-derived fittings", "Guest corridor"),
        "practical_default": 1.0, "fixture_multipliers": {"salon_fp_fire_practical": 0.0, "fire": 0.0, "hearth": 0.0},
        "note": "One low model-southwest daylight state; 20% aperture approximation selected after off/on tests. Interior EV adaptation preserves windowless-room base values.",
    },
    "kitchen10": {
        "reference": "photo_10.jpg / Final Collection-2.jpg",
        "sun_direction": (0.72, 0.62, -0.31), "sun_energy": 3.0,
        "sun_angle": 0.80, "sun_color": (1.0, 0.88, 0.68),
        "sky_rotation": 110, "sky_strength": 1.95,
        "supplemental_window_fraction": 0.2, "window_color": (1.0, 0.96, 0.90),
        "exposure": 2.45, "white_balance_kelvin": 5400, "white_balance_tint": 0,
        "practical_default": 0.0, "fixture_multipliers": {},
        "note": "Warm lateral daylight; woven pendants read largely unlit in the reference.",
    },
    "principal06": {
        "reference": "photo_06.jpg / Final Collection-16.jpg",
        "sun_direction": (-0.64, 0.61, -0.48), "sun_energy": 2.3,
        "sun_angle": 0.85, "sun_color": (1.0, 0.91, 0.79),
        "sky_rotation": 115, "sky_strength": 2.25,
        "supplemental_window_fraction": 0.2, "window_color": (1.0, 0.96, 0.90),
        "exposure": 1.7, "white_balance_kelvin": 5500, "white_balance_tint": 0,
        "practical_default": 0.0, "fixture_multipliers": {"principal_bedside": 0.4},
        "note": "Bright greenery beyond a shaded tobacco interior; small practical contribution.",
    },
    "principal33": {
        "reference": "photo_33.jpg / principal seating cross-view",
        "sun_direction": (-0.64, 0.61, -0.48), "sun_energy": 3.2,
        "sun_angle": 0.60, "sun_color": (1.0, 0.88, 0.69),
        "sky_rotation": 115, "sky_strength": 1.95,
        "supplemental_window_fraction": 0.2, "window_color": (1.0, 0.96, 0.90),
        "exposure": 1.8, "white_balance_kelvin": 5400, "white_balance_tint": 0,
        "practical_default": 0.0, "fixture_multipliers": {},
        "note": "Same sun azimuth as photo06 study, stronger direct light for the visible arch shadow.",
    },
    "salon58": {
        "reference": "photo_58.jpg / fireplace and garden",
        "sun_direction": (-0.81, 0.33, -0.49), "sun_energy": 2.8,
        "sun_angle": 0.90, "sun_color": (1.0, 0.89, 0.72),
        "sky_rotation": 110, "sky_strength": 2.4,
        "supplemental_window_fraction": 0.15, "window_color": (1.0, 0.96, 0.90),
        "exposure": 1.55, "white_balance_kelvin": 5500, "white_balance_tint": 0,
        "practical_default": 0.0,
        "fixture_multipliers": {"salon_fp_fire_practical": 1.0, "salon": 1.35, "dining": 1.0, "fire": 1.0, "hearth": 1.0},
        "note": "Illuminated lanterns and fireplace with brighter garden daylight.",
    },
    "garden02": {
        "reference": "photo_02.jpg / Final Collection-12.jpg",
        "sun_direction": (-0.86, -0.16, -0.48), "sun_energy": 2.7,
        "sun_angle": 0.90, "sun_color": (1.0, 0.90, 0.75),
        "sky_rotation": 100, "sky_strength": 2.1,
        "supplemental_window_fraction": 0.2, "window_color": (1.0, 0.96, 0.90),
        "exposure": 1.55, "white_balance_kelvin": 5500, "white_balance_tint": 0,
        "practical_default": 0.0, "fixture_multipliers": {"guest_1_sconce": 1.1, "guest_1_woven_sconce": 1.1},
        "note": "Luminous window-side curtain edge and illuminated woven sconces.",
    },
    "bedroom09": {
        "reference": "photo_09.jpg / Final Collection-19.jpg",
        "sun_direction": (-0.55, 0.67, -0.50), "sun_energy": 1.7,
        "sun_angle": 1.2, "sun_color": (1.0, 0.94, 0.85),
        "sky_rotation": 120, "sky_strength": 2.25,
        "supplemental_window_fraction": 0.2, "window_color": (1.0, 0.96, 0.90),
        "exposure": 1.9, "white_balance_kelvin": 5600, "white_balance_tint": 0,
        "practical_default": 0.0, "fixture_multipliers": {},
        "note": "Soft neutral daylight supports the light weathered wardrobe and linen.",
    },
    "hall21": {
        "reference": "photo_21.jpg / Final Collection-3.jpg",
        "sun_direction": (-0.92, 0.10, -0.42), "sun_energy": 3.5,
        "sun_angle": 0.55, "sun_color": (1.0, 0.89, 0.72),
        "sky_rotation": 100, "sky_strength": 1.95,
        "supplemental_window_fraction": 0.2, "window_color": (1.0, 0.96, 0.90),
        "exposure": 1.3, "white_balance_kelvin": 5500, "white_balance_tint": 0,
        "practical_default": 0.0, "fixture_multipliers": {"hall_glass_pendant": 0.35},
        "note": "Strong lateral east-glazing sun and warm bounce under the crossing ceiling.",
    },
    "shower05": {
        "reference": "photo_05.jpg / Final Collection-15.jpg; bathroom assignment inferred",
        "sun_direction": (0.18, -0.91, -0.38), "sun_energy": 2.4,
        "sun_angle": 0.75, "sun_color": (1.0, 0.92, 0.81),
        "sky_rotation": 280, "sky_strength": 2.55,
        "supplemental_window_fraction": 0.2, "window_color": (1.0, 0.96, 0.90),
        "exposure": 1.85, "white_balance_kelvin": 5500, "white_balance_tint": 0,
        "practical_default": 0.0, "fixture_multipliers": {},
        "note": "Curtain-filtered daylight from the interpreted north/window wall; no ceiling fill.",
    },
}

# The reverse kitchen study keeps photo10's radiometry as a control and adds
# only the visibly warm wire-fixture practicals. It does not claim recovered
# photo00 photometry; the coherent house walk is unchanged.
PRESETS["kitchen00"] = {
    **PRESETS["kitchen10"],
    "reference": "photo_00.jpg / Final Collection-10.jpg",
    "fixture_multipliers": {"kitchen_fine_wire_pendant_": .6},
    "note": "Reverse construction validation; same daylight/EV as kitchen10 with 60% kitchen practicals. Crop, shift and captured photometry remain inferred.",
}


def fixture_multiplier(name, preset):
    """Longer explicit prefixes win, with a complete fallback for every light."""
    for prefix, value in sorted(preset["fixture_multipliers"].items(), key=lambda item: -len(item[0])):
        if name.startswith(prefix):
            return value
    return preset["practical_default"]
