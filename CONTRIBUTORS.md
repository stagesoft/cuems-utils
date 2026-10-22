<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contributing to cuems-utils

Thank you for your interest in cuems-utils. This library is on the critical path of
every CueMS component — a regression here can silently break audio, video, or DMX
playback at show time. These guidelines exist to protect that reliability while
keeping the project genuinely open to external contributions.

The authoritative governance document for the rules summarised here is
[`specs/planning/contributor-workflow.md`](specs/planning/contributor-workflow.md).
If this file and that document conflict, the planning document wins.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Development Setup](#2-development-setup)
3. [Contribution Tiers](#3-contribution-tiers)
4. [Branch Naming](#4-branch-naming)
5. [Spec-First Requirement](#5-spec-first-requirement)
6. [TDD Workflow — Non-Negotiable](#6-tdd-workflow--non-negotiable)
7. [Commit Hygiene](#7-commit-hygiene)
8. [Developer Certificate of Origin (DCO)](#8-developer-certificate-of-origin-dco)
9. [Pull Request Requirements](#9-pull-request-requirements)
10. [Acceptance Criteria](#10-acceptance-criteria)
11. [Review Process](#11-review-process)
12. [Changelog Line](#12-changelog-line)
13. [Dependency Governance](#13-dependency-governance)
14. [License](#14-license)

---

## 1. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11+ | managed via [pyenv](https://github.com/pyenv/pyenv) |
| hatch | ≥ 1.9 | environment and test matrix management |
| Git | any recent | DCO sign-off required (see §8) |

No system-level packages are required for basic development. The `systemd` optional
extra (`systemd-python`) requires a Linux host with systemd headers; it is not needed
to run the core test suite.

---

## 2. Development Setup

```bash
# Clone and enter the repo
git clone https://github.com/stagesoft/cuems-utils.git
cd cuems-utils

# Install the correct Python version
pyenv install 3.11
pyenv local 3.11

# Editable install with all optional dependencies
pip install -e ".[all]"

# Verify the test suite is green before making any changes
hatch run test.py3.11:run
```

Run lint checks (the CI gate requires 0 findings):

```bash
hatch run test.py3.11:lint
```

Run the Python 3.12 / 3.13 matrix (informational in CI; 3.11 is the one that blocks):

```bash
hatch run test.py3.12:run
hatch run test.py3.13:run
```

Use the `test` environment's scripts, not `hatch test`: hatch's built-in test environment does
not install this project's test dependencies (`hypothesis`, `pyyaml`).

---

## 3. Contribution Tiers

The review requirements depend on what you change.

### Tier 1 — Trivial

No change to any file under `src/cuemsutils/` beyond a single-line correction.
Covers: README edits, doc fixes, comment corrections, adding a test for
already-shipped behaviour, CI/CD config changes, schema annotation updates.

**Gates**: lint + CI green; one owner approval. No spec required.

### Tier 2 — Non-trivial

Any addition, modification, or deletion of logic in `src/cuemsutils/`. Includes
bug fixes that change branching behaviour, new features, refactors, new class
introductions, and schema changes.

**Gates**: spec + plan on the branch; failing test before implementation; CI green;
constitution compliance declaration; one mandatory owner approval.

---

## 4. Branch Naming

```
feat/NNN-short-description       ← new feature  (NNN = spec number, e.g. 004)
fix/NNN-short-description        ← bug fix referencing a spec or issue number
chore/short-description          ← non-production changes (CI, tooling, docs)
```

The `NNN` prefix links the branch to `specs/NNN-feature/` artifacts. Branches
without a valid prefix will not be merged.

---

## 5. Spec-First Requirement

For **Tier 2** changes, before opening a PR for review you MUST commit these two
files on your feature branch:

```
specs/NNN-feature/spec.md    ← feature specification
specs/NNN-feature/plan.md    ← implementation plan with Constitution Check completed
```

If you are a first-time contributor unfamiliar with the spec format, open a
[Discussion](https://github.com/stagesoft/cuems-utils/discussions) first and the
maintainers will help you scope the work.

The PR description must link to both artifacts. A PR without them will be marked
as a draft and returned for pre-work.

---

## 6. TDD Workflow — Non-Negotiable

cuems-utils enforces Test-Driven Development for all Tier 2 changes. This is not
a style preference — it is a constitutional requirement.

The mandatory sequence:

```
1. Write a failing test that precisely describes the intended behaviour.
2. Confirm CI fails on that commit (or run pytest locally and record the failure).
3. Write the minimum production code required to make the test pass.
4. Refactor without changing observable behaviour, keeping all tests green.
```

Your git log on the feature branch MUST show this order. The PR template asks for
the commit SHA of your failing-test commit. Reviewers will check it.

```bash
# Run the full suite
hatch run test.py3.11:run

# Run with coverage report
hatch run test.py3.11:run-cov

# Flush any remaining .milliseconds DeprecationWarnings as hard failures
pytest -W error::DeprecationWarning

# Run only slow-marked tests
pytest -m slow

# Skip slow tests for a fast feedback loop
pytest -m "not slow"

# One kind only (the marker comes from the directory)
pytest -m unit
```

### Where a new test goes

Every test module lives in exactly one of four directories. Its **marker comes from the
directory** (`tests/conftest.py` adds it), so never write `@pytest.mark.unit` and its siblings by
hand. `tests/contract/test_test_layout.py` fails on a `tests/test_*.py` at the root, and on any
test that ends up with no kind marker or more than one.

| Directory | Marker | What belongs there |
|---|---|---|
| `tests/integration/` | `integration` | real sockets / `pynng`, `asyncio` servers, threads, syslog, `CUEMS_CONF_PATH` or `/etc/cuems`, subprocesses of the console tools |
| `tests/contract/` | `contract` | asserts a published surface: schema hashes, the API snapshot, enumerations, version sites, the workflow files |
| `tests/packaging/` | `packaging` | reads `debian/`, builds or inspects a `.deb`, the chroot lifecycle |
| `tests/unit/` | `unit` | everything else (pure in-process) |

Write tests through the public API (`CuemsScript.load` / `save` / `from_json`, `ConfigManager`,
`cuemsutils.errors`). A test that imports a deprecated module on purpose must say so with
`pytestmark = pytest.mark.expects_deprecation`, or `tests/contract/test_deprecated_imports_are_marked.py`
fails. A test that reads a sibling repository checked out beside this one carries
`@pytest.mark.reads_siblings`, and skips with a reason when the sibling is absent.
`--strict-markers` is on, so a misspelt marker is an error.

---

## 7. Commit Hygiene

cuems-utils uses [Conventional Commits](https://www.conventionalcommits.org/) v1.0.

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
Signed-off-by: Your Name <your@email.com>
```

Allowed types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`, `ci`, `perf`, `patch`.

Breaking changes: append `!` after the type and include a `BREAKING CHANGE:` footer.

Rules:
- Each commit MUST represent one logical change.
- Do not squash unrelated changes into a single commit.
- Force-pushing to `main` is forbidden. Amending published commits on shared
  branches is forbidden.

---

## 8. Developer Certificate of Origin (DCO)

Every commit must carry a `Signed-off-by` line, asserting that you have the right to
submit the contribution under GPL-3.0, as per the
[Developer Certificate of Origin](https://developercertificate.org).

```bash
git commit -s -m "feat: add support for ..."
```

To add sign-off to all commits in a branch automatically, set:

```bash
git config --local format.signOff true
```

PRs that contain unsigned commits will not be merged.

---

## 9. Pull Request Requirements

Open your PR against `main` (or the current release candidate branch as directed
by maintainers). Use the PR template — it contains the full acceptance checklist.

Every PR MUST include in its description:

1. **Summary** — what changed and why (2–5 sentences).
2. **Changelog Line** — see §12.
3. **Spec links** (Tier 2 only) — links to `spec.md` and `plan.md` on the branch.
4. **Failing-test commit SHA** (Tier 2 only) — the commit where CI was red before
   implementation began.
5. **Completed PR checklist** — all items in the template ticked.

Draft PRs are welcome for early feedback on approach. Drafts will not be formally
reviewed. Convert to Ready when all gates pass.

---

## 10. Acceptance Criteria

A PR is ready to merge when ALL of the following are true:

| Criterion | How verified |
|---|---|
| `spec.md` and `plan.md` committed on branch (Tier 2) | Reviewer reads the files |
| Failing test committed before implementation (Tier 2) | SHA provided; reviewer checks git log |
| All tests pass | CI green |
| Coverage ≥ 80% | CI coverage gate |
| `ruff check` passes | CI lint gate |
| No new runtime dependency without justification | Reviewer checks `pyproject.toml` diff |
| SPDX header on all new source files | Reviewer inspects new files |
| XSD schema updated in the same commit as any Python model change | Reviewer checks diff |
| DCO sign-off on all commits | GitHub DCO check |
| At least one owner approval | GitHub branch protection |

---

## 11. Review Process

All PRs to `main` require approval from at least one repository owner:

- **Ion Reguera** ([@ibiltari](https://github.com/ibiltari))
- **Adrià Masip** ([@backenv](https://github.com/backenv))

This is enforced by `.github/CODEOWNERS` and GitHub branch protection.

**What owners check:**
- Spec and plan are coherent with the implementation (Tier 2).
- TDD sequence is evidenced in the git log.
- All CI gates pass.
- Constitution checklist is ticked accurately, not perfunctorily.
- No new runtime dependency slipped in without justification.
- SPDX header present on all new source files.
- XSD schema changes are paired with matching Python model and test changes.
- SOLID principles respected — single responsibility, no god classes, dependencies
  injected not constructed.

Expect review turnaround within 5 business days. For urgent fixes, open an issue
first and tag a maintainer — that speeds triage.

---

## 12. Changelog Line

You do not edit `CHANGELOG.md` — that is the maintainers' responsibility at release
time. Instead, include a **Changelog Line** in your PR description. Maintainers copy
this line verbatim (or lightly edited) when cutting a release.

Format:

```
[TYPE] Past-tense sentence describing what changed and why it matters to users.
```

Types: `Added`, `Changed`, `Fixed`, `Removed`, `Security`, `Performance`.

Examples:

```
[Added] FadeCue supports logarithmic and sigmoid curve types in addition to linear.
[Fixed] CTimecode.__str__ no longer wraps to 00:00:00:00 after 24 h continuous MTC.
[Changed] CTimecode.milliseconds split into milliseconds_exact (float) and milliseconds_rounded (int).
```

### Before publishing a release (maintainers)

A release is published only after a **green dispatched run of `tests.yml`** on the exact commit
being released, with **every sibling at its reconciled re-cut tag**:

```bash
gh workflow run tests.yml --ref feat/xml-refactor -f siblings_ref=xml-refactor-merge-candidate
```

For `0.1.1`, that commit is the post-merge `feat/xml-refactor` head. The run comes **before**
the GitHub release, which triggers `pypi-publish.yml`, and before the `.deb` upload. Its
`gate-summary` job writes the run record; copy it into the feature's `evidence/ci-gate.md`. A run
that shows sibling-reading tests skipped did not check the siblings, so it does not count.

---

## 13. Dependency Governance

No new entry under `[project.dependencies]` in `pyproject.toml` may be introduced
without:

1. A written justification in the PR description explaining why the standard library
   and existing dependencies cannot solve the problem.
2. Explicit acknowledgement from a repository owner in the review.

Note that `lxml` is pinned at 5.3.0 due to CVE-2026-41066 (XXE in lxml < 6.1.0).
cuems-utils does not call the vulnerable parser APIs, so active risk is zero, but
bumping past 5.x requires thorough XML round-trip testing across all schema paths
before the pin can be lifted. See the annotation in `pyproject.toml` for details.

Dev-only dependencies (`[tool.hatch.envs.test]`) are lower friction but still
require a one-line justification in the PR description.

---

## 14. License

cuems-utils is licensed under the GNU General Public License v3.0 (GPL-3.0).
By contributing, you agree that your contributions will be licensed under GPL-3.0.

All new source files MUST carry the following SPDX header:

```python
# SPDX-FileCopyrightText: <year> <Your Name or Organisation>
# SPDX-License-Identifier: GPL-3.0-or-later
```
