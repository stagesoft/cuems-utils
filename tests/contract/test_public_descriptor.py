"""T006 / SC-003 — the descriptor's public path equals its internal one.

Feature 010, US3 (wave 0). ``SchemaDescriptor`` lives in ``cuemsutils.xml``,
whose ``__all__`` is ``[]``, so consumers have no way to reach it. D34 settles
that it is exposed **through** ``ConfigManager`` — the existing public config
object — covering all six schemas including ``script``.

**Six assertions, not a sample** (SC-003). Parametrising over
``SCHEMA_NAMES`` rather than over a list retyped here is deliberate: a retyped
list would happily omit a schema that had just stopped working, and a seventh
schema added later must appear here without anyone remembering to add it.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.schema import SCHEMA_NAMES




def _public():
    """Imported at call time, not at module import.

    A module-level import of a symbol that does not exist yet is a **collection
    error**, and a collection error interrupts the whole suite — 2573 unrelated
    tests stop running until wave 0 lands. Deferring it keeps these tests
    honestly red (failed, not skipped, not errored) while the rest of the suite
    still runs on a shared branch.
    """
    from cuemsutils.tools.ConfigManager import ConfigManager, SchemaName

    return ConfigManager, SchemaName


@pytest.fixture
def manager():
    ConfigManager, _ = _public()
    return ConfigManager(load_all=False)


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_public_descriptor_equals_internal_for_every_schema(manager, schema_name):
    """The public result *is* the internal result — not a reshaping of it."""
    _, SchemaName = _public()
    member = SchemaName(schema_name)

    public = manager.get_schema_descriptor(member)
    internal = SchemaDescriptor().types(schema_name)

    assert public == internal


def test_the_enum_covers_every_schema_the_registry_knows():
    _, SchemaName = _public()
    """Guards the parametrisation above: if the enum lost a member, every case
    would still pass while covering less."""
    assert {m.value for m in SchemaName} == set(SCHEMA_NAMES)


def test_the_show_schema_is_reachable_from_the_config_object(manager):
    """FR-020/FR-021 — the deliberate widening. ``ConfigManager`` is otherwise
    a configuration-domain object; serving the *show* schema's descriptor from
    it is the whole point of D34, and a reader who finds it must find the
    reason beside it."""
    ConfigManager, SchemaName = _public()
    assert manager.get_schema_descriptor(SchemaName.SCRIPT)
    assert ConfigManager.get_schema_descriptor.__doc__, (
        "FR-021 requires the rationale to live beside the code, not only in the spec"
    )


def test_the_example_generators_are_reachable_from_the_same_path(manager):
    """FR-023 — retiring ``initial_template``-as-an-instance is what the editor
    and the UI *do* with the descriptor, so the generators travel with it."""
    _, SchemaName = _public()
    assert manager.generate_example(SchemaName.SCRIPT) is not None
    assert manager.generate_example(SchemaName.SETTINGS) is not None
