"""Coverage gaps in ``CTimecode`` left by ``test_ctimecode.py``: the
``init_dict``/``from_dict`` construction path, the ``NotImplemented``
fall-through of ``__eq__``/``__ne__`` against a non-``CTimecode`` operand,
``__ne__`` entirely, the ``int``-operand branches of ``__lt__``/``__gt__``,
the ``CTimecode``-operand branches of ``__le__``/``__ge__``, the
unsupported-operand-type ``CTimecodeError`` raised by every arithmetic
dunder, the ``int`` branches of ``__sub__``/``__mul__``, the
defense-in-depth zero-frames guard in ``__truediv__``, and ``__json__``.
"""

from __future__ import annotations

import pytest

from cuemsutils.tools.CTimecode import CTimecode, CTimecodeError


# --- construction: init_dict / from_dict --------------------------------------


def test_init_dict_is_routed_to_start_timecode():
    """``CTimecode.__init__``'s ``init_dict`` parameter is handed to
    upstream's ``start_timecode`` positional slot — same result as
    constructing with ``start_timecode=`` directly."""
    from_start_timecode = CTimecode(framerate=25, start_timecode="00:00:01:00")
    from_init_dict = CTimecode(init_dict="00:00:01:00", framerate=25)

    assert from_init_dict.frames == from_start_timecode.frames


def test_from_dict_classmethod_delegates_to_init_dict():
    tc = CTimecode.from_dict("00:00:01.500")
    assert tc.framerate == 1000
    assert tc.frames == CTimecode(init_dict="00:00:01.500").frames


# --- __eq__ / __ne__ against a non-CTimecode operand ---------------------------


def test_eq_against_a_non_ctimecode_is_false_not_an_error():
    tc = CTimecode(framerate=25, frames=100)
    assert (tc == "not-a-timecode") is False


def test_ne_against_a_non_ctimecode_is_true_not_an_error():
    tc = CTimecode(framerate=25, frames=100)
    assert (tc != "not-a-timecode") is True


def test_ne_true_for_different_values():
    a = CTimecode(framerate=25, frames=100)
    b = CTimecode(framerate=25, frames=200)
    assert a != b


def test_ne_false_for_equal_values():
    a = CTimecode(framerate=25, frames=100)
    b = CTimecode(framerate=25, frames=100)
    assert not (a != b)


# --- int-operand branches of __lt__ / __gt__, CTimecode branches of __le__/__ge__ --


def test_lt_against_an_int_compares_milliseconds_rounded():
    tc = CTimecode(framerate=25, frames=100)
    assert tc < tc.milliseconds_rounded + 1
    assert not (tc < tc.milliseconds_rounded)


def test_gt_against_an_int_compares_milliseconds_rounded():
    tc = CTimecode(framerate=25, frames=100)
    assert tc > tc.milliseconds_rounded - 1
    assert not (tc > tc.milliseconds_rounded)


def test_le_between_two_ctimecodes():
    a = CTimecode(framerate=25, frames=100)
    b = CTimecode(framerate=25, frames=100)
    c = CTimecode(framerate=25, frames=200)
    assert a <= b
    assert a <= c
    assert not (c <= a)


def test_ge_between_two_ctimecodes():
    a = CTimecode(framerate=25, frames=200)
    b = CTimecode(framerate=25, frames=200)
    c = CTimecode(framerate=25, frames=100)
    assert a >= b
    assert a >= c
    assert not (c >= a)


# --- arithmetic: unsupported operand type -> CTimecodeError -------------------


def test_add_unsupported_type_raises():
    tc = CTimecode(framerate=25, frames=100)
    with pytest.raises(CTimecodeError):
        _ = tc + "not-a-number"


def test_sub_unsupported_type_raises():
    tc = CTimecode(framerate=25, frames=100)
    with pytest.raises(CTimecodeError):
        _ = tc - "not-a-number"


def test_mul_unsupported_type_raises():
    tc = CTimecode(framerate=25, frames=100)
    with pytest.raises(CTimecodeError):
        _ = tc * "not-a-number"


def test_truediv_unsupported_type_raises():
    tc = CTimecode(framerate=25, frames=100)
    with pytest.raises(CTimecodeError):
        _ = tc / "not-a-number"


# --- arithmetic: int branches of __sub__ / __mul__ -----------------------------


def test_sub_int_subtracts_frames_directly():
    tc = CTimecode(framerate=25, frames=100)
    assert (tc - 5).frames == 95


def test_mul_int_multiplies_frames_directly():
    tc = CTimecode(framerate=25, frames=100)
    assert (tc * 2).frames == 200


def test_mul_by_a_ctimecode_multiplies_frame_counts():
    a = CTimecode(framerate=25, frames=100)
    b = CTimecode(framerate=25, frames=2)
    assert (a * b).frames == 200


def test_truediv_by_a_ctimecode_divides_frame_counts():
    a = CTimecode(framerate=25, frames=100)
    b = CTimecode(framerate=25, frames=4)
    assert (a / b).frames == 25


# --- __truediv__'s defense-in-depth zero-frames guard --------------------------


def test_truediv_by_a_ctimecode_with_zero_frames_raises():
    """Unreachable through public construction — upstream's ``frames``
    setter rejects 0 with ``ValueError`` before a zero-frame ``CTimecode``
    can exist. Bypasses the setter (``_frames`` directly) to exercise the
    defense-in-depth guard the division code carries anyway."""
    tc = CTimecode(framerate=25, frames=100)
    zero = CTimecode(framerate=25, frames=1)
    zero._frames = 0

    with pytest.raises(CTimecodeError):
        _ = tc / zero


# --- __json__ --------------------------------------------------------------------


def test_json_dunder_returns_the_wrapped_string_form():
    tc = CTimecode(framerate=25, frames=100)
    assert tc.__json__() == {"CTimecode": str(tc)}


def test_json_dumps_uses_the_json_fix_registration():
    import json

    tc = CTimecode(framerate=25, frames=100)
    assert json.dumps(tc) == json.dumps({"CTimecode": str(tc)})
