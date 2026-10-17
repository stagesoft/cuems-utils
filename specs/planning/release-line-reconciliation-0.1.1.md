<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Release-line reconciliation for `cuems-utils 0.1.1` — merge before release

**Written 2026-10-17** on `feat/xml-refactor` at `5e4c637` (= `origin/feat/xml-refactor`; the
`xml-refactor-merge-candidate` tag still sits on `4b336cd`). **Status: pre-spec, decided where
§0 says so, not started.** It is the input for the next SDD feature,
**`017-release-line-reconciliation`**. Run `/speckit-specify` with Appendix A, then the rest of
the suite.

**Lifetime: temporary.** This file is a pre-spec. Once `specs/017-release-line-reconciliation/`
has absorbed it (spec, plan, research, evidence and upstream reports), it is **deleted as the final
task of 017** (§11, last step). `specs/planning/` holds only living cross-cutting documents.

**What it discharges.** Rule 4 ("merge before bump") of
[`coordinated-release-version-bump.md`](coordinated-release-version-bump.md) for this repository,
and the **NOT YET RECONCILED** section of `../.xml-refactor-tag-messages/cuems-utils.txt`. It also
answers the four obligations `cuems-engine`'s pre-spec places on this library (X-1…X-4,
`../cuems-engine/specs/planning/release-line-reconciliation-0.1.1.md` §8.1, commit `945ccba`).
**cuems-utils is the second repository to reconcile, after cuems-engine.** It still tags last.

**The one finding to read first (§6.2, S-1).** Merging rc17 puts `stop_project` into the
version-2 `ActionType` enum, and XSD validation then passes. But **the refactor's own T2 rule
`action_target_required` refuses every `stop_project` cue, at save and at load**. That includes an
rc17-written project after `cuems-reshape-devices` + `cuems-convert-documents`. So the merge alone
does **not** discharge X-1. An adaptation (A-1) is required, and its exact scope is the first
clarify question.

## 0. Decisions already taken (maintainer, 2026-10-17)

| # | Decision |
|---|---|
| D1 | This session writes a **pre-spec plus a `/speckit-specify` prompt**. It writes no code. |
| D2 | **Feature branch `017-release-line-reconciliation` off `feat/xml-refactor`.** `origin/debian/bookworm` merges in there, then `origin/main` (for the ancestry of the `v0.1.0rc17` tag), and the adaptations are made there. The branch then merges back into `feat/xml-refactor` with `--no-ff`, and the **maintainer** re-cuts the candidate tag. This is the shape of 011–016 here and of engine 009. Agents never move tags. |
| D3 | **`CHANGELOG.md` is complete from `0.1.0rc5` on, enforced by a permanent test.** Every Debian build and every PyPI release from `0.1.0rc5` (where the file starts) gets a section or a source comment. Before that, a single "Earlier releases" pointer names the git tags and PyPI. The test also checks `debian/changelog` (§7.4). |
| D4 | **The absorbed tests are ported to the public API.** rc15's, rc16's and rc17's tests drive the deprecated `XmlReaderWriter` / `Parsers` / `XmlBuilder`, which `v0.1.2` deletes, and they bypass T2. Each assertion is re-expressed through `CuemsScript.save` / `load` / `load_with_report` / `from_json`. An assertion that contradicts a settled refactor decision is **retired, and the retirement is recorded in evidence**. Today there is one: rc15's uppercase md5 normalisation, versus 014's strict rule. |
| D5 | **Which action types may have no target is left to `/speckit-clarify`** (§12 Q1). The two options: `stop_project` only, or every `*_project` value. |
| D6 (inherited) | The version **stays `0.1.1`**. Rule 4 puts the merge *under* the bump that has already been made. The top changelog entry grows; it is not renumbered. Every consumer's `>= 0.1.1`, `<< 0.1.2~` bound is unchanged. |
| D7 (inherited, rule 5) | Validation runs on the re-cut tags. Nothing waits for PyPI. |

## 1. Goal, scope, non-goals

**Goal.** `0.1.1` must carry every fix and feature released from this library's release line since
the refactor branched, so that nothing shipped in `0.1.0rc15`, `0.1.0rc16`, `0.1.0rc16+1` or
`0.1.0rc17` is lost. The xml-refactor contract of this library must hold for the absorbed code too:
- the public object API, with `cuemsutils.xml` exporting nothing;
- strict reading (T1 + T2 on every load);
- version-2 scripts with no version 3;
- `xs:boolean`;
- the device-class shape;
- typed node maps (`node_role`).

**In scope.**
- Everything reachable from `origin/debian/bookworm` and `origin/main` that is not reachable from
  `feat/xml-refactor`: source, tests, docs, packaging and changelogs.
- Adapting that content to the refactor contract.
- Re-verifying this repository's package relations, including the edge the 016 matrix misses
  (X-2).
- Rewriting the tag message (a text file only).
- The first-stable-release cleanup and the CI gate (§14).

**Not in scope.**
- Publishing (PyPI, the archive) and tag moves; both are maintainer acts.
- Any sibling's reconciliation. Siblings' obligations are written as upstream reports.
- Removing the deprecated surface. That is `v0.1.2`, in
  [`deprecated-surface-removal-v0-1-2.md`](deprecated-surface-removal-v0-1-2.md).
- New behaviour beyond what the absorbed releases and the A-items require.

**Moving target.** The release line keeps releasing. The snapshot below is what this spec measures.
The implementation **re-measures at its start and again before hand-off** (§11 steps 1 and 10), and
merges anything newer the same way.

## 2. The lines, measured 2026-10-17 (after `git fetch --all --tags --prune`)

`git remote show origin` → `HEAD branch: main`. The local `origin/HEAD → origin/main` is current.

| Ref | Commit | Date | What it is | Refactor behind / ahead |
|---|---|---|---|---|
| `feat/xml-refactor` = `origin/feat/xml-refactor` | `5e4c637` | 2026-10-17 | `0.1.1 UNRELEASED` | — |
| `xml-refactor-merge-candidate^{commit}` | `4b336cd` | 2026-10-16 | the current tag, an ancestor of HEAD | — |
| **`origin/debian/bookworm`** = tag `debian/0.1.0rc17` | **`398a9cf`** | 2026-10-15 | **the release line** (Debian), `0.1.0rc17` | **77 / 274** |
| `origin/main` = tag `v0.1.0rc17` | `23e4752` | 2026-10-15 | the upstream/PyPI line | 11 / 274 |
| `origin/release/0.1.0rc17` | `ee3de82` | 2026-10-15 | ⊂ `debian/bookworm` | 76 / 274 |
| `origin/release/0.1.0rc16` | `73ad679` | 2026-10-08 | ⊂ `debian/bookworm` | 70 / 274 |
| `origin/release/0.1.0rc15` | `7778a5b` | 2026-10-06 | ⊂ `debian/bookworm` | 65 / 274 |
| `origin/pre_release_1` | `2321a1f` | 2026-06-23 | ⊂ `debian/bookworm` | 2 / 295 |
| `origin/rc_1` | `cbab5b2` | 2026-07-28 | ⊂ HEAD | 0 / 281 |
| merge-base (HEAD, bookworm) = (HEAD, main) | `07a7f9f` | 2026-08-03 | — | — |

- **`main` ⊂ `debian/bookworm` in content.** `git diff origin/main origin/debian/bookworm -- src
  tests CHANGELOG.md` is empty. `main` has exactly one commit that bookworm lacks: `23e4752`, the
  PR #19 merge that is the `v0.1.0rc17` tag. Its content reached bookworm through `a16b610`.
- **The 77 commits are 51 non-merge and 26 merge commits.** Of the 51 non-merge commits:
  - **21** are subject-twins of commits already on HEAD. They are rebased duplicates of the 2025
    `main` history (Settings, docstrings, gh-pages, network-map schema…, and a `debian/changelog`
    bump), plus `2321a1f` (`gradient_osc_port`, twin `ae37389`) and `6f8d4c2` (duration
    validation, twin `46da65a`). `git cherry` calls them `+` only because they were re-applied onto
    different bases. **Their content is already in HEAD**, so they are history only.
  - **1** is patch-equivalent (`git cherry` `-`): `9c17418` ease_in/ease_out ↔ `7825d80`.
  - **21** are packaging and release commits (§4 rows 8–9).
  - **8** carry new content: **869fat84r** (`bdf045f`, `ef59037`, `6fcb7b5`, `4c040eb`),
    **869fej07m** (`3fa8728`), **`stop_project`** (`363eaf5`), **`Replaces:`** (`6a9d1d8`) and
    **CACHEDIR.TAG** (`c01ca36`).
- **Released entries absent from HEAD's `debian/changelog`:** `0.1.0rc17`, `0.1.0rc16+1`,
  `0.1.0rc16`. ⚠ The §10.1 `comm -13` recipe stops there, because it compares headers only. **A
  fourth entry collides:** HEAD carries `cuems-utils (0.1.0rc15) UNRELEASED`, a retrospective
  "NOT BUILT" entry describing *refactor* features. The released `0.1.0rc15 unstable`
  (869fat84r + `Replaces:`) is a different build with the same number (§7.1).
- **PyPI (queried 2026-10-17, `pip index versions cuemsutils --pre`):** the newest release is
  `0.1.0rc16`. **`0.1.0rc17` is not on PyPI**, although `v0.1.0rc17` is tagged and the `.deb`
  shipped. `0.1.0rc9`, `rc12` and `rc13` are not on PyPI either. rc9 and rc12 are Debian-only.
  rc13 exists only as a source version (`3cd860d`) and was never released anywhere. This affects
  the changelog wording (§7.2), and it also affects `cuems-engine`'s release-line floor
  `cuemsutils >= 0.1.0rc17`, which cannot be resolved from PyPI (§8.2).

## 3. Strategy: two real merges, then adaptation commits

**Measured.** `git merge --no-ff origin/debian/bookworm` into `5e4c637` stops with **11 conflicting
files and 25 hunks**:

| File | Hunks | Kind |
|---|---|---|
| `debian/changelog` | 6 | add/add |
| `debian/control` | 3 | add/add |
| `debian/rules` | 2 | add/add |
| `debian/README.Debian` | 1 | add/add |
| `CHANGELOG.md` | 1 | content |
| `src/cuemsutils/__init__.py` | 1 | content |
| `src/cuemsutils/cues/ActionCue.py` | 1 | SPDX header |
| `src/cuemsutils/cues/CueList.py` | 2 | header + 869fej07m |
| `src/cuemsutils/cues/CuemsScript.py` | 1 | header (the `get_own_media` body merges cleanly) |
| `src/cuemsutils/cues/MediaCue.py` | 5 | header + 869fat84r vs 014 |
| `src/cuemsutils/xml/schemas/script.xsd` | 2 | 869fat84r vs 014 |

The `stop_project` enumeration in `script.xsd` **merges cleanly**. Clean merges also reach
`Parsers.py`, `XmlBuilder.py`, `FadeCue.py`, `tests/test_fade_cue.py`, `CLAUDE.md` and
`debian/cuems-utils.links`.

⚠ **The merge also adds 42 tracked paths that must not land** (§4 row 10): debhelper build outputs
(`debian/.debhelper/`, `debian/cuems-utils/DEBIAN/`, `debian/files`, `*.substvars`,
`*.debhelper`, `debhelper-build-stamp`, `.pybuild/`; 20 paths with `debian/compat`),
`.python-version`, and 20 root-level files from a 2025 bus/OSC experiment (`bus_test.py`, `OSC_NODES_*.md`,
`test_osc_hub_*.py`, …). They reached bookworm through the merge commits `38d65b0` and `b71fe0c`
and through the first packaging commits. `debian/compat` beside `debhelper-compat (= 13)` is a
debhelper error that fails the build (known debhelper behaviour, not run here).

The second merge, **`git merge --no-ff origin/main`**, was measured on top of the first: it is
**clean, and its tree diff is empty**. After it, `HEAD..origin/debian/bookworm` = 0,
`HEAD..origin/main` = 0, and `v0.1.0rc17` is an ancestor.

**Methods, chosen per item.** §4 assigns one to every item.

| Method | Used for | Why |
|---|---|---|
| **M — merge** (`git merge --no-ff origin/debian/bookworm`, then `git merge --no-ff origin/main`) | everything, as the vehicle | It is the only method that makes `git rev-list --count HEAD..origin/debian/bookworm` (and `..origin/main`) reach **0**. That count is rule 4's measurable form. It keeps ancestry, so the next release-line commit merges without re-conflicting, and it brings the released changelog entries verbatim. Every `release/*`, `pre_release_1` and `debian/*` tag is an ancestor of bookworm, so they all reach 0 too. |
| **R — conflict resolution** | the 25 hunks, plus deleting the 42 stray paths | §5. Done inside the merge commit and nothing else. |
| **A — adaptation** (TDD, separate commits *after* the merge commits) | code that merged but violates the refactor contract; tests that encode rc-line assumptions; tests red on the merge commit | §6. The fix takes the absorbed code's shape, not either parent's. This is planning document §10.4's rule. |
| **C — cherry-pick** | **nothing** | It loses ancestry, so the behind-count never reaches 0 and the next merge re-conflicts. Kept as a fallback only for an item the maintainer explicitly excludes from 0.1.1. None is excluded. |

**Commit shape** (all GPG-signed; on a gpg failure, retry and never use `--no-gpg-sign`):

1. The merge commit of `origin/debian/bookworm`: the §5 resolutions and the stray deletions,
   **nothing else**.
2. The `origin/main` merge (ancestry only; empty tree diff).
3. One commit per adaptation (§6). Each fixes a test that is red on commit 1, or adds the missing
   red test first (constitution II).
4. The packaging and changelog commit (§7), including the permanent completeness test.
5. The docs commit (§9).
6. The suite and relation re-verification record.
7. The cleanup phase (§14), after the final re-fetch, one commit per sub-section.

Do **not** use `git merge -X ours/theirs`. It silently drops whole hunks of absorbed fixes.

## 4. Inventory: what the merges bring, and the method for each item

ClickUp ids in parentheses. "Released in" is the release-line `debian/changelog` entry.

| # | Item (PR) | Commits | Released in | Method | Seam on the refactor |
|---|---|---|---|---|---|
| 1 | **`stop_project` ActionType**, the authored end of an unattended show (869fhjdq5, PR #19) | `363eaf5`; `a16b610`, `ee3de82`, `23e4752` | **0.1.0rc17** (deb; tag `v0.1.0rc17`; **not on PyPI**) | M (the enum merges cleanly) + R (`ActionCue.py` header) | **A-1** (T2 + constructor refuse it, S-1/S-2), **A-2** (contract tests and schema hash), **A-3** (port its 7 tests) |
| 2 | **Media guards**: `MediaCue.media_status()`; `CueList.get_media` raises a named `ValueError` on an invalid block and skips `None`; `CuemsScript.get_own_media` never raises (869fej07m, PR #16) | `3fa8728` | **0.1.0rc16** (deb + PyPI) | M + R (`CueList` hunk 2 → theirs; headers) | **A-3**: port `tests/test_media_guards.py` (17 tests, no deprecated imports) into `tests/unit/`. Not in the public-API snapshot, because `MediaCue` methods are not snapshotted (§12 Q8) |
| 3 | **Stored media values**: `pixel_width` / `pixel_height` / `file_size` / `file_md5` (869fat84r, PR #13) | `bdf045f`, `ef59037`, `6fcb7b5`, `4c040eb` | **0.1.0rc15** | M + **R → ours** for the model and the schema: feature 014 is this item's re-implementation, with the same element names (014 decision 13) | **A-4**: retire `TestFileMd5::test_stored_lowercase` (rc15 normalises the case, 014 raises on purpose, 014 plan §10.5), and port the rest of `tests/unit/test_media_pixel_dimensions.py` (22 tests) next to `test_media_block.py`. The legacy `Parsers.py` / `XmlBuilder.py` edits merge cleanly; §12 Q5 |
| 4 | **`Replaces: cuems-engine (<< 0.1.0rc6-2~)`** for `cffi-gen-src` (PR #14) | `6a9d1d8` | **0.1.0rc15** | M + R (`debian/control` hunk 3 → both) | **A-5**: the comment block above it says "Replaces is deliberately absent". Reword it so each relation has its own reason. Add the edge to the matrix as **row 26** (X-2, §8.1) |
| 5 | **Stop shipping `/usr/lib/cuems/CACHEDIR.TAG`** (PR #18) | `c01ca36` | **0.1.0rc16+1** | M + R (`debian/rules` hunk 2 → theirs first, then ours) | **A-5**: pin it with a packaging test. HEAD's `rules` has **no** strip. 016's `.deb` had no `CACHEDIR.TAG` only because the bookworm chroot's virtualenv does not write one (016 `evidence/cuems-utils/bookworm-build.txt`). |
| 6 | ease_in/ease_out curve names | `9c17418` | (on bookworm since `pre-869fat84r-merge`) | M | none: patch-equivalent to `7825d80`, already on HEAD |
| 7 | 2025 `main` history duplicated on bookworm, plus `gradient_osc_port` and duration validation | 22 subject-twins (§2) | rc8/rc9 era | M (history only) | none. Content already in HEAD |
| 8 | Packaging history 2025-05…2026-08: dh-virtualenv, `python3-daemon` (`a5ce7a2`), triggers (`e41d610`), the `/usr/bin/python3` pin (`3ea870c`) | `a100019`…`3ea870c` | rc5…rc14 | M | none. HEAD's `debian/` already carries each of them (control `Depends`, `cuems-utils.triggers` identical, the `rules` pin), **except `debian/compat`**, which is deleted (row 10) |
| 9 | Release/version commits | `bbc44a7`, `7ce7ebf`, `2e48707`, `9e9ef43`, `117db5e`, `b08f47f`, `f027750`, `7778a5b`, `73ad679`, `ee3de82` | each | M + R (§5: version sites → ours) | §7 |
| 10 | **Bookworm-only tracked build outputs and stray root files** (42 paths, §3) | via `a100019`, `ed06e49`, `38d65b0`, `b71fe0c` | never shipped content | M + **delete in the merge commit** | Upstream note to the release-line maintainer (§8.3): stop tracking build outputs on `debian/bookworm` |
| 11 | `CHANGELOG.md` sections `0.1.0rc17`, `0.1.0rc16` | `363eaf5`, `3fa8728` | — | M + R | §7.2 |
| 12 | `CLAUDE.md` field note (the rc17 skew/rollback rule) | `363eaf5` | — | M (clean) | §9: wording says "≥ rc17" and "parses to `None` because the parsers bypass the setter". Neither is true on the public path |
| 13 | `origin/main` merge | `23e4752` | (`v0.1.0rc17` tag) | M2 | none (empty tree diff, measured) |

### 4.1 Outside both lines: stray branch heads and tags (swept 2026-10-17)

Every `origin/*` branch and every tag was checked for commits reachable from neither HEAD nor
`origin/debian/bookworm` (`git rev-list --no-merges <ref> ^HEAD ^origin/debian/bookworm`, plus
`git cherry`). **Only five refs have any.** Every other branch, including every `feat/*` and `fix/*`
head (`feat/stop-project-actiontype`, `fix/debian-replaces-engine-cffi-gen-src`,
`feat/869fat84r-media-dimensions`, the `fix/ctimecode-*` series…), is already in one of the two
lines.

| # | Ref | What | Released? | Verdict and reason |
|---|---|---|---|---|
| 14 | tag `v0.0.9rc7` `b0df231` (2025-09-05) | "fix: improve properties typing" (`CuemsScript.py`, `MediaCue.py`) | **yes**, PyPI `0.0.9rc7` | **Code: none.** `git diff v0.0.9rc7 v0.0.9rc8 -- <its two files>` is empty, so rc8 (an ancestor of HEAD) carries the content. **Changelog:** it is before `0.1.0rc5`, so D3's "Earlier releases" pointer covers it. **No** ancestry merge (§12 Q9). |
| 15 | `origin/feat/faders` `17436b0` (2026-04-27) | `docs/ctimecode-migration-for-fade-engine.md`, a briefing for the fade-engine maintainer | no | **Exclude.** The CTimecode migration it briefs has landed (features 002–003). It is engine-facing prose, and this repository's `docs/` is end-user only. |
| 16 | `origin/options` `a224e9f` (2025-02-26) | logger renames | no | **Exclude**: superseded by `log.py`'s later history |
| 17 | `origin/parser-fixxes` `8c86761` (2025-04-02) | "almost passing tests" for the legacy parser | no | **Exclude**: the legacy parser tree was deleted in 006 |
| — | `origin/gh-pages` | MkDocs deploy output (`dc2aab6`, "Deployed 23e4752") | — | not source; excluded |
| — | tags `deb0.0.9rc2`, `debian/0.1.0rc15`…`debian/0.1.0rc17`, `pre-cffi-gen-src-merge`, `pre-869fat84r-merge`, `pre-release-0.1.0rc15-merge`, `v0.1.0rc15`, `v0.1.0rc16` | reachable from bookworm | — | become ancestors through M; nothing to do |
| — | tag `v0.1.0rc17` | reachable from `main` only | yes | becomes an ancestor through M2 |

No unmerged `fix/*` or `feat/*` head newer than the release line exists today. §11 step 1
re-runs this sweep, because the release line's author works on PR branches.

## 5. Conflict resolutions (method R)

⚠ **Resolve `debian/README.Debian` with `git checkout --ours`, never with a marker-splitting
script.** Its `======================` underline begins with `=======`, so a naive resolver treats
it as the conflict separator and silently cuts the file. This happened in the trial's scratch
resolution, which had no test consequence: no test reads the file.

| File / hunk | Resolution | Reason |
|---|---|---|
| `src/cuemsutils/__init__.py` | **Ours** `__version__ = "0.1.1"`, **plus theirs'** `SPDX-FileContributor: Ion Reguera` line | D6; `test_this_repository_is_at_0_1_1` |
| `ActionCue.py`, `CuemsScript.py`, `MediaCue.py` hunk 1, `CueList.py` hunk 1 | **Theirs' three SPDX lines, then ours' imports** | The bookworm side added SPDX headers. HEAD's imports (`typing`, `re`, `Mapping`) are the refactor's |
| `CueList.py` hunk 2 (`get_media`) | **Theirs** (869fej07m `media_status()` branches) | Item 2. HEAD still has the `hasattr(cue.media, 'file_name')` guard, which never catches the `KeyError` |
| `MediaCue.py` hunks 2–5 (`_set_positive_int`, pixel/file accessors, `file_md5`) | **Ours** | 014 is the re-implementation, with the same element names. Theirs' `_get_optional` / lowercasing `set_file_md5` contradict 014's strict rule (D4, A-4) |
| `script.xsd` hunk 1 (media-block comment) | **Ours** | Same elements; 014's comment is the contract |
| `script.xsd` hunk 2 (`Md5Type` vs `CueOutputClassType`) | **Ours**, and drop theirs' `Md5Type` | HEAD already declares `Md5Type` (once, by 014's design). A second declaration is a schema error |
| `debian/control` hunk 1 | **Theirs** (SPDX header) | — |
| `debian/control` hunk 2 | **Ours** (`debhelper-compat (= 13)`, `Standards-Version: 4.6.2`) | 011 packaging hygiene |
| `debian/control` hunk 3 | **Both**: ours' `Breaks: cuems-common (<< 1.3.1~)` with its comment, then theirs' `Replaces: cuems-engine (<< 0.1.0rc6-2~)` | Relation row 1 plus item 4. The comment is reworded by A-5 |
| `debian/rules` hunk 1 | **Theirs** (SPDX) | — |
| `debian/rules` hunk 2 | **Theirs first** (the `CACHEDIR.TAG` `rm -f` directly after `dh_virtualenv`), **then ours** (011's schema/defaults install and `override_dh_installdeb`) | Item 5. The strip belongs inside `override_dh_virtualenv` |
| `debian/README.Debian` | **Ours** (`git checkout --ours`) | 011's operator README |
| `debian/changelog` (6 hunks) | Rebuild per §7.1, not hunk by hunk | — |
| `CHANGELOG.md` | Ours' `0.1.1` section on top, theirs' `0.1.0rc17` / `0.1.0rc16` sections kept; then §7.2 | — |
| the 42 stray paths (§3, item 10) | **Delete** (`git rm` in the merge commit) | not shipped; `debian/compat` breaks the build |
| clean merges into `Parsers.py` / `XmlBuilder.py` | **Keep as merged** (recommended; §12 Q5) | Rule 4: they are rc15's shipped fix for the deprecated read/write path. `file_md5` is kept a string, and the media children are written in schema order. Frozen-shim contract tests stay green with them |
| the `origin/main` merge | nothing conflicts | ancestry only |

## 6. Semantic seams (method A)

### 6.1 Measured: the merged tree versus `5e4c637`

**Environment.** Debian 13 host, kernel 6.12. Interpreter: the hatch `test.py3.11` environment
(uv-managed CPython **3.11.9**, Clang build; pytest from that environment). Each arm is a scratch
`git worktree` under the session scratchpad, with `PYTHONPATH=<arm>/src` (so `cuemsutils` resolves
to the arm, which was verified), `CUEMS_CONF_PATH` unset, and siblings at their `feat/xml-refactor`
heads. Governor `powersave`, load ≈ 1.2–1.6. Arm B is the mechanical §5 resolution, without the
`origin/main` merge, whose tree diff is empty. **Indicative, not validation evidence**: one host, no
chroot, and packaging tests that need `CUEMS_CHROOT_TAR` skip in both arms.

| Arm | Result (`pytest tests/ -q`) |
|---|---|
| A `5e4c637` | 3769 passed, **1 failed**, 134 skipped, 2 xfailed, 44.8 s |
| B merged | 3834 passed, **7 failed**, 134 skipped, 2 xfailed, 41.4 s |

Runs 2 and 3, interleaved A/B/A/B, reproduce exactly the six merged-only failures, with arm A clean
(§13).

**Common to both arms:**
`test_descriptor_laziness.py::test_no_individual_schema_regresses_where_it_is_measurable[project_mappings]`.
It is the open ~2 ms first-call flake CLAUDE.md records, so it is not a reconciliation item. ruff
0.17.0: **0 findings in both arms**. mypy was not run, because its figure on this box is disputed
(283 vs 71–72; 016 record).

**The six failures on the merged tree only**, each with its adaptation:

| Id | Failing test (owner) | Cause | Adaptation |
|---|---|---|---|
| A-2a | `contract/test_action_type.py::test_action_type_enumerates_exactly_twelve_values` (008) | `ActionType` now has 13 values | Make it **thirteen**, by name, and keep the test's purpose: no `fade_in`/`fade_out` may come back. Rename the test |
| A-2b | `contract/test_action_type.py::test_the_descriptor_publishes_exactly_those_twelve_values` (008) | The descriptor publishes 13 | Same. The frontend reads this list (015 G3), so adding `stop_project` there is the wire half of the frontend's STOP chips |
| A-2c | `contract/test_enum_audit.py::test_the_schemas_carry_no_more_and_no_fewer_than_the_retained_set` (008) | `stop_project` is not in the retained set | Add it to the retained set, with its evidence: implemented by `cuems-engine` rc6-5 (869fhjdq5) and authored by the frontend `dev` line. `specs/008-…/enum-audit.md` is frozen; the rationale lives in 017 |
| A-2d | `contract/test_schema_scope.py::test_every_schema_matches_its_recorded_hash` (feature 013/014 ratchet) | `script.xsd` changed | Update `CURRENT_SCHEMA_HASHES['script.xsd']` **in the same commit as A-1**, as the test's own message requires. **No version step**: `script` 1 → 2 is still unreleased (014's precedent) |
| A-3a | `tests/test_action_cue_stop_project.py::test_constructor_accepts_an_empty_target_and_refuses_none` (rc17) | The refactor's coercion maps `""` to `None` at construction, so `action_target == ""` never holds | Ported under D4; the assertion's intent is decided by A-1 |
| A-4 | `tests/unit/test_media_pixel_dimensions.py::TestFileMd5::test_stored_lowercase` (rc15) | rc15 lowercased an uppercase md5; 014 **raises** on purpose (`Md5Type` matches `UuidType`, 014 plan §10.5). `cuems-editor` already lowercases before assigning (its `002`, T039) | **Retire**, recorded in `evidence/test-retirements.md`. The rc15 line's own editor lowercases too (`CuemsDBMedia.py:443` on its bookworm), so no released producer depends on the normalisation |

### 6.2 Found by probing the public path, not by a failing test

The merged tree's own tests pass for these because the absorbed tests use the deprecated path,
which skips T2. Each was measured with a probe script on both arms (§13).

| Id | Probe | Arm A `5e4c637` | Arm B merged | Required |
|---|---|---|---|---|
| **S-1** | Build an `ActionCue(action_type="stop_project", action_target="")` through the public API, then `CuemsScript.save` | refused, **T1** `XsdEnumerationFacets` | refused, **T2** `action_target_required … action_target is required` | **A-1** |
| **S-1′** | **A document written by the released rc17 code** (`398a9cf`'s `XmlReaderWriter`: a VideoCue with all four media values, an AudioCue, and `stop_project` with `<action_target />`), then `cuems-reshape-devices` → `cuems-convert-documents` → `CuemsScript.load_with_report` | reshape **skips it** ("would not validate": enum) | reshape ✅, convert ✅ ("converted"), **load refused by T2** | **A-1**. This is X-1 in its field form: a project saved on an rc17 cluster is refused by every 0.1.1 node |
| control | The same rc17-written document with a `stop` cue aimed at the audio cue | reshape ✅, convert ✅, load **CLEAN** | same | none: the rc-line → 0.1.1 migration path works for everything except `stop_project` |
| **S-2** | `ActionCue({"action_type": "stop_project", "action_target": None})`, which is what the frontend `dev` line sends (`sequence.component.ts:1507`, `action_target = null`) and what the editor passes through `from_json` | raises `action_target is required` | same | **A-1** covers the constructor/setter and `from_json` too |
| **X-4** | rc17-written VideoCue/AudioCue after migration: `media.get("pixel_width")`, `media.pixel_width`, `"pixel_width" in media`, `to_wire()` | present → `int` (`file_size` 107374182400 intact), md5 `str`; **absent → `None`** via both `.get()` and the attribute; the key is not present; `to_wire` omits it. The internal `DECLARED_DEFAULTS` value is `Unset`, and it is **never exposed** | same | **Answer to cuems-engine's X-4/R-1: `None`.** The engine's "missing → probe" branch needs no `Unset` check. Pin it with one test (A-6) |
| S-3 | `cuems-convert-documents` on the S-1′ document after reshape | — | reports "converted" and writes it, **then the loader refuses it** (T2) | The tools validate T1 only before writing. Pre-existing; it is visible now because `stop_project` is the first value that is T1-valid and T2-invalid in a migrated document. After A-1 this case passes. Whether the tools should also run T2 before writing is §12 Q3, **out of scope by default** |
| S-4 | `python -m cuemsutils.xml.reshape_devices <file>` | **exits 0 and does nothing**: the module has no `if __name__ == "__main__"` guard | same | The console script `cuems-reshape-devices`, which `postinst` uses (`CUEMS_RESHAPE=/usr/lib/cuems/bin/cuems-reshape-devices`), works. `convert_documents` has the guard. Found here; §12 Q4 asks whether to fix it in 017 |

**A-1 — what has to change (scope per §12 Q1).** Introduce **one** named set of targetless
(project-scope) action types. Exactly three places consult it:
1. the T2 rule `action_target_required` (`xml/validators.py:541`), which passes `None` when
   `obj.action_type` is in the set;
2. the construction/setter guard (`ActionCue.__init__` / `set_action_target`, `enforce`);
3. through the constructor, `from_json`.

`action_target_resolves` already passes `None`. The rule stays `repairable=False`. Red tests first:
- public `save` → `load_with_report` round trip of `stop_project` with no target, outcome CLEAN,
  writing `<action_target />`;
- `from_json` with `"action_target": null`;
- **the captured rc17 fixture** (S-1′, checked into `tests/data/corpus/` with its provenance) goes
  through reshape → convert → load CLEAN;
- negative twins: `stop` with no target is still refused (T2 at save and at load), and an unknown
  action type is still refused (T1).

Whether a project-scope action that *carries* a target is accepted, cleared or refused is §12 Q2.

**A-5 — packaging pins.** Add a test that fails on `5e4c637` and passes after the merge.
- `debian/control`'s `cuems-utils` stanza has `Replaces: cuems-engine (<< 0.1.0rc6-2~)`.
- `debian/rules` strips `CACHEDIR.TAG` after `dh_virtualenv`.
- `test_built_package.py` asserts the built `.deb` has no `usr/lib/cuems/CACHEDIR.TAG`.

**A-6 — X-4 pinned.** One unit test: on a version-2 `Media` loaded with the four elements
absent, `.get(k)` and the attribute return `None` and `to_wire()` omits the keys. On one loaded with
them, the values are `int`, `int`, `int`, `str`.

## 7. Packaging, versions, changelogs

### 7.1 `debian/changelog`

This follows planning §10.1. Order is by dpkg version, highest first:

```
cuems-utils (0.1.1) UNRELEASED            ← kept; body extended (below)
cuems-utils (0.1.0rc17) unstable          ← verbatim from origin/debian/bookworm
cuems-utils (0.1.0rc16+1) unstable        ← verbatim
cuems-utils (0.1.0rc16) unstable          ← verbatim
cuems-utils (0.1.0rc15) unstable          ← verbatim — REPLACES HEAD's retrospective
                                             "0.1.0rc15 UNRELEASED / NOT BUILT" entry
cuems-utils (0.1.0rc14) … (0.1.0rc8) unstable   ← already byte-identical on both lines (measured)
cuems-utils (0.1.0rc5) … (0.0.1-0) UNRELEASED   ← keep HEAD's form (below)
```

- **HEAD's retrospective `0.1.0rc15 UNRELEASED` entry** describes refactor work (strict reading,
  `doc_version`, `node_role`, the public API, the DMX fix, duration typing), which never shipped
  as rc15. Under §10.1 rule 2, its **body is folded into the `0.1.1` entry**, and its header goes.
  The number belongs to the released build.
- **The old `UNRELEASED` entries `0.1.0rc5`, `0.0.7-31`, `0.0.7-3`, `0.0.7-2` differ between the
  lines.** HEAD added the trailer lines that bookworm's copies lack, and bookworm's file has no
  final newline. Keep HEAD's form. "Verbatim" binds *released* entries; these were never built, and
  HEAD's copies are the ones `dpkg-parsechangelog` parses cleanly. Record this as a deliberate
  exception.
- **The `0.1.1` body.** Replace the "NOT YET RECONCILED" bullet with "Reconciled with
  debian/bookworm at `<sha>` (0.1.0rc17): absorbs rc15, rc16, rc16+1, rc17", listing items 1–5
  one line each. Add A-1's targetless rule.
- Trial result: the rebuilt file parses (`dpkg-parsechangelog` top `0.1.1`, 17 entries).

### 7.2 `CHANGELOG.md` (D3)

The existing convention is one `## <version> — <date>` section per release. Measured coverage
after the merge:

| Version | Released as | `CHANGELOG.md` after merge | Required |
|---|---|---|---|
| `0.1.1` | — | top section | rewrite "Not yet reconciled" → "Reconciled…" (as §7.1) |
| two `## Unreleased — …` sections (feature 004; `hardware_outputs` rename / X14) | never | present, mid-file | **fold into `0.1.1`**: unreleased content belongs to the top entry |
| `0.1.0rc17` | deb + tag (not PyPI) | ✅ from bookworm | add "(Debian only; not published to PyPI)" if §12 Q7 confirms |
| `0.1.0rc16+1` | deb | ⛔ | `<!-- debian: 0.1.0rc16+1 (c01ca36) -->` plus one line under `0.1.0rc16` |
| `0.1.0rc16` | deb + PyPI | ✅ from bookworm | — |
| `0.1.0rc15` | deb + PyPI | ⛔ | new section, from the Debian entry |
| `0.1.0rc14` | deb + PyPI | ⛔ | new section (pynng teardown panic, interpreter pin) |
| `0.1.0rc13` | **never released** | — | none, or one line saying it was never built (§12 Q7) |
| `0.1.0rc12` | deb only | ⛔ | new section (journal dedup and priorities) |
| `0.1.0rc11` | deb + PyPI | ✅ | — |
| `0.1.0rc10` | deb + PyPI | ⛔ | new section (lxml 6.1.0, CVE-2026-41066) |
| `0.1.0rc9` | deb only | ⛔ | new section (duration validation on write) |
| `0.1.0rc8`, `rc7`, `rc6`, `rc5` | PyPI (rc8 deb too) | ✅ | — |
| `≤ 0.1.0rc4`, `0.0.*` (incl. `0.0.9rc7`) | PyPI | — | one `## Earlier releases` pointer (git tags, PyPI) |

The new sections are written **from the Debian entries' text**, which is the released record. Their
dates come from the Debian trailers.

### 7.3 `debian/control`, `debian/rules`

- Relations: row 1 (`Breaks: cuems-common (<< 1.3.1~)`) unchanged, and row 26 (`Replaces:
  cuems-engine (<< 0.1.0rc6-2~)`) new. dpkg verdicts, measured:

  | `cuems-engine` version | Replaced? | Expected |
  |---|---|---|
  | `0.1.0rc5-6`, `0.1.0rc6-1` | yes | yes |
  | `0.1.0rc6-2`, `0.1.0rc6-5`, `0.1.1-1` | no | no |

  No `Breaks:` accompanies it, as released (§12 Q6).
- `debian/rules` must carry all of: the `/usr/bin/python3` pin, the `CACHEDIR.TAG` strip, 011's
  schema/defaults install, and the `override_dh_installdeb` relabel.
- **Build** `0.1.1` in the bookworm chroot (`specs/016-…/tools/bookworm-build.sh`; never overwrite
  016's evidence) and record:
  - `Version: 0.1.1`;
  - in the `.deb`: `home = /usr/bin` and `bin/python -> ../../../bin/python3`;
  - **no `CACHEDIR.TAG`**;
  - whether `usr/lib/cuems/bin/cffi-gen-src` is present. Expected **present**: this package owns
    it, which is why it `Replaces:` the engine. Verify.

### 7.4 The permanent completeness test (D3)

`tests/packaging/test_changelog_completeness.py`. It must work without git refs, because CI may
check out shallow. So it carries the **released set as data**, and it cross-checks against git
only when the refs exist (skipping with a reason otherwise, as `tests/support/sibling_tags.py`
does):

1. `dpkg-parsechangelog` top = `__version__` = `CHANGELOG.md`'s top section.
2. `debian/changelog` headers ⊇ `RELEASED_DEBIAN` (data: `0.1.0rc8 … 0.1.0rc17`, `0.1.0rc16+1`)
   ∪, when present, the headers of `origin/debian/bookworm` ∪ every `debian/*` tag.
3. Every **released** (non-`UNRELEASED`) entry on the release line is **byte-identical** here.
   This is the check the header-only `comm` recipe lacked; it would have caught rc15.
4. No `UNRELEASED` entry except the top.
5. `CHANGELOG.md` has a section or a `<!-- debian: … -->` comment for every version in
   `RELEASED_DEBIAN` ∪ `RELEASED_PYPI` (data: PyPI ≥ `0.1.0rc5`). It has an "Earlier releases"
   pointer and exactly one `Unreleased` section (the top).

Fail-before: it must fail on `5e4c637`, where rc15/rc16/rc16+1/rc17 are missing.

### 7.5 Things that do not move

- The version (`0.1.1`, D6) and every consumer bound.
- `REMOVAL_RELEASE = "v0.1.2"`.
- `test_no_version_bump.py`'s pins of sibling versions.
- `specs/016-…` evidence. 017 writes its own.

## 8. Sibling relations, from the `xml-refactor-merge-candidate` perspective

Verdicts on the merged tree, measured, with siblings at their `feat/xml-refactor` heads
(`cuems-common ba19317`, `cuems-nodeconf 334db12`, `cuems-power-bridge 666cb25`, `cuems-engine
945ccba`, `cuems-editor a2431f0`):
`specs/016-coordinated-minor-bump/tools/verdicts.sh <parent>` → **121 verdicts, 0 FAIL**. `<parent>`
symlinked `cuems-utils` to the merged worktree. The merge moves none of the 25 rows. Re-run at
hand-off.

### 8.1 What this repository owes (and now answers)

| Id | To | Obligation | State after 017 |
|---|---|---|---|
| **X-1** | cuems-engine, cuems-editor, cuems-frontend | `0.1.1` accepts a `stop_project` cue at save **and** load, from code, from JSON (`null` target) and from an rc17-written project after migration | **Needs A-1**, not just the merge (S-1, S-1′, S-2). Once A-1 lands, the engine's strict xfails turn XPASS-strict on its next run against this tag |
| **X-2** | cuems-engine | Keep `Replaces: cuems-engine (<< 0.1.0rc6-2~)` | Arrives with the merge. **Row 26**, new in 017's own contract file (016's matrix is landed record): 017 carries `tools/verdicts-017.sh`, which runs 016's 121 plus row 26's five verdicts |
| X-3 | cuems-engine, cuems-power-bridge | Nobody ships `/usr/lib/cuems/CACHEDIR.TAG` | This package's half arrives with the merge and is pinned by A-5 |
| **X-4** | cuems-engine | `Media` absent-value semantics | **Answered, measured: `None`** (§6.2). A-6 pins it |
| — | cuems-editor | 869fej07m: `CueList.get_media` raises a named `ValueError` for an invalid media block and skips `None` with a warning | Arrives with the merge. The editor calls `project_object.get_media()` on both of its lines (`CuemsDBProject.py:1097` on `feat/xml-refactor`, `:1523` on bookworm), so its refactor line now meets the `ValueError` its release line already handles (its "save gate", rc1-5). The editor's reconciliation confirms its half |
| — | cuems-frontend | The descriptor publishes 13 action types, including `stop_project` | After the merge (A-2b) |

### 8.2 What others owe this repository, or should know

- **cuems-engine.** Its release line's floor `cuemsutils >= 0.1.0rc17` / `cuems-utils (>= 0.1.0rc17)`
  cannot be resolved from PyPI (rc17 was never uploaded). Its pre-spec already resolves both to
  `>= 0.1.1` (its §5), so nothing changes there; this is for the record.
- **cuems-editor, cuems-frontend, cuems-power-bridge.** The `stop_project` wire contract (frontend
  `dev` authors it → editor saves through this library → engine runs it → power-bridge reacts) has
  its library half here, after A-1. Each sibling's reconciliation must show its half at its re-cut
  tag. One note each under `specs/017-…/upstream-reports/`.

### 8.3 The release-line maintainer (not a sibling)

An upstream note (`upstream-reports/release-line-hygiene.md`):
- `debian/bookworm` tracks debhelper build outputs and a set of 2025 experiment files (§3), and they
  should be removed there too;
- `0.1.0rc17` was tagged and built but never published to PyPI;
- after 017, `feat/xml-refactor` contains `debian/bookworm`. **Which branch releases next** is a
  maintainer decision (§12 Q10). Until publication, anything new on the release line is merged in
  again by the same method.

This feature edits no sibling's files. Its outputs for siblings are the upstream reports and the
rewritten `../.xml-refactor-tag-messages/cuems-utils.txt` (§10).

## 9. Docs touched by the merge

- **`CLAUDE.md`.** The merged field note about `stop_project` says "since 0.1.0rc17", "≥ rc17" and
  "parses to `None` because the parsers bypass the setter".
  - Rewrite it for `0.1.1`: the value is in version-2 `script.xsd`; the project-scope target rule
    is A-1's; the skew rule becomes "every box on ≥ 0.1.1". The rollback hazard stays.
  - Rewrite the "two packaging lines" paragraph (Build section), stating the post-merge state:
    `debian/bookworm` ⊂ `feat/xml-refactor` at `<sha>`.
  - Add a Recent Changes entry for 017.
- **`ActionCue` docstring** (merged from rc17). Its "comes back as `None` after parse … assigns
  without going through the setter" describes the deprecated parser. Restate it for the public path.
- **`script.xsd` comment** on `stop_project`: fine as merged. Check that it does not claim the
  deprecated-parser behaviour.
- **Naming collision, not a defect.** `tests/contract/test_version_marker.py` says "rc17 F3"/"rc17
  F4" for the xml-rebuild series' documents, not for the `0.1.0rc17` release. 017 adds no new use
  of that shorthand.
- **`coordinated-release-version-bump.md`**, "still owed" item 1: mark `cuems-utils` reconciled,
  with the merge sha, and point at 017.
- `specs/0NN-…` (landed) are frozen and are not edited.

## 10. Acceptance criteria (for spec.md's success criteria)

1. `git rev-list --count HEAD..origin/debian/bookworm` = **0** and `HEAD..origin/main` = **0**,
   measured at hand-off against freshly fetched refs (re-merge if a line moved). `v0.1.0rc17` and
   every `debian/*` tag are ancestors of HEAD. The §4.1 sweep is re-run and every row has a verdict.
2. Every §4 item is present. One test per item, named in an evidence table, passes on the merged
   branch through the **public** API (D4).
3. The suite has **no failure that `5e4c637` does not also have**, on the same host. Runs: 3.11 ×3
   interleaved A/B; 3.12 and 3.13 once each. The six §6.1 failures are fixed, not skipped. ruff stays
   0. The mypy error set does not grow (same command on both arms).
4. **S-1, S-1′ and S-2 pass**: `stop_project` round-trips through `save`/`load_with_report` (CLEAN),
   through `from_json` with a `null` target, and through the captured rc17 fixture via reshape →
   convert → load. The negative twins stay refused.
5. X-4 is pinned by A-6. A-5's packaging tests fail on `5e4c637` and pass after.
6. No retained test imports `cuemsutils.xml.XmlReaderWriter`, `Parsers` or `XmlBuilder` unless it is
   one of the frozen-shim contract tests marked `expects_deprecation`. Every retirement is listed in
   `evidence/test-retirements.md` with its reason.
7. Relation verdicts: **121/121 + row 26's 5** (`tools/verdicts-017.sh`). The `0.1.1` `.deb`
   builds in the bookworm chroot with the §7.3 checks recorded.
8. Changelog completeness (D3) holds through the permanent §7.4 test, which failed before. The
   `0.1.1` entry and section no longer say "not reconciled".
9. The performance budgets hold (constitution IV), interleaved A/B, against **bands** not single
   lines (015's precedent):
   - the show-document load inside its band (16.465–17.750 ms) or no worse than arm A;
   - suite ms/test within 115% of arm A;
   - `script` descriptor warm call within 115% of arm A.

   One enum value and one membership test should not move any of them. If one does, record it as
   exceeded rather than restating it.
10. `../.xml-refactor-tag-messages/cuems-utils.txt` is rewritten:
    - `Tag:` names the post-017-merge head;
    - "NOT YET RECONCILED" is replaced by "Reconciled with origin/debian/bookworm at `<sha>`
      (0.1.0rc17)";
    - "Carries" gains items 1–5 and A-1;
    - "Pairs with" is unchanged unless a sibling re-cut first.

    The maintainer re-cuts.
11. Upstream reports exist (§8.2, §8.3), and the planning document's owed list points at 017.
12. The §14.6 cleanup acceptance holds.

## 11. Execution order (seed for tasks.md)

1. Fetch. Re-measure §2 (counts, the §7.4 released set, PyPI) and re-run the §4.1 sweep. Update
   this table if a line moved.
2. Create `017-release-line-reconciliation` off `feat/xml-refactor`. Run the baseline suite (arm A)
   and the performance baselines.
3. Merge `origin/debian/bookworm` with the §5 resolutions and the stray deletions. Commit. Run the
   suite and record the red set; expect §6.1's six.
4. Merge `origin/main`. Commit. Confirm the empty tree diff.
5. Adaptations, TDD, one commit each: A-1 together with A-2d (the hash); A-2a–c; A-3 (port rc17's
   and rc16's tests); A-4 (port and retire rc15's); A-5; A-6. Capture the rc17 fixture for A-1 with
   the §13 recipe.
6. Packaging: changelogs (§7.1–7.2), the completeness test (§7.4), the comment rewrite, the build
   checks, `verdicts-017.sh`.
7. Docs (§9). Upstream reports (§8).
8. Suite 3.11 ×3 interleaved A/B, plus 3.12/3.13; performance bands.
9. Re-fetch. If a line moved, merge again (loop to 3 for the delta).
10. **Cleanup phase** (§14), one commit per sub-section. Pure moves and deletes; run the suite after
    each commit and confirm the pass set is unchanged.
11. CI gate (§14.5): a green dispatched run on the 017 head, recorded.
12. Rewrite the tag message. Hand off: the `--no-ff` merge into `feat/xml-refactor`, pushing and the
    tag re-cut are maintainer acts.
13. **Final task: delete this planning file**
    (`git rm specs/planning/release-line-reconciliation-0.1.1.md`).
    - First verify that every section is traceable from `specs/017-release-line-reconciliation/`:
      FRs/SCs for §4–§10 and §14, research for §12's answers, evidence for §6 and §13.
    - Then `git grep -n release-line-reconciliation-0.1.1 -- . ':!specs/017-*'` must return
      nothing in this repository. Re-point any hit first. cuems-engine's own pre-spec has the same
      file name, in its own repository; that is not a hit.
    - 017 links to this file's last commit, so the history stays reachable.

## 12. Open questions for `/speckit-clarify`

1. **(D5) Which action types are targetless?** `stop_project` only (rc17's contract: the one
   implemented project-scope action; YAGNI) or every `*_project` value (`pause_project` and
   `resume_project` are in the schema and implemented nowhere)? *Recommendation:* `stop_project`
   only, in a named set, so adding one later is a one-line change with its own test.
2. A project-scope action that **carries** a target (for example a uuid left over from a cue edited
   from `stop` to `stop_project`): accept it as is, clear it to `None` (a repairable T2 rule), or
   refuse it? rc17 tested "the parsed target is falsy, never a uuid". *Recommendation:* accept and
   ignore it (no new rule); the engine ignores the target for project scope. A new rule is new
   behaviour.
3. Should `cuems-convert-documents` / `cuems-reshape-devices` run T2 before writing (S-3)?
   *Recommendation:* out of scope; record it in `specs/planning/` if wanted.
4. Fix the missing `__main__` guard in `xml/reshape_devices.py` (S-4) inside 017, as one line and a
   test, or defer? *Recommendation:* include it. It is small, it was found here, and
   `python -m … ` exiting 0 while doing nothing is the kind of silent success this project keeps
   removing.
5. The clean-merged rc15 edits to the frozen `Parsers.py` / `XmlBuilder.py`: keep them (rule 4, a
   shipped fix for the deprecated path that `0.1.1` still ships) or revert them to the frozen state?
   *Recommendation:* keep.
6. `Replaces: cuems-engine (<< 0.1.0rc6-2~)` without a matching `Breaks:`: keep it as released, or
   add `Breaks:` (Policy §7.6.1)? *Recommendation:* keep as released. A file moving between
   packages needs only `Replaces`, and the engine's own `cuems-utils (>= 0.1.1)` floor upgrades
   both together anyway.
7. PyPI gaps (§2): should `CHANGELOG.md` mark `0.1.0rc17` (and rc9, rc12) as "Debian only", and
   mention rc13 as never built? And does the maintainer intend to upload rc17 to PyPI at all?
8. Should `MediaCue.media_status()` (869fej07m) enter the public-API snapshot? Today `MediaCue`'s
   methods are not snapshotted, so nothing flags it. *Recommendation:* no; leave the snapshot's scope
   alone.
9. `v0.0.9rc7` (a released tag on no line): pointer only (D3), or also `git merge -s ours v0.0.9rc7`
   for ancestry so future sweeps stop flagging it? *Recommendation:* pointer only. It is one commit
   from 2025, with its content evidenced in rc8.
10. After the merge, which branch releases the next build: does `debian/bookworm` keep cutting
    `0.1.0rcN` until publication, or does it stop? This is a maintainer decision; 017 only records
    it.
11. CI (§14.5): gate on 3.11 only (bookworm's interpreter), with 3.12/3.13 informational, given that
    `test_public_api_matches_the_snapshot` fails on 3.13 in both arms (016 record)? And should the
    gate include the `.deb` build job? *Recommendation:* yes to both.
12. Cleanup (§14): `ToDo.md` — triage into `specs/planning/` or delete? `.claude/settings.local.json`
    — untrack?

## 13. How this was measured (reproducible)

```bash
git fetch --all --tags --prune
git rev-list --count HEAD..origin/debian/bookworm          # 77 (51 non-merge + 26 merges)
git rev-list --left-right --count origin/main...origin/debian/bookworm   # 1 67
git diff origin/main origin/debian/bookworm -- src tests CHANGELOG.md     # empty
git cherry -v HEAD origin/debian/bookworm | grep '^-'      # 9c17418 only
# subject twins: for each non-merge commit, git log --grep=<subject> HEAD
git merge-tree --write-tree HEAD origin/debian/bookworm    # 11 conflicted files
# stray sweep: for r in refs/remotes/origin/* refs/tags/*:
#   git rev-list --no-merges --count $r ^HEAD ^origin/debian/bookworm
pip index versions cuemsutils --pre                         # newest 0.1.0rc16
```

**Trial merge.** Scratch worktrees under the session scratchpad, all removed afterwards:
- `wt-a` at `5e4c637`;
- `wt-merge`: `--no-commit` merge, the §5 rules applied by a script (with the README.Debian
  caveat), `debian/changelog` rebuilt per §7.1, the 42 strays removed, then an unsigned scratch
  commit followed by the `origin/main` merge;
- `wt-bw` at `398a9cf`.

**Suites.** `PYTHONPATH=<arm>/src <hatch test.py3.11 python> -m pytest tests/ -q -p
no:cacheprovider`, `CUEMS_CONF_PATH` unset.

**Interleaved runs 2–3** (same environment, A, B, A, B):

| Run | Arm A `5e4c637` | Arm B merged (+ the `origin/main` merge, empty diff) |
|---|---|---|
| 1 | 3769 p / **1 f** (laziness flake) / 134 s / 2 xf, 44.8 s | 3834 p / 7 f (the six + the flake) / 134 s / 2 xf, 41.4 s |
| 2 | 3770 p / 0 f, 42.2 s | 3835 p / **6 f**, 39.3 s |
| 3 | 3770 p / 0 f, 38.4 s | 3835 p / **6 f**, 38.9 s |

The merged-only set is **the same six in every run**. The flake appeared once per arm in run 1
only. The merged tree adds 65 passing tests and **198 more warnings** (379 → 577). Those are the
absorbed tests' `DeprecationWarning`s from the legacy path, and D4's port removes them. Wall times
are not a performance verdict (§10 criterion 9 uses its own instrument).

**Probes.**
- **The rc17 fixture.** From `wt-bw`, a script written by rc17's own `XmlReaderWriter`:
  - a VideoCue with `pixel_width=1920`, `pixel_height=1080`, `file_size=107374182400` and an
    uppercase md5, which the rc15 setter lowercases;
  - an AudioCue;
  - a `stop_project` ActionCue with `action_target=""`.

  It is in the pre-013 shape, with `True`/`False`, a bare duration and no `doc_version`. The
  control document replaces the last cue with `stop` aimed at the audio cue.
- **Migration.** On each arm: `cuems-reshape-devices <file>` → `cuems-convert-documents <file>` →
  `CuemsScript.load_with_report`. The tools are invoked through `main()`, because the `python -m`
  form of reshape is a no-op (S-4).
- **Relations.** `verdicts.sh` run against a parent directory of symlinks, with `cuems-utils` →
  the merged worktree.
- `dpkg --compare-versions` for row 26.

## 14. Final phase: repository cleanup for the first stable release, and the CI gate

`0.1.1` is the first real stable release, so 017 ends with a cleanup. **It runs last, after the
final re-fetch and re-merge (§11 step 10).** Moving files earlier would turn clean release-line
merges into rename conflicts, and the merge adds three test files that the cleanup has to cover.
**No behaviour change:** each commit is a pure move, delete or rewire, and the pass set stays the
same.

A "live reference" is a path-qualified hit in `src/`, `tests/`, `debian/`, `.github/`,
`pyproject.toml`, `mkdocs.yml` or the user docs. `specs/` is frozen history and does not count.

### 14.1 Root and `dev/`

| Path | Finding | Live references | Verdict |
|---|---|---|---|
| `dev/parsers.py` (2025-04, 40 lines) | scratch for the deleted legacy parser | none | **delete** |
| `dev/test_bus_controller.py`, `dev/test_bus_node.py` (2025-10) | bus-experiment scripts; not collected (`testpaths = ["tests"]`), and the `test_` names are a trap | none | **delete**. `dev/` then no longer exists; `.gitignore`'s `dev/local` goes too |
| `ToDo.md` (2025-12) | stale list. `fade_out` was removed in 008, `ConfigManager.get_*_output_id` is 015's fossil, and the rest is triage | none | **triage → delete** (§12 Q12). Anything still true moves to `specs/planning/` |
| `.claude/settings.local.json` (tracked) | a personal permission allowlist with one developer's command history; `.local` means per-user by convention | none | **untrack** (`git rm --cached`) and ignore it. Keep `.claude/settings.json` |
| `.cursor/`, `.github/agents/`, `.github/prompts/`, `.claude/skills/`, `.specify/` | speckit tooling for each agent | used by the workflow | **keep** |
| `.vscode/` | editor settings | — | keep (team choice; not a release artefact) |
| the 42 bookworm strays | removed in the merge commit (§5) | — | already gone |

### 14.2 User docs (`README.md`, `docs/`, `mkdocs.yml`)

| Path | Finding | Verdict |
|---|---|---|
| `README.md:45-46, 71, 125-129` | presents `XmlReaderWriter` / `XmlBuilder` / `Parsers` as the way in. In `0.1.1` they are deprecated, and `v0.1.2` deletes them | **rewrite** to the public API (`CuemsScript.load/save/validate/from_json/to_wire`, `ConfigManager`, `cuemsutils.errors`) |
| `docs/index.md:41, 109-115, 172, 185` | same | rewrite |
| `docs/xml.md` | mkdocstrings pages for `cuemsutils.xml.Parsers`, `XmlBuilder` and `XmlReaderWriter`, so the published site documents the deprecated modules | replace them with the public surface |
| `README.md:254` | "`gradient_osc_port` … on `NodeType`": the old vocabulary | check, and reword to the current type name |

### 14.3 `tests/`: marked by directory

**Measured.** The layout already exists (tracked files: `unit/` 55, `integration/` 60, `contract/`
134, `packaging/` 10, plus `support/`, `data/` and `golden/`). **But 17 test modules and one
`testdev_` script still sit at `tests/` root, and no marker comes from the directory.** The only registered markers are `slow` and
`expects_deprecation`. `tests/testdev_nng_talk.py` is never collected, because `python_files`
defaults to `test_*.py`. After the merge, two more root files arrive (`test_action_cue_stop_project.py`,
`test_media_guards.py`); D4 ports them into `unit/` anyway.

| Destination | Root files (verify each at move time; signals from a grep for sockets, `pynng`, `asyncio`, threads, `tmp_path`, `/etc/cuems`) |
|---|---|
| `integration/` | `test_hubservices` (real `pynng` sockets), `test_communicatorservices` (`asyncio`), `test_logger` (threads, syslog), `test_configmanager` (touches `CUEMS_CONF_PATH` / `/etc/cuems` and sockets) |
| `contract/` | `test_version` |
| `unit/` | `test_canvas_region_roundtrip`, `test_cue`, `test_cue_output`, `test_cuelist`, `test_fade_cue`, `test_funcdict`, `test_helpers`, `test_name_coercion` (frozen-shim regression; keep its `filterwarnings` entry by updating the module path), `test_project_mappings`, `test_signalengine`, `test_superproperty`, `test_xml` (legacy-reader tests; check which are frozen-shim contracts) |
| **retire** | `testdev_nng_talk.py` (no tests; a manual NNG talk script), recorded in `evidence/test-retirements.md` |

**Wiring.**
- A `pytest_collection_modifyitems` hook in `tests/conftest.py` adds `unit` / `integration` /
  `contract` / `packaging` from the path. Register those markers.
- Add `--strict-markers`.
- A contract test asserts that every collected item carries exactly one directory marker and that
  no `tests/test_*.py` exists at the root.
- The `pyproject.toml` `filterwarnings` path for `test_name_coercion` follows the move.

**Not applicable here**: frontend tooling, a `DATA_DIR` consolidation (`tests/support/` already
centralises paths; verify at move time), and the engine's native-library stubs.

### 14.4 Other stale items

| Item | Finding | Verdict |
|---|---|---|
| `xml/reshape_devices.py` | no `__main__` guard (S-4) | §12 Q4 |
| `.github/workflows/gh-pages.yml` | runs `mkdocs gh-deploy --force` on **every `pull_request` and every dispatch, from any ref**. A PR from `feat/xml-refactor` would publish the refactor's docs, and its deprecated pages, to the live site | **gate** the deploy on `push` to `refs/heads/main` (§14.5) |
| `.github/workflows/pypi-publish.yml` | the test step is commented out; it publishes on any GitHub release | keep the trigger. Add the pre-publication checklist line (§14.5), and optionally `needs:` a test job |

### 14.5 CI: the pre-publication gate, run manually in the cloud

**Measured constraints.**
- **`workflow_dispatch` only works for a workflow file that exists on the default branch**
  (`main`). `main` holds `tests.yml`, `gh-pages.yml` and `pypi-publish.yml`, and `tests.yml`
  already declares `workflow_dispatch`. So `gh workflow run tests.yml --ref <017 or
  feat/xml-refactor>` runs **that ref's version** of the file. ⇒ **Keep the file name `tests.yml`**
  and restructure the jobs inside it. A new file could not be dispatched until it reached `main`.
- **Triggers today:** `push` → `[main]`, `pull_request` → all, `workflow_dispatch`. Add
  `feat/xml-refactor` to `push`.
- **No PyPI dependency.** This is the library itself, so CI builds it from the checkout. The
  analogue of the engine's `cuemsutils_ref` is the reverse direction: **the cross-repository tests
  skip in hosted CI** (`tests/support/sibling_tags.py`: "checkout absent → skip, with a reason"), so
  the gate must check the siblings out to make them run. Add a dispatch input `siblings_ref`
  (default `xml-refactor-merge-candidate`). The job checks out the six siblings at that ref beside
  this repository (with tags) and reports how many sibling-reading tests ran versus skipped.
- **Lock file:** none (hatch resolves from `pyproject.toml`). Record the resolved `xmlschema` /
  `lxml` versions in the job summary, because `xmlschema==3.4.3` is pinned and `lxml==6.1.0` too.
- **Matrix:** `hatch run test:run-cov` runs 3.11, 3.12 and 3.13. 3.13 has a pre-existing failure in
  both arms (`test_public_api_matches_the_snapshot`), so **gate on 3.11** and keep 3.12/3.13
  informational (`continue-on-error`) until that is fixed (§12 Q11).

**Job layout** (inside `tests.yml`):

| Job | Needs | Runs | Notes |
|---|---|---|---|
| `lint` | — | `hatch run test.py3.11:lint` (ruff 0) | — |
| `unit` | lint | `pytest tests/unit tests/contract -m "not slow" --cov` on 3.11 | uploads `.coverage.unit` |
| `integration` | lint | `pytest tests/integration -m "not slow" --cov` on 3.11 | in parallel with `unit`; uploads `.coverage.integration` |
| `packaging` | lint | in a `debian:bookworm` container: `dpkg-buildpackage -us -uc -b`; the §7.3 checks (`home = /usr/bin`, no `CACHEDIR.TAG`, `Version` = changelog); `pytest tests/packaging` without the chroot tests | §12 Q11 |
| `coverage` | unit, integration | `coverage combine` + `report`, then Codecov | the threshold applies to the **combined** number. Upload only on `main` |
| `matrix-info` | lint | 3.12, 3.13 | `continue-on-error: true` |
| `gate-summary` | all | the job summary: utils SHA, `siblings_ref` and each sibling's commit, pass/skip/xfail counts, the strict xfails, the sibling-test ran/skipped count | the record that evidence links to |

**No deploy from non-release refs.** Gate `gh-pages` on `github.event_name == 'push' && github.ref
== 'refs/heads/main'`, and gate Codecov the same way.

**The gate itself.**
- **Before 017 hands off:** one dispatched run on the 017 head SHA must be green, with
  `siblings_ref` set to the current candidate tags. Record the run URL, SHA and summary in
  `specs/017-…/evidence/ci-gate.md`.
- **Before publication:** another dispatched run on the post-merge `feat/xml-refactor` head, with
  every sibling at its **reconciled** re-cut tag. This is a maintainer act, after 017, and it gates
  `pypi-publish.yml` (a GitHub release) and the `.deb` upload. Write that checklist line into the
  tag message and into `CONTRIBUTORS.md`'s release section.

### 14.6 Acceptance for the cleanup phase

- `dev/` does not exist. `ToDo.md` is triaged. `.claude/settings.local.json` is untracked and ignored.
- `git grep -nE "dev/parsers|test_bus_(controller|node)|testdev_nng_talk" -- . ':!specs'` returns
  nothing.
- No `tests/test_*.py` remains at the root. Every collected test carries exactly one directory
  marker, asserted by a contract test.
- `pytest tests/unit tests/contract` passes without network.
- The pass set is identical before and after, apart from the listed retirements.
- README and `docs/` name only the public API, and the published site has no deprecated module
  pages.
- `tests.yml` (same file name) has the §14.5 jobs and the `siblings_ref` input. **A
  `workflow_dispatch` run on the 017 head SHA is green**, with its URL, SHA, sibling commits and
  counts in `evidence/ci-gate.md`. A dispatch or a PR does not deploy `gh-pages` or upload coverage.
- **Tell the release-line maintainer about the layout and the CI.** The release line keeps adding
  tests at the root of `tests/` (all three absorbed test files did), and every future reconciliation
  has to re-file them. Add a short note to `CONTRIBUTORS.md`'s testing section, plus §8.3's upstream
  note.

---

## Appendix A — paste-ready `/speckit-specify` prompt

> Feature `017-release-line-reconciliation` for cuems-utils. Branch off `feat/xml-refactor`
> (`5e4c637`, version `0.1.1` UNRELEASED; the candidate tag is on `4b336cd`).
>
> **Goal.** Absorb this library's release line `origin/debian/bookworm` (`398a9cf`, `0.1.0rc17`,
> 77 commits behind) and `origin/main` (`23e4752`, tag `v0.1.0rc17`) into the refactor before
> `0.1.1` is published ("merge before bump", rule 4 of
> `specs/planning/coordinated-release-version-bump.md`). Nothing shipped in `0.1.0rc15`, `rc16`,
> `rc16+1` or `rc17` may be lost, and the absorbed code must obey the refactor's contract: the
> public object API, strict T1+T2 reading, version-2 scripts with no version 3, `xs:boolean`, the
> device-class shape.
>
> **The work order** is `specs/planning/release-line-reconciliation-0.1.1.md`. Use:
> - its decisions D1–D7: branch 017 merged back with `--no-ff`; `CHANGELOG.md` complete from
>   `0.1.0rc5` with a permanent test; absorbed tests ported to the public API; the targetless
>   action set decided in clarify; the version stays `0.1.1`;
> - its inventory (§4: 13 items, each with a method of merge, conflict resolution or adaptation;
>   cherry-pick for none) and its stray sweep (§4.1: `v0.0.9rc7`, `feat/faders`, `options`,
>   `parser-fixxes`, all with verdicts);
> - its conflict rules (§5: 11 files, 25 hunks, plus deleting 42 bookworm-only build outputs and
>   strays, including `debian/compat`);
> - its measured seams (§6: six tests red on the merged tree, A-2a–d, A-3a, A-4). The headline is
>   **S-1**: the merge adds `stop_project` to the v2 `ActionType`, but T2's
>   `action_target_required` refuses it at save and load, including an rc17-written project after
>   reshape + convert, and the constructor refuses the frontend's `null` target. So adaptation
>   **A-1** introduces one named set of targetless action types consulted by the T2 rule, the
>   construction guard and `from_json`, test-first, with a captured rc17 fixture.
> - its packaging and changelog shape (§7): bookworm's `rc15`/`rc16`/`rc16+1`/`rc17` entries
>   verbatim, HEAD's retrospective `rc15 UNRELEASED` folded into `0.1.1`, `Replaces: cuems-engine
>   (<< 0.1.0rc6-2~)` kept as new relation row 26, the `CACHEDIR.TAG` strip pinned by a test, the
>   bookworm build checks;
> - its sibling obligations (§8: X-1 needs A-1; X-2; X-3; X-4 answered as `None`; notes to the
>   editor, frontend and power-bridge; the release-line hygiene note);
> - its acceptance criteria (§10, including §14.6) and its execution order (§11).
>
> **Final phase: the first-stable-release cleanup (§14).**
> - Delete `dev/`. Triage `ToDo.md`. Untrack `.claude/settings.local.json`.
> - Rewrite README and `docs/` to the public API, and drop the deprecated modules' mkdocstrings
>   pages.
> - Move the 17 root test modules into `unit/` / `integration/` / `contract/`, with markers applied
>   from the directory, `--strict-markers` and a contract test. Retire `testdev_nng_talk.py`.
> - Gate `gh-pages` and Codecov to pushes on `main`.
> - Restructure `tests.yml` (same file name, because dispatch needs it on `main`) into parallel
>   `lint` / `unit` / `integration` / `packaging` (`debian:bookworm` `.deb` build) / `coverage` /
>   `gate-summary` jobs, gating on 3.11. Add a `siblings_ref` dispatch input so the
>   cross-repository tests run instead of skipping.
> - Record a green `workflow_dispatch` run on the 017 head as evidence.
>
> **Last task.** The final task of `tasks.md` deletes the planning file once 017's artefacts carry
> all of its content (§11 step 13).
>
> **Clarify list and limits.** Treat §12 as the clarify list. Out of scope: publishing, tag moves,
> pushes, sibling edits (write upstream reports), the `v0.1.2` removal, and new behaviour beyond A-1.
>
> **Constitution.** TDD (every adaptation starts from a red test), performance budgets as bands with
> interleaved A/B, no new runtime dependency, actionable errors. Planning artefacts go under
> `specs/017-release-line-reconciliation/`, evidence under its `evidence/`, upstream reports under
> its `upstream-reports/`, and 016's evidence is never overwritten.
