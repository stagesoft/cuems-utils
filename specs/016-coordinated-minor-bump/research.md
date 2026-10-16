<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Research — 016 coordinated minor bump

Measured 2026-10-15 after `git fetch --all --tags` in all seven repositories. The planning document
was measured 2026-10-12/13/14; **two releases shipped on 2026-10-15** and change what it says.
Every finding below names how it was measured, so `/speckit-implement`'s FR-002 step can re-run it.

---

## R1 — Starting state of the seven repositories

All seven are on `feat/xml-refactor`, clean, and level with `origin/feat/xml-refactor` (0/0).
`cuems-utils` is on `016-coordinated-minor-bump`, branched from `b83d5c2`.

| Repo | Start commit | Changelog head | Release line | Behind / ahead | Release line's head |
|---|---|---|---|---|---|
| `cuems-utils` | `b83d5c2` | `0.1.0rc16` UNRELEASED | `origin/debian/bookworm` | **73** / 262 | `0.1.0rc16+1`; also `origin/release/0.1.0rc17` (`0.1.0rc17`, 2026-10-15) |
| `cuems-common` | `e595e67` | `1.3.0-23` UNRELEASED | `origin/debian/bookworm` | **22** / 41 | `1.3.0-25` |
| `cuems-engine` | `fc0cad3` → **`7d0bda3`** (3 commits landed 2026-10-15, R16) | `0.1.0rc2-3` bookworm | `origin/debian/bookworm` ⚠ | 114 / 23 → **119 / 26** | `0.1.0rc6-5` (both `debian/bookworm` and `release/0.1.0rc6-5`) |
| `cuems-editor` | `e5e6ac1` | `0.1.0rc1-4` UNRELEASED | `origin/debian/bookworm` | **43** / 62 | `0.1.0rc1-7` |
| `cuems-nodeconf` | `82b0a69` | `0.1.1-1` UNRELEASED | `origin/rc_1` | 0 / 84 | `0.1.0-9` |
| `cuems-power-bridge` | `dd1256f` | `0.3.1-1` unstable | `origin/main` | **41** / 47 | `0.3.0-11`; also `origin/release/0.3.1-2` (2026-10-15) ⚠ |
| `cuems-frontend` | `6b69b41` | — (`package.json` `0.0.0`) | not packaged | — | — |

Method: `git rev-list --left-right --count <line>...feat/xml-refactor`; the highest changelog head
over every `refs/remotes/origin/*` branch, sorted with `sort -V`.

**Corrections to the planning document** (applied to it at the end, per FR-017):

- ⚠ **`cuems-engine` has a release line.** §1, §3, §9 and §10.2 say "nothing tagged; packaging
  exists only on the refactor branch". Measured: tags `v0.1.0rc6-1`…`v0.1.0rc6-4`,
  `origin/debian/bookworm` at `0.1.0rc6-4`, and `origin/release/0.1.0rc6-5`. The refactor branch is
  **114 commits behind**. The target `0.1.1-1` still sorts above every one of them. The engine's
  changelog head `0.1.0rc2-3` is on `origin/debian/bookworm` too, so it is released history, not an
  `UNRELEASED` entry to fold. **PENDING (spec FR-010a)**: new `cuems-engine` work is about to land;
  this row is re-measured at the start of the engine phase and is not final until then.
- `cuems-power-bridge` is **41** behind `main`, not 26.

---

## R2 — `cuems-power-bridge` moves to `0.3.2-1`, and a fourth defeated relation

**Decision**: target **`0.3.2-1`** (upstream `0.3.2`), and `cuems-common`'s
`Breaks: cuems-power-bridge (<< 0.3.1-1)` becomes **`(<< 0.3.2~)`**.

**Measured**: `origin/release/0.3.1-2` (`eb87e20`, 2026-10-15) released `cuems-power-bridge
0.3.1-2`, and its changelog says it is *"Numbered above 0.3.0-11 and the open xml-refactor line
(0.3.1-1)"*. The refactor branch is not its ancestor. `dpkg --compare-versions` puts `0.3.1-1` below
`0.3.1-2`, so keeping the planned target would publish a refactor package that sorts **below** a
release with none of its content. SC-001 forbids that.

That release also has no `cuemspowerbridge/scripts/cluster_poweroff` module, and its
`network_map.py` still reads `node_type` (`NodeType.master`/`NodeType.slave`). Those are exactly
what `cuems-common`'s `cuems-cluster-poweroff` relies on after the heredoc removal.
`Breaks: cuems-power-bridge (<< 0.3.1-1)` **admits `0.3.1-2`**, which is the same failure as
planning document §1.1. It is a fourth defeated relation: the `Breaks:` names a version, a parallel
line reuses the space above it, and the relation goes quiet. `<< 0.3.2~` refuses `0.3.0-11` and
`0.3.1-2` and admits `0.3.2-1` (verified with `dpkg --compare-versions`).

**Rationale**: rule 1 ("the last component of the upstream version advances") applied to the
measured high-water mark, not the planned one. The parallel line chose its number in good faith
against our announced `0.3.1-1`, so we move.

**Alternatives rejected**: keeping `0.3.1-1` (sorts below a shipped build); `0.3.1-3` (only a
revision bump over a different code line, and the next parallel `0.3.1-N` collides again); leaving
the `Breaks:` at `<< 0.3.1-1` (admits a bridge that `cuems-cluster-poweroff` cannot drive).

⚠ **To flag to the maintainer at the first stop**: this overrides the planning document's §3 row,
§4.4's "unchanged", and the power-bridge team's understanding of the refactor's number.

---

### R2a — and again, the next day: `0.4.0-1` (maintainer decision, 2026-10-16)

At Phase 6's measurement, `origin/main` had released **`v0.3.2-1`** (2026-10-15 20:28, the Companion
cue-status relay, "contains 0.3.1-2") and **`v0.3.2-2`** (2026-10-16 14:12, the relay on/off
switch). Neither contains the refactor: both still read `node_type` and have no
`cluster_poweroff`. So the confirmed `0.3.2-1` collided exactly, and `cuems-common`'s just-committed
`Breaks: (<< 0.3.2~)` admitted both. The release line advances `0.3.x`'s last component almost
daily, so following rule 1 literally means chasing it. **Decision (maintainer): `0.4.0-1`**, and
`cuems-common`'s `Breaks: cuems-power-bridge (<< 0.4.0~)`. That leaves the `0.3.x` series to the
release line. It is a **recorded exception** to rule 1's "last component advances" for this
package, justified by its real compatibility break (`node_role`, `cluster_poweroff`, the
`cuemsutils 0.1.1` floor). Verified with `dpkg`: `<< 0.4.0~` breaks `0.3.0-11` … `0.3.2-2` and
`0.3.9-1`, and admits `0.4.0~rc1` and `0.4.0-1`. Because `901a5ba` (common) and `055ec52` (utils:
`CHANGELOG.md`, `test_release_matrix.py`) named `0.3.2-1`, both were **amended** under FR-021, and
their dependents re-ran. ⚠ The power-bridge maintainers must be told the refactor's number. That is
outward-facing, so it is the maintainer's to send.

### R2b — the same race in `cuems-frontend`: `0.2.0` (maintainer decision, 2026-10-16)

At Phase 9, after `npm version 0.1.0 --no-git-tag-version` and before the commit, the tag list showed
**`v0.1.0-rc1`**, created on 2026-10-16 by the frontend's own line on **`origin/dev`**
(`6dc775c`, "stop-project show badge"). It is pushed and is not an ancestor of the refactor. Its
`package.json` still says `0.0.0`. The planning document's "no tag history" was true until that day.
`0.1.0` sorts above `0.1.0-rc1`, but `dev`'s next cut is plainly `v0.1.0`, which would be a second,
different `0.1.0`. **Decision (maintainer): `0.2.0`**, leaving `0.1.x` to `dev`, the same remedy as
R2a. No package relation names the frontend, so nothing else moves. Because `67df8bc` named
`0.1.0` (`CHANGELOG.md`, `test_release_matrix.py`), the `cuems-utils` bump was amended again, and
every dependent build, suite and demo re-ran (FR-021). ⚠ The frontend maintainers must be told the
refactor's version. That is outward-facing, so it is the maintainer's to send.

## R3 — `cuems-utils 0.1.0rc17` is released, and 0.1.1 is behind it in content

`origin/release/0.1.0rc17` (`ee3de82`, 2026-10-15) adds `stop_project` to `script.xsd`'s
`ActionType`. Its changelog says *"Every box of a cluster needs >= 0.1.0rc17 before a project
carrying the cue is saved: older utils reject it"*. `cuems-engine 0.1.0rc6-5` depends on
`cuemsutils>=0.1.0rc17` for it.

- **Version**: `0.1.0rc17` sorts below `0.1.1`, so there is no collision, and the consumer floor
  `>= 0.1.1` refuses it. That is correct, because rc17 has none of the migrated API. US2 scenario 1
  now includes it.
- **Content**: **`0.1.1` as bumped here does not accept `stop_project`.** A project saved by an
  rc17 cluster would be refused by a node upgraded to `0.1.1`. This is a new instance of what
  FR-010 defers: it is not fixed here (Clarifications Q2: no code coordination in this feature),
  but it is the sharpest reason the set must not be published before the reconciliation. It goes
  into `cuems-utils`' and `cuems-engine`'s tag messages and the `CHANGELOG.md` `0.1.1` section by
  name.

---

## R4 — The relation matrix, re-measured: 24 sites change

Re-grepped on each start commit. Line numbers drift; the tasks re-grep before editing. Full table
in [`contracts/relation-matrix.md`](contracts/relation-matrix.md). Summary:

| Repo | Sites that change | Unchanged on purpose |
|---|---|---|
| `cuems-utils` | `debian/control:23` + its comment `:15-22` | — |
| `cuems-common` | `debian/control:12, :13, :57, :58` | `:49` `Suggests: cuems-power-bridge`, unversioned (010 T077) |
| `cuems-engine` | `debian/control:26, :27, :28` (+ comment `:20-21`), `:49`; `pyproject.toml:50` | `:30` `python3-pyossia (>= 2.0.0-rc6+124+cuems3)` — not an ecosystem package of this set |
| `cuems-editor` | `debian/control:18, :19, :20`; `pyproject.toml:23` | — |
| `cuems-nodeconf` | `debian/control:18, :19, :20, :28`; `pyproject.toml:28` | — |
| `cuems-power-bridge` | `debian/control:18, :19, :20, :25`; `pyproject.toml:38` | — |

The planning document said 20 sites. The difference is §4.4's `cuems-common:58` now moving (R2)
plus counting each `pyproject.toml` bound once per repository.

---

## R5 — Self-version sites

| Repo | Sites → target |
|---|---|
| `cuems-utils` | `src/cuemsutils/__init__.py:4` (also the hatch version source), `debian/changelog:1` → `0.1.1` (native, no revision) |
| `cuems-common` | `debian/changelog:1` → `1.3.1-1` |
| `cuems-engine` | `pyproject.toml:11`, `src/cuemsengine/__init__.py:5` → `0.1.1`; new `debian/changelog` head `0.1.1-1` |
| `cuems-editor` | `pyproject.toml:7`, `src/cuemseditor/__init__.py:4` → `0.1.1`; changelog `0.1.1-1` |
| `cuems-nodeconf` | `pyproject.toml:7` (`[tool.poetry]`) → `0.1.1`; changelog already `0.1.1-1` UNRELEASED; no module version constant (measured: none in `cuemsnodeconf/`) |
| `cuems-power-bridge` | `pyproject.toml:7`, `src/cuemspowerbridge/__init__.py:5` (now `0.2.0`) → `0.3.2`; changelog `0.3.2-1` |
| `cuems-frontend` | `package.json:3`, `package-lock.json:3` and `:9` (the root package entry) → `0.1.0` |

---

## R6 — Changelog shape per repository (FR-003)

Rule: a **new top entry at the target, distribution `UNRELEASED`**. An existing head entry is
**folded** into it (body moved, header dropped) only when its number was never shipped *by this
branch* and is now held by someone else's build, or was never shipped at all. Released history is
left verbatim.

| Repo | Existing head | Action |
|---|---|---|
| `cuems-utils` | `0.1.0rc16` UNRELEASED (features 011–015) | fold → `0.1.1` |
| `cuems-common` | `1.3.0-23` UNRELEASED (the handover) | fold → `1.3.1-1` (released `1.3.0-23` is a different build) |
| `cuems-engine` | `0.1.0rc2-3` bookworm, **released** (on `origin/debian/bookworm`) | keep; add `0.1.1-1` above |
| `cuems-editor` | `0.1.0rc1-4` UNRELEASED | fold → `0.1.1-1`; the older `0.1.0rc1-2 UNRELEASED` at `:40` is history, untouched |
| `cuems-nodeconf` | `0.1.1-1` UNRELEASED | keep the header; add a bump bullet (pyproject reconcile, relations) |
| `cuems-power-bridge` | `0.3.1-1` unstable, never tagged or shipped | fold → `0.3.2-1` UNRELEASED |

Every new top entry gets one bullet stating that the release line is **not yet absorbed**, naming
how far behind it is (FR-010). Maintainer line: `Adrià Masip <adria@stagelab.coop>`, the tagger
identity on the existing candidate tags.

---

## R7 — Building for Debian 12

**Decision**: one feature-local script, `specs/016-coordinated-minor-bump/tools/bookworm-build.sh
<repo-path>`, generalised from `cuems-editor/tests/packaging/bookworm-build.sh`:
`mmdebstrap --mode=unshare --variant=apt` bookworm chroot, the build dependencies from
`debian/control`, a `cuemsutils` wheel built from `UTILS=` (the `cuems-utils` checkout) offered
through `PIP_FIND_LINKS`, `dpkg-buildpackage -us -uc -b`, and evidence written to
`specs/016-coordinated-minor-bump/evidence/<repo>/bookworm-build.txt`.

- **Interpreter check**: for `cuems-utils` the built `.deb`'s `usr/lib/cuems/pyvenv.cfg` must read
  `home = /usr/bin` (CLAUDE.md's shipping check). The four sibling dh-virtualenv packages delete
  `pyvenv.cfg` from the package (cuems-utils owns `/usr/lib/cuems`), so the script runs `dh` up to
  `dh_virtualenv` first and reads it there, as the editor script does. `cuems-common` has no venv
  and gets the build check only (SC-003: 6 builds, 5 interpreter checks).
- The built package version must equal the changelog head (`dpkg-deb -f <deb> Version`).
- **Why feature-local, not in each sibling**: a build check that lives in one place has one
  behaviour, and siblings gain no file that only this feature runs. `cuems-editor`'s own script is
  left as is.
- **Rejected**: a host build (Debian 13, Python 3.13, so the wrong target); a host pyenv venv
  (proves nothing about the `.deb`); editing each `debian/rules` (forbidden by the existing
  `PIP_FIND_LINKS` approach and pointless).

Measured on the host: `mmdebstrap` 1.5.7, `dh-virtualenv` 1.2.2, `equivs`, `debhelper`,
subuid/subgid `adria:100000:65536` all present (`equivs` and `debhelper` installed by the maintainer
2026-10-15).

---

## R8 — Test environments and the two-arm comparison

**Interpreters** (Clarifications Q1): siblings run on **pyenv 3.11.9** (built
`--enable-optimizations --with-lto CC=gcc-12`, measured); `cuems-utils` on its hatch matrix
(`uvx hatch run test.py3.11:run`, uv-managed CPython 3.11.9; plus 3.12 and 3.13).

**Sibling venvs**: `<repo>/.venv` from `~/.pyenv/versions/3.11.9/bin/python -m venv`. Measured:
`.venv` is git-ignored only in `cuems-nodeconf` and `cuems-utils`. **Decision**: add `.venv/` to
each repository's local `.git/info/exclude`, **not** to `.gitignore`, so the bump commit carries no
unrelated file. `cuems-engine/.venv` exists, holding only a `pyvenv.cfg`, and is rebuilt.

**Two library worktrees** (both clean, so no evidence is ever stamped `(+ uncommitted changes)`):

- `.016-utils-start` at `b83d5c2`, the library as it was;
- `.016-utils-bump` at the `cuems-utils` **bump commit**, which is made **first** (spec FR-016).
  It is the only `cuemsutils 0.1.1` that exists, and every sibling's `dh_virtualenv` pip must
  resolve `cuemsutils>=0.1.1` from it (analyze C1: measured, all four Python siblings'
  `debian/rules` run `dh_virtualenv` with dependency resolution).

**Install**: `pip install -e <repo>` plus its test extras, and `cuemsutils` editable from one of the
worktrees, `--no-deps`.

- `--no-deps` is needed because the bumped siblings require `cuemsutils>=0.1.1,<0.1.2`, and
  `cuemsutils` is still `0.1.0rc16` until `cuems-utils` commits last.
- A **worktree, not the live checkout**: the live `cuems-utils` tree is on this feature branch and
  changes during the feature. Feature 014's gate-prompt defect (parallel sessions sharing one
  checkout) is the precedent.

**Three runs per sibling** (FR-007):

- **start run** (Phase 2, before any edit): sibling at start, library `.016-utils-start`. This is
  the true starting state.
- **arm A** / **arm B** (after the sibling's bump): sibling at its start / bump commit, **both on
  `.016-utils-bump`**. The only variable is the sibling's own change. Compare by test id: a failure
  in B and not in A is the sibling bump's.
- **start run vs arm A** differ only in the library, so they isolate the library bump's effect on
  that sibling. This replaces the earlier separate "ecosystem pass", which was needed only while
  `cuems-utils` committed last. Measured: no sibling test reads `cuemsutils.__version__` or
  `REMOVAL_RELEASE` today.

**Amend coherence** (spec FR-021): if the `cuems-utils` bump is amended after siblings used it,
`.016-utils-bump` is moved to the new hash (`git -C .016-utils-bump switch --detach <new>`), and every
sibling build, demonstration and arm-A/B run already done is repeated.

**`cuems-engine`**: resolved (FR-020, research R16): the real `pyossia` from the pinned `cuems3` wheel, two CI passes.

**`cuems-frontend`**: `npm ci`, `npm run build`, and
`CHROME_BIN=/usr/bin/google-chrome npm run test:ci` (CLAUDE.md), both arms.

---

## R9 — Tests in siblings that pin the moving versions

Measured with a grep for the old literals (`0.1.0rc16`, `1.3.0-23`, `0.1.0-8`, `0.3.1-1`,
`0.1.0rc1-4`, `0.1.0rc7`, `<< 0.1.1`) in `tests/`. These move **in the same commit** as the bump,
or arm B fails by construction:

| Repo | File | Why |
|---|---|---|
| `cuems-common` | `tests/test_version_bounds.py` | `REFUSED`/`ADMITTED` lists for the `cuems-utils` bound → refused `…rc16, rc17, 0.1.2~rc1, 0.1.2`; admitted `0.1.1, 0.1.1-1, 0.1.1+b1` |
| `cuems-common` | `tests/test_network_map_handover.py`, `tests/test_template_consumers.py` | read and decide per occurrence (some are history, e.g. "since 1.3.0-23") |
| `cuems-common` | `tests/packaging/release-gate-demo.sh`, `stubs/cuems-nodeconf-renamed.ctl` | FR-011 |
| `cuems-nodeconf` | `tests/test_library_prerequisite.py`, `tests/test_service_record.py` | read and decide; the prerequisite test is commit-based by design and may only need its prose |
| `cuems-nodeconf` | `tests/packaging/release-gate-demo.sh`, `stubs/cuems-utils.ctl`, `stubs/cuems-nodeconf.ctl` | FR-011 |
| `cuems-editor` | `tests/packaging/bookworm-build.sh` | comment ("`cuemsutils >= 0.1.0rc16` is not on PyPI") |
| `cuems-engine` | `tests/test_mtclistener.py` | a match on one of the literals; read before deciding, may be unrelated |

**Decision**: each occurrence is read, then either moved or left as history. The task records which
for each occurrence. A literal that describes past history ("introduced in `1.3.0-23`") stays.

---

## R10 — Install demonstrations (FR-011)

| Script | Variable | Today | Becomes |
|---|---|---|---|
| `cuems-common/tests/packaging/release-gate-demo.sh` | `UTILS_VERSIONS` (`:39`) | `0.1.0rc14 0.1.0rc15 0.1.0rc16 0.1.1~rc1` | `0.1.0rc16 0.1.0rc17 0.1.1 0.1.2~rc1` |
| same | `OLD_REF` (`:36`) | `rc_1` (moving; `1.3.0-25` today) | passed explicitly as `v1.3.0-25` |
| same | scenario titles and expectations naming `0.1.0-8`, `1.3.0-22/23` (18 hits) | old edges | the new edges: `cuems-nodeconf` `0.1.0-9` refused, `0.1.1-1` admitted |
| `cuems-nodeconf/tests/packaging/release-gate-demo.sh` | `UTILS_VERSIONS` (`:59`) | `0.1.0rc15 0.1.0rc16 0.1.1~rc1` | `0.1.0rc16 0.1.0rc17 0.1.1 0.1.2~rc1` |
| same | `OLD_REF` (`:52`) | `478bc49` (`0.1.0-7`) | passed: `origin/rc_1` (`0.1.0-9`) |
| same | `COMMON_NEW` (`:54`) | `1a00159` (`1.3.0-23`) | passed: `cuems-common`'s bump commit |
| same | `COMMON_OLD` (`:55`) | `rc_1` | passed: `v1.3.0-25` |
| same | scenario text (20 hits) | old edges | new edges |
| both | `OUT` | the writing feature's evidence | **passed**: `specs/016-coordinated-minor-bump/evidence/<repo>/release-gate-demo.txt` *in `cuems-utils`* |
| both | `UTILS` | `../cuems-utils` | **passed**: `/disk/Projects/StageLab/.016-utils-bump` (clean, at the bump; analyze C1/I1) |

**Decision on where the evidence lives**: in this feature's directory, not the sibling's, so the
feature record is in one place (scope exception) and no sibling evidence file is overwritten.

**Run point**: at each repository's **committed** bump (the demos refuse a dirty tree as evidence,
planning document §11.1 step 1). `cuems-nodeconf`'s demo needs `cuems-common`'s bump commit, which
FR-016's order already provides. These runs are **not** the validation on re-cut tags (planning
document rule 5, §11 step 9). That stays the maintainer's, after the re-cut, and the record says so.

---

## R11 — `cuems-utils`' own changes

- **`v0.1.1` → `v0.1.2`** at the 13 sites in `src/`, `tests/`, `README.md`, `docs/index.md`,
  `CHANGELOG.md:166`, `debian/changelog:94` (measured with `git grep`). `REMOVAL_RELEASE` at
  `src/cuemsutils/_deprecation.py:26` is the load-bearing one. The test literal at
  `tests/contract/test_validate_advice_per_schema.py:91` is **derived from `REMOVAL_RELEASE`**
  instead of re-pinned.
- **Removal document rename**: `git mv specs/planning/deprecated-surface-removal-v0-1-1.md
  …-v0-1-2.md`. 16 files cite the old name (measured, one more than the planning document's 14:
  `src/cuemsutils/xml/settings.py`).
  - **Re-pointed**: `CLAUDE.md`, `specs/planning/*`, `src/`, `tests/`, and `specs/010-*`, which is
    open (68/118).
  - **Left as frozen record**: `specs/014-*` and `specs/015-*`, both landed. This **deviates from
    the planning document's §8**, which listed 014 as editable. This repository's policy on landed
    specs governs.
- **`tests/packaging/test_no_version_bump.py`** is rewritten, not deleted (FR-013), in **two
  steps** because the bump commit precedes the siblings (analyze A1):
  - It is renamed, for example to `test_release_matrix.py`. Its premise reverses, so the name has to.
  - `PINNED` becomes the full matrix: the six packaged repositories plus `cuems-frontend`'s `0.1.0`.
  - **This repository's half** asserts the changelog head and `__version__` at `0.1.1`. It fails
    at `b83d5c2` and passes after the bump (SC-TEST-001).
  - **The siblings' half** keeps 015's FR-080c rule: assert **at the sibling's candidate tag**,
    never its tip. Those tags are re-cut by the maintainer after this feature, so until then this
    half is `xfail(strict=True, reason="until the maintainer re-cuts xml-refactor-merge-candidate")`.
    The day the tags are re-cut it turns `XPASS` and fails, which forces the marker's removal.
    That is the same mechanism `cuems-editor`'s UR-5 used.
  - A second assertion checks the siblings' **`feat/xml-refactor` heads** without `xfail`. That is
    what this feature itself guarantees, so it is added in the **record commit**, once those heads
    exist. In the bump commit it would fail by construction.
- **`CHANGELOG.md`**: the `## 0.1.1 — Unreleased` section stays undated (publication dates it). It
  gains a *Not yet reconciled* subsection naming `0.1.0rc16+1` (`CACHEDIR.TAG`) and `0.1.0rc17`
  (`stop_project`). The two older `## Unreleased` sections are left in place; folding them is
  publication-time editing.
- **`CLAUDE.md`**: correct the `debian/bookworm` / `packaging-rc14` paragraph (measured: the tag
  does not exist, and the branch carries `0.1.0rc16+1`), and add a Recent Changes entry.
- **Planning document**: updated, not deleted (FR-017), with R1's, R2's and R3's corrections.

---

## R12 — Tag messages

Measured: `cuems-common`, `cuems-nodeconf`, `cuems-power-bridge` and `cuems-frontend` carry an
annotated, signed `xml-refactor-merge-candidate`. `cuems-utils`, `cuems-engine` and `cuems-editor`
carry none. `../.xml-refactor-tag-messages/` is empty.

**Decision**: one file per repository, `../.xml-refactor-tag-messages/<repo>.txt`, applied by the
maintainer with `git -C <repo> tag -s -f -a xml-refactor-merge-candidate -F <file> <commit>`. The
existing messages' house style is kept: a subject line, a *what this candidate carries* narrative, a
*pairs with* paragraph naming counterpart commits, test counts. For a re-cut tag, a `RELOCATED from
<old commit>` opening is added. The required fields are in
[`contracts/tag-message.md`](contracts/tag-message.md).

A `../.xml-refactor-tag-messages/README.md` records the order (`cuems-utils` last), the
apply command, and the verification (`git rev-parse <tag>^{commit}` against each file's named
commit, never `git rev-parse <tag>`, per feature 015).

---

## R13 — Order, commits and the stop

FR-016 order (revised by analyze C1): **`cuems-utils` bump** → `cuems-common` → `cuems-nodeconf` →
`cuems-power-bridge` → `cuems-engine` → `cuems-editor` → `cuems-frontend` → **`cuems-utils` record
commit + message**. Mandatory: FR-020 does not relax it (Clarifications).

- **One bump commit per sibling**, GPG-signed, unpushed. Message style:
  `chore(release): <pkg> <target> — coordinated xml-refactor minor (cuems-utils 016)`.
- **Corrections** at a stop are amended into it (FR-021). The record notes the replaced hash and the
  tag message is rewritten.
- **`cuems-utils` gets two commits on `016-coordinated-minor-bump`**:
  1. the **bump commit**: version, `REMOVAL_RELEASE`, the relation, tests, rename, docs;
  2. a final **record commit**: `CLAUDE.md` Recent Changes, the planning-document update, and this
     feature's evidence and records, which have to name the sibling hashes and the bump commit itself.

  Splitting them keeps the bump commit's location clean, which is the purpose of FR-021, and is
  not a fix commit.
- **The `cuems-utils` candidate tag goes on the record commit** (maintainer decision, analyze I2).
  *Superseded 2026-10-16: after the maintainer merged 016 into `feat/xml-refactor`, the tag goes on that
  branch's head, like every sibling's.* The original reasoning was:
  it is the head of `016-coordinated-minor-bump` and carries the complete record. The message also
  names the bump commit, for reference.
- Merging `016-coordinated-minor-bump` into `feat/xml-refactor` in `cuems-utils` is the
  maintainer's, as with every feature here. Until then the `cuems-utils` candidate commit is on the
  016 branch, and the message says so.

---

## R15 — `cuems-power-bridge` builds its own `cuemsutils` wheel (analyze C2)

Measured: `cuems-power-bridge/debian/rules` has `CUEMS_UTILS_SRC ?= $(CURDIR)/../cuems-utils` and
builds a wheel from that path itself; it also prints "`cuemsutils >=0.1.0rc16` is not on PyPI".
**Decision**: `tools/bookworm-build.sh` passes `CUEMS_UTILS_SRC=<path inside the chroot>` pointing
at a copy of `.016-utils-bump`, on the `dpkg-buildpackage` environment (make picks up `?=`
variables from the environment). `debian/rules` is not restructured; its stale message text is a
literal reviewed and moved in the power-bridge bump (`>=0.1.1`).

## R16 — The engine's own inputs (second analyze, 2026-10-15)

Source: `../cuems-engine/specs/planning/coordinated-release-inputs-pyossia-and-engine-ci.md`, and
the commits `fc9e9af` (pyossia pinned in the dev group, relock rc14 → rc16), `729f8b6` (CI in a
`debian:bookworm` container) and `7d0bda3` (the document). Measured: none of them touches
`debian/`, `src/cuemsengine/__init__.py`, or `pyproject.toml:50`, so the relation sites hold.

- **`pyossia` (FR-020)**: the engine's `[tool.poetry.group.dev.dependencies]` pins
  `pyossia = { url = …/v2.0.0-rc6%2B124%2Bcuems3/pyossia-2.0.0rc6+124.cuems.3-cp311-cp311-linux_x86_64.whl }`
  (`pyproject.toml:84`). It needs GLIBC ≥ 2.34 and loads on Debian 13 (this host) and 12.
  **Venv recipe** (T003): from pyenv 3.11.9, `pip install -e .` (main dependencies through
  poetry-core), then the dev group's packages read from `pyproject.toml` (`pytest`, `pytest-cov`,
  `pytest-xdist`, `pytest-mock`, `anyio`, …), **including the wheel URL**, then
  `pip install --no-deps -e <cuemsutils worktree>`, and `pip install poetry==2.4.1` (CI's pin) for
  FR-022's test. Never a full `poetry install` (it would replace the editable `cuemsutils` with
  PyPI's). Check: `pyossia.__version__ == "2.0.0rc6+124.cuems.3"`.
- **The suite** is two passes, as CI runs it: `-m "not integration" -n auto` and
  `-m "integration and not slow"`. The engine document's dev-box baseline is **885 + 32 passed**.
  The one known full-suite failure, `test_project_go_from_controller`, is marked slow and is
  outside both passes.
- **The lock (FR-022)**: the engine is the only repository with a lock file (measured: no
  `poetry.lock`, `uv.lock` or `requirements*.txt` elsewhere). Relocking against `>=0.1.1` cannot
  resolve before publication. **Decision (maintainer)**: no relock. The bump commit adds
  `tests/test_lock_is_current.py`, which runs `poetry check --lock` in the repository root and is
  marked `xfail(strict=True, reason="poetry.lock relocks at publication, once cuemsutils 0.1.1 is
  resolvable (cuems-utils 016, FR-022)")`. If `poetry` is not on `PATH`, it calls `pytest.fail`, not
  skip: a skipped strict-xfail would hide the obligation.
- **`libmtcmaster` (FR-023)**: loaded by `src/cuemsengine/core/libmtc.py` (`libmtcmaster.so.0`),
  declared by no package. Measured in `../libmtcmaster`: the published release is GitHub
  `v0.0.2-0` (`libmtcmaster_0.0.2-0_amd64.deb`, which the engine CI downloads at `ci.yml:95`). The
  `v0.0.2-rc1`/`rc2` tags only carry `0.0.2-1 UNRELEASED`. Package name `libmtcmaster`.
  **Decision**: add `libmtcmaster (>= 0.0.2-0)` to `cuems-engine`'s `Depends:`, directly after
  `python3-pyossia`, with no bump and no edit to libmtcmaster. Verified with `dpkg`: `0.0.1-1` and
  `0.0.2~rc1` are refused; `0.0.2-0` and `0.0.2-1` are admitted.
  ⚠ The `libmtcmaster` package itself depends on `cuems-utils` (the engine document §4.4), so a
  bookworm install pulls `cuems-utils` in. That is harmless for the engine, which depends on it
  anyway. Asking libmtcmaster's maintainers to drop it stays an open item there.
- **libossia** is an **independent input**: `python3-pyossia (>= 2.0.0-rc6+124+cuems3)` and the
  dev-group wheel are unchanged and move together when libossia releases (its next stable is
  `v2.0.1-cuems`).
- **Out of scope, recorded with owners**: `iproute2`/`procps` (implicit, `Priority: important`,
  owner: engine); the `rtpmidid` tag/version mismatch and whether `librtpmidid0` is needed (owner:
  rtpmidid fork); engine CI under rule 5 (§4.3 options A/B) and `poetry check --lock` in CI (owner:
  maintainer, after the re-cut); "one version source per repository" (engine doc §5, future work).
- **Verdict interpreter** (second analyze, E7): pyenv 3.11.9's base interpreter has no `packaging`
  (measured: `ModuleNotFoundError`). `tools/verdicts.sh` runs its Python half through
  `uvx --from packaging python`, leaving the pyenv base untouched.

## R14 — Performance (FR-PERF-001)

No runtime path changes. The suite budget is per-test time within **115%** (015's tolerance),
interleaved: per repository, arm A, arm B, arm A, arm B. **Three samples per arm** (015's sampling
lesson: one window is not evidence). For siblings, 3+3 runs × 6 suites is affordable (each suite
takes seconds to about a minute). `cuems-utils`: three samples per arm on `test.py3.11`, about 25 s each.
