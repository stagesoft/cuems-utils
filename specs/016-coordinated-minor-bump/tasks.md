<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Tasks: Coordinated minor version bump and candidate-tag re-cut preparation

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)
**Tests**: required by the constitution. Here they are the suites' start/A/B comparison, the
relation verdicts (fail-before, pass-after), the bookworm builds, the install demonstrations, and
`cuems-utils`' rewritten release-matrix test.
**Revision**: rewritten 2026-10-15 after `/speckit-analyze`. Engine phase revised after the second analyze (FR-020 resolved, FR-010a re-measured, FR-022 lock guard, FR-023 `libmtcmaster`). C1 fixed the commit order: the
`cuems-utils` bump comes **first** and its record commit and tag message come **last**. I2 puts the
`cuems-utils` tag on the record commit. U1 makes an amend re-run its dependents. I3 makes the order
mandatory.

## Organization — by repository, not by story (deliberate)

The maintainer asked for tasks **split per repository**, with a stop after each, in the sequence
checkout → validate version → bump → bookworm build → test → tag message → commit. The five user
stories each cut across all seven repositories, so **phases are repositories in FR-016's order**,
and every task carries the **story it serves**:

| Label | Story | Typical tasks |
|---|---|---|
| `[US1]` | every package carries a version nobody else shipped | version sites, changelog, suite runs |
| `[US2]` | the set installs together and refuses mixed sets | relations, verdicts, install demonstrations |
| `[US3]` | each package builds for bookworm from local sources | bookworm build + interpreter check |
| `[US4]` | the maintainer can re-cut from prepared messages | tag messages + verification, records |
| `[US5]` | the deprecation timetable moves to `v0.1.2` | `cuems-utils` only |

A story is **complete** only when its tasks are done in all seven repositories (see *Dependencies*).
The **STOP** tasks (T034, T051, T065, T078, T093, T106, T114, T125) are review gates for a whole
repository, so they carry no story label.

## Conventions used by every task

- Paths: `/disk/Projects/StageLab/` is the parent. `F` = `/disk/Projects/StageLab/cuems-utils/specs/016-coordinated-minor-bump`.
  `TM` = `/disk/Projects/StageLab/.xml-refactor-tag-messages`. `US` = `/disk/Projects/StageLab/.016-utils-start`
  (worktree at `b83d5c2`). `UB` = `/disk/Projects/StageLab/.016-utils-bump` (worktree at the
  `cuems-utils` bump commit, created in T024).
- **Re-grep before editing.** Line numbers in contracts and research were measured 2026-10-15.
- **Commits**:
  - Siblings work **on `feat/xml-refactor`**; `cuems-utils` works on `016-coordinated-minor-bump`.
  - Every commit is signed with `git commit -S`. On "gpg failed to sign", retry; **never** use
    `--no-gpg-sign`.
  - **Never push**, never run `git tag`.
  - Sibling subject: `chore(release): <package> <target> — coordinated xml-refactor minor (cuems-utils 016)`.
    The body lists the relation rows changed and says the release line is not yet reconciled.
    End with the session's co-author trailer.
- **Amend (FR-021)**: a correction at a stop is `git commit -S --amend`. Record the replaced hash
  under `bump_commit.replaced` and regenerate that repository's tag message. **If later phases have
  already used the amended commit, re-run them** and record it under `reruns`:
  - an amend of the `cuems-utils` bump means `git -C UB switch --detach <new>`, then every sibling
    build, demonstration and arm A/B already done is repeated;
  - an amend of `cuems-common` means `cuems-nodeconf`'s demonstration is repeated (if it already ran).

  Then update the `Pairs with` lines in the messages already written.
- **Suite protocol (FR-007, R8, R14)** for a sibling, after its bump commit, with its `.venv` on `UB`:
  1. Interleave three times: `git switch --detach <start>`, run arm A; then `git switch feat/xml-refactor`, run arm B.
  2. Each run is `.venv/bin/python -m pytest -q -p no:cacheprovider -rfE`. Append to `F/evidence/<repo>/suite-A.txt` / `suite-B.txt`.
  3. Compare failing ids. B and not A means a new failure, which **stops the phase**. Then compare
     arm A with the Phase 2 start run (`suite-start.txt`): any difference is the **library** bump's
     effect (`library_effect`), and is investigated.
  4. Record counts, ids, `sys.executable` and wall times in `F/records/<repo>.md`. Per-test time
     must stay within 115% (FR-PERF-001).
- **Evidence** is **added, never overwritten**. Reruns get `-2`, `-3`… suffixes. Build and demo
  evidence must not carry `(+ uncommitted changes)` (SC-004): `UTILS=` is always `UB`.

---

## Phase 1: Setup (shared infrastructure)

**Purpose**: records, worktree, environments and tools. No repository is edited.

- [ ] T001 Create `F/records/` and `F/evidence/{cuems-common,cuems-nodeconf,cuems-power-bridge,cuems-engine,cuems-editor,cuems-frontend,cuems-utils}/`, and seed `F/records/<repo>.md` for all seven repositories plus `F/records/preflight.md` from the field lists in `F/data-model.md` (empty values)
- [ ] T002 Create the start worktree: `git -C /disk/Projects/StageLab/cuems-utils worktree add /disk/Projects/StageLab/.016-utils-start b83d5c2`; verify `grep __version__ US/src/cuemsutils/__init__.py` prints `0.1.0rc16`
- [ ] T003 [P] For each of `cuems-nodeconf`, `cuems-power-bridge`, `cuems-engine`, `cuems-editor`:
  - append `.venv/` to `<repo>/.git/info/exclude` if absent (never `.gitignore`);
  - recreate `<repo>/.venv` with `~/.pyenv/versions/3.11.9/bin/python -m venv`;
  - install the repository editable with its test extras (from `[project.optional-dependencies]` / `[tool.poetry.group.*]`), plus `pytest` and `pytest-mock`;
  - `pip install --no-deps -e US`;
  - record `sys.executable` and `cuemsutils.__file__` in `F/records/preflight.md`.

  **`cuems-engine` differs** (FR-020, research R16): after `pip install -e .`, install its dev-group packages read from `[tool.poetry.group.dev.dependencies]` (`pytest`, `pytest-cov`, `pytest-xdist`, `pytest-mock`, `anyio`, …), **including the pinned `pyossia` wheel URL** (`pyproject.toml:84`), plus `poetry==2.4.1` for the FR-022 test. Then `pip install --no-deps -e US`. **Never** a full `poetry install` in this venv. Check `python -c "import pyossia; print(pyossia.__version__)"` → `2.0.0rc6+124.cuems.3`
- [ ] T004 [P] For `cuems-common` (no Python package): create `cuems-common/.venv` from pyenv 3.11.9 with `pytest`, the same way and with the same exclude
- [ ] T005 [P] In `cuems-frontend`, run `npm ci`, then confirm `npm run build` and `CHROME_BIN=/usr/bin/google-chrome npm run test:ci` both run, and record the pass counts in `F/records/preflight.md`
- [ ] T006 Write `F/tools/bookworm-build.sh <repo-path>` per research R7 and R15, generalised from `cuems-editor/tests/packaging/bookworm-build.sh`:
  - env: `UTILS=` (a **clean** cuems-utils checkout; refuse with exit 2 if `git status --porcelain` is non-empty), `OUT=`, `WORK=`, `MIRROR=`;
  - an `mmdebstrap --mode=unshare --variant=apt` bookworm chroot that installs the Build-Depends parsed from `<repo>/debian/control`;
  - a `cuemsutils` wheel built from `UTILS`, offered via `PIP_FIND_LINKS`;
  - for `cuems-power-bridge`, also a copy of `UTILS` inside the chroot, passed as `CUEMS_UTILS_SRC=<that path>` on the `dpkg-buildpackage` environment;
  - `dpkg-buildpackage -us -uc -b`.

  The evidence records: the repository commit plus a `(+ uncommitted changes)` flag, the UTILS commit, every `.deb` produced, `dpkg-deb -f <deb> Version` against `dpkg-parsechangelog -S Version`, and for dh-virtualenv packages the venv `home`. `home` is read from the built `.deb` for `cuems-utils`, and from the pre-`dh_virtualenv` copy for siblings, as the editor script does. Exit 0 only if the build succeeded, the versions match, the expected binary set exists, and `home = /usr/bin` (or "no venv" for `cuems-common`). `chmod +x`
- [ ] T007 **Engine inputs gate** (FR-020, FR-010a): confirm `cuems-engine` is at `7d0bda3` or newer, with `fc9e9af` and `729f8b6` present, and that the `cuems3` wheel URL at `pyproject.toml:84` is reachable (`curl -sfI`). Record both in `F/records/preflight.md`. If the engine moved again past `7d0bda3`, re-read its `specs/planning/coordinated-release-inputs-pyossia-and-engine-ci.md` for changes before Phase 7

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the preflight passes, the verdicts fail-before, and every start state is known, **before any repository is edited**.

- [ ] T008 Run the FR-018 preflight per `F/quickstart.md` §0 and write `F/records/preflight.md`, one row per item:
  - tools, subuid/subgid, and pyenv 3.11.9 `CONFIG_ARGS` (`--enable-optimizations --with-lto`, `CC=gcc-12`);
  - `commit.gpgsign` in all seven repositories, plus a signing test;
  - mirror and PyPI reachable;
  - `uvx hatch run test.py3.11:run -- --co -q` collects;
  - every venv from T003/T004 imports `cuemsutils` from `US`; the frontend from T005;
  - `TM` exists and is empty, or holds only this feature's files;
  - all seven repositories clean and 0/0 with origin (`cuems-utils`: `016-coordinated-minor-bump`, only docs commits past `b83d5c2`);
  - `cuems-engine/.venv` imports `pyossia` at `2.0.0rc6+124.cuems.3` and has `poetry` 2.4.1 (FR-020, FR-022).

  Anything needing root goes to the maintainer as one exact command. **Re-run until every row is ✅.**
- [ ] T009 [P] Write `F/tools/verdicts.sh`. It reads the **current** `debian/control` and `pyproject.toml` of every repository and judges every row of `F/contracts/relation-matrix.md` § Verdicts, **including row 25** (`libmtcmaster`; absent before, so FAIL). The Debian relations use `dpkg --compare-versions`; the Python bounds use `packaging.specifiers.SpecifierSet` through **`uvx --from packaging python`** (the pyenv base has no `packaging`; research R16). It prints `site edge candidate expected observed OK|FAIL` and exits non-zero on any FAIL. Run it now: it **must FAIL**. Save the output to `F/evidence/relation-verdicts-before.txt` (SC-002 fail-before)
- [ ] T010 [P] **Start run** of every suite, with everything at its start: siblings via their `.venv` on `US` (`cuems-engine`: its two CI passes, `-m "not integration" -n auto` then `-m "integration and not slow"`); `cuems-utils` via `uvx hatch run test.py3.11:run -- -q`; the frontend via `npm run test:ci`. Append to `F/evidence/<repo>/suite-start.txt`, and record the pre-existing failures by id in `F/records/<repo>.md`
- [ ] T011 Write `TM/README.md` per `F/contracts/tag-message.md` § The folder's README: the order, the apply command, the `^{commit}` check, and that pushing is separate and maintainer-only. Record the current tag commits in `F/records/preflight.md`: `cuems-common e3c9430`, `cuems-nodeconf 5be6cf0`, `cuems-power-bridge 399baf7`, `cuems-frontend f5453a3`; none in utils, engine or editor. Also record each `origin/<branch>` hash, for SC-006

**Checkpoint**: the preflight is clean, the verdicts fail against today's bounds, and every suite's start state is known.

---

## Phase 3: `cuems-utils` bump → `0.1.1` (FIRST — row 1, the deprecation timetable)

**Goal**: the only `cuemsutils 0.1.1` that exists, committed, so every sibling build can resolve it.
**Independent test**: the release-matrix test's own-repository half fails at `b83d5c2` and passes at the bump. Ruff 0, mypy ≤ 72. The build gives `0.1.1` with `home = /usr/bin`. Row 1's verdicts are OK.

- [ ] T012 [US1] Verify `cuems-utils` is on `016-coordinated-minor-bump`, whose only commits past `b83d5c2` are this feature's docs commit(s); the tree is clean. Measure and record in `F/records/cuems-utils.md`:
  - `src/cuemsutils/__init__.py:4` and `debian/changelog:1` (`0.1.0rc16 UNRELEASED`);
  - the release line `origin/debian/bookworm` (`0.1.0rc16+1`) and `origin/release/0.1.0rc17`, and the highest version on any remote branch;
  - `dpkg --compare-versions 0.1.1 gt <high-water>`;
  - behind/ahead (73) and the absent entries
- [ ] T013 [P] [US1] Set `src/cuemsutils/__init__.py:4` to `__version__ = "0.1.1"`. In `debian/changelog`, fold the `0.1.0rc16 UNRELEASED` head into `cuems-utils (0.1.1) UNRELEASED; urgency=medium` (FR-003 fold). Add bullets:
  - bump;
  - removal release `v0.1.2`;
  - row 1;
  - "release line debian/bookworm (0.1.0rc16+1: CACHEDIR.TAG) and release/0.1.0rc17 (stop_project in script.xsd ActionType) not yet absorbed — a project saved by an rc17 cluster with a stop_project cue is refused by 0.1.1; do not publish until reconciled".

  Fix `debian/changelog:94-95` ("REMOVED IN v0.1.1… << 0.1.1~") → `v0.1.2` / `<< 0.1.2~`
- [ ] T014 [P] [US5] Set `src/cuemsutils/_deprecation.py:26` to `REMOVAL_RELEASE = "v0.1.2"` and update its prose at `:11` and `:25`. Then `v0.1.1` → `v0.1.2` at:
  - `src/cuemsutils/timeoutloop.py:5`, `src/cuemsutils/tools/CTimecode.py:222`;
  - `src/cuemsutils/xml/xml_reader_writer.py:204`, `src/cuemsutils/xml/XmlReaderWriter.py:4`, `src/cuemsutils/xml/Settings.py:4`, `src/cuemsutils/xml/CMLCuemsConverter.py:4`, `src/cuemsutils/xml/__init__.py:14`;
  - `README.md:117`, `docs/index.md:103`, `CHANGELOG.md:166`.

  Re-run `git grep -n 'v0\.1\.1\b' -- src tests README.md docs CHANGELOG.md debian`; only history may remain (SC-007)
- [ ] T015 [P] [US5] Tests:
  - `tests/contract/test_deprecation_shims.py:171` and `tests/unit/test_ctimecode.py:406` (+ docstring `:403`) → `"v0.1.2"`;
  - `tests/contract/test_validate_advice_per_schema.py:91` → `assert f"removed in {REMOVAL_RELEASE}" in …`, with `from cuemsutils._deprecation import REMOVAL_RELEASE`, derived rather than re-pinned
- [ ] T016 [US1] Release-matrix test, **step 1 of 2** (FR-013, research R11). `git mv tests/packaging/test_no_version_bump.py tests/packaging/test_release_matrix.py` and rewrite it:
  - `PINNED` = `{cuems-utils: 0.1.1, cuems-common: 1.3.1-1, cuems-nodeconf: 0.1.1-1, cuems-power-bridge: 0.3.2-1, cuems-engine: 0.1.1-1, cuems-editor: 0.1.1-1, cuems-frontend: 0.1.0}`;
  - `test_this_repository_is_at_0_1_1`, which asserts the changelog head **and** `__version__`;
  - `test_siblings_at_their_candidate_tags`, parametrised over the six, using `tests.support.sibling_tags.tagged`, with `xfail(strict=True, reason="until the maintainer re-cuts xml-refactor-merge-candidate (016)")`.

  The docstring states the reversed premise. **No sibling-head assertion yet** (T117). Prove fail-before by running the new file against the `US` tree, and save to `F/evidence/cuems-utils/release-matrix-fail-before.txt`
- [ ] T017 [US2] Set `debian/control:23` (row 1) to `Breaks: cuems-common (<< 1.3.1~)`, and rewrite the comment at `:15-22`: `1.3.0-23`…`-25` shipped with no handover, so the bound moves with the version (planning document §1.1)
- [ ] T018 [US5] `git mv specs/planning/deprecated-surface-removal-v0-1-1.md specs/planning/deprecated-surface-removal-v0-1-2.md`. Retitle it and apply planning document §7:
  - §1.1's table re-derived from `F/contracts/relation-matrix.md`;
  - §1.2 rebased;
  - §3's atomic step marked **fired by 016**;
  - §5 item 1 re-opened;
  - §7's example message
- [ ] T019 [US5] Re-point every citation of the old filename. Current list: `git grep -l deprecated-surface-removal-v0-1-1`. Edit `CLAUDE.md`, `specs/planning/coordinated-release-version-bump.md`, `specs/planning/etc-cuems-first-install.md`, `src/cuemsutils/tools/CTimecode.py`, `src/cuemsutils/xml/settings.py`, `tests/unit/test_ctimecode.py`, and `specs/010-consumer-migration/{baseline,contracts/release-gate,import-census,spec,tasks}.md` (010 is open). **Leave** `specs/014-*` and `specs/015-*` (frozen per FR-012). Afterwards `git grep` must show only 014/015 hits
- [ ] T020 [US2] Correct the version-bearing instructions in non-frozen documents (planning document §8, files that still exist). Re-grep each for `0.1.0rc16`, `<< 0.1.1~` and `v0.1.1`:
  - `specs/planning/etc-cuems-first-install.md` §12/§12.1 (decision reversed, its two reasons resolved);
  - `specs/planning/etc-cuems-first-install-execution.md` (`:25, 92-94, 285, 640-641`);
  - `specs/planning/tools-external-consumers-and-timeoutloop-migration.md:216`;
  - `specs/planning/xml-rebuild/010-consumer-prompts/{00-cuems-utils,01-cuems-engine,02-cuems-editor,03-cuems-common,04-cuems-nodeconf,04a-*,04b-*,07-cuems-power-bridge,README}.md`;
  - `specs/010-consumer-migration/{contracts/release-gate.md,baseline.md,tasks.md,spec.md,import-census.md,migration-guide.md}`: floor `>= 0.1.1`, ceiling `<< 0.1.2~`, T090's premise retired
- [ ] T021 [US1] In `CHANGELOG.md` `## 0.1.1 — Unreleased` (undated), add a *Coordinated release* paragraph (the versions and the `v0.1.2` removal move) and a *Not yet reconciled* subsection naming `0.1.0rc16+1` (`CACHEDIR.TAG`) and `0.1.0rc17` (`stop_project`), with "do not publish until reconciled" (FR-010)
- [ ] T022 [US1] On the working tree, run `uvx hatch run test.py3.11:run -- -q`, `uvx hatch run test.py3.11:lint` (0) and `uvx hatch run types:check` (≤ 72; SC-QUALITY-001). Fix anything this feature caused
- [ ] T023 [US1] **Bump commit** on `016-coordinated-minor-bump`, signed and unpushed, containing only T013–T021 (`git add` explicit paths; no records or evidence). Subject `chore(release): cuems-utils 0.1.1 — coordinated xml-refactor minor; removal moves to v0.1.2 (016)`. Record `bump_commit`
- [ ] T024 [US1] Create the bump worktree: `git -C /disk/Projects/StageLab/cuems-utils worktree add /disk/Projects/StageLab/.016-utils-bump <bump>`. Confirm `git -C UB status --porcelain` is empty and `__version__` is `0.1.1`
- [ ] T025 [US2] Run `F/tools/verdicts.sh`. Row 1 must be OK (sibling rows still FAIL). Append to `F/evidence/relation-verdicts-progress.txt`
- [ ] T026 [US3] `UTILS=UB OUT=F/evidence/cuems-utils/bookworm-build.txt F/tools/bookworm-build.sh /disk/Projects/StageLab/cuems-utils`. Expect `cuems-utils_0.1.1_*.deb`, and the CLAUDE.md shipping check `dpkg-deb --fsys-tarfile <deb> | tar -xO ./usr/lib/cuems/pyvenv.cfg | grep '^home'` → `home = /usr/bin`
- [ ] T027 [US1] Run the hatch suite protocol: interleave `git switch --detach b83d5c2` / `git switch 016-coordinated-minor-bump` three times on `test.py3.11`, and once each on `.py3.12` and `.py3.13`. Compare by id: the only B-only changes allowed are the T015/T016 tests. Check the 115% budget and record
- [ ] T028 [US1] In every sibling `.venv` (T003/T004), `pip install --no-deps -e UB`; confirm `cuemsutils.__version__ == "0.1.1"` and `__file__` under `UB`. From here on, sibling arms A/B run on `UB`
- [ ] T029 [US4] Seed `TM/cuems-utils.txt` as a **draft**, with the subject, version, row 1, the `v0.1.2` move, carries (features 011–016) and the reconciliation gaps. `Tag:` and `Pairs with` stay `<pending>`; T121 completes it
- [ ] T030 [US1] Record `release_gap_bump` for `cuems-utils` (behind/ahead at the bump)
- [ ] T031 [US1] Fill `F/records/cuems-utils.md` for the bump half (bump commit, build, suites, verdicts)
- [ ] T032 [US4] Write the bump half's evidence index in `F/records/cuems-utils.md`: the paths of T016's fail-before, T025, T026 and T027
- [ ] T033 [US1] Confirm `git -C /disk/Projects/StageLab/cuems-utils status --porcelain` lists only untracked `F/records`, `F/evidence` and `F/tools` (nothing tracked is modified), and that nothing is pushed
- [ ] T034 **STOP (FR-021)**: present `F/records/cuems-utils.md` (bump half) and the research R2 decision ahead of Phase 4. Wait for an explicit go-ahead and record it with its date. On a correction: amend the bump, move `UB` (`git -C UB switch --detach <new>`), and re-run T024–T032

---

## Phase 4: `cuems-common` → `1.3.1-1` (rows 2–5)

**Goal**: `cuems-common` at `1.3.1-1` UNRELEASED, rows 2–5 moved, its demonstration updated and passing.
**Independent test**: verdict rows 2–5 are OK, the suite has no new failure, the build gives `1.3.1-1`, the demonstration exits 0 with clean-checkout evidence, and `TM/cuems-common.txt` verifies.

- [ ] T035 [US1] Verify `cuems-common` is on `feat/xml-refactor` at `e595e67` (or re-measure and record a newer hash per FR-001), clean, and 0/0. Fill `start_commit`
- [ ] T036 [US1] Measure and record (FR-002, FR-010): the changelog head (`1.3.0-23 UNRELEASED`); the highest version on any remote branch (`1.3.0-25` expected) and `1.3.1-1 gt` it; behind/ahead against `origin/debian/bookworm` (22); and the absent released entries (`1.3.0-23`, `-24`, `-25`)
- [ ] T037 [US1] In `cuems-common/debian/changelog`, fold `1.3.0-23 UNRELEASED` into `cuems-common (1.3.1-1) UNRELEASED; urgency=medium`, body kept. Add bullets:
  - the coordinated minor bump;
  - rows 2–5;
  - "release line debian/bookworm (1.3.0-23…-25) not yet absorbed: N commits behind; do not publish until reconciled; re-verify relations after the merge".

  Add a fresh trailer: `Adrià Masip <adria@stagelab.coop>`, today
- [ ] T038 [US2] In `cuems-common/tests/test_version_bounds.py`: `REFUSED = ["0.1.0rc16", "0.1.0rc16+1", "0.1.0rc17", "0.1.0", "0.1.1~rc1", "0.1.2~rc1", "0.1.2"]`, `ADMITTED = ["0.1.1", "0.1.1-1", "0.1.1+b1"]`, and update the docstring's examples
- [ ] T039 [US2] Read every hit of `grep -nE '1\.3\.0-2[23]|0\.1\.0-8|0\.1\.0rc1[456]|0\.3\.1-1|<< ?0\.1\.1' cuems-common/tests/test_network_map_handover.py cuems-common/tests/test_template_consumers.py`. Move current-bound statements and keep history; record each under `literals_reviewed`
- [ ] T040 [US2] Update `cuems-common/tests/packaging/release-gate-demo.sh` per research R10:
  - `UTILS_VERSIONS=(0.1.0rc16 0.1.0rc17 0.1.1 0.1.2~rc1)`;
  - the 18 scenario hits moved to the new edges: nodeconf `0.1.0-9` broken / `0.1.1-1` accepted; utils `0.1.0rc17` refused / `0.1.1` accepted / `0.1.2~rc1` refused;
  - the `OLD_REF` default comment corrected;
  - `stubs/cuems-nodeconf-renamed.ctl` adjusted if it embeds a version
- [ ] T041 [US2] **Last edit**: `cuems-common/debian/control` rows 2–5:
  - `:12` → `cuems-utils (>= 0.1.1)`, `:13` → `(<< 0.1.2~)`;
  - `:57` → `Breaks: cuems-nodeconf (<< 0.1.1~)`, `:58` → `cuems-power-bridge (<< 0.3.2~)`;
  - the comment above `:57` explains the released `0.1.0-8`/`-9` (still `node_type`) and `0.3.1-2` (no `cluster_poweroff`, reads `node_type`; research R2).

  `:49` stays untouched
- [ ] T042 [US2] Run `F/tools/verdicts.sh`: rows 2–5 OK. Append to the progress evidence
- [ ] T043 [US1] Commit (signed, unpushed): `chore(release): cuems-common 1.3.1-1 — …`. Confirm the tree is clean. Record `bump_commit`
- [ ] T044 [US3] `UTILS=UB OUT=F/evidence/cuems-common/bookworm-build.txt F/tools/bookworm-build.sh /disk/Projects/StageLab/cuems-common`. Expect `cuems-common_1.3.1-1_all.deb` and "no venv"
- [ ] T045 [US1] Suite protocol for `cuems-common` (start `e595e67`): zero new failures, within 115%, and `library_effect` recorded
- [ ] T046 [US2] Run the demonstration at the committed bump: `cd /disk/Projects/StageLab/cuems-common && OLD_REF=v1.3.0-25 UTILS=UB OUT=F/evidence/cuems-common/release-gate-demo.txt tests/packaging/release-gate-demo.sh` (paths expanded). Exit 0, no `(+ uncommitted changes)`, and every scenario names its refusing tool
- [ ] T047 [US1] Record `release_gap_bump`
- [ ] T048 [US4] Write `TM/cuems-common.txt` per the contract:
  - start from `git cat-file -p xml-refactor-merge-candidate` with the header and signature stripped;
  - `RELOCATED from e3c9430`, `Tag: <bump>`, rows 2–5, the R2 explanation;
  - `NOT YET RECONCILED with origin/debian/bookworm` + "re-verify relations after the merge";
  - evidence paths, and "not validated on re-cut tags";
  - `Pairs with`: `cuems-utils 0.1.1` and the others as `<pending: repo>`, filled in T121.

  Verify the file
- [ ] T049 [US4] Fill `F/records/cuems-common.md` completely
- [ ] T050 [US1] Confirm nothing is pushed and no tag was touched in `cuems-common` (compare with T011)
- [ ] T051 **STOP (FR-021)**: present the record and the R2 power-bridge renumbering (`0.3.2-1`, `<< 0.3.2~`, an override of the planning document). Wait for an explicit go-ahead. On a correction: amend, re-run T042–T049, **and** T062 if `cuems-nodeconf`'s demonstration has already run

---

## Phase 5: `cuems-nodeconf` → `0.1.1-1` (rows 15–19)

**Goal**: pyproject reconciled to `0.1.1`, rows 15–19, and the demonstration run against `cuems-common`'s bump.
**Independent test**: verdict rows 15–19 OK, the suite has no new failure, the build gives `0.1.1-1`, the demonstration exits 0, and the message verifies.

- [ ] T052 [US1] Verify `cuems-nodeconf` is on `feat/xml-refactor` at `82b0a69` (or re-measure), clean, 0/0. Fill `start_commit`
- [ ] T053 [US1] Measure and record:
  - the changelog head (`0.1.1-1 UNRELEASED`) and `pyproject.toml:7` (`0.1.0`), and confirm no `__version__` exists under `cuemsnodeconf/`;
  - the highest version on any remote branch (`0.1.0-9`) and `0.1.1-1 gt` it;
  - behind/ahead against `origin/rc_1` (0/84, reconciled)
- [ ] T054 [US1] Set `pyproject.toml` `[tool.poetry] version = "0.1.1"`. In `debian/changelog`, keep the `0.1.1-1 UNRELEASED` header (FR-003, third rule) and add bullets: the pyproject reconcile, rows 15–19, "release line rc_1 fully absorbed". Refresh the trailer date
- [ ] T055 [US2] Read every hit of `grep -nE '0\.1\.0rc16|1\.3\.0-23|0\.1\.0-8|<< ?0\.1\.1' cuems-nodeconf/tests/test_library_prerequisite.py cuems-nodeconf/tests/test_service_record.py`. Move current-bound statements and keep history (the prerequisite test is commit-based by design); record each
- [ ] T056 [US2] Update `cuems-nodeconf/tests/packaging/release-gate-demo.sh` per research R10:
  - `UTILS_VERSIONS=(0.1.0rc16 0.1.0rc17 0.1.1 0.1.2~rc1)`;
  - the 20 scenario hits moved to the new edges: common `1.3.0-25` broken / `1.3.1-1` accepted; own old release `0.1.0-9`; utils as in T040;
  - the `OLD_REF`/`COMMON_NEW`/`COMMON_OLD`/`UTILS` default comments corrected;
  - `stubs/{cuems-utils,cuems-nodeconf}.ctl` adjusted if they embed versions
- [ ] T057 [US2] **Last edit**: `cuems-nodeconf/debian/control` `:18` `(>= 0.1.1)`, `:19` `(<< 0.1.2~)`, `:20` `cuems-common (>= 1.3.1~)`, `:28` `Breaks: cuems-common (<< 1.3.1~)`; and `pyproject.toml:28` `cuemsutils = ">=0.1.1,<0.1.2"` (rows 15–19)
- [ ] T058 [US2] Run `F/tools/verdicts.sh`: rows 15–19 OK
- [ ] T059 [US1] Commit (signed, unpushed): `chore(release): cuems-nodeconf 0.1.1-1 — …`. Record `bump_commit`
- [ ] T060 [US3] `UTILS=UB … F/tools/bookworm-build.sh /disk/Projects/StageLab/cuems-nodeconf`. Expect `0.1.1-1` and `home = /usr/bin`
- [ ] T061 [US1] Suite protocol for `cuems-nodeconf`, covering both of `run-tests.sh`'s parts (`tests/` and `specs/planning/yardstick/`) through `.venv/bin/python`. Zero new failures, within 115%, `library_effect` recorded
- [ ] T062 [US2] Run the demonstration at the committed bump: `OLD_REF=origin/rc_1 COMMON=/disk/Projects/StageLab/cuems-common COMMON_NEW=<cuems-common bump> COMMON_OLD=v1.3.0-25 UTILS=UB OUT=F/evidence/cuems-nodeconf/release-gate-demo.txt tests/packaging/release-gate-demo.sh`. Exit 0, clean-checkout evidence; read it
- [ ] T063 [US1] Record `release_gap_bump`
- [ ] T064 [US4] Write `TM/cuems-nodeconf.txt`: from its current tag message, `RELOCATED from 5be6cf0`, `Tag: <bump>`, rows 15–19, "rc_1 reconciled", and pairs (`cuems-utils`, `cuems-common` filled; others pending). Verify, then fill `F/records/cuems-nodeconf.md`
- [ ] T065 **STOP (FR-021)**: present and wait for an explicit go-ahead. On a correction, amend and re-run T058–T064

---

## Phase 6: `cuems-power-bridge` → `0.3.2-1` (rows 20–24)

**Goal**: `0.3.2-1` UNRELEASED (research R2), `__init__` reconciled from `0.2.0`, rows 20–24.
**Independent test**: verdict rows 20–24 OK, row 5 refuses `0.3.1-2`, the suite has no new failure, the build gives `0.3.2-1`, and the message verifies.

- [ ] T066 [US1] Verify `cuems-power-bridge` is on `feat/xml-refactor` at `dd1256f` (or re-measure), clean, 0/0. Fill `start_commit`
- [ ] T067 [US1] Measure and record:
  - the changelog head (`0.3.1-1 unstable`, never tagged), `pyproject.toml:7` (`0.3.1`), `src/cuemspowerbridge/__init__.py:5` (`0.2.0`);
  - the highest version on any remote branch (`0.3.1-2` from `origin/release/0.3.1-2`) and `0.3.2-1 gt` it;
  - behind/ahead against `origin/main` and `origin/release/0.3.1-2`, and the absent entries
- [ ] T068 [US1] Set `pyproject.toml:7` and `src/cuemspowerbridge/__init__.py:5` to `0.3.2`. In `debian/changelog`, fold the never-shipped `0.3.1-1 unstable` into `cuems-power-bridge (0.3.2-1) UNRELEASED; urgency=medium` (FR-003, first rule). Add bullets:
  - "renumbered above the released 0.3.1-2";
  - the `__init__` reconcile;
  - rows 20–24;
  - "release lines main (0.3.0-7…-11) and release/0.3.1-2 not yet absorbed — includes CACHEDIR.TAG (0.3.0-8); do not publish until reconciled; re-verify relations after the merge"
- [ ] T069 [US2] Literal review (FR-005): grep `cuems-power-bridge/tests` **and `cuems-power-bridge/debian/rules`** for `0\.1\.0rc16|1\.3\.0-23|0\.3\.1-1|0\.2\.0|<< ?0\.1\.1`. In `debian/rules`, move the build message "cuemsutils >=0.1.0rc16 is not on PyPI" to `>=0.1.1`, text only (research R15). Record each decision
- [ ] T070 [US2] **Last edit**: `cuems-power-bridge/debian/control` `:18` `(>= 0.1.1)`, `:19` `(<< 0.1.2~)`, `:20` `cuems-common (>= 1.3.1~)`, `:25` `Breaks: cuems-common (<< 1.3.1~)`; and `pyproject.toml:38` `cuemsutils = ">=0.1.1,<0.1.2"` (rows 20–24)
- [ ] T071 [US2] Run `F/tools/verdicts.sh`: rows 20–24 and row 5 OK
- [ ] T072 [US1] Commit (signed, unpushed): `chore(release): cuems-power-bridge 0.3.2-1 — …`. Record `bump_commit`
- [ ] T073 [US3] `UTILS=UB … F/tools/bookworm-build.sh /disk/Projects/StageLab/cuems-power-bridge`. `CUEMS_UTILS_SRC` is provided per T006. Expect `0.3.2-1` and `home = /usr/bin`
- [ ] T074 [US1] Suite protocol for `cuems-power-bridge`. Zero new failures, within 115%
- [ ] T075 [US1] Record `release_gap_bump`
- [ ] T076 [US4] Write `TM/cuems-power-bridge.txt`: from its current tag message, `RELOCATED from 399baf7`, `Tag: <bump>`, the renumbering reason (R2), rows 20–24, `NOT YET RECONCILED` (main + release/0.3.1-2, naming `CACHEDIR.TAG`), and pairs. Verify, then fill the record
- [ ] T077 [US1] Confirm nothing is pushed and no tag was touched in `cuems-power-bridge`
- [ ] T078 **STOP (FR-021)**: present the record and the renumbering again. Wait for an explicit go-ahead

---

## Phase 7: `cuems-engine` → `0.1.1-1` (rows 6–10, 25)

**Goal**: `0.1.1-1` UNRELEASED above the released `0.1.0rc2-3`, both self-versions `0.1.1`, rows 6–10, `libmtcmaster` declared (row 25, FR-023), and the lock guarded (FR-022).
**Independent test**: verdict rows 6–10 and 25 OK. Both CI passes run against the real `pyossia` with no new failure. The lock test reports `xfail`. The build gives `cuems-engine` and `cuems-engine-mock` `0.1.1-1`, with `libmtcmaster` in `Depends:`. The message verifies.

- [ ] T079 [US1] Fetch, then verify `cuems-engine` is on `feat/xml-refactor` at `7d0bda3` (FR-010a; re-measure per FR-001 if it moved), clean, 0/0. Fill `start_commit`
- [ ] T080 [US1] Measure and record:
  - the changelog head (`0.1.0rc2-3 bookworm`, released) and the two self-version sites (`0.1.0rc7` expected);
  - the highest version on any remote branch (`0.1.0rc6-5` expected) and `0.1.1-1 gt` it;
  - behind/ahead against `origin/debian/bookworm` (119/26 expected) and the absent entries;
  - `poetry check --lock` (passes at `7d0bda3`, per `fc9e9af`).

  If anything differs, re-derive per FR-002 and update `F/contracts/relation-matrix.md`
- [ ] T081 [US1] Set `pyproject.toml:11` and `src/cuemsengine/__init__.py:5` to `0.1.1`. In `debian/changelog`, **add** a new top entry `cuems-engine (0.1.1-1) UNRELEASED; urgency=medium` above the untouched released `0.1.0rc2-3` (FR-003, second rule). Its bullets:
  - the coordinated bump;
  - the self-version reconcile;
  - rows 6–10;
  - `libmtcmaster (>= 0.0.2-0)` declared: it was loaded but never declared (FR-023);
  - "poetry.lock is not relocked: cuemsutils 0.1.1 is unresolvable until published; relock at publication (FR-022)";
  - "release line debian/bookworm and release/0.1.0rc6-5 not yet absorbed — includes the stop_project ActionCue, which needs cuemsutils' stop_project (rc17); do not publish until reconciled and relocked; re-verify relations after the merge"
- [ ] T082 [US2] Add `cuems-engine/tests/test_lock_is_current.py` (FR-022, research R16): run `poetry check --lock` in the repository root and assert exit 0. Mark it `pytest.mark.xfail(strict=True, reason="poetry.lock relocks at publication, once cuemsutils 0.1.1 is resolvable (cuems-utils 016, FR-022)")`. If `poetry` is not on `PATH`, call `pytest.fail`, never skip. Give it no `integration` marker, so it runs in the first CI pass. Then read the hit(s) of `grep -nE '0\.1\.0rc16|1\.3\.0-23|0\.1\.0-8|0\.1\.0rc7|<< ?0\.1\.1' cuems-engine/tests/test_mtclistener.py` (it may be an unrelated number); decide and record
- [ ] T083 [US2] **Last edit**: `cuems-engine/debian/control` `:26` `(>= 0.1.1)`, `:27` `(<< 0.1.2~)`, `:28` `cuems-common (>= 1.3.1~)` with the comment at `:20-21` rewritten, and `:49` `cuems-engine (>= 0.1.1)`; and **insert `libmtcmaster (>= 0.0.2-0),` directly after `:30`** (row 25), with a comment naming `libmtc.py` and the published `v0.0.2-0` release. Also `pyproject.toml:50` `cuemsutils = ">=0.1.1,<0.1.2"` (rows 6–10). `:30` `python3-pyossia` and `pyproject.toml:84` stay untouched (libossia is an independent input). **Do not run `poetry lock`**
- [ ] T084 [US2] Run `F/tools/verdicts.sh`: rows 6–10 and 25 OK
- [ ] T085 [US1] Commit (signed, unpushed): `chore(release): cuems-engine 0.1.1-1 — …`. Record `bump_commit`
- [ ] T086 [US3] `UTILS=UB … F/tools/bookworm-build.sh /disk/Projects/StageLab/cuems-engine`. Expect **both** `cuems-engine_0.1.1-1` and `cuems-engine-mock_0.1.1-1`, with `home = /usr/bin`, and `dpkg-deb -f <cuems-engine deb> Depends` containing `libmtcmaster (>= 0.0.2-0)`. `python3-pyossia` and `libmtcmaster` are runtime-only, so the build needs neither
- [ ] T087 [US1] Suite protocol for `cuems-engine`, with each arm being **the two CI passes** (`-m "not integration" -n auto`, then `-m "integration and not slow"`) against the **real** `pyossia` (FR-020). Expected baseline 885 + 32 passed (engine document). In arm B, `test_lock_is_current` reports `xfail`; it is new and does not count as a new failure. Zero other new failures, within 115%
- [ ] T088 [US1] Record `release_gap_bump`
- [ ] T089 [US4] Write `TM/cuems-engine.txt` (first tag, no relocation line):
  - `Tag: <bump>`, and the carries narrative since the branch point, including `fc9e9af`/`729f8b6` (pyossia `cuems3` wheel, bookworm CI);
  - rows 6–10, plus row 25 (`libmtcmaster` declared);
  - `NOT YET RECONCILED` (naming `stop_project`), and "poetry.lock relock pending publication (FR-022)";
  - "engine CI resolves cuemsutils from PyPI and stays red until the re-cut tag or 0.1.1 is used (engine doc §4.3)";
  - pairs.

  Verify
- [ ] T090 [US4] Fill `F/records/cuems-engine.md` completely
- [ ] T091 [US1] Confirm nothing is pushed and no tag exists in `cuems-engine`
- [ ] T092 [US2] Update `F/contracts/relation-matrix.md` § Sites with the engine's final line numbers (row 9 moves to `:50` after row 25's insertion) and any T080 change; note it in the record
- [ ] T093 **STOP (FR-021)**: present and wait for an explicit go-ahead

---

## Phase 8: `cuems-editor` → `0.1.1-1` (rows 11–14)

**Goal**: `0.1.1-1` UNRELEASED folding `0.1.0rc1-4`, self-versions `0.1.1`, rows 11–14.
**Independent test**: verdict rows 11–14 OK, the suite has no new failure, the build gives `0.1.1-1`, and the message verifies.

- [ ] T094 [US1] Verify `cuems-editor` is on `feat/xml-refactor` at `e5e6ac1` (or re-measure), clean, 0/0. Fill `start_commit`
- [ ] T095 [US1] Measure and record:
  - the changelog head (`0.1.0rc1-4 UNRELEASED`), `pyproject.toml:7` and `src/cuemseditor/__init__.py:4` (`0.1.0rc1`), and whether `[tool.hatch.version]` reads `__init__`;
  - the highest version on any remote branch (`0.1.0rc1-7`) and `0.1.1-1 gt` it;
  - behind/ahead (43) and the absent entries (`rc1-5`, `-6`, `-7`)
- [ ] T096 [US1] Set `pyproject.toml:7` and `src/cuemseditor/__init__.py:4` to `0.1.1`. In `debian/changelog`, fold `0.1.0rc1-4 UNRELEASED` into `cuems-editor (0.1.1-1) UNRELEASED; urgency=medium` (body kept). Leave the older `0.1.0rc1-2 UNRELEASED` untouched. Add bullets: bump, rows 11–14, "debian/bookworm (0.1.0rc1-5…-7) not yet absorbed; do not publish until reconciled; re-verify relations after the merge"
- [ ] T097 [US2] Update the comment in `cuems-editor/tests/packaging/bookworm-build.sh` (`cuemsutils >= 0.1.0rc16 is not on PyPI` → `>= 0.1.1`). Grep `cuems-editor/tests` for the other old literals and record the decisions
- [ ] T098 [US2] **Last edit**: `cuems-editor/debian/control` `:18` `(>= 0.1.1)`, `:19` `(<< 0.1.2~)`, `:20` `cuems-common (>= 1.3.1~)`; plus `pyproject.toml:23` `"cuemsutils>=0.1.1,<0.1.2"` (rows 11–14)
- [ ] T099 [US2] Run `F/tools/verdicts.sh`: rows 11–14 OK
- [ ] T100 [US1] Commit (signed, unpushed): `chore(release): cuems-editor 0.1.1-1 — …`. Record `bump_commit`
- [ ] T101 [US3] `UTILS=UB … F/tools/bookworm-build.sh /disk/Projects/StageLab/cuems-editor`. Expect `0.1.1-1` and `home = /usr/bin`. Optionally corroborate with the repository's own `tests/packaging/bookworm-build.sh`, using `UTILS=UB` and `OUT=` under `F/evidence/cuems-editor/`
- [ ] T102 [US1] Suite protocol for `cuems-editor`. Zero new failures, within 115%
- [ ] T103 [US1] Record `release_gap_bump`
- [ ] T104 [US4] Write `TM/cuems-editor.txt` (first tag): `Tag: <bump>`, carries (001 migration, 002 config round trip, 015 halves), rows 11–14, `NOT YET RECONCILED`, pairs. Verify
- [ ] T105 [US4] Fill `F/records/cuems-editor.md` completely
- [ ] T106 **STOP (FR-021)**: present and wait for an explicit go-ahead

---

## Phase 9: `cuems-frontend` → `0.1.0` (no package, no relations)

**Goal**: first real version `0.1.0` (FR-014).
**Independent test**: `package.json` and the lockfile root say `0.1.0`; the build passes; `test:ci` has no new failing spec in the two-arm run; the message verifies.

- [ ] T107 [US1] Verify `cuems-frontend` is on `feat/xml-refactor` at `6b69b41` (or re-measure), clean, 0/0. Fill `start_commit` and the measured `0.0.0` sites (`package.json:3`, `package-lock.json:3`, `:9`)
- [ ] T108 [US1] Run `npm version 0.1.0 --no-git-tag-version` in `cuems-frontend`. It edits `package.json` and both root entries of `package-lock.json` and **creates no tag** (FR-014). Confirm `git diff` touches only those three lines and `git tag -l` is unchanged
- [ ] T109 [US1] Commit (signed, unpushed): `chore(release): cuems-frontend 0.1.0 — first version, coordinated xml-refactor minor (cuems-utils 016)`. Record `bump_commit`
- [ ] T110 [US3] Run `npm run build` at the bump; record in `F/evidence/cuems-frontend/build.txt` (the frontend's build check; FR-006 does not apply)
- [ ] T111 [US1] Suite protocol with `CHROME_BIN=/usr/bin/google-chrome npm run test:ci` instead of pytest (A/B interleaved three times). Zero new failing specs
- [ ] T112 [US4] Write `TM/cuems-frontend.txt`: `RELOCATED from f5453a3`, `Tag: <bump>`, "first version 0.1.0", carries since `f5453a3`, "no package; compatibility contract is the payload handshake (payload_version: 1)", pairs. Verify
- [ ] T113 [US4] Fill `F/records/cuems-frontend.md` completely
- [ ] T114 **STOP (FR-021)**: present and wait for an explicit go-ahead

---

## Phase 10: `cuems-utils` record commit and tag message (LAST)

**Goal**: the record commit, which is the `cuems-utils` candidate-tag commit (I2), and seven messages that compose.
**Independent test**: the release-matrix test's sibling-head half passes. All verdicts are OK. The seven messages verify and every pair matches. `TM/cuems-utils.txt` names the record commit.

- [ ] T115 [US2] Run `F/tools/verdicts.sh`: **all** rows OK. Write `F/evidence/relation-verdicts.txt` (SC-002)
- [ ] T116 [US1] Re-run every sibling suite once more at its bump commit, on `UB`, to confirm the final state after all phases (no new failures against each arm B). Append to `F/evidence/<repo>/suite-final.txt`
- [ ] T117 [US1] Release-matrix test, **step 2 of 2**. Add `test_siblings_at_feat_xml_refactor` to `tests/packaging/test_release_matrix.py`: parametrised over the six, reading `git show feat/xml-refactor:<file>` in each sibling (`package.json` for the frontend), skipping when a checkout is absent. Run it: it passes
- [ ] T118 [US1] Update `specs/planning/coordinated-release-version-bump.md` (FR-017):
  - status "§3–§8 and §11 step 6 executed by 016";
  - the research R1/R2/R3 corrections (engine has a release line, FR-010a; power-bridge `0.3.2-1` and §4.4; rc17's `stop_project`);
  - the pending items: rule 4, re-cut, §11.1 validation, publication;
  - **not deleted**
- [ ] T119 [US1] Update `CLAUDE.md`:
  - correct the `debian/bookworm` / `packaging-rc14` paragraph (FR-015);
  - add a *Recent Changes* entry for 016: versions, every sibling bump hash, R2, R3, the deferred reconciliation, FR-010a, evidence locations, suite numbers
- [ ] T120 [US4] Fill `F/records/cuems-utils.md` completely, tick every completed task in `F/tasks.md`, then make the **record commit** on `016-coordinated-minor-bump` (signed, unpushed): T117–T119, `F/records/`, `F/evidence/`, `F/tools/`, `F/tasks.md`. Subject `docs(016): coordinated minor bump — records, evidence, planning status`. Record its hash. **This is the commit the `cuems-utils` candidate tag goes on**
- [ ] T121 [US4] Complete `TM/cuems-utils.txt` (from the T029 draft) and fill the pending `Pairs with` lines in all six sibling messages:
  - the utils message gets `Tag: <record commit>`, `Branch: 016-coordinated-minor-bump (not yet merged into feat/xml-refactor)`, `Bump commit: <bump>`, pairs for all six, and "not validated on re-cut tags".

  Run the contract verification across **all seven** files: each `Tag:` equals its repository's head, and every pair equals the `Tag:` in that repository's own message
- [ ] T122 [P] SC-006: each repository's `origin/<branch>` equals T011's recorded value (nothing pushed), and every `xml-refactor-merge-candidate^{commit}` equals T011's value (no tag created or moved). Write `F/evidence/no-push-no-tag.txt`
- [ ] T123 [P] SC-001: re-read every self-version site in all seven repositories at their final commits. Every one states its target, and none collides with a version released on any remote branch. Write `F/evidence/version-sites.txt`
- [ ] T124 [US4] Fold T121–T123's evidence and the final checkbox ticks into the record commit (`git commit -S --amend`, FR-021). Update `TM/cuems-utils.txt`'s `Tag:` to the new hash and re-run the seven-file verification
- [ ] T125 **STOP (FR-021)**: present the `cuems-utils` record, the seven-message verification and SC-001/SC-006. Wait for an explicit go-ahead. A correction targets the bump commit if it concerns the bump: amend, then follow the Conventions' dependent re-run rule. Otherwise it targets the record commit

---

## Phase 11: Polish

- [ ] T126 Remove the worktrees: `git -C /disk/Projects/StageLab/cuems-utils worktree remove /disk/Projects/StageLab/.016-utils-start`, then the same for `.016-utils-bump`, then `git worktree prune`. Leave the `.venv`s (excluded locally); any sibling `.venv` still pointing at `UB` is re-pointed with `pip install --no-deps -e /disk/Projects/StageLab/cuems-utils` so it keeps working
- [ ] T127 Hand over to the maintainer:
  - every hash, plus the `TM/` files and `TM/README.md`'s apply order (`cuems-utils` last, on its record commit);
  - the open items: the re-cut; §11.1 validation on the re-cut tags; release-line reconciliation (rule 4, `stop_project`, `CACHEDIR.TAG`, then re-verifying the relations); merging 016 into `feat/xml-refactor`; FR-010a if still pending; publication

---

## Dependencies & Execution Order

```text
Phase 1 Setup ──► Phase 2 Foundational (preflight clean; T007 answered)
  ──► P3 cuems-utils BUMP ─STOP─► P4 common ─STOP─► P5 nodeconf ─STOP─► P6 power-bridge ─STOP─►
      P7 engine ─STOP─► P8 editor ─STOP─► P9 frontend ─STOP─► P10 cuems-utils RECORD + messages ─STOP─► P11
```

- **Strictly sequential and mandatory** (FR-016, FR-020, FR-021). A phase starts only after the
  previous STOP gets an explicit go-ahead. There is no reordering around `cuems-engine`.
- **Why `cuems-utils` is split**: every sibling build resolves `cuemsutils>=0.1.1` (C1), so the
  bump is first. The message names every other repository, and the tag goes on the record commit
  (I2), so the record commit and message are last.
- **Inside a sibling phase**: measure → edits → relations **last** → verdicts → commit → build /
  suites / demonstration → gap → message → STOP. The build and the suite protocol may run
  concurrently once the build script has finished copying the source, because the suite switches
  the working tree.
- **Amend propagation** (FR-021): `cuems-utils` bump → every completed sibling's build,
  demonstration and suites; `cuems-common` → `cuems-nodeconf`'s demonstration; every amend → the
  `Pairs with` lines.

### Story completion

| Story | Complete when |
|---|---|
| US1 | T023, T043, T059, T072, T085, T100, T109 committed; every suite protocol clean; T116, T123 |
| US2 | T115 all verdicts OK; T046 + T062 demonstrations exit 0 with clean-checkout evidence |
| US3 | T026, T044, T060, T073, T086, T101 builds pass (+ T110 frontend build) |
| US4 | T121 seven messages verify and compose; T011 README; T124 |
| US5 | T014, T015, T018, T019 (warning names `v0.1.2`, document renamed, citations resolve) |

## Parallel opportunities

Limited by design, since phases run one repository at a time:

- **Phase 1**: T003, T004, T005 in parallel; T006 alongside them.
- **Phase 2**: T009 and T010 in parallel.
- **Phase 3**: T013, T014, T015 edit disjoint files and can be done in parallel.
- **Phase 10**: T122 and T123 in parallel.

```text
# Phase 1, together:
T003 venvs (nodeconf, power-bridge, engine, editor) | T004 common venv | T005 frontend npm ci | T006 build script
```

## Implementation strategy

- **MVP = Phases 1–4**: the preflight, the verdict tool, the `cuems-utils` bump (which unblocks
  every build), and `cuems-common` with its demonstration green. The R2 power-bridge decision comes
  up at the first two stops, before anything depends on it.
- **Incremental**: each phase leaves a committed, built, tested, message-ready repository and a
  stop. Abandoning midway leaves only unpushed local commits. Undoing them is
  `git reset --hard <start_commit>`, the maintainer's decision (spec Assumptions).
- **Not in this feature**: the tag re-cut; validation on re-cut tags (§11.1); release-line
  reconciliation and re-verification; merging 016 into `feat/xml-refactor`; publication. T127
  hands them over.
