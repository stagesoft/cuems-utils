<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract: the migration tools' post-write T2 report — FR-029c (Q3), and S-4

**Tools:** `cuems-reshape-devices` (`xml/reshape_devices.py`), `cuems-convert-documents`
(`xml/convert_documents.py`). Both run in `postinst` (010 T040). **Consumers:** the operator
reading the `postinst` output or a `--check` run; `cuems-init-node` is unaffected.

## What changes

After a tool **writes** a document, it validates the written document with the loader's own T1 +
T2 path (`CuemsScript.load_with_report` semantics, applied to a throwaway copy; R6).

| Case | Written? | Exit status | WARNING | Summary |
|---|---|---|---|---|
| loader would accept (CLEAN/REPAIRED/CONVERTED) | yes (unchanged) | unchanged | none | unchanged |
| loader would refuse (T2 unrepairable, or T1) | **yes (unchanged)** | **unchanged** | `<path>: would be refused on load: [<tier>] <rule> at <cue>/<field>: <message>` | listed under a new bucket, "written, refused on load" (exact label follows the tool's existing summary vocabulary, read at implementation) |
| tool skipped the document (existing behaviour) | no | unchanged | existing message | unchanged; not re-validated |
| `--check` (no write) | no | unchanged | — | the same check runs on the tree the tool **would** write, and the same bucket reports each document that would then be refused (spec FR-029c) |

**Never:** a change to the bytes written, a non-zero exit introduced by this check, or a write
refused because of it.

## S-4: `python -m`

`python -m cuemsutils.xml.reshape_devices <args>` behaves exactly as `cuems-reshape-devices <args>`
(same output, same exit status). Today it exits 0 and does nothing. `convert_documents` already has
the guard.

## Tests (red first, FR-029a, FR-029c)

1. The rc17 control twin with its `stop` cue's `action_target` emptied → reshape → convert. The
   file is written, a WARNING is emitted, the summary bucket is listed, and the exit status equals
   the no-check run's.
2. The rc17 fixture after A-1 → no bucket entry.
3. A clean corpus document → no bucket entry, no WARNING.
4. `subprocess.run([sys.executable, "-m", "cuemsutils.xml.reshape_devices", <file>])` reports a
   verdict for the file (red on M3: empty output).

## Cost

One extra validation per **written** document. Measured interleaved A/B over
`tests/data/corpus/`, recorded in `evidence/perf.md`, no budget (013 SC-PERF-003 precedent).
