"""One `items()`, one base type — user story 2, FR-012–FR-014, SC-004/SC-008 (T014).

**Must FAIL on pre-005 code**: ten `items()` overrides exist in ``cues/`` and the
script root is a plain ``dict``.

The root's divergence is what forces the duplicated ``setter``, the missing
build hook, the divergent ``items()`` and the JSON unwrap heuristic. Story 1's
guarantee cannot even be *stated* generically while one object in the model
answers "no" to "is this a declared-field model object?".
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.helpers import CuemsDict

CUES_DIR = Path("src/cuemsutils/cues")
HELPERS = Path("src/cuemsutils/helpers.py")


def items_definitions() -> dict[str, list[str]]:
    """``{file: [class names defining items()]}`` across the model.

    Scoped to ``cues/`` and ``helpers.py`` deliberately. ``tools/CTimecode.py``
    and ``tools/Uuid.py`` also define ``items()``; both are **value types**, not
    model objects, and neither has a declared field set. Widening this scan to
    all of ``src/`` would demand they be collapsed too, which would be wrong.
    """
    found: dict[str, list[str]] = {}
    for path in [*sorted(CUES_DIR.glob("*.py")), HELPERS]:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "items":
                    found.setdefault(str(path), []).append(node.name)
    return found


def test_exactly_one_items_definition_exists_in_the_model():
    """FR-014, SC-004 — one definition, one meaning.

    Ten overrides exist today, each layering its own ``REQ_ITEMS`` and two of
    them (``FadeCue``, ``CueOutput``) additionally hand-ordering their output.
    That ordering job belongs to the mapper's ``TypeSpec`` now.
    """
    found = items_definitions()
    flat = [(path, cls) for path, classes in found.items() for cls in classes]
    assert len(flat) == 1, (
        f"{len(flat)} items() definitions in the model, expected 1:\n  "
        + "\n  ".join(f"{path}: {cls}" for path, cls in flat)
    )
    assert flat[0][1] == "CuemsDict", f"the one definition is on {flat[0][1]}"


def test_the_script_root_is_a_model_object():
    """FR-012, SC-008 — ``isinstance`` answers true for the root too."""
    assert issubclass(CuemsScript, CuemsDict)
    assert isinstance(CuemsScript(), CuemsDict)


def test_the_root_does_not_define_its_own_setter():
    """FR-013 — the duplicated setter goes.

    ``CuemsScript.setter`` is a verbatim copy of ``CuemsDict.setter``. A copy
    that must be kept in step by hand is how F17's narrowing would land in one
    place and not the other.
    """
    assert "setter" not in CuemsScript.__dict__


def test_the_root_uses_the_shared_items_definition():
    assert "items" not in CuemsScript.__dict__
    assert CuemsScript.items is CuemsDict.items


@pytest.mark.parametrize(
    "field", ["id", "name", "description", "created", "modified", "CueList", "ui_properties"]
)
def test_the_root_declares_its_fields(field):
    """The root answers the declared-field question like every other class."""
    assert field in CuemsScript.declared_fields()
