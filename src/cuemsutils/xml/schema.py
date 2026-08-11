"""Schema loading and caching (T037).

The six bundled XSDs, each loaded **once per process** as its own
``XMLSchema11`` object.

Per-schema isolation is mandatory, not stylistic (research R4). ``script.xsd``
and ``outputs.xsd`` both declare ``{https://stagelab.coop/cuems/}OutputsType``
in the same namespace with **different content** — ``AudioCueOutput,
VideoCueOutput, DmxCueOutput`` in one, ``output`` in the other. The two cannot
coexist in a single namespace-aware schema object, which is why ``outputs.xsd``
has never been loaded alongside the others (X11). Keeping them separate routes
around the collision without editing a ``.xsd``, which D3 forbids.

XSD 1.1 is required throughout: ``script.xsd`` uses ``xs:assert`` (X7).
"""

from __future__ import annotations

from functools import lru_cache
from os import path

from xmlschema import XMLSchema11

#: The six bundled schemas. Order is stable so error messages and test
#: parametrisation read the same way every run.
SCHEMA_NAMES = (
    "script",
    "settings",
    "network_map",
    "project_mappings",
    "project_settings",
    "outputs",
)

#: Root element per schema. Needed because the registry binds anonymous root
#: types by element path rather than by type name (research R3).
SCHEMA_ROOTS = {
    "script": "CuemsProject",
    "settings": "CuemsSettings",
    "network_map": "CuemsNetworkMap",
    "project_mappings": "CuemsProjectMappings",
    "project_settings": "CuemsProjectSettings",
    "outputs": "CuemsOutputs",
}

SCHEMAS_DIR = path.join(path.dirname(__file__), "schemas")


def schema_path(schema_name: str) -> str:
    """Absolute path to a bundled ``.xsd``.

    Accepts a bare name or one already carrying the extension, matching
    ``xml_reader_writer.get_pkg_schema`` — consumers pass both spellings today.
    """
    if not schema_name.endswith(".xsd"):
        schema_name = schema_name + ".xsd"
    resolved = path.join(SCHEMAS_DIR, schema_name)
    if not path.isfile(resolved):
        raise FileNotFoundError(f"Schema file {schema_name} not found")
    return resolved


@lru_cache(maxsize=None)
def get_schema(schema_name: str, converter: type | None = None) -> XMLSchema11:
    """Load a bundled schema, cached per ``(name, converter)``.

    Cached because parsing an XSD is expensive and the result is immutable in
    use. The converter is part of the key: ``XMLSchema11`` stores it, and the
    two reader configurations (FR-013) need different ones, so a single-key
    cache would silently hand one configuration the other's converter.

    The cache is also what makes SC-PERF-002's "schema load once per process"
    an implementation fact rather than an aspiration.
    """
    return XMLSchema11(schema_path(schema_name), converter=converter)


def root_element(schema_name: str):
    """The schema's single global element."""
    return get_schema(schema_name).elements[SCHEMA_ROOTS[schema_name]]


def clear_cache() -> None:
    """Drop every cached schema. For tests that measure load counts."""
    get_schema.cache_clear()
