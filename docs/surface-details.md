# Host surfaces, room finishes and physical trim

A feature has one architectural host. Decorative generators read the compiled
surface instead of repeating a footprint, pitch, room height or opening size.
All IR frames and coordinates are millimetres; Blender options are metres.

`SlabGeometry.top_surface` is measured from the completed CAD top faces after
cuts. `WallGeometry.surfaces`, wall infills and `RoofGeometry.surfaces` publish
their final planar faces. `PlanarSurface` stores a validated right-handed
`SurfaceFrame`, local vertices and CCW triangles. This preserves concave outlines,
separate islands, stairs/skylights and openings. IR serialization retains nine
decimal places so direction vectors survive a typed round trip.

Inside Blender:

```python
from surfaces import floor_courses, cover_surface

floor_courses(scene, "floor", [limestone_a, limestone_b],
              module=(.4, .8), joint=.003, thickness=.003,
              bed=.001, grout=mortar, bevel=.0003, relief=.0002)

for i, surface in enumerate(scene.entity("wall")["derived"]["surfaces"]):
    if surface["role"] == "outside":
        cover_surface(scene, surface, [stone], name=f"facade_{i}",
                      module=(.45, .22), joint=.012, thickness=.025,
                      bed=.01, grout=mortar, bevel=.001)

for i, surface in enumerate(scene.entity("roof")["derived"]["surfaces"]):
    if surface["role"] == "roof_top":
        cover_surface(scene, surface, [tile], name=f"roof_tiles_{i}",
                      module=(.25, .4), thickness=.02, bed=0,
                      joint=.004, bevel=.001)
```

`module` is pitch including the joint. The origin defaults to the surface's
grid-space minimum; `angle` rotates courses within its plane in radians.
Variation uses host, seed, row and column identity. Adding unrelated objects
cannot shuffle it. Relief lowers each top within the declared thickness;
bevels cannot exceed half its remaining thickness. Each piece keeps its host,
surface role and course identity. Pieces are presentation details, not individual
BIM entities. Real joints and relief are geometry; the pigment texture cannot
create them. UVs are in surface metres, independent of material repeat size.

`detail="coarse"` preserves the same outline and holes with one flat covering.
The default full detail has an explicit `max_courses` budget and rejects
non-finite or impossible dimensions. This generator makes flat planks, flags,
stone courses and tiles. Profiled canal tiles, edge erosion and construction
overlaps remain project generators; they should consume the same surface facts.
Courses on separate faces currently start their grids separately. Continuity
across an unfolded corner requires an explicitly shared grid origin/phase.

## Material-only room finishes

`RoomFinish` extends the existing constructor DSL:

```python
RoomFinish("kitchen.paint", room="kitchen", hosts=["shared_wall"],
           material="cream_plaster", role="room")
```

The room supplies its actual polygon and vertical extent. The host includes
declared `WallToRoofInfill` attachments by default. Assembly `finish_in/out` and
entity material establish the base slots; room finishes apply after them in
declaration order. An overlap therefore has explicit last-declaration precedence.
Roles `inside`/`outside` select the corresponding wall face, `reveal` selects
only the room's half of opening reveals, and `room` includes the room-facing wall
and its half-reveals. `all` also supports non-wall members within the room.
The finish does not alter wall thickness or quantity schedules.

Generated Blender materials use the same rule without a spec-only material:

```python
from finishes import room_finish
room_finish(scene, ["shared_wall"], "kitchen", generated_plaster)
room_finish(scene, ["shared_beam"], "living", oak,
            preserve_materials=["sawn_endgrain"])
```

Faces are split at room boundary and storey planes before selection. BMesh
interpolates the existing UVs, the material slots of other faces are retained,
and shared meshes detach before edits. Finish selection requires declared
room boundaries and wall frames. Generic roof gables without a wall attachment
are not silently guessed to belong to a nearby wall. Reveal selection currently
supports declared rectangular, circular, semicircular and segmental apertures
in prismatic wall bodies, with 2 mm tolerance for curved mesh tessellation.
Ordinary roof-limited or boolean-cut wall tops are not opening reveals. It is not a general
semantic classifier for arbitrary sculpted walls. Standard room height remains
the vertical scope; an inferred paint line above it must be declared as distinct
project evidence, not hidden in a shader mask.

`BeamGeometry.member` and square `ColumnGeometry.member` publish real member
frames. The origin is the centre of the start cross-section, longitudinal
coordinates run from zero to length, and across/normal coordinates are centred.
Clipped ceiling beams retain their member origin so grain phase stays continuous.
Use [material assets](material-assets.md) for metre grain and explicit endgrain.
No project truss is reconstructed from guessed global coordinates by this API.

## Physical skirting and tread clearance

For trim that belongs in CAD, quantities and IFC, declare a single covering:

```python
Skirting("room.skirting", room="room", floor="floor",
         openings=["door", "low_window"], height=100, depth=20,
         base=2, material="stone")
```

Its ring is mitered against the room's `bounded_by` wall frames and clipped to
the structural floor's actual footprint. Named opening dependencies reuse exact
cutters, including curved profiles; exact end-cap extensions cut through the full
trim depth and raised thresholds retain trim below the void.
The result is one `IfcCovering`, not one entity per decorative block. All openings
crossing the trim band must be listed. The floor and opening hosts must finish
their cuts before this dependent trim realizes. Skirting cannot infer an omitted
door from a photograph. The legacy kitchen presentation skirting remains local;
its floor courses and wall finishes now use the shared APIs.

`homespec.clearance.TreadZone` provides an actual tread/approach outline, walking
elevation, name and optional tread identity. `tread_clearance` checks every zone
against completed physical solids and returns typed obstructions, positions,
minimum and checked height. Both core straight stairs and Bastide's local
winder/spiral adapters use it. A clear result certifies only the finite checked
vertical envelope. It does not certify a continuous escape route, handrails or a
moving body's swept volume. Empty/collapsed zones fail rather than disappearing
from coverage.

Independent fixtures cover concavity, holes, skew faces, exact door-cut trim,
frame serialization, manifold Blender courses, material/UV isolation and winder
clearance. The diagnostic surface image produced by `test_blender_surfaces.py`
is a reusable small review artifact; it is not a Bastide fidelity assessment.
