# Verification — La Bastide de Fléchon

Reconstruction reviewed in Blender 5.2.1 on 4 September 2026.

## Architecture and source evidence

The architectural model has 314 entities and passes 344 HomeSpec checks,
including physical intersections, door access, stair landings and 2 m of
headroom above both curved stairs. The supplied ground-floor, first-floor and
site plans anchor the layout. Sixty-one supplied photographs inform the
finishes, furniture, roof structure, glazing and garden.

Corrections include connected skew-wing partitions, exact arched openings,
complete main gables, a vaulted suite ceiling with exposed oak framing, kitchen
beams, west-suite rectangular glazing, guest-room joists, the entrance gallery
opening and floor openings trimmed to clear the physical stairs. Decisions
D017–D026 and the preceding project decisions describe assumptions and changes.

## Furnishings and audit

The diagonal walls required oriented footprint intersection calculations in the
presentation audit. Existing checks and thresholds remain intact; 32 geometry
regression tests verify the calculations. The full repository suite passed
192 tests. Ruff and Pyright passed for the core changes.

The furnished-scene review identified unsupported walnut chair seats and
axis-aligned bounding boxes around rotated bed linen. The chairs received
timber support rails and decks. Cloth meshes now retain local coordinates and
their bed transforms, so the audit evaluates the oriented footprint. A genuine
duvet intrusion into one bathroom approach was also corrected. The gallery
retains 1,441 mm between its aperture and the stair well, with a connected
upper floor and supported ironwork along its three free edges.

## Walkthrough and visual review

The current passing generation is `723363ddaabf46a2a8d6fd7865e33e46`, with
presentation fingerprint `f2648f107593ba2c`. The furnished scene contains 9,624
objects and reports zero audit findings. Final diagnostic plans and sections
were reviewed from this generation.

The exported `deliverables/model/house_walk.blend` contains 29 packed images
and three baked irradiance volumes spanning both floors. All 19 room operators
were invoked and their camera positions checked. Five separate Eevee renders
verify the actual interactive lighting in the garden, salon, kitchen, ground
bedroom and principal suite. The desktop launcher starts this file and reports
that the navigation panel is ready. Keyboard navigation uses Blender's built-in
walk operator.

An independent artifact review passed 42 checks: the model, navigation script,
launcher and source-scene hashes match `SOURCE.json`; the current build resolves
with passed checks and fresh inputs; all architectural exports and model
companions exist. The shell launcher passes `zsh -n`.

All 19 final gallery views rendered successfully at 1920 × 1200, using up to
192 Cycles samples with adaptive sampling and denoising. Each camera and frame
passed its collision/visibility and black-frame checks. `gallery-manifest.json`
records the source generation, settings and every image hash; `gallery-overview.jpg`
provides a contact sheet. The five separate Eevee previews were also reviewed.
The portable ZIP passed CRC integrity checks and preserves launcher permissions.

Visual comparison prompted the corrected west-suite window, roof braces, guest
ceiling timbers, entrance gallery, ivory/rust curtain pattern, open kitchen
shades, darker coverlet/countertop, ochre foyer, planar mirror reflections and
three improved camera compositions. The geometry audit could not detect those
appearance/framing issues. Future checks could validate a named viewpoint's
facing direction and mirror cap normals; photographic resemblance still needs
manual review against the supplied images.

## Not verified

The source does not establish exact storey heights, concealed construction,
all opening dimensions, furniture dimensions, true north or landscape contours.
Those details are inferred from plans and photographs and documented in
`decisions.md`. Furniture, vegetation and materials are modeled approximations.
The paisley textile is generated from the supplied reference images, with its
prompt recorded in `references.md`.

This is an editable visual reconstruction. It is not a measured scan, and
render quality alone does not establish geometric accuracy or photographic
identity to the original house.
