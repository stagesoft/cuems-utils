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
