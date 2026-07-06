# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>
"""CTimecode — cuems wrapper around upstream `timecode` 1.5.1.

Type contract — three accessors for "milliseconds of the position":

- ``.milliseconds_exact: float``
    Mathematical answer (``frame_number * 1000 / _int_framerate``). Use for
    precision-sensitive math (offset calc, scheduler) where sub-ms accuracy
    matters at fractional framerates (29.97/23.976).

- ``.milliseconds_rounded: int``
    ``round(.milliseconds_exact)``. Use for sleep durations, integer CLI args,
    polling comparisons, dict/set keys, arithmetic with other ints.

- ``.milliseconds: int`` *(DEPRECATED — alias of .milliseconds_rounded)*
    Emits ``DeprecationWarning``. Will be removed at the first stable release.
    Migrate every call-site to one of the explicit names above.

Semantics: cuems uses *playhead* semantics — at MTC position T,
``.milliseconds_exact == T*1000``. Upstream `timecode` 1.5.1 ships
*exposure-window* semantics (a frame represents 1/FPS of elapsed exposure;
``00:00:00:00`` is the END of frame 1). The wrapper canonicalizes by routing
all `start_seconds=` construction through upstream's `tc_to_frames` (HMSF
string), which handles drop-frame correction at 29.97/59.94 DF correctly.
"""
from __future__ import annotations

import warnings

from deprecated import deprecated
from timecode import Timecode
import json_fix  # noqa: F401  -- registers __json__ JSON support


class CTimecode(Timecode):
    """SMPTE timecode with playhead semantics over upstream `timecode` 1.5.1.

    See module docstring for the .milliseconds / .milliseconds_rounded /
    .milliseconds_exact precision split contract.
    """

    def __init__(
        self,
        init_dict=None,
        start_timecode=None,
        start_seconds=None,
        frames=None,
        framerate: str | int = "ms",
    ):
        if init_dict is not None:
            super().__init__(framerate, init_dict, start_seconds, frames)
            return

        # Detect the start_seconds-only path BEFORE neutralizing 0, so we
        # know whether to apply playhead-semantics canonicalization.
        # Upstream's float_to_tc returns int(s * _int_framerate)
        # (exposure-window); tc_to_frames returns frame_number+1 and
        # applies drop-frame correction at 29.97/59.94 DF. cuems needs
        # playhead semantics — at MTC position T, .milliseconds_exact ==
        # T*1000 — and must agree with the start_timecode path at every
        # framerate including DF.
        canonicalize = (
            start_seconds is not None
            and start_seconds != 0
            and start_timecode is None
            and frames is None
        )
        original_start_seconds = start_seconds

        if canonicalize:
            # Skip upstream's start_seconds path entirely — it runs
            # `self.frames = float_to_tc(s) = int(s * _int_framerate)` which
            # raises if `int(s*ifps) == 0` (e.g., s=0.03125 at 24fps gives
            # int(0.75)=0, hitting the frames>0 setter guard). We're going to
            # overwrite frames ourselves anyway, so initialize to default
            # ('00:00:00:00' → frames=1) just to set up framerate machinery.
            super().__init__(framerate)
        else:
            # Upstream raises ValueError on start_seconds=0; let the default
            # '00:00:00:00' path handle it (frames=1 == playhead at t=0).
            if start_seconds == 0:
                start_seconds = None
                frames = None
            super().__init__(framerate, start_timecode, start_seconds, frames)

        if canonicalize:
            # Convert seconds to HMSF and delegate to tc_to_frames — correct
            # at DF, non-DF, and ms framerates uniformly. Verified empirically
            # that `round(s * _int_framerate) + 1` is wrong at 29.97 DF
            # (gives 1801 at 1min vs upstream's 1799; off by 18 frames at
            # 10min). The HMSF route inherits upstream's drop-frame logic.
            total_frames = round(original_start_seconds * self._int_framerate)
            ifps = self._int_framerate
            h, rem = divmod(total_frames, ifps * 3600)
            m, rem = divmod(rem, ifps * 60)
            s, f = divmod(rem, ifps)
            # tc_to_frames inserts the drop-frame `;` separator itself when
            # self.drop_frame is True (upstream timecode.py line 277-278), so
            # always pass `:` here.
            tc_str = f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"
            self.frames = self.tc_to_frames(tc_str)

    @classmethod
    def from_dict(cls, init_dict):
        return cls(init_dict=init_dict)

    # ------------------------------------------------------------------
    # framerate getter override (Option D)
    # ------------------------------------------------------------------
    @property
    def framerate(self):
        """Canonical framerate: int for SMPTE, float for fractional, int 1000 for ms.

        Upstream stores integer SMPTE framerates as strings (``'25'``, ``'30'``)
        but ``'ms'``/``'1000'`` as int 1000 — making ``tc.framerate == 25``
        silently False. This getter normalizes the return type so callers can
        compare against numeric literals reliably.
        """
        fr = self._framerate
        if isinstance(fr, str):
            try:
                return int(fr)
            except ValueError:
                return float(fr)
        return fr

    @framerate.setter
    def framerate(self, value):
        # Delegate to upstream's setter for all the framerate normalization
        # (NTSC detection, ms_frame flag, _int_framerate computation, drop_frame).
        Timecode.framerate.fset(self, value)

    # ------------------------------------------------------------------
    # milliseconds — precision split (V2 deprecation cycle)
    # ------------------------------------------------------------------
    @property
    def milliseconds_exact(self) -> float:
        """Time as exact-precision milliseconds (float).

        The mathematical answer: ``frame_number * 1000 / _int_framerate``.
        At integer framerates (24, 25, 30, ms) this is always a whole number
        as a float (e.g., 25fps frame 31 → 1200.0). At fractional framerates
        (29.97, 23.976) the float carries the true sub-ms value (29.97fps
        frame 31 → 1001.001001...) — this is the precision the old
        int-truncating ``.milliseconds`` was throwing away.

        **Use for:**

        - precision-sensitive math (BaseEngine.go_offset calc, scheduler
          drift compensation, MTC bias measurement)
        - any place where adding/subtracting milliseconds across many frames
          at fractional framerates would accumulate truncation drift
        - comparison against expected exact values in tests
          (``pytest.approx(expected, abs=1e-9)``)

        **Do NOT use for:**

        - sleep durations (``time.sleep`` accepts float but ``_rounded``
          better signals integer-ms intent)
        - CLI args expecting integer ms
        - dict/set keys (float equality is fragile)
        - arithmetic with other ints (float contamination)

        Resolves the ``# TODO: float math for other framerates`` from the
        pre-869cyndtv code.

        Note on framerate divisor: uses ``float(self.framerate)`` (the actual
        SMPTE rate, e.g., 29.97) rather than ``_int_framerate`` (the rounded
        label rate, 30 for 29.97). For NTSC fractional rates this is the
        difference between getting real-time ms (1001.001 at frame 31) vs
        label-rate ms (1000.0). cuems consumers want real-time semantics.
        """
        return self.frame_number * 1000 / float(self.framerate)

    @property
    def milliseconds_rounded(self) -> int:
        """Time as milliseconds, rounded to the nearest int (banker's rounding).

        Equivalent to ``round(self.milliseconds_exact)``. Rounding (not
        int-truncation) halves the per-call max error at fractional
        framerates from ~1ms to ~0.5ms, and over long sums averages to
        zero drift instead of monotonic loss.

        **Use for:**

        - sleep durations passed to ``time.sleep()``
        - CLI args expecting integer ms (e.g., ``audiowaveform -e``)
        - polling comparisons (``while mtc.main_tc.milliseconds_rounded < target_ms``)
        - dict/set keys
        - arithmetic with other ints (no float contamination)

        **Migration note:** This is the spiritual successor of the old
        ``.milliseconds``, but with ``round()`` instead of ``int()``
        truncation. At integer framerates, behavior is identical to the old
        ``.milliseconds``. At fractional framerates, values may differ by
        ±1 from the old truncation — review every call-site that compared
        against an exact expected ms value at 29.97/23.976.
        """
        return round(self.milliseconds_exact)

    @property
    @deprecated(
        reason=(
            "Renamed to .milliseconds_rounded (int, rounded) — or use "
            ".milliseconds_exact (float, precise) for precision-sensitive code. "
            "The old .milliseconds will be removed at the first stable release."
        ),
        version="0.1.0rc6",
    )
    def milliseconds(self) -> int:
        """DEPRECATED — alias of .milliseconds_rounded.

        The original ``.milliseconds`` returned ``int(...)`` (truncation).
        The new ``.milliseconds_rounded`` returns ``round(...)`` (nearest
        int) — at integer framerates the values are identical; at
        fractional framerates they may differ by ±1ms. Migrate every
        call-site to the explicit name to clarify rounding intent and
        silence this warning.

        Will be removed in the first stable release after 0.1.0rc6.
        """
        return self.milliseconds_rounded

    # ------------------------------------------------------------------
    # frame-domain conversions
    # ------------------------------------------------------------------
    def return_in_other_framerate(self, framerate):
        """Return a copy of this CTimecode at a different framerate.

        Frame-domain conversion via frame_number (0-indexed elapsed-frames
        count) avoids the lossy time-domain round-trip the previous
        implementation used (which constructed the new instance via
        ``start_seconds=self.milliseconds/1000``, losing one frame to
        upstream's int(s*fr) → frame_number+1 round-trip).

        NOTE — throwaway object cost (deferred 869cyndtv PR #6, 2026-04-27):
            The ``CTimecode(framerate=framerate)`` construction below is
            used only to read ``_int_framerate`` from the resulting object.
            It runs upstream's framerate setter (correct, what we want) but
            ALSO calls ``tc_to_frames("00:00:00:00")`` to populate
            ``_frames=1`` (pure waste). Cost is ~5μs per call. Call-sites
            (run_cue.py:62/252, helpers.py:28/31, loop_cue.py:74/183) are
            all construction-time, not hot-loop — total project-load impact
            ~2ms for 100 cues. Deferred because the cost is unmeasurable in
            production.

            If profiling ever flags this, the recommended fix is a
            class-level memoization cache keyed on the framerate input
            (Option D in the 869cyndtv PR #6 plan)::

                _INT_FR_CACHE: dict = {}

                @classmethod
                def _int_framerate_for(cls, fr):
                    key = (type(fr), fr) if isinstance(fr, (int, float, str)) else repr(fr)
                    if key not in cls._INT_FR_CACHE:
                        cls._INT_FR_CACHE[key] = CTimecode(framerate=fr)._int_framerate
                    return cls._INT_FR_CACHE[key]

            Then replace the ``target_int_fr = ...`` line below with
            ``target_int_fr = self._int_framerate_for(framerate)``.

            Why a cache (Option D) over inlining upstream's NTSC-detection
            logic (Option F): inlining duplicates upstream's algorithm and
            silently diverges if upstream changes tolerance or adds new
            NTSC-like rates. The cache delegates to upstream on the first
            lookup per unique framerate and pays zero on subsequent calls.

            Revisit triggers: (1) profiling shows this method on a hot path,
            (2) a feature introduces dynamic framerate changes during
            playback, (3) the same cache pattern is needed elsewhere in
            CTimecode (unify at that point).
        """
        target_int_fr = CTimecode(framerate=framerate)._int_framerate
        new_frame_number = round(self.frame_number * target_int_fr / self._int_framerate)
        return CTimecode(framerate=framerate, frames=new_frame_number + 1)

    # ------------------------------------------------------------------
    # hashing + comparison (use _rounded directly to avoid DeprecationWarning storm)
    # ------------------------------------------------------------------
    def __hash__(self):
        # Use _rounded explicitly: the deprecated .milliseconds emits a
        # DeprecationWarning on every access, which would flood every
        # dict/set/sorted/min/max usage. Hash compatibility with __eq__ is
        # preserved (both sides use _rounded).
        return hash((self.milliseconds_rounded,))

    def __eq__(self, other):
        if isinstance(other, CTimecode):
            return self.milliseconds_rounded == other.milliseconds_rounded
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, CTimecode):
            return self.milliseconds_rounded != other.milliseconds_rounded
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, CTimecode):
            return self.milliseconds_rounded < other.milliseconds_rounded
        elif isinstance(other, int):
            return self.milliseconds_rounded < other
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, CTimecode):
            return self.milliseconds_rounded <= other.milliseconds_rounded
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, CTimecode):
            return self.milliseconds_rounded > other.milliseconds_rounded
        elif isinstance(other, int):
            return self.milliseconds_rounded > other
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, CTimecode):
            return self.milliseconds_rounded >= other.milliseconds_rounded
        return NotImplemented

    # ------------------------------------------------------------------
    # arithmetic dunders — playhead-correct + same-framerate assertion
    # ------------------------------------------------------------------
    def __add__(self, other):
        """Return a new CTimecode with `other` added.

        For CTimecode operands, both operands' `frames` are 1-indexed counts;
        naively summing them double-applies the +1 offset. Subtract 1 to get
        the playhead-correct sum.
        """
        if isinstance(other, CTimecode):
            if other._int_framerate != self._int_framerate:
                raise CTimecodeError(
                    f"Arithmetic between CTimecodes of different framerates "
                    f"({self.framerate} vs {other.framerate}); use "
                    f".return_in_other_framerate() first."
                )
            result_frames = self.frames + other.frames - 1
        elif isinstance(other, int):
            # int operand: caller passes a frame count to add (e.g.,
            # MtcListener.py does `self.main_tc + 1` to advance one MTC
            # frame). No 1-indexing adjustment needed.
            result_frames = self.frames + other
        else:
            raise CTimecodeError(
                f"Type {other.__class__.__name__} not supported for arithmetic."
            )
        return CTimecode(framerate=self.framerate, frames=result_frames)

    def __sub__(self, other):
        """Return a new CTimecode with `other` subtracted.

        Symmetric to __add__: subtracting two 1-indexed frame counts yields
        a 0-indexed delta, so add +1 to land back in the 1-indexed
        convention. Subtracting a larger duration from a smaller position
        produces frames<=0, which upstream's frames setter rejects with
        ValueError — that's the intended contract (no silent wrap).
        """
        if isinstance(other, CTimecode):
            if other._int_framerate != self._int_framerate:
                raise CTimecodeError(
                    f"Arithmetic between CTimecodes of different framerates "
                    f"({self.framerate} vs {other.framerate}); use "
                    f".return_in_other_framerate() first."
                )
            result_frames = self.frames - other.frames + 1
        elif isinstance(other, int):
            result_frames = self.frames - other
        else:
            raise CTimecodeError(
                f"Type {other.__class__.__name__} not supported for arithmetic."
            )
        return CTimecode(framerate=self.framerate, frames=result_frames)

    def __mul__(self, other):
        """Return a new CTimecode with frames multiplied by `other`."""
        if isinstance(other, CTimecode):
            if other._int_framerate != self._int_framerate:
                raise CTimecodeError(
                    f"Arithmetic between CTimecodes of different framerates "
                    f"({self.framerate} vs {other.framerate}); use "
                    f".return_in_other_framerate() first."
                )
            multiplied_frames = self.frames * other.frames
        elif isinstance(other, int):
            multiplied_frames = self.frames * other
        else:
            raise CTimecodeError(
                f"Type {other.__class__.__name__} not supported for arithmetic."
            )
        return CTimecode(framerate=self.framerate, frames=multiplied_frames)

    def __truediv__(self, other):
        """Return a new CTimecode with frames divided by `other`.

        Rounds the float result to int (upstream's frames setter requires
        positive int). Rejects zero/negative divisors explicitly to avoid
        silent ``max(1, negative)`` clamp paths.
        """
        if isinstance(other, CTimecode):
            if other._int_framerate != self._int_framerate:
                raise CTimecodeError(
                    f"Arithmetic between CTimecodes of different framerates "
                    f"({self.framerate} vs {other.framerate}); use "
                    f".return_in_other_framerate() first."
                )
            if other.frames == 0:  # defense-in-depth; upstream ensures frames>=1
                raise CTimecodeError("Division by CTimecode with zero frames")
            div_frames = round(self.frames / other.frames)
        elif isinstance(other, int):
            if other <= 0:
                raise CTimecodeError(
                    f"Division by non-positive int ({other}); CTimecode "
                    f"division requires a positive divisor (frames must "
                    f"stay >= 1)."
                )
            div_frames = round(self.frames / other)
        else:
            raise CTimecodeError(
                f"Type {other.__class__.__name__} not supported for arithmetic."
            )
        # round() can yield 0 only when self.frames is small and divisor is
        # large; clamp to 1 (upstream frames setter requires > 0). Negative
        # results are ruled out by the int>0 / frames>0 guards above.
        return CTimecode(framerate=self.framerate, frames=max(1, div_frames))

    # ------------------------------------------------------------------
    # serialization
    # ------------------------------------------------------------------
    def __json__(self):
        return {"CTimecode": self.__str__()}

    def __str__(self):
        # skip_rollover=True keeps __str__ monotonic past 24h. Without this,
        # frames=2_160_002 at 25fps would render as "00:00:00:01" (wrapped)
        # instead of "24:00:00:01" — bug 869cpdbzy reported by Sergio: long-
        # running install (>24h MTC) with audio/sequence stops while video
        # keeps looping. Note the underlying .frames, .milliseconds_exact, and
        # .milliseconds_rounded accessors are already monotonic post-PR-#6;
        # this fix is for the string display + log readability + any consumer
        # that round-trips through str. (869cyndtv PR #10)
        return self.tc_to_string(*self.frames_to_tc(self.frames, skip_rollover=True))

    def __iter__(self):
        yield ("timecode", self.__str__())
        yield ("framerate", self.framerate)

    def items(self):
        return list(self)


class CTimecodeError(Exception):
    """Raised when an error occurred in timecode calculation."""
    pass
