"""SC-003 (T030) — the two UI payloads are one projection.

The editor receives the same document type on two paths, and until this
feature they disagreed (F21):

============================  =====================  ====================
field                         ``initial_template``   ``project_load``
============================  =====================  ====================
``enabled``/``autoload``      ``true`` (bool)        ``"True"`` (str)
``ui_properties.warning``     ``0`` (int)            ``"0"`` (str)
``schemaLocation``            absent                 **present**
============================  =====================  ====================

``initial_template`` is what ``json.dumps(script)`` produces — the
``__json__`` hook. ``project_load`` is the reader dict. This test renders one
script both ways and diffs **the full dict**, field by field, under contracts
§W1a: recursive structure, exact scalar type, key order. Not a chosen subset,
so "zero differing fields" cannot be true by selection.

**It fails before T035/T036 and passes after** — on every boolean and on every
``ui_properties`` integer. That is the fail-then-pass evidence for enumerated
behaviour change 1.

No frontend change is required: the Angular UI's
``=== true || === 'True'`` dual-check already absorbs the boolean case.
Removing that dual-check is the frontend team's to schedule, and is why they
are told (``frontend-note.md``).
"""

from __future__ import annotations

import json
import sys

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from tests.support import roundtrip as rt
from tests.support.corpus import loadable_script_documents
from tests.support.public_api import assert_no_xml_import

#: The documents that reach the object layer — ``script_documents()`` minus
#: the two ``legacy/`` entries pinned as ``to_objects: error``, which must
#: stay rejected (FR-025) and so cannot be loaded to be projected.
SCRIPT_DOCS = loadable_script_documents()
IDS = [d.relpath for d in SCRIPT_DOCS]


def _template_payload(script) -> dict:
    """What ``cuems-editor``'s ``initial_template`` call site produces.

    ``json.dumps`` rather than ``to_json``, deliberately: the consumer reaches
    the projection through the ``__json__`` hook, and testing ``to_json``
    instead would assert the two *new* paths agree while leaving the one that
    actually crosses the repository boundary unmeasured.
    """
    return {"CuemsScript": json.loads(json.dumps(script))}


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_the_two_payloads_agree_field_for_field(doc):
    script = CuemsScript.load(doc.path)

    template = _template_payload(script)
    project_load = script.to_wire()

    diffs = rt.wire_diff(template, project_load)
    assert not diffs, (
        f"{doc.relpath}: initial_template and project_load disagree (W1a):\n  "
        + "\n  ".join(diffs)
    )


def test_the_diff_actually_compares_the_whole_document():
    """Without this, "zero differences" could be true of an empty comparison."""
    script = CuemsScript.load(SCRIPT_DOCS[0].path)
    payload = _template_payload(script)

    def _leaves(node):
        if isinstance(node, dict):
            return sum(_leaves(v) for v in node.values())
        if isinstance(node, list):
            return sum(_leaves(v) for v in node)
        return 1

    assert _leaves(payload) > 50, "the parity comparison covers almost nothing"


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_the_template_payload_carries_the_project_load_forms(doc):
    """The change stated positively, not only as "they are equal now".

    Two equal payloads could in principle both have moved to the *wrong* form.
    This names which form they agreed on: the schema's.
    """
    script = CuemsScript.load(doc.path)
    template = _template_payload(script)["CuemsScript"]

    booleans = _collect(template, ("autoload", "enabled", "timecode"))
    assert booleans, f"{doc.relpath} carries no boolean fields to check"
    for path, value in booleans:
        assert value in ("True", "False"), f"{path} == {value!r}"
        assert not isinstance(value, bool), f"{path} is a JSON boolean"


def _collect(node, keys, path="$", out=None):
    out = [] if out is None else out
    if isinstance(node, dict):
        for key, value in node.items():
            if key in keys:
                out.append((f"{path}.{key}", value))
            _collect(value, keys, f"{path}.{key}", out)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _collect(item, keys, f"{path}[{index}]", out)
    return out


def test_the_module_under_test_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])
