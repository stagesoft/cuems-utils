"""Runtime state survives every entry point — contract C12, FR-004a (T009).

**This test passes on pre-005 code.** It is not a fix; it is a guard on what
must not be lost while the constructor path is replaced. A decoded cue that
arrives without ``_go_thread`` fails at *playback*, in a running show, not at
load — so the guarantee is written down before the code that could break it
moves.

Two halves, and they fail in opposite directions:

* runtime attributes must be **present** on objects from every entry point;
* they must be **absent** from ``items()``, the XML and both wire projections —
  a runtime attribute that leaked into the document would be persisted and then
  decoded back as data.
"""

from __future__ import annotations

import pytest

from cuemsutils.cues.ActionCue import ActionCue
from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.cues.Cue import Cue
from cuemsutils.cues.CueList import CueList
from cuemsutils.cues.CueOutput import VideoCueOutput
from cuemsutils.cues.DmxCue import DmxCue
from cuemsutils.cues.FadeCue import FadeCue
from cuemsutils.cues.MediaCue import MediaCue
from cuemsutils.cues.VideoCue import VideoCue
from tests.support import roundtrip as rt
from tests.support.corpus import by_relpath

#: The largest corpus document — the one with the widest variety of cue types.
LARGEST = "cuems-engine/projects/complex_test/script.xml"

#: Measured across ``cues/`` (data-model §5). Named here so a new one added
#: without a thought about persistence shows up as an unlisted attribute.
RUNTIME_ATTRIBUTES = frozenset(
    {
        "_target_object",
        "_conf",
        "_armed_list",
        "_start_mtc",
        "_end_mtc",
        "_end_reached",
        "_go_thread",
        "_stop_requested",
        "_local",
        "_player",
        "_osc_route",
        "_initialized",
        "_action_target_object",
        "_offset_route",
    }
)

CUE_CLASSES = [Cue, CueList, MediaCue, AudioCue, VideoCue, ActionCue, FadeCue, DmxCue]
IDS = [c.__name__ for c in CUE_CLASSES]

#: A minimal *valid* init dict per class. Written out rather than derived from
#: ``declared_defaults()``, because two classes reject their own declared
#: defaults when handed back as an init dict: ``ActionCue.__init__`` raises on
#: an explicit ``action_target=None``, which is exactly what its defaults
#: contain. That asymmetry is pre-existing and out of scope here — this test is
#: about runtime state, and reproducing it would only obscure that.
INIT_DICTS = {
    Cue: {"name": "probe"},
    CueList: {"name": "probe", "contents": []},
    MediaCue: {"name": "probe"},
    AudioCue: {"name": "probe"},
    VideoCue: {"name": "probe"},
    ActionCue: {"action_target": "probe-target", "action_type": "play"},
    FadeCue: {"action_target": "probe-target", "action_type": "fade_action"},
    DmxCue: {"name": "probe"},
}

#: An ``output_name`` of the alias shape ``<uuid>_<int>`` that
#: ``_classify_output_name`` accepts (``CueOutput.py:13-15``).
ALIAS_OUTPUT_NAME = "0367f391-ebf4-48b2-9f26-000000000001_0"
CUSTOM_OUTPUT_NAME = "0367f391-ebf4-48b2-9f26-000000000001_custom_0"


def runtime_state(obj) -> set[str]:
    """The runtime attributes actually present on ``obj``."""
    return {name for name in RUNTIME_ATTRIBUTES if hasattr(obj, name)}


@pytest.mark.parametrize("model", CUE_CLASSES, ids=IDS)
def test_bare_construction_initializes_runtime_state(model):
    """Every cue class carries runtime state — the baseline the rest compares to."""
    assert runtime_state(model()), f"{model.__name__} initialized no runtime state"


@pytest.mark.parametrize("model", CUE_CLASSES, ids=IDS)
def test_construction_from_a_dict_matches_bare_construction(model):
    """The two programmatic entry points agree.

    ``cls()`` and ``cls(init_dict)`` take different branches in every cue
    ``__init__``; only one of them is exercised by most tests.
    """
    bare = runtime_state(model())
    from_dict = runtime_state(model(dict(INIT_DICTS[model])))
    assert from_dict == bare


@pytest.mark.parametrize("model", CUE_CLASSES, ids=IDS)
def test_runtime_attributes_are_not_persisted(model):
    """They are instance attributes, never dict keys.

    The two must not be confusable: a runtime attribute that became a key would
    be emitted, validated against the schema, and decoded back as data.
    """
    # Built from an init dict, not bare: ``Cue()`` is empty today (the F20
    # defect this feature fixes), and its ``items()`` raises ``KeyError`` on
    # the declared fields that were never inserted.
    obj = model(dict(INIT_DICTS[model]))
    assert RUNTIME_ATTRIBUTES.isdisjoint(set(obj.keys()))
    assert RUNTIME_ATTRIBUTES.isdisjoint({k for k, _ in obj.items()})


@pytest.fixture(scope="module")
def corpus_script():
    return rt.read_objects(by_relpath(LARGEST))


def test_decoded_cues_carry_the_same_runtime_state_as_built_ones(corpus_script):
    """The guarantee this feature must not lose (FR-004a).

    Decode reaches model objects through the mapper rather than through a
    direct constructor call. Today that path happens to call ``model()``;
    feature 005 replaces it. This asserts the outcome rather than the mechanism,
    so it keeps holding across the swap.
    """
    checked = 0
    for cue in corpus_script["CueList"]["contents"]:
        model = type(cue)
        if model not in CUE_CLASSES:
            continue
        assert runtime_state(cue) == runtime_state(model()), (
            f"decoded {model.__name__} has runtime state "
            f"{sorted(runtime_state(cue))}, built has "
            f"{sorted(runtime_state(model()))}"
        )
        checked += 1
    assert checked, "no cue in the corpus document was checked"


def test_initialized_is_false_during_population_and_true_after():
    """``_initialized`` is **not** an ordinary runtime attribute.

    It gates value-rejecting rules in three classes — ``ActionCue``'s
    ``set_action_target``, ``FadeCue``'s ``set_action_type`` and
    ``VideoCueOutput``'s ``set_output_name`` / ``set_canvas_region`` — and each
    holds it ``False`` *while populating* so those rules stay off the load path.
    ``CuemsDict.setter`` does resolve and call those setters during
    construction, so the flag is the only thing keeping them out.

    If ``_init_runtime()`` ever sets it true before population, fourteen
    inventoried setters gain reach on decode (FR-006b forbids it) and the
    failure is **arrival-order dependent**: a ``custom`` ``output_name``
    arriving before ``canvas_region`` raises, the reverse order does not. The
    corpus catches that only by luck, so it is asserted directly here.
    """
    seen = []

    class Probe(ActionCue):
        def set_action_type(self, action_type):
            seen.append(getattr(self, "_initialized", "absent"))
            super().set_action_type(action_type)

    obj = Probe({"action_target": "x", "action_type": "play"})

    assert seen, "the probe setter never ran during population"
    assert all(flag is False for flag in seen), (
        f"_initialized was {seen} during population; it must be False "
        f"throughout, or the gated rules reach the load path"
    )
    assert obj._initialized is True


def test_initialized_gates_the_video_output_rules_the_same_way():
    """The case contract C12 names, asserted at its own call site."""
    output = VideoCueOutput({"output_name": ALIAS_OUTPUT_NAME})
    assert output._initialized is True

    # With the flag true, the region-consistency rule is live: switching an
    # alias output to the custom shape without a canvas_region is rejected.
    with pytest.raises(ValueError):
        output.set_output_name(CUSTOM_OUTPUT_NAME)

    # The same object populated through ``__init__`` with the *same* pairing
    # does not raise, because the flag is false throughout population. That
    # asymmetry is what FR-006b requires this feature to leave standing.
    assert VideoCueOutput({"output_name": ALIAS_OUTPUT_NAME}) is not None


def test_action_cue_target_rule_is_gated_the_same_way():
    """``ActionCue`` carries the same pattern, and the spec did not enumerate it.

    Discovered while implementing T008: ``set_action_target`` raises on ``None``
    only once ``_initialized`` is true, exactly as ``VideoCueOutput``'s rules
    do. It is asserted here so the flag's contract is pinned at every site that
    depends on it, not only the one the contract document happened to name.
    """
    cue = ActionCue({"action_target": "x"})
    assert cue._initialized is True
    with pytest.raises(ValueError):
        cue.action_target = None

    # Population with the same value does **not** raise, because the flag is
    # false throughout — this is the asymmetry the load path depends on.
    assert ActionCue({"action_type": "play"})["action_target"] is None
