# Implementation Plan: FadeCue Class

**Branch**: `003-fade-cue` | **Date**: 2026-04-16 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/003-fade-cue/spec.md`

## Summary

Add `FadeCue`, a child of `ActionCue`, that stores a fade-to-level command: a target cue identifier (inherited), a fixed `action_type` of `'fade_action'`, a `curve_type` enum (`linear` / `exponential` / `logarithmic` / `sigmoid`), a `duration` timecode, and a `target_value` integer (0–100). The class follows the established `REQ_ITEMS` / property / `items()` pattern. The XML schema is extended with `FadeCurveType`, `FadeCueType`, and the new `fade_action` enum value. `create_script` and the `cues` package export are updated accordingly.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: stdlib only (`enum`); `CTimecode` (already present); `xmlschema` (already present for validation)  
**Storage**: XML files (via `script.xsd` / `XmlReaderWriter`)  
**Testing**: pytest  
**Target Platform**: Linux (library, no platform-specific concerns)  
**Project Type**: Python library  
**Performance Goals**: Construction, serialization, and deserialization of FadeCue must complete in the same order of magnitude as ActionCue (microseconds; no I/O involved)  
**Constraints**: No new dependencies. No new warnings under `ruff check`.  
**Scale/Scope**: Single new class + XSD additions + one test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code Quality**: `ruff check .` must pass with zero new warnings. All properties follow the getter/setter pattern and docstrings used by `ActionCue` and `DmxCue`. No global state introduced.
- **Testing Standards**: A new `tests/test_fade_cue.py` file covers: (1) construction with valid defaults, (2) construction with explicit values, (3) rejection of invalid `action_type`, (4) rejection of invalid `curve_type`, (5) rejection of zero/negative `duration`, (6) rejection of out-of-range `target_value`, (7) XML round-trip parity. Tests must fail before implementation and pass after. `create_script` test updated to assert FadeCue presence.
- **UX Consistency**: Error messages follow the `ValueError: ...` pattern used by `MediaCue` validators. Property names are snake_case matching the XML element names. Default values are documented in `REQ_ITEMS`.
- **Performance Requirements**: No measurable budget beyond "same order of magnitude as ActionCue". Validated by the fact that FadeCue adds only in-memory dict operations and a `format_timecode()` call — no I/O or iteration.

**Post-design re-check**: Constitution passes. No new dependencies, no warnings introduced by design, test strategy is defined.

## Project Structure

### Documentation (this feature)

```text
specs/003-fade-cue/
├── plan.md        ← this file
├── research.md    ← Phase 0 (complete)
├── data-model.md  ← Phase 1 (complete)
└── tasks.md       ← Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code (repository root)

```text
src/cuemsutils/
├── cues/
│   ├── FadeCue.py              ← NEW: FadeCue class + FadeCurveType enum
│   └── __init__.py             ← MODIFY: add FadeCue export
├── xml/
│   └── schemas/
│       └── script.xsd          ← MODIFY: FadeCurveType, FadeCueType, fade_action, CueListContentsType
└── create_script.py            ← MODIFY: add FadeCue instance

tests/
└── test_fade_cue.py            ← NEW: unit + round-trip tests
```

**Structure Decision**: Single project layout (existing). FadeCue lives alongside other cue classes. No new directories needed.

## Complexity Tracking

No constitution violations. No complexity justification required.
