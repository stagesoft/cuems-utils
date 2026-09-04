"""T009 / FR-024 — publishing the descriptor does not widen ``cuemsutils.xml``.

Feature 010, US3. This feature gives the descriptor a public door; it must not
leave the back one open. Q14 ("``xml/`` is internal machinery") is asserted by
006's FR-019/SC-005 and is *strengthened* here, not relaxed: the one legitimate
external consumer gets a front door, and the package still exports nothing.
"""

from __future__ import annotations

import pytest

import cuemsutils.xml as xml_pkg


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


def test_the_xml_package_still_exports_nothing():
    assert xml_pkg.__all__ == []


@pytest.mark.parametrize("name", ["SchemaDescriptor", "get_schema_descriptor", "SchemaName"])
def test_the_descriptor_surface_is_not_reachable_from_the_xml_package(name):
    """A consumer must not be able to reach it the back way — otherwise the
    public path is decorative and the next consumer imports whichever it found
    first."""
    assert not hasattr(xml_pkg, name)


def test_the_public_path_is_the_config_object():
    ConfigManager, SchemaName = _public()
    assert hasattr(ConfigManager, "get_schema_descriptor")
    assert SchemaName is not None


def test_the_accessor_takes_the_enum_and_not_a_bare_string():
    """FR-028a — accepting both would reintroduce the stringly-typed surface
    the enum exists to remove. D12's "public surface returns objects" applies to
    what an API *takes* as much as to what it returns."""
    ConfigManager, _ = _public()
    manager = ConfigManager(load_all=False)
    with pytest.raises((TypeError, ValueError)):
        manager.get_schema_descriptor("script")
