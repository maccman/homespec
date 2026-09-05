"""Typed photographic evidence and square-pixel perspective cameras.

This module uses only the standard library, including when loaded directly by
Blender. Coordinates are metres, Z up; photo UV starts at the upper left. Fits
are conditional on the supplied geometry, never a photographic fidelity score.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

Vec3 = tuple[float, float, float]
Evidence = Literal["observed", "plan-derived", "inferred", "unverified"]
CONVENTION = "perspective-square-pixels-long-axis-zero-roll"


def _finite(values: Any, name: str) -> None:
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values):
        raise ValueError(f"{name} must contain finite numbers")


def _size(size: tuple[int, int]) -> None:
    if len(size) != 2 or any(type(v) is not int or v <= 0 for v in size):
        raise ValueError("Image dimensions must be positive integers")


def digest(path: str | Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class ReferenceImage:
    """Identity of the untouched original; dimensions may remain unverified.

    ``size`` is the original raster's size, not its review thumbnail. Set it
    only when measured. Unknown original dimensions are retained as uncertainty.
    """

    path: str
    sha256: str
    size: tuple[int, int] | None = None
    framing: Literal["full-original"] = "full-original"

    def __post_init__(self) -> None:
        if not self.path or not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("Reference requires a path/identity and SHA-256")
        if self.framing != "full-original":
            raise ValueError("Photo comparisons must retain full original framing")
        if self.size is not None:
            object.__setattr__(self, "size", tuple(self.size))
            _size(self.size)

    def verify(self, root: str | Path) -> Path:
        path = Path(root) / self.path
        if digest(path) != self.sha256:
            raise ValueError(f"Reference changed: {self.path}")
        return path


@dataclass(frozen=True)
class Landmark:
    name: str
    world_m: Vec3
    photo_uv: tuple[float, float]
    role: Literal["fit", "holdout"] = "fit"
    weight: float = 1.0
    evidence: Evidence = "unverified"
    uncertainty: str = "Geometry and image annotation uncertainty have not been measured."

    def __post_init__(self) -> None:
        object.__setattr__(self, "world_m", tuple(self.world_m))
        object.__setattr__(self, "photo_uv", tuple(self.photo_uv))
        if not self.name or len(self.world_m) != 3 or len(self.photo_uv) != 2:
            raise ValueError("Landmark requires name, XYZ and UV")
        _finite((*self.world_m, *self.photo_uv, self.weight), "Landmark")
        if self.weight < 0 or (self.weight == 0 and self.role == "fit") or self.role not in {"fit", "holdout"} or self.evidence not in {"observed", "plan-derived", "inferred", "unverified"}:
            raise ValueError("Invalid landmark weight, role or evidence")
        if not all(0 <= v <= 1 for v in self.photo_uv):
            raise ValueError("Landmark UV must lie in the full original frame")


@dataclass(frozen=True)
class ExifPrior:
    physical_focal_length_mm: float | None = None
    sensor_long_mm: float | None = None
    reported_35mm_equivalent_mm: float | None = None
    source: str = "Unverified metadata; editing/crop history is unknown."

    def __post_init__(self) -> None:
        for value in (self.physical_focal_length_mm, self.sensor_long_mm, self.reported_35mm_equivalent_mm):
            if value is not None:
                _finite((value,), "EXIF prior")
                if value <= 0:
                    raise ValueError("EXIF dimensions must be positive")


@dataclass(frozen=True)
class PhotoView:
    id: str
    location: Vec3
    target: Vec3
    lens_mm: float
    size: tuple[int, int]
    reference: ReferenceImage | None = None
    sensor_dimension_mm: float = 36
    shift_x: float = 0
    shift_y: float = 0
    roll_degrees: float = 0
    convention: str = CONVENTION
    landmarks: tuple[Landmark, ...] = ()
    exif_prior: ExifPrior | None = None
    camera_evidence: Evidence = "inferred"
    uncertainty: str = "Camera pose, geometry, distortion and edited image field are unsurveyed."
    exposure: float = 0

    def __post_init__(self) -> None:
        for name in ("location", "target", "size", "landmarks"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", self.id):
            raise ValueError("Camera id must be filename-safe")
        if len(self.location) != 3 or len(self.target) != 3:
            raise ValueError("Camera pose requires XYZ")
        _finite((*self.location, *self.target, self.lens_mm, self.sensor_dimension_mm, self.shift_x, self.shift_y, self.roll_degrees, self.exposure), "Camera")
        _size(self.size)
        if self.lens_mm <= 0 or self.sensor_dimension_mm <= 0:
            raise ValueError("Camera lens and sensor must be positive")
        if self.convention != CONVENTION or self.roll_degrees != 0:
            raise ValueError("Unsupported camera projection convention or nonzero roll")
        if self.camera_evidence not in {"observed", "plan-derived", "inferred", "unverified"}:
            raise ValueError("Invalid camera evidence")
        if self.reference and self.reference.size:
            rw, rh = self.reference.size
            w, h = self.size
            if not math.isclose(w / h, rw / rh, rel_tol=0.001):
                raise ValueError("Review dimensions crop or distort original reference aspect")
        self.basis()  # reject coincident/vertical look direction, whose roll is undefined
        names = [v.name for v in self.landmarks]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate landmark names")
        for landmark in self.landmarks:
            self.project(landmark.world_m)

    def basis(self) -> tuple[Vec3, Vec3, Vec3]:
        delta = tuple(b - a for a, b in zip(self.location, self.target, strict=True))
        _finite(delta, "Camera direction")
        length = math.hypot(*delta)
        if not math.isfinite(length) or length <= 1e-12:
            raise ValueError("Degenerate camera look direction")
        forward = tuple(v / length for v in delta)
        horizontal = math.hypot(forward[0], forward[1])
        if horizontal <= 1e-12:
            raise ValueError("Vertical camera direction has undefined zero roll")
        right = (forward[1] / horizontal, -forward[0] / horizontal, 0.0)
        up = (right[1] * forward[2], -right[0] * forward[2], right[0] * forward[1] - right[1] * forward[0])
        return right, up, (forward[0], forward[1], forward[2])

    def scaled_size(self, scale: float = 1) -> tuple[int, int]:
        """Round a requested raster scale only when full-frame aspect is retained."""
        _finite((scale,), "Review scale")
        if scale <= 0:
            raise ValueError("Review scale must be positive")
        width, height = self.size
        scaled = (width * scale, height * scale)
        _finite(scaled, "Scaled review dimensions")
        result = (round(scaled[0]), round(scaled[1]))
        _size(result)
        if result[0] * height != result[1] * width:
            raise ValueError(f"Camera {self.id}: scale {scale} rounds {width}x{height} to {result[0]}x{result[1]}, "
                             "which changes the full-frame aspect ratio; choose a scale producing proportional integer dimensions")
        return result

    def project(self, point: Vec3) -> tuple[float, float]:
        if len(point) != 3:
            raise ValueError("Projection point requires XYZ")
        _finite(point, "Projection point")
        right, up, forward = self.basis()
        delta = tuple(b - a for a, b in zip(self.location, point, strict=True))
        depth = sum(d * f for d, f in zip(delta, forward, strict=True))
        if depth <= 1e-12:
            raise ValueError("Landmark is behind camera or on its projection plane")
        width, height = self.size
        edge = max(self.size)
        focal = edge * self.lens_mm / self.sensor_dimension_mm
        projected = (.5 + focal / width * sum(d * r for d, r in zip(delta, right, strict=True)) / depth - self.shift_x * edge / width,
                .5 - focal / height * sum(d * u for d, u in zip(delta, up, strict=True)) / depth + self.shift_y * edge / height)
        _finite(projected, "Projected UV")
        return projected

    @property
    def sha256(self) -> str:
        return fingerprint(asdict(self))

    def residuals(self) -> dict[str, Any]:
        rows = []
        for landmark in self.landmarks:
            uv = self.project(landmark.world_m)
            error = [(a - b) * s for a, b, s in zip(uv, landmark.photo_uv, self.size, strict=True)]
            rows.append({**asdict(landmark), "projected_uv": uv, "error_preview_px": error, "distance_preview_px": math.hypot(*error)})

        def rms(items: list[dict[str, Any]]) -> float | None:
            return math.sqrt(sum(p["distance_preview_px"] ** 2 for p in items) / len(items)) if items else None

        return {"purpose": "Conditional reprojection disagreement, not a visual-fidelity score", "pixels": self.size,
                "rms_preview_px": rms(rows), "fit_rms_preview_px": rms([p for p in rows if p["role"] == "fit"]),
                "holdout_rms_preview_px": rms([p for p in rows if p["role"] == "holdout"]),
                "independent_holdout_count": sum(p["role"] == "holdout" for p in rows),
                "uncertainty": self.uncertainty, "original_dimensions_verified": bool(self.reference and self.reference.size), "landmarks": rows}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PhotoView:
        """Read the typed schema, without accepting unknown projection fields."""
        data = dict(value)
        if data.get("reference"):
            data["reference"] = ReferenceImage(**data["reference"])
        if data.get("exif_prior"):
            data["exif_prior"] = ExifPrior(**data["exif_prior"])
        data["landmarks"] = tuple(Landmark(**v) for v in data.get("landmarks", ()))
        return cls(**data)

    @classmethod
    def from_legacy(cls, value: dict[str, Any]) -> PhotoView:
        """Adapter for original project camera-lock rows; project evidence stays local."""
        reference = None
        if value.get("reference_sha256"):
            reference = ReferenceImage(value["reference_original"], value["reference_sha256"], value.get("reference_size"))
        capture = value.get("reference_capture", {})
        prior = ExifPrior(capture.get("physical_focal_length_mm"), capture.get("physical_sensor_long_mm"),
                          capture.get("reported_35mm_equivalent_mm"), capture.get("sensor_source", "Unverified metadata")) if capture else None
        names = ("id", "location", "target", "lens_mm", "size", "sensor_dimension_mm", "shift_x", "shift_y", "roll_degrees", "exposure", "convention")
        return cls(**{key: value[key] for key in names if key in value}, reference=reference, exif_prior=prior,
                   landmarks=tuple(Landmark(**p) for p in value.get("landmarks", ())),
                   uncertainty=value.get("fit_note", value.get("note", "Camera and geometry are unverified.")))


@dataclass(frozen=True)
class PhotoViews:
    id: str
    views: tuple[PhotoView, ...]
    method: str = "Conditional image/geometry comparison; visual review remains necessary."
    schema: int = field(default=1, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "views", tuple(self.views))
        if not self.id or not self.views or len({v.id for v in self.views}) != len(self.views):
            raise ValueError("Photo views require an identity and unique nonempty views")

    @classmethod
    def read(cls, path: str | Path) -> PhotoViews:
        data = json.loads(Path(path).read_text())
        if data.get("schema") != 1:
            raise ValueError("Unsupported photo-view schema")
        legacy = "lock_id" in data
        return cls(data["lock_id"] if legacy else data["id"],
                   tuple((PhotoView.from_legacy if legacy else PhotoView.from_dict)(row) for row in data["views"]), data.get("method", cls.method))

    def write(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2, allow_nan=False) + "\n")


def fit_level_camera(view: PhotoView, bounds: tuple[list[float], list[float]], *, max_evaluations: int = 5000) -> PhotoView:
    """Bounded XYZ/yaw/shifts fit, with lens fixed and holdouts excluded.

    Requires optional SciPy only when invoked. The soft height/shift priors are
    explicit regularizers, not evidence. A fit can worsen holdout/visual results.
    """
    import importlib

    fits = tuple(p for p in view.landmarks if p.role == "fit")
    if len(fits) < 3:
        raise ValueError("Level-camera fitting requires at least three fit landmarks")
    initial = [*view.location, math.atan2(view.target[1] - view.location[1], view.target[0] - view.location[0]), view.shift_x, view.shift_y]
    if len(bounds) != 2 or any(len(row) != 6 for row in bounds):
        raise ValueError("Fit bounds must contain six lower and upper limits")
    for row in bounds:
        _finite(row, "Fit bounds")
    if any(lo >= hi or not lo <= v <= hi for lo, hi, v in zip(*bounds, initial, strict=True)):
        raise ValueError("Fit bounds must contain the initial camera")

    def unpack(values: Any, landmarks: tuple[Landmark, ...] = ()) -> PhotoView:
        loc = tuple(float(v) for v in values[:3])
        return replace(view, location=(loc[0], loc[1], loc[2]), target=(loc[0] + math.cos(values[3]), loc[1] + math.sin(values[3]), loc[2]),
                       shift_x=float(values[4]), shift_y=float(values[5]), landmarks=landmarks)

    def objective(values: Any) -> list[float]:
        camera = unpack(values)
        errors = []
        for point in fits:
            try:
                uv = camera.project(point.world_m)
                errors.extend((a - b) * math.sqrt(point.weight) for a, b in zip(uv, point.photo_uv, strict=True))
            except ValueError:
                errors.extend((1000.0, 1000.0))
        return [*errors, (values[2] - initial[2]) * .01, values[4] * .002]

    optimize = importlib.import_module("scipy.optimize")
    result = optimize.least_squares(objective, initial, bounds=bounds, loss="soft_l1", f_scale=.025, max_nfev=max_evaluations)
    if not result.success:
        raise ValueError(f"Camera fitting did not converge: {result.message}")
    return unpack(result.x, view.landmarks)
