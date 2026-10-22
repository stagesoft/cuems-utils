<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# 017 hand-off: what is delivered, and what the maintainer does next

**Branch:** `017-release-line-reconciliation`, local and **not pushed**. It branched from
`feat/xml-refactor` at `2318dee` (the work order, on top of `5e4c637`). The last commit is the
work-order deletion (T085). Every commit on the first-parent line is GPG-signed and verifies (`G`).
No tag was created or moved, and no sibling file was edited.

## What 017 delivers

| | Result | Evidence |
|---|---|---|
| **Both release lines merged, with history** | `origin/debian/bookworm` `398a9cf` (0.1.0rc17) in `6a17392`, `origin/main` `23e4752` in `909d6f3` (empty tree diff), `v0.0.9rc7` for ancestry `-s ours` in `97ee1f9`. No `-X`, no cherry-pick. M1 was made first on the trial branch `017-m1-trial`, approved, then fast-forwarded. The 42 never-shipped paths (research R17) were removed by name | [merge-bookworm.md](merge-bookworm.md), [suite-M1.txt](suite-M1.txt), [probes-M3.md](probes-M3.md), [remeasure-start.md](remeasure-start.md) |
| **Nothing shipped is lost** | 14/14 rows of what the release line shipped are present: stop_project, media guards, stored media values, `Replaces:`, no `CACHEDIR.TAG`, and the rest | [inventory.md](inventory.md) |
| **A-1: `stop_project` takes no target** | `None` is accepted. A left-over target is repaired to `None` on load (a repairable T2 rule, reported) and refused on save. An rc17-written project loads after the two migration tools | [red-green.md](red-green.md), [suite-A-1.txt](suite-A-1.txt), [suite-A-1b.md](suite-A-1b.md) |
| **Q13: pause/resume retired** | `ActionType` has 11 values. Handover in `specs/planning/project-pause-resume-deferred.md` | [enum-audit-017.md](enum-audit-017.md), [test-retirements.md](test-retirements.md) |
| **S-3, S-4** | The migration tools report "refused on load". `python -m cuemsutils.xml.reshape_devices` runs | [red-green.md](red-green.md) |
| **Public surface** | `MediaCue` snapshotted; 14 deprecated-import modules marked `expects_deprecation` (they are R10 in the v0.1.2 removal plan) | [public-api-rehash.txt](public-api-rehash.txt), [deprecated-imports.txt](deprecated-imports.txt) |
| **Packaging** | `Replaces: cuems-engine (<< 0.1.0rc6-2~)` as row 26; the `CACHEDIR.TAG` strip pinned; relations **126/126**; `.deb` built in a bookworm chroot, `home = /usr/bin`, relative `bin/python`, built-package tests 7/7 | [verdicts-017.txt](verdicts-017.txt), [bookworm-build.txt](bookworm-build.txt), [deb-checks.md](deb-checks.md) |
| **Changelogs** | Both complete from `0.1.0rc5`, with Debian-only and never-published versions marked. `tests/packaging/test_changelog_completeness.py` keeps them so, byte for byte against the release line | [red-green.md](red-green.md) |
| **Suites** | 3.11 interleaved A/B ×3, with no new failure. 3.12 as 3.11. 3.13: +2, both pre-existing on arm A. At hand-off: **3936 passed, 114 skipped, 2 xfailed, 0 failed** | [suite-verdict.md](suite-verdict.md), `suite-[AB]-run{1,2,3}.txt`, [suite-B-py3.12.txt](suite-B-py3.12.txt), [suite-B-py3.13.txt](suite-B-py3.13.txt) |
| **Performance** (bands, interleaved A/B) | show load B/A 99.6%, suite ms/test 105.9%, descriptor warm call ~100%: all within 115% | [perf.md](perf.md) |
| **Quality** | ruff 0. mypy: 2 genuine findings fixed (`cb66cc3`); the rest is environmental and recorded | [quality-A.txt](quality-A.txt), [quality-B.txt](quality-B.txt) |
| **First-stable cleanup** (§14.1–§14.4) | `dev/` and `ToDo.md` gone; README and site on the public API only; every test in a kind directory with its marker from the directory; site deployed only from a push to `main`. The pass set is unchanged except for 3 new layout tests | [cleanup-checks.txt](cleanup-checks.txt), [cleanup-pass-set.md](cleanup-pass-set.md) |
| **The pre-publication gate** (§14.5) | `tests.yml` restructured with the `siblings_ref` input, checked statically (`tests/contract/test_ci_workflow.py`, 7/7 red → 10/10 green), actionlint clean. **Its run is owed** (step 3 below) | [ci-gate.md](ci-gate.md) (template), `contracts/ci-workflow.md` (with its measured correction) |
| **Upstream reports** (no sibling edited) | editor, frontend, engine, power-bridge, and the release-line maintainer | [`../upstream-reports/`](../upstream-reports/) |
| **Release safety** | tags, sibling heads, statuses and worktrees, and 016's 102 file hashes are identical to the start; nothing pushed; FR-036 holds (`0.1.1`, `v0.1.2`, no consumer bound moved) | [release-safety-start.txt](release-safety-start.txt), [release-safety-end.txt](release-safety-end.txt) |
| **Re-measured at hand-off** | neither release line moved; PyPI unchanged | [remeasure-handoff.md](remeasure-handoff.md) |
| **Tag message** | `../.xml-refactor-tag-messages/cuems-utils.txt` rewritten: reconciled line, items 1–5, A-1, Q13, the pre-publication line, and `Tag:` as a maintainer placeholder | (outside the repository; not under version control) |

### Findings made on the way, not in the work order

- **Two order-dependent test leaks, both older than 017**: `test_configmanager`'s `CUEMS_CONF_PATH`
  (C3), and `test_version_steps`' conversion registry (T075). Both were fixed in the tests only.
- **The seven failures recorded since `5e4c637` were stale assertions**, not defects:
  six strict xfails that the 2026-10-16 re-cut overtook, and an equality check where its docstring
  says floor (`2560b09`).
- **No integration test reads a sibling.** So the gate checks the siblings out in three jobs, and
  "reads siblings" is an explicit marker (`contracts/ci-workflow.md`, measured correction).
- **The strict docs build cannot pass yet**: 156 griffe docstring warnings, recorded in
  `cleanup-checks.txt` C2. The non-strict build has 0 errors.
- **The box clock stepped backwards during the session** (`remeasure-handoff.md`): committer
  dates are not monotonic across `cb66cc3` → `9c02cdc`.

## The maintainer's acts, in order

1. **Merge** `017-release-line-reconciliation` into `feat/xml-refactor` with `--no-ff`, signed.
   Its history includes the release lines' own commits. Of those, 78 carry signatures from two keys
   absent from this box's keyring, and one (`v0.0.9rc7`, 2025) is unsigned. That is expected.
2. **Push** `feat/xml-refactor`. Do not push `017-release-line-reconciliation` itself unless you
   want it on `origin`.
3. **Dispatch the gate** and fill [ci-gate.md](ci-gate.md):
   `gh workflow run tests.yml --ref feat/xml-refactor -f siblings_ref=xml-refactor-merge-candidate`.
   If a sibling repository is private, first create a token that can read all six and store it as
   the secret `SIBLINGS_TOKEN`, and record that you did. A run that skips `reads_siblings` tests
   does not count.
4. **Coordinate the commit to tag** with the siblings' landings and any upstream requests that
   follow from `upstream-reports/`.
5. **Fill the `Tag:` placeholder** in `../.xml-refactor-tag-messages/cuems-utils.txt`. It is the
   only edit that message needs. Then **re-cut** `xml-refactor-merge-candidate` with
   `git tag -a -f -F`. Re-check every counterpart tag: a candidate set is only as current as its
   least current member.
6. **Rule 4 for the other repositories**: each sibling reconciles its own release line
   (`specs/planning/coordinated-release-version-bump.md`), and re-cuts. Then re-run step 3 on the
   final set. **Publish only after a green gate**: the GitHub release (which triggers PyPI) and the
   `.deb` upload come after it. `0.1.0rc17` is not on PyPI. Uploading it is the release-line
   maintainer's call (`upstream-reports/release-line-hygiene.md` §3).

## Clean-up left on this box

The scratchpad worktrees `wt-a`, `wt-b`, `wt-build` and `wt-bw` (detached, under `/tmp/claude-1000/…`)
are removed after T085. They hold no commits of their own.
