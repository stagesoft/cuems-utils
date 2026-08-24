"""Contracts §W8 (T043a, T043b) — config projects through the **same** engine.

Two claims, and the second is what keeps the first from decaying:

**W8** — for every corpus config document, the config object's ``to_wire()``
equals the recorded ``tests/golden/dict/*.config.json``, under the same
predicate the show projection is held to (``rt.wire_diff``, contracts §W1a:
recursive structure, exact scalar type, key order). The goldens already exist,
were captured before this feature by the same harness that captured
``*.reader.json``, and are **not** regenerated.

**SC-017** — the config path and the show path reach *the same* ``encode_wire``.
Not "produce the same shape", which two implementations could do for a while:
the same function object, on the same method body, with no second projection
anywhere in the package. That assertion is what stops FR-014a decaying into the
parallel definition it exists to prevent — the drift mechanism behind F15's
three incompatible mappings shapes.

**Why configuration is projected at all**, given that it is *not* transmitted
to the UI today: opening configuration files to the UI is planned follow-on
work, and building the projection once, here, costs almost nothing — the config
types become registry-bound model classes in this feature regardless. The cost
of not doing it is a second projection written later.
"""

from __future__ import annotations

import inspect
import json

import pytest

from cuemsutils.config import ConfigDict
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.helpers import CuemsDict
from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT

CONFIG_DOCS = [
    d
    for d in DOCUMENTS
    if d.config_class and (GOLDEN_ROOT / "dict" / f"{d.slug}.config.json").exists()
]
IDS = [d.relpath for d in CONFIG_DOCS]

#: Present in the recorded golden, absent from every projection.
#:
#: The same key the show side drops (FR-011): an ``xsi:`` attribute on the root
#: element that the converter maps like any other attribute. It is an XML
#: artifact with no meaning to a consumer, and the config projection drops it
#: for exactly the reason the show projection does — it is not a declared field
#: of any type. So the comparison is against the golden **minus** that key,
#: which is how T005 states the same thing on the show side.
SCHEMA_LOCATION = "schemaLocation"


def _wire_form(value):
    """The golden's decoded value, converted to its ``to_wire()`` form.

    Identity for every field except ``network_map``'s ``bool`` ones (feature
    007, research R1): decoding now produces a real ``bool`` where the
    golden used to record — and the wire form still is — the capitalised
    string ``_Bool.to_lexical``/``to_wire`` emit. That was an *identity*
    before this feature (the decoded value already was the string), which is
    exactly the property FR-011a gives up for ``network_map`` alone; every
    other config schema's golden carries no JSON ``bool`` at all, so this is
    a no-op for them.
    """
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, dict):
        return {k: _wire_form(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_wire_form(v) for v in value]
    return value


def _expected(doc) -> dict:
    golden = json.loads(
        (GOLDEN_ROOT / "dict" / f"{doc.slug}.config.json").read_text(encoding="utf-8")
    )
    return {k: _wire_form(v) for k, v in golden.items() if k != SCHEMA_LOCATION}


def test_the_corpus_actually_covers_all_four_config_schemas():
    """Without this, "every config document" could be one document."""
    assert {d.schema for d in CONFIG_DOCS} == {
        "settings",
        "network_map",
        "project_mappings",
        "project_settings",
    }


@pytest.mark.parametrize("doc", CONFIG_DOCS, ids=IDS)
def test_config_to_wire_matches_its_recorded_golden(doc):
    obj = rt.read_config_dict(doc)
    diffs = rt.wire_diff(obj.to_wire(), _expected(doc))
    assert not diffs, (
        f"{doc.relpath}: the config projection disagrees with "
        f"{doc.slug}.config.json (W1a):\n  " + "\n  ".join(diffs)
    )


@pytest.mark.parametrize("doc", CONFIG_DOCS, ids=IDS)
def test_the_golden_does_carry_the_key_the_projection_drops(doc):
    """The control for ``_expected``'s carve-out.

    If a golden stopped carrying ``schemaLocation``, the filter above would be
    silently doing nothing and the test would still pass — which is how a
    carve-out turns into a permanent exemption nobody re-reads.
    """
    golden = json.loads(
        (GOLDEN_ROOT / "dict" / f"{doc.slug}.config.json").read_text(encoding="utf-8")
    )
    assert SCHEMA_LOCATION in golden


@pytest.mark.parametrize("doc", CONFIG_DOCS, ids=IDS)
def test_config_to_json_is_the_projection_serialized(doc):
    obj = rt.read_config_dict(doc)
    assert json.loads(obj.to_json()) == json.loads(json.dumps(obj.to_wire()))


# --- T043b: one projection, asserted as such -------------------------------


def test_config_and_show_objects_share_one_to_wire_body():
    """Not "the same output" — the same function object."""
    assert ConfigDict.to_wire is CuemsDict.to_wire
    assert CuemsScript.to_wire is CuemsDict.to_wire
    assert ConfigDict.to_json is CuemsDict.to_json
    assert CuemsScript.to_json is CuemsDict.to_json


def test_no_class_overrides_the_projection():
    """A subclass override would be a second body wearing the same name."""
    import cuemsutils.config.mappings  # noqa: F401
    import cuemsutils.config.network_map  # noqa: F401
    import cuemsutils.config.settings  # noqa: F401
    import cuemsutils.cues  # noqa: F401

    def subclasses(cls):
        for sub in cls.__subclasses__():
            yield sub
            yield from subclasses(sub)

    offenders = [
        cls.__name__
        for cls in subclasses(CuemsDict)
        if "to_wire" in vars(cls) or "to_json" in vars(cls)
    ]
    assert not offenders, f"these classes redefine the projection: {offenders}"


def test_both_domains_reach_the_same_encode_wire():
    """Down to the ``Mapper`` method, not just the ``CuemsDict`` method."""
    source = inspect.getsource(CuemsDict.to_wire)
    assert "encode_wire" in source
    assert source.count("encode_wire") == 1, (
        "to_wire() names encode_wire more than once, which suggests a branch"
    )


#: Where a ``to_wire``/``to_json`` definition is allowed to appear, and why.
#:
#: ``helpers.py``
#:     the one object projection. This is the claim.
#: ``xml/adapters.py``
#:     ``Adapter.to_wire`` — a **scalar codec**, a different protocol with a
#:     different signature. It converts one value to its JSON form; it does not
#:     project an object. The object projection *calls* these, which is what
#:     makes encode and decode agree by construction.
#: ``tools/ConfigManager.py``
#:     the facade delegation (T056b). Asserted below to be a delegation and not
#:     an implementation.
PROJECTION_SITES = {
    "helpers.py",
    "xml/adapters.py",
    "tools/ConfigManager.py",
}


def _projection_definitions() -> dict[str, list[int]]:
    from pathlib import Path

    import cuemsutils

    root = Path(cuemsutils.__file__).parent
    found: dict[str, list[int]] = {}
    for path in sorted(root.rglob("*.py")):
        relative = str(path.relative_to(root))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("def to_wire") or stripped.startswith("def to_json"):
                found.setdefault(relative, []).append(number)
    return found


def test_no_second_projection_is_defined_anywhere_in_the_package():
    """SC-017 over the package, not over two classes.

    Two classes agreeing is a fact about today. This asks the stronger
    question: is there anywhere a second definition *could* be hiding?
    """
    found = _projection_definitions()
    assert set(found) <= PROJECTION_SITES, (
        "a projection is defined outside the permitted sites: "
        f"{sorted(set(found) - PROJECTION_SITES)}"
    )
    assert "helpers.py" in found and len(found["helpers.py"]) == 2, found


def test_the_config_facade_delegates_rather_than_projecting():
    """``ConfigManager.to_wire`` is a router, not a second implementation.

    It resolves a named section and calls **that object's** ``to_wire``. If it
    ever started assembling a payload itself, this feature's central claim
    would be false while every other assertion in this file still passed.
    """
    from cuemsutils.tools.ConfigManager import ConfigManager

    source = inspect.getsource(ConfigManager.to_wire)
    body = source[source.index('"""', source.index('"""') + 3) + 3 :]
    assert "project()" in body, body
    assert "encode_wire" not in body, body
    assert "Mapper" not in body, body


def test_the_facade_projection_equals_the_object_projection():
    from tests.support.config_inventory import build_config_manager

    manager = build_config_manager()
    for section in ("settings", "network_map", "node_conf", "mappings"):
        assert manager.to_wire(section) == getattr(manager, section).to_wire()


def test_the_facade_refuses_an_unknown_section_by_name():
    from tests.support.config_inventory import build_config_manager

    manager = build_config_manager()
    with pytest.raises(ValueError) as caught:
        manager.to_wire("not_a_section")
    assert "not_a_section" in str(caught.value)
    assert "network_map" in str(caught.value)
