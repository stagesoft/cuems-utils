"""Clearing an identifier clears it — contract C7, FR-019 row 3 (T034).

**Must FAIL on pre-005 code**: ``Uuid.__init__`` mints a fresh uuid4 whenever
its argument is falsy, so ``script.id = None`` assigns a **new random id**
instead of emptying the field. The initial template ships two random ids that
the code plainly intends to clear — the retired script-template function set them to ``None`` and
they come back populated.

This is a coercion-location fix, not a setter special case (research R7).
``_UuidAdapter.decode`` already returns ``None`` for ``None`` and ``""``; the
setters simply were not using it. Generating an id stays where it belongs — the
``new_uuid`` callable in ``REQ_ITEMS``, which runs at defaulting time, not at
assignment time.
"""

from __future__ import annotations

from cuemsutils.xml.descriptor import generate_script_example
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


# --- the generated example (feature 008, T074) -----------------------------


def test_the_generated_example_carries_populated_identifiers():
    """The retired script-template function's id-blanking step is not
    carried forward (FR-033):

    it existed only to produce a "blank template for the editor to fill in",
    and validating a populated script and then clearing ids on the way out is
    exactly the ordering defect FR-033 names. ``generate_script_example()``
    has nothing to undo that defect *for* — every identifier it sets stays
    set.
    """
    example = generate_script_example()
    assert example["id"] is not None
    assert example["CueList"]["id"] is not None


def test_the_generated_example_carries_its_content():
    example = generate_script_example()
    assert example["name"]
    assert example["CueList"]["contents"]


# --- feature 006 addition (T070, FR-024a) ----------------------------------


def test_the_uuid_shape_check_is_not_in_the_t2_registry():
    """The fifteenth rule, and the one that stayed out.

    The corpus sweep measured every rule against the values the load path
    actually produces. Fourteen would reject nothing. The uuid4 shape check
    would reject **live editor traffic** — three nil ``Media.id`` values in one
    ordinary payload — so it is not a validation rule here at all. It stays a
    *coercion* concern: ``_UuidAdapter`` keeps an unparseable identifier as its
    raw string.

    Asserted as an absence because that is what it is. A registry that acquired
    this rule would be correct-looking and would break the editor on first use.
    """
    from cuemsutils.xml.validators import RULES

    for name in RULES:
        assert "uuid" not in name.lower(), name


def test_an_unparseable_identifier_is_preserved_as_its_raw_string():
    from cuemsutils.xml.adapters import adapter_for

    nil = "00000000-0000-0000-0000-000000000000"
    for type_name in ("UuidType", "TargetType"):
        decoded = adapter_for(type_name).decode(nil)
        assert decoded == nil
        assert isinstance(decoded, str)


def test_the_nil_uuid_survives_the_public_ingestion_path():
    """Through ``from_json``, which is the editor's actual route (FR-002)."""
    import json
    from pathlib import Path

    from cuemsutils.cues.CuemsScript import CuemsScript

    payload = json.loads(Path("tests/data/sample_script.json").read_text())
    script = CuemsScript.from_json(payload["value"])

    media_ids = [
        cue["Media"]["id"]
        for cue in script.cuelist.contents
        if isinstance(cue, dict) and cue.get("Media")
    ]
    assert "00000000-0000-0000-0000-000000000000" in [str(i) for i in media_ids]


def test_validate_does_not_object_to_the_nil_uuid():
    """The rule is absent from the tier, so ``validate()`` says nothing.

    If the uuid check ever joined the registry, this would start reporting
    violations for a payload the editor sends every day — which is the failure
    the sweep exists to have prevented.
    """
    import json
    from pathlib import Path

    from cuemsutils.cues.CuemsScript import CuemsScript

    payload = json.loads(Path("tests/data/sample_script.json").read_text())
    script = CuemsScript.from_json(payload["value"])

    offenders = [
        v for v in script.validate() if "uuid" in v.message.lower()
    ]
    assert not offenders, offenders
