"""T007 / FR-022a / SC-003 — a constructible empty instance per complex type.

Feature 010, US3. The one descriptor capability this feature adds, and the sixth
fact ``TypeDescriptor`` emits. It exists because a **nested object is not a
field default**: ``getTemplateOutputStructure`` in the UI needs the *shape* of a
cue's output — geometry, region, mapping — which no combination of the five
per-field facts supplies.

**What this file does not assert, and why.** An earlier draft required every
instance to validate against its schema. It cannot: measured 2026-09-04, **12 of
the 58** complex types have a required field with no usable default, so a
defaults-only instance is incomplete for them by construction. The instance is a
**seed the consumer fills**, and SC-003 now says so. The criterion was widened
and then narrowed across three passes; this note is here so the final position
is legible rather than looking like an omission.
"""

from __future__ import annotations

import pytest

from cuemsutils.helpers import Unset
from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.schema import SCHEMA_NAMES
from cuemsutils.xml.spec import FieldKind, derive


def _child_fields(key) -> set[str]:
    """Field names whose type is complex, so the instance expands them."""
    return {f.name for f in derive(key).fields if f.child is not None}


def _public():
    """Imported at call time — see ``test_public_descriptor`` for why."""
    from cuemsutils.tools.ConfigManager import ConfigManager, SchemaName

    return ConfigManager, SchemaName


def _types(schema_name: str):
    return SchemaDescriptor().types(schema_name)


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_every_complex_type_yields_an_instance(schema_name):
    """100% of types, counted — not the one type the UI happened to need."""
    described = _types(schema_name)
    assert described, f"{schema_name} declares no complex types"

    for type_descriptor in described:
        assert isinstance(type_descriptor.instance, dict), type_descriptor.key


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_the_instance_carries_every_declared_field(schema_name):
    """Shape completeness. A seed missing a field is a seed the consumer cannot
    fill without knowing the schema — which is what it exists to avoid."""
    for type_descriptor in _types(schema_name):
        # Wildcards are excluded: a wildcard has no name to seed and no type to
        # expand, so the instance omits it rather than inventing a key.
        expected = {
            f.name for f in type_descriptor.fields if f.kind is not FieldKind.WILDCARD
        }
        missing = expected - set(type_descriptor.instance)
        assert not missing, f"{type_descriptor.key} instance is missing {sorted(missing)}"


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_scalar_fields_carry_their_declared_default(schema_name):
    """Where a default is a plain value, the instance uses it — this is the half
    of FR-022a that ``master_vol``'s drifted ``|| 20`` fallback in the UI exists
    to be replaced by."""
    for type_descriptor in _types(schema_name):
        for field in type_descriptor.fields:
            value = type_descriptor.instance.get(field.name)
            if isinstance(value, (dict, list)):
                continue  # nested; covered below
            if field.default is None or callable(field.default):
                continue  # deliberately None — see the next test
            if field.default is Unset:
                continue  # no value to seed with
            assert value == field.default, (
                f"{type_descriptor.key}.{field.name} is {value!r}, "
                f"declared default is {field.default!r}"
            )


def test_callable_defaults_are_not_invoked():
    """Decisive reason: derivation is cached, so calling ``new_uuid()`` once
    would freeze one "fresh" identifier and hand the same one to every caller.
    The callable stays visible on the field for anyone who wants to call it."""
    for schema_name in SCHEMA_NAMES:
        for type_descriptor in _types(schema_name):
            expanded = _child_fields(type_descriptor.key)
            for field in type_descriptor.fields:
                if not callable(field.default) or field.name in expanded:
                    # A field with a complex child expands into a nested
                    # instance, which is the more informative value and the
                    # correct one: ``ActionCueType.offset`` defaults to the
                    # CTimecode *class* and is also a CTimecodeType element, so
                    # its seed is ``{"CTimecode": None}``, not ``None``.
                    continue
                assert type_descriptor.instance[field.name] is None, (
                    f"{type_descriptor.key}.{field.name} invoked its factory"
                )


def test_a_complex_field_expands_into_its_own_instance():
    """The property that makes this a replacement for deep-cloning an example.

    ``AudioCueOutputsType`` is the concrete case ``getTemplateOutputStructure``
    needs: it must reach ``channels.channel[0]``'s own fields, not stop at a
    field named ``channels``.
    """
    outputs = next(
        t for t in _types("script") if t.key.name == "AudioCueOutputsType"
    )
    channels = outputs.instance["channels"]
    assert isinstance(channels, dict), channels
    assert isinstance(channels["channel"], list), channels
    assert channels["channel"], "a repeated complex field must carry one exemplar"
    assert "channel_num" in channels["channel"][0]


def test_a_cyclic_content_model_terminates():
    """``CueListType`` → ``CueListContentsType`` → ``CueListType`` is a real
    cycle (research R8 of feature 008). Building an instance must not recurse
    into it forever, and the revisit must yield an empty object rather than
    raising."""
    cuelist = next(t for t in _types("script") if t.key.name == "CueListType")
    assert isinstance(cuelist.instance, dict)


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_the_instance_is_reachable_from_the_public_path(schema_name):
    """FR-022a is a descriptor fact, so it arrives with the descriptor — no
    second public accessor, and no extra exposure to SC-004."""
    ConfigManager, SchemaName = _public()
    described = ConfigManager(load_all=False).get_schema_descriptor(SchemaName(schema_name))
    assert all(isinstance(t.instance, dict) for t in described)
