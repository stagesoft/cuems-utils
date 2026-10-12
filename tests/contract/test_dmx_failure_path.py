"""DMX scene failure raises — contract C11, FR-019 row 7, FR-023.

**Inverted by feature 005** (T040). This file used to assert the opposite.

``DmxSceneXmlBuilder.build`` wrapped its whole body in ``except Exception`` and
logged instead of raising, so a DMX scene that failed to serialize produced **no
elements and no exception** — the surrounding document saved as if the scene
were empty. A show file written that way is missing a scene and says so nowhere.

Feature 004 could not fix it: making a saving document fail is a behaviour
change, and 004 preserved behaviour. So it reproduced the swallow behind a named
``DmxSceneCompatibility`` object carrying ``REMOVAL_TARGET = "005"``, and this
file pinned it. Feature 005 is that removal target.

What changed, precisely:

* the compatibility object is **deleted** — it had no call sites in the engine,
  because the engine already let the exception propagate;
* what the engine did *not* do was say which scene failed. A bare
  ``RuntimeError`` from somewhere inside a 24 KB document is not actionable, so
  the error now identifies the scene by ``id`` (or by zero-based index when it
  has none) and names the originating cue;
* the guard is scoped to DMX scenes. An ambient ``except Exception`` would
  swallow unrelated failures — the same defect, widened.

The **legacy** ``XmlBuilder`` keeps its own swallow. It is the frozen legacy
tree, unreachable from the engine and removed with the deprecation shims in
feature 006; changing it here would be editing code this feature does not own.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.mapper import DmxSceneWriteError
from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS

SCRIPT_DOC = next(d for d in DOCUMENTS if d.schema == "script")


class _ExplodingScene:
    """A DMX scene whose serialization fails.

    Raising from ``keys()`` is the earliest point the writer touches the object,
    so the failure lands with nothing yet emitted — the worst case, and the one
    worth pinning.
    """

    def __init__(self, scene_id=None):
        self._id = scene_id

    def get(self, key, default=None):
        return self._id if key == "id" else default

    def keys(self):
        raise RuntimeError("scene serialization failed")

    def items(self):
        raise RuntimeError("scene serialization failed")


def script_with_scene(scene):
    obj = rt.build_generated_script()
    cue = next(c for c in obj["CueList"]["contents"] if "DmxScene" in c)
    dict.__setitem__(cue, "DmxScene", scene)
    return obj, cue


# --- the change: it raises -------------------------------------------------


def test_a_failing_scene_aborts_the_write():
    """**Inverted.** The write used to succeed with the scene missing."""
    obj, _ = script_with_scene(_ExplodingScene())
    with pytest.raises(DmxSceneWriteError):
        rt.write_bytes(SCRIPT_DOC, obj)


def test_the_error_identifies_the_scene_by_id():
    """FR-023 — by ``id`` when it has one."""
    obj, _ = script_with_scene(_ExplodingScene(scene_id=7))
    with pytest.raises(DmxSceneWriteError) as excinfo:
        rt.write_bytes(SCRIPT_DOC, obj)
    assert "id=7" in str(excinfo.value)


def test_the_error_falls_back_to_the_index_when_there_is_no_id():
    """FR-023 — zero-based index in the cue's scene contents."""
    obj, _ = script_with_scene(_ExplodingScene(scene_id=None))
    with pytest.raises(DmxSceneWriteError) as excinfo:
        rt.write_bytes(SCRIPT_DOC, obj)
    assert "index 0" in str(excinfo.value)


def test_the_error_names_the_originating_cue():
    """Which scene *and* which cue — one without the other is half an answer."""
    obj, cue = script_with_scene(_ExplodingScene())
    with pytest.raises(DmxSceneWriteError) as excinfo:
        rt.write_bytes(SCRIPT_DOC, obj)

    message = str(excinfo.value)
    assert type(cue).__name__ in message
    assert str(cue["id"]) in message


def test_the_original_failure_is_preserved_as_the_cause():
    """The actionable error must not replace the diagnosis."""
    obj, _ = script_with_scene(_ExplodingScene())
    with pytest.raises(DmxSceneWriteError) as excinfo:
        rt.write_bytes(SCRIPT_DOC, obj)
    assert isinstance(excinfo.value.__cause__, RuntimeError)
    assert "scene serialization failed" in str(excinfo.value.__cause__)


def test_the_error_carries_no_object_repr():
    """FR-033 — identifiers only. Show content stays out of error strings."""
    obj, _ = script_with_scene(_ExplodingScene(scene_id=7))
    with pytest.raises(DmxSceneWriteError) as excinfo:
        rt.write_bytes(SCRIPT_DOC, obj)
    assert "_ExplodingScene object at" not in str(excinfo.value)


# --- the control case ------------------------------------------------------


def test_a_healthy_scene_still_emits():
    """Without this, swallowing *everything* would pass every test above.

    FR-020: no valid document changes. The generated script contains a real DMX
    scene, and it writes byte-identically to its golden.
    """
    obj = rt.build_generated_script()
    produced = rt.normalize_uuids(rt.write_bytes(SCRIPT_DOC, obj))
    assert produced == rt.golden_bytes("generated/example_script.xml")
    assert b"<DmxScene>" in produced


def test_the_compatibility_object_is_gone():
    """Its removal target was this feature, recorded in 004's own code."""
    import cuemsutils.xml.mapper as mapper

    assert not hasattr(mapper, "DmxSceneCompatibility")
    assert not hasattr(mapper, "_SwallowAndLog")
