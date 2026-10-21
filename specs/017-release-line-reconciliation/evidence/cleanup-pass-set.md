<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Cleanup pass set (T075, SC-012)

**Before:** `cleanup-passset-before.txt`, taken ahead of C1 (`9c02cdc`).
**After:** the full suite on `3a99883` plus the `test_version_steps` isolation fix
(`cleanup-checks.txt`, C4 section), hatch `test.py3.11` interpreter. Totals: **7 failed, 3918
passed, 114 skipped, 2 xfailed**.

**Method:** JUnit XML, one `<outcome> <classname>::<name>` row per test. Module paths are normalised
`tests.<kind>.` → `tests.`, so C3's moves compare as the same test. Both sides are sorted *after*
normalising and compared as sets (`comm`), and outcomes are joined by name.

| | Count |
|---|---|
| rows before | 4038 |
| rows after | 4041 |
| only before (a test lost) | **0** |
| only after | **3**: `test_test_layout`'s three tests, PASSED (C3's guard) |
| same test, different outcome | **0** |

**Retirements: none show in the pass set.** `tests/testdev_nng_talk.py` (`test-retirements.md`) did not
match `test_*.py` and was never collected, and nothing under `dev/` was collected either. So C1–C4
retired no collected test. The 7 failures are the same 7 pre-existing ones as arm A (`suite-verdict.md`).
SC-012 holds.
