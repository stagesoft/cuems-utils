<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract: package relations at the 017 head — FR-036, FR-040 (X-2), SC-007

016's matrix (`specs/016-coordinated-minor-bump/contracts/relation-matrix.md`, rows 1–25,
121 verdicts) is **landed record and is not edited**. 017 adds one row.

## Row 26 (new)

| Field | Value |
|---|---|
| Site | `debian/control`, `Package: cuems-utils` stanza |
| Relation | `Replaces: cuems-engine (<< 0.1.0rc6-2~)` |
| Shipped in | `0.1.0rc15` (`6a9d1d8`, PR #14) |
| Reason (the reworded comment carries it) | `/usr/lib/cuems/bin/cffi-gen-src` moved from `cuems-engine` to this package; without `Replaces:` dpkg aborts on the file conflict when an older engine is installed |
| Why no `Breaks:` (Q6; the comment carries it too) | as released; engine `0.1.1-1` depends on `cuems-utils (>= 0.1.1)`, so apt upgrades both together, and engine versions below `0.1.0rc6-2` predate this package owning the file |

| `cuems-engine` version | `dpkg --compare-versions <v> lt 0.1.0rc6-2~` | Expected |
|---|---|---|
| `0.1.0rc5-6` | true | replaced |
| `0.1.0rc6-1` | true | replaced |
| `0.1.0rc6-2` | false | not replaced |
| `0.1.0rc6-5` | false | not replaced |
| `0.1.1-1` | false | not replaced |

## Tool

`specs/017-release-line-reconciliation/tools/verdicts-017.sh [parent]`:
1. runs `specs/016-…/tools/verdicts.sh [parent]` unchanged (121 verdicts);
2. reads row 26 from the parent's `cuems-utils/debian/control` (a missing or changed line fails);
3. runs the five `dpkg --compare-versions` verdicts;
4. prints `126/126` or the failures.

Its output goes to `evidence/verdicts-017.txt`, never to 016's evidence.

**The parent directory is built for the run, never the live checkouts** (analyze U2). It holds one
`git worktree` per sibling at its `feat/xml-refactor` commit (`git -C ../<repo> worktree add
$S/rel/<repo> feat/xml-refactor`), and `cuems-utils` at the 017 head. Each worktree's commit is
written above the verdicts. A sibling checkout's current branch (for example `cuems-engine` on
`009-release-line-reconciliation`, measured 2026-10-21) never enters the result.

## Rows that must not move

Row 1, `Breaks: cuems-common (<< 1.3.1~)`, stays unchanged, and so does every consumer's
`cuems-utils (>= 0.1.1)`, `(<< 0.1.2~)` bound (D6).
