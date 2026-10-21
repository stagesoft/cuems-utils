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
