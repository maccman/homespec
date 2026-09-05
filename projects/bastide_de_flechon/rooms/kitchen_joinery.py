"""Kitchen furniture construction inferred from photos 00, 10, 35 and 54.

Run after the shared fidelity passes. The photograph-locked stone-top bounds
remain unchanged; the visible furniture has independent rails, stiles, panels,
and a real sink void. Dimensions below are photographic estimates in metres.
"""

from __future__ import annotations

import importlib.util
import math
import os

import bpy


def _load(name):
    spec = importlib.util.spec_from_file_location("kitchen_joinery_" + name, os.path.join(os.path.dirname(__file__), name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F, S, J = (_load(name) for name in ("furnishings", "living_shapes", "fidelity_living"))
TOP_BOUNDS = (-3.16, -2.10, 10.35, 13.795)
TOP_Z = 0.9575
STONE_THICKNESS = 0.025
SINK_BOUNDS = (-2.98, -2.38, 11.99, 12.68)
BODY_SOUTH = 11.25


def _remove(*prefixes):
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)


def _box(scene, name, at, size, material, *, rot=0, bevel=0.0015):
    obj = J.box(scene, name, at, size, material, rot=rot, bevel=bevel)
    layer = obj.data.uv_layers["Walnut grain"]
    obj.data.uv_layers.active = layer
    layer.active_render = True
    return obj


def _grain(obj, along, across):
    """A broad end panel keeps vertical grain even when wider than high."""
    layer = obj.data.uv_layers.get("Walnut grain") or obj.data.uv_layers.new(name="Walnut grain")
    obj.data.uv_layers.active = layer
    layer.active_render = True
    for face in obj.data.polygons:
        for index in face.loop_indices:
            point = obj.data.vertices[obj.data.loops[index].vertex_index].co
            layer.data[index].uv = (point[along], point[across])


def _panel(scene, name, at, width, height, material, rot=0, *, horizontal=False):
    """Four mitred solid members and a recessed field; local front is -Y.

    The photograph shows a broad flat border, one ogee transition and a narrow
    inner bead. The earlier five detached concentric stick rectangles were not
    that construction. Each member gets its own lengthwise material UVs.
    """
    p = F.transform(at, rot)
    border = min(0.095, height * 0.24, width * 0.20)
    # (inset from outside edge, forward projection). Smooth rounded profiles
    # are sampled explicitly instead of shading a succession of square rods.
    sections = [(0, 0.003), (0.006, 0.009), (border * 0.45, 0.010),
                (border * 0.55, 0.012), (border * 0.64, 0.017),
                (border * 0.72, 0.019), (border * 0.81, 0.015),
                (border * 0.89, 0.007), (border * 0.96, 0.004),
                (border, 0.006)]
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for side in range(4):
        vertices, faces = [], []
        for inset, projection in sections:
            for corner in (side, (side + 1) % 4):
                sx, sz = corners[corner]
                vertices.append((sx * (width / 2 - inset), -projection, sz * (height / 2 - inset)))
        for i in range(len(sections) - 1):
            faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
        # Close each solid member at the joinery back plane.
        outline = [0, 1] + list(range(3, len(vertices), 2)) + list(range(len(vertices) - 2, 0, -2))
        back = len(vertices)
        vertices.extend((vertices[i][0], 0.021, vertices[i][2]) for i in outline)
        faces.append(tuple(reversed(range(back, len(vertices)))))
        for i, front in enumerate(outline):
            following = (i + 1) % len(outline)
            faces.append((front, back + i, back + following, outline[following]))
        obj = S.mesh(scene, name + ("_rail" if side % 2 == 0 else "_stile"), vertices, faces, material, at=at, rot=rot)
        J.grain_uv(obj)
        for face in obj.data.polygons:
            face.use_smooth = face.index < len(sections) - 1
        normal = obj.modifiers.new("Broad joinery faces", "WEIGHTED_NORMAL")
        normal.keep_sharp = True
    field = _box(scene, name + "_field", p(0, 0.009, 0), (width - 2 * border + 0.002, 0.019, height - 2 * border + 0.002), material, rot=rot)
    _grain(field, 0 if horizontal else 2, 2 if horizontal else 0)


def _pull(scene, name, at, width, material, rot=0):
    J.handle(scene, name, at, width, material, rot)


def _rounded_rect(bounds, radius, z, count=64):
    x0, x1, y0, y1 = bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    width, depth = x1 - x0, y1 - y0
    points = []
    quarter = count // 4
    for i in range(count):
        corner, step = divmod(i, quarter)
        angle = corner * math.pi / 2 + step / (quarter - 1) * math.pi / 2
        sx = 1 if corner in (0, 3) else -1
        sy = 1 if corner in (0, 1) else -1
        points.append((cx + sx * (width / 2 - radius) + radius * math.cos(angle),
                       cy + sy * (depth / 2 - radius) + radius * math.sin(angle), z))
    return points


def _worktop(scene, N):
    """One continuous stone mesh with an actual open, rounded cutout."""
    count = 64
    vertices = _rounded_rect(TOP_BOUNDS, 0.002, TOP_Z)
    vertices += _rounded_rect(SINK_BOUNDS, 0.035, TOP_Z)
    vertices += _rounded_rect(TOP_BOUNDS, 0.002, TOP_Z - STONE_THICKNESS)
    vertices += _rounded_rect(SINK_BOUNDS, 0.035, TOP_Z - STONE_THICKNESS)
    faces = []
    for i in range(count):
        j = (i + 1) % count
        faces.extend(((i, j, count + j, count + i),
                      (2 * count + i, 3 * count + i, 3 * count + j, 2 * count + j),
                      (i, 2 * count + i, 2 * count + j, j),
                      (count + i, count + j, 3 * count + j, 3 * count + i)))
    top = S.mesh(scene, "kitchen_island_continuous_stone_with_sink_cutout", vertices, faces, N.travertine, tag="primitive")
    for face in top.data.polygons:
        face.use_smooth = False
    bevel = top.modifiers.new("1.2 mm eased stone edges", "BEVEL")
    bevel.width = 0.0012
    bevel.segments = 3
    top["kitchen_stone_thickness_m"] = STONE_THICKNESS
    top["kitchen_counter_hole_bounds_m"] = list(SINK_BOUNDS)


def _island(scene, N):
    _remove("kitchen_island_", "kitchen_sink_", "kitchen_chopping_board")
    x0, x1, y0, y1 = -3.135, -2.125, BODY_SOUTH, 13.77
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    length = y1 - y0
    # Structural skins sit behind the recessed panel fields. A 20 mm centre
    # inset put their opaque faces 7.5 mm in front of those fields and exposed
    # horizontal backing grain. The 48 mm inset gives 1.5 mm clear behind the
    # field's back while retaining its intended face and all frame positions.
    for x in (x0 + 0.048, x1 - 0.048):
        _box(scene, "kitchen_island_shell_side", (x, cy, 0.505), (0.032, length - 0.045, 0.735), N.walnut)
    for y in (y0 + 0.048, y1 - 0.048):
        _box(scene, "kitchen_island_shell_end", (cx, y, 0.505), (x1 - x0 - 0.064, 0.032, 0.735), N.walnut)
    _box(scene, "kitchen_island_bottom_board", (cx, cy, 0.145), (0.92, length - 0.065, 0.032), N.walnut)
    _box(scene, "kitchen_island_recessed_plinth", (cx, cy, 0.060), (0.935, length - 0.045, 0.12), N.walnut)
    for z, height, extra in ((0.126, 0.026, 0.025), (0.165, 0.022, 0.012), (0.891, 0.026, 0.012), (0.920, 0.025, 0.026)):
        for x in (x0 + 0.023, x1 - 0.023):
            _box(scene, "kitchen_island_edge_rail", (x, cy, z), (0.046 + extra, length, height), N.walnut)
        for y in (y0 + 0.023, y1 - 0.023):
            _box(scene, "kitchen_island_end_rail", (cx, y, z), (x1 - x0 + extra, 0.046, height), N.walnut)
    for y, rot in ((y0 + 0.012, 0), (y1 - 0.012, math.pi)):
        _panel(scene, "kitchen_island_framed_end", (cx, y, 0.520), 0.976, 0.700, N.walnut, rot)
    bays = 3
    bay = (length - 0.08) / bays
    for i in range(bays):
        y = y0 + 0.040 + (i + 0.5) * bay
        _panel(scene, "kitchen_island_east_joined_panel", (x1 - 0.012, y, 0.520), bay - 0.010, 0.700, N.walnut, math.pi / 2)
        for z, height in ((0.351, 0.355), (0.714, 0.350)):
            _panel(scene, "kitchen_island_working_drawer", (x0 + 0.012, y, z), bay - 0.010, height, N.walnut, -math.pi / 2, horizontal=True)
            _pull(scene, "kitchen_island_working_pull", (x0 - 0.009, y, z + 0.025), min(0.28, bay * 0.55), N.brass, -math.pi / 2)
    # Photo35/54 and the plan show a garden-end table extension. The inferred
    # steel subframe continues into the full cabinet and bears on its end/side
    # frame; its two rails stay outside the actual bowl clearance envelope.
    for x in (-3.075, -2.185):
        support = _box(scene, "kitchen_island_table_support", (x, (10.375 + 13.71) / 2, 0.911), (0.035, 13.71 - 10.375, 0.040), N.iron)
        support["kitchen_inferred_construction"] = "Concealed steel underframe supports the photographed stone extension; not surveyed"
    for y in (11.285, 13.71):
        _box(scene, "kitchen_island_table_crossmember", (cx, y, 0.911), (0.89, 0.035, 0.040), N.iron)
    _worktop(scene, N)
    _sink(scene, N)


def _sink(scene, N):
    sx0, sx1, sy0, sy1 = SINK_BOUNDS
    cx, cy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
    count = 64
    vertices, faces = [], []
    for z, width, depth, radius in ((TOP_Z - 0.003, 0.600, 0.690, 0.035),
                                  (0.928, 0.584, 0.674, 0.036),
                                  (0.770, 0.530, 0.610, 0.068),
                                  (0.748, 0.460, 0.540, 0.090)):
        vertices += _rounded_rect((cx - width / 2, cx + width / 2, cy - depth / 2, cy + depth / 2), radius, z)
    vertices += [(cx + 0.035 * math.cos(i * math.tau / count), cy + 0.035 * math.sin(i * math.tau / count), 0.746) for i in range(count)]
    for row in range(4):
        for i in range(count):
            j = (i + 1) % count
            faces.append((row * count + i, row * count + j, (row + 1) * count + j, (row + 1) * count + i))
    bowl = S.mesh(scene, "kitchen_sink_open_steel_shell", vertices, faces, N.silver, tag="primitive")
    for face in bowl.data.polygons:
        face.use_smooth = face.index < 3 * count
    solid = bowl.modifiers.new("1.2 mm stainless shell", "SOLIDIFY")
    solid.thickness = 0.0012
    bowl["kitchen_sink_clear_depth_m"] = TOP_Z - 0.748
    S.lathe(scene, "kitchen_sink_open_drain_neck", [(0.712, 0.033), (0.746, 0.035), (0.749, 0.040), (0.751, 0.038), (0.748, 0.032), (0.712, 0.030)], N.silver, at=(cx, cy, 0), segments=64)
    paths = [S.ring(0.027, 0.749, centre=(cx, cy))]
    for i in range(8):
        angle = i * math.tau / 8
        paths.append([(cx + 0.007 * math.cos(angle), cy + 0.007 * math.sin(angle), 0.749),
                      (cx + 0.026 * math.cos(angle), cy + 0.026 * math.sin(angle), 0.749)])
    S.curves(scene, "kitchen_sink_perforated_strainer", paths, 0.0018, N.silver)
    scene.cyl("kitchen_sink_strainer_screw", (cx, cy, 0.750), 0.007, 0.003, N.silver, verts=32)
    # The overflow plate is on the far inside bowl wall, visible in photo10.
    _box(scene, "kitchen_sink_overflow_plate", (cx, sy0 + 0.028, 0.892), (0.077, 0.002, 0.031), N.silver, bevel=0.004)
    for x in (cx - 0.022, cx, cx + 0.022):
        _box(scene, "kitchen_sink_overflow_slot", (x, sy0 + 0.030, 0.892), (0.013, 0.0015, 0.008), N.iron, bevel=0.002)


def _tap_and_board(scene, N):
    _remove("kitchen_tap", "kitchen_polished_swan_spout", "kitchen_chopping_board")
    at = (-2.22, 12.29, TOP_Z)
    # Photos00/10 show a turned vertical column and a nearly horizontal,
    # undulating reach, not a continuous high semicircular kitchen hose.
    S.lathe(scene, "kitchen_tap_period_column", [(0, 0.042), (0.012, 0.042), (0.020, 0.026),
            (0.045, 0.019), (0.060, 0.025), (0.075, 0.020), (0.130, 0.019),
            (0.150, 0.025), (0.168, 0.020), (0.280, 0.017), (0.291, 0.028),
            (0.305, 0.025), (0.317, 0.016), (0.328, 0.018), (0.334, 0)], N.silver, at=at, segments=64)
    path = S.bezier((0, 0, 0.285), (-0.11, 0, 0.275), (-0.18, 0, 0.225), (-0.235, 0, 0.278), 28)
    path += S.bezier((-0.235, 0, 0.278), (-0.285, 0, 0.335), (-0.34, 0, 0.292), (-0.340, 0, 0.226), 24)[1:]
    S.curves(scene, "kitchen_tap_undulating_spout", [path], 0.012, N.silver, at=at)
    S.lathe(scene, "kitchen_tap_spout_nozzle", [(0.208, 0.014), (0.223, 0.016), (0.235, 0.014)], N.silver, at=(at[0] - 0.34, at[1], at[2]), segments=40)
    for y in (12.14, 12.44):
        S.lathe(scene, "kitchen_tap_deck_valve", [(0, 0.027), (0.012, 0.027), (0.022, 0.016),
                    (0.085, 0.013), (0.095, 0.021), (0.106, 0.013)], N.silver, at=(-2.22, y, TOP_Z), segments=48)
        S.curves(scene, "kitchen_tap_cross_handle", [[(-0.033, 0, 0.113), (0.033, 0, 0.113)],
                 [(0, -0.033, 0.113), (0, 0.033, 0.113)]], 0.0045, N.silver, at=(-2.22, y, TOP_Z))
    board_material = getattr(N, "board", N.walnut)
    board = _box(scene, "kitchen_chopping_board", (-2.63, 11.65, TOP_Z + 0.014), (0.84, 0.46, 0.028), board_material, bevel=0.020)
    _grain(board, 0, 1)


def _wall_cabinets(scene, N):
    _remove("kitchen_lower", "kitchen_tall", "kitchen_display", "kitchen_glazed", "kitchen_crystal", "kitchen_glass_jug",
            "kitchen_ceramics", "kitchen_crown", "kitchen_continuous_cornice", "kitchen_plinth", "kitchen_west_travertine", "kitchen_hood")
    # Retain the west run and range centre. Photo35 gives a narrow tall unit
    # beside two glazed leaves; photo00 ends the north run at a low counter.
    south, tall_end, north = 9.24, 9.98, 15.62
    for a, b in ((south, 11.755), (13.085, north)):
        _box(scene, "kitchen_lower_structural_base", (-4.715, (a + b) / 2, 0.466), (0.570, b - a, 0.880), N.grey)
        _box(scene, "kitchen_lower_recessed_toe", (-4.745, (a + b) / 2, 0.068), (0.475, b - a, 0.136), N.grey)
        if a == south:
            a = tall_end
        _box(scene, "kitchen_west_thin_stone_counter", (-4.70, (a + b) / 2, TOP_Z - STONE_THICKNESS / 2), (0.660, b - a, STONE_THICKNESS), N.travertine)
        _box(scene, "kitchen_west_stone_upstand", (-4.997, (a + b) / 2, TOP_Z + 0.080), (0.024, b - a, 0.160), N.travertine)
    rot, front = math.pi / 2, -4.390
    # South/garden tall bank: top cupboard, long middle door, lower door.
    _box(scene, "kitchen_tall_narrow_carcase", (-4.72, (south + tall_end) / 2, 1.395), (0.56, tall_end - south, 2.51), N.grey)
    for z0, z1, pull_z in ((0.142, 0.932, 0.839), (0.940, 2.145, 1.067), (2.153, 2.650, None)):
        _panel(scene, "kitchen_tall_stacked_door", (front, (south + tall_end) / 2, (z0 + z1) / 2), 0.704, z1 - z0, N.grey, rot)
        if pull_z is not None:
            _pull(scene, "kitchen_tall_stacked_pull", (front + 0.022, (south + tall_end) / 2, pull_z), 0.31, N.silver, rot)
    # Double doors beneath glazing, with narrow top drawers; three drawers
    # next to the range are independently editable fronts with real gaps.
    for a, b in ((10.00, 11.265), (13.57, 14.825), (14.835, 15.62)):
        width = (b - a) / 2
        for i in range(2):
            y = a + (i + 0.5) * width
            _panel(scene, "kitchen_lower_paneled_door", (front, y, 0.478), width - 0.010, 0.648, N.grey, rot)
            _panel(scene, "kitchen_lower_top_drawer", (front, y, 0.857), width - 0.010, 0.100, N.grey, rot, horizontal=True)
            _pull(scene, "kitchen_lower_drawer_pull", (front + 0.021, y, 0.857), min(0.27, width * 0.62), N.silver, rot)
    for a, b in ((11.275, 11.755), (13.085, 13.56)):
        for z0, z1 in ((0.154, 0.510), (0.518, 0.740), (0.748, 0.906)):
            _panel(scene, "kitchen_range_adjacent_drawer", (front, (a + b) / 2, (z0 + z1) / 2), b - a - 0.010, z1 - z0, N.grey, rot, horizontal=True)
            _pull(scene, "kitchen_range_adjacent_pull", (front + 0.021, (a + b) / 2, z1 - 0.053), 0.255, N.silver, rot)
    glass = getattr(N, "glass", bpy.data.materials["fidelity_living_glass"])
    for a, b in ((10.00, 11.265), (13.57, 14.825)):
        cy, width = (a + b) / 2, b - a
        _box(scene, "kitchen_glass_bank_back", (-4.995, cy, 1.793), (0.025, width, 1.65), N.walnut)
        for y in (a + 0.019, b - 0.019):
            _box(scene, "kitchen_glass_bank_side", (-4.753, y, 1.793), (0.490, 0.038, 1.65), N.grey)
        for z in (0.977, 1.384, 1.791, 2.198, 2.605):
            _box(scene, "kitchen_glass_bank_shelf", (-4.752, cy, z), (0.488, width, 0.022), N.grey)
        for leaf in range(2):
            centre = a + (leaf + 0.5) * width / 2
            pane = _box(scene, "kitchen_glass_door_pane", (-4.492, centre, 1.790), (0.004, width / 2 - 0.055, 1.600), glass, bevel=0)
            pane["homespec"] = "part"
            for y in (centre - width / 4 + 0.016, centre, centre + width / 4 - 0.016):
                _box(scene, "kitchen_glass_door_stile", (-4.475, y, 1.790), (0.034, 0.027 if y == centre else 0.032, 1.650), N.grey)
            for z in (0.980, 1.385, 1.790, 2.195, 2.600):
                _box(scene, "kitchen_glass_door_rail", (-4.475, centre, z), (0.034, width / 2 - 0.010, 0.025), N.grey)
            scene.sphere("kitchen_glass_door_small_knob", (-4.445, centre + (0.25 if leaf == 0 else -0.25), 1.055), 0.011, N.silver)
        for shelf, z in enumerate((0.990, 1.397, 1.804, 2.211)):
            for i in range(5):
                J.goblet(scene, "kitchen_display_crystal", (-4.73 - 0.035 * (i % 2), a + 0.14 + i * (width - 0.28) / 4, z), 0.13 + 0.014 * (i % 3), glass, stemmed=shelf in (1, 3))
    # Shallow wood shelf transitions flank the retained central extractor.
    for a, b in ((11.275, 11.735), (13.105, 13.56)):
        _box(scene, "kitchen_hood_side_open_back", (-4.996, (a + b) / 2, 1.975), (0.023, b - a, 1.300), N.walnut)
        for z in (1.51, 1.95, 2.39):
            _box(scene, "kitchen_hood_side_open_shelf", (-4.77, (a + b) / 2, z), (0.470, b - a, 0.030), N.walnut)
            J.goblet(scene, "kitchen_shelf_small_glass", (-4.76, (a + b) / 2, z + 0.017), 0.13, glass)
    _box(scene, "kitchen_hood_timber_shell", (-4.75, 12.42, 2.13), (0.560, 1.390, 0.990), N.walnut)
    _panel(scene, "kitchen_hood_painted_front", (-4.458, 12.42, 2.130), 1.330, 0.950, N.grey, rot)
    _box(scene, "kitchen_hood_canopy_lip", (-4.70, 12.42, 1.629), (0.660, 1.440, 0.040), N.walnut)
    for a, b, dz in ((south, tall_end, 0.046), (tall_end, 14.84, 0)):
        for z, depth, height in ((2.638, 0.620, 0.028), (2.670, 0.657, 0.030), (2.698, 0.682, 0.023)):
            _box(scene, "kitchen_crown_contoured_member", (-5.006 + depth / 2, (a + b) / 2, z + dz), (depth, b - a, height), N.grey, bevel=0.004)
    grille_paths = []
    for a, b in ((south + 0.08, tall_end - 0.08), (10.08, 11.17)):
        cells = round((b - a) / 0.055)
        for i in range(cells):
            y = a + i * (b - a) / cells
            end = a + (i + 1) * (b - a) / cells
            grille_paths.extend([[(0, y, 0.034), (0, end, 0.101)], [(0, y, 0.101), (0, end, 0.034)]])
    S.curves(scene, "kitchen_plinth_diamond_grille", grille_paths, 0.0032, N.grey, at=(-4.404, 0, 0))


def apply(scene, N):
    _wall_cabinets(scene, N)
    _island(scene, N)
    _tap_and_board(scene, N)
    scene.scene["flechon_kitchen_joinery_evidence"] = "Photo00/10/35/54; narrow three-door south tower, glazed pairs, north coffee counter, continuous 25 mm stone, hollow sink/cabinet"
    scene.scene["flechon_kitchen_top_bounds_m"] = list(TOP_BOUNDS)
    scene.scene["flechon_kitchen_cabinet_body_bounds_m"] = [-3.135, -2.125, BODY_SOUTH, 13.77]
    scene.scene["flechon_kitchen_south_seating_extension_m"] = BODY_SOUTH - TOP_BOUNDS[2]
    scene.scene["flechon_kitchen_sink_clear_volume_m"] = [-2.96, -2.40, 12.01, 12.66, 0.75, 0.95]
