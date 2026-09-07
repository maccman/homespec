"""Render visibility across Blender's collection DAG and enabled view layers.

Duck-typed and independent of bpy so ancestor/multiple-link behavior is testable.
Viewport-only hide flags do not determine the source render's asset scope.
"""

from collections import defaultdict


def render_visibility(scene):
    paths = defaultdict(list)

    def visit(layer, view_name, ancestors=(), parent_visible=True):
        collection = layer.collection
        path = (*ancestors, collection.name)
        visible = parent_visible and not collection.hide_render and not layer.exclude
        for obj in collection.objects:
            paths[obj.name].append({"view_layer": view_name, "collections": list(path), "visible": visible})
        for child in layer.children:
            visit(child, view_name, path, visible)

    for layer in scene.view_layers:
        if layer.use:
            visit(layer.layer_collection, layer.name)
    return {
        obj.name: {
            "effective_hidden_render": obj.hide_render or not any(path["visible"] for path in paths[obj.name]),
            "render_collection_paths": paths[obj.name],
        }
        for obj in scene.objects
    }
