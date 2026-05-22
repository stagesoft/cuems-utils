# cuems-utils Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-16

## Active Technologies
- Python 3.11+ + stdlib only (`enum`); `CTimecode` (already present); `xmlschema` (already present for validation) (003-fade-cue)
- XML files (via `script.xsd` / `XmlReaderWriter`) (003-fade-cue)

- Python 3.11+ + stdlib only (`threading`, `time`) — `timecode` already present via `CTimecode` (002-timecode-qf-timer)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 003-fade-cue: Added Python 3.11+ + stdlib only (`enum`); `CTimecode` (already present); `xmlschema` (already present for validation)

- 002-timecode-qf-timer: Added Python 3.11+ + stdlib only (`threading`, `time`) — `timecode` already present via `CTimecode`

<!-- MANUAL ADDITIONS START -->

## specs/planning — canonical home for non-code artifacts

All of the following file types MUST be stored in `specs/planning/` and looked for
there first before creating them anywhere else:

- Planning documents and implementation plans
- Agent prompts and reusable AI prompt templates
- Specification documents that span multiple features or repos
- Contributor workflow and process documentation
- Future-development notes, deferred-work records, and roadmap sketches
- Any other file that guides how work is done rather than implementing it

Do NOT store these in `docs/`, repo root, or feature spec directories.
Feature-specific specs (`specs/NNN-feature/`) are the exception — they stay in
their own numbered directory. Cross-cutting or repo-level planning lives in
`specs/planning/`.

Current contents:
- `specs/planning/documentation-prompt.md` — unified prompt for generating
  documentation (README, CHANGELOG, docs/index.md, CONTRIBUTORS, CI workflow)
  across CueMS / StageLab sibling repositories.
<!-- MANUAL ADDITIONS END -->
