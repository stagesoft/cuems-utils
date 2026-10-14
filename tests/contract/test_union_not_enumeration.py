"""Contract C6 (S2, T051) — SC-010: all five measured sites stop reporting a
one-value closed choice set.

Three node-identity ``uuid`` fields across three schemas (``NodeUuidType``),
and **two numeric latency fields** (``AutoOrIntLatencyMsType``) — the case
the source planning document did not record, and the worse of the two:
``0``-``500`` are valid and a descriptor-driven form offering only ``'auto'``
would silently refuse them.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.descriptor import SchemaDescriptor

SITES = (
    ("network_map", "NodeType", "uuid"),
    ("settings", "NodeConfType", "uuid"),
    ("project_mappings", "NodeMappingType", "uuid"),
    ("settings", "AudioPlayerType", "output_latency_ms"),
    ("settings", "VideoPlayerType", "output_latency_ms"),
)


@pytest.mark.parametrize("schema_name,type_name,field_name", SITES)
def test_the_site_no_longer_reports_a_one_value_choice_set(schema_name, type_name, field_name):
    descriptor = SchemaDescriptor()
    type_descriptor = next(
        td for td in descriptor.types(schema_name) if td.key.name == type_name
    )
    field = next(f for f in type_descriptor.fields if f.name == field_name)

    assert field.enum_values is None, (
        f"{schema_name}.{type_name}.{field_name} still reports a closed "
        f"choice set: {field.enum_values}"
    )


def test_all_five_sites_are_covered():
    """The control: SC-010's claim is 5 -> 0. Fewer sites parametrized above
    would make the claim weaker than it is."""
    assert len(SITES) == 5
