"""Open a walk file in the Blender GUI ready to explore.

    blender out/<project>/house_walk.blend --python homespec/blender/walk.py -- [cycles|eevee]

W or backtick starts walk navigation from anywhere in the 3D view (W is also
forward once walking). The viewport renders with Cycles by default so it
matches the stills; pass ``eevee`` for a smooth but flatter preview.
"""
import sys

import bpy

engine = "cycles"
if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1:
    engine = sys.argv[sys.argv.index("--") + 1]

wm = bpy.context.window_manager
kc = wm.keyconfigs.addon
if kc:
    km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
    km.keymap_items.new('view3d.walk', 'W', 'PRESS')
    km.keymap_items.new('view3d.walk', 'ACCENT_GRAVE', 'PRESS')
prefs = bpy.context.preferences
prefs.inputs.navigation_mode = 'WALK'
prefs.inputs.walk_navigation.mouse_speed = 1.0
prefs.inputs.walk_navigation.walk_speed = 2.5
prefs.inputs.walk_navigation.view_height = 1.6

scn = bpy.context.scene
if engine == "cycles":
    p = prefs.addons['cycles'].preferences
    p.compute_device_type = 'METAL'
    p.get_devices()
    for d in p.devices:
        d.use = (d.type == 'METAL')
    scn.render.engine = 'CYCLES'
    scn.cycles.device = 'GPU'
    scn.cycles.preview_samples = 48
    scn.cycles.use_preview_denoising = True
    scn.cycles.preview_denoiser = 'OPENIMAGEDENOISE'
    scn.cycles.preview_denoising_start_sample = 2
    scn.cycles.preview_adaptive_threshold = 0.2
    try:
        scn.render.preview_pixel_size = '2'
    except Exception as e:  # noqa: BLE001
        print("pixel size:", e)
else:
    scn.render.engine = 'BLENDER_EEVEE'


def setup():
    for win in wm.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                sp = area.spaces.active
                sp.shading.type = 'RENDERED'
                sp.overlay.show_overlays = False
                sp.show_gizmo = False
                sp.lens = 24
                sp.clip_start = 0.05
                region = [r for r in area.regions if r.type == 'WINDOW'][0]
                with bpy.context.temp_override(window=win, area=area, region=region):
                    bpy.ops.view3d.view_camera()
                    bpy.ops.screen.screen_full_area(use_hide_panels=True)
                return None
    return 0.5


bpy.app.timers.register(setup, first_interval=1.0)
