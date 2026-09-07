"""Collection-level exclusion must not leak alternate source staging into export."""

import unittest
from types import SimpleNamespace as NS

from render_visibility import render_visibility


def collection(name, objects=(), children=(), hidden=False, excluded=False):
    return NS(collection=NS(name=name, objects=objects, hide_render=hidden), children=children, exclude=excluded)


def layer(root, enabled=True, name="ViewLayer"):
    return NS(name=name, use=enabled, layer_collection=root)


class RenderVisibility(unittest.TestCase):
    def test_hidden_collection_hides_visible_objects(self):
        obj = NS(name="alternate flower", hide_render=False)
        alternate = collection("Alternate", [obj], hidden=True)
        scene = NS(objects=[obj], view_layers=[layer(collection("Root", children=[alternate]))])
        self.assertTrue(render_visibility(scene)[obj.name]["effective_hidden_render"])

    def test_hidden_ancestor_cannot_be_overridden_by_child(self):
        obj = NS(name="flower", hide_render=False)
        child = collection("Child", [obj])
        scene = NS(objects=[obj], view_layers=[layer(collection("Hidden root", children=[child], hidden=True))])
        self.assertTrue(render_visibility(scene)[obj.name]["effective_hidden_render"])

    def test_visible_second_link_keeps_object(self):
        obj = NS(name="shared asset", hide_render=False)
        root = collection("Root", children=[collection("Hidden", [obj], hidden=True), collection("Visible", [obj])])
        result = render_visibility(NS(objects=[obj], view_layers=[layer(root)]))[obj.name]
        self.assertFalse(result["effective_hidden_render"])
        self.assertEqual(len(result["render_collection_paths"]), 2)

    def test_excluded_layer_path_and_disabled_view_layer_do_not_render(self):
        obj = NS(name="asset", hide_render=False)
        layers = [layer(collection("Excluded", [obj], excluded=True)), layer(collection("Disabled", [obj]), enabled=False)]
        self.assertTrue(render_visibility(NS(objects=[obj], view_layers=layers))[obj.name]["effective_hidden_render"])

    def test_second_enabled_view_layer_may_render(self):
        obj = NS(name="asset", hide_render=False)
        layers = [layer(collection("Excluded", [obj], excluded=True)), layer(collection("Visible", [obj]), name="Second")]
        self.assertFalse(render_visibility(NS(objects=[obj], view_layers=layers))[obj.name]["effective_hidden_render"])

    def test_object_hidden_remains_hidden_when_collection_visible(self):
        obj = NS(name="hidden object", hide_render=True)
        self.assertTrue(render_visibility(NS(objects=[obj], view_layers=[layer(collection("Root", [obj]))]))[obj.name]["effective_hidden_render"])


if __name__ == "__main__":
    unittest.main()
