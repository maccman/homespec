"""Plan-derived service rooms and restrained circulation-area dressing.

No photographs show the laundry, WC or the upper landing. The fixtures below
are explicitly inferred at everyday scale, using the photographed house's
limestone, aged oak, black fittings and warm linen. Their placement follows
the actual IR outlines and leaves the full published door approaches clear.
"""
from __future__ import annotations

import importlib.util
import math
import os
from types import SimpleNamespace

import bpy
from mathutils import Vector

_SPEC = importlib.util.spec_from_file_location("flechon_service_furniture", os.path.join(os.path.dirname(__file__), "furnishings.py"))
F = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(F)

# The two compact rooms use the P_SERV inside frame, measured from its west end.
_ORIGIN = Vector((-6.6263387, 26.0555688, 0))
_U = Vector((0.9548, -0.2973, 0))
_N = Vector((0.2973, 0.9548, 0))


def position(s, n, z):
    return tuple(_ORIGIN + _U * s + _N * n + Vector((0, 0, z)))


def direction(ds, dn, dz):
    return tuple((_U * ds + _N * dn + Vector((0, 0, dz))).normalized())


SHOTS = [
    (position(1.82, -1.03, 1.06), direction(-1.35, 0.395, -0.46), 0.60),
    (position(3.44, -0.18, 1.12), direction(-1.105, -0.207, -0.57), 0.60),
    ((-1.72, 22.06, 4.94), (-0.18, -0.97, -0.16), 0.55),
    ((-1.86, 25.21, 1.57), (-0.95, 0.30, -0.08), 0.55),
]
SHOT_NAMES = [
    "Laundry · plan-derived fittings",
    "Guest WC · plan-derived fittings",
    "Upper entrance gallery",
    "Guest corridor",
]


def part(ob):
    ob["homespec"] = "part"
    return ob


def materials(scene, M):
    P = SimpleNamespace(**vars(M))
    P.enamel = scene.flat("service_warm_white_appliance_enamel", (0.70, 0.69, 0.64), rough=0.28, metal=0.15)
    P.ceramic = scene.flat("service_ivory_glazed_ceramic", (0.78, 0.76, 0.69), rough=0.20)
    P.rubber = scene.flat("service_charcoal_rubber", (0.009, 0.011, 0.009), rough=0.79)
    P.chrome = scene.flat("service_burnished_chrome", (0.42, 0.43, 0.42), metal=1, rough=0.22)
    P.dark_glass = scene.flat("service_washer_tinted_glass", (0.06, 0.08, 0.071), rough=0.06, transmission=0.68)
    P.black = bpy.data.materials.get("bath_photo05_matte_black_fittings") or M.iron
    P.stone = bpy.data.materials.get("bath_carved_honed_Baux_stone") or M.limestone
    P.linen = bpy.data.materials.get("bath_warm_white_terry") or M.linen
    P.glow = scene.flat("service_opal_lamp_diffuser", (0.92, 0.80, 0.59), rough=0.31, emit=0.55)
    return P


def service_frame(scene):
    d = scene.entity("P_SERV")["derived"]["face"]
    origin = Vector((*d["origin"], 0)) / 1000
    u = Vector((*d["u"], 0))
    n = Vector((*d["n"], 0))
    return lambda s, t, z: tuple(origin + u * s + n * t + Vector((0, 0, z))), math.atan2(u.y, u.x)


def circular_face(scene, name, p, at, radius, depth, mat, rot):
    ob = scene.cyl(name, p(*at), radius, depth, mat, verts=80)
    ob.rotation_euler = (math.pi / 2, 0, rot)
    for polygon in ob.data.polygons:
        if len(polygon.vertices) > 4:
            polygon.use_smooth = False
    return ob


def laundry(scene, P, p, angle):
    """600mm appliance fits west of the900mm doorway without narrowing it."""
    # Unit face points east along P_SERV. Door approach begins at s=.803m;
    # this complete unit stops at s=.783m, including the projecting door.
    at = p(0.470, -0.635, 0)
    rot = angle + math.pi / 2
    q = F.transform(at, rot)
    scene.box("laundry_washer_body", q(0, 0, 0.424), (0.590, 0.572, 0.838), P.enamel, rot_z=rot, bevel=0.009)
    for x in (-0.237, 0.237):
        for y in (-0.232, 0.232):
            scene.cyl("laundry_washer_adjustable_foot", q(x, y, 0.018), 0.029, 0.036, P.rubber)
    scene.box("laundry_washer_control_fascia", q(0, -0.288, 0.760), (0.572, 0.014, 0.110), P.enamel, rot_z=rot, bevel=0.003)
    circular_face(scene, "laundry_washer_selector", q, (-0.01, -0.307, 0.760), 0.031, 0.017, P.chrome, rot)
    part(scene.box("laundry_washer_display", q(0.151, -0.299, 0.759), (0.117, 0.006, 0.040), P.rubber, rot_z=rot, bevel=0.003))
    part(scene.box("laundry_detergent_drawer", q(-0.181, -0.299, 0.759), (0.145, 0.010, 0.059), P.enamel, rot_z=rot, bevel=0.002))
    part(scene.box("laundry_detergent_drawer_pull", q(-0.181, -0.307, 0.755), (0.115, 0.008, 0.005), P.rubber, rot_z=rot))
    for name, radius, depth, mat in [("rubber_seal", 0.224, 0.014, P.rubber), ("chrome_bezel", 0.213, 0.018, P.chrome), ("drum_glass", 0.184, 0.018, P.dark_glass)]:
        circular_face(scene, "laundry_washer_" + name, q, (0, -0.291, 0.433), radius, depth, mat, rot)
    for i in range(3):
        a = math.tau * i / 3
        F.curve(scene, "laundry_washer_inner_drum_lifter", [q(0.136 * math.cos(a) * t, -0.276, 0.433 + 0.136 * math.sin(a) * t) for t in (0.25, 0.5, 0.75, 1)], 0.009, P.chrome)
    F.curve(scene, "laundry_washer_door_handle", [q(0.162 + 0.017 * math.sin(i * math.pi / 12), -0.311, 0.385 + i * 0.008) for i in range(13)], 0.007, P.enamel)
    scene.box("laundry_honed_stone_counter", q(0, 0.007, 0.862), (0.620, 0.586, 0.040), P.stone, rot_z=rot, bevel=0.004)
    # Shallow wall cabinetry occupies the same west strip above the appliance.
    scene.box("laundry_antique_oak_wall_cabinet", q(0, 0.100, 1.752), (0.59, 0.34, 0.70), P.oak, rot_z=rot, bevel=0.004)
    for x in (-0.148, 0.148):
        scene.box("laundry_oak_cabinet_panel", q(x, -0.081, 1.752), (0.280, 0.025, 0.666), P.oak, rot_z=rot, bevel=0.002)
        for xx in (-0.118, 0.118):
            part(scene.box("laundry_oak_cabinet_stile", q(x + xx, -0.100, 1.752), (0.021, 0.014, 0.640), P.dark_oak, rot_z=rot, bevel=0.002))
        for zz in (-0.298, 0.298):
            part(scene.box("laundry_oak_cabinet_rail", q(x, -0.101, 1.752 + zz), (0.245, 0.015, 0.031), P.dark_oak, rot_z=rot, bevel=0.002))
        scene.sphere("laundry_oak_cabinet_latch", q(x * 0.3, -0.114, 1.75), 0.008, P.black)
    # Cabinet brackets return to the west boundary, not to an invented wall.
    for x in (-0.21, 0.21):
        scene.rod("laundry_cabinet_supported_bracket", q(x, 0.258, 1.402), q(x, 0.305, 1.402), 0.012, P.black)
        scene.rod("laundry_cabinet_bracket_upright", q(x, 0.300, 1.38), q(x, 0.300, 1.73), 0.012, P.black)
    F.soft(scene, "laundry_folded_linen", q(-0.06, 0.02, 0.905), (0.35, 0.28, 0.043), P.linen, rot=rot, bevel=0.016)
    for dx in (-0.19, 0.19):
        scene.cyl("laundry_wall_shelf_jars", q(dx, 0.008, 1.195), 0.046, 0.16, P.enamel)
    scene.box("laundry_small_oak_shelf", q(0, 0.08, 1.10), (0.59, 0.27, 0.027), P.dark_oak, rot_z=rot, bevel=0.004)
    for x in (-0.21, 0.21):
        scene.rod("laundry_shelf_bracket", q(x, 0.17, 1.085), q(x, 0.30, 1.085), 0.009, P.black)
        scene.rod("laundry_shelf_bracket_return", q(x, 0.30, 1.085), q(x, 0.30, 1.33), 0.009, P.black)
    ceiling_lamp(scene, "laundry", p(1.20, -0.64, 2.945), P, 45)


def wc(scene, P, p, angle):
    # The pan occupies s2.15..2.52, west of D_WC's clear s2.553..3.453.
    at = p(2.335, -0.387, 0)
    q = F.transform(at, angle)
    F.soft(scene, "wc_pan_floor_pedestal", q(0, 0.028, 0.195), (0.248, 0.366, 0.38), P.ceramic, rot=angle, bevel=0.078)
    bowl = F.lathe(scene, "wc_glazed_ceramic_bowl", (0, 0, 0), [(0.19, 0.115), (0.27, 0.172), (0.39, 0.214), (0.414, 0.213), (0.425, 0.202), (0.417, 0.175), (0.36, 0.15), (0.265, 0.078), (0.252, 0.006)], P.ceramic, segments=80)
    bowl.location = at
    bowl.scale = (0.845, 1.25, 1)
    bowl.rotation_euler[2] = angle
    # Separate seat follows the oval rim, with a real central opening.
    F.curve(scene, "wc_ivory_toilet_seat", [q(0.171 * math.cos(a), -0.005 + 0.253 * math.sin(a), 0.434) for a in [math.tau * i / 96 for i in range(97)]], 0.014, P.ceramic)
    scene.box("wc_compact_cistern", q(0, 0.240, 0.543), (0.347, 0.168, 0.453), P.ceramic, rot_z=angle, bevel=0.036)
    scene.box("wc_cistern_lid", q(0, 0.240, 0.781), (0.357, 0.179, 0.029), P.ceramic, rot_z=angle, bevel=0.015)
    for dx, radius in ((-0.013, 0.019), (0.020, 0.013)):
        scene.cyl("wc_dual_flush_button", q(dx, 0.232, 0.798), radius, 0.005, P.chrome)
    # A narrow hand basin attaches directly to the WC's eastern partition.
    basin_at = p(3.533, -0.720, 0)
    rot = angle - math.pi / 2
    r = F.transform(basin_at, rot)
    scene.box("wc_small_oak_basin_cabinet", r(0, 0.018, 0.421), (0.360, 0.190, 0.818), P.oak, rot_z=rot, bevel=0.004)
    scene.box("wc_basin_panel_door", r(0, -0.088, 0.433), (0.327, 0.017, 0.744), P.oak, rot_z=rot, bevel=0.003)
    scene.sphere("wc_basin_brass_knob", r(0.132, -0.102, 0.453), 0.012, P.brass)
    # Closed profile stone basin with a shallow carved inner well.
    sink = F.lathe(scene, "wc_compact_honed_stone_basin", (0, 0, 0), [(0, 0.145), (0.057, 0.177), (0.073, 0.181), (0.077, 0.164), (0.050, 0.134), (0.023, 0.085), (0.016, 0)], P.stone, segments=64)
    sink.location = r(0, 0.0, 0.84)
    sink.scale = (1.03, 0.63, 1)
    sink.rotation_euler[2] = rot
    scene.rod("wc_black_basin_tap", r(0, 0.070, 0.858), r(0, 0.070, 1.061), 0.009, P.black)
    scene.rod("wc_black_basin_spout", r(0, 0.07, 1.057), r(0, -0.025, 1.057), 0.009, P.black)
    scene.box("wc_small_oak_mirror_frame", r(0, 0.091, 1.453), (0.335, 0.029, 0.620), P.dark_oak, rot_z=rot, bevel=0.004)
    mirror_mat = bpy.data.materials.get("interior_true_mirror")
    if mirror_mat:
        scene.box("wc_mirror_silver", r(0, 0.071, 1.453), (0.293, 0.008, 0.576), mirror_mat, rot_z=rot)
    # A low paper holder occupies the pan's western side, outside its approach.
    scene.rod("wc_paper_holder_arm", p(2.137, -0.412, 0.610), p(2.225, -0.412, 0.610), 0.007, P.black)
    roll = scene.cyl("wc_paper_roll", p(2.190, -0.412, 0.61), 0.052, 0.087, P.linen, verts=48)
    roll.rotation_euler[1] = math.pi / 2
    roll.rotation_euler[2] = angle
    ceiling_lamp(scene, "wc", p(2.94, -0.65, 2.945), P, 35)


def ceiling_lamp(scene, name, at, P, watts):
    # The restored beams project beneath the nominal ceiling plane. Attach
    # the mount to the first real soffit above its position, including beams.
    bpy.context.view_layer.update()
    hit, location, *_ = scene.scene.ray_cast(
        bpy.context.evaluated_depsgraph_get(),
        Vector((at[0], at[1], at[2] - 1.5)), Vector((0, 0, 1)), distance=4,
    )
    if hit:
        at = (at[0], at[1], location.z - 0.025)
    scene.cyl(name + "_ceiling_brass_mount", (at[0], at[1], at[2] + 0.007), 0.105, 0.03, P.brass, verts=64)
    F.lathe(scene, name + "_opal_ceiling_light", at, [(-0.086, 0.028), (-0.073, 0.082), (-0.033, 0.123), (0, 0.105)], P.glow, segments=64)
    # An area source represents the illuminated underside of the opal shade.
    # Its plane must be outside the opaque housing for light to reach the room.
    data = bpy.data.lights.new(name + "_ceiling_practical", "AREA")
    data.shape = "DISK"
    data.size = 0.19
    data.energy = watts
    data.color = (1.0, 0.84, 0.66)
    data.specular_factor = 0
    ob = bpy.data.objects.new(name + "_ceiling_practical", data)
    scene.link(ob)
    ob.location = (at[0], at[1], at[2] - 0.091)
    ob.visible_glossy = False
    ob.visible_camera = False
    ob.visible_transmission = False


def circulation(scene, P):
    # Circulation remains furnished sparingly; both ledgers mark it unphotographed.
    wall = scene.entity("A1")["derived"]["face"]
    o = Vector((*wall["origin"], 0)) / 1000
    u = Vector((*wall["u"], 0))
    n = Vector((*wall["n"], 0))
    # A shallow coat rail on the solid pier before the corridor's existing window, not a bulky console.
    at = o + u * 0.40 + n * 0.036 + Vector((0, 0, 1.79))
    rot = math.atan2(u.y, u.x)
    scene.box("guest_corridor_oak_coat_rail", tuple(at), (0.64, 0.025, 0.082), P.oak, rot_z=rot, bevel=0.004)
    for i in range(4):
        c = at + u * (-0.24 + i * 0.16)
        scene.rod("guest_corridor_forged_coat_hook", tuple(c), tuple(c + n * 0.035 + Vector((0, 0, 0.02))), 0.006, P.black)
    # Light the windowless west end from a genuine surface-mounted practical.
    ceiling_lamp(scene, "guest_corridor", (-4.53, 26.04, 2.945), P, 32)
    # Above the stair landing, the gallery and glazing provide the architecture;
    # nothing occupies the measured narrow floor bridge or stair arrival.
    ceiling_lamp(scene, "upper_gallery", (-2.55, 20.01, 6.445), P, 42)
    # A small fixed bronze reading sconce on the north wall offers human-scale detail.
    wall = scene.entity("H2")["derived"]["face"]
    o = Vector((*wall["origin"], 0)) / 1000
    u = Vector((*wall["u"], 0))
    n = Vector((*wall["n"], 0))
    at = o + u * 0.72 + n * 0.027 + Vector((0, 0, 5.16))
    rot = math.atan2(u.y, u.x)
    part(scene.box("upper_gallery_sconce_backplate", tuple(at), (0.095, 0.031, 0.145), P.brass, rot_z=rot, bevel=0.006))
    stem = at + n * 0.08
    scene.rod("upper_gallery_sconce_arm", tuple(at), tuple(stem), 0.009, P.brass)
    scene.cone("upper_gallery_linen_sconce", tuple(stem + Vector((0, 0, -0.074))), 0.089, 0.065, 0.17, P.glow)
    scene.point_light("upper_gallery_sconce_practical", tuple(stem + Vector((0, 0, -0.173))), 9, color=(1, 0.77, 0.51), radius=0.020)


def apply(scene, M):
    P = materials(scene, M)
    p, angle = service_frame(scene)
    laundry(scene, P, p, angle)
    wc(scene, P, p, angle)
    circulation(scene, P)
    scene.scene["flechon_service_room_reference_note"] = "Laundry, WC and circulation furnishings inferred from plan only; these spaces have no supplied interior photographs."
