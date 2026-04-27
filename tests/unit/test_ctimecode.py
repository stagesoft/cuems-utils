# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>
"""
Test harness for CTimecode (cuems-utils wrapper around upstream `timecode` lib).

Class layout mirrors the API surface:
- TestConstruction: every ctor path (`init_dict`, `start_timecode`, `start_seconds`,
  `frames`) across the framerate matrix.
- TestArithmetic: __add__, __sub__, __mul__, __truediv__ — same-framerate operands
  and cross-framerate assertion behavior.
- TestComparison: __eq__, __ne__, __lt__, __le__, __gt__, __ge__ — including
  None-handling protocol-correctness (PR #4).
- TestConversion: return_in_other_framerate round-trips across framerate pairs.
- TestSerialization: items(), __iter__, __json__ — dict/JSON contract (PR #5).
- TestPrecisionSplit: V2 deprecation contract for .milliseconds /
  .milliseconds_rounded / .milliseconds_exact (PR #6).
- TestRoundTrip: hypothesis-driven property tests.

The `'ms'` framerate is CTimecode's default and is heavily used by
`format_timecode` callers throughout cuems-utils — first-class case in every
test class.
"""

from __future__ import annotations

import warnings

import pytest
from hypothesis import given, settings, strategies as st

from cuemsutils.helpers import format_timecode
from cuemsutils.tools.CTimecode import CTimecode, CTimecodeError


# Standard framerate matrix per the 869cyndtv plan. 'ms' is CTimecode's default.
FRAMERATE_MATRIX: list[int | float | str] = [24, 25, 29.97, 30, "ms"]


@pytest.fixture(params=FRAMERATE_MATRIX, ids=lambda fr: f"fr={fr}")
def framerate(request):
    """Parametrize a test across every framerate cuems cares about."""
    return request.param


# ----------------------------------------------------------------------
# TestConstruction
# ----------------------------------------------------------------------
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

    def test_start_seconds_and_start_timecode_agree(self):
        # Playhead-semantics canonicalization (PR #6 __init__): both ctor
        # paths produce identical `frames` for the same real time.
        a = CTimecode(framerate=25, start_seconds=30.0)
        b = CTimecode(framerate=25, start_timecode="00:00:30:00")
        assert a.frames == b.frames

    def test_start_seconds_zero_gives_frame_one(self):
        # Special case: upstream raises on start_seconds=0; the wrapper
        # neutralizes to the default '00:00:00:00' path which produces
        # frames=1 (== playhead at t=0).
        tc = CTimecode(framerate=25, start_seconds=0)
        assert tc.frames == 1

    def test_canonicalization_at_25fps_minute_boundary(self):
        # Non-DF parity check: the canonicalized start_seconds path matches
        # the start_timecode path at the 1-minute boundary (well past the
        # default test framerate's first integer rollover).
        a = CTimecode(framerate=25, start_seconds=60.0)
        b = CTimecode(framerate=25, start_timecode="00:01:00:00")
        assert a.frames == b.frames == 1501

    @pytest.mark.parametrize(
        "seconds,expected_frames",
        [
            (60.0, 1799),    # 1 min: drop 2 frames per non-10th minute
            (600.0, 17983),  # 10 min: 18 frames dropped (9 non-10th minutes × 2)
            (660.0, 19781),  # 11 min: 20 frames dropped (verified empirically)
        ],
    )
    def test_canonicalization_at_2997_df_minute_boundaries(self, seconds, expected_frames):
        # Drop-frame parity (Sonnet BLOCKER #1 from PR #6 plan review):
        # the canonicalized start_seconds path must match start_timecode at
        # DF minute boundaries. The naive `round(s*ifr)+1` formula gave
        # 1801 vs upstream's 1799 at 1min — off by 2; off by 18 at 10min.
        # PR #6 routes through HMSF-string + tc_to_frames to inherit
        # upstream's drop-frame correction.
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        tc_string = f"{h:02d}:{m:02d}:{s:02d}:00"
        a = CTimecode(framerate=29.97, start_seconds=seconds)
        b = CTimecode(framerate=29.97, start_timecode=tc_string)
        assert a.frames == b.frames == expected_frames

    def test_framerate_returns_int_for_smpte_rate(self):
        # Option D (PR #6): upstream stores integer SMPTE rates as strings
        # ('25', '30'); the getter override returns canonical numeric types.
        tc = CTimecode(framerate=25, frames=10)
        assert tc.framerate == 25
        assert isinstance(tc.framerate, int)

    def test_framerate_returns_float_for_fractional_rate(self):
        tc = CTimecode(framerate=29.97, frames=10)
        assert tc.framerate == 29.97
        assert isinstance(tc.framerate, float)

    def test_framerate_is_int_for_ms(self):
        # 'ms' input → upstream normalizes to int 1000. Pinned as regression
        # against the Option D getter.
        tc = CTimecode(framerate="ms", frames=10)
        assert tc.framerate == 1000

    def test_framerate_default_via_getter(self):
        # Default framerate ('ms') round-trips through the getter as int 1000.
        tc = CTimecode()
        assert tc.framerate == 1000
        assert isinstance(tc.framerate, int)

    def test_format_timecode_int_matches_start_timecode_path(self):
        # format_timecode(N) treats N as seconds (helpers.py). After PR #6
        # (__init__ canonicalization + helpers +1 removal), format_timecode
        # must produce the same CTimecode as the start_timecode path for the
        # same real time. Pins the parity contract that helpers' +1
        # compensation removal preserved.
        tc_from_helper = format_timecode(30)
        tc_from_string = CTimecode(framerate="ms", start_timecode="00:00:30.000")
        assert tc_from_helper.frames == tc_from_string.frames


# ----------------------------------------------------------------------
# TestArithmetic
# ----------------------------------------------------------------------
class TestArithmetic:
    """Arithmetic dunders. PR #6 fixes off-by-one + cross-framerate guards."""

    def test_add_int_returns_ctimecode(self):
        tc = CTimecode(framerate=25, frames=100)
        result = tc + 1
        assert isinstance(result, CTimecode)

    def test_add_position_plus_duration_at_25fps(self):
        # 10s position + 20s duration at 25fps → 30s position == 30000 ms.
        # Pre-PR-#6: returned 29960 (1-vs-0-indexed mismatch). Post-PR-#6:
        # __add__ routes through frames-1 to land at the playhead-correct sum.
        a = CTimecode(framerate=25, start_seconds=10.0)
        b = CTimecode(framerate=25, start_seconds=20.0)
        assert (a + b).milliseconds_rounded == 30000

    def test_sub_position_minus_position_at_25fps(self):
        # 30s - 10s == 20s == 20000 ms. Pre-PR-#6: returned 19960.
        a = CTimecode(framerate=25, start_seconds=30.0)
        b = CTimecode(framerate=25, start_seconds=10.0)
        assert (a - b).milliseconds_rounded == 20000

    def test_truediv_int_produces_valid_ctimecode(self):
        # Pre-PR-#6: __truediv__ produced float frames → upstream TypeError.
        # Post-PR-#6: round() the float result.
        tc = CTimecode(framerate=25, frames=100)
        result = tc / 3
        assert isinstance(result, CTimecode)
        assert isinstance(result.frames, int)

    def test_add_cross_framerate_raises(self):
        # MTC framerate ≠ media framerate is supported via explicit
        # .return_in_other_framerate() — direct arithmetic must fail loudly.
        a = CTimecode(framerate=25, frames=100)
        b = CTimecode(framerate=30, frames=100)
        with pytest.raises(CTimecodeError):
            _ = a + b

    def test_sub_cross_framerate_raises(self):
        a = CTimecode(framerate=25, frames=100)
        b = CTimecode(framerate=30, frames=100)
        with pytest.raises(CTimecodeError):
            _ = a - b

    def test_mul_cross_framerate_raises(self):
        a = CTimecode(framerate=25, frames=100)
        b = CTimecode(framerate=30, frames=2)
        with pytest.raises(CTimecodeError):
            _ = a * b

    def test_truediv_cross_framerate_raises(self):
        a = CTimecode(framerate=25, frames=100)
        b = CTimecode(framerate=30, frames=2)
        with pytest.raises(CTimecodeError):
            _ = a / b

    def test_truediv_negative_int_raises(self):
        # Sonnet IMPORTANT #4: tc/-2 must raise, not silently produce frame=1
        # via max(1, negative).
        tc = CTimecode(framerate=25, frames=100)
        with pytest.raises(CTimecodeError):
            _ = tc / -2

    def test_truediv_zero_int_raises(self):
        # tc/0 must raise CTimecodeError, not bubble up ZeroDivisionError.
        tc = CTimecode(framerate=25, frames=100)
        with pytest.raises(CTimecodeError):
            _ = tc / 0

    def test_truediv_clamps_small_to_one_frame(self):
        # round() can yield 0 when self.frames is small and divisor is large.
        # Clamp to 1 (upstream frames setter requires > 0).
        tc = CTimecode(framerate=25, frames=1)
        result = tc / 1000
        assert result.frames == 1

    def test_sub_smaller_minus_larger_raises_value_error(self):
        # Subtracting a larger duration from a smaller position produces
        # frames<=0; upstream's frames setter rejects with ValueError. Pin
        # that this IS the contract (no silent wrap or clamp).
        a = CTimecode(framerate=25, frames=10)
        b = CTimecode(framerate=25, frames=100)
        with pytest.raises((ValueError, TypeError)):
            _ = a - b

    def test_add_int_advances_one_frame(self):
        # int operand path: caller passes a frame count to add. Used by
        # MtcListener for quarter-frame advancement (`self.main_tc + 1`).
        tc = CTimecode(framerate=25, frames=100)
        result = tc + 1
        assert result.frames == 101


# ----------------------------------------------------------------------
# TestComparison
# ----------------------------------------------------------------------
class TestComparison:
    """Comparison dunders + None-handling (PR #4) + post-PR-#6 _rounded migration."""

    def test_eq_same_value(self):
        a = CTimecode(framerate=25, frames=100)
        b = CTimecode(framerate=25, frames=100)
        assert a == b

    def test_lt_with_none_raises(self):
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
        # Post-PR-#6: __hash__ uses _rounded directly (avoids deprecation
        # warning on every hash() call).
        assert hash(tc) == hash((tc.milliseconds_rounded,))

    def test_hash_consistent_with_eq(self):
        a = CTimecode(framerate=25, frames=100)
        b = CTimecode(framerate=25, frames=100)
        assert a == b
        assert hash(a) == hash(b)

    def test_sorted_with_none_raises(self):
        tc = CTimecode(framerate=25, frames=100)
        with pytest.raises(TypeError):
            sorted([tc, None])


# ----------------------------------------------------------------------
# TestConversion
# ----------------------------------------------------------------------
class TestConversion:
    """return_in_other_framerate. PR #6 frame-domain rewrite."""

    def test_round_trip_25_to_30_to_25_preserves_frames(self):
        # Conversion to another framerate and back must preserve the original
        # frame count. Pre-PR-#6: lossy ms→seconds→frames round-trip dropped
        # one frame per conversion.
        original = CTimecode(framerate=25, frames=750)
        round_tripped = original.return_in_other_framerate(30).return_in_other_framerate(25)
        assert round_tripped.frames == original.frames

    def test_round_trip_29_97_to_25_to_29_97(self):
        # Cross-NTSC round-trip: integer rounding may drift by ±1 frame at
        # the conversion boundaries; assert within tolerance.
        original = CTimecode(framerate=29.97, frames=900)
        round_tripped = original.return_in_other_framerate(25).return_in_other_framerate(29.97)
        assert abs(round_tripped.frames - original.frames) <= 1

    def test_milliseconds_preserved_across_conversion(self):
        # Converting framerates preserves real-time milliseconds (within one
        # frame at the target rate's resolution).
        original = CTimecode(framerate=25, frames=750)  # ~30s
        converted = original.return_in_other_framerate(30)
        # 1 frame at 30fps == 33.33ms
        assert abs(converted.milliseconds_exact - original.milliseconds_exact) < 1000 / 30


# ----------------------------------------------------------------------
# TestSerialization
# ----------------------------------------------------------------------
class TestSerialization:
    """items(), __iter__, __json__ — dict/JSON serialization (PR #5)."""

    def test_items_constructs_dict(self):
        tc = CTimecode(framerate=25, frames=100)
        d = dict(tc.items())
        assert "timecode" in d
        assert "framerate" in d

    def test_items_matches_iter(self):
        tc = CTimecode(framerate=25, frames=100)
        assert tc.items() == list(tc)

    def test_iter_constructs_dict(self):
        tc = CTimecode(framerate=25, frames=100)
        d = dict(tc)
        assert "timecode" in d
        assert "framerate" in d


# ----------------------------------------------------------------------
# TestPrecisionSplit (PR #6: V2 deprecation contract)
# ----------------------------------------------------------------------
class TestPrecisionSplit:
    """Anchors the V2 deprecation contract for the milliseconds split."""

    def test_milliseconds_rounded_returns_int(self):
        tc = CTimecode(framerate=25, frames=100)
        assert isinstance(tc.milliseconds_rounded, int)

    def test_milliseconds_exact_returns_float(self):
        tc = CTimecode(framerate=25, frames=100)
        assert isinstance(tc.milliseconds_exact, float)

    def test_milliseconds_rounded_equals_round_of_exact(self):
        # Defining identity: _rounded == round(_exact).
        tc = CTimecode(framerate=29.97, frames=31)
        assert tc.milliseconds_rounded == round(tc.milliseconds_exact)

    def test_milliseconds_deprecated_alias_emits_warning(self):
        tc = CTimecode(framerate=25, frames=100)
        with pytest.warns(DeprecationWarning):
            _ = tc.milliseconds

    def test_milliseconds_deprecated_alias_returns_rounded(self):
        # Semantic compatibility during deprecation.
        tc = CTimecode(framerate=25, frames=100)
        with pytest.warns(DeprecationWarning):
            assert tc.milliseconds == tc.milliseconds_rounded

    def test_milliseconds_rounded_at_integer_framerates_matches_exact_int(self, framerate):
        # At all integer-or-ms framerates in the matrix, _exact is a whole
        # float and _rounded is its int form.
        if framerate == 29.97:
            pytest.skip("non-integer framerate handled by separate test")
        tc = CTimecode(framerate=framerate, frames=100)
        assert tc.milliseconds_rounded == int(tc.milliseconds_exact)

    def test_milliseconds_rounded_vs_exact_diverges_at_2997(self):
        # At 29.97fps frame 31, _exact ≈ 1001.001 but _rounded == 1001 —
        # confirms the precision split is functioning at fractional rates.
        tc = CTimecode(framerate=29.97, frames=31)
        assert tc.milliseconds_exact == pytest.approx(30 * 1000 / 29.97, abs=1e-9)
        assert tc.milliseconds_rounded == 1001

    def test_comparators_use_rounded_not_deprecated_milliseconds(self):
        # Sonnet BLOCKER #2: comparators + __hash__ must NOT emit
        # DeprecationWarning on every call. Migrated to _rounded in PR #6.
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            a = CTimecode(framerate=25, frames=100)
            b = CTimecode(framerate=25, frames=200)
            _ = a < b
            _ = a == b
            _ = a > b
            _ = sorted([b, a])
            _ = hash(a)
            _ = {a, b}
            depwarns = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert depwarns == [], (
                f"Comparator/hash code paths must not emit DeprecationWarning "
                f"from CTimecode internals; got: {[str(x.message) for x in depwarns]}"
            )


# ----------------------------------------------------------------------
# TestRoundTrip — hypothesis property tests
# ----------------------------------------------------------------------
class TestRoundTrip:
    """Hypothesis-driven invariants."""

    def test_milliseconds_exact_precision_at_2997(self):
        # frame 31 at 29.97fps → frame_number 30 → exact ms = 30 * 1000 / 29.97
        # ≈ 1001.001001. Old .milliseconds int() truncated to 1001. New
        # .milliseconds_exact returns the precise float.
        tc = CTimecode(framerate=29.97, frames=31)
        expected = 30 * 1000 / 29.97
        assert tc.milliseconds_exact == pytest.approx(expected, abs=1e-9)

    @settings(max_examples=100)
    @given(
        frames=st.integers(min_value=1, max_value=10**6),
        fr=st.sampled_from([24, 25, 29.97, 30, "ms"]),
    )
    def test_frames_milliseconds_exact_round_trip(self, frames, fr):
        # frame_number = frames - 1; .milliseconds_exact is exact float.
        # Inverting gives frames back within rounding tolerance.
        tc = CTimecode(framerate=fr, frames=frames)
        recovered_frame_number = round(tc.milliseconds_exact * float(tc.framerate) / 1000)
        assert recovered_frame_number == frames - 1

    @settings(max_examples=50)
    @given(
        seconds=st.floats(min_value=0.001, max_value=3600, allow_nan=False, allow_infinity=False),
        fr=st.sampled_from([24, 25, 30, "ms"]),  # non-DF only
    )
    def test_seconds_canonicalization_invariant_non_df(self, seconds, fr):
        # At non-DF rates, CTimecode(start_seconds=s).milliseconds_exact ≈ s*1000
        # within one frame at the framerate's resolution.
        tc = CTimecode(framerate=fr, start_seconds=seconds)
        tolerance_ms = 1000 / float(tc.framerate)
        assert abs(tc.milliseconds_exact - seconds * 1000) <= tolerance_ms
