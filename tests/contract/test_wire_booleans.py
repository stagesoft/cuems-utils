"""Feature 014 — booleans on the wire are **real JSON booleans** (X1).

**This file's premise was retired deliberately.** It used to assert the
opposite, and its own docstring said why:

    ``cms:BoolType`` is an ``xs:string`` restricted to those two literals, not
    an ``xs:boolean``. So the payload carries the capitalised Python spelling
    as text […] Decoding them to JSON booleans is the single most natural
    "improvement" available in this code and would break every consumer of the
    payload at once. It is deferred item X1 and a file-format migration; it is
    explicitly forbidden here.

Every sentence of that was true when written. **Feature 014 is X1**: the type
is retyped, the migration is done, and the consumers moved with it as one
coordinated step — which is exactly the condition the deferral named, not an
exception to it.

So the file is kept and inverted rather than deleted. Deleting it would lose
the only place that states the wire's boolean form *is* a contract and not an
accident; a reader meeting ``"enabled": true`` later should find an assertion
saying it must be a ``bool``, with the history of why it once had to be a
string.

**What survives unchanged**, and it is the more important half:
:func:`test_the_object_still_holds_real_python_booleans`. The object model held
real ``bool``s before X1 and holds them after — the wire was the only thing
that differed — so that assertion never moved. It is the reason
``if cue.enabled:`` in ``cuems-engine`` was always safe.

Both halves of every assertion are kept (``is True`` **and**
``not isinstance(..., str)``) because ``"False"`` is truthy: a test checking
only truthiness would pass on either encoding, which is how a half-applied
change hides.
"""

from __future__ import annotations

import json
import sys

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from tests.support.corpus import loadable_script_documents
from tests.support.public_api import assert_no_xml_import

#: The documents that reach the object layer — ``script_documents()`` minus
#: the two ``legacy/`` entries pinned as ``to_objects: error``, which must
#: stay rejected (FR-025) and so cannot be loaded to be projected.
SCRIPT_DOCS = loadable_script_documents()
IDS = [d.relpath for d in SCRIPT_DOCS]

#: Every ``cms:BoolType`` element in ``script.xsd``.
BOOLEAN_FIELDS = ("autoload", "enabled", "timecode")


def _boolean_values(node, path="$", out=None):
    out = [] if out is None else out
    if isinstance(node, dict):
        for key, value in node.items():
            if key in BOOLEAN_FIELDS:
                out.append((f"{path}.{key}", value))
            _boolean_values(value, f"{path}.{key}", out)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _boolean_values(item, f"{path}[{index}]", out)
    return out


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_every_boolean_field_is_the_string_form(doc):
    found = _boolean_values(CuemsScript.load(doc.path).to_wire())
    assert found, f"{doc.relpath} carries no boolean fields to check"
    for path, value in found:
        assert isinstance(value, bool), (
            f"{path} is {type(value).__name__}, not a bool — X1 retyped "
            f"cms:BoolType to xs:boolean, so the wire carries JSON booleans"
        )
        assert not isinstance(value, str), f"{path} is still a string: {value!r}"


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_the_json_text_carries_no_quoted_booleans_for_those_fields(doc):
    """The same claim at the bytes, where a consumer actually meets it.

    Inverted with the rest: the old spelling is what must now be absent. This
    is the assertion ``cuems-frontend``'s ``sequence.component.ts:997`` is
    coupled to — it writes ``'True'``, which the library now refuses.
    """
    text = CuemsScript.load(doc.path).to_json()
    for field in BOOLEAN_FIELDS:
        assert f'"{field}": "True"' not in text, field
        assert f'"{field}": "False"' not in text, field


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_the_object_still_holds_real_python_booleans(doc):
    """The wire form is a *projection*, not the model's own type.

    ``_Bool.decode`` turns ``"True"`` into ``True`` so the engine can branch on
    it. If the object started holding strings, every ``if cue.enabled:`` in
    ``cuems-engine`` would become unconditionally true.
    """
    script = CuemsScript.load(doc.path)
    assert isinstance(script.cuelist.enabled, bool)


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_a_boolean_survives_the_json_round_trip_as_a_boolean(doc):
    script = CuemsScript.load(doc.path)
    rebuilt = CuemsScript.from_json(json.dumps(script.to_wire()))
    assert isinstance(rebuilt.cuelist.enabled, bool)
    assert rebuilt.cuelist.enabled == script.cuelist.enabled


def test_the_module_under_test_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])
