"""glTF assets from the library, placed by their bounding-box bottom centre and instanced."""
from __future__ import annotations

import glob

import bpy
import session
from materials import tinted
from mathutils import Matrix, Vector


class Models:
    """Mixed into :class:`Scene`."""

    _models: dict = {}

    def model(self, asset: str, loc, rot_z=0.0, scale=1.0, height=None, tint=None):
        """Place a glTF asset by id with its bounding-box bottom centre at ``loc``.

        The first use imports and merges the asset; later uses are linked
        duplicates sharing the same mesh, so a grove of trees costs one tree.
        ``height`` rescales uniformly to that height in metres. ``tint``
        multiplies every material's colour, so one chair model can be painted
        black, grey or white: each tint is its own shared mesh.
        """
        key = asset if tint is None else f"{asset}@{','.join(f'{c:.2f}' for c in tint)}"
        base = self._models.get(key)
        if base is None:
            base = self._import(asset)
            if base is None:
                return None
            if tint is not None:
                base.data = base.data.copy()
                base.name = key
                base.data.materials.clear()
                for m in self._import_materials(asset):
                    base.data.materials.append(tinted(m, tint, key))
            self._models[key] = base
            o = base
        else:
            o = base.copy()
            o.data = base.data
            session.scn.collection.objects.link(o)
            o.name = f"{asset}.{len([x for x in bpy.data.objects if x.name.startswith(asset)])}"
        if height:
            scale = height / base["homespec_height"]
        o.scale = (scale,) * 3
        o.rotation_euler = (0.0, 0.0, rot_z)
        o.location = loc
        return o

    def _import_materials(self, asset: str):
        src = self._models.get(asset)
        if src is None:
            src = self._import(asset)
            self._models[asset] = src
            src.hide_render = src.hide_viewport = True     # the untinted original stays as a hidden template
            src.location = (0.0, 0.0, -50.0)
        return list(src.data.materials)

    def _import(self, asset: str):
        files = glob.glob(f"{session.ASSETS}/models/{asset}/*.gltf") + glob.glob(f"{session.ASSETS}/models/{asset}/*.glb")
        if not files:
            print("MISSING MODEL", asset)
            return None
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=files[0])
        new = [o for o in bpy.data.objects if o not in before]
        mesh_names = [o.name for o in new if o.type == 'MESH']
        other = [o.name for o in new if o.type != 'MESH']
        bpy.ops.object.select_all(action='DESELECT')
        for n in mesh_names:
            bpy.data.objects[n].parent = None
            bpy.data.objects[n].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[mesh_names[0]]
        if len(mesh_names) > 1:
            bpy.ops.object.join()
        o = bpy.context.view_layer.objects.active
        o.name = asset
        for n in other:
            if n in bpy.data.objects:
                bpy.data.objects.remove(bpy.data.objects[n])
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bb = [Vector(c) for c in o.bound_box]
        lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        ctr = (lo + hi) / 2
        o.data.transform(Matrix.Translation((-ctr.x, -ctr.y, -lo.z)))
        o["homespec_height"] = float(hi.z - lo.z)
        return o
