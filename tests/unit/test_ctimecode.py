# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>
"""
Test harness for CTimecode (cuems-utils wrapper around upstream `timecode` lib).

Class layout mirrors the API surface so each PR in the 869cyndtv hardening pass
can extend the matching class:
- TestConstruction: every ctor path (`init_dict`, `start_timecode`, `start_seconds`,
  `frames`) across the framerate matrix.
- TestArithmetic: __add__, __sub__, __mul__, __truediv__ — same-framerate operands
  and (post-PR-#6) cross-framerate assertion behavior.
- TestComparison: __eq__, __ne__, __lt__, __le__, __gt__, __ge__ — including the
  None-handling protocol-correctness fixes from PR #4.
- TestConversion: return_in_other_framerate round-trips across framerate pairs.
- TestSerialization: items(), __iter__, __json__ — dict/JSON contract (PR #5).
- TestRoundTrip: hypothesis-driven property tests (e.g.,
  CTimecode(frames=N).milliseconds → invertible across the framerate matrix).

The `'ms'` framerate is CTimecode's default (line 6 of CTimecode.py) and is heavily
used by `format_timecode` callers throughout cuems-utils — it must be a first-class
case in every test class.

xfail markers reference the 869cyndtv plan. `strict=True` is intentional: when
the corresponding fix lands the marker must be removed (otherwise CI fails).
Reason strings cite which PR will flip each one.
"""

from __future__ import annotations

import pytest

from cuemsutils.helpers import format_timecode
from cuemsutils.tools.CTimecode import CTimecode


# Standard framerate matrix per the 869cyndtv plan. 'ms' is CTimecode's default.
FRAMERATE_MATRIX: list[int | float | str] = [24, 25, 29.97, 30, "ms"]


@pytest.fixture(params=FRAMERATE_MATRIX, ids=lambda fr: f"fr={fr}")
def framerate(request):
    """Parametrize a test across every framerate cuems cares about."""
    return request.param


class TestConstruction:
    """CTimecode construction paths across the framerate matrix."""

    def test_default_framerate_is_ms(self):
        # 'ms' is the documented default input alias; upstream normalizes the
        # stored framerate to the integer 1000.
        tc = CTimecode()
        assert tc.framerate == 1000

    def test_construct_from_frames(self, framerate):
        tc = CTimecode(framerate=framerate, frames=10)
        assert isinstance(tc, CTimecode)
        assert tc.frames == 10

    @pytest.mark.xfail(
        strict=True,
        reason="869cyndtv issue #3 — start_seconds and start_timecode disagree by "
        "1 frame; PR #6 __init__ canonicalization makes them agree.",
    )
    def test_start_seconds_and_start_timecode_agree(self):
        # Upstream's `start_seconds` uses int(s*fr) (exposure-window semantics);
        # `start_timecode` adds +1 via `tc_to_frames`. cuems needs playhead
        # semantics — both ctor paths must produce the same `frames` for the
        # same real time.
        a = CTimecode(framerate=25, start_seconds=30.0)
        b = CTimecode(framerate=25, start_timecode="00:00:30:00")
        assert a.frames == b.frames

    @pytest.mark.xfail(
        strict=True,
        reason="869cyndtv Option D — framerate getter normalization; PR #6 "
        "overrides .framerate to return canonical types (int/float, not str).",
    )
    def test_framerate_returns_int_for_smpte_rate(self):
        # Upstream stores integer SMPTE framerates as strings ('25', '30').
        # PR #6 adds a getter override that returns canonical types.
        tc = CTimecode(framerate=25, frames=10)
        assert tc.framerate == 25
        assert isinstance(tc.framerate, int)

    @pytest.mark.xfail(
        strict=True,
        reason="869cyndtv Option D — framerate getter normalization for "
        "fractional rates; PR #6.",
    )
    def test_framerate_returns_float_for_fractional_rate(self):
        tc = CTimecode(framerate=29.97, frames=10)
        assert tc.framerate == 29.97
        assert isinstance(tc.framerate, float)

    def test_framerate_is_int_for_ms(self):
        # 'ms' input → upstream normalizes to int 1000. This already works
        # today; pinned as a regression test against the PR #6 getter override.
        tc = CTimecode(framerate="ms", frames=10)
        assert tc.framerate == 1000

    @pytest.mark.xfail(
        strict=True,
        reason="869cyndtv format_timecode — after PR #6 removes the manual +1 "
        "compensation in helpers.py:119, format_timecode(value).milliseconds "
        "must still equal `value` (in ms-frame units at the default 'ms' fr).",
    )
    def test_format_timecode_int_round_trip(self):
        # Default framerate is 'ms' (1 frame == 1 ms). format_timecode(N) is
        # supposed to represent "N ms-frames" — currently it returns a tc whose
        # `start_seconds=N` was passed in (i.e., N seconds at 1000 fps), so the
        # +1 compensation lands `frames=N*1000+1`. After PR #6 canonicalizes
        # __init__ AND drops the manual +1, the contract becomes:
        # format_timecode(N).milliseconds == N for integer N at 'ms' fr.
        tc = format_timecode(30)
        assert tc.milliseconds == 30


class TestArithmetic:
    """Arithmetic dunders. PRs #2 and #6 expand this with the off-by-one captures."""

    def test_add_int_returns_ctimecode(self):
        tc = CTimecode(framerate=25, frames=100)
        result = tc + 1
        assert isinstance(result, CTimecode)

    @pytest.mark.xfail(
        strict=True,
        reason="869cyndtv issue #2 — __add__ uses 1-indexed frames; combined "
        "with .milliseconds (0-indexed) it cancels by accident in some paths "
        "and breaks in others. PR #6 routes __add__ through frame_number.",
    )
    def test_add_position_plus_duration_at_25fps(self):
        # 10s position + 20s duration at 25fps → 30s position == 30000 ms.
        # Currently: tc1.frames=250, tc2.frames=500, sum=750, .milliseconds=29960.
        a = CTimecode(framerate=25, start_seconds=10.0)
        b = CTimecode(framerate=25, start_seconds=20.0)
        assert (a + b).milliseconds == 30000

    @pytest.mark.xfail(
        strict=True,
        reason="869cyndtv __sub__ — symmetric to __add__: returns 1-indexed "
        "subtraction passed back as `frames=`, producing a 0-indexed delta "
        "that's one frame short. PR #6 fixes alongside __add__.",
    )
    def test_sub_position_minus_position_at_25fps(self):
        # 30s - 10s == 20s == 20000 ms. Currently returns 19960.
        a = CTimecode(framerate=25, start_seconds=30.0)
        b = CTimecode(framerate=25, start_seconds=10.0)
        assert (a - b).milliseconds == 20000

    @pytest.mark.xfail(
        strict=True,
        reason="869cyndtv issue #7 — __truediv__ produces float frames and "
        "passes them to upstream ctor which raises TypeError. PR #6 round()s.",
    )
    def test_truediv_int_produces_valid_ctimecode(self):
        tc = CTimecode(framerate=25, frames=100)
        result = tc / 3
        assert isinstance(result, CTimecode)
        assert isinstance(result.frames, int)

    @pytest.mark.xfail(
        strict=True,
        reason="869cyndtv same-framerate assertion — cross-framerate arithmetic "
        "currently silently uses other.frames as if same-framerate. PR #6 adds "
        "a same-framerate assertion in __add__/__sub__/__mul__/__truediv__.",
    )
    def test_add_cross_framerate_raises(self):
        # MTC framerate ≠ media framerate is supported via explicit
        # .return_in_other_framerate() — direct arithmetic must fail loudly.
        a = CTimecode(framerate=25, frames=100)
        b = CTimecode(framerate=30, frames=100)
        with pytest.raises(Exception):  # CTimecodeError after PR #6
            _ = a + b


class TestComparison:
    """Comparison dunders. PR #4 adds None-handling cases here."""

    def test_eq_same_value(self):
        a = CTimecode(framerate=25, frames=100)
        b = CTimecode(framerate=25, frames=100)
        assert a == b

    def test_lt_with_none_raises(self):
        # Python data-model contract: comparators return NotImplemented for
        # unsupported types (including None); Python then raises TypeError.
        tc = CTimecode(framerate=25, frames=100)
        with pytest.raises(TypeError):
            _ = tc < None

    def test_le_with_none_raises(self):
        tc = CTimecode(framerate=25, frames=100)
        with pytest.raises(TypeError):
            _ = tc <= None

    def test_gt_with_none_raises(self):
        tc = CTimecode(framerate=25, frames=100)
        with pytest.raises(TypeError):
            _ = tc > None

    def test_ge_with_none_raises(self):
        tc = CTimecode(framerate=25, frames=100)
        with pytest.raises(TypeError):
            _ = tc >= None

    def test_hash_uses_single_field(self):
        tc = CTimecode(framerate=25, frames=100)
        assert hash(tc) == hash((tc.milliseconds,))

    def test_hash_consistent_with_eq(self):
        # Pin as a regression test against PR #4's __hash__ change.
        a = CTimecode(framerate=25, frames=100)
        b = CTimecode(framerate=25, frames=100)
        assert a == b
        assert hash(a) == hash(b)

    def test_sorted_with_none_raises(self):
        # Practical impact of PR #4's None-handling fix: sorting a list with
        # None mixed in must raise TypeError, not silently corrupt the order.
        tc = CTimecode(framerate=25, frames=100)
        with pytest.raises(TypeError):
            sorted([tc, None])


class TestConversion:
    """return_in_other_framerate. PR #6 adds round-trip stability tests."""

    @pytest.mark.xfail(
        strict=True,
        reason="869cyndtv issue #1 — return_in_other_framerate goes through "
        "the lossy .milliseconds → start_seconds round-trip, dropping a frame "
        "every conversion. PR #6 rewrites in frame domain via frame_number.",
    )
    def test_round_trip_25_to_30_to_25_preserves_frames(self):
        # Conversion to another framerate and back to the original must
        # preserve the original frame count for any reasonable frame value.
        original = CTimecode(framerate=25, frames=750)  # 30s at 25fps
        round_tripped = original.return_in_other_framerate(30).return_in_other_framerate(25)
        assert round_tripped.frames == original.frames


class TestSerialization:
    """items(), __iter__, __json__ — dict/JSON serialization contract (PR #5)."""

    def test_items_constructs_dict(self):
        # items() mirrors __iter__: list of (k, v) pairs that dict() consumes.
        tc = CTimecode(framerate=25, frames=100)
        d = dict(tc.items())
        assert "timecode" in d
        assert "framerate" in d

    def test_items_matches_iter(self):
        # Pin: items() must stay aligned with __iter__'s shape.
        tc = CTimecode(framerate=25, frames=100)
        assert tc.items() == list(tc)

    def test_iter_constructs_dict(self):
        # __iter__ already yields (k, v) pairs correctly. Pin as regression.
        tc = CTimecode(framerate=25, frames=100)
        d = dict(tc)
        assert "timecode" in d
        assert "framerate" in d


class TestRoundTrip:
    """Hypothesis-driven invariants. PR #6 populates these."""

    @pytest.mark.xfail(
        strict=True,
        reason="869cyndtv issue #4 + TODO line 23 — .milliseconds truncates "
        "via int(), losing sub-ms precision at non-integer framerates. PR #6 "
        "switches to exact precision (round() or float return).",
    )
    def test_milliseconds_exact_precision_at_2997(self):
        # frame 31 at 29.97fps → frame_number 30 → exact ms = 30 * 1000 / 29.97
        # ≈ 1001.001001. Currently int() truncates to 1001.
        tc = CTimecode(framerate=29.97, frames=31)
        expected = 30 * 1000 / 29.97
        assert tc.milliseconds == pytest.approx(expected, abs=1e-9)
