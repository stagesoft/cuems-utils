"""FR-011 (T031) — no ``schemaLocation`` key anywhere in the wire dict.

**A guard, not a fail-then-pass test**, and the distinction is worth stating
because the task list carried the opposite claim until 2026-08-18.
``encode_wire`` has never emitted this key: the gating test (T005) compares
against the ``read()`` golden *minus* it, so a projection that emitted it would
be failing its own gate. There is no state in which the projection is correct
and the key is present, and therefore nothing here can ever have failed first.

It is worth having anyway, because the change **is** real from a consumer's
point of view — ``project_load`` carries the key today — and because the key
arrives from the XML layer by leakage rather than by decision: it is an
``xsi:`` attribute on the root element that the converter maps like any other
attribute. A future change to attribute handling could reintroduce it without
touching a line of this projection.
"""

from __future__ import annotations

import json
import sys

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from tests.support.corpus import GOLDEN_ROOT, loadable_script_documents
from tests.support.public_api import assert_no_xml_import

#: The documents that reach the object layer — ``script_documents()`` minus
#: the two ``legacy/`` entries pinned as ``to_objects: error``, which must
#: stay rejected (FR-025) and so cannot be loaded to be projected.
SCRIPT_DOCS = loadable_script_documents()
IDS = [d.relpath for d in SCRIPT_DOCS]

#: Both spellings: the namespaced key reader configuration A produces, and the
#: bare one configuration B would.
SCHEMA_LOCATION_KEYS = (
    "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation",
    "schemaLocation",
)


def _keys_at_every_depth(node, path="$", out=None):
    out = [] if out is None else out
    if isinstance(node, dict):
        for key, value in node.items():
            out.append((f"{path}.{key}", key))
            _keys_at_every_depth(value, f"{path}.{key}", out)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _keys_at_every_depth(item, f"{path}[{index}]", out)
    return out


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_no_schema_location_key_at_any_depth(doc):
    wire = CuemsScript.load(doc.path).to_wire()
    offending = [
        path for path, key in _keys_at_every_depth(wire) if key in SCHEMA_LOCATION_KEYS
    ]
    assert not offending, f"{doc.relpath}: {offending}"


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_the_json_form_carries_it_either(doc):
    text = CuemsScript.load(doc.path).to_json()
    assert "schemaLocation" not in text


def test_the_source_document_does_carry_the_key():
    """The control: without it, the assertions above prove nothing.

    Every corpus document's ``read()`` golden carries the key. If it stopped
    doing so, the guard above would pass on a payload that never had anything
    to drop.
    """
    doc = SCRIPT_DOCS[0]
    golden = json.loads(
        (GOLDEN_ROOT / "dict" / f"{doc.slug}.reader.json").read_text(encoding="utf-8")
    )
    keys = {key for _, key in _keys_at_every_depth(golden)}
    assert keys & set(SCHEMA_LOCATION_KEYS), (
        f"{doc.relpath}'s reader golden no longer carries schemaLocation, so "
        f"this guard is measuring nothing"
    )


def test_the_module_under_test_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])
