<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# The coordinated xml-refactor landing cuts a stable minor release in **every** repository

**Decided 2026-10-12** by the development team; rule 5 added 2026-10-14 by the maintainer. Parallel bugfix and small-feature work is being
released from every repository's own line, so the refactor cannot merge under a version number any
of them still holds. **Status: decided; §3–§8 executed by feature 016 (2026-10-16), the rest owed — see below.** This document is the work order — the
measured target version for each repository, every versioned package relation that moves with it,
and the file inventory in this repository.

> **Status 2026-10-16 — §3–§8 and §11 step 6 EXECUTED by feature 016**
> (`specs/016-coordinated-minor-bump/`, records and evidence there). Signed commits on each
> `feat/xml-refactor`, **pushed 2026-10-16**, and **every `xml-refactor-merge-candidate` re-cut and
> pushed by the maintainer the same day**, each on its repository's `feat/xml-refactor` head:
>
> | Repo | Version | Commit |
> |---|---|---|
> | cuems-utils | `0.1.1` | bump `8f6eede`, record `67f18f7`, merge `8a4bc42`; **tag at `4b336cd`** (016's docs follow-up, the branch head at the re-cut) |
> | cuems-common | `1.3.1-1` | `fb450b5` |
> | cuems-nodeconf | `0.1.1-1` | `334db12` |
> | cuems-power-bridge | **`0.4.0-1`** (not `0.3.1-1`) | `666cb25` (re-signed by the maintainer from `f0da390`, same tree) |
> | cuems-engine | `0.1.1-1` | `e994a5e` |
> | cuems-editor | `0.1.1-1` | `a2431f0` |
> | cuems-frontend | **`0.2.0`** (not `0.1.0`, §9.1 answered) | `9e91464` |
>
> **Corrections to this document, measured by 016** (its research R1–R3, R2a, R2b, R16):
> - **`cuems-engine` has a release line** (§1, §3, §9, §10.2 say none): `debian/bookworm` at
>   `0.1.0rc6-5`, 119 commits ahead of the refactor.
> - **`cuems-power-bridge`'s release line released `0.3.1-2`, `0.3.2-1` and `0.3.2-2`** after this
>   document, so its target moved to **`0.4.0-1`**, and §4.4's "unchanged"
>   `cuems-common Breaks: cuems-power-bridge` became **`(<< 0.4.0~)`**. This is a recorded exception
>   to rule 1 (maintainer, 2026-10-16).
> - **`cuems-frontend`'s `dev` tagged `v0.1.0-rc1`** on 2026-10-16, so its first version is
>   **`0.2.0`**.
> - **`cuems-utils 0.1.0rc17` released `stop_project`**, which `0.1.1` does not accept. It is part of
>   rule 4's backlog.
> - **The maintainer scripts were a fifth defeated relation**: `cuems-common`'s `rm_conffile`
>   prior-versions `1.3.0-23~` would have skipped the network-map handover and left the retired
>   `99-cuems` sudo rules active when upgrading from the released `1.3.0-23`…`-25`. They are now
>   `1.3.1~`.
> - `cuems-engine` now declares `libmtcmaster (>= 0.0.2-0)` (relation row 25); libossia stays an
>   independent input.
>
> **NOT done, and still owed** (this document stays until all of it is):
> 1. **Rule 4: release-line reconciliation**, deliberately deferred: `cuems-utils` 77, `cuems-common`
>    22, `cuems-engine` 119, `cuems-editor` 43, `cuems-power-bridge` 59 commits behind, and
>    `cuems-frontend` 31 behind its own `origin/dev` (it tagged `v0.1.0-rc1` on 2026-10-16). That
>    includes `stop_project` on every side (library rc17, engine rc6-5, frontend's STOP chips) and
>    `CACHEDIR.TAG`. Re-verify every relation after each merge
>    (`specs/016-coordinated-minor-bump/tools/verdicts.sh`).
> 2. ~~**The re-cut** of every `xml-refactor-merge-candidate`~~: ✅ **done 2026-10-16** by the
>    maintainer (`../.xml-refactor-tag-messages/recut-and-push.sh`); all seven verified on the remotes.
> 3. **§11.1 validation on the re-cut tags.** It is now unblocked. ⚠ It validates the set **as
>    tagged**, so it says nothing about the release-line content of item 1, which has to be validated
>    again after that reconciliation.
> 4. **`cuems-engine`'s `poetry.lock` relock** (FR-022), and engine CI under rule 5.
> 5. ~~**Merging `016-coordinated-minor-bump`** into this repository's `feat/xml-refactor`~~: ✅ done
>    2026-10-16 (`8a4bc42`). Before publication, also tell the `cuems-power-bridge` and `cuems-frontend`
>    maintainers the refactor's numbers (`0.4.0-1`, `0.2.0`), so their release lines stay below them.
> 6. **Publication** (§11 step 10).

## The decision, in five rules

1. **Every affected repository moves to its own next stable minor at the coordinated
   `xml-refactor-merge-candidate` landing** — not just `cuems-utils`. The last component of the
   upstream version advances, any `rc` suffix is dropped, and the Debian revision resets to `-1`.
   Examples given by the team: `cuems-common` → **`v1.3.1`**, `cuems-nodeconf` → **`v0.1.1`**.
2. **`cuems-utils` cuts `0.1.1` directly** — no `0.1.1~rc1` (settled 2026-10-12). That is what makes
   a plain `>= 0.1.1` the correct consumer floor.
3. **The deprecated-surface removal moves with it**, `v0.1.1` → **`v0.1.2`**. That work is
   [`deprecated-surface-removal-v0-1-2.md`](deprecated-surface-removal-v0-1-2.md), which this
   decision renames (§7).
4. **Merge before bump.** Every fix already released from a parallel line is absorbed into the
   refactor branch before the new version is published, so nothing shipped is lost. The version entry
   becomes the newest/top changelog entry; everything the parallel lines keep adding until
   publication is absorbed as part of each repository's reconciliation — §10.
5. **Validation runs on the re-cut tags, not on a published release** (maintainer decision,
   2026-10-14). The coordinated set is validated against the coordinated re-cut of
   `xml-refactor-merge-candidate` in **every** sibling repository, with each package built from its
   tag and `cuemsutils` built from `cuems-utils`' tag. **Nothing waits for `0.1.1` on PyPI.**
   Publishing (PyPI, the `.deb` archive) comes after validation and is a separate step. §11.1 is how
   the validation runs. This answers §12 item 3, which assumed the opposite.

**It reverses three standing decisions**, each recorded where it was made rather than quietly
overwritten: §12/§12.1 of [`etc-cuems-first-install.md`](etc-cuems-first-install.md) ("the library
version stays at `0.1.0rc16`" / "why not `0.1.1`"), §0a of
[`upcoming-feature-requirements-2026-10-02.md` *(deleted 2026-10-14, feature 015; in git history)*](../015-consumer-gate-closure/spec.md) ("the
version does not move for this tag"), and decision 2 of
`specs/014-xs-boolean-and-media-elements/plan.md` ("the branch stays on rc16").

---

## 1. Why the versions have to move: four collisions, measured

The refactor branches have been holding version numbers that the release lines have since **taken
and shipped**. Measured 2026-10-12 after fetching every sibling; the `cuems-nodeconf` row was
corrected 2026-10-13 by `../cuems-nodeconf/specs/upstream-reports/coordinated-release-bump-corrections.md`, which measured the line that is actually releasing.

| Repo | Branch holds | Parallel line released | Same commit? | Verdict |
|---|---|---|---|---|
| `cuems-utils` | `0.1.0rc16` (UNRELEASED) | `v0.1.0rc16`, and a revision `debian/0.1.0rc16+1` | ❌ no | **collision** |
| `cuems-common` | `1.3.0-23` (UNRELEASED) | `v1.3.0-23` (`8109884`, 2026-10-07), then `-24`, `-25` | ❌ no | **collision** |
| `cuems-editor` | `0.1.0rc1-4` (UNRELEASED) | `v0.1.0rc1-4` (`faaa626`, 2026-10-06), then `-5`, `-6`, `-7` | ❌ no | **collision** |
| `cuems-engine` | `0.1.0rc2-3` (`bookworm`) | nothing tagged; packaging exists only on the refactor branch | — | no collision |
| `cuems-nodeconf` | `0.1.0-8` (UNRELEASED) — the TXT-record rename | `0.1.0-8` (2026-10-06, foreign-controller filtering) and `0.1.0-9` (2026-10-07), both on **`origin/rc_1`**, untagged | ❌ no | **collision** — the 2026-10-12 reading measured `debian/bookworm`, which stopped 2025-12-30 |
| `cuems-power-bridge` | `0.3.1-1` (`unstable`) | `v0.3.0-10`, which sorts **below** it | — | no collision |

**The released commits are not ancestors of the refactor branches**, verified for all four
collisions. So a user with `cuems-common 1.3.0-23` installed has a package that shares a version
number with the `/etc/cuems` handover and contains none of it.

All four are resolved by **§10.1 rule 2**: the colliding `UNRELEASED` header is dropped and its body
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

**Two more relations are defeated the same way** (measured by `../cuems-nodeconf/specs/upstream-reports/coordinated-release-bump-corrections.md` §2), both on the
TXT-record rename (`node_type` → `node_role`, D33). Each lets through a half-renamed pair: the
listener reads `node_role`, the publisher writes `node_type`, and the cluster discovers nothing, with
no install error.

| Relation | Lets through, though it should refuse | Fixed by |
|---|---|---|
| `cuems-common` `Breaks: cuems-nodeconf (<< 0.1.0-8)` | released `cuems-nodeconf` `0.1.0-8`, `-9` (still `node_type`) | §4.3 → `<< 0.1.1~` |
| `cuems-nodeconf` `Breaks: cuems-common (<< 1.3.0-23~)` | released `cuems-common` `1.3.0-23`, `-24`, `-25` (still `node_type`; `origin/rc_1` still ships `cuems.service.{firstrun,master,slave}`) | §4.2 → `<< 1.3.1~` |

So this is not a separate repair to schedule — it is **§4's relation matrix doing its job**, and the
reason the matrix cannot be skipped as cosmetic. The matrix already carried all three fixes; only
the measurement of the second and third was missing.

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
| `cuems-nodeconf` | `0.1.0` | `0.1.0-9` (`origin/rc_1`, untagged) | `0.1.1-1` UNRELEASED — headed so during the 2026-10-13 merge (§10.2), a maintainer decision so the changelog never runs backwards | **`0.1.1-1`** | `pyproject.toml:7`, `debian/changelog:1` |
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

⚠ **`<< 0.2.0~` is wrong** — both `deprecated-surface-removal-v0-1-2.md` §3 and
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
| `specs/planning/deprecated-surface-removal-v0-1-2.md` | **21 sites** | `git mv` to `…-v0-1-2.md`; retitle; §1.1's `dpkg` table re-derived (§4.1 supersedes it); §1.2's "wrong in the other direction" argument rebased on `v0.1.2`; §3's atomic step **no longer belongs there** — it fires at this landing; §5 item 1's struck question re-opens as "is `0.1.2` the first release after a stable one?"; §7's rendered example message |
| …the **14 files citing that filename** | 14 | `git grep -l deprecated-surface-removal-v0-1-2` — two are **not documents**: `src/cuemsutils/tools/CTimecode.py` and `tests/unit/test_ctimecode.py` |
| `debian/changelog` | 1 | `(0.1.0rc16) UNRELEASED` → `(0.1.1)`. It **cannot** keep `0.1.0rc16` — §2 |
| `debian/changelog` | 94-95 | "REMOVED IN v0.1.1, which is why every consumer pins `<< 0.1.1~`" — both halves wrong |
| `debian/control` | **23** | `Breaks: cuems-common (<< 1.3.1~)` + the comment at `:15-22` — §1.1, §4.2 |
| `CHANGELOG.md` | 3 | **The `## 0.1.1 — Unreleased` section exists since 2026-10-14** (§10.4 opened it). Date it at the cut, and decide whether the two older `## Unreleased` sections below it (the `hardware_outputs` rename and feature 004), which ship in `0.1.1` too, fold into it or stay as they are |
| `CHANGELOG.md` | feature 004's *Deprecated* section | "removed in `v0.1.1`" → `v0.1.2` (it was line 96 before §10.4's section was added above it; re-grep) |
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
| `specs/planning/tools-external-consumers-and-timeoutloop-migration.md` *(deleted 2026-10-16, done; corrected by 016 before deletion)* | 216 | `REMOVAL_RELEASE` quote; R6's coordination point |
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
| `cuems-nodeconf` | `ac14b90` 2026-10-14 *(re-measured)* | `5be6cf0` 2026-09-30 | **27 ahead** *(re-measured 2026-10-14)* | **`origin/rc_1`** → `0.1.0-9` (corrected 2026-10-13; `debian/bookworm` → `0.1.0-1` stopped 2025-12-30) | **0 behind both** after the 2026-10-13 merges (was 6 behind `rc_1`, 9 behind `debian/bookworm`; disjoint sets) |
| `cuems-power-bridge` | `dd1256f` 2026-10-05 | `399baf7` ✅ | **2 ahead** | **`origin/main`** → `0.3.0-10` | 47 ahead / **26 behind** |
| `cuems-frontend` | `f5453a3` 2026-10-07 | `f5453a3` | at the tag | not packaged | §9.1 |

⚠ **The packaging release line is `debian/bookworm`, not `main` or `rc_1`, in three of the five
packaged repositories** — `cuems-nodeconf` is the exception the other way round: its releasing line
is `rc_1`, and `debian/bookworm` is the one that stopped (corrected 2026-10-13, `../cuems-nodeconf/specs/upstream-reports/coordinated-release-bump-corrections.md` §1;
the 2026-10-12 table said "four of the five"). Measuring against the default branch gives wrong answers in both
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

Two rules follow from that, and they are what make the four collisions in §1 disappear:

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
| `cuems-nodeconf` | **`0.1.0-8`, `-9`** from `origin/rc_1` (`0.1.0-7` is identical on both lines). ✅ **Absorbed 2026-10-13** — `78e7290` (`rc_1`, entries kept word for word) and `952b9dd` (`debian/bookworm`, recorded as absorbed; its `postinst`, which enables and starts the daemon, deliberately **not** taken — the `rc_1` packages never shipped maintainer scripts). `141cf1f` (static link-local address) was ported as `16b207d`; `80ccc83` (foreign controllers) is §10.4 | the old `0.1.0-8` UNRELEASED body, folded into the `0.1.1-1 UNRELEASED` entry already at the top |
| `cuems-power-bridge` | **`0.3.0-7`, `-8`, `-9`, `-10`** — the `/poweroff` endpoint, the `CACHEDIR.TAG` fix, `nextcue_name`, the NDI preview | the `0.3.1-1` entry, which is already at the target |
| `cuems-engine` | **none** — no release line exists; packaging lives only on the refactor branch | its `0.1.0rc2-3` entry |

The `CACHEDIR.TAG` row is worth reading twice: it is a **cross-package file-overwrite conflict**,
exactly the class `CLAUDE.md` warns about ("a `.deb` must not bundle anything another package
already ships"), and it was fixed independently in `cuems-utils 0.1.0rc16+1` and
`cuems-power-bridge 0.3.0-8`. If the merge drops either fix, `dpkg -i` breaks again at install
time — which is the concrete form of "nothing is lost on the new versions".

The `cuems-nodeconf` row was corrected 2026-10-13 (the 2026-10-12 reading said "none", having
measured `debian/bookworm`). It also found an **older** collision: `debian/bookworm` released a
`0.1.0-1` (dated 19 Dec 2024, the `.deb` cached in `rc1_packages/`) that is a different build from the
`0.1.0-1 UNRELEASED` that `rc_1`'s history starts from. The changelog keeps `rc_1`'s history, which is
what the shipped `-2`…`-9` carry, and both `-1` builds sort below `0.1.1-1`, so the bump is unaffected.

### 10.3 The merge is also how the branches stop being behind

Every refactor branch except `cuems-engine`'s was behind its release line (§9: 73, 22, 43 and 26
commits; `cuems-nodeconf` was 6 behind `rc_1` and is now 0, merged 2026-10-13). Merge-before-bump discharges that lag as a precondition of the bump rather than leaving it
as debt, which also means **the relation edits in §4 should be made after the merge**, on the merged
`debian/control` — otherwise a merge conflict resolves them back to the parallel line's values.

### 10.4 Rule-4 items this library re-implements instead of absorbing by merge

Some fixes shipped from a sibling's release line live in code that the refactor moved into this
library. Merging that sibling's release line brings the changelog entry but not a working fix,
because the code it patched is gone from the refactor branch. Each such fix is re-implemented here,
and **`0.1.1` must contain it**. If one misses `0.1.1`, the release notes must say so, because rule 4
is then broken for that item.

| Shipped fix | Re-implemented here | Status | Consumer obligation |
|---|---|---|---|
| `cuems-nodeconf` `80ccc83` (`0.1.0-8`): foreign-controller filtering. A controller on a shared LAN adopted other clusters' controllers into its map | `CuemsNetworkMapType.refresh(..., *, cluster=)`; `NodeIndex.cluster_controllers`, `is_foreign_controller`, `foreign_controllers`, `drop_foreign_controllers`. Request: `../cuems-nodeconf/specs/upstream-reports/foreign-controller-scoping.md` (D22 puts the map mutation here) | ✅ **landed** on `feat/xml-refactor`, `38d2ede` (2026-10-14). Listed in `CHANGELOG.md`'s `0.1.1` section | `cuems-nodeconf` only: delete its interim discovery filter (`6afb5eb`, which keeps new foreign controllers out but cannot remove saved ones), pass `cluster=` computed with `cluster_controllers(settings_uuid, own_role)`, and log `foreign_controllers(cluster)`. Its strict `xfail` removal test turns `XPASS`. It needs no feature detection, because §4.1's floor is `>= 0.1.1` |

Known limitation, carried as in the shipped fix: a fresh node that hears two clusters' controllers
on its first pass accepts both. Fixing that is `cuems-nodeconf`'s controller-election work, not
this release's.

## 11. Execution order

1. ~~Fetch the stale siblings and reconcile the tag table.~~ **Done 2026-10-12** — §9 is measured.
2. **Agree the seven target versions** (§3) and `cuems-frontend`'s shape (§9.1). Everything below
   depends on the numbers being fixed, because the relations in §4 name them.
3. **Correct §8's top three documents** — they are instructions other flows execute. Correct
   `CLAUDE.md`'s `debian/bookworm` / `packaging-rc14` claim at the same time (§9), since step 4
   merges from the branch it says is dead.
4. **Merge the release line into each refactor branch** (§10) — `debian/bookworm` for `cuems-utils`,
   `cuems-common` and `cuems-editor`; `main` for `cuems-power-bridge`;
   `cuems-engine` has none — and **`rc_1` for `cuems-nodeconf`, already done 2026-10-13** (§10.2).
   Resolve `debian/changelog` per §10.1: released entries absorbed verbatim,
   the branch's `UNRELEASED` header dropped and its body folded upward. Suite green per repository
   **before** anything is renumbered. Check every §10.4 row: the library half is landed, and the
   consumer half has been applied on the consumer's refactor branch (for `cuems-nodeconf`, its
   foreign-controller `xfail` reads `XPASS`).
5. **Rename the removal document** (§7) and fix its 14 citations, including the two code/test ones.
6. **The atomic set, on the merged trees.** Per repository: the new top changelog entry at the target
   version, the self-version sites (§3), §3.1's drift reconciles, and **every relation in §4** — the
   relations last, so a merge conflict cannot resolve them back to the parallel line's values
   (§10.3). A version move with the relations left behind is an ecosystem `dpkg` refuses to install,
   so these do not land as separate per-repository commits; they land as one coordinated set.
   **The packaging demonstrations are part of that set** (§11.1 step 2). Their stub versions and
   scenario expectations name the versions and relations this step moves, so they move in the
   same commit.
7. ✅ *Done 2026-10-16.* **Re-cut every candidate tag** (§9), `cuems-utils` last. The re-cut tags are what step 9
   validates (rule 5), so nothing below runs against a branch head.
8. Suite green in each repository, and this one's `tests/packaging/test_no_version_bump.py` passing
   **in its rewritten form** — a green run of the old form would mean the bump did not happen.
9. **Validate the set on the re-cut tags** (§11.1): the packaging demonstrations, with every
   checkout at its tag, and their evidence recorded.
10. **Publish only after step 9 passes**: `cuems-utils` `0.1.1` to PyPI, and the `.deb`s to the
    archive. When that happens is §12 item 5; it does not gate anything above.

### 11.1 Validating on the re-cut tags — the packaging demonstrations

**What exists.** Two repositories have a **release-gate demonstration**, a script that builds the
real packages and replays install scenarios in a disposable, unprivileged bookworm system
(`mmdebstrap --mode=unshare`), recording whether `apt`/`dpkg` accepts or refuses each one:

| Script | Builds for real | Stubs (equivs) | Proves |
|---|---|---|---|
| `../cuems-nodeconf/tests/packaging/release-gate-demo.sh` | `cuems-nodeconf` (new and previous release) **and** `cuems-common` (both sides of its cutover) | `cuems-utils` | every relation between those two packages, and their bounds on `cuems-utils` |
| `../cuems-common/tests/packaging/release-gate-demo.sh` | `cuems-common` (new and previous) | `cuems-utils`, `cuems-nodeconf` | `cuems-common`'s relations |

A third script, `../cuems-editor/tests/packaging/bookworm-build.sh`, builds the `cuems-editor`
`.deb` in bookworm and checks its interpreter. It proves the package **builds**, not its relations.
**`cuems-engine`, `cuems-power-bridge` and this library have no install demonstration.** Their §4
edges are checked by `dpkg --compare-versions` only. The validation record must say so, not imply
otherwise.

**Why none of them needs PyPI for `cuemsutils`.** Each builds a `cuemsutils` wheel from the
`cuems-utils` checkout named by `UTILS=` and hands it to dh-virtualenv's pip through
`PIP_FIND_LINKS`. dh-virtualenv passes `os.environ` to pip unchanged (measured in the nodeconf
script's §2 comment), so `debian/rules` is not edited. Network access is still needed: the Debian
mirror for the chroots, and PyPI for **third-party** dependencies only.

**Proper use at the coordinated re-cut:**

1. **Every checkout at its re-cut tag, clean.** That covers the repository running the script, its
   `COMMON=` and `UTILS=`. The evidence records each commit and flags `(+ uncommitted changes)`. A
   dirty run is not validation evidence. Run it again from clean tags.
2. **Update the scripts first, in step 6's commit.** Neither script reads versions from
   `debian/control`; both hard-code them:
   - `UTILS_VERSIONS` (the `cuems-utils` stubs) must straddle §4.1: one below the floor, one
     admitted, one past the ceiling — `0.1.0rc16`, `0.1.1`, `0.1.2~rc1`. Today's sets
     (`0.1.0rc15 0.1.0rc16 0.1.1~rc1` in nodeconf's, plus `0.1.0rc14` in common's) test the
     **old** bounds;
   - every scenario's expectation and title that names `0.1.0-8`, `1.3.0-23` or `1.3.0-22`, and the
     `stubs/*.ctl` versions, move to the §3/§4 values. A scenario that still expects the old edge
     will "pass" while testing nothing that ships.
3. **Pass every ref explicitly. The defaults are stale.**
   - nodeconf's `OLD_REF` defaults to `478bc49` (`0.1.0-7`). The field baseline is now **`0.1.0-9`**
     (`origin/rc_1`), so pass that.
   - nodeconf's `COMMON_NEW` defaults to `1a00159` (`1.3.0-23`). Pass `cuems-common`'s **re-cut
     tag** (`1.3.1-1`).
   - nodeconf's `COMMON_OLD`, and cuems-common's own `OLD_REF`, default to `rc_1`. The comments call
     that `1.3.0-22`, but `cuems-common`'s `rc_1` is now `1.3.0-25`, and a default branch moves.
     Pass the release you mean as a fixed ref.
   - `UTILS=` points at `cuems-utils` checked out at **its** re-cut tag.
4. **Write new evidence; don't overwrite the old.** `OUT=` defaults to the evidence of the feature
   that wrote the script (nodeconf: `specs/001-network-map-object-adoption/evidence/out-of-order-refusal.txt`).
   That file is the record of an earlier gate. Point `OUT=` at a new file for this validation.
5. **Read the exit status and the evidence together.** Exit `0` means every scenario's observed
   outcome matched its expectation, and the evidence lists each one with the tool that refused. A
   non-zero exit names the scenario.
6. **It is not part of any test suite.** It needs `mmdebstrap`, `uidmap`, `equivs`, `dpkg-dev`,
   `debhelper`, `fakeroot`, `uv` or `pip3`, and `/etc/subuid`/`/etc/subgid` ranges for the calling
   user. It takes about six minutes and runs by hand (nodeconf's `run-tests.sh` excludes it
   deliberately).

Example, from `cuems-nodeconf` at its re-cut tag, once the scripts carry step 2's values:

```bash
OLD_REF=origin/rc_1 \
COMMON=../cuems-common COMMON_NEW=<cuems-common re-cut tag> COMMON_OLD=<cuems-common 1.3.0-25 commit> \
UTILS=../cuems-utils \
OUT=specs/<bump feature or record>/evidence/out-of-order-refusal-0.1.1.txt \
tests/packaging/release-gate-demo.sh
```

## 12. What this document does not settle

1. **Which feature, or whether a feature, cuts the release.** `deprecated-surface-removal` §5 item 3
   asked the same of `v0.1.1`; it now applies to the release itself. Feature 015 is the last of the
   011–015 set and so the natural host, but a thin release-only feature is equally defensible.
2. **Whether the five tag gates (G1–G5 of `upcoming-feature-requirements` §0a) block the release or
   only the tag.** They were written as tag gates when the tag cut no version. Cutting seven stable
   releases from the same point raises the bar; this needs an explicit answer rather than an
   inherited one.
3. ~~**When `0.1.1` goes to PyPI, relative to the sibling `.deb` builds.**~~ **Answered
   2026-10-14 by the maintainer: after validation, not before** (rule 5, §11 steps 9–10). This item
   said `0.1.1` *"must be on PyPI before any sibling `.deb` that bounds `>= 0.1.1` can be built"*,
   because dh-virtualenv resolves `cuemsutils` from PyPI in a plain build. Validation builds don't
   do that: they offer a wheel built from `cuems-utils`' re-cut tag through `PIP_FIND_LINKS`
   (§11.1), as `cuems-nodeconf`'s and `cuems-editor`'s build scripts already do. Publishing to PyPI
   still precedes any **archive** build that resolves from PyPI, but it no longer orders step 6.
4. ~~How the branches behind their release lines catch up.~~ **Answered 2026-10-12: merge before
   bump** — §10. The lag is discharged as a precondition of the bump, not carried as debt.
5. **When.** The decision is made; the schedule is not.
