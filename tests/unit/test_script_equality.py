"""Equality, copy and hashability on the model base (T020) — FR-028b/c/d.

Three properties, one of which is invisible until it breaks in somebody else's
repository:

**Equality compares declared fields only.** That is what makes
``load(save(x)) == load(x)`` hold after a show has been running: playback state
lives in instance attributes, not in the document, and two scripts differing
only in it are the same script. It **widens** ``Cue.__eq__``, which compares by
``id`` alone today — enumerated behaviour change 5.

**Copy yields fresh runtime state.** A copied cue that shares its parent's
``_go_thread`` is a cue that stops the wrong playback. Asserted under
``copy.copy`` *and* ``copy.deepcopy``, because they take different paths.

**Hashability survives.** Defining ``__eq__`` without restating ``__hash__``
sets it to ``None``, and every cue becomes unhashable. It produces no failure
in any test that does not itself hash a cue, is invisible in review, and
surfaces as a ``TypeError`` in the engine. So it is asserted, not preserved and
hoped for.
"""

from __future__ import annotations

import copy

import pytest

from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.cues.Cue import Cue
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.cues.VideoCue import VideoCue
from tests.support import invalid_scripts as broken
from tests.support.corpus import by_relpath

RUNTIME_SENTINEL = object()

#: A **fixed** document, not the generated template. ``create_script`` mints a
#: fresh uuid per call, so two of its scripts differ in a declared field by
#: construction — which is correct behaviour and useless as an equality
#: fixture. Loading the same document twice gives two independent objects with
#: identical content, which is the pair equality is actually about.
DOC = by_relpath("cuems-engine/projects/complex_test/script.xml")


def _a_script() -> CuemsScript:
    return CuemsScript.load(DOC.path)


def _a_cue() -> Cue:
    return _a_script().cuelist.contents[0]


# --- equality -------------------------------------------------------------


def test_two_independently_loaded_scripts_with_the_same_content_are_equal():
    assert _a_script() == _a_script()


def test_playback_state_does_not_affect_equality():
    left, right = _a_script(), _a_script()
    left.cuelist.contents[0]._go_thread = RUNTIME_SENTINEL
    left.cuelist.contents[0]._end_reached = True
    assert left == right


def test_a_declared_field_difference_does_affect_equality():
    left, right = _a_script(), _a_script()
    right.name = "a different show"
    assert left != right


def test_cue_equality_is_wider_than_id():
    """Behaviour change 5, asserted directly.

    Two cues sharing an id but differing in a declared field used to compare
    **equal**, because ``Cue.__eq__`` looked at ``id`` and nothing else.
    """
    left, right = _a_cue(), _a_cue()
    assert left == right

    right.name = "renamed"
    assert right.id == left.id
    assert left != right


def test_a_cue_is_not_equal_to_a_cue_of_a_different_class():
    audio, video = AudioCue(), VideoCue()
    video["id"] = audio["id"]
    assert audio != video


def test_load_save_load_round_trips_to_an_equal_script(tmp_path):
    first = tmp_path / "a.xml"
    second = tmp_path / "b.xml"

    original = broken.valid_script()
    original.save(first)

    loaded = CuemsScript.load(first)
    loaded.cuelist.contents[0]._go_thread = RUNTIME_SENTINEL
    loaded.save(second)

    assert CuemsScript.load(second) == CuemsScript.load(first)


# --- hashability ----------------------------------------------------------


def test_a_cue_is_hashable_and_survives_a_set_and_a_dict_key():
    cue = _a_cue()
    assert isinstance(hash(cue), int)
    assert cue in {cue}
    assert {cue: "value"}[cue] == "value"


def test_equal_cues_hash_equal():
    left, right = _a_cue(), _a_cue()
    assert left == right
    assert hash(left) == hash(right)


# --- copy -----------------------------------------------------------------


@pytest.mark.parametrize("clone", [copy.copy, copy.deepcopy], ids=["copy", "deepcopy"])
def test_copying_a_cue_yields_fresh_runtime_state(clone):
    cue = _a_cue()
    cue._go_thread = RUNTIME_SENTINEL
    cue._end_reached = True

    duplicate = clone(cue)

    assert duplicate._go_thread is not RUNTIME_SENTINEL
    assert duplicate._end_reached is False


@pytest.mark.parametrize("clone", [copy.copy, copy.deepcopy], ids=["copy", "deepcopy"])
def test_copying_never_shares_a_timecode_instance(clone):
    """The factory-defaults constraint, observed from the outside."""
    cue = _a_cue()
    duplicate = clone(cue)
    assert duplicate._start_mtc is not cue._start_mtc
    assert duplicate._end_mtc is not cue._end_mtc


@pytest.mark.parametrize("clone", [copy.copy, copy.deepcopy], ids=["copy", "deepcopy"])
def test_a_copy_is_equal_and_keeps_its_class(clone):
    cue = _a_cue()
    duplicate = clone(cue)
    assert type(duplicate) is type(cue)
    assert duplicate == cue


def test_deepcopy_does_not_share_declared_containers():
    script = broken.valid_script()
    duplicate = copy.deepcopy(script)
    assert duplicate.cuelist is not script.cuelist
    duplicate.cuelist.contents.pop()
    assert len(duplicate.cuelist.contents) != len(script.cuelist.contents)
