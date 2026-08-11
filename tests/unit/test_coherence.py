"""Python ↔ schema coherence (T057) — FR-020, data-model §6.

A model class and the XSD type it is bound to must declare the **same field
set**. Nothing enforced that before: the two were maintained by hand in two
files, and the only thing that noticed a divergence was a document failing to
validate at save time, long after the mistake.

**Sets, not order.** Order is the engine's job now (FR-001), derived from the
content model. ``REQ_ITEMS`` keeps exactly the two jobs the audit established —
layered defaults and the alphabetical developer index — and loses the
accidental third one it had acquired, which was deciding element order.

Reach: classes bound in the registry, which today means the show-document
classes. Configuration documents have no model classes until feature 006, so
their bindings are all ``GENERIC`` and there is nothing to compare.

T058 proves this fails on injected drift; without that it would only prove the
two happen to agree today.
"""

from __future__ import annotations

import inspect
import re
import sys

import pytest

from cuemsutils.xml.registry import get_registry
from cuemsutils.xml.spec import derive

#: Any module-level mapping of defaults, whatever it is called. The cue classes
#: use ``REQ_ITEMS``; ``DmxChannel`` uses ``DMXCHANNEL_REQ_ITEMS``, ``DmxScene``
#: uses ``SCENE_REQ_ITEMS``, and so on. Matching the *name* rather than
#: hardcoding a list means a new class with a new spelling is covered the day
#: it is written.
_REQ_ITEMS_NAME = re.compile(r"\b([A-Z_]*REQ_ITEMS)\b")


def declared_fields(model: type) -> set[str]:
    """``REQ_ITEMS`` keys accumulated across the MRO.

    Accumulated because a cue subclass declares only what it *adds*:
    ``AudioCue``'s ``REQ_ITEMS`` holds ``Media``, ``outputs``, ``master_vol``
    and ``fade_profiles``, while the thirteen common properties come from
    ``Cue``. Reading one class's dict alone reports thirteen spurious
    "missing" fields.

    Resolved per class in the MRO, against **that class's own module**, because
    several modules hold more than one defaults dict — ``DmxCue.py`` has four,
    and picking the module-level ``REQ_ITEMS`` for ``DmxChannel`` would compare
    a channel against a cue.
    """
    accumulated: set[str] = set()
    for klass in reversed(model.__mro__):
        init = klass.__dict__.get("__init__")
        if init is None:
            continue
        try:
            source = inspect.getsource(init)
        except (TypeError, OSError):
            continue
        module = sys.modules.get(klass.__module__)
        if module is None:
            continue
        for name in _REQ_ITEMS_NAME.findall(source):
            accumulated.update(getattr(module, name, {}) or {})
    return accumulated


def bound_models():
    """(type name, model class, derived field names) for every real binding."""
    registry = get_registry("script")
    for type_name in sorted(registry.bound_type_names):
        model = registry.model_for(type_name)
        if model is None:
            continue
        spec = derive(registry.binding_for(type_name).key)
        yield type_name, model, {f.name for f in spec.fields}


COVERED = [
    (type_name, model, fields)
    for type_name, model, fields in bound_models()
    if declared_fields(model)
]
UNCOVERED = [
    (type_name, model)
    for type_name, model, _ in bound_models()
    if not declared_fields(model)
]

IDS = [f"{t}->{m.__name__}" for t, m, _ in COVERED]


@pytest.mark.parametrize("type_name,model,derived", COVERED, ids=IDS)
def test_declared_and_derived_field_sets_are_equal(type_name, model, derived):
    declared = declared_fields(model)
    assert declared == derived, (
        f"{model.__name__} and {type_name} disagree.\n"
        f"  only in {model.__name__}: {sorted(declared - derived)}\n"
        f"  only in {type_name}:      {sorted(derived - declared)}"
    )


def test_coverage_is_not_silently_empty():
    """A parametrisation that shrank to nothing would pass in silence."""
    assert len(COVERED) >= 10


def test_every_cue_type_is_covered():
    """The classes that matter most, named so they cannot drop out."""
    covered = {model.__name__ for _, model, _ in COVERED}
    assert {
        "Cue",
        "CueList",
        "AudioCue",
        "VideoCue",
        "DmxCue",
        "ActionCue",
        "FadeCue",
        "MediaCue",
    } <= covered


def test_uncovered_classes_are_the_expected_ones():
    """Which classes this check cannot reach, stated rather than left implicit.

    ``Media``, ``Region`` and the three ``CueOutput`` subclasses declare no
    defaults dict at all — they take their fields from the init dict directly.
    They are therefore invisible to a ``REQ_ITEMS``-based comparison, and
    saying so here is better than a passing suite that quietly covers thirteen
    of eighteen bindings.

    Giving them defaults dicts is an object-model change, which feature 004
    explicitly does not make.
    """
    assert {model.__name__ for _, model in UNCOVERED} == {
        "Media",
        "Region",
        "AudioCueOutput",
        "VideoCueOutput",
        "DmxCueOutput",
    }


def test_order_is_not_part_of_the_comparison():
    """FR-020 — sets, deliberately.

    ``REQ_ITEMS`` is maintained alphabetically as a developer index. The schema
    declares a different order, and that difference is now correct rather than
    a bug: element order comes from the content model. Comparing sequences here
    would fail on every cue type and push someone toward "fixing" ``REQ_ITEMS``
    to match the schema — reintroducing the coupling this feature removed.
    """
    _, model, derived = COVERED[0]
    declared = declared_fields(model)
    assert isinstance(declared, set)
    assert sorted(declared) == sorted(derived)
