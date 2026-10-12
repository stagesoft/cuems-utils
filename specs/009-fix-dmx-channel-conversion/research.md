# Phase 0 Research: DMX channel conversion error

No `NEEDS CLARIFICATION` markers remain in the spec — the XSD reachability question was resolved
during `/speckit.specify` (see spec.md's "XSD investigation, resolved" section) and is not
reopened here. This phase resolves the remaining implementation-shape decisions the spec
deliberately left to planning (it names *what* must happen, not the exact class shape).

## Decision 1: Where the new error type lives and what it subclasses

**Decision**: Add `DmxChannelDecodeError` to `src/cuemsutils/errors.py`, as a direct subclass of
`CuemsError`, added to `errors.py`'s `__all__`.

**Rationale**: FR-006 is explicit: "The new error type MUST be added to `cuemsutils.errors` as a
public, catchable symbol, consistent with this library's existing convention." `errors.py`'s own
module docstring states the contract this codebase already committed to: "An exception the caller
cannot name is one it cannot catch." Placing it under `CuemsError` (rather than bare `Exception`
or `RuntimeError`) means a consumer catching `CuemsError` broadly — the pattern this library's own
docstring recommends — catches this too, without needing to know DMX-specific exception names.

**Alternatives considered**:
- *Mirror `DmxSceneWriteError` exactly* (a bare `RuntimeError` subclass, defined locally in
  `xml/mapper.py`, not part of the `CuemsError` hierarchy). Rejected: that precedent predates
  `errors.py`'s consolidation (feature 006) and was never migrated into it; the defect record cites
  it as "the same shape of defect," not as "the exact class hierarchy to copy." FR-006's explicit
  instruction (write this into `cuemsutils.errors`) takes precedence over an older, inconsistent
  precedent. Subclassing `CuemsError` is *more* consistent with the codebase's current, stated
  convention, not less.
- *Subclass `ValidationError`*. Rejected: `ValidationError`'s docstring ties it specifically to
  document/schema validation outcomes (T1/T2, `violation` attribute shape) — this failure has
  nothing to do with schema validation (confirmed: it is unreachable from schema-valid XML at
  all). Conflating the two would make a consumer's `except ValidationError` catch something that
  never came from a validated document, which is exactly the kind of ambiguity `errors.py`'s
  docstring (`IngestError`'s rationale: "deliberately not a `ValidationError`... nothing was
  validated") already warns against for a structurally analogous case.

## Decision 2: Constructor signature and message shape

**Decision**: `DmxChannelDecodeError(universe, index, entry)` — carries the failing universe (for
`universe_num`, when gettable), the zero-based index of the failing entry within the input list,
and the raw entry value (for internal inspection only, never rendered into the message). Message:
`f"DMX channel entry at index {index} in universe {universe_num!r} could not be converted to a DmxChannel (entry: {type(entry).__name__})."`
— names the universe, the index, and the failing entry's *type* only, never its `repr()`.

**Rationale**: Directly mirrors `DmxSceneWriteError.__init__(self, scene, index, cue)`
(`xml/mapper.py:922-944`) — same three-argument shape (container, index, failing-item), same
"identifiers only, never object repr" rule (FR-002, echoing `DmxSceneWriteError`'s FR-033
precedent: "show content does not belong in an error string any more than in a log record").
Naming the entry's *type* (not its value) gives a debugger enough to know "this was an `int`, not
a `dict`" without risking a repr of arbitrary — potentially large or sensitive — show content
leaking into a log line.

**Alternatives considered**:
- *Original exception as the only detail (`raise ... from original`), no custom message
  beyond `str(original)`.* Rejected: `KeyError`'s and `TypeError`'s default messages
  (`"'DmxChannel'"` and `"'int' object is not subscriptable"` respectively) say nothing about
  *which* universe or *which* index — exactly the actionability gap `DmxSceneWriteError`'s own
  docstring calls out ("A bare `RuntimeError` from somewhere inside a 24 KB document is not
  actionable"). The original exception is still preserved via `raise ... from exc` (Python's
  standard chaining, matching `DmxSceneWriteError`'s own `from exc` pattern at `mapper.py:638`),
  satisfying "diagnosable" without making it the *only* information carried.
- *Carry the whole `channels` list rather than the caller identifying the one bad entry.*
  Rejected: FR-002 requires identifying "the failing entry," singular — pointing at the batch
  rather than the entry reproduces the current defect's actionability problem at one remove.

## Decision 3 (revised during `/speckit.analyze` remediation): unified new-object → append →
raise-if-error loop, replacing the two-branch original

**Decision**: Replace the original two-branch loop (one branch for already-`DmxChannel` instances,
one for raw dicts needing conversion, each independently reassigning `dmx_channels`) with a single
unified loop:

```text
channel_list = []
for index, entry in enumerate(channels):
    if entry is None:
        continue
    if isinstance(entry, DmxChannel):
        channel_list.append(entry)
        continue
    try:
        converted = DmxChannel(entry['DmxChannel'])
    except (KeyError, TypeError) as exc:
        raise DmxChannelDecodeError(universe=self, index=index, entry=entry) from exc
    channel_list.append(converted)
if channel_list:
    super().__setitem__('dmx_channels', channel_list)
```

Every entry is resolved to a proper `DmxChannel` object — already-converted instances are appended
as-is (identity preserved), raw dicts are converted and the new instance appended — before
anything is placed in the result. `dmx_channels` is assigned once, after the full pass succeeds,
**and only if at least one entry survived** (see the empirical correction below — an empty or
all-`None` input must leave the key untouched, not set it to `[]`). Any single failure still
aborts the whole call immediately (FR-003): the first bad entry raises, not after finishing the
batch and reporting every bad entry found.

**Empirical correction, found during implementation (not by reading the code)**: the first draft
of this decision assigned `channel_list` unconditionally at the end. Running the *original* code
against an empty list and an all-`None` list revealed that `dmx_channels` is **never actually set**
in either case — the original loop's `super().__setitem__` call lives inside its `if r is not
None:` branch, so it runs zero times for both inputs, leaving the key exactly as it was before the
call (its declared default, `None`, on a freshly constructed `DmxUniverse`). An unconditional
assignment at the end of the unified loop would have turned this into "always sets `[]`" — a real,
untested observable behavior change, and one this feature's own FR-004 explicitly forbids. The
`if channel_list:` guard reproduces the original rule exactly, because every non-`None` entry
either appends or raises, so "channel_list is non-empty" and "at least one non-`None` entry
existed and converted" are the same condition. This also means spec.md's original Edge Cases text
("an empty list stores an empty list") was wrong and has been corrected there.

**Rationale**: The original two-branch design (research.md's first draft of this decision) kept
each branch's existing per-iteration `super().__setitem__` call to minimize the diff, but this
produces an unstated contradiction for a batch mixing already-`DmxChannel` instances with
still-raw-but-valid dict entries: the two branches' independent reassignments race, and whichever
branch's iteration runs last silently wins, dropping the other kind of entry from the batch
(discovered during `/speckit.analyze`, finding I1). A single unified loop that always appends to
one list and assigns once removes the race by construction — there is no second reassignment path
left to contradict the first. This also matches the user's explicit direction on remediation ("new
object → append to parent → raise if error") and features 005-008's standing direction that decoded
content is superseded by proper model objects rather than left as raw dicts (FR-004a): raw dicts
never survive into `dmx_channels` even transiently, in any branch.

Raising on the *first* failure (rather than collecting all failures and raising once at the end)
still matches `_emit_dmx_scene`'s precedent (`mapper.py:634-638`), which also raises on the first
scene that fails to serialize rather than collecting every failing scene in the cue first. FR-003
is explicit that the whole call must fail on one bad entry — the fix is proposal 1 (raise), not
proposal 2 (per-entry recovery/collection), which the spec's Assumptions section explicitly
excludes; nothing about unifying the loop changes that.

**Alternatives considered**:
- *Keep the two-branch design, just wrap the conversion branch's per-iteration `try` more
  narrowly* (this decision's original text). Rejected: this is exactly what produced finding I1 —
  it doesn't resolve the mixed-batch race, it just narrows where the still-contradictory
  reassignment happens.
- *Collect every bad entry's index before raising, listing all of them in one error.* Rejected as
  over-scoped: not requested by any FR, adds complexity (a second pass or an accumulator) for a
  benefit the spec never asks for, and diverges from the `DmxSceneWriteError` precedent this
  feature is explicitly modeled on.

**Incidental performance effect**: this design also removes the redundant per-iteration
`super().__setitem__('dmx_channels', ...)` calls the original code made once per entry (up to 512
times for a full universe) — measured as the dominant cost in the pre-fix baseline (see Decision 6
below). This is a natural side effect of the correctness fix (FR-003 already required "assign
`dmx_channels` only once, after success"), not separate scope added for performance's sake.

## Decision 6: Performance budget, measured rather than assumed

**Decision**: SC-PERF-001 sets **≤ 3 ms/call for a realistic universe (≤ 32 channels)**, and **"no
regression versus the measured 37.07 ms/call pre-fix baseline"** for the DMX-spec maximum (512
channels) — two separate bars, not one number stretched to cover both scales.

**Rationale**: Constitution Principle IV requires a measurable performance target unconditionally,
with no "N/A" carve-out in the ratified text (flagged as CRITICAL finding C1 in `/speckit.analyze`).
Measured via `hatch run test:python` (Python 3.11.9, this project's pinned test runtime) against
the **current, pre-fix** code:

| Batch size | Calls | Total | Per-call |
|---|---|---|---|
| 8 entries (realistic) | 5000 | 3565.04 ms | **0.7130 ms** |
| 512 entries (DMX maximum) | 2000 | 74142.97 ms | **37.0715 ms** |

The 8-entry realistic case is already 4× under a 3 ms budget, so 3 ms is a real, meaningful
non-regression bar rather than a number picked to trivially pass. The 512-entry case is
**dominated by the per-iteration reassignment removed in Decision 3** — a single number covering
both scales would either be too loose for the common case (masking a real regression there) or
force an unverified promise about the worst case before the fixed code exists to measure. Stating
both separately, with the 512-entry bar pinned to the actual measured baseline rather than a guess,
keeps the budget honest at both scales.

**Alternatives considered**:
- *One number for all batch sizes (e.g., "≤ 3 ms always")*. Rejected: false today for the
  512-channel maximum (measured 37.07 ms pre-fix) and asserting the fix will get there is a claim
  research.md cannot make before the implementation exists to measure — Phase 4's polish task
  measures the actual fixed code and the budget is revisited then if the unified loop does not, in
  fact, bring the worst case under a tighter number.
- *"N/A with rationale" (original plan.md text)*. Rejected per finding C1 — the constitution's
  Principle IV text contains no such carve-out.

**Post-implementation measurement (T008), and a correction**: the finished implementation measures
0.727-0.736 ms/call for the 8-entry case (two runs) and 37.60-37.80 ms/call for the 512-entry case
(two runs) — both within the stated budget, the 8-entry case with the same comfortable margin as
pre-fix. The paragraph above predicted the 512-entry case would improve because it assumed the
redundant per-iteration `dmx_channels` reassignment was the dominant cost there. **That assumption
was wrong, and measurement is what caught it**: the ~1-2% difference between pre- and post-fix
512-entry timings is within this benchmark's own run-to-run noise (the 8-entry case shows the same
spread between its two runs), meaning the reassignment was never the dominant cost. The true
dominant cost is the 512 individual `DmxChannel(...)` constructions themselves — each one runs
through `ensure_items`, `self.setter(...)`, and two property setters with `Logger` calls — and this
fix's loop restructuring does not touch that at all; it only changes *what happens on failure* and
*how many times the cheap list-reassignment runs on success*, and the latter was never expensive
relative to object construction. The budget stands as "no regression", met — not "improved", which
is what the pre-measurement paragraph above claimed to expect.

## Decision 4: What counts as "cannot be converted" — exception scope

**Decision**: Catch `(KeyError, TypeError)` specifically at the `r['DmxChannel']` /
`DmxChannel(r['DmxChannel'])` call, matching exactly the two failure modes the characterization
tests already pin (`test_a_malformed_dict_entry_falls_back_to_storing_the_raw_input` — `KeyError`;
`test_a_non_subscriptable_entry_falls_back_to_storing_the_raw_input` — `TypeError`). Do not use a
bare `except Exception`.

**Rationale**: FR-005 requires both failure kinds to produce the *same* named error — an unqualified
`except Exception` would also achieve that, but reintroduces exactly the ambient-catch defect shape
the defect record traces back to feature 004/005's precedent (`_emit_dmx_scene`'s own docstring:
"An ambient `except Exception` in the general emit path would catch unrelated failures... which is
the defect being removed, widened rather than fixed"). Scoping to the two concrete exception types
actually producible at this call site keeps the fix narrow and auditable, and avoids masking a
genuinely unexpected bug (e.g. a `RecursionError` or a bug inside `DmxChannel.__init__` unrelated
to input shape) behind the same generic message.

**Alternatives considered**:
- *Bare `except Exception`, same as today.* Rejected per rationale above — narrows the blast radius
  of what this feature's `except` clause hides, consistent with the constitution's "Code Quality By
  Default" principle (readable, small in scope) and this repo's own stated precedent for removing
  ambient catches (005/`_emit_dmx_scene`).

## Decision 5: Test strategy

**Decision**: (a) Rewrite `tests/unit/test_dmx_universe_channels.py`'s three
"exception-swallow fallback" tests to assert the raise instead (same three scenarios: malformed
dict, non-subscriptable entry, one-bad-entry-in-a-good-batch), keeping the five "well-formed path"
tests unmodified as the regression guard. (b) Add
`tests/contract/test_dmx_channel_decode_failure_path.py`, mirroring
`tests/contract/test_dmx_failure_path.py`'s structure: raises, identifies the universe, identifies
the failing index, preserves `__cause__`, carries no object repr in the message, plus a healthy-path
control case.

**Rationale**: Matches the constitution's "Tests As A Release Gate" (fail-before-pass) and this
repo's own established pattern of a unit-level characterization file plus a contract-level
behavior-change file for exactly this shape of fix (005's `test_dmx_failure_path.py` is the direct
precedent, cited by name in the defect record itself).

**Alternatives considered**: *Only update the unit test file.* Rejected — the defect record
explicitly draws the parallel to feature 005's contract test, and a contract test is the layer this
codebase uses to pin "the write/read boundary now raises," making the behavior change discoverable
independent of the unit-level characterization file's internals.
