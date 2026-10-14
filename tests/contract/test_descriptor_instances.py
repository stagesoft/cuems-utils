"""T007/FR-022a/SC-003, **reversed by G3** (feature 015) — a constructible,
**wire-shaped and saveable** instance per complex type.

Feature 010, US3 introduced the instance as a null-filled seed the consumer
fills — "not required to be schema-valid". G3 reverses that position
(FR-026): the instance is now wire-shaped by construction (projected
through the same ``Mapper.encode_wire`` ``to_wire()`` uses, research R2)
and saveable (FR-023/FR-024), with every field populated from either the
bound model's own default or a seed derived from the field's declared XSD
type (contracts/seeding-rules.md) — never a null placeholder.

**What this file still does not assert, and why.** Nothing here claims an
instance never needs editing — a consumer still supplies the *meaningful*
values (a real file name, a real target uuid). What changed is that the
seed is now a value satisfying the field's type, not an absence.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.schema import SCHEMA_NAMES
from cuemsutils.xml.spec import FieldKind
from tests.support.corpus import REPO_ROOT  # feature 011, T007: no host /etc/cuems


def _public():
    """Imported at call time — see ``test_the_instance_is_reachable_from_the_public_path``."""
    from cuemsutils.tools.ConfigManager import ConfigManager, SchemaName

    return ConfigManager, SchemaName


def _types(schema_name: str):
    return SchemaDescriptor().types(schema_name)


def _unwrapped(instance, expected_names=frozenset()):
    """Peel away G3's wire wrapping (a bare list, or a single-key dict
    whose key is not one of this type's own declared fields) to reach the
    dict that actually carries this type's fields, for shape-level checks
    that do not care about the wrapper itself."""
    if isinstance(instance, list):
        assert instance, "a wrapped repeated instance must carry one exemplar"
        only = instance[0]
        assert isinstance(only, dict) and len(only) == 1, only
        (key,) = only
        # When the wrap tag *is* this type's own declared field (a type
        # that is itself wrapper-shaped and unbound, collapsed to a bare
        # list at the top level), peeling further would remove the very
        # thing being checked for.
        return only if key in expected_names else only[key]
    if isinstance(instance, dict) and len(instance) == 1:
        (key,) = instance
        if key not in expected_names:
            return instance[key]
    return instance


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_every_complex_type_yields_an_instance(schema_name):
    """100% of types, counted — not the one type the UI happened to need.

    A ``dict`` for most types; a bare ``list`` for the pure wrapper
    containers G3 collapses (``OutputsType``, ``AudioChannelsType``, …) —
    see :class:`cuemsutils.xml.descriptor.TypeDescriptor`'s own docstring.
    """
    described = _types(schema_name)
    assert described, f"{schema_name} declares no complex types"

    for type_descriptor in described:
        assert isinstance(type_descriptor.instance, (dict, list)), type_descriptor.key


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_the_instance_carries_every_declared_field(schema_name):
    """Shape completeness, G3's own invariant (FR-020..FR-027): every
    declared non-wildcard field is present, required and optional alike —
    checked on the dict that actually carries this type's own fields, once
    any wire wrapping is peeled away."""
    for type_descriptor in _types(schema_name):
        expected = {
            f.name for f in type_descriptor.fields if f.kind is not FieldKind.WILDCARD
        }
        instance = type_descriptor.instance
        if isinstance(instance, list) and all(
            isinstance(item, dict) and len(item) == 1 and next(iter(item)) in expected
            for item in instance
        ):
            # A multi-member wrapper-shaped container (``OutputsType``,
            # ``CueListContentsType``) carries one exemplar **per**
            # declared field rather than one dict with every field as a
            # key — the union of the list's own tags is what "every field
            # present" means for this shape.
            present = {next(iter(item)) for item in instance}
        else:
            present = set(_unwrapped(instance, expected))
        missing = expected - present
        assert not missing, f"{type_descriptor.key} instance is missing {sorted(missing)}"


def test_callable_defaults_are_not_invoked():
    """FR-027 — the callable itself is never called (``derive`` is cached,
    so calling ``new_uuid()`` once would freeze one "fresh" identifier for
    every later caller). Measured as: two independently-derived instances
    of a type with a callable-defaulted field agree on that field's seed —
    which could only happen if neither call actually invoked the factory.
    """
    found = 0
    for schema_name in SCHEMA_NAMES:
        for type_descriptor in _types(schema_name):
            for field in type_descriptor.fields:
                if not callable(field.default):
                    continue
                found += 1
                expected = {f.name for f in type_descriptor.fields}
                first = SchemaDescriptor().describe(type_descriptor.key)
                second = SchemaDescriptor().describe(type_descriptor.key)
                body1 = _unwrapped(first.instance, expected)
                body2 = _unwrapped(second.instance, expected)
                assert body1.get(field.name) == body2.get(field.name), (
                    f"{type_descriptor.key}.{field.name} differs between two "
                    f"derivations — its factory default was invoked"
                )
    assert found > 0, "no callable-defaulted field was exercised"


def test_a_complex_field_expands_into_its_own_instance():
    """The property that makes this a replacement for deep-cloning an
    example: ``AudioCueOutputsType``'s own instance reaches
    ``channels[0]``'s own fields — the shape ``getTemplateOutputStructure``
    needs — projected the way the wire actually nests a repeated complex
    field (FR-020, research R2): a list of singly-keyed objects, not an
    object holding a list.
    """
    outputs = next(t for t in _types("script") if t.key.name == "AudioCueOutputsType")
    expected = {f.name for f in outputs.fields}
    body = _unwrapped(outputs.instance, expected)
    channels = body["channels"]
    assert isinstance(channels, list), channels
    assert channels, "a repeated complex field must carry one exemplar"
    assert "channel_num" in channels[0]["channel"]


def test_a_cue_output_instance_carries_the_wire_wrapper():
    """FR-021/contract C3 — queried standalone, a cue-output instance
    carries the same ``CueOutput`` wrapper the wire carries when it is
    embedded in a real cue's ``outputs`` list (research R2, data-model.md
    §3). This is what the old, unwrapped instance measurably lacked."""
    for name in ("AudioCueOutputsType", "VideoCueOutputsType", "DmxCueOutputsType"):
        td = next(t for t in _types("script") if t.key.name == name)
        assert isinstance(td.instance, dict) and list(td.instance) == ["CueOutput"], (
            name,
            td.instance,
        )


def test_a_cyclic_content_model_terminates():
    """``CueListType`` → ``CueListContentsType`` → ``CueListType`` is a real
    cycle (research R8 of feature 008). Building an instance must not recurse
    into it forever, and the revisit must yield an empty object rather than
    raising."""
    cuelist = next(t for t in _types("script") if t.key.name == "CueListType")
    assert isinstance(cuelist.instance, dict)


def test_a_type_reached_twice_down_two_branches_expands_both_times():
    """FR-030/data-model.md §3 invariant 7 — the cycle guard bounds by
    *branch*, not by a global visited set. ``CueListContentsType``'s own
    standalone instance carries one exemplar per declared member,
    including its self-recursive ``CueList`` one — exercising ``CueListType``
    down two *different* branches of the same query (the ``CueList`` member
    itself, and whatever that member's own nested ``contents`` resolves
    to). Neither may be a hole left by a global "already visited" guard.
    """
    contents = next(t for t in _types("script") if t.key.name == "CueListContentsType")
    by_tag = {next(iter(item)): next(iter(item.values())) for item in contents.instance}

    assert isinstance(by_tag["Cue"], dict) and by_tag["Cue"], "the Cue member must expand"
    assert isinstance(by_tag["CueList"], dict) and by_tag["CueList"], (
        "the self-recursive CueList member must expand, not hole"
    )


def test_nothing_non_serialisable_enters_the_instance():
    """FR-030 — this object is served over a websocket to the UI. No
    field spec, model class, or other non-JSON-safe value may leak into
    an instance."""
    import json

    for schema_name in SCHEMA_NAMES:
        for type_descriptor in _types(schema_name):
            json.dumps(type_descriptor.instance, default=lambda o: (_ for _ in ()).throw(
                TypeError(f"non-serialisable value in {type_descriptor.key}: {o!r}")
            ))


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_the_instance_is_reachable_from_the_public_path(schema_name):
    """FR-022a is a descriptor fact, so it arrives with the descriptor — no
    second public accessor, and no extra exposure to SC-004."""
    ConfigManager, SchemaName = _public()
    described = ConfigManager(config_dir=str(REPO_ROOT / "tests/data/corpus/cuems-engine"), load_all=False).get_schema_descriptor(SchemaName(schema_name))
    assert all(isinstance(t.instance, (dict, list)) for t in described)
