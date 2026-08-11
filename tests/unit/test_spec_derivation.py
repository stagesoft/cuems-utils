"""Derivation unit tests (T033) — contract C6, research R2/R3/R7/R8.

``spec.py`` is where "the schema is the single source of truth" either is or
is not true. These tests check the derivation itself; the goldens check what
comes out the other end. Both are needed: a golden failure says the bytes
changed, these say which rule broke.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.spec import (
    FieldKind,
    ModelGroup,
    TypeKey,
    clear_cache,
    derivation_count,
    derive,
    derive_named,
    derive_path,
    derive_root,
)

SCRIPT_ROOT_FIELDS = (
    "CueList",
    "created",
    "description",
    "id",
    "modified",
    "name",
    "ui_properties",
)


# --- ordered content models: declaration order ----------------------------


def test_sequence_type_reports_declaration_order():
    spec = derive_named("script", "AudioCueType")
    assert spec.ordered
    assert spec.field_names[:3] == ("autoload", "description", "enabled")
    assert spec.field_names[-2:] == ("master_vol", "fade_profiles")


def test_order_keys_sorts_by_declaration_not_by_name():
    """The assertion that separates "derived" from "alphabetical".

    ``master_vol`` sorts *after* ``fade_profiles`` alphabetically and *before*
    it in the schema. Any implementation that sorted by name would fail here,
    which is the whole point of choosing this pair.
    """
    spec = derive_named("script", "AudioCueType")
    assert spec.order_keys(["fade_profiles", "master_vol"]) == [
        "master_vol",
        "fade_profiles",
    ]
    assert sorted(["fade_profiles", "master_vol"]) == ["fade_profiles", "master_vol"]


def test_order_keys_is_stable_regardless_of_input_order():
    spec = derive_named("script", "AudioCueType")
    forward = spec.order_keys(["name", "id", "master_vol"])
    backward = spec.order_keys(["master_vol", "id", "name"])
    assert forward == backward == ["id", "name", "master_vol"]


def test_unknown_keys_keep_arrival_order_and_sort_last():
    """Wildcard content and the leaked ``schemaLocation`` land here.

    Dropping unknown keys would silently lose data; interleaving them would
    change byte order. Appending in arrival order does neither.
    """
    spec = derive_named("script", "AudioCueType")
    result = spec.order_keys(["zzz", "master_vol", "aaa", "id"])
    assert result == ["id", "master_vol", "zzz", "aaa"]


# --- order-free content models: arrival order (FR-001b) -------------------


@pytest.mark.parametrize(
    "spec_factory",
    [
        lambda: derive_path("script", "CuemsProject/CuemsScript"),
        lambda: derive_named("script", "DmxSceneType"),
    ],
    ids=["CuemsScript", "DmxSceneType"],
)
def test_the_two_order_free_types_are_identified(spec_factory):
    """Both instances named, so neither can be missed.

    These are the only two ``xs:all`` content models across all six schemas.
    """
    spec = spec_factory()
    assert spec.model_group is ModelGroup.ALL
    assert not spec.ordered


def test_order_free_types_preserve_arrival_order():
    """FR-001b — **not** a sorted-key tie-break.

    An earlier draft specified sorting, on the evidence of library-written
    files whose roots are alphabetical. Two of the four captured
    ``CuemsScript`` goldens are not sorted, because today's builder iterates
    the object's items and so preserves the *source document's* order. Sorting
    would rewrite the root element of every hand-authored script.
    """
    spec = derive_path("script", "CuemsProject/CuemsScript")
    hand_authored = ["id", "name", "description", "created", "modified", "ui_properties", "CueList"]
    assert spec.order_keys(hand_authored) == hand_authored
    assert hand_authored != sorted(hand_authored)

    library_written = list(SCRIPT_ROOT_FIELDS)
    assert spec.order_keys(library_written) == library_written


def test_order_free_ordering_is_not_reachable_for_ordered_types():
    """FR-001a — arrival order is confined to the ``xs:all`` branch.

    An ordered type must reorder its input; if it passed keys through
    unchanged, dict iteration order would be deciding the output.
    """
    spec = derive_named("script", "AudioCueType")
    shuffled = ["fade_profiles", "master_vol", "autoload"]
    assert spec.order_keys(shuffled) != shuffled


def test_the_branch_keys_off_the_content_model_not_a_type_name():
    """C6 — no name comparison decides ordering.

    Both branches are selected by ``model_group``, which is schema data. A
    hardcoded list of "the order-free types" would be F1's hack in a new
    costume.
    """
    for spec in (
        derive_named("script", "AudioCueType"),
        derive_path("script", "CuemsProject/CuemsScript"),
        derive_named("script", "DmxSceneType"),
    ):
        assert spec.ordered == (spec.model_group is not ModelGroup.ALL)


# --- anonymous types (R3) -------------------------------------------------


def test_anonymous_root_types_are_keyed_by_element_path():
    """There is no ``CuemsScriptType`` to bind by name."""
    spec = derive_root("script")
    assert spec.key.is_path
    assert spec.key.name == "CuemsProject"
    assert spec.field_names == ("CuemsScript",)

    script = derive_path("script", "CuemsProject/CuemsScript")
    assert script.key.is_path
    assert set(script.field_names) == set(SCRIPT_ROOT_FIELDS)


# --- cardinality and wildcards -------------------------------------------


def test_cardinality_comes_from_the_schema():
    spec = derive_named("script", "AudioCueType")
    assert spec.field("fade_profiles").required is False
    assert spec.field("master_vol").required is True


def test_repeated_elements_are_marked():
    """Repetition is read from the *group*, not from the element.

    ``CueListContentsType`` is an ``xs:choice`` with ``maxOccurs="unbounded"``
    whose six members are each declared ``1..1``. Reading ``max_occurs`` off
    the element alone reports every cue type as single — so a cue list holding
    twenty cues would derive as holding one, and FR-014's repeated-element
    shape would be lost for the most common structure in the format.
    """
    spec = derive_named("script", "CueListContentsType")
    assert all(f.repeated for f in spec.fields if f.kind is FieldKind.ELEMENT)
    assert all(f.name for f in spec.fields)


def test_singular_elements_are_not_marked_repeated():
    """The control: without it, ``repeated=True`` everywhere would pass above."""
    spec = derive_named("script", "AudioCueType")
    assert not any(f.repeated for f in spec.fields if f.kind is FieldKind.ELEMENT)


def test_wildcard_content_is_marked_and_carries_no_derived_shape():
    """R6 — nothing about ``UiPropertiesType``'s children is derivable.

    No name, no type, no cardinality. Recording that explicitly is what stops
    the mapper from inventing a shape for it (FR-009).
    """
    spec = derive_named("script", "UiPropertiesType")
    assert spec.wildcard
    assert spec.mixed
    wildcards = [f for f in spec.fields if f.is_wildcard]
    assert len(wildcards) == 1
    assert wildcards[0].name == ""
    assert wildcards[0].xsd_type is None


# --- attributes, including the name clash (R7) ----------------------------


def test_attributes_are_recorded_separately_from_elements():
    spec = derive_named("script", "DmxUniverseType")
    kinds = {(f.name, f.kind) for f in spec.fields}
    assert ("universe_num", FieldKind.ELEMENT) in kinds
    assert ("universe_num", FieldKind.ATTRIBUTE) in kinds


def test_the_universe_num_clash_is_preserved_not_resolved():
    """``DmxUniverseType`` declares an attribute *and* an element of one name.

    With the converter's ``attr_prefix=''`` the decoded key is ambiguous. That
    is pre-existing behaviour: 004 reproduces it, and the DMX corpus goldens
    are the arbiter. Disambiguating with a prefix would be a wire change.
    """
    spec = derive_named("script", "DmxUniverseType")
    named = [f for f in spec.fields if f.name == "universe_num"]
    assert len(named) == 2
    assert {f.kind for f in named} == {FieldKind.ELEMENT, FieldKind.ATTRIBUTE}


def test_anyattribute_wildcard_does_not_become_a_named_attribute():
    spec = derive_named("script", "UiPropertiesType")
    assert spec.attributes == ()


# --- cyclic models and memoisation (R8, SC-PERF-002) ---------------------


def test_cyclic_content_model_terminates():
    """``CueListType`` -> ``CueListContentsType`` -> ``CueListType``.

    A genuine cycle. Derivation holds a child *reference* rather than an
    inlined spec, so it terminates; eager recursion would not.
    """
    cuelist = derive_named("script", "CueListType")
    contents = cuelist.field("contents")
    assert contents.child == TypeKey("script", "CueListContentsType")

    contents_spec = derive(contents.child)
    back = contents_spec.field("CueList")
    assert back.child == TypeKey("script", "CueListType")


def test_derivation_is_memoised_per_type():
    clear_cache()
    first = derive_named("script", "AudioCueType")
    before = derivation_count()
    for _ in range(50):
        derive_named("script", "AudioCueType")
    assert derivation_count() == before
    assert derive_named("script", "AudioCueType") is first


def test_derivation_count_is_bounded_by_distinct_types_not_calls():
    """SC-PERF-002, in its smallest form.

    The full assertion over real objects is T064; this one pins the mechanism.
    """
    clear_cache()
    names = ["AudioCueType", "VideoCueType", "CueListType", "AudioCueType", "VideoCueType"]
    for name in names:
        derive_named("script", name)
    assert derivation_count() == len(set(names))


# --- the same rules hold for the other five schemas ----------------------


@pytest.mark.parametrize(
    "schema",
    ["settings", "network_map", "project_mappings", "project_settings", "outputs"],
)
def test_every_schema_root_derives(schema):
    spec = derive_root(schema)
    assert spec.fields, f"{schema} root derived no fields"


def test_outputs_type_differs_between_schemas():
    """R4 — the collision that makes per-schema isolation mandatory.

    Both schemas declare ``OutputsType`` in the same namespace with different
    content. Deriving them through one shared object would silently give one
    schema the other's fields.
    """
    script_outputs = derive_named("script", "OutputsType")
    outputs_outputs = derive_named("outputs", "OutputsType")
    assert script_outputs.field_names != outputs_outputs.field_names
    assert outputs_outputs.field_names == ("output",)
