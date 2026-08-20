"""FR-027, SC-012 (T033) — runtime state cannot reach the wire.

Cues carry state that is not part of the document: playback handles, timecode
marks, arm flags, thread objects. None of it may appear in the UI payload, in
``to_json()`` output, or in a written document — a ``_go_thread`` in a saved
show file is meaningless at best and unserializable at worst.

The guarantee is **by construction**: the projection walks declared fields, and
``RUNTIME_FIELDS`` names are not among them. So this is not a filter under
test — it is the *absence* of a leak, asserted against the declaration itself
rather than against a list of names retyped here. Add a runtime attribute
without declaring it and the last test fails; declare it and every assertion
above automatically covers it.
"""

from __future__ import annotations

import sys

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.helpers import CuemsDict
from tests.support import invalid_scripts as broken
from tests.support.corpus import loadable_script_documents
from tests.support.public_api import assert_no_xml_import

#: The documents that reach the object layer — ``script_documents()`` minus
#: the two ``legacy/`` entries pinned as ``to_objects: error``, which must
#: stay rejected (FR-025) and so cannot be loaded to be projected.
SCRIPT_DOCS = loadable_script_documents()
IDS = [d.relpath for d in SCRIPT_DOCS]


def _all_subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from _all_subclasses(sub)


def declared_runtime_names() -> set[str]:
    """Every name any model class declares as runtime state.

    Read from the classes, not from a literal list: a list would have to be
    edited whenever a class is, which is the maintenance-by-hand this whole
    feature removes.
    """
    import cuemsutils.cues  # noqa: F401 - import for the side effect of loading

    names: set[str] = set()
    for cls in _all_subclasses(CuemsDict):
        names.update(cls.runtime_fields())
    names.add("_initialized")
    return names


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


def test_the_declaration_is_not_empty():
    """The control. An empty name set makes every assertion below vacuous."""
    names = declared_runtime_names()
    assert len(names) >= 10, sorted(names)
    assert "_go_thread" in names
    assert "_start_mtc" in names


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_no_runtime_name_appears_in_the_wire_payload(doc):
    names = declared_runtime_names()
    wire = CuemsScript.load(doc.path).to_wire()
    offending = [path for path, key in _keys_at_every_depth(wire) if key in names]
    assert not offending, f"{doc.relpath}: {offending}"


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_no_runtime_name_appears_in_the_json_text(doc):
    text = CuemsScript.load(doc.path).to_json()
    offending = [name for name in declared_runtime_names() if f'"{name}"' in text]
    assert not offending, f"{doc.relpath}: {offending}"


def test_no_runtime_name_appears_in_a_written_document(tmp_path):
    """Populate the runtime state first, so absence is not absence of a value."""
    script = broken.valid_script()
    for cue in script.cuelist.contents:
        cue._go_thread = "a thread"
        cue._armed_list = ["armed"]
        cue._end_reached = True

    target = tmp_path / "show.xml"
    script.save(target)

    text = target.read_text(encoding="utf-8")
    offending = [name for name in declared_runtime_names() if name in text]
    assert not offending, offending


def test_a_runtime_attribute_that_escapes_the_declaration_is_caught():
    """SC-012's enforcement clause.

    An attribute set in ``__init__`` and *not* declared is exactly the mistake
    converting imperative bodies to data invites, and it is invisible until a
    cue reaches playback without it. Every underscore-prefixed instance
    attribute on a freshly constructed cue must be accounted for by a
    declaration.
    """
    from cuemsutils.cues.AudioCue import AudioCue
    from cuemsutils.cues.DmxCue import DmxCue
    from cuemsutils.cues.VideoCue import VideoCue

    declared = declared_runtime_names()
    for cls in (AudioCue, VideoCue, DmxCue):
        instance = cls()
        undeclared = {
            name
            for name in vars(instance)
            if name.startswith("_") and name not in declared
        }
        assert not undeclared, f"{cls.__name__} sets undeclared runtime state: {undeclared}"


def test_the_module_under_test_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])
