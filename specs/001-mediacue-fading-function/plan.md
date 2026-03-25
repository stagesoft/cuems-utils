# Implementation Plan: MediaCue Parametric Fades

**Branch**: `001-mediacue-fading-function` | **Date**: 2026-03-20 | **Spec**: `/disk/Projects/StageLab/cuems-utils/specs/001-mediacue-fading-function/spec.md`
**Input**: Feature specification from `/specs/001-mediacue-fading-function/spec.md`

## Summary

Add directional fade-profile support to `MediaCue` so cues accept both
`fade_in` and `fade_out`, each using either a parametric fade function or a
predefined system fade function without user parameters. Extend XML schema
contracts and parser behavior so typed fade-profile definitions are persisted,
validated, and backward compatible with legacy scripts that omit fade data.

## Technical Context

**Language/Version**: Python 3.11+ (project supports 3.11/3.12/3.13)  
**Primary Dependencies**: `xmlschema`, `lxml`, `pytest`, `pytest-cov`  
**Storage**: File-based XML script serialization/deserialization  
**Testing**: `pytest` unit + integration + schema contract validation tests  
**Target Platform**: Linux runtime for CueMS tooling  
**Project Type**: Python library (cue models + XML schema/parsing)  
**Performance Goals**: Fade-data parse/serialize adds <=5% overhead vs current
MediaCue roundtrip baseline for representative script samples  
**Constraints**: Preserve compatibility for scripts without fade blocks;
maintain existing cue behavior when no fade profile is configured; ensure both
`fade_in` and `fade_out` directions are accepted independently using typed
`fade_profile` entries (`type: in|out`)  
**Scale/Scope**: Covers `MediaCue` model, XML schema, XML parser flow, and
related tests/documentation for audio/video cue inheritance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code Quality**: PASS - change set scoped to cue model, parser, and schema
  with explicit contracts and regression tests; no warning debt accepted.
- **Testing Standards**: PASS - plan includes unit tests for `MediaCue` data
  behavior, integration tests for parser roundtrip, and schema contract tests.
- **UX Consistency**: PASS - user-facing consistency applies to script XML shape
  and validation messaging; new fields follow existing naming conventions.
- **Performance Requirements**: PASS - budget set to <=5% parse/serialize
  overhead; validation includes before/after benchmark on sample scripts.

### Post-Design Re-check (after Phase 1)

- **Code Quality**: PASS - design isolates changes to existing cue/parser/schema
  boundaries with explicit data model and contract docs.
- **Testing Standards**: PASS - quickstart mandates fail-first tests across unit,
  integration, and schema contract suites.
- **UX Consistency**: PASS - XML field naming and mode semantics mirror current
  cue/schema conventions and preserve legacy behavior.
- **Performance Requirements**: PASS - benchmark method defined in `research.md`
  and verified in quickstart acceptance flow.

## Project Structure

### Documentation (this feature)

```text
specs/001-mediacue-fading-function/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── mediacue-fade-xml-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/cuemsutils/
├── cues/
│   ├── FadeProfile.py
│   ├── MediaCue.py
│   ├── AudioCue.py
│   └── VideoCue.py
├── xml/
│   ├── Parsers.py
│   ├── XmlBuilder.py
│   └── schemas/
│       └── script.xsd
└── create_script.py

tests/
├── contract/
│   └── test_mediacue_fade_schema_contract.py
├── integration/
│   └── test_mediacue_fade_roundtrip.py
└── unit/
    └── test_mediacue_fade_profile.py
```

**Structure Decision**: Single Python library layout. New fade model classes live
in `src/cuemsutils/cues/FadeProfile.py`, `MediaCue` imports from it. Schema
updates in `src/cuemsutils/xml/schemas`, parsing updates in
`src/cuemsutils/xml/Parsers.py`, with dedicated unit/integration/contract tests
under `tests/`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
