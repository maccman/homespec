"""Project-local equivalents of Scene primitives without UI operators.

Thousands of garden/furniture parts make Blender's operator-driven primitive
creation expensive: each operator evaluates the growing dependency graph.
These factories create identical-sized meshes through the data API. They keep
the core primitives' material slots, names, object tags and bevel parameters;
the normal homespec design audit still evaluates every placed object.
"""
from __future__ import annotations

import math

import bpy
from mathutils import Vector


def install(scene):
    cache = {}

    def mesh(key, name, verts, faces, material, smooth=False):
        cached = cache.get(key)
        if cached is not None:
            return cached
        data = bpy.data.meshes.new(name)
        data.from_pydata(verts, [], faces)
        data.materials.append(material)
        if smooth:
            for poly in data.polygons:
                poly.use_smooth = True
        data.update()
        cache[key] = data
        return data

    def obj(name, data, loc, tag):
        o = bpy.data.objects.new(name, data)
        scene.link(o)
        o.location = loc
        o["homespec"] = tag
        return o

    def box(name, loc, size, m, rot_z=0.0, bevel=0.0):
        sx, sy, sz = (v / 2 for v in size)
        verts = [(-sx,-sy,-sz), (sx,-sy,-sz), (sx,sy,-sz), (-sx,sy,-sz),
                 (-sx,-sy,sz), (sx,-sy,sz), (sx,sy,sz), (-sx,sy,sz)]
        faces = [(3,2,1,0), (4,5,6,7), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)]
        data = mesh(("box",tuple(size),m.name,bool(bevel)), name, verts, faces, m, smooth=bool(bevel))
        o = obj(name,data,loc,"primitive")
        o.rotation_euler[2] = rot_z
        if bevel:
            mod = o.modifiers.new("bevel", 'BEVEL')
            mod.width = bevel
            mod.segments = 4
        return o

    def rings_mesh(name, r_bottom, r_top, h, verts, m, open_ends, key):
        points = []
        for r,z in [(r_bottom,-h/2),(r_top,h/2)]:
            points += [(r*math.cos(i*math.tau/verts),r*math.sin(i*math.tau/verts),z) for i in range(verts)]
        faces = [(i,(i+1)%verts,(i+1)%verts+verts,i+verts) for i in range(verts)]
        if not open_ends:
            faces += [tuple(reversed(range(verts))),tuple(range(verts,2*verts))]
        return mesh(key,name,points,faces,m,smooth=True)

    def cyl(name, loc, r, h, m, verts=32):
        data = rings_mesh(name,r,r,h,verts,m,False,("cylinder",r,h,verts,m.name))
        return obj(name,data,loc,"part")

    def cone(name, loc, r_bottom, r_top, h, m, verts=48, open_ends=True):
        data = rings_mesh(name,r_bottom,r_top,h,verts,m,open_ends,("cone",r_bottom,r_top,h,verts,open_ends,m.name))
        return obj(name,data,(loc[0],loc[1],loc[2]+h/2),"part")

    def sphere(name, loc, r, m):
        key = ("sphere",r,m.name)
        data = cache.get(key)
        if data is None:
            segments, rings = 24, 12
            points = [(0,0,r)]
            for j in range(1,rings):
                phi = math.pi*j/rings
                points += [(r*math.sin(phi)*math.cos(i*math.tau/segments),
                            r*math.sin(phi)*math.sin(i*math.tau/segments),r*math.cos(phi)) for i in range(segments)]
            bottom = len(points)
            points.append((0,0,-r))
            faces = [(0,1+i,1+(i+1)%segments) for i in range(segments)]
            for j in range(rings-2):
                a,b = 1+j*segments,1+(j+1)*segments
                faces += [(a+i,b+i,b+(i+1)%segments,a+(i+1)%segments) for i in range(segments)]
            a=1+(rings-2)*segments
            faces += [(a+i,bottom,a+(i+1)%segments) for i in range(segments)]
            data = mesh(key,name,points,faces,m,smooth=True)
        return obj(name,data,loc,"part")

    def blob(name, loc, r, m, noise=0.18, seed=0, scale_z=0.85):
        import bmesh
        from mathutils import noise as N
        key = ("blob",r,m.name,noise,seed)
        data = cache.get(key)
        if data is None:
            bm = bmesh.new()
            bmesh.ops.create_icosphere(bm,subdivisions=3,radius=r)
            offset = Vector((seed*7.3,seed*3.1,seed*5.7))
            for v in bm.verts:
                v.co *= 1.0+noise*N.noise((v.co/r)*2.2+offset)
            data = bpy.data.meshes.new(name)
            bm.to_mesh(data)
            bm.free()
            data.materials.append(m)
            for p in data.polygons:
                p.use_smooth = True
            cache[key] = data
        o = obj(name,data,loc,"plant")
        o.scale = (1.0,1.0,scale_z)
        return o

    scene.box = box
    scene.cyl = cyl
    scene.cone = cone
    scene.sphere = sphere
    scene.blob = blob
