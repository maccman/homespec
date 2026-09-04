"""One Cycles device policy for stills, animation and interactive walks."""
from __future__ import annotations

import os

import bpy

BACKENDS = ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL")


def configure_cycles(scene, requested: str | None = None) -> str:
    """Select a detected GPU, or CPU when none is available.

    ``HOMESPEC_DEVICE`` accepts ``auto``, ``cpu``, or a backend name. An
    explicit GPU request fails if unavailable rather than silently
    rendering on another device. CPU selection never probes a GPU.
    """
    selection = (requested or os.environ.get("HOMESPEC_DEVICE", "auto")).upper()
    if selection not in ("AUTO", "CPU", *BACKENDS):
        raise ValueError(f"Unknown HOMESPEC_DEVICE {selection!r}; expected auto, cpu, or {', '.join(b.lower() for b in BACKENDS)}")
    preferences = bpy.context.preferences.addons['cycles'].preferences
    if selection != "CPU":
        supported = {item[0] for item in preferences.get_device_types(bpy.context)}
        candidates = BACKENDS if selection == "AUTO" else (selection,)
        for backend in candidates:
            if backend not in supported:
                continue
            try:
                preferences.compute_device_type = backend
                preferences.get_devices()
            except (RuntimeError, TypeError) as exc:
                if selection != "AUTO":
                    raise RuntimeError(f"Cycles {backend} device discovery failed: {exc}") from exc
                continue
            available = [device for device in preferences.devices if device.type == backend]
            if not available:
                continue
            for device in preferences.devices:
                device.use = device.type == backend
            scene.cycles.device = 'GPU'
            print(f"DEVICE {backend}: {', '.join(device.name for device in available)}", flush=True)
            return backend
        if selection != "AUTO":
            raise RuntimeError(f"No Cycles {selection} GPU is available; use HOMESPEC_DEVICE=auto or cpu")
    for device in preferences.devices:
        device.use = False
    scene.cycles.device = 'CPU'
    print("DEVICE CPU", flush=True)
    return "CPU"
