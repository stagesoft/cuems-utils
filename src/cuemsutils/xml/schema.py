"""Schema loading and caching (T037).

The six bundled XSDs, each loaded **once per process** as its own
``XMLSchema11`` object.

Per-schema isolation is the established structure (research R4), and until
rc16 it was also mandatory: ``script.xsd`` and what is now
``hardware_outputs.xsd`` both declared ``{https://stagelab.coop/cuems/}OutputsType``
in the same namespace with **different content** — ``AudioCueOutput,
VideoCueOutput, DmxCueOutput`` in one, ``output`` in the other. The two could
not coexist in a single namespace-aware schema object, which is the structural
half of why that schema was never loaded alongside the others (X11/X14).

**rc16 resolved the collision** by renaming the second to
``HardwareOutputsType``; the two names are now distinct and
``tests/unit/test_spec_derivation.py`` pins that they stay so. Isolation is
kept regardless: nothing has established that a shared schema object would be
correct now, and every registry, binding and cached derivation is built per
schema on top of it. Whether it *could* be relaxed is untested and out of
scope.

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
    "hardware_outputs",
)

#: Root element per schema. Needed because the registry binds anonymous root
#: types by element path rather than by type name (research R3).
SCHEMA_ROOTS = {
    "script": "CuemsProject",
    "settings": "CuemsSettings",
    "network_map": "CuemsNetworkMap",
    "project_mappings": "CuemsProjectMappings",
    "project_settings": "CuemsProjectSettings",
    "hardware_outputs": "CuemsHardwareOutputs",
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
