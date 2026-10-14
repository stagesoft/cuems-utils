<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# The coordinated xml-refactor landing cuts a stable minor release in **every** repository

**Decided 2026-10-12** by the development team. Parallel bugfix and small-feature work is being
released from every repository's own line, so the refactor cannot merge under a version number any
of them still holds. **Status: decided, not executed.** This document is the work order — the
measured target version for each repository, every versioned package relation that moves with it,
and the file inventory in this repository.

## The decision, in four rules

1. **Every affected repository moves to its own next stable minor at the coordinated
   `xml-refactor-merge-candidate` landing** — not just `cuems-utils`. The last component of the
   upstream version advances, any `rc` suffix is dropped, and the Debian revision resets to `-1`.
   Examples given by the team: `cuems-common` → **`v1.3.1`**, `cuems-nodeconf` → **`v0.1.1`**.
2. **`cuems-utils` cuts `0.1.1` directly** — no `0.1.1~rc1` (settled 2026-10-12). That is what makes
   a plain `>= 0.1.1` the correct consumer floor.
3. **The deprecated-surface removal moves with it**, `v0.1.1` → **`v0.1.2`**. That work is
   [`deprecated-surface-removal-v0-1-1.md`](deprecated-surface-removal-v0-1-1.md), which this
   decision renames (§7).
4. **Merge before bump.** Every fix already released from a parallel line is absorbed into the
   refactor branch before the new version is published, so nothing shipped is lost. The version entry
   becomes the newest/top changelog entry; everything the parallel lines keep adding until
   publication is absorbed as part of each repository's reconciliation — §10.

**It reverses three standing decisions**, each recorded where it was made rather than quietly
overwritten: §12/§12.1 of [`etc-cuems-first-install.md`](etc-cuems-first-install.md) ("the library
version stays at `0.1.0rc16`" / "why not `0.1.1`"), §0a of
[`upcoming-feature-requirements-2026-10-02.md` *(deleted 2026-10-14, feature 015; in git history)*](../015-consumer-gate-closure/spec.md) ("the
version does not move for this tag"), and decision 2 of
`specs/014-xs-boolean-and-media-elements/plan.md` ("the branch stays on rc16").

---

## 1. Why the versions have to move: three collisions, measured

The refactor branches have been holding version numbers that the release lines have since **taken
and shipped**. Measured 2026-10-12 after fetching every sibling.

| Repo | Branch holds | Parallel line released | Same commit? | Verdict |
|---|---|---|---|---|
| `cuems-utils` | `0.1.0rc16` (UNRELEASED) | `v0.1.0rc16`, and a revision `debian/0.1.0rc16+1` | ❌ no | **collision** |
| `cuems-common` | `1.3.0-23` (UNRELEASED) | `v1.3.0-23` (`8109884`, 2026-10-07), then `-24`, `-25` | ❌ no | **collision** |
| `cuems-editor` | `0.1.0rc1-4` (UNRELEASED) | `v0.1.0rc1-4` (`faaa626`, 2026-10-06), then `-5`, `-6`, `-7` | ❌ no | **collision** |
| `cuems-engine` | `0.1.0rc2-3` (`bookworm`) | nothing tagged; packaging exists only on the refactor branch | — | no collision |
| `cuems-nodeconf` | `0.1.0-8` (UNRELEASED) | nothing tagged | — | no collision |
| `cuems-power-bridge` | `0.3.1-1` (`unstable`) | `v0.3.0-10`, which sorts **below** it | — | no collision |

**The released commits are not ancestors of the refactor branches**, verified for all three
collisions. So a user with `cuems-common 1.3.0-23` installed has a package that shares a version
number with the `/etc/cuems` handover and contains none of it.

All three are resolved by **§10.1 rule 2**: the colliding `UNRELEASED` header is dropped and its body
folded into the new top entry, so the contested numbers stay with the builds that actually shipped
under them.

### 1.1 One collision had already defeated a `Breaks:` — and the bump is what fixes it

`cuems-utils`' own [debian/control:23](../../debian/control#L23) reads
`Breaks: cuems-common (<< 1.3.0-23~)`. Feature 011 wrote it so that a `cuems-common` predating the
handover cannot sit beside this package and claim `/etc/cuems/network_map.xml` as its own conffile.

Released `1.3.0-23`, `-24` and `-25` **satisfy that `Breaks:` while carrying no handover at all** —
the relation names a version, the version got reused, and the relation went quiet instead of
failing. Same shape as the `>= 0.1.0rc16` floor in §2.

**The minor bump resolves it, provided the relation moves with the version.** Verified with
`dpkg --compare-versions`:

| `cuems-common` version | `Breaks: (<< 1.3.0-23~)` — today | `Breaks: (<< 1.3.1~)` — proposed |
|---|---|---|
| `1.3.0-22` | correctly refused | correctly refused |
| `1.3.0-23`, `-24`, `-25` *(released, no handover)* | ⛔ **admitted — the defect** | ✅ correctly refused |
| `1.3.1~rc1`, `1.3.1-1` *(the handover)* | admitted | ✅ admitted |

So this is not a separate repair to schedule — it is **§4's relation matrix doing its job**, and the
reason the matrix cannot be skipped as cosmetic.

## 2. `0.1.0rc16` is released, and carries none of the migrated API

The `cuems-utils` row of §1 deserves its own statement, because five sibling floors rest on it.
`origin/main` and `origin/release/0.1.0rc16` both declare `__version__ = "0.1.0rc16"`, there are
`debian/0.1.0rc15`, `debian/0.1.0rc16` and `debian/0.1.0rc16+1` tags — and that released tree
contains **no** `tools/init_node.py`, **no** `xml/descriptor.py`, **no** `xml/reshape_devices.py` and
not even `_deprecation.py`.

So `cuems-utils (>= 0.1.0rc16)` is today satisfied by a library with neither the public object API
nor any entry point the consumer flows were migrated onto. **The floor is already broken**; moving
to `0.1.1` repairs it. This also retires feature 010's **T090** premise — *"sound because rc16 was
never released"* — true when written, false now.

## 3. Target versions

| Repo | Upstream now | Released high-water | Debian now (refactor branch) | **Target** | Version sites to edit |
|---|---|---|---|---|---|
| `cuems-utils` | `0.1.0rc16` | `v0.1.0rc16` (+`+1`) | `0.1.0rc16` *(native, no revision)* | **`0.1.1`** | `src/cuemsutils/__init__.py:4`, `debian/changelog:1` |
| `cuems-common` | `1.3.0` | `v1.3.0-25` | `1.3.0-23` ⚠ | **`1.3.1-1`** | `debian/changelog:1` *(no Python version in this repo)* |
| `cuems-engine` | `0.1.0rc7` | *(none tagged)* | `0.1.0rc2-3` ⚠ **disagrees with source** | **`0.1.1-1`** | `pyproject.toml:11`, `src/cuemsengine/__init__.py:5`, `debian/changelog:1` |
| `cuems-editor` | `0.1.0rc1` | `v0.1.0rc1-7` | `0.1.0rc1-4` ⚠ | **`0.1.1-1`** | `pyproject.toml:7`, `src/cuemseditor/__init__.py:4`, `debian/changelog:1` |
| `cuems-nodeconf` | `0.1.0` | *(none tagged)* | `0.1.0-8` | **`0.1.1-1`** | `pyproject.toml:7`, `debian/changelog:1` |
| `cuems-power-bridge` | `0.3.1` (pyproject) / **`0.2.0`** (`__init__`) ⚠ | `v0.3.0-10` | `0.3.1-1` | **`0.3.1-1`** — already correct | `src/cuemspowerbridge/__init__.py:5` **only**, to reconcile |
| `cuems-frontend` | `0.0.0` (`package.json`, name `formitgo-tw`) | *(none)* | not packaged, no `debian/` | **decision needed** — §9.1 | `package.json:3` |

**`cuems-power-bridge` is the only repository already at its target**, because `13a9af4` bumped it
to `0.3.1` in September. It still needs the `__init__.py` reconcile and every relation in §4.

### 3.1 Three pre-existing version drifts the bump must reconcile, not inherit

Found while measuring; none is caused by this decision, and all three are cheapest to fix in the
same commit as the bump:

| Repo | Drift |
|---|---|
| `cuems-engine` | `debian/changelog` says `0.1.0rc2-3`; `pyproject.toml` and `src/cuemsengine/__init__.py` both say `0.1.0rc7`. The package and the module have never agreed |
| `cuems-power-bridge` | `pyproject.toml` says `0.3.1`; `src/cuemspowerbridge/__init__.py` says **`0.2.0`** — a whole minor behind |
| `cuems-frontend` | `package.json` has never left `0.0.0`; there is no tag and no package, so nothing anywhere states what it ships |

Feature 010's FR-092 reconciled `cuems-engine`'s two disagreeing *dependency bounds*. Nothing has
ever reconciled these **self**-versions.

## 4. The relation matrix — every versioned package edge

**20 versioned sites across six `debian/control` files and four `pyproject.toml` bounds.** This is
the part that cannot be done per repository in isolation: a version move with the relations left
behind is an ecosystem `dpkg` refuses to install.

### 4.1 Edges naming `cuems-utils` → `>= 0.1.1`, `<< 0.1.2~`

| Repo | `debian/control` | `pyproject.toml` |
|---|---|---|
| `cuems-common` | `:12`, `:13` | — |
| `cuems-engine` | `:26`, `:27` | `:50` `>=0.1.1,<0.1.2` |
| `cuems-editor` | `:18`, `:19` | `:27` |
| `cuems-nodeconf` | `:18`, `:19` | `:28` |
| `cuems-power-bridge` | `:18`, `:19` | `:38` |

Verified with `dpkg`: the pair refuses every `0.1.0rcN` (including the released `rc16` and
`rc16+1`), admits `0.1.1` with Debian revisions, and refuses `0.1.2~rc1`, `0.1.2` and `0.2.0`.
`0.1.2` is the removal release, so the ceiling still refuses exactly the library version that would
break an unmigrated consumer at runtime.

⚠ **`<< 0.2.0~` is wrong** — both `deprecated-surface-removal-v0-1-1.md` §3 and
`upcoming-feature-requirements-2026-10-02.md` *(deleted 2026-10-14, feature 015; in git history)* §3 propose it, and it would admit `0.1.2`, the release
that deletes the surface the ceiling exists to protect. It is `<< 0.1.2~`.

### 4.2 Edges naming `cuems-common` → `1.3.1`

| Repo | Site | Today | Becomes |
|---|---|---|---|
| **`cuems-utils`** | `debian/control:23` | `Breaks: (<< 1.3.0-23~)` | `Breaks: (<< 1.3.1~)` — §1.1, and the comment at `:15-22` explaining *why* `1.3.0-23` must be rewritten with it |
| `cuems-engine` | `debian/control:28` | `Depends: (>= 1.3.0-23~)` | `>= 1.3.1~` |
| `cuems-editor` | `debian/control:20` | `Depends: (>= 1.0.0)` — **stale** | `>= 1.3.1~` |
| `cuems-nodeconf` | `debian/control:20` | `Depends: (>= 1.0.0)` — **stale** | `>= 1.3.1~` |
| `cuems-nodeconf` | `debian/control:28` | `Breaks: (<< 1.3.0-23~)` | `<< 1.3.1~` |
| `cuems-power-bridge` | `debian/control:20` | `Depends: (>= 1.3.0-23)` | `>= 1.3.1~` |
| `cuems-power-bridge` | `debian/control:25` | `Breaks: (<< 1.3.0-23)` | `<< 1.3.1~` |

The two `>= 1.0.0` floors in `cuems-editor` and `cuems-nodeconf` are stale independently of this
decision — they admit a `cuems-common` from before the node-identity contract existed.

### 4.3 Edges naming `cuems-nodeconf` → `0.1.1`

| Repo | Site | Today | Becomes |
|---|---|---|---|
| `cuems-common` | `debian/control:57` | `Breaks: cuems-nodeconf (<< 0.1.0-8)` | `<< 0.1.1~` |

Verified: `<< 0.1.1~` marks `0.1.0-8` too old and admits both `0.1.1~rc1` and `0.1.1-1`.

### 4.4 Edges naming `cuems-power-bridge` and `cuems-engine`

| Repo | Site | Today | Becomes |
|---|---|---|---|
| `cuems-common` | `debian/control:58` | `Breaks: cuems-power-bridge (<< 0.3.1-1)` | **unchanged** — the bridge is already at its target |
| `cuems-common` | `debian/control:49` | `Suggests: cuems-power-bridge`, **unversioned** | **unchanged, deliberately** — 010 T077's decision; promoting it would make a controller-only opt-in feature mandatory on every node |
| `cuems-engine` | `debian/control:49` | `cuems-engine-mock Depends: cuems-engine (>= 0.1.0rc2)` | `>= 0.1.1` — moves with its own package |

## 5. This repository — code

| File | Line(s) | Current | Becomes |
|---|---|---|---|
| `src/cuemsutils/__init__.py` | 4 | `__version__ = "0.1.0rc16"` | `"0.1.1"` — also the `[tool.hatch.version]` source (`pyproject.toml:73-74`), so wheel and sdist follow with no second edit |
| `src/cuemsutils/_deprecation.py` | **26** | `REMOVAL_RELEASE = "v0.1.1"` | `"v0.1.2"` — **the load-bearing one**: it rewrites every warning the package emits, from one place |
| `src/cuemsutils/_deprecation.py` | 11, 25 | prose naming `v0.1.1` | `v0.1.2` |
| `src/cuemsutils/timeoutloop.py` | 5 | "removed in `v0.1.1`" | `v0.1.2` |
| `src/cuemsutils/tools/CTimecode.py` | 224 | docstring `(``v0.1.1``)` | `v0.1.2` |
| `src/cuemsutils/xml/xml_reader_writer.py` | 205 | "removed at `v0.1.1` regardless" | `v0.1.2` |
| `src/cuemsutils/xml/XmlReaderWriter.py` | 4 | "Removed in `v0.1.1`" | `v0.1.2` |
| `src/cuemsutils/xml/Settings.py` | 4 | "Removed in `v0.1.1`" | `v0.1.2` |
| `src/cuemsutils/xml/CMLCuemsConverter.py` | 4 | "Removed in `v0.1.1`" | `v0.1.2` |
| `src/cuemsutils/xml/__init__.py` | 14 | `v0.1.1` | `v0.1.2` |

Line numbers measured 2026-10-12 on `014-xs-boolean-and-media-elements` (the integration branch —
`feat/xml-refactor` itself is still at `0.1.0rc14` with no `debian/`). Re-grep rather than trust
them.

## 6. This repository — tests

| File | Line(s) | What breaks | Required change |
|---|---|---|---|
| `tests/packaging/test_no_version_bump.py` | 17, 30-31, docstring, test name | Pins the changelog head **and** `__init__.py` at `0.1.0rc16`. Its premise ("no package version moves") is reversed, and `test_this_repository_stays_at_rc16` is false **by its own name** | Re-pin to `0.1.1`; rewrite the docstring; rename the test. Do **not** delete it — it is what makes a stray bump fail the suite rather than review |
| `tests/packaging/test_no_version_bump.py` | 17 | Also pins `cuems-common: 1.3.0-23` and `cuems-nodeconf: 0.1.0-8` — **both now move** (§3) | Re-pin to `1.3.1-1` and `0.1.1-1`. Consider adding the other three siblings, since the pin set is now the release matrix |
| `tests/contract/test_deprecation_shims.py` | 171 | `assert REMOVAL_RELEASE == "v0.1.1"` | `"v0.1.2"` |
| `tests/unit/test_ctimecode.py` | 403, 406 | `assert REMOVAL_RELEASE == "v0.1.1"` + docstring. It exists **precisely so a move surfaces here** — working as designed | `"v0.1.2"` |
| `tests/contract/test_validate_advice_per_schema.py` | 91 | `assert "removed in v0.1.1" in _advice(...)` — a **literal**, not derived | `v0.1.2`; better, derive from `REMOVAL_RELEASE` |
| `tests/test_version.py` | — | **No change.** Verified: `"0.1.1"` splits to `['0','1','1']` and passes `is_zero_or_digit`/`is_alpha_beta_rc` | none |

Three further tests reference `REMOVAL_RELEASE` **by symbol** and need nothing
(`test_deprecation_shims.py:166,254`, `test_timeout_loop_deprecation_shim.py:41`). That is the
correct pattern; the two literal sites above are the exceptions.

## 7. This repository — the removal document, packaging and user docs

| File | Line(s) | Change |
|---|---|---|
| `specs/planning/deprecated-surface-removal-v0-1-1.md` | **21 sites** | `git mv` to `…-v0-1-2.md`; retitle; §1.1's `dpkg` table re-derived (§4.1 supersedes it); §1.2's "wrong in the other direction" argument rebased on `v0.1.2`; §3's atomic step **no longer belongs there** — it fires at this landing; §5 item 1's struck question re-opens as "is `0.1.2` the first release after a stable one?"; §7's rendered example message |
| …the **14 files citing that filename** | 14 | `git grep -l deprecated-surface-removal-v0-1-1` — two are **not documents**: `src/cuemsutils/tools/CTimecode.py` and `tests/unit/test_ctimecode.py` |
| `debian/changelog` | 1 | `(0.1.0rc16) UNRELEASED` → `(0.1.1)`. It **cannot** keep `0.1.0rc16` — §2 |
| `debian/changelog` | 94-95 | "REMOVED IN v0.1.1, which is why every consumer pins `<< 0.1.1~`" — both halves wrong |
| `debian/control` | **23** | `Breaks: cuems-common (<< 1.3.1~)` + the comment at `:15-22` — §1.1, §4.2 |
| `CHANGELOG.md` | 3 | the `## Unreleased` heading becomes the `0.1.1` release heading, dated |
| `CHANGELOG.md` | 96 | "removed in `v0.1.1`" → `v0.1.2` |
| `README.md` | 117 | `TimeoutLoop` note → `v0.1.2` |
| `docs/index.md` | 103 | same note → `v0.1.2` |
| `debian/README.source` | 11 | narrates the rc14→rc16 packaging gap; add the rc-line split (optional, recommended) |
| `CLAUDE.md` | 202-211, 333, 635 | the `v0.1.1` version move, the `<< 0.1.1~` gate reasoning, "gone in `v0.1.1`"; the candidate-tag record (§9); a "Recent Changes" entry for this decision |

## 8. This repository — planning and in-progress specs

**Editable.** Highest risk first: the top three are instructions other flows execute, so a stale
line there gets *run*, not merely read.

| File | Sites | What has to change |
|---|---|---|
| `specs/planning/feature-014-sibling-gate-prompt.md` *(deleted 2026-10-14, feature 015; in git history)* | 111-113, 134, 477 | the check `expect: 0.1.0rc16` and **"Do not bump any version or dependency bound"** — handed to sibling flows, the most dangerous stale instruction in the set |
| `specs/planning/upcoming-feature-requirements-2026-10-02.md` *(deleted 2026-10-14, feature 015; in git history)* | 44-54, 225, 233, 238-254, 280 | §0a's **"The version does not move for this tag"**, its "do not propose an `rc17`", and its "§3 belongs to a later release and is unaffected". §3's ceiling → `<< 0.1.2~`. §0a is the current work order for the tag, so correct it first |
| `specs/planning/etc-cuems-first-install.md` | 959, 1327-1360 | **§12 and §12.1 are the decision being overturned** — rewrite. §12.1's two reasons were sound and are now *resolved*: `REMOVAL_RELEASE` moves with the version, and the ceilings re-bind in the same step |
| `specs/planning/etc-cuems-first-install-execution.md` | 25, 92-94, 285, 640-641 | "Do not move the library version off `0.1.0rc16`" reverses |
| `specs/planning/refactor-sequencing-2026-10-01.md` *(deleted 2026-10-14 by feature 015, T110; its residue is `adoption-liveness-ui-tier.md`; recoverable from git history)* | 30, 77, 108, 223 | §2's hostage argument and "if `v0.1.1` is not wanted soon" both resolve |
| `specs/planning/editor-001-amend-after-013-prompt.md` *(deleted 2026-10-14, feature 015; in git history)* | 279 | "Do not lower `cuemsutils>=0.1.0rc16,<0.1.1`" → it is now *raised* |
| `specs/planning/editor-specify-prompt.md` *(deleted 2026-10-14, feature 015; in git history)* | 156 | the `v0.1.1` move reference |
| `specs/planning/tools-external-consumers-and-timeoutloop-migration.md` | 216 | `REMOVAL_RELEASE` quote; R6's coordination point |
| `specs/planning/stored-media-values-preimplementation.md` *(deleted 2026-10-14, feature 015; in git history)* | 142, 203, 237 | quoted sibling pins; the "rc15 must be on PyPI first" precondition now reads against `0.1.1` |
| `specs/planning/media-pixel-dimensions-for-xml-refactor.md` *(deleted 2026-10-14, feature 015; in git history)* | 156 | engine pin quote (low) |
| `specs/planning/xml-rebuild/010-consumer-prompts/00-cuems-utils.md` | 28, 119, 245 | plus single-line hits in `01`, `02`, `03`, `04`, `04a`, `04b`, `07`, `README.md` |
| `specs/010-consumer-migration/contracts/release-gate.md` | **18** | the gate contract itself — its `dpkg` table and every "closed edge" verdict assume `<< 0.1.1~` |
| `specs/010-consumer-migration/baseline.md` | **19** | incl. §T090 ("inside `0.1.0rc16`, no bump" — §2 retires its premise) and the four-edge table at 1458-1471 |
| `specs/010-consumer-migration/tasks.md` | **13** | T076, T038's ⚠ obligation, T089/T090, the migrated-out block at 537-578 |
| `specs/010-consumer-migration/spec.md` | 44, 533-536, 752, 1287 | the FR/SC text on the indivisible step |
| `specs/010-consumer-migration/import-census.md` | 51, 82 | R1's gate wording; the "breaks at `v0.1.1`" note |
| `specs/010-consumer-migration/migration-guide.md` | 32-34, 474, 610-611 | **"Requires `cuemsutils >= 0.1.0rc16`"** is the consumer-facing floor → `>= 0.1.1`. §2 is why this matters beyond tidiness |
| `specs/014-xs-boolean-and-media-elements/plan.md` | 32, 901-902 | **decision 2** is "the branch stays on rc16, guarded by `test_no_version_bump.py:17`" |
| `specs/014-xs-boolean-and-media-elements/tasks.md` | 30, 420 | S2's note and the verified-version record |
| `specs/014-xs-boolean-and-media-elements/migration-guide.md` | 34, 133, 367, 428 | "`0.1.0rc16` does not move" ×3, and the release note |

**Frozen — do not rewrite**: about twenty `v0.1.1` references in `specs/004-*`, `006-*`, `007-*`,
`011-*`, `012-*`, `013-*`. Per `CLAUDE.md`'s policy these are historical record. The one candidate
exception is `specs/013-device-class-reshape/migration-guide.md:484`, an *active* hand-off already
consolidated as R9 of the removal document — correct it there.

Each sibling repository also carries its own `specs/` prose quoting these bounds and versions.
Secondary, but it will read wrong.

## 9. Branch, tag and release-line state per sibling

Measured 2026-10-12, after fetching `cuems-common` and `cuems-power-bridge` (both two months
stale) and checking both out on `feat/xml-refactor`.

| Repo | Refactor branch | Candidate tag | Branch vs tag | **Packaging release line** | Refactor vs that line |
|---|---|---|---|---|---|
| `cuems-utils` | `014-…` (integration) | none yet, cuts last | — | **`origin/debian/bookworm`** → `0.1.0rc16+1` | 231 ahead / **73 behind** |
| `cuems-common` | `e595e67` 2026-10-05 | `e3c9430` ✅ | **3 ahead** | **`origin/debian/bookworm`** → `1.3.0-25` | 41 ahead / **22 behind** |
| `cuems-engine` | `fc0cad3` | **none** | — | none — packaging exists *only* on this branch; every other branch still says `osc-control (0.0.0-2)` | n/a |
| `cuems-editor` | `a3309ab` | **none** | — | **`origin/debian/bookworm`** → `0.1.0rc1-7` | 36 ahead / **43 behind** |
| `cuems-nodeconf` | `65605de` | `5be6cf0` 2026-09-30 | at the tag | **`origin/debian/bookworm`** → `0.1.0-1` only | 71 ahead / **9 behind** |
| `cuems-power-bridge` | `dd1256f` 2026-10-05 | `399baf7` ✅ | **2 ahead** | **`origin/main`** → `0.3.0-10` | 47 ahead / **26 behind** |
| `cuems-frontend` | `f5453a3` 2026-10-07 | `f5453a3` | at the tag | not packaged | §9.1 |

⚠ **The packaging release line is `debian/bookworm`, not `main` or `rc_1`, in four of the five
packaged repositories.** Measuring against the default branch gives wrong answers in both
directions: `cuems-common` reports "0 behind `main`" while being 22 behind its actual release line,
and `cuems-editor` reports 16 behind `rc1` when it is **43** behind `debian/bookworm`.

⚠ **`CLAUDE.md` is wrong about this repository's own packaging branch**, and §10 depends on the
correction. It says packaging moved to the working branch on 2026-09-24, that `debian/bookworm` is
"preserved and tagged `packaging-rc14`", and that "nothing new lands on it". Measured 2026-10-12:
`origin/debian/bookworm` is **the active release line** — `4ee34b6` (2026-10-09), carrying
`0.1.0rc16+1`, cut by exactly the merge-`main`-in workflow that note says was abandoned
(`4b54b67 Merge branch 'main' into debian/bookworm (release/0.1.0rc16)`). The **`packaging-rc14`
tag does not exist.** Correct `CLAUDE.md` before anyone plans a build from it.

**Every candidate tag is re-cut by this decision**, since every tag message names `0.1.0rc16` as the
coordinated version. Two are behind their branches *already*, in both cases by a 2026-10-05 commit
doing feature 014's sibling-gate work — `cuems-common`'s `e595e67` (`xs:boolean` true/false
fixtures, T031) and `cuems-power-bridge`'s `dd1256f` (`network_map` fixtures + the settings device
shape). So the re-cut is owed on 014's account regardless.

**`CLAUDE.md`'s tag record was accurate**; an earlier reading of it as "drifted" came from the two
stale clones, where a missing fetch and a deleted tag are indistinguishable. Only two rows really
changed: `cuems-nodeconf` moved (`b305c1c` → `5be6cf0`) and `cuems-frontend` acquired one.
**Moving a published tag is maintainer-only, never an agent's**, and `cuems-utils` tags last (D27).

⚠ **Measure against the release line, not the default branch.** `cuems-common`'s release line is
`rc_1`/`debian/bookworm` (`main` still sits at `1.3.0-12`), so measuring against `main` reports
"0 behind" and hides both the 19-commit lag and §1's collision.

### 9.1 `cuems-frontend` needs a versioning decision, not a bump

It has no `debian/` directory, no tag history, and `package.json` has never left `0.0.0` (package
name `formitgo-tw`). It is also the one consumer with no package edge at all — the gate reaches it
through the payload handshake instead (010 FR-108), and `payload_version: 1` already flows. So
"move to the next stable minor" has no defined meaning here yet. Either give it a first real version
at this landing (`0.1.0`) or state explicitly that it stays unversioned and the handshake is its
only compatibility contract.

## 10. Merge before bump, and the changelog reconciliation

**Decided 2026-10-12.** Every fix released from a parallel line is **absorbed into the refactor
branch before the new version is published**, so nothing shipped is lost by the bump. The merge
comes first; the version entry is written afterwards, on top of the merged history.

### 10.1 The changelog shape this produces

Each repository's `debian/changelog` ends up as:

```
<package> (<target version>) unstable      <- NEW, the newest/top entry: the xml-refactor landing
                                              (and whatever the parallel line adds before publication)
<package> (<highest released>) bookworm    <- absorbed from the release line, verbatim
<package> (<…>) bookworm                   <- …the rest of the released history, in order
```

Two rules follow from that, and they are what make the three collisions in §1 disappear:

1. **The released entries are absorbed verbatim.** They describe builds that exist in the field; they
   are history and are not rewritten, renumbered or merged into the new entry.
2. **The refactor branch's `UNRELEASED` entry is not renumbered — it is *folded into* the new top
   entry.** `cuems-common`'s `1.3.0-23 UNRELEASED` and `cuems-editor`'s `0.1.0rc1-4 UNRELEASED`
   describe work that has never shipped under those numbers, and those numbers now belong to someone
   else's build. Their **content** becomes the body of the `1.3.1-1` / `0.1.1-1` entry; the stale
   headers go.

**The reconciliation is ongoing, not a single event.** The parallel lines keep releasing until
publication, so each merge absorbs whatever has accumulated since the last one, and the top entry
keeps growing until the release is cut. The lists in §10.2 are dated, not final — re-derive them at
merge time with:

```bash
comm -13 <(git show <refactor>:debian/changelog | grep -oE '^<pkg> \([^)]+\)' | sort -u) \
         <(git show <release-line>:debian/changelog | grep -oE '^<pkg> \([^)]+\)' | sort -u)
```

### 10.2 What each merge has to absorb — measured 2026-10-12

| Repo | Entries on the release line, absent from the refactor branch | Folded into the new top entry |
|---|---|---|
| `cuems-utils` | **`0.1.0rc16+1`** — stops shipping `/usr/lib/cuems/CACHEDIR.TAG`, which `0.1.0rc16` picked up from virtualenv and which `cuems-editor 0.1.0rc1-5` and `cuems-engine 0.1.0rc4`/`rc5` also ship, so `dpkg -i` failed with "trying to overwrite" unless forced. No code change | the `0.1.0rc16` UNRELEASED entry *(features 011–015)* |
| `cuems-common` | **`1.3.0-23`, `-24`, `-25`** | the `1.3.0-23` UNRELEASED entry *(the `/etc/cuems` handover)* |
| `cuems-editor` | **`0.1.0rc1-5`, `-6`, `-7`** | the `0.1.0rc1-4` UNRELEASED entry |
| `cuems-nodeconf` | **none** — the release line stopped at `0.1.0-1`; the refactor branch already carries `-2`…`-8` | `-2`…`-8`, all of them UNRELEASED or `unstable`-but-unreleased |
| `cuems-power-bridge` | **`0.3.0-7`, `-8`, `-9`, `-10`** — the `/poweroff` endpoint, the `CACHEDIR.TAG` fix, `nextcue_name`, the NDI preview | the `0.3.1-1` entry, which is already at the target |
| `cuems-engine` | **none** — no release line exists; packaging lives only on the refactor branch | its `0.1.0rc2-3` entry |

The `CACHEDIR.TAG` row is worth reading twice: it is a **cross-package file-overwrite conflict**,
exactly the class `CLAUDE.md` warns about ("a `.deb` must not bundle anything another package
already ships"), and it was fixed independently in `cuems-utils 0.1.0rc16+1` and
`cuems-power-bridge 0.3.0-8`. If the merge drops either fix, `dpkg -i` breaks again at install
time — which is the concrete form of "nothing is lost on the new versions".

**A rule-4 item that lands in this library, not in a merge** (added 2026-10-14). `cuems-nodeconf`'s
shipped `0.1.0-8` carries foreign-controller filtering (`80ccc83`), a fix inside the daemon's merge.
On the refactor line that merge is this library's (D22), so the fix cannot arrive by merging the
release line: it was re-implemented here, on `feat/xml-refactor`, as
`CuemsNetworkMapType.refresh(..., *, cluster=)` plus `NodeIndex.cluster_controllers`,
`is_foreign_controller`, `foreign_controllers` and `drop_foreign_controllers`
(`../cuems-nodeconf/specs/upstream-reports/foreign-controller-scoping.md`). It must ship **inside
`0.1.1`**: `cuems-nodeconf` passes `cluster=` with no feature detection, and no other consumer
needs to. If it misses `0.1.1`, the release notes must say so, because rule 4 would then be broken
for this item. Note that the `cuems-nodeconf` row above ("none") predates
`coordinated-release-bump-corrections.md`, which records this collision.

### 10.3 The merge is also how the branches stop being behind

Every refactor branch except `cuems-engine`'s is behind its release line (§9: 73, 22, 43, 9 and 26
commits). Merge-before-bump discharges that lag as a precondition of the bump rather than leaving it
as debt, which also means **the relation edits in §4 should be made after the merge**, on the merged
`debian/control` — otherwise a merge conflict resolves them back to the parallel line's values.

## 11. Execution order

1. ~~Fetch the stale siblings and reconcile the tag table.~~ **Done 2026-10-12** — §9 is measured.
2. **Agree the seven target versions** (§3) and `cuems-frontend`'s shape (§9.1). Everything below
   depends on the numbers being fixed, because the relations in §4 name them.
3. **Correct §8's top three documents** — they are instructions other flows execute. Correct
   `CLAUDE.md`'s `debian/bookworm` / `packaging-rc14` claim at the same time (§9), since step 4
   merges from the branch it says is dead.
4. **Merge the release line into each refactor branch** (§10) — `debian/bookworm` for `cuems-utils`,
   `cuems-common`, `cuems-editor` and `cuems-nodeconf`; `main` for `cuems-power-bridge`;
   `cuems-engine` has none. Resolve `debian/changelog` per §10.1: released entries absorbed verbatim,
   the branch's `UNRELEASED` header dropped and its body folded upward. Suite green per repository
   **before** anything is renumbered.
5. **Rename the removal document** (§7) and fix its 14 citations, including the two code/test ones.
6. **The atomic set, on the merged trees.** Per repository: the new top changelog entry at the target
   version, the self-version sites (§3), §3.1's drift reconciles, and **every relation in §4** — the
   relations last, so a merge conflict cannot resolve them back to the parallel line's values
   (§10.3). A version move with the relations left behind is an ecosystem `dpkg` refuses to install,
   so these do not land as separate per-repository commits; they land as one coordinated set.
7. **Re-cut every candidate tag** (§9), `cuems-utils` last.
8. Suite green in each repository, and this one's `tests/packaging/test_no_version_bump.py` passing
   **in its rewritten form** — a green run of the old form would mean the bump did not happen.

## 12. What this document does not settle

1. **Which feature, or whether a feature, cuts the release.** `deprecated-surface-removal` §5 item 3
   asked the same of `v0.1.1`; it now applies to the release itself. Feature 015 is the last of the
   011–015 set and so the natural host, but a thin release-only feature is equally defensible.
2. **Whether the five tag gates (G1–G5 of `upcoming-feature-requirements` §0a) block the release or
   only the tag.** They were written as tag gates when the tag cut no version. Cutting seven stable
   releases from the same point raises the bar; this needs an explicit answer rather than an
   inherited one.
3. **When `0.1.1` goes to PyPI, relative to the sibling `.deb` builds.** *Not* whether — that is
   settled: `debian/bookworm`'s `0.1.0rc16+1` entry states "cuemsutils 0.1.0rc16 on PyPI", so the
   parallel line already publishes. But `dh-virtualenv` resolves the editor's `cuemsutils` bound
   from PyPI at build time (`stored-media-values-preimplementation.md` *(deleted 2026-10-14, feature 015; in git history)* §203), so **`0.1.1` must be on
   PyPI before any sibling `.deb` that bounds `>= 0.1.1` can be built.** That orders step 6's
   coordinated set internally, and nothing in §11 currently says so.
4. ~~How the branches behind their release lines catch up.~~ **Answered 2026-10-12: merge before
   bump** — §10. The lag is discharged as a precondition of the bump, not carried as debt.
5. **When.** The decision is made; the schedule is not.
