"""Rules that run on every build. See :mod:`homespec.checks.base`."""
from .base import Result, registered, rule, run, write_report

__all__ = ["Result", "rule", "run", "registered", "write_report"]
