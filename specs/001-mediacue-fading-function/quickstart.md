# Quickstart: MediaCue Parametric Fades

## Goal

Verify typed fade-profile support (`type: in|out`) for `MediaCue`,
XML schema enforcement, and backward compatibility for scripts without fade data.

## Prerequisites

- Python environment with project dependencies installed
- Working branch: `001-mediacue-fading-function`
- Test runner available (`pytest`)

## 1) Implement model + schema changes

- Extend `MediaCue` data model to hold optional typed `fade_profile` entries.
- Extend `script.xsd` `MediaCueType` with optional repeatable `fade_profile`
  structure including required `type`.
- Ensure parser/serializer roundtrip preserves typed fade profile
  semantics.

## 2) Add tests (write failing tests first)

- Unit tests: `MediaCue` fade profile validation and normalization behavior.
- Contract tests: XML schema acceptance/rejection for valid/invalid fade blocks.
- Integration tests: full script roundtrip containing media cues with:
  - both profile types (`in` and `out`) configured
  - preset fade function (no user parameters)
  - parametric fade function (with parameters)
  - legacy cue without fade profile

## 3) Run quality gates

- Run relevant test suites for unit/integration/contract.
- Run lint/type checks required by project workflow.
- Confirm no new warnings in touched files.

## 4) Verify success criteria

- Roundtrip preserves fade data for valid samples.
- Invalid fade XML is rejected deterministically.
- Legacy scripts still validate and execute unchanged.
- Both `in` and `out` profile types resolve and apply the matching directional
  function profile.
- Parse/serialize overhead increase is within <=5% budget on representative
  script samples.

## 5) Manual sanity check

- Build one script using a preset fade and one with parametric fade.
- Validate both scripts, then load and inspect resulting cue objects.
- Confirm `preset` mode requires no user parameters and remains executable.
