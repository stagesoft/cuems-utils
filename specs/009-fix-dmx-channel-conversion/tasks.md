# Tasks: Stop `DmxUniverse` from silently corrupting DMX channel data on construction

**Input**: Design documents from `/specs/009-fix-dmx-channel-conversion/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/dmx-channel-decode-error.md](./contracts/dmx-channel-decode-error.md),
[quickstart.md](./quickstart.md)

**Tests**: Required by the project constitution ("Tests As A Release Gate" — fail-before-pass).
Included for the single user story below.

**Organization**: This feature has exactly one user story (P1 — the defect has one shape and one
fix, per spec.md). There is no US2/US3 to keep independent from it; "independently testable" here
means the story is testable on its own, not that it must coexist with sibling stories.

**Revision note**: this version resolves two issues `/speckit.analyze` found in the prior draft:
(1) T005's instructions were self-contradictory for a batch mixing already-`DmxChannel` instances
with still-raw entries (finding I1) — replaced with a single unified loop (research.md Decision 3,
revised); (2) the performance budget was "N/A", violating the constitution's unconditional MUST for
a measurable target (finding C1) — replaced with SC-PERF-001, measured against real pre-fix
baselines (research.md Decision 6). Task T008 (performance verification) is new; T003/T004 gained
coverage for the mixed-batch case (finding E2) and the `CuemsScript.from_json` path (finding E1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 for every task in Phase 3; Setup/Foundational/Polish tasks carry no story label
- Every implementation/test task names its exact file path

## Path Conventions

Single project (existing `cuems-utils` library layout): `src/cuemsutils/`, `tests/{unit,contract}/`.

---

## Phase 1: Setup

**Purpose**: Establish the pre-change baseline this feature must not regress.

- [X] T001 Run `hatch test --show` from the repo root and confirm the full suite is green
      (baseline, no changes yet). Note the pass/skip/xfail counts so Phase 4's regression check
      (T011) has something concrete to compare against, per FR-008/SC-003. (The performance
      baseline is already measured and recorded in research.md Decision 6 / plan.md's Technical
      Context — 0.7130 ms/call for an 8-entry batch, 37.0715 ms/call for a 512-entry batch, Python
      3.11.9 — no need to re-measure here; T008 re-measures against the *fixed* code later.)
      **Baseline confirmed 2026-09-03: 2562 passed, 96 skipped, 2 xfailed in 53.41s** (`hatch test`,
      hatch-test env, Python 3.11).

**Checkpoint**: Baseline confirmed green. Safe to start Foundational work.

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: The new public exception type must exist before the fix in Phase 3 can import and
raise it.

**⚠️ CRITICAL**: T002 must be complete before T005 (the fix) can be written.

- [X] T002 Add `DmxChannelDecodeError` to `src/cuemsutils/errors.py`: a direct subclass of
      `CuemsError`, constructor `__init__(self, universe, index: int, entry: object)` storing
      `self.universe`, `self.index`, `self.entry`, building the message
      `f"DMX channel entry at index {index} in universe {universe_num!r} could not be converted to a DmxChannel (entry: {type(entry).__name__})."`
      where `universe_num` is read defensively (mirror `DmxSceneWriteError.__init__`'s
      `scene.get("id")` guard at `src/cuemsutils/xml/mapper.py:927-932` — wrap only the attribute
      read in `try`/`except Exception`, falling back to a placeholder such as
      `"<universe_num unknown>"` on failure, never letting the read raise). The message names the
      entry's **type**, never its value or a `repr()` (FR-002 — settled, no longer "and/or"). Add
      `"DmxChannelDecodeError"` to the module's `__all__` list. Follow the existing docstring
      pattern in this file (cite the FR it satisfies, one short paragraph, no more; also cite
      FR-UX-001 for the "matches `DmxSceneWriteError`'s conventions" rule). See research.md
      Decisions 1–2 and data-model.md's `DmxChannelDecodeError` table and Invariants for the exact
      contract.

**Checkpoint**: `from cuemsutils.errors import DmxChannelDecodeError` works and is catchable as
`CuemsError`. User Story 1 implementation can now begin.

---

## Phase 3: User Story 1 - A corrupt DMX universe fails to construct, loudly and precisely (Priority: P1) 🎯 MVP

**Goal**: `DmxUniverse.set_dmx_channels` raises `DmxChannelDecodeError` (naming the universe and
the failing entry) instead of silently storing raw, unconverted channel data, while leaving every
input that converts cleanly today completely unaffected — including a *mixed* batch of
already-converted and still-raw entries, which today's code silently corrupts (FR-004a).

**Independent Test**: Construct a `DmxUniverse` and assign `dmx_channels` to a list containing one
malformed entry among otherwise well-formed ones; confirm `DmxChannelDecodeError` is raised naming
the universe and the failing index, and that a batch of only well-formed entries (including a
mixed batch of already-`DmxChannel` instances and raw dicts) still converts correctly. See
quickstart.md for the exact snippets.

### Tests for User Story 1 (write first, confirm they FAIL against the still-unfixed code)

- [X] T003 [P] [US1] In `tests/unit/test_dmx_universe_channels.py`:
      - Rewrite the three "exception-swallow fallback" tests to assert the new behavior instead of
        pinning the old one:
        - `test_a_malformed_dict_entry_falls_back_to_storing_the_raw_input` → assert
          `pytest.raises(DmxChannelDecodeError)` when setting
          `dmx_channels = [{"not_dmxchannel_key": 1}]`, and that `u.dmx_channels` is still `None`
          (unset) afterward, not the raw list.
        - `test_a_non_subscriptable_entry_falls_back_to_storing_the_raw_input` → same assertion
          for `dmx_channels = [5]`.
        - `test_one_bad_entry_discards_conversion_of_every_good_entry_in_the_batch` → same
          assertion for the three-entry batch (`good, bad, good`); additionally assert the raised
          error's `.index == 1` (the bad entry's position).
      - **Add a new test** (FR-004a, closing analysis finding E2):
        `test_a_batch_mixing_already_converted_and_raw_entries_converts_both`: set
        `dmx_channels` to `[DmxChannel({"channel": 1, "value": 10}), {"DmxChannel": {"channel": 2, "value": 20}}]`
        (an already-converted instance followed by a still-raw-but-valid dict, no malformed
        entry). Assert the result has **both** entries as `DmxChannel` objects, in order, with the
        first being the *same object* (`is`) as the input instance — this is the case today's
        two-branch code drops one side of, order-dependently.
      - Leave the five original "well-formed path" tests (`test_default_dmx_channels_is_none`,
        `test_wrapped_dict_entries_convert_to_dmxchannel_instances`,
        `test_a_single_dmxchannel_instance_is_wrapped_into_a_list_unconverted`,
        `test_a_list_of_dmxchannel_instances_passes_through_unconverted`,
        `test_none_entries_are_skipped_without_disturbing_valid_ones`) completely unmodified —
        they are the FR-004/FR-008 regression guard.
      - Update the file's module docstring to describe the new behavior (it currently says the
        tests characterize a swallow that "is not correct" but is being kept; update it to say the
        swallow has been replaced by a raise, and the mixed-batch case is now well-defined,
        referencing this feature). Import `DmxChannelDecodeError` and `DmxChannel` from
        `cuemsutils.errors`/`cuemsutils.cues.DmxCue` as needed.

- [X] T004 [P] [US1] Create `tests/contract/test_dmx_channel_decode_failure_path.py`, mirroring
      `tests/contract/test_dmx_failure_path.py`'s structure and module-docstring style (explain
      what changed and why, citing this feature and the precedent it mirrors). Cover:
      - a malformed entry raises `DmxChannelDecodeError` (the change);
      - the error identifies the universe by `universe_num` (assert the number appears in
        `str(exc)`);
      - the error identifies the failing entry's index and type name (assert both appear in
        `str(exc)`, matching FR-002's settled wording — not the entry's value);
      - `exc.__cause__` is the original `KeyError` or `TypeError` (test both, mirroring
        `test_the_original_failure_is_preserved_as_the_cause`);
      - the message carries no object repr of the failing entry or the universe's channel data
        (mirroring `test_the_error_carries_no_object_repr` — FR-002);
      - a control case: a `DmxUniverse` populated entirely with well-formed entries still converts
        every entry to a `DmxChannel` and raises nothing (mirroring `test_a_healthy_scene_still_emits`);
      - **a second control case** (closing analysis finding E2 at the contract level): a mixed
        batch of an already-`DmxChannel` instance and a still-raw dict converts both, per FR-004a;
      - **a `CuemsScript.from_json` case** (closing analysis finding E1, FR-007): build a minimal
        JSON-decodable payload for a script whose `DmxUniverse.dmx_channels` contains one malformed
        entry (reuse `tests/support/roundtrip.py`'s helpers for a minimal valid script skeleton,
        following the pattern `tests/contract/test_dmx_failure_path.py` uses for
        `rt.build_generated_script()`, then inject the malformed entry the same way that file
        injects `_ExplodingScene`), call `CuemsScript.from_json(...)` on it, and assert
        `DmxChannelDecodeError` is raised — proving the error surfaces through this
        non-XML-validated construction path, not just through direct `DmxUniverse` construction.

### Implementation for User Story 1

- [X] T005 [US1] In `src/cuemsutils/cues/DmxCue.py`, rewrite `DmxUniverse.set_dmx_channels`
      (currently lines 372-396) as a single unified pass — no separate branch per kind of entry,
      no per-iteration reassignment (research.md Decision 3, revised):

      ```python
      def set_dmx_channels(self, channels):
          Logger.info("DmxUniverse set_channels called with channels: {}".format(channels))
          if not isinstance(channels, list):
              channels = [channels]
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

      **The trailing `if channel_list:` guard is load-bearing, verified empirically during
      implementation, not obvious from reading the original code**: today, `super().__setitem__`
      only ever runs inside the original loop's `if r is not None:` branch, so an empty list or an
      all-`None` batch calls it **zero times** — `dmx_channels` is left completely untouched (its
      declared default on a fresh universe; unchanged if reassigned on an already-populated one),
      **never actually set to `[]`**. (This corrects the spec's original Edge Cases claim that an
      empty list "stores an empty list" — that was never true; verify with
      `DmxUniverse().dmx_channels` after assigning `[]` or `[None]` before trusting either the old
      or new code's behavior here.) Since every non-`None` entry either appends to `channel_list`
      or raises, `channel_list` is non-empty exactly when at least one non-`None` entry existed and
      converted successfully — so `if channel_list:` reproduces today's "touch the key iff at least
      one non-`None` entry existed" rule exactly, without the per-iteration reassignment that made
      it expensive (Decision 3/6).

      Keep the existing `isinstance(channels, list)` wrapping (unchanged — a single non-list
      argument is still wrapped into a one-item list before the loop, per Acceptance Scenario 4).
      Already-`DmxChannel` instances are appended **as-is** (identity preserved — this is what
      keeps `test_a_single_dmxchannel_instance_is_wrapped_into_a_list_unconverted` and
      `test_a_list_of_dmxchannel_instances_passes_through_unconverted` passing, since both only
      assert element identity via `is`, not that the *list object itself* is unchanged). Raw dict
      entries are converted and the **new** instance appended. There is no separate fallback
      branch, no outer `try`/`except Exception`, and no per-iteration `super().__setitem__` call
      left in the new code. Import `DmxChannelDecodeError` from `cuemsutils.errors` at the top of
      this file.

### Verification for User Story 1

- [X] T006 [US1] Run
      `hatch test --show -- tests/unit/test_dmx_universe_channels.py tests/contract/test_dmx_channel_decode_failure_path.py`
      and confirm all tests pass, including the five unmodified well-formed-path tests in
      `test_dmx_universe_channels.py` and the new mixed-batch and `from_json` cases in T003/T004.
- [X] T007 [US1] Manually run the "Reproduce the defect", "After the fix", "Verify no regression on
      valid input", and "Verify the mixed-batch fix" snippets from `quickstart.md` in a Python
      shell (or a scratch script) against the fixed code, and confirm the output matches what
      quickstart.md documents.
- [X] T008 [US1] **Performance verification (SC-PERF-001, closes analysis finding C1)**: run
      `quickstart.md`'s "Verify the performance budget" snippet (or an equivalent benchmark script)
      against the **fixed** implementation for both a realistic (8-entry) and a maximum (512-entry)
      batch, matching research.md Decision 6's methodology (`hatch run test:python`, warm-up loop,
      1000+ calls, per-call average). Confirm: (a) the 8-entry case is ≤ 3 ms/call; (b) the
      512-entry case is no worse than the recorded 37.0715 ms/call pre-fix baseline. If the
      512-entry case measures meaningfully faster post-fix (expected, per Decision 3's removal of
      the redundant per-iteration reassignment), update research.md Decision 6, plan.md's
      Technical Context, and spec.md's SC-PERF-001 with the new measured number instead of leaving
      the "no regression versus baseline" placeholder bar in place — a real improved number is more
      useful to future readers than a preserved-baseline bar once it's known.
      **Measured 2026-09-03 (Python 3.11.9, two runs each)**: 8-entry — 0.727/0.736 ms/call (budget
      met, ≤3ms, unchanged from 0.71 ms/call pre-fix). 512-entry — 37.60/37.80 ms/call (budget met:
      no regression vs. 37.07 ms/call pre-fix, within measurement noise). **The "expected to
      improve" prediction was wrong** — measured and corrected in research.md/spec.md/plan.md: the
      redundant per-iteration reassignment this fix removes was never the 512-entry case's
      dominant cost; the 512 individual `DmxChannel(...)` constructions are, and this fix doesn't
      touch those.

**Checkpoint**: User Story 1 is fully implemented, tested, and independently verified — including
the mixed-batch fix, the `from_json` reachability path, and the performance budget. This is the
entire feature — proceed to Polish.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Constitution gates (lint, types, full-suite regression) and keeping this repo's
self-documentation (CLAUDE.md, the defect record) accurate now that the fix has landed.

- [X] T009 [P] Run `hatch run test:lint` (`ruff check src/ tests/`) and confirm zero new warnings
      in `src/cuemsutils/cues/DmxCue.py`, `src/cuemsutils/errors.py`,
      `tests/unit/test_dmx_universe_channels.py`, and
      `tests/contract/test_dmx_channel_decode_failure_path.py`.
      **Verified**: the repo has 605 pre-existing lint findings unrelated to this feature (checked
      via before/after diff on every touched file). `errors.py` was clean before and after;
      `DmxCue.py` dropped from 63 to 62 pre-existing findings (net improvement, none introduced);
      both new/rewritten test files pass `ruff check` cleanly (one `I001` blank-line fix applied).
- [X] T010 [P] Run `hatch run types:check` (`mypy --install-types --non-interactive src/cuemsutils tests`)
      and confirm no new type errors introduced by this feature's changes.
      **Verified**: the one `DmxCue.py` mypy finding (a pre-existing `DECLARED_DEFAULTS` type
      mismatch, unrelated to `set_dmx_channels`) and the "cannot find stub for pytest" errors
      across the whole test suite both predate this feature — confirmed via `git stash`
      before/after comparison. `errors.py` type-checks clean.
- [X] T011 [P] Run the full suite (`hatch test --show`) and confirm the only differences from
      T001's baseline are: the three rewritten tests plus the new mixed-batch test in
      `tests/unit/test_dmx_universe_channels.py` passing, and the new
      `tests/contract/test_dmx_channel_decode_failure_path.py` file's tests passing — no other
      test's outcome changes (SC-003).
      **Verified, after two real regressions found and fixed**: `test_public_api_surface.py`'s
      exact-match assertion on `cuemsutils.errors.__all__` failed (expected — `PUBLIC_ERRORS`
      needed the new name added, plus the `api/public_api.json` golden needed the new class's
      snapshot entry) and `test_golden_immutability.py` then failed on that golden's changed hash
      (expected — re-hashed in `MANIFEST.sha256` with a recorded justification paragraph, following
      the feature 008 ITEM E precedent exactly). Final: **2573 passed** (2562 baseline + 11: 1 new
      test in T003, 10 new tests in T004), 96 skipped, 2 xfailed — identical skip/xfail counts,
      confirming zero other test's outcome changed.
- [X] T012 [P] Add a "Recent Changes" bullet for `009-fix-dmx-channel-conversion` to `CLAUDE.md`
      (top of the list, matching the existing entries' style for 007/008): summarize that
      `DmxUniverse.set_dmx_channels` now raises `DmxChannelDecodeError` (`cuemsutils.errors`)
      instead of silently storing corrupted channel data on a conversion failure, that a mixed
      batch of already-converted and still-raw entries is now correctly converted instead of
      silently dropping one side (FR-004a), that this is unreachable from schema-valid
      `script.xml` (confirmed by investigation — no `.xsd` change), that it is reachable from
      `CuemsScript.from_json`/direct construction, and the measured performance budget
      (SC-PERF-001, with T008's final numbers).
- [X] T013 [P] Update `specs/planning/dmx-universe-channel-conversion-defect.md` to record that
      this defect is resolved by `specs/009-fix-dmx-channel-conversion/` (remediation proposal 1),
      following this repo's own convention of correcting planning docs once their described gap is
      closed (see the `007-node-model-migration` correction note in `CLAUDE.md`'s "Submodules"
      section for the precedent of how such a correction is worded and dated).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 only in that T001's baseline should be captured
  first; T002 itself has no code dependency on T001. Blocks Phase 3 (T005 imports the class T002
  creates).
- **User Story 1 (Phase 3)**: Depends on Phase 2 (T002) for T005. T003/T004 (tests) can be written
  before or in parallel with T002/T005, per TDD, but T006 (running them) requires T002 and T005
  both done.
- **Polish (Phase 4)**: Depends on Phase 3 being complete (T005 merged, T006/T007/T008 green).

### Within Phase 3

- T003 and T004 are independent files — parallelizable, and both should be written (and observed
  failing against the pre-fix code) before T005 lands, per the constitution's fail-before-pass
  rule.
- T005 depends on T002 (needs `DmxChannelDecodeError` to import).
- T006 depends on T003, T004, and T005 all being done.
- T007 depends on T005 (nothing to demo before the fix exists); independent of T006.
- T008 depends on T005 (needs the fixed implementation to measure); independent of T006/T007, but
  logically runs last since it may prompt an update to three other documents (Decision: run it
  after T006/T007 confirm correctness, since a broken implementation makes a performance number
  meaningless).

### Parallel Opportunities

- T003 and T004 (different files, no shared state).
- T009, T010, T011 (three independent verification runs against the same finished code — no file
  conflicts, can run concurrently).
- T012 and T013 (different files, both pure documentation edits).

---

## Parallel Example: Phase 3 tests

```bash
# Launch both test-writing tasks together (different files):
Task: "Rewrite fallback-path tests + add mixed-batch test in tests/unit/test_dmx_universe_channels.py"
Task: "Create tests/contract/test_dmx_channel_decode_failure_path.py mirroring test_dmx_failure_path.py, with from_json and mixed-batch cases"
```

## Parallel Example: Phase 4 verification

```bash
# Launch all three verification runs together:
Task: "Run hatch run test:lint"
Task: "Run hatch run types:check"
Task: "Run hatch test --show and diff against T001's baseline"
```

---

## Implementation Strategy

### MVP = the whole feature

There is exactly one user story, so there is no "MVP subset" to choose — Phase 3 complete (T003
through T008 green) is a fully working, fully tested, independently verifiable, performance-checked
fix. Phase 4 is release hygiene (lint, types, regression, documentation), not additional
functionality.

### Suggested order

1. T001 (baseline) → T002 (foundational error class)
2. T003, T004 in parallel (tests, written to fail against current code)
3. T005 (the fix — unified loop) — confirm T003/T004 now pass
4. T006, T007 (correctness verification), then T008 (performance verification)
5. T009, T010, T011, T012, T013 in parallel (polish)

---

## Notes

- [P] tasks touch different files and have no unmet dependency at the point they can start.
- Every task names its exact file path except T001/T006/T008-T011, which are verification runs
  (their scope is the file paths named within their description).
- This feature makes no `.xsd` change and adds no new dependency — confirmed during
  `/speckit.specify` and `/speckit.plan`; no task here touches `src/cuemsutils/xml/schemas/`.
- Commit after each task or logical group, per repository convention (GPG-signed commits — retry
  on "gpg failed to sign", never `--no-gpg-sign`, per CLAUDE.md).
