"""Rules that run on every build.

A rule is a function of the IR that yields :class:`Result` records. Generic
rules register with :func:`rule`; a project adds its own through
``house.check``. Rules never touch geometry files directly; they read the
IR's derived facts and bounding boxes, which keeps them fast and keeps the
geometry authority in one place.
"""
from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable
from typing import Any

from pydantic import BaseModel

from ..ir import IRDocument


class Result(BaseModel):
    """One finding. ``value`` is what was measured, ``limit`` what was required."""

    rule: str
    target: str
    ok: bool
    value: Any = None
    limit: Any = None
    note: str = ""
    clause: str = ""

    @classmethod
    def of(cls, rule: str, target: str, ok: bool, value: Any = None, limit: Any = None, note: str = "", clause: str = "") -> Result:
        """Build a result from positional values, the shape project checks yield as tuples."""
        return cls(rule=rule, target=target, ok=ok, value=value, limit=limit, note=note, clause=clause)


Rule = Callable[[IRDocument], Iterable[Result]]
_RULES: list[tuple[str, str, Rule]] = []


def rule(name: str, clause: str = "") -> Callable[[Rule], Rule]:
    """Register a generic rule. ``clause`` names the code clause or rule of thumb it implements."""

    def register(fn: Rule) -> Rule:
        _RULES.append((name, clause, fn))
        return fn

    return register


def registered() -> list[tuple[str, str, Rule]]:
    return list(_RULES)


def run(ir: IRDocument, extra: Iterable[Callable[..., Any]] = ()) -> list[Result]:
    """Run every registered rule and the project's own over the IR."""
    from . import clashes, residential  # noqa: F401  (registers the standard rules)

    results: list[Result] = []
    for name, clause, fn in _RULES:
        for r in fn(ir):
            results.append(r.model_copy(update={"rule": r.rule or name, "clause": r.clause or clause}))
    for fn in extra:
        for r in fn(ir):
            results.append(r if isinstance(r, Result) else Result.of(*r))
    return results


def write_report(results: list[Result], out_dir: str, title: str) -> tuple[str, str]:
    """``checks.md`` for people and ``checks.json`` for machines."""
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "checks.json")
    with open(json_path, "w") as f:
        json.dump([r.model_dump() for r in results], f, indent=1)
    md_path = os.path.join(out_dir, "checks.md")
    fails = [r for r in results if not r.ok]
    with open(md_path, "w") as f:
        f.write(f"# Checks: {title}\n\n{len(results) - len(fails)} passed, {len(fails)} failed\n\n")
        f.write("| result | rule | target | value | limit | note | clause |\n|---|---|---|---|---|---|---|\n")
        for r in results:
            f.write(f"| {'PASS' if r.ok else '**FAIL**'} | {r.rule} | {r.target} | {r.value} | {r.limit} | {r.note} | {r.clause} |\n")
    return md_path, json_path
