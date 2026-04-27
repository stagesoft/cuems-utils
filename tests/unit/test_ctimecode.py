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
- TestRoundTrip: hypothesis-driven property tests (e.g.,
  CTimecode(frames=N).milliseconds → invertible across the framerate matrix).

The `'ms'` framerate is CTimecode's default (line 6 of CTimecode.py) and is heavily
used by `format_timecode` callers throughout cuems-utils — it must be a first-class
case in every test class.
"""

from __future__ import annotations

import pytest

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


class TestArithmetic:
    """Arithmetic dunders. PRs #2 and #6 expand this with the off-by-one captures."""

    def test_add_int_returns_ctimecode(self):
        tc = CTimecode(framerate=25, frames=100)
        result = tc + 1
        assert isinstance(result, CTimecode)


class TestComparison:
    """Comparison dunders. PR #4 adds None-handling cases here."""

    def test_eq_same_value(self):
        a = CTimecode(framerate=25, frames=100)
        b = CTimecode(framerate=25, frames=100)
        assert a == b


class TestConversion:
    """return_in_other_framerate. PR #6 adds round-trip stability tests."""


class TestRoundTrip:
    """Hypothesis-driven invariants. PR #6 populates these."""
