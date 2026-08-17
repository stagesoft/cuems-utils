"""Clearing an identifier clears it — contract C7, FR-019 row 3 (T034).

**Must FAIL on pre-005 code**: ``Uuid.__init__`` mints a fresh uuid4 whenever
its argument is falsy, so ``script.id = None`` assigns a **new random id**
instead of emptying the field. The initial template ships two random ids that
the code plainly intends to clear — ``create_script`` sets them to ``None`` and
they come back populated.

This is a coercion-location fix, not a setter special case (research R7).
``_UuidAdapter.decode`` already returns ``None`` for ``None`` and ``""``; the
setters simply were not using it. Generating an id stays where it belongs — the
``new_uuid`` callable in ``REQ_ITEMS``, which runs at defaulting time, not at
assignment time.
"""

from __future__ import annotations

from cuemsutils.create_script import create_script
from cuemsutils.cues.ActionCue import ActionCue
from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.cues.MediaCue import Media
from cuemsutils.tools.Uuid import Uuid


def test_clearing_a_script_id_leaves_it_empty():
    script = CuemsScript({"name": "probe"})
    assert script["id"] is not None

    script.id = None
    assert script["id"] is None, (
        f"clearing minted {script['id']!r} instead of emptying the field"
    )


def test_clearing_a_cue_list_id_leaves_it_empty():
    script = CuemsScript({"name": "probe"})
    script.cuelist.id = None
    assert script.cuelist["id"] is None


def test_clearing_a_cue_id_leaves_it_empty():
    cue = AudioCue({"name": "probe"})
    cue.id = None
    assert cue["id"] is None


def test_clearing_a_media_id_leaves_it_empty():
    media = Media({"file_name": "f.wav", "id": str(Uuid())})
    media.id = None
    assert media["id"] is None


def test_clearing_an_action_target_leaves_it_empty():
    cue = ActionCue({"action_target": str(Uuid()), "action_type": "play"})
    # ``set_action_target`` guards against ``None`` once initialised, so clear
    # through the empty string the schema's TargetType permits.
    cue.action_target = ""
    assert cue["action_target"] is None


def test_setting_a_real_id_still_works():
    """The inverse: clearing must not become "ids stop working"."""
    script = CuemsScript({"name": "probe"})
    value = str(Uuid())
    script.id = value
    assert isinstance(script["id"], Uuid)
    assert str(script["id"]) == value


def test_generation_still_happens_at_defaulting_time():
    """FR-019 row 3 — assignment stops minting, construction keeps minting.

    ``new_uuid`` in ``REQ_ITEMS`` runs when a field is defaulted. Removing the
    minting from the *setter* must not remove it from *construction*, or every
    newly built object would arrive without an id.
    """
    assert isinstance(CuemsScript({"name": "probe"})["id"], Uuid)
    assert isinstance(AudioCue({"name": "probe"})["id"], Uuid)


# --- the consumer-visible change (FR-022) ---------------------------------


def test_the_initial_template_ships_without_identifiers():
    """The delta the editor sees, asserted as the fields FR-022 enumerates.

    ``create_script`` clears the script and cue-list identifiers at the end;
    three of the five cue identifiers already arrive empty, and these two came
    back random. This is the behaviour change consumers observe.
    """
    template = create_script()
    assert template["id"] is None, f"script id is {template['id']!r}"
    assert template["CueList"]["id"] is None, (
        f"cue-list id is {template['CueList']['id']!r}"
    )


def test_the_initial_template_still_carries_its_content():
    """Clearing ids must not clear anything else."""
    template = create_script()
    assert template["name"]
    assert template["CueList"]["contents"]
    assert len(template["CueList"]["contents"]) == 5
