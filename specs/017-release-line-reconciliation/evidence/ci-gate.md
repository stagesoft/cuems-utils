<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Pre-publication gate run (FR-075, SC-013): TEMPLATE, not yet run

**Status: owed after hand-off.** 017 delivers the gate and its static check
(`tests/contract/test_ci_workflow.py`, green). It does not deliver a run (clarification: the CI gate
moved out of 017). The run is the maintainer's and happens **after** 017 is merged into
`feat/xml-refactor`. `0.1.1` is not published until this record is filled and every check below
holds.

## How to fill it

1. Merge 017 into `feat/xml-refactor`, and push it (maintainer). `tests.yml` must also exist on
   `main` for `workflow_dispatch` to accept it. It does: the file name is unchanged.
2. Re-cut every sibling's `xml-refactor-merge-candidate` at its reconciled head (rule 4,
   `specs/planning/coordinated-release-version-bump.md`).
3. If any sibling repository is private, create a token that can read all six and store it as
   the repository secret `SIBLINGS_TOKEN`. Without it the checkout uses `github.token`, which reads
   public repositories only. Record below that you did.
4. Dispatch:
   ```bash
   gh workflow run tests.yml --ref feat/xml-refactor -f siblings_ref=xml-refactor-merge-candidate
   gh run watch "$(gh run list --workflow tests.yml --limit 1 --json databaseId -q '.[0].databaseId')"
   ```
5. Copy the `gate-summary` job's summary into the blanks below (the run page, *Summary*).

## Record

| Field | Value |
|---|---|
| Run URL | ____ |
| Date | ____ |
| Tested `cuems-utils` SHA (must be the post-merge `feat/xml-refactor` head) | ____ |
| `siblings_ref` | ____ |
| `SIBLINGS_TOKEN` created? (needed only if a sibling is private) | ____ |

### Sibling commits (each must be its reconciled re-cut tag's commit, `<tag>^{commit}`)

| Sibling | Resolved commit | = its tag's commit? |
|---|---|---|
| cuems-common | ____ | ____ |
| cuems-nodeconf | ____ | ____ |
| cuems-power-bridge | ____ | ____ |
| cuems-engine | ____ | ____ |
| cuems-editor | ____ | ____ |
| cuems-frontend | ____ | ____ |

### Tests per job

| Job | passed | failed | skipped | xfailed | `reads_siblings` ran | `reads_siblings` skipped |
|---|---|---|---|---|---|---|
| unit (unit + contract) | ____ | ____ | ____ | ____ | ____ | ____ |
| integration | ____ | ____ | ____ | ____ | ____ | ____ |
| packaging | ____ | ____ | ____ | ____ | ____ | ____ |
| matrix-py3.12 | ____ | ____ | ____ | ____ | ____ | ____ |
| matrix-py3.13 | ____ | ____ | ____ | ____ | ____ | ____ |

- Strict xfails that passed (`XPASS(strict)`, each a failure): ____
- Resolved `xmlschema` / `lxml`: ____ / ____ (must be `3.4.3` / `6.1.0`, the pins)

### Job results

| Job | Blocking (Q11) | Result |
|---|---|---|
| lint | yes | ____ |
| unit | yes | ____ |
| integration | yes | ____ |
| packaging | yes | ____ |
| coverage | yes | ____ |
| matrix-info (3.12, 3.13) | no | ____ |
| gate-summary | (the gate) | ____ |

- Docs deployed by this run? **must be no** (a dispatch never deploys, FR-073): ____
- Coverage uploaded to Codecov by this run? **must be no** (FR-073): ____

## The gate holds when

- every blocking job is `success`, and so `gate-summary` is `success`;
- **`reads_siblings` skipped is 0** in `unit` and `packaging`. A skip means a sibling or its tag
  was not there, so the cross-repository claims were not checked, and the run does not count. The
  one exception is the `slow` chroot test, which is deselected by `-m "not slow"` and appears in
  neither count;
- every sibling commit is its re-cut tag's commit;
- nothing was deployed or uploaded.

An informational failure (3.12/3.13) does not block. Record it, with the failing tests, here.
