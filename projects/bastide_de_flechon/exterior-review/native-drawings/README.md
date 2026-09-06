# Native drawing check — production e3b0760284354eac9ea110ca7e12ec92

The two untouched production SVGs are native CAD horizontal sections from source `55a3069`, IR SHA256 `c5ae2d0418beefc946656622791043ea0ceb73c1bfe6e262ee174ed5369f1171`. Both full landscape sheets were rasterized with bundled Sharp 0.35.4 / librsvg 2.62.91, inspected visually, and saved as RGB PNGs at **3968 × 2806 px**.

- [Ground plan](plan_L0.png): absolute cut **1200 mm**. The main, hall, kitchen and guest exterior door apertures are present in the actual cut walls. Main front leaves show their modeled open pose.
- [Upper plan](plan_L1.png): absolute cut **4500 mm**, 1200 mm above L1. It shows the corrected **1350 mm** kitchen south opening and hall opening. It intentionally cannot show the east oculi, whose sill is 5100 mm.
- [Supplementary oculus section](plan_L1-oculus-5425mm.png): absolute cut **5425 mm**, derived read-only from the same exact IR. The two actual 650 mm masonry openings occupy y2000–2650 and y6050–6700; their centers **2325 / 6375 mm** align exactly with the centers of ground D_E1/D_E2 at y1500–3150 and y5550–7200. Both upper apertures are on the master side of P_DRESS. This is an explicitly labeled diagnostic sheet, separate from the untouched production drawings.

The principal building is fully framed. The production ground SVG clips the pool underlay at the lower A3 edge, and dimension text overlaps around the compact guest rooms and corridor/stair junction. Width dimensions use structural opening widths and wall reference lines, so an arched aperture's cut chord may be narrower; the main 7300 mm wall-reference dimension does not replace the 8000 mm outer footprint. These drawings validate physical plan relationships at their stated planes, not facade heights or photographic resemblance.

Original ground SVG SHA256: `fe2a4d4101fb6544de17b931da13013696245293716d418a9bade860751dfc24`.  
Original upper SVG SHA256: `3283bd2dc78ad0adf4d167ec79c3d3e3fe69c8862883382cf0b4f69fa3b0b395`.

[drawing-provenance.json](drawing-provenance.json) records source/output hashes, cut planes, renderer versions and exact numerical section checks. No native geometry, project source, camera register or original SVG was changed. No Blender process was used.
