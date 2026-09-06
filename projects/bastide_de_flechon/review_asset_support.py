"""Blender/Pillow-independent binding between legacy rows and verified renders."""

from pathlib import Path


def verify_render_mapping(review, rows, manifest_directory, review_directory):
    """Require each legacy camera to name its own unique authoritative image."""
    artifacts = {(Path(review_directory) / artifact.path).resolve(): artifact
                 for artifact in review.artifacts if artifact.kind == 'render'}
    if len(rows) != len(artifacts):
        raise ValueError('Legacy and authoritative render coverage disagree')
    seen = set()
    for row in rows:
        view_id = row.get('id')
        if view_id is None:
            index = row.get('index')
            if type(index) is not int or index < 1:
                raise ValueError('Legacy render has no valid camera identity')
            view_id = f'view-{index:02d}'
        value = row.get('render', row.get('file'))
        if not value:
            raise ValueError('Legacy render has no image path')
        path = (Path(manifest_directory) / value).resolve()
        artifact = artifacts.get(path)
        if artifact is None or artifact.sha256 != row.get('sha256'):
            raise ValueError('Legacy render is absent from authoritative review: ' + str(path))
        if artifact.id.rsplit(':', 1)[0] != view_id:
            raise ValueError('Legacy camera identity disagrees with authoritative render: ' + str(view_id))
        if artifact.id in seen:
            raise ValueError('Duplicate legacy render coverage: ' + artifact.id)
        seen.add(artifact.id)
