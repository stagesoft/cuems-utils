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
<!-- MANUAL ADDITIONS END -->
