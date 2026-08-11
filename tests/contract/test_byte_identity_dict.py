"""Contract C2 (T014) — the read dict is byte-identical.

The read side of the refactor gate, and the one that matters most to consumers:
this dict is what ``cuems-editor`` transmits verbatim to the Angular UI on
``project_load``.

The comparison is ``json.dumps`` output, not ``==``, and that is a requirement
rather than a convenience (FR-011a). Two dicts with the same keys in a different
insertion order compare equal and serialize differently, so ``==`` would let a
reordering through unnoticed — and a reordering is exactly what a rewritten
mapper is most likely to introduce.
"""

from __future__ import annotations

import json

import pytest

from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT

READABLE = [
    d for d in DOCUMENTS if (GOLDEN_ROOT / "dict" / f"{d.slug}.reader.json").exists()
]
CONFIG_READABLE = [
    d for d in DOCUMENTS if (GOLDEN_ROOT / "dict" / f"{d.slug}.config.json").exists()
]

SCHEMA_LOCATION_KEY = "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"


@pytest.mark.parametrize("doc", READABLE, ids=[d.relpath for d in READABLE])
def test_reader_dict_is_byte_identical(doc):
    """Reader configuration A — ``XmlReaderWriter.read`` (FR-013)."""
    produced = rt.json_dumps(rt.read_dict(doc))
    assert produced == rt.golden_json(f"dict/{doc.slug}.reader.json")


@pytest.mark.parametrize(
    "doc", CONFIG_READABLE, ids=[d.relpath for d in CONFIG_READABLE]
)
def test_config_dict_is_byte_identical(doc):
    """Reader configuration B — the config classes (FR-013).

    ``strip_namespaces=True``, explicit ``dict``/``list``, ``attr_prefix=''``.
    Captured separately from configuration A because the two produce *different*
    output today, and FR-013 requires the differences to survive too.
    """
    produced = rt.json_dumps(rt.read_config_dict(doc))
    assert produced == rt.golden_json(f"dict/{doc.slug}.config.json")


def test_generated_document_dict_is_byte_identical(tmp_path):
    """The generated document, read back after being written.

    Covers every cue type in one dict — audio, video, dmx, action and fade —
    which the three writable vendored documents do not.
    """
    doc = next(d for d in DOCUMENTS if d.schema == "script")
    written = tmp_path / "generated.xml"
    written.write_bytes(rt.write_bytes(doc, rt.build_generated_script()))
    produced = rt.normalize_uuids(rt.json_dumps(rt.read_dict(doc, source=written)).encode())
    assert produced.decode() == rt.golden_json("generated/create_script.reader.json")


@pytest.mark.parametrize("doc", READABLE, ids=[d.relpath for d in READABLE])
def test_read_dict_stays_json_dumps_compatible(doc):
    """FR-011a — the dict must remain serializable at all.

    Inside the guarantee, not adjacent to it: if a value stopped being
    JSON-serializable the editor's ``project_load`` payload would fail to
    transmit, and the byte comparison above would fail with a ``TypeError``
    rather than a diff — obscuring what actually broke.
    """
    json.dumps(rt.read_dict(doc))


@pytest.mark.parametrize("doc", READABLE, ids=[d.relpath for d in READABLE])
def test_key_insertion_order_is_inside_the_guarantee(doc):
    """The property ``==`` cannot see.

    Compares the flattened key sequence explicitly, so a reordering fails here
    with a readable diff instead of as an opaque long-string mismatch.
    """

    def keys(node, out):
        if isinstance(node, dict):
            for k, v in node.items():
                out.append(k)
                keys(v, out)
        elif isinstance(node, list):
            for item in node:
                keys(item, out)
        return out

    produced = keys(rt.read_dict(doc), [])
    golden = keys(json.loads(rt.golden_json(f"dict/{doc.slug}.reader.json")), [])
    assert produced == golden


def test_leaked_schema_location_key_is_still_present():
    """F23 — leaked, and it must stay leaked in this feature.

    ``schemaLocation`` is an artifact of the source document, not content, and
    it should not be in the payload at all. Removing it is a wire change, so it
    is deferred to feature 006 — which means a well-meaning cleanup here would
    be a breaking change disguised as a tidy-up. Pinned so it cannot happen by
    accident.
    """
    carriers = [
        d
        for d in READABLE
        if SCHEMA_LOCATION_KEY in json.loads(rt.golden_json(f"dict/{d.slug}.reader.json"))
    ]
    assert carriers, "no golden carries the leaked schemaLocation key"
    for doc in carriers:
        assert SCHEMA_LOCATION_KEY in rt.read_dict(doc)


@pytest.mark.parametrize("doc", READABLE, ids=[d.relpath for d in READABLE])
def test_repeated_elements_keep_their_decoded_shape(doc):
    """FR-014, F22 — the repeated-element shape *is* the UI contract.

    ``CMLCuemsConverter`` decodes repeated elements as a list of single-key
    dicts (``[{"output": "0"}, {"output": "1"}]``) rather than collapsing them
    to a list of values. The Angular UI reads that shape directly, so
    "simplifying" it would break the frontend without touching a line of
    frontend code.
    """
    golden = json.loads(rt.golden_json(f"dict/{doc.slug}.reader.json"))
    produced = rt.read_dict(doc)
    assert type(produced) is type(golden)

    def shapes(node, path="", out=None):
        out = [] if out is None else out
        if isinstance(node, dict):
            for k, v in node.items():
                shapes(v, f"{path}/{k}", out)
        elif isinstance(node, list):
            out.append((path, len(node), [type(i).__name__ for i in node]))
            for item in node:
                shapes(item, f"{path}[]", out)
        return out

    assert shapes(produced) == shapes(golden)
