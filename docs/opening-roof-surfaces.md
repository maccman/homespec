# Shared opening profiles and roof surfaces

`OpeningProfile` is a constructor value on the existing `Window`, `Door` and
`Arch` vocabulary. Dimensions remain millimetres and positioning remains an
offset on the host wall. A profile is published in `OpeningGeometry` and is
used for the exact CAD cutter, concentric frame/glass and a matching `Surround`.

```python
Window("oculus", host="wall", width=900, height=900, sill=2600,
       profile=OpeningProfile(shape="circular"))
Door("garden", host="wall", width=2200, height=2440, glazed=True,
     profile=OpeningProfile(shape="segmental", rise=360))
Surround("garden.stone", opening="garden", material="limestone", jamb=180)
```

Supported shapes are rectangular, semicircular, segmental and circular.
Explicit profiles use **overall envelope height**. Existing `Arch` and
`ArchedDoor` without an explicit profile retain their springing-height
convention. A segmental rise must be positive and at most half the width;
circular openings require equal width and height. Nested values reject
non-finite dimensions. Curved surround bands use `jamb` as their radial width;
`lintel` retains its rectangular-head meaning. `embed` controls how far the
surround extends behind the outside wall face.

The inset reduces the original circle's radius and offsets straight sides,
retaining the same centre. It does not fit a second, unrelated arch to the
glass. Floor-level door frames omit a fixed threshold. A circular light has
no full-width rectangular passage height. The IFC opening reuses the emitted
exact-source void mesh; its curves have the shared export tessellation
tolerance, currently 2 mm. It is not silently exported as its bounding box,
and it is not claimed to be an analytic IFC circle.

`DoorComposition` distinguishes a central operable passage from the facade's
fixed sidelights and transom:

```python
Door("entrance", host="wall", width=3000, height=3400,
     composition=DoorComposition(passage_width=1300,
                                 passage_height=2450, leaves=2),
     glazed=False, leaf="oak")
```

Passage dimensions are inside the two fixed posts and below the transom.
Both central leaves operate, without a fixed central mullion. Fixed lights
remain glass when central leaves are opaque. Typed component roles and
opening-relative passage intervals are recorded. Room analysis uses those
intervals for access and clips actual glass to each room for daylight; the
3000 mm facade cannot earn 3000 mm of passage. The component ranges describe
envelopes that are clipped to a curved profile, rather than rectangular glass
areas inferred from those ranges.

Composition currently supports a symmetric pair of sidelights, a fixed
transom, and one or two central hinged leaves, including the legacy
`ArchedDoor` springing-height convention. It is rejected on `SlidingDoor`.
Passage dimensions must accommodate the modeled 2 mm leaf side gaps and
8 mm floor gap. The envelope-wide `panes` grid is rejected with composition,
because those fixed frame bars would cross the declared operable passage.
It does not solve arbitrary joinery
grids, moving astragals, hinge kinematics, threshold accessibility or measured
hardware clearances. The legacy double-door `leaves` behavior is unchanged
unless composition is declared. Decorative project fanlights remain custom
`OpeningPart`/opening implementations.

## Roofs and host attachments

`Roof` accepts concave polygon footprints, through-apertures in `voids`, and
`ridge_angle` measured counter-clockwise from world +X. A rotated roof's
`high_side` is in its local frame. Thickness remains vertical, matching the
original roof convention. For unrotated rectangular roofs existing gables,
overhangs, abutting sides and génoise behavior remain available. Polygon roofs
use explicit wall infills; axis-named `abuts` and automatic `genoise` are
rejected for those roofs rather than guessed along polygon edges.
Interior rings created when an overhang buffer closes a narrow courtyard
entrance are retained alongside explicitly declared apertures.

```python
Roof("roof", outline=[(0, 0), (6000, 0), (6000, 2500),
                      (3500, 2500), (3500, 5000), (0, 5000)],
     ridge_angle=27, pitch=22, overhang=0, thickness=180, level="upper",
     voids=[[(900, 900), (1700, 900), (1700, 1600), (900, 1600)]])
WallToRoofInfill("wall.infill", wall="wall", roof="roof",
                 opening_voids=["tall_door"])
RoofCovering("lining", roof="roof", side="underside",
             thickness=24, gap=1, follow="structural", material="plaster")
RoofCovering("cover", roof="roof", side="top",
             thickness=30, follow="finished", material="tile")
```

`RoofGeometry.surface` records a horizontal `SurfaceFrame`, local footprint
and holes, typed height sections and vertical thickness. The roof top is the
minimum of those section heights. Public `roof_shell(surface)` realizes a
layer from those facts without calling a private `Roof._shell`. An emitted
nonphysical `roof.surface` entity retains the exact structural solid before
`cut_against` junction cuts. `RoofGeometry.surfaces` records the **final** CAD
top and underside faces as shared `PlanarSurface` triangles, including their
holes. Tile and other decorative generators can follow the final surfaces
without inventing their own roof pitch or bbox footprint.

Roof quantities distinguish nominal footprint, actual material surface and
actual covered plan. They are all in square millimetres:

| Published field | Gross or net meaning |
| --- | --- |
| `RoofGeometry.plan_area_mm2` | Historical **gross nominal footprint**: the declared outline's area, before overhang, apertures and junction cuts. Retained for compatibility; it is not a net material quantity. |
| `RoofGeometry.surface_area_mm2` | **Net physical surface**: the sum of the final upward-facing planar CAD skin areas, after overhang, all retained holes and junction cuts. Vertical edge/reveal areas are excluded. |
| `RoofGeometry.covered_plan_area_mm2` | **Net covered plan**: the union of those final upward-facing surfaces projected onto world XY. Holes remain holes; vertically overlapping fragments cover a plan location once. |
| `RoofCoveringGeometry.area_mm2` | **Net physical covering surface**: actual area of the completed layer's selected outer skin, top for a covering or underside for a lining, after the chosen attachment, apertures and optional room outline clipping. It is not volume divided by vertical thickness. |
| `RoofCoveringGeometry.plan_area_mm2` | **Net covering plan**: the union of that same selected skin projected onto world XY. |

The net quantities are measured in completed-model analysis, so subsequent
cuts cannot leave stale realization-time areas. `follow="structural"` counts
the lining actually retained across a roof junction; `follow="finished"`
counts a layer clipped by that junction. Both subtract intentional apertures.
For a simple pitched layer, physical area equals covered plan area divided
by the cosine of pitch. A cut that produces vertically separated plates can
create multiple upward-facing skins; their physical areas add, while their
covered plan is a union. These definitions count the resulting geometry and
do not infer whether such a junction is a good construction detail.

`Wall(roof_limit=..., roof_clearance=...)` terminates its physical body at the
structural underside; nominal wall height remains explicit and
`physical_z_top` records the highest retained point. `Wall.cut_against` and
`Roof.cut_against` make exact solid junction cuts and disable the wall's old
uncut IFC extrusion. `WallToRoofInfill.cut_against` subtracts actual solids;
these lists name declared entities. A project referring to an emitted child
must explicitly order after its declaring parent in its `deps()` override.
`opening_voids` reuses named openings' exact voids, including their rectangular
extrusions when a separate void entity is absent. Declare every opening that
crosses an infill boundary in that list. Empty infills retain typed reference
facts but emit no physical geometry or phantom IFC product.

Structural and finished attachment are intentionally explicit. Projecting
the final roof's junction holes downward can remove masonry that should stay
under an adjoining roof. `RoofCovering` extrudes the selected actual CAD skin
and retains its apertures. Optional `outline` limits it to a room. It does not
independently rebuild a ceiling pitch or use a bbox minimum as an attachment.

Finished wall and infill `surfaces` publish the actual inside/outside main
faces for stone courses and room finishes, retaining opening holes. Reveal
faces are not currently published by this planar-face interface. Wall-top
maximum height is not a full room-height analysis of a sloping ceiling.
Existing room-height and headroom checks remain distinct from roof attachment
consistency; they must not be weakened to compensate for reconstruction data.

The compact fixtures in `tests/test_opening_profiles.py` and
`tests/test_roof_surfaces.py` exercise independent analytic area, CAD, IFC,
room contact, concavity, through-holes and rotation. Bastide callers remove
the redundant exact-arch wrapper and migrate the round lights, shallow arch,
stone surround, wing roofs and plaster to these APIs. House-specific roof
junction footprint exclusions still remain local; the stabilized exterior
branch's later dimensions and ornament are not imported into this upstream
change.
