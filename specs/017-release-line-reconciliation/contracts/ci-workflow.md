<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract: the pre-publication CI gate — FR-070–FR-076, SC-013

**File:** `.github/workflows/tests.yml`. The name is kept: `workflow_dispatch` only works for a file
that exists on the default branch `main` (research R11). **Static check:**
`tests/contract/test_ci_workflow.py` (PyYAML, test environment only).

## Triggers

```yaml
on:
  push:
    branches: [main, feat/xml-refactor]
  pull_request:
  workflow_dispatch:
    inputs:
      siblings_ref:
        description: ref (tag or branch) checked out in each sibling repository
        default: xml-refactor-merge-candidate
        required: false
```

## Jobs

| Job | `needs` | Python | Blocking (Q11) | Does |
|---|---|---|---|---|
| `lint` | — | 3.11 | **yes** | `hatch run test.py3.11:lint` → 0 findings |
| `unit` | `lint` | 3.11 | **yes** | `pytest tests/unit tests/contract -m "not slow" --cov`; uploads `.coverage.unit` as an artefact |
| `integration` | `lint` | 3.11 | **yes** | checks the six siblings out at `siblings_ref` into `../<repo>` (`fetch-depth: 0`, tags); `pytest tests/integration -m "not slow" --cov`; uploads `.coverage.integration`; writes the sibling-reading ran/skipped count |
| `packaging` | `lint` | bookworm's 3.11 (`container: debian:bookworm`) | **yes** | build-deps; `dpkg-buildpackage -us -uc -b`; checks `Version` == changelog, `home = /usr/bin`, `bin/python -> ../../../bin/python3`, no `usr/lib/cuems/CACHEDIR.TAG`; `pytest tests/packaging` (chroot tests skip) |
| `coverage` | `unit`, `integration` | 3.11 | **yes** | `coverage combine` + `report` (the threshold applies to the combined figure); Codecov upload **only if** `github.event_name == 'push' && github.ref == 'refs/heads/main'` |
| `matrix-info` | `lint` | 3.12, 3.13 | no (`continue-on-error: true`) | `hatch run test.py3.X:run` |
| `gate-summary` | all of the above, `if: always()` | — | — | writes `$GITHUB_STEP_SUMMARY` (fields below); **fails iff a blocking job's result is not `success`** |

## Measured correction (T077, 2026-10-22): siblings in three jobs, not one

The table above put the sibling checkouts in `integration` only. Measured while writing the
static test: **no `tests/integration/` module reads a sibling.** The tests that do are five in
`contract/test_migration_guide.py`, three in `contract/test_migration_guide_names_sites.py`, and
four in packaging (`test_release_matrix` ×2, `test_ordering_premise`, and the `slow`
`test_lifecycle_chroot` custody test). That is 33 collected items. If the siblings were checked out
in `integration` only, the gate would have run none of them, and FR-071's "so the
cross-repository tests run" would have been missed.

So:
- `unit`, `integration` and `packaging` each check this repository out at `path: cuems-utils`
  (`fetch-depth: 0`). Each then uses the local action `.github/actions/checkout-siblings` with
  `ref: ${{ inputs.siblings_ref || 'xml-refactor-merge-candidate' }}`. The action places the six
  beside it (`stagesoft/cuems_editor` → `cuems-editor/`), with full history and tags, and writes
  `sibling-commits.txt`. `actions/checkout` cannot write outside `$GITHUB_WORKSPACE`, so this
  repository is the one in a sub-directory.
- "Sibling-reading" is an explicit marker, `@pytest.mark.reads_siblings`, on those 12 functions
  (33 items). It is not a path heuristic: the grep version both missed modules and caught
  non-readers. `tests/conftest.py` copies it into `user_properties`, so it reaches the JUnit XML.
  `.github/scripts/gate_summary.py` (stdlib) counts it, ran versus skipped, per job.
- Two of 017's seven pre-existing failures were stale assertions that would have kept a
  sibling-carrying gate red forever: `test_siblings_at_their_candidate_tags` (a strict xfail the
  2026-10-16 re-cut overtook) and the coupled-engine check (equality where its docstring says
  floor). They were fixed in `2560b09` before the restructure.

The static check asserts all of this: the three jobs, the action's six paths and `ref`, and the
marker's path into the XML.

## `gate-summary` fields (also the `evidence/ci-gate.md` template)

This repository's SHA; `siblings_ref` and each sibling's resolved commit; pass, skip and xfail
counts per job; the strict xfails; sibling-reading tests ran versus skipped; resolved `xmlschema`
and `lxml` versions; each blocking job's result; each informational job's result.

## `gh-pages.yml`

The deploy step runs only if `github.event_name == 'push' && github.ref == 'refs/heads/main'`.
On a pull request or a dispatch, the site may still be **built** (`mkdocs build --strict`) as a
check, but it is never deployed.

## `pypi-publish.yml`

The trigger is unchanged. The pre-publication checklist line (FR-076) lives in the tag message and
in `CONTRIBUTORS.md`, not in this file.

## Static check asserts

1. The trigger map includes the three triggers and `siblings_ref` with its default. PyYAML reads
   `on:` as `True`, so the test looks under both keys.
2. The job set and the `needs:` graph are exactly the table above.
3. The `packaging` job runs in `debian:bookworm`.
4. `matrix-info` is `continue-on-error`, and no other job is.
5. `gate-summary`'s failure condition names exactly the blocking set.
6. Every Codecov step and the `gh-pages` deploy step carry the `main`-push-only condition.

Red first: every assertion is red against today's single-job file.

## After hand-off (not 017's run)

A dispatch on the post-merge `feat/xml-refactor` head with `siblings_ref` at the current candidate
tags must be green, and it fills `evidence/ci-gate.md`. If a sibling repository is private, the
checkout needs a token. Creating one is the maintainer's act and is recorded there.
