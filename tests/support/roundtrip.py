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
    "as_plain",
    "GENERATED_MODIFIED",
    "build_generated_script",
    "golden_bytes",
    "golden_json",
    "json_dumps",
    "normalize_uuids",
    "read_config_dict",
    "read_dict",
    "read_objects",
    "wire_diff",
    "wire_equal",
    "write_bytes",
    "write_bytes_raw",
]


def _reader(schema: str, xmlfile: str):
    from cuemsutils.xml.xml_reader_writer import XmlReaderWriter

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

    ``normalize_schema_location`` is retained and is now a **no-op**: T037
    writes the bare schema filename, so there is no machine path left to
    replace. Keeping the call rather than deleting it is deliberate — it is the
    thing that would start substituting again if the absolute path ever came
    back, and ``write_bytes_raw`` below is the assertion that it has not.
    """
    return normalize_schema_location(write_bytes_raw(doc, obj))


def write_bytes_raw(doc: CorpusDoc, obj) -> bytes:
    """``write_bytes`` with **no** normalization at all (T037).

    Exists because "the normalization is a no-op now" is a claim that a
    normalizing comparison cannot make.
    """
    out = Path(tempfile.mkdtemp()) / "written.xml"
    _reader(doc.schema, str(out)).write_from_object(obj)
    return out.read_bytes()


def as_plain(value):
    """``value`` with every model object replaced by a plain ``dict``.

    Insertion order is preserved, because that is what the dict goldens record
    and what C2 compares.

    Needed from feature 006 onward: ``CuemsDict`` gained a ``__json__`` hook, so
    ``json.dumps`` on a decoded document now runs the **projection** rather than
    serializing the mapping. That is correct for a payload and wrong for a
    structural comparison — the projection filters undeclared keys (the leaked
    ``schemaLocation``) and orders by declaration, neither of which the golden
    is a record of. Stripping the classes first asks the question C2 has always
    asked: *is the decoded structure the same?*
    """
    if isinstance(value, dict):
        return {k: as_plain(v) for k, v in dict.items(value)}
    if isinstance(value, list):
        return [as_plain(v) for v in value]
    return value


def json_dumps(value) -> str:
    """The comparison C2 specifies — order-sensitive, and deliberately so."""
    return json.dumps(as_plain(value))


def golden_bytes(relpath: str) -> bytes:
    return (GOLDEN_ROOT / relpath).read_bytes()


def golden_json(relpath: str) -> str:
    return (GOLDEN_ROOT / relpath).read_text(encoding="utf-8")


def wire_diff(produced, golden, path: str = "$") -> list[str]:
    """Structural differences between two wire payloads, per contracts §W1a.

    Empty when they are equal under W1a: same recursive structure and list
    order/length, matching dict key **order**, and exact scalar **type** —
    checked with ``type(a) is type(b)``, not ``==``, because ``True == 1`` in
    Python. Text is compared as plain ``str``, which is already
    codepoint-equality once both sides are decoded from JSON. Every
    byte-equality test in this feature (T005, T030, T043a) uses this one
    predicate.
    """
    if isinstance(golden, dict) or isinstance(produced, dict):
        if not (isinstance(golden, dict) and isinstance(produced, dict)):
            return [f"{path}: type {type(produced).__name__} != {type(golden).__name__}"]
        pk, gk = list(produced.keys()), list(golden.keys())
        if pk != gk:
            return [f"{path}: key order {pk!r} != {gk!r}"]
        diffs = []
        for k in gk:
            diffs.extend(wire_diff(produced[k], golden[k], f"{path}.{k}"))
        return diffs

    if isinstance(golden, list) or isinstance(produced, list):
        if not (isinstance(golden, list) and isinstance(produced, list)):
            return [f"{path}: type {type(produced).__name__} != {type(golden).__name__}"]
        if len(produced) != len(golden):
            return [f"{path}: length {len(produced)} != {len(golden)}"]
        diffs = []
        for i, (p, g) in enumerate(zip(produced, golden)):
            diffs.extend(wire_diff(p, g, f"{path}[{i}]"))
        return diffs

    if type(produced) is not type(golden):
        return [
            f"{path}: type {type(produced).__name__} != {type(golden).__name__} "
            f"({produced!r} vs {golden!r})"
        ]
    if produced != golden:
        return [f"{path}: {produced!r} != {golden!r}"]
    return []


def wire_equal(produced, golden) -> bool:
    """``True`` iff ``wire_diff`` finds nothing — see its docstring for W1a."""
    return not wire_diff(produced, golden)


# Re-exported, not reimplemented: the tests must build the generated document
# through the exact code path the goldens were captured from.
