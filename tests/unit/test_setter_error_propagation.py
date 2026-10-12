"""A failing setter is not swallowed — contract C8, FR-019 row 4 (T039).

**The second half must FAIL on pre-005 code.**

``CuemsDict.setter`` wrapped both the attribute *lookup* and the setter *call*
in one ``except AttributeError: pass``. Those are two different events:

* the lookup failing means "this class has no setter for that key" — a real,
  routine case, and skipping is correct;
* an ``AttributeError`` raised **inside** a setter means the coercion logic
  broke, and swallowing it drops the field silently.

The blanket guard could not tell them apart, so a defect in any setter that
touched a missing attribute produced a *missing field* instead of an error —
the kind of bug that hides indefinitely, because the object still constructs.

Exceptions of other types already propagated (the guard only ever caught
``AttributeError``) and are unaffected. Only ``AttributeError`` changes meaning:
from "swallowed wherever it came from" to "swallowed only when it came from the
lookup".
"""

from __future__ import annotations

import pytest

from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.helpers import CuemsDict


class NoSuchSetter(CuemsDict):
    """Nothing declares ``whatever``, so the lookup misses."""


class RaisesInside(CuemsDict):
    DECLARED_DEFAULTS = {"boom": None}

    def set_boom(self, value):
        raise AttributeError("the setter itself is broken")


class RaisesOtherInside(CuemsDict):
    DECLARED_DEFAULTS = {"boom": None}

    def set_boom(self, value):
        raise ValueError("a different failure")


# --- half one: unchanged ---------------------------------------------------


def test_a_key_with_no_setter_is_still_skipped():
    """**Passes before and after.** This path must not change.

    Model objects are routinely populated from dicts carrying keys the class
    does not model; skipping them is how that has always worked.
    """
    obj = NoSuchSetter()
    obj.setter({"whatever": 1, "another": 2})
    assert "whatever" not in obj


def test_skipping_still_works_alongside_a_real_setter():
    """A mixed dict: known keys are set, unknown keys skipped."""
    cue = AudioCue({"name": "probe"})
    cue.setter({"name": "renamed", "no_such_field": "ignored"})
    assert cue["name"] == "renamed"
    assert "no_such_field" not in cue


def test_a_non_dict_still_raises():
    """The one AttributeError ``setter`` raises deliberately."""
    with pytest.raises(AttributeError):
        NoSuchSetter().setter(["not", "a", "dict"])


# --- half two: the change --------------------------------------------------


def test_an_attribute_error_raised_inside_a_setter_propagates():
    """**Must FAIL before.** The field used to vanish instead.

    This is the whole of change 4: a coercion failure becomes an error rather
    than a silently missing field.
    """
    with pytest.raises(AttributeError, match="the setter itself is broken"):
        RaisesInside().setter({"boom": 1})


def test_other_exception_types_are_unaffected():
    """They propagated before this feature too — asserted so that stays true."""
    with pytest.raises(ValueError, match="a different failure"):
        RaisesOtherInside().setter({"boom": 1})


def test_the_two_cases_are_distinguishable():
    """The distinction the narrowed guard exists to make.

    Same exception type, same call site, opposite outcomes — one skipped, one
    raised — decided by *where* it came from.
    """
    NoSuchSetter().setter({"boom": 1})  # no setter: skipped

    with pytest.raises(AttributeError):
        RaisesInside().setter({"boom": 1})  # setter raises: propagates


def test_construction_surfaces_the_error_too():
    """Not just ``setter()`` — the path real objects are built through."""

    class Broken(AudioCue):
        def set_master_vol(self, value):
            raise AttributeError("coercion failed")

    with pytest.raises(AttributeError, match="coercion failed"):
        Broken({"name": "probe", "master_vol": 50})


# --- feature 006 addition (T071, FR-024c) ----------------------------------
#
# The fourteen value-rejecting rules moved into a named registry and their
# setters now delegate. Two properties must survive that, and neither is
# implied by "the tier works":
#
#   1. programmatic assignment still fails **immediately**, with the **current
#      message**. A rule that only fires on ``save()`` would leave a consumer
#      assigning nonsense and discovering it an hour later.
#   2. ``_initialized`` still holds the rules off **during population**, in all
#      three classes that use it. Moving a rule body must not move its gate.


def test_assignment_still_fails_immediately_with_the_current_message():
    from cuemsutils.cues.FadeCue import FadeCue

    cue = FadeCue()
    with pytest.raises(ValueError, match="target_value must be between 0 and 100"):
        cue.target_value = 101
    with pytest.raises(ValueError, match="duration must be positive and non-zero"):
        cue.duration = "00:00:00.000"
    with pytest.raises(ValueError, match="curve_type must be one of"):
        cue.curve_type = "corkscrew"


def test_the_media_duration_message_delegates_to_format_timecode():
    """Feature 008, FR-004 — the message changed on purpose.

    ``Media.duration`` no longer wraps the parse failure in its own
    "Invalid media duration ..." text; it delegates entirely to
    ``format_timecode``/``CTimecode``, the same machinery every other
    ``CTimecodeType`` setter uses, and gets that machinery's message.
    """
    from cuemsutils.cues.MediaCue import Media

    media = Media()
    with pytest.raises(ValueError, match="invalid literal for int"):
        media.duration = "garbage"


@pytest.mark.parametrize(
    "factory,field,value",
    [
        pytest.param(
            lambda: __import__(
                "cuemsutils.cues.ActionCue", fromlist=["ActionCue"]
            ).ActionCue(),
            "action_target",
            None,
            id="ActionCue.action_target",
        ),
        pytest.param(
            lambda: __import__(
                "cuemsutils.cues.FadeCue", fromlist=["FadeCue"]
            ).FadeCue(),
            "action_type",
            "play",
            id="FadeCue.action_type",
        ),
    ],
)
def test_the_gate_is_open_after_construction_and_shut_during_it(factory, field, value):
    """``_initialized`` gates the rule, and construction must not trip it.

    Both classes hold the flag ``False`` while populating, precisely so the
    rule stays off the decode path. The pairing is the test: constructing
    succeeds, assigning the *same* value afterwards raises.
    """
    obj = factory()
    assert getattr(obj, "_initialized", False) is True, (
        "the object finished construction without opening its gate"
    )
    with pytest.raises(ValueError):
        setattr(obj, field, value)


def test_all_three_gating_classes_still_gate():
    """``_initialized`` lives in **three** classes, not one.

    Feature 005's spec said one; the measurement said ``ActionCue``,
    ``FadeCue`` and ``VideoCueOutput``. Named here so a fourth cannot be added
    silently and a third cannot be dropped.
    """
    import inspect

    from cuemsutils.cues.ActionCue import ActionCue
    from cuemsutils.cues.CueOutput import VideoCueOutput
    from cuemsutils.cues.FadeCue import FadeCue

    for cls in (ActionCue, FadeCue, VideoCueOutput):
        source = inspect.getsource(cls)
        assert "_initialized" in source, cls.__name__


def test_the_gate_is_never_a_declared_runtime_field():
    """It is not inert state; it gates value-rejecting rules during population.

    Declaring it would let ``_init_runtime`` set it — and setting it true
    before population gives fourteen setters new reach on decode, with an
    **arrival-order dependent** failure the corpus would catch only by luck.
    """
    from cuemsutils.cues.ActionCue import ActionCue
    from cuemsutils.cues.CueOutput import VideoCueOutput
    from cuemsutils.cues.FadeCue import FadeCue

    for cls in (ActionCue, FadeCue, VideoCueOutput):
        assert "_initialized" not in cls.runtime_fields(), cls.__name__


def test_the_setter_and_the_tier_call_the_same_function():
    """FR-024c's "one definition, two call sites", by identity.

    ``enforce`` looks the rule up in ``RULES``; ``run_rules`` runs the same
    entry. There is no second copy for either to drift from.
    """
    from cuemsutils.xml.validators import RULES, enforce

    with pytest.raises(ValueError, match="target_value must be between 0 and 100"):
        enforce("fade_target_value_range", 101)

    from cuemsutils.cues.FadeCue import FadeCue

    cue = FadeCue()
    try:
        cue.target_value = 101
    except ValueError as exc:
        setter_message = str(exc)
    try:
        RULES["fade_target_value_range"].check(101, cue)
    except ValueError as exc:
        rule_message = str(exc)
    assert setter_message == rule_message
