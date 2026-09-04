"""T008 / research R8 — asking for one schema builds one schema.

Feature 010, US3. Constitution IV states the budget for wave 0 as "no
measurable cost", quantified by FR-PERF-001 as within 110% of the internal
path's per-schema cost. The failure mode is specific rather than general: the
internal path builds **one** schema's descriptor on demand, and a public
accessor that eagerly built all six would put five unnecessary schema
constructions on the path of any consumer wanting one.

Feature 005 already measured what that costs — ``coercion._resolve`` calling
``all_registries()`` is the entire 36.3 → 49.6 ms cold delta it recorded.

**This test must not be defeated by its neighbours.** ``get_schema`` is
``lru_cache``d process-wide, so a test that ran earlier can hide an eager build
behind a warm cache. Every case clears the cache first and reads
``cache_info().currsize`` afterwards — the number of *distinct* schemas built.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.registry import get_registry
from cuemsutils.xml.schema import SCHEMA_NAMES, get_schema


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


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_one_schema_asked_for_is_one_schema_built(schema_name):
    ConfigManager, SchemaName = _public()
    member = SchemaName(schema_name)
    get_schema.cache_clear()
    get_registry.cache_clear()

    ConfigManager(load_all=False).get_schema_descriptor(member)

    assert get_schema.cache_info().currsize == 1, (
        f"asking for {member.value} built {get_schema.cache_info().currsize} schemas; "
        "eager construction here is a design error, not a budget overrun to accept"
    )


def test_asking_for_two_builds_two_not_six():
    """Laziness is per schema, not a one-shot warm-up."""
    ConfigManager, SchemaName = _public()
    get_schema.cache_clear()
    get_registry.cache_clear()

    manager = ConfigManager(load_all=False)
    manager.get_schema_descriptor(SchemaName.SCRIPT)
    manager.get_schema_descriptor(SchemaName.SETTINGS)

    assert get_schema.cache_info().currsize == 2
