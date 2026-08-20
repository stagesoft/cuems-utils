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

import pytest

from cuemsutils.xml.registry import get_registry
from cuemsutils.xml.spec import derive


def declared_fields(model: type) -> set[str]:
    """The model's own answer (T007) — this test no longer owns a second one.

    Until feature 005 this function reconstructed the field set by reading each
    ``__init__``'s **source** and regex-matching ``REQ_ITEMS`` names. It worked,
    and it was the problem: the declared field set existed only as a convention,
    recoverable by anyone willing to parse source, and this test's reconstruction
    was one of two independent implementations of it. The engine had the other.
    Two rules that agree only because a test says so is exactly what this
    feature removes, so the classes now **declare** it and both consumers ask.

    Kept as a function rather than inlined so the parametrisation below reads
    unchanged, and so a class with no declaration still answers with an empty
    set — which is what puts ``Media``, ``Region`` and the three ``CueOutput``
    subclasses in ``UNCOVERED`` until they gain declared field sets.
    """
    declared = getattr(model, "declared_fields", None)
    return set(declared()) if declared is not None else set()


#: Every schema whose types have model classes.
#:
#: ``script`` alone until feature 006. The four configuration schemas were
#: excluded because *there was nothing to compare*: every one of their types
#: was bound to ``GENERIC``, and this test's reach is real bindings. T048 gives
#: all twenty-two of them model classes, so the exclusion is gone rather than
#: merely smaller — which is the point of extending the test rather than
#: writing a second one for config (T041).
SCHEMAS = ("script", "settings", "project_settings", "project_mappings", "network_map")


def bound_models():
    """(type name, model class, derived field names) for every real binding."""
    for schema_name in SCHEMAS:
        registry = get_registry(schema_name)
        for type_name in sorted(registry.bound_type_names):
            model = registry.model_for(type_name)
            if model is None:
                continue
            spec = derive(registry.binding_for(type_name).key)
            yield f"{schema_name}:{type_name}", model, {f.name for f in spec.fields}


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


def test_every_config_schema_is_covered():
    """T041 — the four config schemas, named so they cannot drop out again.

    Twenty-two complex types across four schemas, every one of which was
    ``GENERIC`` before this feature. Naming the schemas rather than asserting a
    count keeps this honest if a type is added: the new type appears in
    ``COVERED`` or in ``UNCOVERED``, and both are asserted.
    """
    covered_schemas = {name.split(":", 1)[0] for name, _, _ in COVERED}
    assert {
        "settings",
        "project_settings",
        "project_mappings",
        "network_map",
    } <= covered_schemas, sorted(covered_schemas)


def test_the_two_node_types_are_different_classes():
    """``NodeType`` exists in two schemas and means two different things.

    ``network_map.xsd``'s describes node **identity**; ``project_mappings.xsd``'s
    describes node **mappings**. Binding one class to both would make its
    coercion table ambiguous by construction (registries are per schema,
    research R4) — and would be F15's failure in miniature, one type standing
    for two shapes.
    """
    identity = get_registry("network_map").model_for("NodeType")
    mapping = get_registry("project_mappings").model_for("NodeType")
    assert identity is not None and mapping is not None
    assert identity is not mapping
    assert set(identity.declared_fields()) != set(mapping.declared_fields())


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
    """Nothing is uncovered any more — coverage is 18/18 (T029, research R4).

    Until feature 005 this asserted an uncovered set of exactly ``{Media,
    Region, AudioCueOutput, VideoCueOutput, DmxCueOutput}``: five classes that
    declared no defaults dict at all and took their fields straight from the
    init dict, leaving this check silently covering thirteen of eighteen
    bindings. The comment said so — *"giving them defaults dicts is an
    object-model change, which feature 004 explicitly does not make"* — and
    named this feature as the one that would.

    T026 and T027 gave all five a declared field set, so the exclusion is gone
    rather than merely smaller. Asserted as **empty** rather than deleted: a
    deleted test would let the set silently refill.
    """
    assert {model.__name__ for _, model in UNCOVERED} == set()


def test_coverage_reaches_every_bound_model():
    """The positive half of the same claim: every binding compared.

    ``18`` until feature 006 — the script schema's bindings, all of them. T048
    binds the four configuration schemas' twenty-two complex types plus their
    four anonymous document roots, so the number is now **40**: 18 show
    classes and 22 config ones.

    Kept as an exact count rather than a lower bound, and rewritten rather than
    relaxed. A count that only ever grows would let a binding disappear in
    silence, which is the whole reason this assertion is stated positively
    alongside the ``UNCOVERED`` one.
    """
    assert len(COVERED) == 40
    assert not UNCOVERED


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
