"""Contract C7 (T034) — registry totality, proven to fail when it should.

Every complex type in every schema must be bound. The point is not the count:
it is that a *missing* binding raises, naming the type. The three ``globals()``
lookups this replaces failed by returning a generic, so a missing handler was
indistinguishable from a deliberate one — ``mediaParser`` has been unreachable
for thirteen call sites' worth of corpus and nothing ever said so.

``test_removing_a_binding_raises`` is the fail-before-pass evidence the
constitution requires for this assertion (plan §II). Without it, this file
would only prove that the registry currently happens to be complete.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.registry import (
    GENERIC,
    RegistryIncompleteError,
    SchemaRegistry,
    all_registries,
    get_registry,
)
from cuemsutils.xml.schema import SCHEMA_NAMES, get_schema


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_every_complex_type_is_bound(schema_name):
    registry = get_registry(schema_name)
    assert registry.unbound_type_names() == frozenset()


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_registry_validates_on_build(schema_name):
    get_registry(schema_name).validate()


def test_removing_a_binding_raises_and_names_the_type():
    """Fail-before-pass, for an assertion that otherwise proves nothing.

    A totality check that has never been seen to fail is indistinguishable
    from ``assert True``.
    """
    registry = SchemaRegistry("script")
    registry.bind_path("CuemsProject", GENERIC)
    for name in registry.complex_type_names():
        if name != "AudioCueType":
            registry.bind(name, GENERIC)

    with pytest.raises(RegistryIncompleteError) as excinfo:
        registry.validate()

    assert "AudioCueType" in str(excinfo.value)
    assert excinfo.value.missing == ["AudioCueType"]


def test_the_error_names_every_missing_type_not_just_the_first():
    """One run should tell you everything to fix.

    Reporting the first miss turns a 56-type audit into 56 runs.
    """
    registry = SchemaRegistry("network_map")
    with pytest.raises(RegistryIncompleteError) as excinfo:
        registry.validate()
    assert set(excinfo.value.missing) == set(registry.complex_type_names())


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_binding_count_matches_the_schema(schema_name):
    """Neither more nor fewer bindings than the schema has complex types.

    An *extra* binding is as much a defect as a missing one: it names a type
    that does not exist, so it is dead code that reads as coverage.
    """
    registry = get_registry(schema_name)
    schema = get_schema(schema_name)
    complex_names = {n for n, t in schema.types.items() if not t.is_simple()}
    assert registry.bound_type_names == complex_names


def test_the_colliding_outputs_type_is_bound_separately_per_schema():
    """R4 — the collision that makes per-schema registries mandatory.

    Both schemas declare ``OutputsType`` in the same namespace with different
    content. A shared registry would give one of them the other's binding, and
    the failure would surface as wrong output rather than as an error.
    """
    script_binding = get_registry("script").binding_for("OutputsType")
    outputs_binding = get_registry("outputs").binding_for("OutputsType")

    assert script_binding is not None
    assert outputs_binding is not None
    assert script_binding.key != outputs_binding.key
    assert script_binding.key.schema == "script"
    assert outputs_binding.key.schema == "outputs"


def test_anonymous_root_types_are_bound_by_path():
    """R3 — ``CuemsScript`` has no type qname to bind by."""
    registry = get_registry("script")
    assert registry.binding_for_path("CuemsProject") is not None
    binding = registry.binding_for_path("CuemsProject/CuemsScript")
    assert binding is not None
    assert binding.key.is_path
    assert not binding.is_generic


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_every_schema_root_is_bound_by_path(schema_name):
    registry = get_registry(schema_name)
    assert registry.binding_for_path(registry.root) is not None


def test_generic_bindings_are_explicit_not_absent():
    """FR-007 — "accounted for", not "given a bespoke class".

    ``UiPropertiesType`` reaches ``GenericDict`` today and must keep doing so:
    the ``UI_properties`` class exists but has never been reached, because the
    lookup searches for the lowercase tag. Binding it to the class would start
    running code that has never run.
    """
    registry = get_registry("script")
    binding = registry.binding_for("UiPropertiesType")
    assert binding is not None
    assert binding.is_generic
    assert registry.model_for("UiPropertiesType") is None


def test_model_bindings_resolve_to_real_classes():
    registry = get_registry("script")
    for type_name in ("AudioCueType", "VideoCueType", "DmxCueType", "CueListType"):
        model = registry.model_for(type_name)
        assert isinstance(model, type), f"{type_name} -> {model!r}"


def test_no_public_registration_api():
    """D11 + Q14 — nothing external owns a model.

    ``bind`` exists on the registry object, but the registries themselves are
    built and cached inside this module; there is no exported hook for a
    consumer to inject a binding. That is the deliberate replacement for
    ``cuems-nodeconf``'s module-globals injection (FR-026d).
    """
    import cuemsutils.xml.registry as registry_module

    assert not hasattr(registry_module, "register")
    assert not hasattr(registry_module, "register_binding")


def test_registries_are_cached():
    assert get_registry("script") is get_registry("script")
    assert all_registries()["script"] is get_registry("script")
