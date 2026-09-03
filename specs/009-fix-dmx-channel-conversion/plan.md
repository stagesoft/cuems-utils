# Implementation Plan: Stop `DmxUniverse` from silently corrupting DMX channel data on construction

**Branch**: `009-fix-dmx-channel-conversion` | **Date**: 2026-09-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-fix-dmx-channel-conversion/spec.md`

## Summary

`DmxUniverse.set_dmx_channels` (`src/cuemsutils/cues/DmxCue.py:372-396`) wraps its whole per-entry
conversion loop in one `except Exception`, so a single malformed channel entry — anywhere in the
batch — silently discards conversion of every entry (good and bad alike) and stores the raw,
unconverted input instead, with only a log line as any trace. The fix (remediation proposal 1 from
`specs/planning/dmx-universe-channel-conversion-defect.md`) raises a new, named, catchable error
(`DmxChannelDecodeError`, in `cuemsutils.errors`) identifying the universe and the failing entry,
mirroring feature 005's `DmxSceneWriteError` precedent on the write side. Investigation during
`/speckit.specify` confirmed this needs **no XSD change**: a schema-valid `script.xml` can never
produce the malformed shape this defect depends on (the converter's list-shape guarantee for
repeated elements is driven purely by declared cardinality, not actual occurrence count), so the
defect is reachable only from a payload that bypassed schema validation — `CuemsScript.from_json`
or direct/programmatic construction. The technical approach, revised during `/speckit.analyze`
remediation: every entry is resolved to a proper `DmxChannel` object (new object → append to the
result list → raise immediately on the first conversion failure), so a raw dict never survives
into `dmx_channels`, matching features 005-008's standing direction that decoded content is
superseded by model objects rather than left as raw dicts. This still raises on the *first*
failure and aborts the whole call — proposal 1's semantics, not proposal 2's per-entry
skip-and-continue — but resolves what was an unstated contradiction between "assign once after the
loop" and "preserve the already-`DmxChannel` branch's per-iteration reassignment exactly" for
batches mixing already-converted instances with still-raw-but-valid entries.

## Technical Context

**Language/Version**: Python 3.11+ (tests run under pyenv 3.11.9, per project CLAUDE.md)
**Primary Dependencies**: None new. Touches only `cuemsutils.cues.DmxCue` and `cuemsutils.errors`
(stdlib only in both — no `xmlschema`/`lxml` involvement, this is below the XML decode boundary).
**Storage**: N/A (in-memory object model only)
**Testing**: `hatch test` (pytest under the hood) — unit tests in `tests/unit/`, contract tests in
`tests/contract/` mirroring `tests/contract/test_dmx_failure_path.py`'s pattern for
`DmxSceneWriteError`.
**Target Platform**: Library consumed by cuems-engine, cuems-editor, and other CUEMS components;
no platform-specific concerns.
**Project Type**: Library (single project, `src/cuemsutils/`).
**Performance Goals**: **≤ 3 ms per `set_dmx_channels` call for a realistic DMX universe (≤ 32
channels)** — SC-PERF-001. Measured pre-fix baseline (Python 3.11.9, `hatch run test:python`, 5000
calls): **0.71 ms/call** for an 8-entry batch, comfortably under budget already, so this is a
non-regression bar. Separately measured for the DMX-spec maximum (512 channels, 2000 calls):
**37.07 ms/call** pre-fix, dominated by today's redundant per-iteration `dmx_channels`
reassignment inside the conversion loop — the fix's unified single-assignment-after-the-loop
design (research.md Decision 3, revised) removes that pattern, so this number is expected to drop,
but the budget for the 512-channel case is stated as "no regression versus 37.07 ms/call", not a
specific improved figure, until the actual fixed implementation is measured (Phase 4 polish task).
This path is not on document decode's measured hot path (confirmed by the XSD investigation: DMX
construction runs through opaque, non-recursive `DmxCue(body)` construction, already outside the
measured `Mapper.decode` path), so the existing suite-level budget
(`specs/008-rebuild-extension/baseline.md`) is unaffected by this feature either way.
**Constraints**: Zero behavior change for any input that converts cleanly today (FR-004, FR-008,
SC-003) — this is a pure failure-path change.
**Scale/Scope**: One method (`DmxUniverse.set_dmx_channels`), one new error type, its test coverage.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Post-Phase-1 re-check**: No new violation surfaced by research.md/data-model.md/contracts/. The
design stayed within the single-method-plus-one-error-type scope assumed below; no new gate is
implicated.

- **Code Quality**: No new lint/type warnings. The new error class follows `cuemsutils/errors.py`'s
  existing pattern exactly (docstring citing the FR it satisfies, `__all__` entry, placement in the
  `CuemsError` hierarchy, identifiers-only message per `DmxSceneWriteError`'s FR-033 precedent).
  `set_dmx_channels` itself shrinks (the swallow-and-fallback branch is deleted, not extended), which
  is a net simplification, not new complexity.
- **Testing Standards**: `tests/unit/test_dmx_universe_channels.py`'s three "exception-swallow
  fallback" tests currently pin the *old* behavior and MUST be rewritten to assert the new raise
  (fail-before-pass: run them unmodified against the fixed code first to confirm they now fail,
  confirming the change is observable, then rewrite and confirm green). Its five "well-formed path"
  tests MUST pass unmodified before and after — they are the regression guard for FR-004/FR-008. A
  new contract test file, `tests/contract/test_dmx_channel_decode_failure_path.py`, mirrors
  `test_dmx_failure_path.py`'s structure (raises, identifies the universe, identifies the failing
  entry, preserves `__cause__`, carries no object repr, control case for the healthy path).
- **UX Consistency**: FR-UX-001 (spec.md) states this explicitly now. The new error's message
  shape, `__cause__` chaining, and "identifiers-only, never object repr" rule follow
  `DmxSceneWriteError` exactly — the one existing precedent for this exact situation (DMX,
  read/write-symmetric failure surfacing) in this codebase. No new CLI surface; this is a library
  exception, so "consistency" here means consistency with `cuemsutils.errors`'s existing four
  public exception types (docstring shape, catchability, no `None`-only-when-degenerate rule
  violated).
- **Performance Requirements**: SC-PERF-001 defines a measurable budget (≤ 3 ms/call for a
  realistic ≤32-channel universe; no regression versus the measured 37.07 ms/call baseline for the
  512-channel maximum) — see Technical Context for the measured baselines and methodology. Not a
  hot-path budget (this construction path sits outside `Mapper.decode`'s measured path entirely,
  confirmed by the XSD investigation), but Principle IV requires a measurable target regardless of
  hot-path status, so one is stated and will be re-measured against the finished implementation in
  Phase 4 polish rather than left as "N/A".

## Project Structure

### Documentation (this feature)

```text
specs/009-fix-dmx-channel-conversion/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── dmx-channel-decode-error.md   # Phase 1 output — the new exception's public contract
├── checklists/
│   └── requirements.md  # /speckit.specify output
└── tasks.md              # Phase 2 output (/speckit.tasks command — NOT created here)
```

### Source Code (repository root)

```text
src/cuemsutils/
├── cues/
│   └── DmxCue.py         # set_dmx_channels — the fix lands here
└── errors.py              # DmxChannelDecodeError — the new public exception lands here

tests/
├── unit/
│   └── test_dmx_universe_channels.py   # rewritten: fallback tests → raise tests
└── contract/
    └── test_dmx_channel_decode_failure_path.py   # new, mirrors test_dmx_failure_path.py
```

**Structure Decision**: Single project (this is the existing `cuems-utils` library layout —
`src/cuemsutils/`, `tests/{unit,contract,integration}/`). No new module, package, or directory is
introduced; the fix is two file edits (one production, one errors module) plus one rewritten test
file and one new contract test file, matching the scope of the defect record's proposal 1.

## Complexity Tracking

*No constitution violations. Table intentionally omitted per template instructions (fill only if
violations must be justified).*
