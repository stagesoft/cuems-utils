"""Contract C2 (T040) — every accessor name survives (FR-018).

*Every name that exists today is present after and means the same thing.* The
claim is asserted against the **recorded inventory**
(``tests/golden/api/config_accessors.json``, captured by introspection before
any US3 change landed) rather than against a list retyped into this file.

That distinction is the whole point of T040a. A retyped list asserts its own
contents: it is written *after* the change, by the same person making it, and
would happily omit an accessor that had just been dropped. A golden captured
beforehand cannot.

Three things are checked, and "means the same thing" is split into the two
halves that fail independently:

* the **name** is still there;
* its **kind** has not changed — a property that became a method is still
  "present" and breaks every call site;
* a method's **signature** has not changed.
"""

from __future__ import annotations

import pytest

from tests.support.config_inventory import load_golden, snapshot

GOLDEN = load_golden()
LIVE = snapshot()

NAMES = [
    (class_name, name)
    for class_name, entries in sorted(GOLDEN.items())
    for name in sorted(entries)
]
IDS = [f"{c}.{n}" for c, n in NAMES]


def test_the_inventory_covers_both_classes():
    assert set(GOLDEN) == {"ConfigBase", "ConfigManager"}
    assert len(GOLDEN["ConfigManager"]) >= 30, len(GOLDEN["ConfigManager"])


@pytest.mark.parametrize("class_name,name", NAMES, ids=IDS)
def test_the_name_is_still_present(class_name, name):
    assert name in LIVE[class_name], (
        f"{class_name}.{name} existed before this feature and does not now "
        f"(FR-018)"
    )


@pytest.mark.parametrize("class_name,name", NAMES, ids=IDS)
def test_the_kind_has_not_changed(class_name, name):
    before = GOLDEN[class_name][name]["kind"]
    after = LIVE[class_name][name]["kind"]
    assert before == after, (
        f"{class_name}.{name} was a {before} and is now a {after}; the name "
        f"survives but every call site breaks"
    )


@pytest.mark.parametrize("class_name,name", NAMES, ids=IDS)
def test_method_signatures_have_not_changed(class_name, name):
    before = GOLDEN[class_name][name]
    if before["kind"] != "method":
        pytest.skip("not a method")
    assert before["signature"] == LIVE[class_name][name]["signature"]


def test_only_the_structural_accessors_changed_return_type():
    """The enumerated half of FR-018: *only* return types change, and only
    where the value is a structure rather than a scalar.

    A scalar accessor that started returning an object would satisfy every
    assertion above and still be a breaking change.
    """
    moved = {
        f"{class_name}.{name}"
        for class_name, entries in GOLDEN.items()
        for name, entry in entries.items()
        if entry["kind"] in ("property", "attribute")
        and entry.get("return") != LIVE[class_name][name].get("return")
    }

    # Every accessor whose recorded return type was ``dict`` — those are the
    # ones FR-014 requires to become objects. Nothing else may move.
    expected = {
        f"{class_name}.{name}"
        for class_name, entries in GOLDEN.items()
        for name, entry in entries.items()
        if entry.get("return") == "dict"
    }

    assert moved == expected, (
        "return types moved outside the structural set:\n"
        f"  unexpected: {sorted(moved - expected)}\n"
        f"  expected but unchanged: {sorted(expected - moved)}"
    )


def test_no_scalar_accessor_moved():
    """Stated separately and positively, because it is the promise consumers
    actually rely on: ``library_path`` still returns a path string."""
    for class_name, entries in GOLDEN.items():
        for name, entry in entries.items():
            if entry.get("return") in ("str", "int", "float", "bool"):
                assert LIVE[class_name][name].get("return") == entry["return"], (
                    f"{class_name}.{name} was a scalar and is now a "
                    f"{LIVE[class_name][name].get('return')}"
                )
