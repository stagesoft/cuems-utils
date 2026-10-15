<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Feature Specification: Coordinated minor version bump and candidate-tag re-cut preparation

**Feature Branch**: `016-coordinated-minor-bump`
**Created**: 2026-10-15
**Status**: Draft
**Input**: User description: "base a new spec using `specs/planning/coordinated-release-version-bump.md`. The main goal of this spec is to raise the minor value of the version for the whole ecosystem, and re-cut its coordinated tag. This SDD, as an exception, will be able to edit and commit work in sibling repositories, so all coordinated tasks can be landed and verified as a single feature managed and registered here. A usual speckit branch (016) will be created only here; all the other repositories will stay on and commit directly to `feat/xml-refactor`. Tasks are split, for each repository, into: checkout HEAD of `feat/xml-refactor`; validate the known state of the version; move the minor version up as required and keep it `UNRELEASED`; check the build in a local environment prepared for Debian 12, since nothing is released; validate/test the final state; rewrite the `xml-refactor-merge-candidate` tag message in the `../.refactor-tag-messages/` folder so the tags can be re-cut from the parent directory once everything is done; commit the required changes, but push nothing." Follow-up: "also add all the proposed speckit commands to the flow."

## Clarifications

### Session 2026-10-15

- Q: The tag-message folder: `../.refactor-tag-messages/` (as requested) or
  `../.xml-refactor-tag-messages/` (as CLAUDE.md records)? → A: **`../.xml-refactor-tag-messages/`**
  — the maintainer created it 2026-10-15 (empty) and confirmed it is the right path.
- Q: Four refactor branches are still behind their release lines (`cuems-utils` 73 commits behind
  `debian/bookworm`, `cuems-common` 22, `cuems-editor` 43, `cuems-power-bridge` 26 behind `main`).
  Does this feature merge them before the bump? → A: **No.** The coordinated versions land first;
  code coordination with the release lines (cherry-pick, merge or direct adoption) is a later step,
  after this feature. Rule 4 of the planning document is recorded as **not yet met**.
- Q: `cuems-frontend` has no package, no tag history and `package.json` at `0.0.0`. → A: It takes
  its **first real version, `0.1.0`**, at this landing.
- Q: How are the suites run, given pyenv 3.11.9 must stay the development interpreter? → A: **Every
  sibling Python suite runs on pyenv 3.11.9**, in its own git-ignored `.venv` created from
  `~/.pyenv/versions/3.11.9/bin/python`. **`cuems-utils` is the exception**: it is the only
  repository with a test matrix (3.11/3.12/3.13), so it keeps its `hatch` environments and their
  uv-managed interpreters (`uvx hatch run test.py3.11:run`), and the interpreter restriction is
  relaxed for it.
- Q: `cuems-engine`'s suite imports `pyossia`, which is not installed on the host (feature 015 ran
  it against a mock: 28 failures in both arms). How is that suite run? → A: **RESOLVED by
  `cuems-engine` itself** (`fc9e9af`, `729f8b6`, 2026-10-15): `pyossia` is pinned in the engine's
  Poetry **dev group** to the released `cuems3` wheel
  (`pyossia-2.0.0rc6+124.cuems.3-cp311-cp311-linux_x86_64.whl`, URL and hash in `poetry.lock`),
  built from the same commit, on Debian 12, as the `python3-pyossia` `.deb`. The suite runs against
  the **real** `pyossia`, in the engine's two CI passes (FR-020).
- Q (analyze, I2): On which `cuems-utils` commit does its candidate tag go — the bump commit or the
  later record commit? → A: **The record commit** (FR-016, SC-005).
- Q (analyze, I3): May later repositories run ahead of `cuems-engine` while FR-020 is open? → A:
  **No — the order is mandatory** (FR-016); the `pyossia` question has since been resolved (FR-020).
- Q (analyze, U1): Does an amend to a commit that later phases already used re-run them? → A:
  **Yes — dependent builds, demonstrations and suites re-run**, for coherence (FR-021).
- Q (analyze, U3): `cuems-engine` has a release line 114 commits ahead, which the planning document
  says it lacks. → A: **Registered (FR-010a)**, pending until the new `cuems-engine` work landed —
  it has (`7d0bda3`), and FR-010a is now resolved with the re-measured values.
- Q (analyze 2, E1): `cuems-engine` is the only repository with a lock file. Its bound moves to
  `>=0.1.1,<0.1.2`, which no index can resolve until `0.1.1` is published, so it cannot be relocked
  now. → A: **Leave the lock as it is, and add a strict-xfail test** in the engine bump commit
  asserting `poetry check --lock` passes; it flips the day the relock lands, at publication (FR-022).
- Q (analyze 2, E5/E6): libossia's place, and the engine's undeclared runtime dependencies. → A:
  **libossia is an independent input** (the engine keeps `python3-pyossia (>= 2.0.0-rc6+124+cuems3)`
  unchanged), and **016 declares `libmtcmaster`** in `cuems-engine/debian/control`, pinned to the
  **actual release**, `libmtcmaster (>= 0.0.2-0)` — the `.deb` published as GitHub release `v0.0.2-0`
  and downloaded by the engine CI. `libmtcmaster` has not changed and gets **no version bump**
  (FR-023). `iproute2`/`procps` and the `rtpmidid` naming stay unchanged on purpose.
- Q (analyze, G1): Do sibling quality gates count toward SC-QUALITY-001? → A: **No — narrowed to
  this repository.**
- Q: When does implementation stop for maintainer review? → A: **After every repository**, and a
  correction made at a stop is amended into that repository's bump commit by default. Once a
  repository is committed and its tag message written, implementation stops, presents that
  repository's evidence and waits for the maintainer's go-ahead before starting the next one.

## Specification workflow

The maintainer added every proposed spec-kit step to this feature's flow. Steps 2 and 6 are
mandatory by the original request; the rest were proposed and adopted. Each step runs in this
repository, on this branch, and writes into this feature directory.

| # | Command | Purpose here | Status |
|---|---|---|---|
| 1 | `/speckit-specify` | This document | ✅ done 2026-10-15 |
| 2 | `/speckit-clarify` | Mandatory. Resolve what remains ambiguous after the three answers above | ✅ done 2026-10-15 |
| 3 | `/speckit-plan` | Per-repository procedure, research (re-measured versions, relation sites, build method), quickstart for the bookworm build | ✅ done 2026-10-15 |
| 4 | `/speckit-checklist` | A **release-safety** checklist: the §4 relation matrix, no push, no tag move, evidence never overwritten, deferred rule 4 stated everywhere it must be | ✅ done 2026-10-15 (`checklists/release-safety.md`) |
| 5 | `/speckit-tasks` | Tasks grouped **per repository** in FR-016's order, each group the request's seven steps (checkout → measure → bump → bookworm build → test → tag message → commit) | ✅ done 2026-10-15 |
| 6 | `/speckit-analyze` | Mandatory. Cross-artifact consistency of spec, plan, tasks and checklist before any sibling is touched | ✅ done 2026-10-15; findings applied |
| 7 | `/speckit-implement` | One repository at a time — `cuems-utils` bump first, siblings, `cuems-utils` record + message last (FR-016); stops after each repository for the maintainer's go-ahead (FR-021) | pending |

`/speckit-taskstoissues` is **not** in the flow: nothing is pushed, so there is no remote tracker
state for it to reflect. `/speckit-constitution` is unchanged by this feature.

**Work order**: [`specs/planning/coordinated-release-version-bump.md`](../planning/coordinated-release-version-bump.md)
(the *planning document* below). Its five rules, its target table (§3), its relation matrix (§4)
and its file inventory for this repository (§5–§8) are the requirements' source; this spec does
not restate them line by line, it binds them.

## Scope exception — this feature writes to sibling repositories

Every earlier feature in this repository edited only this repository and *measured* its siblings.
**This one edits and commits in six sibling repositories**, because a version move whose package
relations are left behind is an ecosystem `dpkg` refuses to install (planning document §4, §11
step 6): the set is only correct as a whole. The exception is bounded:

- **Only this repository gets a feature branch** (`016-coordinated-minor-bump`). Every sibling —
  `cuems-common`, `cuems-engine`, `cuems-editor`, `cuems-nodeconf`, `cuems-power-bridge`,
  `cuems-frontend` — commits **directly on its own `feat/xml-refactor`**.
- **Commit order is not message order.** `cuems-utils` commits its bump **first** — every sibling
  build needs `cuemsutils 0.1.1`, which exists nowhere else — and its record commit and tag message
  **last** (FR-016).
- **No release line is merged in.** Reconciling with the parallel release lines (planning document
  rule 4, §10) is deliberately deferred to after this feature (Clarifications); this feature moves
  versions and relations only.
- **Nothing is pushed**, in any repository. **No tag is created, moved or deleted** — moving a
  candidate tag is maintainer-only (standing rule); this feature prepares the messages the
  maintainer re-cuts from.
- **The feature record lives here**: every sibling commit is listed, with its hash and the
  evidence that verified it, in this feature's directory.

## User Scenarios & Testing *(mandatory)*

The actors are the **maintainer** (who re-cuts the candidate tags and later publishes), the
**release validator** (who builds and installs the coordinated set), and the **operator** whose
node receives the packages.

### User Story 1 — Every package carries a version nobody else has shipped (Priority: P1)

The maintainer looks at any repository's `feat/xml-refactor` head and finds its package at its
own next stable minor (`cuems-utils 0.1.1`, `cuems-common 1.3.1-1`, `cuems-engine 0.1.1-1`,
`cuems-editor 0.1.1-1`, `cuems-nodeconf 0.1.1-1`, `cuems-power-bridge 0.3.2-1` — re-derived
2026-10-15, see research R2), marked
`UNRELEASED`, with every place that states the package's own version agreeing.

**Why this priority**: four of the six packaged repositories hold a version number a parallel
release line has already shipped with different content (planning document §1). Until that ends,
an installed package's version does not say what it contains.

**Independent Test**: for each repository, read every self-version site (changelog head, project
metadata, module version constant) and compare against the target table; compare each target
against the highest version released from that repository's release line.

**Acceptance Scenarios**:

1. **Given** a repository at its `feat/xml-refactor` head, **When** its self-version sites are
   read, **Then** all of them state the target version and the changelog head is `UNRELEASED`.
2. **Given** the highest version released from that repository's release line, **When** it is
   compared with the target, **Then** the target sorts strictly above it.
3. **Given** `cuems-engine` (changelog `0.1.0rc2-3`, module `0.1.0rc7`) and
   `cuems-power-bridge` (metadata `0.3.1`, module `0.2.0`), **When** the bump lands, **Then** the
   pre-existing disagreements (planning document §3.1) are gone, not carried forward.

---

### User Story 2 — The coordinated set installs together, and refuses mixed sets (Priority: P1)

The release validator installs the six packages, all at their targets, onto a fresh Debian 12
(bookworm) system and the install succeeds; replacing any one with its previously-released version
is refused by the package manager rather than silently producing a broken node.

**Why this priority**: a moved version with stale relations is uninstallable, and three existing
relations are already *defeated* by reused version numbers, admitting half-migrated pairs with no
install error (planning document §1.1). This is the story that makes the bump safe rather than
cosmetic.

**Independent Test**: every versioned relation in `contracts/relation-matrix.md` is evaluated
against the version that should pass and the version that should be refused; where an install
demonstration exists for a repository, it is run.

**Acceptance Scenarios**:

1. **Given** the consumer bound on `cuems-utils`, **When** evaluated against `0.1.0rc16`,
   `0.1.0rc16+1`, `0.1.0rc17` (released 2026-10-15), `0.1.1`, `0.1.2~rc1` and `0.1.2`, **Then**
   only `0.1.1` (with any Debian revision) is admitted.
2. **Given** `cuems-utils`' `Breaks:` on `cuems-common`, **When** evaluated against the released
   `1.3.0-23`, `-24` and `-25`, **Then** all three are refused — the defect of §1.1 is closed.
3. **Given** `cuems-common`'s `Breaks:` on `cuems-nodeconf`, **When** evaluated against the
   released `0.1.0-8` and `0.1.0-9`, **Then** both are refused.
4. **Given** `cuems-common`'s `Breaks:` on `cuems-power-bridge`, **When** evaluated against the
   released `0.3.0-11` and `0.3.1-2` (released 2026-10-15, still reading `node_type` and without
   the cluster-poweroff module), **Then** both are refused, and `0.3.2-1` is admitted.
5. **Given** the two existing install demonstrations (`cuems-common`, `cuems-nodeconf`), **When**
   run with every checkout at its committed `feat/xml-refactor` head, **Then** every scenario's
   observed outcome matches its expectation, and the evidence is written to a new file, never
   over a previous feature's evidence.

---

### User Story 3 — Each package builds for Debian 12 from local sources, without a published release (Priority: P2)

The release validator builds each packaged repository's `.deb` in a Debian 12 environment, with
`cuemsutils` supplied as a wheel built from this repository's checkout rather than from PyPI, and
the resulting package's interpreter points at the system interpreter.

**Why this priority**: nothing in this set is published (planning document rule 5); a build that
only works against PyPI cannot be built at all until after release. Ranked below P1 because a
build failure does not corrupt anything, it just blocks the tag.

**Independent Test**: build each package in a disposable bookworm environment; inspect the built
package's virtualenv interpreter configuration.

Expected binary packages: one per repository, plus `cuems-engine-mock` from `cuems-engine`.

**Acceptance Scenarios**:

1. **Given** a repository with a `debian/` directory, **When** built in a bookworm environment
   with the locally built `cuemsutils` wheel offered, **Then** the build succeeds and produces a
   package at the target version.
2. **Given** a package built into the shared venv, **When** its virtualenv configuration is read,
   **Then** the interpreter home is `/usr/bin` (the CLAUDE.md "verify the venv interpreter" check).

---

### User Story 4 — The maintainer can re-cut every candidate tag from prepared messages (Priority: P2)

Once every repository is committed, the maintainer finds one prepared tag message per repository
in `../.xml-refactor-tag-messages/`, each naming the commit to tag, the version it carries, the
counterpart tags it composes with, and whether that repository's release line is still to be
reconciled, and re-cuts all seven
`xml-refactor-merge-candidate` tags (`cuems-utils` last) without having to research anything.

**Why this priority**: every existing candidate tag names `0.1.0rc16` as the coordinated version
and is therefore stale (planning document §9); three repositories have no tag at all. The re-cut is
the maintainer's act, but the information has to be ready and correct.

**Independent Test**: for each message, check that the commit it names exists, is the
repository's committed `feat/xml-refactor` head, carries the version the message states, and that
every counterpart the message names is itself named by another message in the set.

**Acceptance Scenarios**:

1. **Given** the prepared messages, **When** each named commit is resolved, **Then** it is the
   repository's committed head and its version sites state the version the message states.
2. **Given** the set of messages, **When** read together, **Then** every counterpart reference is
   consistent with the other messages (the set "composes" — the 2026-09-28 lesson in CLAUDE.md).
3. **Given** a repository still behind its release line, **When** its message is read, **Then** it
   states that the release line is not yet reconciled and that the set must not be published
   until it is.

---

### User Story 5 — This library's deprecation timetable moves with the version (Priority: P3)

A consumer still using a deprecated name receives a warning that says the name goes away in
`v0.1.2`, not `v0.1.1` — because `0.1.1` is now the version they are running.

**Why this priority**: purely this repository; correct messaging, no install-time effect. It is
still required in this feature because the planning document's rule 3 binds it to the bump.

**Independent Test**: trigger each deprecation warning and read the removal release it names;
search non-frozen documents for the old removal release.

**Acceptance Scenarios**:

1. **Given** any deprecated entry point, **When** used, **Then** the warning names `v0.1.2`.
2. **Given** the removal planning document, **When** looked up, **Then** it carries its `v0-1-2`
   name and every citation of the old filename (including the two in code and tests) resolves.

### Edge Cases

- **A sibling's `feat/xml-refactor` is dirty or diverged from its remote** at checkout: the
  repository is not touched until the state is recorded and resolved; a bump is never committed on
  top of uncommitted foreign work.
- **A sibling's version is not what the planning document measured** (it was measured
  2026-10-12/13, and parallel lines keep releasing): the target is re-derived from the measured
  released high-water mark, and the discrepancy is recorded rather than silently absorbed.
- **The later release-line reconciliation conflicts in `debian/control`**: out of scope here, but
  the risk is real (planning document §10.3) — a merge could resolve the new relations back to the
  release line's values. Each affected tag message and the feature record MUST warn that the
  relations are re-verified after that reconciliation.
- **A sibling's suite fails at its head before any change**: the failure is recorded as
  pre-existing (two-arm measurement, as features 012–015 did) and is not attributed to the bump.
- **`cuems-engine`'s suite needs the real `pyossia`**: provided by the pinned `cuems3` wheel
  (FR-020). Its one known full-suite failure, `test_project_go_from_controller` (marked slow), is
  outside the two CI passes and pre-existing.
- **`cuems-frontend` has no package and no tag history**: it takes `0.1.0` (FR-014) and is
  neither built as a `.deb` nor subject to any package relation.
- **An install demonstration still hard-codes the old versions** (it does today): it is updated in
  the same commit as the relations it tests, or it would "pass" while testing nothing that ships
  (planning document §11.1 step 2).
- **The build needs network** (Debian mirror, third-party PyPI dependencies): a network failure
  is recorded as an environment failure, never as a package defect.

## Requirements *(mandatory)*

### Functional Requirements

**Per-repository procedure** (applies to all seven repositories, in the order of FR-016):

- **FR-001**: Each repository MUST be worked from its local `feat/xml-refactor` head (for
  `cuems-utils`, the `016-coordinated-minor-bump` branch cut from it), verified clean and in step
  with its remote before any edit; the starting commit is recorded. If a sibling's
  `origin/feat/xml-refactor` advances during the feature, that repository is re-measured before its
  phase starts and the advance is recorded; nothing is pulled in without the maintainer's decision.
- **FR-002**: Each repository's known version state MUST be measured and recorded before any edit:
  every self-version site, the changelog head and its distribution, the highest version released
  on **any** remote branch (release lines, `release/*`, `rc_1`, `main`), and whether that released
  commit is an ancestor of the refactor branch. If a release above the planned target is found —
  before or during the feature — the target is re-derived by rule 1 (the last upstream component
  advances, revision `-1`), recorded as a decision, and every relation that names it moves with it.
- **FR-003**: Each packaged repository MUST be moved to its target version (`contracts/relation-matrix.md`
  § Targets, re-derived per FR-002) with a top changelog entry marked `UNRELEASED`. The existing
  head entry is treated by one of three rules (research R6): **folded** (body kept, header dropped)
  when its number was never shipped by this branch — whatever its distribution (`UNRELEASED` or
  `unstable`); **kept verbatim** below the new entry when it is released history; or **kept as the
  header** when it already states the target (`cuems-nodeconf 0.1.1-1`).
- **FR-004**: Every self-version site in a repository MUST state the same version after the bump,
  including the two pre-existing drifts (`cuems-engine`, `cuems-power-bridge`).
- **FR-005**: Every versioned package relation in **`contracts/relation-matrix.md`** — the
  authority for this feature, superseding the planning document's §4 (which counts 20 sites and
  keeps `cuems-power-bridge`'s `Breaks:` unchanged) — MUST move to its stated value in the same
  commit as the version it names, and each MUST be shown by version comparison to admit exactly what
  it should and refuse what it should (US2 scenarios). The relations deliberately left unchanged
  are listed there too. Stale bound *text* outside those sites (comments, build-script messages
  such as `cuems-power-bridge/debian/rules`) is reviewed with the same rule as test literals. Within
  a repository's bump, the relations are the **last** edit before the commit: the version and the
  relations that name it land in one commit, and a half-finished edit never commits relations ahead
  of their version.
- **FR-006**: Each packaged repository MUST be built for Debian 12 (bookworm) from local sources,
  in an environment that does not alter the host, with `cuemsutils` supplied as a wheel built from
  a **clean checkout of `cuems-utils` at its bump commit** (never from a working tree with
  uncommitted changes); the built package's version and interpreter configuration MUST be checked.
- **FR-007**: Each repository's own test suite MUST be run after the bump and compared against a
  run at the starting commit, with the same `cuemsutils` in both arms (the bumped library, from
  the same clean checkout); only failures absent at the starting commit count against this
  feature. A separate run with everything at its start (library included) isolates the library's
  own effect on each sibling.
- **FR-008**: Each repository's `xml-refactor-merge-candidate` message MUST be (re)written into
  `../.xml-refactor-tag-messages/`, naming the commit to tag, its version, the counterpart tags it
  composes with, and the state of its release-line reconciliation (FR-010). No tag is created or
  moved.
- **FR-009**: Each repository's changes MUST be committed GPG-signed and MUST NOT be pushed. A
  signing failure ("gpg failed to sign") is retried; `--no-gpg-sign` is never used. Local working
  state — the library worktrees, the `.venv`s, their `.git/info/exclude` entries, build scratch —
  MUST never enter a commit; the worktrees are removed at the end, the `.venv`s stay, excluded
  locally.

**Release-line reconciliation (deferred)**:

- **FR-010**: This feature MUST NOT merge, cherry-pick or adopt anything from a parallel release
  line (Clarifications). For each repository it MUST instead record, at its starting and final
  commits, how far the refactor branch is behind its release line and which released changelog
  entries are absent (planning document §10.1's `comm` recipe). Rule 4 is recorded as **not yet
  met** for every repository with a non-zero gap. The **"do not publish until reconciled"**
  statement MUST appear in: the feature record, that repository's tag message, its new top
  changelog entry, and this repository's `CHANGELOG.md` `0.1.1` section. Two content gaps MUST be
  named wherever they apply: **`stop_project`** (released in `cuems-utils 0.1.0rc17` and
  `cuems-engine 0.1.0rc6-5`; a project saved by an rc17 cluster with that cue is refused by `0.1.1`)
  and **`CACHEDIR.TAG`** (`cuems-utils 0.1.0rc16+1`, `cuems-power-bridge 0.3.0-8`). After the later
  reconciliation, each repository's relations MUST be re-verified against
  `contracts/relation-matrix.md` — an obligation on that future work, owned by the maintainer, stated
  in each tag message.
- **FR-010a**: **`cuems-engine`'s release-line state** (resolved 2026-10-15, Clarifications). It has
  a release line the planning document says it lacks. Re-measured after the new engine work landed:
  start commit **`7d0bda3`**; `origin/debian/bookworm` and `origin/release/0.1.0rc6-5` both at
  `0.1.0rc6-5`; the refactor branch is **119 behind / 26 ahead** of `debian/bookworm`. The target
  `0.1.1-1` sorts above it. Its phase re-measures once more at its start (FR-001, FR-002).
- **FR-011**: The install demonstrations MUST be updated to the new versions and bounds in the
  same commit as the relations they test, and run with every ref passed explicitly (planning
  document §11.1 steps 2–3), against clean checkouts only. Evidence that is not full validation MUST
  say so in every record and tag message that cites it: demonstrations run at the bump commits,
  **not on re-cut tags** (planning document rule 5); and the relations of `cuems-engine`,
  `cuems-editor`, `cuems-power-bridge` and `cuems-utils`, checked **by `dpkg --compare-versions`
  only** — no install demonstration exists for them.

**This repository** (planning document §5–§8):

- **FR-012**: The deprecation removal release MUST move from `v0.1.1` to `v0.1.2` everywhere it
  is stated in code, tests and non-frozen documents; the removal planning document MUST be renamed
  accordingly and its citations fixed. **Frozen** means a landed feature directory —
  `specs/004-*` … `specs/009-*` and `specs/011-*` … `specs/015-*`; `specs/010-*` is open and is
  edited.
- **FR-013**: The version-pin test MUST be rewritten, not deleted, to pin the new release matrix
  — so that a stray bump still fails the suite — and a green run of its *old* form after this
  feature MUST be impossible. Its assertion on this repository lands with the bump commit; its
  assertions on the siblings' `feat/xml-refactor` heads land with the record commit, once those
  heads exist.
- **FR-014**: `cuems-frontend` MUST take its first real version, **`0.1.0`**, at every version
  site it has (`package.json` and any lock file that records the project's own version), without
  creating a git tag, and receive a candidate-tag message. It has no `debian/` and no package
  relation, so FR-005 and FR-006 do not apply to it; its build check is its own production build,
  and FR-007's two-arm rule applies to its test run. Its compatibility contract with the library
  stays the payload handshake.
- **FR-015**: `CLAUDE.md` MUST be corrected where it is measured wrong — its claim that
  `debian/bookworm` is retired and tagged `packaging-rc14` (planning document §9) — and gain a
  Recent Changes entry for this feature, including the deferred release-line reconciliation.
- **FR-016**: Repositories are taken in this order, **mandatory** (FR-020 does not relax it):
  1. **`cuems-utils` bump commit** — first, because every sibling build resolves
     `cuemsutils>=0.1.1` and only this commit provides it (no `0.1.1` exists anywhere else);
  2. `cuems-common` → `cuems-nodeconf` → `cuems-power-bridge` → `cuems-engine` → `cuems-editor` →
     `cuems-frontend`;
  3. **`cuems-utils` record commit and its tag message** — last (D27), since the message names
     every other repository. **The `cuems-utils` candidate tag goes on the record commit.**
- **FR-017**: The planning document MUST be updated, not deleted, at the end of this feature:
  its §3–§8 and §11 step 6 are done, but rule 4 (§10), the tag re-cut, validation on the re-cut
  tags (§11.1) and publication are not. Per this repository's deletion policy it is deleted only
  once all of that is done.
- **FR-018**: Before any repository is edited, a **readiness preflight** MUST pass and be recorded
  in this feature's directory: every host tool the builds and install demonstrations check for,
  subordinate uid/gid ranges, GPG signing in all seven repositories, pyenv 3.11.9 (built with
  `--enable-optimizations --with-lto`), the `hatch` matrix for `cuems-utils`, a working `.venv`
  per sibling Python repository, the frontend's Node/Chrome toolchain, and network access to the
  Debian mirror and PyPI (the checks in `quickstart.md` §0). Anything missing that needs elevated
  rights is handed to the maintainer as one exact command to run; implementation does not start
  until a re-run of the preflight is clean.
- **FR-019**: Every sibling Python suite MUST run on pyenv 3.11.9 from that repository's own
  `.venv`, in both arms of FR-007's comparison; `cuems-utils` runs its `hatch` test environments.
  Each suite record MUST state the interpreter path it ran on.
- **FR-020**: `cuems-engine`'s suite MUST run against the **real** `pyossia`, from the `cuems3`
  wheel its Poetry dev group pins (Clarifications, resolved), installed into its pyenv `.venv`
  together with its other dev-group packages, and MUST run as the engine's CI runs it — two passes,
  `-m "not integration" -n auto` and `-m "integration and not slow"`. The preflight checks
  `pyossia.__version__ == "2.0.0rc6+124.cuems.3"`. A full `poetry install` MUST NOT be used in that
  venv, because it would replace the editable `cuemsutils` with PyPI's.
- **FR-021**: After each repository's commit and tag message, implementation MUST stop, present
  that repository's record (FR-001–FR-009, FR-019 evidence and commit hash) and wait for the
  maintainer's **explicit go-ahead** — a reply in the session, recorded with its date in the
  repository record — before starting the next repository in FR-016's order. A correction requested
  at a stop is **amended into that repository's bump commit by default** (re-signed, still
  unpushed), so the version bump lands as one clean commit with no trail of partial errors and
  fixes; a separate commit is used only when the maintainer asks for one. After any amend, the
  repository record and its tag message are rewritten to name the new commit hash, and the
  superseded hash is noted in the record as replaced. **An amend to a commit that later phases
  already used MUST re-run those dependents** — their builds, install demonstrations and suites —
  and update their records and messages, so the set stays coherent: an amend of the `cuems-utils`
  bump re-runs every sibling build, demonstration and suite done so far; an amend of
  `cuems-common` re-runs `cuems-nodeconf`'s demonstration. In `cuems-utils`, a correction targets
  the bump commit if it concerns the bump, and the record commit otherwise.
- **FR-022**: `cuems-engine`'s `poetry.lock` is **not relocked** by this feature: its new bound
  `cuemsutils>=0.1.1,<0.1.2` is unresolvable until `0.1.1` is published, and a lock naming a local
  source must never be committed. The engine bump commit MUST instead add a test asserting
  `poetry check --lock` passes, marked **strict xfail** with a reason naming publication, so it turns
  `XPASS` — and fails — the day the relock lands. "Relock `cuems-engine`" joins the
  do-not-publish-until list in the engine's changelog entry and tag message (FR-010).
- **FR-023**: `cuems-engine/debian/control` MUST declare the runtime dependency it loads but never
  declared: **`libmtcmaster (>= 0.0.2-0)`** on `cuems-engine` (`src/cuemsengine/core/libmtc.py`
  loads `libmtcmaster.so.0`). `0.0.2-0` is the published release (GitHub `v0.0.2-0`); `libmtcmaster`
  is not bumped and not edited. The relation is a new row in `contracts/relation-matrix.md` with its
  own verdicts (`0.0.1-1` refused; `0.0.2-0`, `0.0.2-1` admitted). libossia is an **independent
  input**: `python3-pyossia (>= 2.0.0-rc6+124+cuems3)` and the dev-group wheel pin stay unchanged,
  and move together whenever libossia releases.
- **FR-UX-001**: Operator-facing text this feature touches — changelog entries, deprecation
  warnings, tag messages — MUST follow each repository's established changelog and message
  conventions; the deprecation wording changes only in the release it names.
- **FR-PERF-001**: No runtime path changes, so no runtime budget applies. The only budget is the
  test suite's: per-test time in each repository MUST stay within the 115% tolerance this
  repository adopted in feature 015, compared as interleaved runs of the starting and final commits,
  **three samples per arm**.

### Key Entities

- **Repository record**: one per repository — starting commit, measured version state (FR-002),
  target, final commit(s), suite result in both arms, build result, tag-message path.
- **Version site**: a place stating a repository's own version (changelog head, project metadata,
  module constant).
- **Package relation**: a versioned `Depends:`/`Breaks:` or a Python dependency bound, naming
  another package; owned by the repository whose control file declares it
  (`contracts/relation-matrix.md`).
- **Candidate-tag message**: one file per repository in the shared folder; names commit, version
  and counterparts. The tag itself is the maintainer's.
- **Evidence**: the outputs of version comparisons, builds, suites and install demonstrations,
  stored in this feature's directory; added, never overwritten (reruns are suffixed).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 7 of 7 repositories state their target version at every self-version site
  (`cuems-frontend` at `0.1.0`), and 0 targets collide with a version released on any remote
  branch.
- **SC-002**: All 25 versioned relation sites of `contracts/relation-matrix.md` (24 moved + the new
  `libmtcmaster` declaration) hold their new value; 100% of its verdicts give the expected admit/refuse result, and the same verdicts
  **fail** against the starting bounds (fail-before).
- **SC-003**: 6 of 6 packaged repositories build for Debian 12 from local sources, producing the
  expected binary packages (`cuems-engine` also `cuems-engine-mock`), and 5 of 5 virtualenv-based
  packages (all but `cuems-common`, which ships no venv) were built from the system interpreter
  (`home = /usr/bin`).
- **SC-004**: Both install demonstrations exit successfully against clean checkouts (no
  `(+ uncommitted changes)` flag in their evidence), with evidence that lists each scenario and its
  refusing tool, written to new files.
- **SC-005**: 7 of 7 candidate-tag messages exist, each naming a commit that is its repository's
  committed head — for `cuems-utils`, the record commit at the head of
  `016-coordinated-minor-bump` — and every `Pairs with` commit equals the `Tag:` commit in that
  repository's own message.
- **SC-006**: 0 commits pushed and 0 tags created or moved by this feature, in any repository,
  measured as: `origin/<branch>` unchanged from FR-001's record, and every
  `xml-refactor-merge-candidate^{commit}` equal to the value recorded before the first edit.
- **SC-007**: 0 references to `v0.1.1` as the removal release remain in this repository's code,
  tests or non-frozen documents (FR-012 defines frozen).
- **SC-008**: 7 of 7 repository records state the release-line gap at the starting and final
  commits, and every repository with a gap says so in its tag message.
- **SC-QUALITY-001**: Lint and type-check finding counts in **this repository** do not rise (ruff
  0, mypy ≤ 72). Sibling quality gates are not measured by this feature.
- **SC-TEST-001**: The rewritten version-pin test fails at the starting commit and passes at the
  final one; each sibling suite shows zero failures present after the bump and absent before it.

## Assumptions

- **"A local environment prepared for Debian 12"** means a disposable, unprivileged bookworm root
  built with `mmdebstrap --mode=unshare`, the method feature 011 and both sibling install
  demonstrations already use. The host is Debian 13 (Python 3.13), so a host build would not test
  what ships. A bookworm Python virtualenv on the host alone is not that environment.
- **The tag-message folder is `../.xml-refactor-tag-messages/`** (Clarifications), created empty by
  the maintainer 2026-10-15. Earlier messages applied to the current tags are not in it, so every
  message is written fresh, using the existing tags' messages (`git tag -n99`) as the starting point
  where a tag exists.
- **`UNRELEASED`** is the changelog distribution for every bumped entry. The planning document's
  §10.1 sketch shows `unstable`; the release step that replaces `UNRELEASED` is publication, and it is
  out of scope here.
- **The target table is the planning document's §3**, re-derived by FR-002's measurement. The
  2026-10-15 measurement moved one target: `cuems-power-bridge` released `0.3.1-2` from
  `release/0.3.1-2` that day, numbered "above the open xml-refactor line", so the refactor line
  takes **`0.3.2-1`** (research R2).
- **The six siblings are all clean and level with their remotes today** (measured 2026-10-15), so
  FR-001 starts from a known state.
- **Publication** (PyPI, the `.deb` archive) and **the tag re-cut itself** are out of scope:
  planning document rule 5 and §11 steps 7, 9–10 belong to the maintainer after this feature.
- **Merging `016-coordinated-minor-bump` into this repository's `feat/xml-refactor`** is out of
  scope and the maintainer's, as with every feature here. Until then `cuems-utils`' candidate commit
  lives on the 016 branch, and its tag message says so.
- **Abandonment**: every commit is local and unpushed, so dropping the bump midway is
  `git reset --hard <start commit>` on each affected repository's branch — the maintainer's decision,
  never taken by the implementation on its own.
- **Folding a stale `UNRELEASED` entry (FR-003) is not a merge.** It edits only the refactor
  branch's own changelog and so is in scope, even though absorbing the release line's entries
  verbatim (planning document §10.1 rule 1) is deferred.
- Rule-4 items re-implemented in this library (planning document §10.4, foreign-controller
  scoping) are already landed and need no work here.

## Dependencies

- Feature 015's consumer halves are all closed (CLAUDE.md, 2026-10-15), so every sibling's
  `feat/xml-refactor` is the state the tag is meant to capture.
- Building and installing need `mmdebstrap`, `uidmap`, `equivs`, `dpkg-dev`, `debhelper`,
  `dh-virtualenv`, `fakeroot`, `uv`, subordinate uid/gid ranges for the user, and network access
  to the Debian mirror and PyPI (for third-party dependencies only).
- **Host readiness, measured 2026-10-15** (the FR-018 preflight's first run):

  | Item | State |
  |---|---|
  | `mmdebstrap` 1.5.7, `uidmap`, `dpkg-dev` 1.22.22, `dh-virtualenv` 1.2.2, `fakeroot`, `uv`, `hatch` | ✅ present |
  | subuid/subgid `adria:100000:65536` | ✅ |
  | GPG signing (`B25EB0EDCB9F13C2`, `commit.gpgsign=true` in all seven repositories) | ✅ signs |
  | pyenv 3.11.9 with `--enable-optimizations --with-lto`, `CC=gcc-12` | ✅ |
  | Node 20.19.2, npm, `/usr/bin/google-chrome` | ✅ |
  | **`equivs`** (`equivs-build`) | ❌ **missing** — both install demonstrations exit 2 without it |
  | **`debhelper`** (`dh`) | ❌ **missing** — host-side `dpkg-buildpackage` of `cuems-common` needs it |
  | `cuems-engine/.venv` | ⚠ points at pyenv 3.11.9 but has no `site-packages`; to be rebuilt |
  | `cuems-editor`, `cuems-nodeconf`, `cuems-power-bridge` `.venv` | ❌ absent; to be created |
  | `pyossia` | ✅ resolved: the engine's dev group pins the `cuems3` wheel (FR-020); installed into `cuems-engine/.venv` by T003 |

  The maintainer's command for the two missing packages: `sudo apt install equivs debhelper`.
