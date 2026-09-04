# Bastide gallery

These images were regenerated from the passing build in
[../deliverables/SOURCE.json](../deliverables/SOURCE.json). [SOURCE.json](SOURCE.json)
associates each image with its camera frame or diagnostic view, source image
hash, published JPEG hash, build fingerprint, and presentation fingerprint.

The stills use Blender 5.2.1 at 1600 × 900 and 48 samples. Plans, sections,
and structure views use Workbench. The dressed scene reports zero audit
findings. All images were visually inspected against the revised plan.

To regenerate from the current source, build the project, run `homespec views`
with `--only plan,section,structure`, and render the frame numbers recorded in
SOURCE.json. Outputs are saved under the build's presentation directory.
The gallery is a visual record, not a reusable build or saved Blender scene.
