"""T010a / FR-028a — the schema-name enum agrees with the registry, both ways.

Feature 010, US3 (wave 0). ``get_schema_descriptor`` takes an enum rather than a
string, so a consumer naming a schema that does not exist fails at the call
instead of returning nothing useful.

**The anti-drift contract is the point of this file**, and it mirrors what
``NodeRole`` already holds against ``NodeRoleType``'s XSD facets: the members are
*asserted against* the library's own schema registry, never hand-copied. Checked
in **both directions** — a registry entry missing from the enum is as much a
defect as an enum member naming a schema that no longer exists — so a seventh
schema cannot come to exist in one place and not the other.

The enum is **declared**, not generated from ``SCHEMA_NAMES`` at import time.
A dynamically built enum has no static members, and five repositories will
import these names: a consumer's editor and type-checker should both know
``SchemaName.SCRIPT`` exists. Declared-plus-asserted buys that without the drift
a hand-copied list would allow.
"""

from __future__ import annotations

from cuemsutils.tools.ConfigManager import SchemaName
from cuemsutils.xml.schema import SCHEMA_NAMES


def test_no_schema_in_the_registry_is_missing_from_the_enum():
    missing = set(SCHEMA_NAMES) - {member.value for member in SchemaName}
    assert not missing, f"schemas the registry knows and the enum does not: {sorted(missing)}"


def test_no_enum_member_names_a_schema_the_registry_does_not_have():
    extra = {member.value for member in SchemaName} - set(SCHEMA_NAMES)
    assert not extra, f"enum members naming no registered schema: {sorted(extra)}"


def test_the_two_agree_exactly():
    """Stated positively as well, because the two assertions above can both pass
    on an empty enum if ``SCHEMA_NAMES`` ever emptied."""
    assert {member.value for member in SchemaName} == set(SCHEMA_NAMES)
    assert len(list(SchemaName)) == 6


def test_a_member_is_reachable_by_value():
    """How ``get_schema_descriptor``'s callers and the library's own internals
    cross between the string form the registry uses and the enum the public
    surface takes."""
    for name in SCHEMA_NAMES:
        assert SchemaName(name).value == name


def test_the_enum_does_not_read_as_the_loaded_schema_object():
    """FR-028a — ``get_schema`` returns a loaded ``XMLSchema``. An enum called
    ``Schema`` would be misread as that object at every call site, so the name
    must keep the two distinguishable."""
    assert SchemaName.__name__ != "Schema"
