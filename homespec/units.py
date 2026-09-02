"""Lengths in homespec are millimetres, as plain floats.

These helpers exist to make intent visible at the call site: ``m(2.4)`` says
"2.4 metres" where ``2400`` says nothing.
"""
from __future__ import annotations


def mm(value: float) -> float:
    """Millimetres, the native unit. Identity, for symmetry with :func:`m`."""
    return float(value)


def cm(value: float) -> float:
    """Centimetres to millimetres."""
    return float(value) * 10.0


def m(value: float) -> float:
    """Metres to millimetres."""
    return float(value) * 1000.0


def to_m(value_mm: float) -> float:
    """Millimetres to metres, for SI consumers such as IFC."""
    return float(value_mm) / 1000.0
