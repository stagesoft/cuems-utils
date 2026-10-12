"""One defaulting protocol — contract C9, FR-017/FR-018 (T033).

**Must FAIL on pre-005 code**: six classes return an *empty* object from bare
construction while thirteen return full defaults. Same question, two answers,
depending on which class you happened to ask.

Two counts run through this feature and are easy to conflate:

* **six** classes gain declared *defaults* — ``Cue``, ``CuemsScript``,
  ``Media`` and the three ``CueOutput`` subclasses (data-model §2, ``bare = 0``);
* **five** gain a declared *field set* — ``Media``, ``Region`` and the three
  ``CueOutput`` subclasses (§3), which is what moved coherence to 18/18.

Different sets. This file is about the first.
"""

from __future__ import annotations

import pytest

from cuemsutils.cues.ActionCue import ActionCue
from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.cues.Cue import Cue
from cuemsutils.cues.CueList import CueList
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.cues.CueOutput import AudioCueOutput, DmxCueOutput, VideoCueOutput
from cuemsutils.cues.DmxCue import DmxChannel, DmxCue, DmxScene, DmxUniverse
from cuemsutils.cues.FadeCue import FadeCue
from cuemsutils.cues.MediaCue import Media, MediaCue, Region
from cuemsutils.cues.VideoCue import VideoCue
from cuemsutils.helpers import Unset

#: All 17 model classes — 19 minus ``FadeProfile``/``FadeFunctionParameter``,
#: deleted whole (feature 008, FR-007a). Defaulting is parametrised over 17;
#: coherence coverage counts 16, because ``CuemsScript`` is bound by path
#: rather than by type qname and so never appears in that test's
#: parametrisation.
MODEL_CLASSES = [
    Cue, CueList, AudioCue, VideoCue, MediaCue, ActionCue, FadeCue, DmxCue,
    CuemsScript, DmxScene, DmxUniverse, DmxChannel,
    Media, Region, AudioCueOutput, VideoCueOutput,
    DmxCueOutput,
]
IDS = [c.__name__ for c in MODEL_CLASSES]

#: The six that returned an empty object before this feature (research R3).
PREVIOUSLY_EMPTY = {
    Cue, CuemsScript, Media, AudioCueOutput, VideoCueOutput, DmxCueOutput,
}


def test_there_are_seventeen_model_classes():
    """A parametrisation that silently shrank would pass without testing."""
    assert len(MODEL_CLASSES) == 17
    assert len(set(MODEL_CLASSES)) == 17


@pytest.mark.parametrize("model", MODEL_CLASSES, ids=IDS)
def test_every_class_declares_its_defaults(model):
    """FR-017 — one protocol, answered the same way by every class."""
    declared = model.declared_defaults()
    assert isinstance(declared, dict)
    assert declared, f"{model.__name__} declares no fields at all"
    assert tuple(declared) == model.declared_fields()


@pytest.mark.parametrize("model", MODEL_CLASSES, ids=IDS)
def test_bare_construction_yields_the_declared_defaults(model):
    """The claim itself: ``cls()`` contains exactly its declared fields.

    Fields declared ``Unset`` are **absent**, not present-and-empty — that is
    what stops six newly-defaulted classes from emitting elements their
    documents never contained.
    """
    obj = model()
    expected = {
        key for key, value in model.declared_defaults().items() if value is not Unset
    }
    assert set(obj.keys()) == expected, (
        f"{model.__name__}() has {sorted(obj.keys())}, expected {sorted(expected)}"
    )


@pytest.mark.parametrize(
    "model", sorted(PREVIOUSLY_EMPTY, key=lambda c: c.__name__),
    ids=lambda c: c.__name__,
)
def test_the_six_previously_empty_classes_are_no_longer_empty(model):
    """FR-019 row 5 — ``Cue()`` is no longer empty.

    The consumer-visible half of change 5. Any code that relied on the empty
    result has to be found, which T036's sweep records.
    """
    if all(v is Unset for v in model.declared_defaults().values()):
        pytest.skip(f"{model.__name__} declares every field Unset by design")
    assert model(), f"{model.__name__}() is still empty"


@pytest.mark.parametrize("model", MODEL_CLASSES, ids=IDS)
def test_bare_construction_never_invents_an_undeclared_key(model):
    assert set(model()).issubset(set(model.declared_fields()))


def test_unset_fields_stay_absent():
    """``VideoCueOutput.canvas_region`` is the case that matters.

    It is ``minOccurs="0"``, an alias output must **not** carry it, and
    inserting it as ``None`` would both emit an element no document contained
    and trip ``__init__``'s own alias/custom consistency rule.
    """
    assert VideoCueOutput.declared_defaults()["canvas_region"] is Unset
    assert "canvas_region" not in VideoCueOutput()


# --- FR-018: REQ_ITEMS keeps both of its jobs ------------------------------


def test_req_items_is_still_the_declared_defaults_source():
    """FR-018, job one: layered defaults.

    ``DECLARED_DEFAULTS`` *is* ``REQ_ITEMS`` — the same object, not a copy — so
    there is no second source of truth to drift from.
    """
    from cuemsutils.cues import Cue as cue_module

    assert Cue.DECLARED_DEFAULTS is cue_module.REQ_ITEMS


@pytest.mark.parametrize(
    "model", [Cue, ActionCue, FadeCue, DmxChannel],
    ids=lambda c: c.__name__,
)
def test_req_items_is_still_the_alphabetical_developer_index(model):
    """FR-018, job two: the alphabetical index is unchanged.

    Two dicts were reordered by this feature — ``AudioCue`` and ``VideoCue`` —
    and both were reordered *into* alphabetical order, which is the property
    this job describes. They had been the only two whose literal order differed
    from the order their own ``items()`` emitted, via ``sorted()``.
    """
    own = list(model.DECLARED_DEFAULTS)
    assert own == sorted(own), f"{model.__name__}.REQ_ITEMS is not alphabetical"


def test_the_two_reordered_dicts_are_now_alphabetical():
    """The reorder T006 required, asserted rather than described."""
    import importlib

    for name in ("AudioCue", "VideoCue"):
        # The module, not the class ``cues/__init__`` re-exports under the
        # same name.
        module = importlib.import_module(f"cuemsutils.cues.{name}")
        keys = list(module.REQ_ITEMS)
        assert keys == sorted(keys), f"{name}.REQ_ITEMS is {keys}"


# --- the inheritance chain ------------------------------------------------


def test_defaults_accumulate_across_the_mro():
    """A subclass declares only what it adds."""
    assert "master_vol" in AudioCue.declared_defaults()
    assert "master_vol" not in MediaCue.declared_defaults()

    # The thirteen common properties come from Cue, at every depth.
    for field in Cue.declared_fields():
        assert field in AudioCue.declared_fields()
        assert field in FadeCue.declared_fields()


def test_sibling_subclasses_do_not_share_a_field_set():
    """The MRO-inheritance trap, on declarations rather than adapters."""
    assert "master_vol" in AudioCue.declared_fields()
    assert "master_vol" not in VideoCue.declared_fields()
    assert "opacity" in VideoCue.declared_fields()
    assert "opacity" not in AudioCue.declared_fields()
