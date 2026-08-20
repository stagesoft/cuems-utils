"""Document-level read, validate and write (T024, T028) — internal.

Split out of ``XmlReaderWriter`` so the public surface can delegate here.
``XmlReaderWriter`` becomes a one-release deprecation shim over
``CuemsScript.load``/``save`` in US4, and a shim that calls the class that
calls it is a circle. Everything the shim needs lives here instead, and the
import direction stays one-way: ``documents`` never imports
``xml_reader_writer``.

Nothing in this module validates *semantics*. T1 is the schema and lives here;
T2 is ``validators.run_rules`` and is invoked from the public surface, so that
"reading never becomes stricter" (standing rule 8) is a property of the call
sites rather than of a flag threaded through here.
"""

from __future__ import annotations

import os
import tempfile
from os import PathLike
from pathlib import Path
from xml.etree.ElementTree import ElementTree

from xmlschema import XMLSchema11

from ..log import Logger
from .converter import CuemsConverter
from .mapper import build_document

#: The one namespace every CueMS document declares.
NAMESPACE = {"cms": "https://stagelab.coop/cuems/"}

#: Root element per schema. Previously a default argument on ``CuemsXml`` plus
#: a table in the golden harness; one table, named once.
XML_ROOT_TAG = {
    "script": "CuemsProject",
    "settings": "CuemsSettings",
    "network_map": "CuemsNetworkMap",
    "project_mappings": "CuemsProjectMappings",
    "project_settings": "CuemsProjectSettings",
    "outputs": "CuemsOutputs",
}

#: Reader configuration **A** (FR-013): what ``XmlReaderWriter.read`` uses, and
#: what every ``*.reader.json`` golden was captured with. ``strip_namespaces``
#: is ``False`` here and ``True`` in configuration B, and the difference is
#: visible in the payload — it is why the leaked ``schemaLocation`` key carries
#: its full namespace.
DOCUMENT_READER_OPTIONS = {
    "validation": "strict",
    "strip_namespaces": False,
}

#: Built ``XMLSchema11`` objects, keyed on the resolved ``.xsd`` **path**.
#:
#: Keyed on the path rather than on the schema name so that a test relocating
#: the schemas directory gets a fresh object rather than a stale one — which
#: is exactly what the portability test (T078) does.
_SCHEMA_CACHE: dict[str, XMLSchema11] = {}


def get_pkg_schema(schema_name: str) -> str:
    """The absolute path to a bundled ``.xsd``.

    Accepts the bare name or the filename — consumers pass both spellings.
    """
    schemas_dir = os.path.join(os.path.dirname(__file__), "schemas")
    if not schema_name.endswith(".xsd"):
        schema_name = schema_name + ".xsd"
    schema = os.path.join(schemas_dir, schema_name)
    if not os.path.isfile(schema):
        raise FileNotFoundError(f"Schema file {schema_name} not found")
    return schema


def schema_object(schema_name: str) -> XMLSchema11:
    """The compiled schema, built once per process per ``.xsd`` path.

    ``XmlReaderWriter`` compiles one per instance, which is the single largest
    fixed cost on the read path. Caching it is safe because ``XMLSchema11`` is
    read-only once built, and it is what keeps ``load()`` inside SC-PERF-001's
    budget without the projection having to cut corners.
    """
    path = get_pkg_schema(schema_name)
    cached = _SCHEMA_CACHE.get(path)
    if cached is None:
        cached = _SCHEMA_CACHE[path] = XMLSchema11(path, converter=CuemsConverter)
    return cached


def clear_cache() -> None:
    """Drop every compiled schema. For tests that relocate the schemas dir."""
    _SCHEMA_CACHE.clear()


def read_document(schema_name: str, source: str | PathLike) -> dict:
    """Decode a document under reader configuration A.

    ``OSError``/``FileNotFoundError`` propagate unwrapped (FR-035); a
    structurally invalid document raises ``xmlschema``'s validation error,
    which the public surface translates to ``SchemaError``.
    """
    source = os.fspath(source)
    # INFO is declared at the level of XML file access (FR-033): one record per
    # file touched, never one per cue.
    Logger.info(f"Reading {schema_name} document {source}")
    if not os.path.exists(source):
        raise FileNotFoundError(f"No such file: {source}")
    return schema_object(schema_name).to_dict(source, **DOCUMENT_READER_OPTIONS)


def build_tree(obj, schema_name: str) -> ElementTree:
    """Serialize a model object to an element tree — no file, no validation."""
    return build_document(
        obj,
        schema_name=schema_name,
        namespace=NAMESPACE,
        xsd_path=get_pkg_schema(schema_name),
        xml_root_tag=XML_ROOT_TAG[schema_name],
    )


def iter_schema_errors(schema_name: str, tree: ElementTree):
    """Every T1 violation in ``tree``, in document order.

    ``iter_errors`` rather than ``validate`` because ``validate()`` collects
    (FR-004) and ``save()`` stops at the first — one generator serves both, so
    the two cannot report a document differently.
    """
    return schema_object(schema_name).iter_errors(tree)


def write_tree(tree: ElementTree, target: str | PathLike) -> None:
    """Write ``tree`` to ``target`` atomically (FR-003, FR-036a).

    A temporary file in the **same directory** followed by ``os.replace``: same
    filesystem, so the rename is atomic, and a reader either sees the previous
    document or the new one and never a truncated one. On any failure the
    temporary is removed and the target is left exactly as it was — including
    *not existing*, when it did not.

    ``encoding="utf-8"`` and ``xml_declaration=True`` are passed explicitly and
    are not optional. The previous writer passed both; this is the one place an
    atomic rewrite could silently introduce the package's first
    locale-dependent path, and the failure would be invisible on a UTF-8
    developer machine and fatal on a node booted with ``LANG=C`` (C6).
    """
    target = Path(os.fspath(target))
    handle, temporary = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
    )
    os.close(handle)
    try:
        tree.write(temporary, encoding="utf-8", xml_declaration=True)
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:  # pragma: no cover - the replace already consumed it
            pass
        raise
    Logger.info(f"Wrote document {target}")
