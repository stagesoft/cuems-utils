<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Data model — 016 coordinated minor bump

There is no runtime data. The "entities" are the records this feature produces, all plain files
in `specs/016-coordinated-minor-bump/` or `../.xml-refactor-tag-messages/`.

## Repository record — `records/<repo>.md` (one per repository, seven)

| Field | Source | Rule |
|---|---|---|
| `start_commit` | `git rev-parse feat/xml-refactor` before any edit | FR-001; tree clean, 0/0 with origin |
| `measured_versions` | every self-version site + changelog head and distribution | FR-002; compared with research R5 |
| `release_line`, `released_high_water` | research R1 method | FR-002; target must sort strictly above it |
| `release_gap_start` | `behind/ahead` + absent changelog entries (`comm` recipe) | FR-010 |
| `target` | research R5 / `contracts/relation-matrix.md` | FR-003 |
| `bump_commit` | hash after commit; `replaced: [old hashes]` after amends | FR-009, FR-021 |
| `release_gap_bump` | as above, at `bump_commit` | FR-010 |
| `relations` | sites owned, old → new | FR-005 |
| `literals_reviewed` | each R9 occurrence: moved / kept-as-history, with reason | FR-005, R9 |
| `suite_start` | start run: sibling and library both at start | FR-007 |
| `suite_A`, `suite_B` | pass/fail/skip/xfail counts, failing ids, interpreter path, 3 timings each; both on the bumped library | FR-007, FR-019, FR-PERF-001 |
| `library_effect` | ids differing between `suite_start` and `suite_A` | FR-007 |
| `reruns` | dependent re-runs caused by an amend (which commit, what was repeated) | FR-021 |
| `new_failures` | ids in B and not in A; must be empty | SC-TEST-001 |
| `build` | `.deb` name, `Version`, pyvenv `home` (or "no venv") | FR-006 |
| `demo` | exit status + evidence path (common, nodeconf only) | FR-011 |
| `tag_message` | path + verification result | FR-008 |
| `go_ahead` | maintainer's decision at the stop, with date | FR-021 |

**State transitions** (one repository):

```text
measured ──► edited ──► committed ──► built ──► tested ──► demo'd* ──► message written ──► STOP
                ▲                                                                              │
                └──────────────── correction requested → amend (FR-021) ◄──────────────────────┘
                                                                 go-ahead ──► next repository
```

`*` Only `cuems-common` and `cuems-nodeconf` have a demo. A failure at any step returns to `edited`.
Nothing advances past a failure.

## Preflight record — `records/preflight.md`

One row per FR-018 item: what was checked, the command, the result, and for a missing item the
exact command handed to the maintainer. It is re-run until clean. FR-020 (`pyossia`) is a row checking
`pyossia.__version__ == "2.0.0rc6+124.cuems.3"` in `cuems-engine/.venv`.

## Evidence — `evidence/`

`evidence/relation-verdicts.txt` (every verdict in the relation-matrix contract);
`evidence/<repo>/{suite-start.txt,suite-A.txt,suite-B.txt,bookworm-build.txt,release-gate-demo.txt}`. Evidence files are **added, never overwritten**. A
rerun gets a numbered suffix.

## Candidate-tag message

See `contracts/tag-message.md`.
