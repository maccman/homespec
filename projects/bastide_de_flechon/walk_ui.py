"""A small Blender navigation panel for the Bastide walkthrough.

Loaded explicitly by Walk Bastide.command, never by automatic script execution.
"""

import contextlib
import json

import bpy
from mathutils import Vector


class FLECHON_OT_view(bpy.types.Operator):
    bl_idname = "flechon.view"
    bl_label = "Go to this room"
    index: bpy.props.IntProperty(default=0)

    def execute(self, context):
        points = json.loads(context.scene.get("flechon_waypoints", "[]"))
        p = points[self.index]
        cam = context.scene.camera
        cam.animation_data_clear()
        cam.location = p["location"]
        cam.rotation_euler = Vector(p["look"]).to_track_quat("-Z", "Y").to_euler()
        context.scene.view_settings.exposure = p.get("exposure", 0)
        if context.area and context.area.type == "VIEW_3D":
            context.space_data.region_3d.view_perspective = "CAMERA"
        context.scene["current_room"] = p["name"]
        return {"FINISHED"}


class FLECHON_OT_walk(bpy.types.Operator):
    bl_idname = "flechon.walk"
    bl_label = "Walk from here"

    def execute(self, context):
        # Navigation must be invoked over the view's WINDOW region, not sidebar.
        region = next(r for r in context.area.regions if r.type == "WINDOW")
        with context.temp_override(region=region):
            bpy.ops.view3d.walk("INVOKE_DEFAULT")
        return {"FINISHED"}


class FLECHON_PT_navigation(bpy.types.Panel):
    bl_label = "La Bastide de Flechon"
    bl_idname = "FLECHON_PT_navigation"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Flechon"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Explore the house", icon="HOME")
        layout.operator("flechon.walk", icon="VIEW_PAN")
        layout.label(text="W / A / S / D: move. Mouse: look.")
        layout.label(text="E / Q: up / down. Shift: faster.")
        layout.label(text="Click: stop. Esc: cancel. Tab: gravity.")
        layout.separator()
        points = json.loads(context.scene.get("flechon_waypoints", "[]"))
        for i, p in enumerate(points):
            op = layout.operator("flechon.view", text=p["name"], icon="CAMERA_DATA")
            op.index = i
        layout.separator()
        layout.prop(context.scene.render, "engine", text="Renderer")
        layout.prop(context.scene.view_settings, "exposure")
        layout.label(text="Plan-led reconstruction from supplied photos.")


for cls in (FLECHON_OT_view, FLECHON_OT_walk, FLECHON_PT_navigation):
    with contextlib.suppress(ValueError):
        bpy.utils.register_class(cls)
prefs = bpy.context.preferences
prefs.inputs.navigation_mode = "WALK"
prefs.inputs.walk_navigation.mouse_speed = 0.8
prefs.inputs.walk_navigation.walk_speed = 2.0
prefs.inputs.walk_navigation.view_height = 1.65
prefs.inputs.walk_navigation.use_gravity = False
try:
    cycles = prefs.addons["cycles"].preferences
    cycles.compute_device_type = "METAL"
    cycles.get_devices()
    for device in cycles.devices:
        device.use = device.type == "METAL"
    bpy.context.scene.cycles.device = "GPU"
except (TypeError, AttributeError):
    bpy.context.scene.cycles.device = "CPU"
bpy.context.scene.cycles.preview_samples = 32
bpy.context.scene.cycles.use_preview_denoising = True
wm = bpy.context.window_manager
if wm.keyconfigs.addon:
    km = wm.keyconfigs.addon.keymaps.new(name="3D View", space_type="VIEW_3D")
    km.keymap_items.new("view3d.walk", "W", "PRESS")
    km.keymap_items.new("view3d.walk", "ACCENT_GRAVE", "PRESS")


def setup():
    for win in wm.windows:
        for area in win.screen.areas:
            if area.type != "VIEW_3D":
                continue
            sp = area.spaces.active
            sp.shading.type = "RENDERED"
            sp.overlay.show_overlays = False
            sp.show_gizmo = False
            sp.show_region_ui = True
            sp.lens = 24
            sp.clip_start = 0.03
            sp.clip_end = 400
            sp.region_3d.view_perspective = "CAMERA"
            sp.region_3d.view_camera_zoom = 0
            for region in area.regions:
                if region.type == "UI":
                    with contextlib.suppress(AttributeError, TypeError):
                        region.active_panel_category = "Flechon"
            region = next(r for r in area.regions if r.type == "WINDOW")
            with bpy.context.temp_override(window=win, area=area, region=region):
                bpy.ops.flechon.view(index=bpy.context.scene.get("walk_start_index", 0))
                # Give the walk the whole window while retaining the room sidebar.
                if not win.screen.show_fullscreen:
                    bpy.ops.screen.screen_full_area(use_hide_panels=False)
            return None
    return 0.5


bpy.app.timers.register(setup, first_interval=1)
print("FLECHON WALK READY: W to walk, N for room navigation.")
