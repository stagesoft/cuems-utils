"""Every enumeration's facets agree with T004a's recorded verdict table (T059; FR-029b, SC-012a).

This test asserts **agreement with the audit artifact**
(``specs/008-rebuild-extension/enum-audit.md``) — it does not itself decide
what the system honours, which is a judgment over three consumer
repositories, not a testable predicate. The ``RETAIN`` set below is
transcribed from that document's summary table; if the two drift apart,
either the schema changed without an audit update or the audit's evidence
needs re-checking — both are failures this test exists to surface, not
resolve.
"""

from __future__ import annotations

from cuemsutils.xml.schema import SCHEMA_NAMES, get_schema

#: (schema, named simple type) -> the RETAIN set, transcribed from
#: enum-audit.md's summary table. ``FadeTypeType``/``FadeModeType`` are
#: absent by design — ITEM A already deleted both whole (enum-audit.md's
#: "REMOVE — whole type deleted" rows).
RETAINED = {
    ("script", "ActionType"): {
        "play", "pause", "stop", "load", "unload", "enable", "disable",
        "fade_action", "wait", "go_to", "pause_project", "resume_project",
    },
    ("script", "FadeCurveType"): {"linear", "exponential", "logarithmic", "sigmoid"},
    ("script", "PostGoType"): {"pause", "go", "go_at_end"},
    ("script", "BoolType"): {"True", "False"},
    ("settings", "BoolType"): {"True", "False"},
    ("settings", "AutoOrIntLatencyMsType"): {"auto"},
    ("network_map", "BoolType"): {"True", "False"},
    ("network_map", "NodeRoleType"): {"controller", "node", "firstrun"},
}


def _enumerated_types():
    """``(schema, type_name) -> facet values``, for every named enum type,
    across all six schemas, resolving union member facets (settings'
    ``AutoOrIntLatencyMsType``) the same way the descriptor does."""
    found: dict[tuple[str, str], set[str]] = {}
    for schema_name in SCHEMA_NAMES:
        schema = get_schema(schema_name)
        for type_name, xsd_type in schema.types.items():
            if not xsd_type.is_simple():
                continue
            values = xsd_type.enumeration
            if not values:
                member_types = getattr(xsd_type, "member_types", None) or ()
                merged: set[str] = set()
                for member in member_types:
                    merged.update(getattr(member, "enumeration", None) or ())
                values = merged
            if values:
                found[(schema_name, type_name)] = set(values)
    return found


def test_every_facet_value_in_the_schemas_has_a_recorded_verdict():
    found = _enumerated_types()
    unaudited = sorted(set(found) - set(RETAINED))
    assert unaudited == [], f"enumerations with no recorded verdict: {unaudited}"


def test_the_schemas_carry_no_more_and_no_fewer_than_the_retained_set():
    found = _enumerated_types()
    for key, expected in RETAINED.items():
        assert key in found, f"{key} is recorded as retained but not in any schema"
        assert found[key] == expected, (key, found[key], expected)
