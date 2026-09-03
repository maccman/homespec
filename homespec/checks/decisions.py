"""``decisions.md`` is checked like everything else.

A project keeps its reasons beside its spec: one ``## D-nnn Title`` entry
per decision, each optionally opening with an ``Entities:`` line naming
what it governs, and three ledgers at the end. *Against the reference*
compares the model with the photographs or drawings it was built from and
says what was kept or changed and why (when there is a reference).
*Considered and not changed* stops the next reader re-litigating settled
questions. *Not verified* is what no rule and no eye has checked, kept
apart from what is out of scope.

This module reads the file and reports: decision ids are unique; every id
on an ``Entities:`` line exists in the build (an entity, level, material
or assembly), so a decision cannot quietly outlive what it decided; and
the two required ledgers are present. It runs from the pipeline, which
knows the project directory; rules proper only see the IR.
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterable

from pydantic import BaseModel

from ..ir import IRDocument
from .base import Result

HEADING = re.compile(r"^## (D-\d+)\s+(.*?)\s*$", re.MULTILINE)
LEDGER = re.compile(r"^## (?!D-\d)(.+?)\s*$", re.MULTILINE)
ENTITIES = re.compile(r"^Entities:\s*(.*?)\s*$", re.MULTILINE)
REQUIRED = ("Considered and not changed", "Not verified")
OPTIONAL = ("Against the reference",)


class Decision(BaseModel):
    id: str
    title: str
    entities: list[str]
    body: str


class Decisions(BaseModel):
    decisions: list[Decision]
    ledgers: list[str]

    def cited(self) -> set[str]:
        return {e for d in self.decisions for e in d.entities}


def parse(text: str) -> Decisions:
    """The decisions and ledger headings of a ``decisions.md``."""
    heads = list(HEADING.finditer(text))
    decisions = []
    for k, m in enumerate(heads):
        end = heads[k + 1].start() if k + 1 < len(heads) else len(text)
        body = text[m.end():end]
        nxt = LEDGER.search(body)
        if nxt:
            body = body[:nxt.start()]
        ents = ENTITIES.search(body)
        names = [e.strip("` ") for e in re.split(r"[,\s]+", ents.group(1)) if e.strip("` ")] if ents else []
        decisions.append(Decision(id=m.group(1), title=m.group(2), entities=names, body=body.strip()))
    return Decisions(decisions=decisions, ledgers=[m.group(1) for m in LEDGER.finditer(text)])


def known_ids(ir: IRDocument) -> set[str]:
    return {e.id for e in ir.entities} | set(ir.levels) | set(ir.materials) | set(ir.assemblies)


def check(doc: Decisions, ir: IRDocument) -> Iterable[Result]:
    seen: dict[str, int] = {}
    for d in doc.decisions:
        seen[d.id] = seen.get(d.id, 0) + 1
    dupes = sorted(i for i, n in seen.items() if n > 1)
    yield Result(rule="decision_ids", target="decisions.md", ok=not dupes, value=f"{len(doc.decisions)} decisions" + (f", repeated: {', '.join(dupes)}" if dupes else ""),
                 limit="one entry per id")
    known = known_ids(ir)
    for d in doc.decisions:
        if not d.entities:
            continue
        unknown = [e for e in d.entities if e not in known]
        yield Result(rule="decision_entities", target=d.id, ok=not unknown, value=", ".join(d.entities), limit="ids in the build",
                     note=("unknown: " + ", ".join(unknown)) if unknown else d.title)
    for name in REQUIRED:
        yield Result(rule="decision_ledgers", target=name, ok=name in doc.ledgers, value="present" if name in doc.ledgers else "missing",
                     limit=f"a '## {name}' section")


def validate(project_dir: str, ir: IRDocument) -> list[Result]:
    """Every finding about a project's ``decisions.md``; one failure when there is no such file."""
    path = os.path.join(project_dir, "decisions.md")
    if not os.path.exists(path):
        return [Result(rule="decisions", target="decisions.md", ok=False, value="missing", limit="a decisions.md beside project.py",
                       note="every project keeps its reasons beside its spec")]
    with open(path) as f:
        doc = parse(f.read())
    return list(check(doc, ir))
