# Kitchen photographic evidence and changes

The focused kitchen reconstruction starts from merged source ec117ec97c3a5610c9f9bf8b8e4fb18b2a2fc5a8. It corrects construction and appearance discrepancies established by the original photographs and plans while preserving the kitchen footprint, room connections, photo10 camera, and island stone-top outline and datum. The implementation is in rooms/kitchen_envelope.py, kitchen_joinery.py, kitchen_furniture.py and kitchen_surfaces.py, with limited structural and integration changes.

This ledger distinguishes source evidence, the initial model and implemented decisions. Measured build/audit results and current render observations belong to the separate dated verification report and render manifests. Inferred dimensions remain hypotheses after implementation; this report does not claim photographic equivalence or surveyed construction accuracy.

## Original evidence and workflow

The review used references.md, decisions.md including D-034, camera_calibration.md, the photo10 lock and projection implementation, photo-discrepancies.md, the project README and actual project/interior/fidelity source. It follows .claude/skills/design-audit/SKILL.md: preserve circulation, inspect physical geometry and distinguish reconstruction assumptions from verification. All three original plan PDFs were inspected visually. Local plan renderings and image crops are diagnostic derivatives; the supplied archive and extracted originals remain unchanged.

Original reference root: /Users/cloud/.codex/worktrees/54c7/homespec/projects/bastide_de_flechon/reference/.

| Index | Original | Evidence |
| --- | --- | --- |
| 10 | PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-2.jpg | Main axial kitchen, clear island, beams, garden head and daylight |
| 00 | PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-10.jpg | Reverse kitchen, flat hall lintel, stone, tap and three beams ahead |
| 35 | PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-9.jpg | Transverse cabinetry, stool construction, island extension and pendant detail |
| 54 | PHOTOS/VICTOR FITZ/DSC05098.jpg | Independent transverse corroboration, with different styling and light |
| 12 | PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-21.jpg | Exterior garden opening and four-column glazing |
| 34 | PHOTOS/MARK ELST/Bastide de Flechon - Final Collection-8.jpg | Outdoor dining, not the kitchen; the inherited kitchen photo-map entry was incorrect |

Full-resolution source files were opened. The viewing tool resized the large photo54 for display; its original pixels and file were preserved.

## Island, stone and cabinetry

**Evidence.** The ground plan draws a northern sink/DW cabinet followed by a southern seating-table continuation, with chairs on both sides and the end. Photo35 shows the top extending substantially image-left/south beyond the walnut body; one stool has the pale west cabinet behind it rather than an island panel. Photo54 independently shows the same arrangement. Photo10's near/north end has a complete paneled face and small side overhang. The plan establishes a seating zone, not a measured stool inventory or exact photograph-period furniture dimensions.

**Initial condition.** The inherited 3.58 m solid carcase, centered at y=12.0 m, occupied approximately y=10.21–13.79 m. Its stone occupied y=10.35–13.795 m, so the body extended beyond the top at the south end and left no useful knee space. Simply moving stools inward could create a cabinet clash before reproducing their photographic occlusion. The nominally hollow sink shell also overlapped the solid carcase beneath it. Both island and west countertops used a visually excessive 75 mm stone thickness.

**Implemented.** The island body now begins at y=11.25 m beneath the retained y=10.35 m stone edge, creating an inferred 900 mm garden-end seating extension. Independent cabinet boards leave the sink volume open; concealed steel rails support the extension. The stone is one continuous 25 mm slab with an actual sink opening, thin stainless bowl and drain. Its top remains at z=0.9575 m and retains the photo10-locked XY bounds. Separate timber cornice and profiled joinery distinguish stone from the moulding beneath it. Three cast stools occupy the seating zone and bear on the new floor finish.

The west cabinet fronts now face into the room; the inherited local-Y sign placed panels and pulls into their carcase. Revised segmentation includes a narrower three-door southern tower informed by photo35, drawers, paired glazed banks, open shelves and the lower northern counter visible in photo00. Broad profiled members replace detached nested square sticks, and end-panel grain runs vertically. Cabinet geometry and hardware remain editable.

**Uncertainty.** A seating extension is strongly supported; its 900 mm length and concealed supports are inferred. Early evidence review considered conservative 400–600 mm trials, but the side photographs and plan support a more substantial extension without uniquely determining its length. Photo10 alone cannot settle the hidden southern body extent. The selected 25 mm stone is within the approximately 20–30 mm photographic edge estimate, but neither thickness nor cabinet/furniture dimensions were surveyed. Photo35/54 and the reverse view remain essential checks. Exact mouldings, appliance details and hardware remain approximate.

## Ceiling timbers

**Fine joist evidence and change.** The initial 92 mm joists on 245 mm centers provided only 37.6% timber in plan. Photo10's clear central bay contains markedly more timber than plaster; photo00 and photo35 corroborate the rhythm. Samples from the untouched 1500×2000 photo10, x=400–1099 at y=220/260/300, classified timber versus pale plaster at mean-RGB thresholds of 150/165/180. Timber fractions were 59.6–63.7% across these thresholds. The sampled strips contained approximately 45–69 px timber and 18–50 px plaster. Irregular edges and visible side faces account for part of the spread. This is a silhouette proxy, not material albedo or a surveyed section.

Fine joists are now 150 mm wide at the retained 245 mm pitch and 105 mm depth. This selects the middle of the 145–155 mm range corresponding to roughly 59–63% timber. Bearing planes and ceiling height remain unchanged. Grain follows individual members and distinct end-grain assignments are retained.

**Heavy beam evidence and retained discrepancy.** Photo10 shows four distinct heavy beams, with the nearest cropped by the top edge. Photo00 shows three ahead of its reverse viewpoint; photo35 shows one across the transverse doorway, with others obscured by cabinetry. These views support retaining four modeled members but do not establish the room's total count. None of the three plans locates or dimensions the exposed beams.

The centers remain y=10.60/11.85/13.10/14.35 m, with 285×310 mm sections, 2.557 m soffits and a 2.867 m bearing plane. These are inherited photographic hypotheses. The unchanged photo10 camera gives the following conditional silhouette comparison at a 2000 px image height. Photo coordinates are approximate manual reads, not optimized annotations or a new render score.

| Visible beam, near to far | Model upper/lower silhouette v | Photo10 approximate v |
| --- | --- | --- |
| y=14.35 m | Cropped above frame to 172 | Cropped above frame to 184 |
| y=13.10 m | 320–530 | 380–498 |
| y=11.85 m | 541–672 | 558–658 |
| y=10.60 m | 654–749 | 658–728 |

The second beam remains the largest silhouette disagreement; the farther members are closer. Equal pitch and uniform depth may contribute, but camera height, unknown image correction/crop and absolute ceiling/bearing height are coupled. This pass therefore retains the heavy structure rather than deriving a uniformly shallower section from one camera. Exact spacing, section, total count and timber aging remain open to stronger multi-view evidence.

## Openings and wall artwork

**Kitchen–hall portal.** Photo00 shows a flat horizontal lintel and square left upper corner. Initially, A_HALL_K and A_K_HALL both used Arch(width=1100, height=2100), producing semicircular crowns to 2650 mm. Both now use SquareHeadedOpening with 2100 mm flat heads, retaining 1100 mm width and their shared world center at (-2500,16650) mm. The ground plan shows approximately 1.0–1.1 m between the skew wall ends and no door swing at this connection. Flat shape is well established; exact lintel height remains inferred. The host walls and their actual skew alignment remain.

**Garden and terrace openings.** Photo12 and photo10 corroborate a shallow segmental garden head and four-column/three-row glazing. This kitchen pass leaves the old merged garden-opening baseline unchanged: 2200 mm width, 2080 mm spring and 360 mm rise. Its spring/rise remain inferred. The existing terrace opening and exterior surrounds are also retained. Independent exterior work may revise these openings and surrounds; those changes are not integrated into this ec117ec-based kitchen scene and require another kitchen/exterior check after integration. Background vegetation and furniture remain approximate and do not justify moving room geometry.

**Artwork.** Photo10 shows a thin dark frame with bronze/black curved hourglass-like shapes, fine gold lines and reflective glazing/green areas. The missing piece is now an editable 620×1250 mm geometric abstraction on the actual K1 inside face, centered at y=10.56 m and z=1.65 m. Its nearest edge at y=10.25 m preserves 50 mm clearance beyond A_DINING_K. The original artwork's identity, precise dimensions and surface composition remain unknown.

Its conditional photo10 projection spans approximately u=0.143–0.185 and v=0.402–0.569, against reference u≈0.15–0.205 and v≈0.405–0.565. Vertical correspondence is close, while a roughly 20–30 source-pixel lateral disagreement is retained: an exact lateral fit at this wall face would overlap the dining opening. No camera or opening was moved to conceal that discrepancy.

## Floor, skirting and surfaces

The ground plan depicts longitudinal strips and approximately half-bond staggered joints. Its raster hatch is roughly 330×1000 mm, but the schematic graphic does not establish installed fabrication sizes. Photo10/00 show broad, long limestone flags with subtle staggered cross joints and fine pale mortar. The photograph-led estimate was 400–500 mm widths, 800–1000 mm lengths along +y and roughly 2–4 mm joints. Exact module and any mixed-length pattern remain uncertain.

The implementation selects individual 400×800 mm flags in half bond, long axis +y, with 2.5 mm physical joints and shallow arrises. Each flag is clipped to the native convex/skew F0_K outline. Its finish top is 2 mm above the compiled slab; grout tops are 0.6 mm above that slab. Pale stone skirting is an inferred 100 mm high by 20 mm deep, mitered at corners and cut around actual opening voids. Skirting local axes follow the wall edges so their bounding boxes describe the thin physical strips. This representation change retains world geometry, UVs and the existing audit policy.

Kitchen-only shaders use quieter cream plaster, cleaned honey oak, waxed walnut and bronze-grey striated stone. Photo10 plaster has restrained broad variation and fine trowelling; most large brightness/color changes are illumination. The photographed island face is warm medium-dark walnut with broad grain. Grey/putty cabinets have relatively quiet paint surfaces, where profiles, crown and diamond plinth vents supply detail. Photo00's warmer stone does not establish an intrinsically orange worktop pigment.

Generated pigment maps feed Base Color. Roughness, fine pores and fiber relief are independent, and geometry supplies tile joints and joinery profiles. The new cleaned-oak sibling asset retains its prompt and hash; prior oak and salon/bedroom assets remain unchanged. Exact shader choices and texture provenance are in kitchen-materials-provenance.md. Surface brightness, timber aging, plaster contrast and grazing stone reflections remain visual comparison questions, with current observations reported separately; parameter values alone are not photographic acceptance.

## Pendants, stools, styling and light

The source stools have pierced cast saddle seats, fluted pedestals, open radial bases and curved iron footrests. The reconstruction retains this family and places three stools around the actual garden-end knee space. Their exact scale, spacing and photographic occlusion remain inferred.

Original-pixel inspection of photo10 distinguishes **three** separate pendant necks and overlapping bells, correcting the inherited pair and the initial full-frame reading. The fixtures have long narrow woven necks, irregular shouldered bodies and fine dense wire mesh. Three reconstructed shades occupy y=10.65/11.55/12.45 m, with inferred 235 mm radii, 815 mm heights and lower rims at 1.65 m. They remain entirely over the fixed counter; attachment logic checks the actual counter footprint and finds the first ceiling/beam/joist hit for each cord. These low countertop fixtures do not imply a lower walking route. Count is better established than exact shape, dimensions or height.

Photo10 has unlit pendants and a clear island; photo00 includes a lit practical and flowers, while photo54 has fruit/cushion styling. The editable photo00 flowers remain a disabled alternate collection, not default photo10 dressing. The photo10 preset retains its previous 20% aperture-light approximation and unlit pendants. The separate photo00 inspection preset retains the same daylight/EV with 60% pendant practicals; it does not claim measured photo00 photometry. The coherent shared walk preset remains unchanged. Neutral, clay and supplemental-light-off comparisons are controls for separating construction, material and illumination disagreements; the verification record identifies which were completed.

## Camera limits

Photo10 retains the recorded Canon TS-E 24 mm optics, fitted shift and six island landmarks from the merged lock. Its inherited 6.9 px RMS at 900×1200 measures conditional island/camera alignment, not photographic likeness. Island dimensions are not surveyed, and this pass does not move the lock to hide joinery, opening or ceiling discrepancies.

The separate reverse photo00 camera retains its recorded Canon 5DS R / TS-E 24 mm lens and fits five manually annotated coplanar stone/sink points. The fitted pose touches its y=9.1 m lower bound, exposing residual ambiguity; those inferred correspondences do not determine surveyed furniture dimensions. Optical shift, final crop, stitching and correction profiles are unknown in the Photoshop-processed JPEG. The lock records the rejected initial pose and approximately 15 px annotation uncertainty at a 2000 px long edge. No room geometry was changed to reduce this reverse residual.

The additional 28 mm side camera is an unfitted construction diagnostic, informed by photo35/54 and reused identically for baseline/current. It is not a recovery of photo35's recorded 50 mm capture field. Camera, image and model provenance remain in kitchen_camera_lock.json, kitchen-baseline.json and the individual render manifests. Low landmark residuals, clean audits and passing geometry checks answer different questions from photographic likeness.

## Original source hashes

| Source | SHA256 |
| --- | --- |
| photo10 | d884b2fbf52556af8cba69d5e2a7fb6d741e3274d07bf29e8891b82c1cf3f8bd |
| photo00 | 041770ebdc2d4d052fb389559f93dc235bad6246a6bec12d8b688bac08a3a848 |
| photo35 | 701e8d843dda1aea931b1ac17c6b0dfbcafe23fae8b3d82cbb7255b9c7772579 |
| photo12 | fa2099c9ef048bde63d79746601a7cc31ec7efb5d52c8925ee7b3d882990a8a4 |
| photo54 | 6d5673783dc84f9b66ea2de59df267933b0511b2e88237d02653f2a53323cda2 |
| Ground plan PDF | c8c6def5fe0043ac3c7227fc2a77999ad159d03b7da19e51cd8c6a5da2e8e44e |
