<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# rc17 fixture: provenance (feature 017, FR-022)

Written by **`cuemsutils 0.1.0rc17`'s own `XmlReaderWriter`**, at `398a9cf`
(`origin/debian/bookworm` = tag `debian/0.1.0rc17`), never by the refactor. That is the only way
the fixture shows what an rc17 cluster actually saves.

| | |
|---|---|
| Captured | 2026-10-21 |
| Writer | `398a9cf`, `src/cuemsutils/xml/XmlReaderWriter.py`; rc17's `validate()` passed on both |
| Interpreter | Python 3.11.9, hatch `test.py3.11` (uv-managed, Clang build) |
| Tool | `specs/017-release-line-reconciliation/tools/capture_rc17_fixture.py` |
| Command | `git worktree add --detach $S/wt-bw 398a9cf`, then `env -u CUEMS_CONF_PATH PYTHONPATH=$S/wt-bw/src $PY -W ignore …/capture_rc17_fixture.py --out tests/data/rc17/` |
| Reproducible | yes: ids and timestamps are fixed, and a second run gave byte-identical files |

| File | sha256 | Content |
|---|---|---|
| `stop_project.xml` | `5a352ccf301a99115479d9039ae964bdf371737ebf984b0545d4a718bfdeeabb` | VideoCue with `pixel_width` 1920, `pixel_height` 1080, `file_size` 107374182400 and the md5 `D41D8CD98F00B204E9800998ECF8427E` (rc15's setter wrote it **lowercased**); an AudioCue; a `stop_project` ActionCue written `<action_target />` |
| `stop_control.xml` | `dfe91a0c2f39723671bba5e8e91dedd5be203cb4208a0d4e84dc51f73049b222` | the same, with the last cue `stop` aimed at the AudioCue (`2c7b5a2f-…`) |

**Shape:** pre-013. It has per-class cue elements (`<VideoCue>`, `<AudioCue>`, `<ActionCue>`),
`True`/`False` booleans and a bare `<duration>`, and no `doc_version`. Loading it on `0.1.1`
therefore means `cuems-reshape-devices` → `cuems-convert-documents` → `CuemsScript.load_with_report`.
That is the S-1′ path of the work order (`specs/017-release-line-reconciliation/research.md` R13),
tested by `tests/integration/test_rc17_migration.py`.

**Do not regenerate these with the refactor's writer.** A re-capture must use rc17's code, as above.
