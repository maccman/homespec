"""decisions.md is parsed and checked: ids unique, cited entities real, ledgers present."""
from homespec.checks import decisions

TEXT = """# Decisions: test

## D-001 Grid lines are inside faces
Entities: W1, W2, L0, ext_wall
Room dimensions are what the client thinks in.

## D-002 The library wall is W3
Entities: `W3`, N1
North light is even.

## D-003 A decision about nothing in particular
No entities line here.

## Against the reference

| reference | model | kept or changed |
|---|---|---|

## Considered and not changed

- Nothing.

## Not verified

- Everything else.
"""


def test_parse_finds_decisions_entities_and_ledgers():
    doc = decisions.parse(TEXT)
    assert [d.id for d in doc.decisions] == ["D-001", "D-002", "D-003"]
    assert doc.decisions[0].entities == ["W1", "W2", "L0", "ext_wall"] and doc.decisions[1].entities == ["W3", "N1"] and doc.decisions[2].entities == []
    assert doc.decisions[1].title == "The library wall is W3" and "North light" in doc.decisions[1].body and "Considered" not in doc.decisions[2].body
    assert doc.ledgers == ["Against the reference", "Considered and not changed", "Not verified"]
    assert doc.cited() == {"W1", "W2", "L0", "ext_wall", "W3", "N1"}


def test_check_reports_unknown_ids_duplicates_and_missing_ledgers(library_room_ir):
    text = TEXT.replace("Entities: `W3`, N1", "Entities: W3, N9").replace("## D-003", "## D-001").replace("## Not verified\n\n- Everything else.\n", "")
    rows = {(r.rule, r.target): r for r in decisions.check(decisions.parse(text), library_room_ir)}
    assert not rows[("decision_ids", "decisions.md")].ok and "D-001" in rows[("decision_ids", "decisions.md")].value
    assert rows[("decision_entities", "D-001")].ok
    assert not rows[("decision_entities", "D-002")].ok and rows[("decision_entities", "D-002")].note == "unknown: N9"
    assert rows[("decision_ledgers", "Considered and not changed")].ok and not rows[("decision_ledgers", "Not verified")].ok


def test_a_missing_file_is_one_failure(tmp_path, library_room_ir):
    (found,) = decisions.validate(str(tmp_path), library_room_ir)
    assert not found.ok and found.value == "missing"


def test_the_example_projects_pass(library_room_report):
    ours = [r for r in library_room_report.results if r.rule.startswith("decision")]
    assert ours and all(r.ok for r in ours), [r for r in ours if not r.ok]
