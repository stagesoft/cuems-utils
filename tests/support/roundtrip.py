"""The read/write operations under contract, in one place.

Every byte-identity test drives the library through these three functions, so
there is exactly one definition of "what the library does with a document" for
the goldens to have been captured from. When the engine is swapped in at T047,
nothing here changes — that is the point.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tests.support.capture_goldens import (
    GENERATED_CREATED,
    GENERATED_MODIFIED,
    XML_ROOT_TAG,
    build_generated_script,
    normalize_schema_location,
    normalize_uuids,
)
from tests.support.corpus import GOLDEN_ROOT, CorpusDoc

__all__ = [
    "GENERATED_CREATED",
    "GENERATED_MODIFIED",
    "build_generated_script",
    "golden_bytes",
    "golden_json",
    "json_dumps",
    "normalize_uuids",
    "read_config_dict",
    "read_dict",
    "read_objects",
    "write_bytes",
]


def _reader(schema: str, xmlfile: str):
    from cuemsutils.xml.XmlReaderWriter import XmlReaderWriter

    return XmlReaderWriter(
        schema_name=schema, xmlfile=xmlfile, xml_root_tag=XML_ROOT_TAG[schema]
    )


def read_dict(doc: CorpusDoc, source: str | Path | None = None):
    """Reader configuration A: ``strip_namespaces=False`` (FR-013)."""
    return _reader(doc.schema, str(source or doc.path)).read()


def read_config_dict(doc: CorpusDoc, source: str | Path | None = None):
    """Reader configuration B: the config classes (FR-013).

    ``strip_namespaces=True``, explicit ``dict``/``list``, ``attr_prefix=''``.
    Resolved off the package rather than ``cuemsutils.xml.Settings``, whose name
    is shadowed by the class of the same name.
    """
    import cuemsutils.xml as xml_package

    assert doc.config_class is not None
    cls = getattr(xml_package, doc.config_class)
    return cls(str(source or doc.path)).xml_dict


def read_objects(doc: CorpusDoc, source: str | Path | None = None):
    return _reader(doc.schema, str(source or doc.path)).read_to_objects()


def write_bytes(doc: CorpusDoc, obj) -> bytes:
    """Serialize ``obj`` and return the file's bytes, schema path normalized.

    Writes to a scratch file because ``XmlReaderWriter.write`` takes its
    destination from the instance, not from an argument — the bytes on disk are
    the artifact C1 compares.
    """
    out = Path(tempfile.mkdtemp()) / "written.xml"
    _reader(doc.schema, str(out)).write_from_object(obj)
    return normalize_schema_location(out.read_bytes())


def json_dumps(value) -> str:
    """The comparison C2 specifies — order-sensitive, and deliberately so."""
    return json.dumps(value)


def golden_bytes(relpath: str) -> bytes:
    return (GOLDEN_ROOT / relpath).read_bytes()


def golden_json(relpath: str) -> str:
    return (GOLDEN_ROOT / relpath).read_text(encoding="utf-8")


# Re-exported, not reimplemented: the tests must build the generated document
# through the exact code path the goldens were captured from.
