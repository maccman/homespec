"""Lights and sky."""
from __future__ import annotations

import math
import os

import bpy
import session
from mathutils import Vector


class Lighting:
    """Mixed into :class:`Scene`."""

    def point_light(self, name, loc, energy, color=(1, 0.85, 0.7), radius=0.15, reflect=False):
        light = bpy.data.lights.new(name, 'POINT')
        light.energy = energy
        light.color = color
        light.shadow_soft_size = radius
        o = bpy.data.objects.new(name, light)
        session.scn.collection.objects.link(o)
        o.location = loc
        o.visible_glossy = reflect
        return o

    def sun(self, direction, energy=5.0, angle=0.8):
        s = bpy.data.lights.new("sun", 'SUN')
        s.energy = energy
        s.angle = math.radians(angle)
        o = bpy.data.objects.new("sun", s)
        session.scn.collection.objects.link(o)
        o.rotation_euler = Vector(direction).to_track_quat('-Z', 'Y').to_euler()
        o.visible_camera = False
        return o

    def world_hdri(self, path, rotation_deg=0.0, strength=1.0):
        world = bpy.data.worlds.new("world")
        session.scn.world = world
        world.use_nodes = True
        nt = world.node_tree
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(os.path.abspath(path))
        mp = nt.nodes.new("ShaderNodeMapping")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp.inputs["Rotation"].default_value[2] = math.radians(rotation_deg)
        nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
        bg = nt.nodes["Background"]
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = strength
