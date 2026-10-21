<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Feature Specification: Release-line reconciliation before `0.1.1`, then the first-stable-release cleanup

**Feature Branch**: `017-release-line-reconciliation`
**Created**: 2026-10-17
**Status**: Draft
**Input**: User description: "Feature `017-release-line-reconciliation` for cuems-utils. Branch off `feat/xml-refactor` (`5e4c637`, version `0.1.1` UNRELEASED; the candidate tag is on `4b336cd`). **Goal.** Absorb this library's release line `origin/debian/bookworm` (`398a9cf`, `0.1.0rc17`, 77 commits behind) and `origin/main` (`23e4752`, tag `v0.1.0rc17`) into the refactor before `0.1.1` is published ("merge before bump", rule 4 of `specs/planning/coordinated-release-version-bump.md`). Nothing shipped in `0.1.0rc15`, `rc16`, `rc16+1` or `rc17` may be lost, and the absorbed code must obey the refactor's contract […]. **The work order** is `specs/planning/release-line-reconciliation-0.1.1.md` […]. **Final phase: the first-stable-release cleanup (§14).** […] **Last task.** The final task of `tasks.md` deletes the planning file once 017's artefacts carry all of its content (§11 step 13). **Clarify list and limits.** Treat §12 as the clarify list. Out of scope: publishing, tag moves, pushes, sibling edits (write upstream reports), the `v0.1.2` removal, and new behaviour beyond A-1. **Constitution.** TDD […], performance budgets as bands with interleaved A/B, no new runtime dependency, actionable errors. Planning artefacts go under `specs/017-release-line-reconciliation/`, evidence under its `evidence/`, upstream reports under its `upstream-reports/`, and 016's evidence is never overwritten." (full text in the `/speckit-specify` invocation of 2026-10-17; it is Appendix A of the work order, verbatim).

## Clarifications

**The clarify list is the work order's §12** (twelve questions), restated with their
answers under [Open questions for `/speckit-clarify`](#open-questions-for-speckit-clarify).
All twelve are answered (sessions below); no requirement remains provisional.

### Session 2026-10-17

- Q (Q1, D5): Which action types may have no target? → A: **`{stop_project}` only, in a named
  set** — plus a task to write a planning document (`specs/planning/`) explaining how
  `pause_project` / `resume_project` would be incorporated, with clear examples and/or code, and
  their relation to `libmtcmaster`: how the engine would use that library's interfaces (as wrapped
  by `cuems-engine`'s `core/libmtc.py`) to pause and resume (play) the MTC timecode (FR-053). The
  document is written in 017; implementing those values is not. *(Reframed on 2026-10-21 by Q13:
  the values are retired, and the document is their handover.)*
- Q (Q2): A `stop_project` cue that still carries a target (e.g. a uuid left over from a cue edited
  from `stop`)? → A: **Accept it as is and ignore it; no new rule** (FR-023). *(Superseded
  2026-10-21: repaired to `None` by a repairable rule. See "Q2 revisited".)* Raised in answering:
  could `stop` be "repaired" into project-scope behaviour? **No, measured**: `stop` and
  `stop_project` are distinct `ActionType` values checked by T1, no T2 rule rewrites `action_type`,
  and `action_target_required` stays non-repairable, so a `stop` with no target is still refused.
  Renaming `stop` → `stop_cue` (explicit cue- vs project-scope naming) is **not done in 017** — it
  is a cross-repository wire change (every v1/v2 document, `cuems-engine`'s dispatch tables,
  `cuems-frontend`) and would reopen 014's ambiguous-version-2 window — but it is **recorded as a
  future option in the FR-053 planning document**.
- Q: The CI gate run (FR-075) needs the 017 head on the remote, and pushing is out of scope. How is
  it reached? → A: **The gate moves out of 017.** It runs on `feat/xml-refactor` after the
  maintainer's `--no-ff` merge. 017 delivers the restructured workflow and the evidence template
  (`evidence/ci-gate.md`, with every field to fill in); the green run is a **hand-off item**, and
  SC-013 is verified then, not before 017 hands off. This departs from work order §14.5 ("before
  017 hands off: one dispatched run on the 017 head") and §14.6, by decision.
- Q (Q11): Which CI jobs does the gate block on? → A: **3.11 (`lint`, `unit`, `integration`,
  `coverage`) and `packaging` (the `debian:bookworm` `.deb` build) block; 3.12 and 3.13 are
  informational** (`continue-on-error`) until the pre-existing 3.13
  `test_public_api_matches_the_snapshot` failure is fixed, which is not 017's work.
- Q (Q7): How does `CHANGELOG.md` mark releases that never reached PyPI? → A: **Mark `0.1.0rc17`,
  `0.1.0rc9`, `0.1.0rc12` "(Debian only; not published to PyPI)", and one line saying `0.1.0rc13`
  was never built.** The completeness test's PyPI set is **re-measured at hand-off**; a marking is
  dropped if that version has been uploaded by then. Whether to upload rc17 stays the maintainer's
  call and is not asked by 017.

### Session 2026-10-18

- Q (Q5): The clean-merged rc15 edits to the frozen `Parsers.py` (+6 lines) / `XmlBuilder.py`
  (+29) — keep or revert? → A: **Keep both as merged**, frozen-shim contract tests green — **and
  the machinery moves to the public API where real usage needs it**: every behaviour those edits
  provide (an all-digit `file_md5` kept a string on read; the media children written in schema
  order) MUST be shown to hold through `CuemsScript.save` / `load` by a public-API test, and is
  ported there (red test first) wherever it does not. The legacy copies are not the ones 0.1.1's
  consumers are meant to rely on, and `v0.1.2` deletes them.
- Q (Q10): After 017, does `debian/bookworm` keep releasing? → A: **Continue.** It may keep cutting
  `0.1.0rcN` until `0.1.1` is published; the new structure and the package versions are already
  agreed with the development team, so no freeze is requested. 017's pre-hand-off re-fetch merges
  anything new by the same method (FR-004), and the hygiene report asks for the test layout and no
  tracked build outputs, not for a freeze.
- Q (Q3, S-3): Should `cuems-reshape-devices` / `cuems-convert-documents` run T2 before writing?
  → A: **Report, don't refuse.** After writing, each tool runs the loader's own T1+T2 check on what
  it wrote and reports every document the loader would refuse — a WARNING naming the document and
  the rule, and a distinct entry in the run summary / `--check`. What is written, and the exit
  status, do not change (both tools run in `postinst`, which never fails). This is the one
  reporting-only addition beside A-1's rule.
- Q (Q4, S-4): Fix the missing `__main__` guard in `xml/reshape_devices.py` inside 017? → A:
  **Yes, in 017**: the guard plus a test that `python -m cuemsutils.xml.reshape_devices` actually
  runs the tool (FR-029a), so both migration tools behave alike.
- Q (Q6): `Replaces: cuems-engine (<< 0.1.0rc6-2~)` without a matching `Breaks:`? → A: **Keep it
  as released**, `Replaces:` only (a file moving between packages needs only `Replaces`, and engine
  `0.1.1-1`'s `cuems-utils (>= 0.1.1)` floor upgrades both together). No row 27 (FR-036, FR-040).
- Q (Q12): `ToDo.md` and the tracked `.claude/settings.local.json`? → A: **Triage `ToDo.md`** (each
  item still true moves to `specs/planning/`, done or superseded items are recorded as such, then the
  file is deleted) **and untrack + ignore `settings.local.json`** (FR-061).
- Q (Q9): `v0.0.9rc7`, a PyPI release on neither line — pointer only, or also an ancestry merge?
  → A: **Also `git merge -s ours v0.0.9rc7`** (signed, a third merge after `origin/main`), its
  message citing the measured equivalence (`git diff v0.0.9rc7 v0.0.9rc8 -- src/cuemsutils/cues/CuemsScript.py
  src/cuemsutils/cues/MediaCue.py` is empty, and rc8 is an ancestor), so future stray sweeps stop
  flagging it. Its tree diff MUST be empty. The "Earlier releases" pointer still covers it in
  `CHANGELOG.md` (FR-001, FR-005, SC-001).
- Q (Q8): Should `MediaCue.media_status()` enter the public-API snapshot? → A: **Extend the snapshot
  to all of `MediaCue`'s public methods** (`MediaCue` joins `PUBLIC_CLASSES` in
  `tests/contract/test_public_api_surface.py`), as one deliberate, recorded re-hash of
  `tests/golden/api/public_api.json` (FR-026a).

### Session 2026-10-21

- Q (Q13, maintainer, after the plan): Do `pause_project` / `resume_project` stay in the
  vocabulary? → A: **No. Project pause/resume is deferred to a future release and is not part of
  `0.1.1`.** Its vocabulary is **retired from this repository**: both values leave
  `script.xsd`'s `ActionType`, in the still-unreleased version-2 step with no version 3, and leave
  the enum audit's retained set. Its logic, vocabulary and prior art go to a **new planning
  document**, `specs/planning/project-pause-resume-deferred.md`, for a clean handover (FR-029d,
  FR-053). The cue-level `pause` action is **not** affected. Measured 2026-10-21 to bound the
  retirement:
  - **no producer:** zero hits in `cuems-frontend` (`feat/xml-refactor`, `origin/dev`,
    `origin/main`), `cuems-editor` (all lines), `cuems-nodeconf` and `cuems-power-bridge`;
  - **no document:** zero hits in this repository's corpus and goldens;
  - **no implementation on any live line:** in this repository the values appear only in the enum
    (`script.xsd:321-322`) and in `tests/contract/test_enum_audit.py:24`. `cuems-engine` names them
    as unimplemented (`cues/ActionHandler.py:29`) and parametrizes them in
    `tests/test_action_cue.py:1519` on its `debian/bookworm`. Its only implementation is 2020 prior
    art on `origin/dev` (`src/cuems/ActionCue.py:95-97`, `9852d79`).

  So no field document can carry them, and no conversion is registered. The released rc17
  `CHANGELOG.md` line that says they "stay in the enum" is kept verbatim as the release record, and
  `0.1.1`'s section records the retirement. This **supersedes FR-053's original framing** (Q1: "how
  they would be incorporated") with a retirement handover. Q1's targetless set is unchanged.

- Q (Q2 revisited, maintainer, after the plan): Can a `stop_project` cue's leftover target be
  degraded to `None`, and how? → A: **Option C: repair it to `None`**, through a new
  **repairable** T2 rule, `project_action_takes_no_target`. This **supersedes Q2's "accept and
  ignore; no new rule"**. Its behaviour, read from the code (research R16):
  - **On load**, the repair machinery substitutes the field's declared default, `None`, which is
    exactly the target. `load_with_report` returns REPAIRED with a `RepairRecord` (the previous
    uuid, `None`, the rule name), and the file is reported stale.
  - **On `save`**, it is refused. `save` refuses every T2 violation, repairable or not, so a
    `stop_project` built in code with a target raises `ValidationError` with an actionable
    message. `from_json` constructs, and the following `save` refuses.
  - **`validate()`** reports it.

  Two existing pieces of machinery need small companion edits so the rule is correct (R16):
  - `action_target_resolves` skips targetless types, so a **dangling** leftover uuid gives **one**
    finding, the repairable one, rather than an unrepairable refusal that fires first in
    registration order.
  - The descriptor's per-field repairability map changes from "the last registered rule wins" to
    "repairable only if every rule targeting the field is repairable". Measured: no field has
    disagreeing rules today, so no classification and no golden moves, and `ActionCue.action_target`
    stays UNREPAIRABLE for every other action type.

- Q (analyze I2, maintainer): The tag message's `Tag:` line cannot name the post-merge commit
  before it exists. Must the maintainer re-cut without editing the message? → A: **No (option b).
  The `Tag:` line is the one field the maintainer fills at re-cut.** The commit coordination
  comes after 017's merge, because it also depends on siblings landing and on upstream requests
  that may arrive after this work. 017 writes everything else, and leaves `Tag:` as an explicit
  placeholder naming the 017 head it must contain (FR-044, SC-010, T083).

- Q (checklist CHK021, maintainer): How is a bookworm merge (M1) that is rejected at its stop point
  recovered? → A: **Trial branch first (option A).** M1 is made on a local scratch branch,
  `017-m1-trial`, in its own worktree, started from the 017 head, and its evidence is presented
  there.
  - **Approved:** the 017 branch is fast-forwarded onto it (`git merge --ff-only 017-m1-trial`), so
    the reviewed, signed commit is exactly the one that lands. The scratch branch and worktree are
    then removed.
  - **Rejected:** the scratch branch is deleted and the merge is redone.

  The 017 branch never holds a rejected merge, and no history is rewritten. This applies to M1
  only; M2 and M3 have no stop point of their own and are made on the 017 branch after the
  fast-forward (FR-002).

### Measured corrections (plan, 2026-10-21)

- **M1 — `0.1.0rc5` and `0.1.0rc6` were never published** (`research.md` R9). PyPI's JSON API
  (yanked files included) has no rc5 or rc6, neither has a git tag, rc5's Debian entry is
  `UNRELEASED`, and rc6 has none. The work order's §7.2 listed both as PyPI releases. By Q7's
  intent, their existing `CHANGELOG.md` sections are kept and marked "(never published: no Debian
  build, not on PyPI)", joining rc13 in the never-published set (FR-032, FR-033).
- **M2 — FR-033 check (4) contradicted FR-030.** "No `UNRELEASED` entry but the top" cannot hold
  while FR-030 keeps the six old never-built entries (`0.1.0rc5`, `0.0.7-31`, `0.0.7-3`, `0.0.7-2`,
  `0.0.6-0`, `0.0.1-0`), which are `UNRELEASED` by nature. Check (4) now applies to entries **above
  the oldest released entry** (`0.1.0rc8`): between the top and rc8, only the top may be
  `UNRELEASED`. That is the case the check exists for, HEAD's retrospective rc15 entry.
- **M3 — the rc17 fixture lives in `tests/data/rc17/`, not `tests/data/corpus/`** (implementation,
  T016). The corpus is a pinned inventory: `tests/support/corpus.py` lists every document, pins a
  count per directory, and requires a pre-refactor verdict in `outcomes.json`, which must never be
  regenerated with `--force`. An rc17-written document has no pre-refactor verdict. 014 met the
  same constraint and put its fixture in `tests/data/media_block/` (`tests/unit/test_media_block.py`
  says why), and 017 follows that precedent. The work order's §6.1 wording ("checked into
  `tests/data/corpus/`") is superseded by this one fact; nothing else moves.

## Specification workflow

| # | Command | Purpose here | Status |
|---|---|---|---|
| 1 | `/speckit-specify` | This document | ✅ done 2026-10-17 |
| 2 | `/speckit-clarify` | Mandatory. Answer §12 Q1–Q12; Q1 (the targetless set, D5) decides A-1's scope | ✅ done 2026-10-18 (Q1–Q12 + the CI-gate question) |
| 3 | `/speckit-plan` | Merge procedure, the A-items as red→green pairs, research (§12 answers, re-measured §2), quickstart for the trial worktrees and the bookworm build | ✅ done 2026-10-21 (measured corrections M1, M2) |
| 4 | `/speckit-checklist` | A **merge-safety** checklist: no hunk dropped, no stray landed, no tag moved, no push, 016 evidence untouched, every retirement recorded | ✅ done 2026-10-21 (`checklists/merge-safety.md`, 40 items, six findings) |
| 5 | `/speckit-tasks` | In the work order's §11 order; the last task deletes the work order (FR-060) | ✅ done 2026-10-21 (85 tasks; T085 deletes the work order; the checklist findings are closed by T001/T007/T011/T026/T081–T083) |
| 6 | `/speckit-analyze` | Mandatory. Spec ↔ plan ↔ tasks ↔ checklist, and the traceability table below against the work order, before the merge is attempted | pending |
| 7 | `/speckit-implement` | §11 steps 1–13 | pending |

## Work order and its lifetime

**Work order**: [`specs/planning/release-line-reconciliation-0.1.1.md`](../planning/release-line-reconciliation-0.1.1.md)
(the *work order* below), as committed in `2318dee`. Its decisions (§0), inventory (§4, §4.1),
conflict rules (§5), seams (§6), packaging and changelog shape (§7), sibling obligations (§8), docs
(§9), acceptance (§10), execution order (§11), clarify list (§12), measurement recipe (§13) and
cleanup (§14) are this feature's requirements' source. This spec **binds** them and restates what
the work order's deletion (FR-060) must not lose; the plan, research and evidence carry the rest
(see [Traceability](#traceability-to-the-work-order)).

**The work order is temporary.** It is deleted as the final task of this feature, once every one
of its sections is traceable from this directory. Its last commit is linked from here so the
history stays reachable.

**Decisions already taken by the maintainer (work order §0), binding here:**

| # | Decision |
|---|---|
| D1 | The pre-spec session wrote no code. (Discharged.) |
| D2 | Branch `017-release-line-reconciliation` off `feat/xml-refactor`. `origin/debian/bookworm` merges in, then `origin/main`, then the adaptations. The branch merges back into `feat/xml-refactor` with `--no-ff`; the **maintainer** re-cuts the candidate tag. Agents never move tags. |
| D3 | `CHANGELOG.md` is complete from `0.1.0rc5` on, enforced by a **permanent** test that also checks `debian/changelog`. Before `0.1.0rc5`, one "Earlier releases" pointer. |
| D4 | The absorbed tests are **ported to the public API**. An assertion that contradicts a settled refactor decision is retired, and the retirement recorded. Known today: one (rc15's uppercase-md5 normalisation versus 014's strict rule). |
| D5 | Which action types may have no target is decided in clarify (Q1). |
| D6 | The version **stays `0.1.1`**. The top changelog entry grows; it is not renumbered. Every consumer's `>= 0.1.1`, `<< 0.1.2~` bound is unchanged. |
| D7 | Validation runs on the re-cut tags. Nothing waits for PyPI. |

## Scope

**In scope.**
- Everything reachable from `origin/debian/bookworm` and `origin/main` and not from
  `feat/xml-refactor`: source, tests, docs, packaging, changelogs.
- Adapting that content to the refactor's contract: the public object API (`cuemsutils.xml`
  exports nothing), strict reading (T1 + T2 on every load), version-2 scripts with **no version 3**,
  `xs:boolean`, the device-class shape, typed node maps (`node_role`).
- Re-verifying this repository's package relations, including the edge 016's matrix misses (X-2).
- Rewriting this repository's tag message (a text file in `../.xml-refactor-tag-messages/`).
- The first-stable-release cleanup and the pre-publication CI gate (work order §14).

**Out of scope.**
- Publishing (PyPI, the archive), pushing, and creating or moving any tag: maintainer acts.
- Editing any sibling repository. Siblings' obligations are written as upstream reports.
- The deprecated-surface removal (`v0.1.2`, `specs/planning/deprecated-surface-removal-v0-1-2.md`).
- New behaviour beyond what the absorbed releases and the A-items require. A-1's
  `project_action_takes_no_target` (Q2 revisited) is the only new rule. The migration tools'
  post-write T2 report (FR-029c, Q3) is the only other addition, and it only reports. The one **removal** is the retirement of `pause_project` / `resume_project`
  (FR-029d, Q13).
- Project-scope pause/resume itself, in any repository: deferred to a future release, handed over
  through `specs/planning/project-pause-resume-deferred.md`.
- Overwriting or editing `specs/016-coordinated-minor-bump/` evidence, or any landed `specs/0NN-*`.

**Moving target.** The release line keeps releasing. The snapshot below is what this spec measures;
the implementation re-measures at its start and again before hand-off, and merges anything newer
the same way (FR-004).

### The snapshot (measured 2026-10-17, re-checked at spec time)

| Ref | Commit | What | Refactor behind |
|---|---|---|---|
| `feat/xml-refactor` | `2318dee` (`5e4c637` + the pre-spec commit) | `0.1.1 UNRELEASED` | — |
| `xml-refactor-merge-candidate^{commit}` | `4b336cd` | current candidate tag, an ancestor | — |
| `origin/debian/bookworm` = tag `debian/0.1.0rc17` | `398a9cf` | **the release line**, `0.1.0rc17` | **77** (51 non-merge, 26 merge) |
| `origin/main` = tag `v0.1.0rc17` | `23e4752` | the upstream/PyPI line; ⊂ bookworm in content | 11 |
| merge-base | `07a7f9f` (2026-08-03) | — | — |

PyPI's newest is `0.1.0rc16`; **`0.1.0rc17` is not on PyPI** although it is tagged and its `.deb`
shipped. `rc9`, `rc12` are Debian-only; `rc13` was never released anywhere, and neither were `rc5`
and `rc6` (M1, measured 2026-10-21).

## User Scenarios & Testing *(mandatory)*

The actors are the **operator** (whose node upgrades from a `0.1.0rc17` cluster to `0.1.1`), the
**show author** (who builds cues in the frontend and saves them through the editor), the
**maintainer** (who re-cuts tags, decides which line releases, and publishes), the **release-line
maintainer** (who cuts `0.1.0rcN` from `debian/bookworm`), and the **sibling maintainers** (engine,
editor, frontend, power-bridge) who build on this library.

### User Story 1 — A show that ends itself survives the upgrade (Priority: P1)

A show author on an rc17 cluster has authored a cue that ends an unattended show
(`stop_project`, which needs no target). After the cluster is upgraded to `0.1.1` and its projects
are migrated (`cuems-reshape-devices`, then `cuems-convert-documents`), the project loads cleanly
on every node, and the author can still create, save and reload such a cue from code and from the
frontend's JSON, where the target arrives as `null`.

**Why this priority**: it is the one finding where the merge alone silently breaks the field
(work order S-1). Without A-1, every project saved on an rc17 cluster with a `stop_project` cue is
**refused by every `0.1.1` node** at load, after both migration tools have reported success.

**Independent Test**: a captured rc17-written document (VideoCue with all four media values, an
AudioCue, a `stop_project` cue with an empty target) goes through reshape → convert →
`load_with_report` and comes back CLEAN; a `stop_project` cue built through the public API with no
target round-trips through `save` / `load_with_report`; `from_json` accepts `"action_target": null`.

**Acceptance Scenarios**:

1. **Given** the captured rc17 fixture, **When** it is reshaped, converted and loaded through the
   public path, **Then** the outcome is CLEAN and the cue's action type is `stop_project` with no
   target.
2. **Given** a `stop_project` cue built through the public API with no target, **When** it is saved
   and reloaded, **Then** the save succeeds, the document carries an empty target element, and the
   load is CLEAN.
3. **Given** a JSON payload with `"action_type": "stop_project", "action_target": null`, **When**
   it is decoded through `from_json`, **Then** construction succeeds.
4. **Given** a `stop` cue with no target, **When** it is saved or loaded, **Then** it is still
   refused by T2 with the existing actionable message (negative twin).
5. **Given** an unknown action type, **When** it is saved or loaded, **Then** it is still refused
   by T1 (negative twin).
6. **Given** the same rc17 document with its last cue replaced by `stop` aimed at the audio cue,
   **When** it is migrated and loaded, **Then** it is CLEAN, as it already is on `5e4c637`
   (control).
7. **Given** a document whose `stop_project` cue still carries a target uuid, resolving or
   dangling, **When** it is loaded, **Then** the outcome is REPAIRED, the target is `None`, the
   report names `project_action_takes_no_target` and the uuid it replaced, and the file is flagged
   stale. **When** the same cue is saved from code, **Then** the save is refused with that rule's
   actionable message.

---

### User Story 2 — Nothing the release line shipped is lost (Priority: P1)

The maintainer inspects the `0.1.1` candidate and finds every fix and feature released in
`0.1.0rc15`, `rc16`, `rc16+1` and `rc17` present, behaving as released wherever the refactor's
contract allows, each proven by a test that drives the **public** API, and the release line fully
an ancestor so the next release-line commit merges without re-conflicting.

**Why this priority**: it is rule 4 itself. A `0.1.1` that omits a shipped fix is a regression for
every rc-line node that upgrades.

**Independent Test**: `git rev-list --count HEAD..origin/debian/bookworm` and `..origin/main` are
0 against freshly fetched refs; the evidence table gives each inventory item the proof FR-003
assigns it (a passing public-API test for every behaviour item); the suite on the merged branch has no failure `5e4c637` lacks.

**Acceptance Scenarios**:

1. **Given** fresh refs, **When** behind-counts are measured at hand-off, **Then** both are 0 and
   `v0.1.0rc17` plus every `debian/*` tag are ancestors of HEAD.
2. **Given** an invalid media block in a cue list, **When** `get_media` is called, **Then** it
   raises a named `ValueError`, skips `None` entries with a warning, and `get_own_media` never
   raises (869fej07m, rc16).
3. **Given** the four stored media values on a version-2 document, **When** it is loaded, **Then**
   they are `int`, `int`, `int`, `str`; **when** they are absent, `.get(k)` and the attribute
   return `None` and `to_wire()` omits them (rc15 / 014; X-4).
4. **Given** the merged tree, **When** the suite runs, **Then** the six merged-only failures of the
   work order §6.1 are fixed, not skipped.

---

### User Story 3 — The package installs and upgrades correctly (Priority: P2)

The operator installs the `0.1.1` `.deb` over an rc-line node, or beside an old `cuems-engine`,
and `dpkg` neither aborts on a file conflict nor leaves a stale cache tag in the shared venv.

**Why this priority**: two shipped packaging fixes (`Replaces: cuems-engine (<< 0.1.0rc6-2~)` for
`cffi-gen-src`, and the `CACHEDIR.TAG` strip) are absent from the refactor's `debian/`. 016's build
lacked `CACHEDIR.TAG` only because the chroot's virtualenv happened not to write one.

**Independent Test**: packaging tests that fail on `5e4c637` and pass after; a bookworm-chroot build
of `0.1.1` with its checks recorded; the relation verdict script reports 121/121 plus row 26's
five.

**Acceptance Scenarios**:

1. **Given** the merged `debian/control`, **When** the `cuems-utils` stanza is read, **Then** it
   declares `Replaces: cuems-engine (<< 0.1.0rc6-2~)`, with its own stated reason, beside the
   unchanged `Breaks: cuems-common (<< 1.3.1~)`.
2. **Given** `cuems-engine` at `0.1.0rc5-6` or `0.1.0rc6-1`, **When** dpkg compares, **Then** it is
   replaced; at `0.1.0rc6-2`, `0.1.0rc6-5` or `0.1.1-1`, it is not.
3. **Given** the built `.deb`, **When** inspected, **Then** `Version: 0.1.1`, `home = /usr/bin`,
   `bin/python -> ../../../bin/python3`, no `usr/lib/cuems/CACHEDIR.TAG`, and
   `usr/lib/cuems/bin/cffi-gen-src` present (expected; verified, not assumed).

---

### User Story 4 — The release history is complete, and stays complete (Priority: P2)

Anyone reading `CHANGELOG.md` or `debian/changelog` finds every build and release since
`0.1.0rc5`, with the released Debian entries byte-identical to the release line, and a permanent
test that fails the day a released entry goes missing or drifts again.

**Why this priority**: two release candidates once left the tree with no changelog entry at all,
and the header-only comparison used before would not have caught that HEAD's `0.1.0rc15` entry is a
different, never-built entry with the same number.

**Independent Test**: the completeness test fails on `5e4c637` and passes after; it runs on a
shallow checkout by carrying the released set as data.

**Acceptance Scenarios**:

1. **Given** the merged tree, **When** the changelogs are parsed, **Then** the top entry is `0.1.1`
   in both and equals `__version__`, and it no longer says "not reconciled".
2. **Given** the release line's released entries, **When** compared, **Then** each is
   byte-identical here, and HEAD's retrospective `0.1.0rc15 UNRELEASED` entry is gone, its body
   folded into `0.1.1`.
3. **Given** a checkout without the release-line refs, **When** the test runs, **Then** it checks
   the carried data and skips only the cross-check, with a reason.

---

### User Story 5 — Siblings and the maintainers know what changed (Priority: P3)

Each sibling maintainer finds an upstream report naming their half of the `stop_project` wire
contract; the release-line maintainer finds a hygiene note; the maintainer finds a rewritten tag
message ready to re-cut, and `CLAUDE.md` / docs that describe `0.1.1`, not rc17's deprecated
parser.

**Why this priority**: the wire contract (frontend authors → editor saves through this library →
engine runs → power-bridge reacts) only holds when every half lands at its re-cut tag.

**Independent Test**: the reports and the tag message exist with the required content; the
coordinated-bump planning document's owed list points at 017.

**Acceptance Scenarios**:

1. **Given** 017's `upstream-reports/`, **When** read, **Then** there is one note each for the
   editor, frontend, engine (Q13) and power-bridge, and a release-line hygiene note.
2. **Given** `../.xml-refactor-tag-messages/cuems-utils.txt`, **When** read, **Then** "NOT YET
   RECONCILED" is replaced by "Reconciled with origin/debian/bookworm at `<sha>` (0.1.0rc17)",
   "Carries" lists items 1–5 and A-1, and `Tag:` is a placeholder for the maintainer naming the 017
   head the tagged commit must contain.

---

### User Story 6 — A clean first stable release (Priority: P3)

A new contributor or user of `0.1.1` finds no scratch directories, no stale to-do list, no
personal settings tracked, a README and published docs that teach only the public API, and a test
tree where every test sits in, and is marked by, its kind's directory.

**Why this priority**: `0.1.1` is the first real stable release; the docs currently present the
modules `v0.1.2` deletes as the way in, and the published site documents them.

**Independent Test**: the §14.6 acceptance checks (greps, the directory-marker contract test, an
unchanged pass set before and after the cleanup).

**Acceptance Scenarios**:

1. **Given** the cleaned tree, **When** the stale-path grep runs outside `specs/`, **Then** it
   returns nothing, and `dev/` does not exist.
2. **Given** the collected suite, **When** the contract test runs, **Then** every item carries
   exactly one directory marker and no `tests/test_*.py` sits at the root.
3. **Given** the pass set before the cleanup, **When** compared to after, **Then** it is identical
   apart from the recorded retirements.

---

### User Story 7 — A pre-publication gate the maintainer can run in the cloud (Priority: P3)

The maintainer dispatches the test workflow on a ref, with the siblings checked out at a chosen
tag, and gets a green or red verdict whose summary names every commit it ran against, without that
run deploying docs or uploading coverage.

**Why this priority**: today the cross-repository tests skip in hosted CI, and the docs workflow
deploys from any ref, including a PR from the refactor branch.

**Independent Test**: within 017, the workflow's structure, inputs and deploy/upload conditions
are checked statically (a test or lint over the workflow file). At hand-off, after the maintainer
merges 017 into `feat/xml-refactor` and pushes, one green dispatched run on that head is recorded
in `evidence/ci-gate.md` (Clarifications, gate question).

**Acceptance Scenarios**:

1. **Given** a dispatch on the post-merge `feat/xml-refactor` head (after hand-off) with
   `siblings_ref` set to the candidate tags, **When** it runs, **Then**
   the sibling-reading tests run (the summary reports ran versus skipped), and the run is green on
   3.11.
2. **Given** a dispatch or a pull request, **When** it runs, **Then** neither the docs deploy nor
   the coverage upload happens.

### Edge Cases

- **The release line moves during the feature.** Re-measure at the start and before hand-off; merge
  the delta by the same method (merge, never cherry-pick) and loop through the adaptations for it.
- **A naive conflict resolver cuts `debian/README.Debian`**: its `======================` underline
  begins with `=======`. It is resolved by taking ours whole, never by marker splitting.
- **`-X ours` / `-X theirs`** would silently drop whole hunks of absorbed fixes; forbidden.
- **`debian/compat` beside `debhelper-compat (= 13)`** is a debhelper error that fails the build;
  deleted in the merge commit with the other strays.
- **A `stop_project` cue that carries a leftover target** (edited from `stop`): repaired to `None`
  on load and reported; refused on save with an actionable message (Q2 revisited). A dangling
  leftover gives one finding, not two. No path converts one action type into another.
- **`cuems-convert-documents` reports "converted" for a document the loader then refuses** (S-3):
  the tools validated T1 only. After A-1 the S-1′ case passes; for any other such document the tools
  now warn and list it in their summary after writing (FR-029c, Q3), without changing what is
  written or the exit status.
- **`python -m cuemsutils.xml.reshape_devices` exits 0 and does nothing** (S-4): no `__main__`
  guard. Fixed in 017 with a test (FR-029a, Q4 answered).
- **An absorbed assertion contradicts a refactor decision** (rc15 md5 case folding vs 014's raise):
  retired with its reason, never "fixed" by weakening the refactor.
- **The known flake** `test_descriptor_laziness.py::…[project_mappings]` fails intermittently in
  both arms; it is not a reconciliation item and must not be counted as one.
- **3.13 fails `test_public_api_matches_the_snapshot` in both arms**: pre-existing; CI gates on 3.11.
- **Moving test files before the final re-merge** would turn clean release-line merges into rename
  conflicts; the cleanup runs last.
- **GPG signing fails**: retry; never `--no-gpg-sign`.
- **A document carrying a retired value** (`pause_project`/`resume_project`, Q13): none is known.
  No producer has ever written one (measured), so none exists in the field. If one surfaces, the
  loader refuses it with T1 (an enumeration violation on `action_type` listing the allowed values), and the handover document says how to reinstate it.
  No conversion silently rewrites it into another action.

## Requirements *(mandatory)*

### Functional Requirements

#### Merge (work order §2–§3, §4, §4.1)

- **FR-001**: The release line MUST be absorbed by **two real merges** on the feature branch:
  `origin/debian/bookworm` with `--no-ff`, then `origin/main` with `--no-ff` (ancestry of the
  `v0.1.0rc17` tag; its tree diff MUST be empty), followed by **one ancestry-only merge**,
  `git merge -s ours v0.0.9rc7` (Q9; tree diff empty; message cites the rc8 equivalence).
  Cherry-picking MUST NOT be used for any item.
- **FR-002**: The bookworm merge commit MUST contain the §5 conflict resolutions and the stray
  deletions **and nothing else**. Adaptations, packaging, docs and cleanup are separate, later
  commits, in the work order's §3 commit shape. All commits are GPG-signed. Two further rules
  (checklist CHK003, CHK016):
  - No merge uses `-X ours` / `-X theirs`, or any strategy other than the default; M3 is the one
    `-s ours` merge, on purpose.
  - The planning artefacts are committed **before** M1, so M1 never carries an unrelated change.
  - M1 is made and reviewed on a scratch branch, `017-m1-trial`, and reaches the 017 branch only
    by `git merge --ff-only` after approval. A rejected trial is deleted and redone, never fixed
    forward, and never reset on the 017 branch (checklist CHK021).
- **FR-003**: Every inventory item (table below) MUST be present on the merged branch by its
  assigned method and MUST be demonstrated in one evidence table: a behaviour item (1–5) by one named
  test that passes through the public API (packaging items 4–5 by their packaging tests); a
  history-only item (6–8, 13, 14) by its recorded check (patch equivalence, subject twin, ancestry,
  empty tree diff); item 9 by the changelog test; items 10–12 by their FR-011 / FR-032 / FR-050
  checks.
- **FR-004**: The §2 measurements and the §4.1 stray sweep MUST be re-run at the start and again
  before hand-off against freshly fetched refs; anything newer on either line MUST be merged the
  same way, and every stray ref MUST carry a verdict. The release line is expected to keep
  releasing (Q10), so a pre-hand-off delta is the normal case, not an exception: each new release
  gets its inventory row, its changelog entry (verbatim) and its public-API test before hand-off.
- **FR-005**: The stray-sweep verdicts are binding unless re-measurement changes the facts:
  `v0.0.9rc7` — no code (rc8 carries it), covered by the "Earlier releases" pointer, and made an
  ancestor by the `-s ours` merge of FR-001 (Q9, answered), so a later sweep no longer lists it; `feat/faders`, `options`, `parser-fixxes` — excluded, with the work
  order's reasons; `gh-pages` — not source.

**Inventory (work order §4), binding:**

| # | Item | Released in | Method | Adaptation |
|---|---|---|---|---|
| 1 | `stop_project` ActionType (869fhjdq5, PR #19) | rc17 (deb, tag; not PyPI) | merge (enum clean) + resolve header | A-1, A-2, A-3 |
| 2 | Media guards: `media_status()`, `get_media` named `ValueError` + skip `None`, `get_own_media` never raises (869fej07m, PR #16) | rc16 | merge + resolve (`CueList` hunk 2 → theirs) | A-3 (port 17 tests to `tests/unit/`) |
| 3 | Stored media values `pixel_width`/`pixel_height`/`file_size`/`file_md5` (869fat84r, PR #13) | rc15 | merge + resolve **ours** (014 re-implemented it, same names) | A-4 (retire the md5-lowercase test, port the rest) |
| 4 | `Replaces: cuems-engine (<< 0.1.0rc6-2~)` (PR #14) | rc15 | merge + resolve (both) | A-5, relation row 26 |
| 5 | No `/usr/lib/cuems/CACHEDIR.TAG` (PR #18) | rc16+1 | merge + resolve (`rules`: theirs, then ours) | A-5 |
| 6 | ease_in/ease_out names | — | merge | none (patch-equivalent) |
| 7 | 22 subject-twin commits of 2025 `main` history | rc8/rc9 era | merge (history only) | none |
| 8 | Packaging history rc5…rc14 | rc5–rc14 | merge | none, except `debian/compat` deleted |
| 9 | Release/version commits | each | merge + resolve (version sites → ours) | changelogs (FR-030–FR-034) |
| 10 | 42 bookworm-only build outputs and stray root files | never shipped | merge + **delete** | upstream hygiene note |
| 11 | `CHANGELOG.md` rc17/rc16 sections | — | merge + resolve | FR-032 |
| 12 | `CLAUDE.md` rc17 field note | — | merge (clean) | FR-050 |
| 13 | `origin/main` merge | `v0.1.0rc17` tag | merge | none (empty diff) |
| 14 | `v0.0.9rc7` ancestry (stray tag, work order §4.1 row 14) | PyPI `0.0.9rc7` | `merge -s ours` (Q9) | none (content in rc8, empty diff); "Earlier releases" pointer |

- **FR-003a (checklist CHK009)**: "As released, wherever the refactor's contract allows" has
  exactly these deliberate departures from what rc15–rc17 shipped. Each is recorded with its
  reason, and none other is permitted:
  1. an uppercase `file_md5` is **refused**, not lowercased (FR-027; 014's strict `Md5Type`);
  2. an empty `action_target` is stored as **`None`**, not `""` (FR-026; the refactor's coercion);
  3. a `stop_project` cue's leftover target is **repaired to `None` on load and refused on save**
     (FR-023);
  4. `pause_project` and `resume_project` are **removed from the vocabulary** (FR-029d, Q13);
  5. absorbed behaviour is reached through the **public API**, and the deprecated XML path keeps
     its rc15 edits only as a shim (FR-012, D4).
  6. a `stop_project` cue **accepts a `None` target** at construction and at the setter, where
     rc17 refused it (A-1, S-2: the frontend sends `null`). Two rc17 assertions are retired for
     it (T037, `evidence/test-retirements.md`).

  Any other ported rc-line assertion that fails is an adaptation (red → green), unless it
  contradicts a settled refactor decision. In that case it is retired with its reason (D4) and
  added to this list.

#### Conflict resolutions (work order §5)

- **FR-010**: The 11 conflicting files / 25 hunks MUST be resolved exactly as the work order's §5
  table states. In summary: version sites → **ours** (`__version__ = "0.1.1"`) plus theirs' SPDX
  contributor line; SPDX headers → **theirs' header, then ours' imports**; `CueList.get_media` →
  **theirs**; `MediaCue` accessors and both `script.xsd` hunks → **ours** (dropping theirs' second
  `Md5Type` declaration); `debian/control` → theirs' header, ours' build fields, **both** relation
  lines; `debian/rules` → theirs' header, then **theirs' `CACHEDIR.TAG` strip directly after
  `dh_virtualenv`, then ours' schema/defaults install and `override_dh_installdeb`**;
  `debian/README.Debian` → ours whole; `debian/changelog` rebuilt per FR-030; `CHANGELOG.md`
  per FR-032.
- **FR-011**: The 42 stray paths MUST be deleted in the merge commit. **The binding list is research
  R17's enumeration**: 21 build outputs including `debian/compat`, and 21 root files including
  `.python-version`. It is derived **three-way**, from paths added on bookworm since the
  merge-base, never by patterns or a two-way diff, which would sweep in files the refactor deleted.
  R17's ten kept additions are never deleted. A re-derived list that differs from R17 is a delta
  under FR-004 (checklist CHK010, CHK011).
- **FR-012**: The clean-merged rc15 edits to the frozen `Parsers.py` / `XmlBuilder.py` MUST be kept
  as merged, and the frozen-shim contract tests MUST stay green with them (Q5, answered). For each
  behaviour those edits provide — an all-digit `file_md5` read back as a string, and the four media
  children written in schema order — a test MUST demonstrate the same behaviour through the
  **public** path (`CuemsScript.save` / `load` / `load_with_report`). Where the public path lacks
  it, the behaviour MUST be ported there as an adaptation (red test first, its own commit); the
  legacy edit is not the implementation consumers rely on. Each behaviour's public-path test is
  listed in the inventory evidence table under item 3.

#### Adaptations (work order §6), each starting from a red test

- **FR-020 (A-1)**: The library MUST define **one** named set of targetless (project-scope) action
  types, containing **exactly `stop_project`** (Q1, answered). `pause_project` and `resume_project`
  are not candidates in 017: they are retired from the vocabulary (FR-029d, Q13), so they are
  refused by T1. Exactly these places MUST consult it:
  - the T2 rule `action_target_required`, which passes `None` when the action type is in the set
    and stays non-repairable;
  - the T2 rule `action_target_resolves`, which skips a type in the set, so one fault gives one
    finding;
  - the **new** T2 rule `project_action_takes_no_target` (FR-023), which fires for a type in the
    set whose target is not `None`;
  - the construction/setter guard, and through the constructor, `from_json`.

  Adding a member later MUST be a one-line change with its own test.
- **FR-021 (A-1 tests)**: Red tests first, then green: a public `save` → `load_with_report` round
  trip of `stop_project` with no target (CLEAN, writing an empty target element); `from_json` with
  `"action_target": null`; the **captured rc17 fixture** through reshape → convert → load CLEAN;
  and the negative twins (`stop` with no target refused by T2 at save and load; an unknown action
  type refused by T1).
- **FR-022 (A-1 fixture)**: The rc17 fixture MUST be produced by rc17's own writer (`398a9cf`'s
  `XmlReaderWriter`) per the work order's §13 recipe, checked into **`tests/data/rc17/`** with its
  provenance (commit, recipe, date), together with its `stop` control twin. It sits outside the
  pinned corpus (spec M3).
- **FR-023 (A-1, Q2 revisited)**: A project-scope action that carries a target MUST be **repaired
  to `None`** by a new T2 rule, `project_action_takes_no_target`. It applies to
  `("ActionCue", "action_target")`, is `repairable=True`, and its repair is the field's declared
  default `None`. Its message names the field, the value and the fix, for example: *"action_target
  `<uuid>` must be empty: `stop_project` acts on the whole project and takes no target; clear it"*
  (FR-081). Behaviour:
  - **load**: REPAIRED, with one `RepairRecord` (previous uuid → `None`, this rule's name) and the
    file reported stale. This holds whether the uuid **resolves or dangles**, and the dangling case
    produces no `action_target_resolves` finding.
  - **save**: refused with `ValidationError` naming this rule, for a cue built in code or via
    `from_json`.
  - **validate()**: reports it.

  Red tests first, for: load of a resolving and of a dangling leftover uuid (REPAIRED, one record
  each); save refusal; `validate()`; and that no path changes a cue's `action_type` (a `stop` cue
  with no target is refused, never converted).
- **FR-023a (A-1, descriptor)**: The descriptor's per-field repairability MUST become
  order-independent and conservative: a field is REPAIRABLE only if **every** rule targeting it is
  repairable. Today the last registered rule wins. Red test first: with the new rule registered,
  `ActionCue.action_target` is still UNREPAIRABLE (red if the map keeps last-wins and the rule is
  registered last). A second test asserts the map does not depend on registration order. Measured
  (R16): no field has disagreeing rules today, so every existing classification, the descriptor
  goldens and the frontend's published repairability stay byte-identical.
- **FR-024 (A-2a–c)**: The `ActionType` contract tests MUST enumerate **eleven** values by name:
  HEAD's twelve, plus `stop_project` from the merge, minus `pause_project` and `resume_project`
  (FR-029d). They keep their purpose: no `fade_in`/`fade_out` may return, and neither may the two
  retired values. The descriptor MUST publish the eleven (the frontend reads this list).
  `stop_project` MUST join the enum audit's retained set, and the two retired values MUST leave
  it. The evidence for all three changes is recorded in 017, since 008's `enum-audit.md` is
  frozen: `stop_project` is implemented by `cuems-engine` rc6-5 and authored by the frontend's
  `dev` line, and the retirement rests on Q13's measurements.
- **FR-025 (A-2d)**: `script.xsd`'s recorded hash MUST be updated in **the same commit as A-1**,
  and **every** `script.xsd` edit 017 makes lands in that commit: the `ActionType` comment, the
  Q13 removal, and FR-051's `stop_project` comment check. The hash therefore moves exactly once
  after M1 (checklist CHK037).
  **No version step**: `script` 1 → 2 is still unreleased (014's precedent), so no `doc_version="3"`
  and no registry entry.
- **FR-026 (A-3)**: rc17's `stop_project` tests (7) and rc16's media-guard tests (17) MUST be ported
  to the public API under `tests/unit/`; A-3a's constructor assertion is re-expressed by A-1's
  decision (the refactor's coercion maps `""` to `None` at construction).
- **FR-026a (Q8)**: `MediaCue` MUST join `PUBLIC_CLASSES` in
  `tests/contract/test_public_api_surface.py`, so the snapshot records every public method of
  `MediaCue` by the same enumeration rule the snapshot already applies to `CuemsScript` — including
  `media_status()` and the four stored-media accessors. This is **one** deliberate re-hash of
  `tests/golden/api/public_api.json`, made after A-1/A-3/A-4 have settled `MediaCue`'s surface: the
  `MediaCue` block is inserted by hand in sorted position, **every pre-existing entry stays
  byte-identical** (asserted by diff in evidence), `MANIFEST.sha256` is updated for that one file, and
  the event is recorded in `tests/contract/test_golden_immutability.py`'s docstring beside the
  earlier re-hashes (009, 011, axis D, foreign-controller scoping). The test is red before the
  golden carries the block (fail-before recorded).
- **FR-027 (A-4)**: rc15's `TestFileMd5::test_stored_lowercase` MUST be retired (014 raises on an
  uppercase md5 on purpose; every released producer lowercases before assigning), and the rest of
  rc15's media-value tests (22) ported next to the existing media-block tests.
- **FR-028 (A-5)**: Packaging tests MUST fail on `5e4c637` and pass after: the `Replaces:` line in
  the `cuems-utils` stanza, the `CACHEDIR.TAG` strip after `dh_virtualenv` in `debian/rules`, and
  the built `.deb` having no `usr/lib/cuems/CACHEDIR.TAG`. The `debian/control` comment that says
  "Replaces is deliberately absent" MUST be reworded so each relation states its own reason.
- **FR-029 (A-6)**: One unit test MUST pin X-4: on a version-2 `Media` loaded without the four
  elements, `.get(k)` and the attribute return `None` and `to_wire()` omits the keys; loaded with
  them, the values are `int`, `int`, `int`, `str`. The internal `Unset` is never exposed.
- **FR-029a (S-4)**: `xml/reshape_devices.py` MUST gain a `__main__` guard, with a test that
  `python -m cuemsutils.xml.reshape_devices` actually runs it (reports a verdict for a given file,
  as the console script does), red first (Q4, answered).
- **FR-029c (S-3, Q3)**: After writing, `cuems-reshape-devices` and `cuems-convert-documents` MUST
  each run the same T1+T2 check the loader runs on every document they wrote, and for each one the
  loader would refuse MUST emit a WARNING naming the document path and the failing rule, and list it
  under a distinct entry in the run summary. Under `--check`, which writes nothing, each tool MUST
  run the same check on the tree it **would** write and report it under the same entry. The
  written bytes and the exit status MUST NOT change. Red tests first: a document that is T1-valid and T2-invalid after
  migration (the rc17 control twin with its `stop` cue's target emptied) is written **and**
  reported; a clean document produces no such entry. The per-document
  cost of the extra check is measured (interleaved A/B over the same corpus) and recorded, not
  budgeted (013's precedent: the tools' cost is per-document validation).
- **FR-029d (Q13, retirement)**: `pause_project` and `resume_project` MUST be removed from
  `script.xsd`'s `ActionType`. This rides the unreleased `script` 1 → 2 step, with **no version 3
  and no conversion entry** (014's precedent, justified by Q13's measured absence of any producer
  or document). It MUST land **in A-1's commit**, so that `script.xsd`'s recorded hash changes once
  (A-2d). Red tests first:
  - a script carrying `action_type="pause_project"` or `"resume_project"` is refused by **T1** at
    `save` and at `load` (red on M3, where both validate);
  - `from_json` with either value is refused at the same point a document would be;
  - the descriptor's `ActionType` list no longer contains them.

  The `ActionType` comment in `script.xsd` MUST point at the handover document. `0.1.1`'s
  changelog entry and `CHANGELOG.md` section MUST record the retirement. The released rc17 line
  saying they "stay in the enum" is kept verbatim, because it is true of rc17.
- **FR-029b (D4)**: No retained test may import `cuemsutils.xml.XmlReaderWriter`, `Parsers` or
  `XmlBuilder` unless it is a frozen-shim contract test marked `expects_deprecation`.
  `evidence/test-retirements.md` is the **one index of every retirement**, with its reason. That
  covers a retired assertion (the md5 case folding), a retired script (`testdev_nng_talk.py`),
  absorbed root copies replaced by their ports, and retired vocabulary (Q13). The vocabulary row
  points at `specs/planning/project-pause-resume-deferred.md`, which holds the verbatim record
  (checklist CHK029, CHK030).

#### Packaging and changelogs (work order §7)

- **FR-030**: `debian/changelog` MUST be ordered by dpkg version: `0.1.1 UNRELEASED` (kept, body
  extended); `0.1.0rc17`, `0.1.0rc16+1`, `0.1.0rc16`, `0.1.0rc15` **verbatim** from the release
  line (the released `rc15` replaces HEAD's retrospective `0.1.0rc15 UNRELEASED` entry, whose body
  folds into `0.1.1`); `rc14`…`rc8` as already identical; the old never-built entries (`0.1.0rc5`,
  `0.0.7-*`) in HEAD's form, recorded as a deliberate exception to "verbatim".
- **FR-031**: The `0.1.1` entry's "NOT YET RECONCILED" bullet MUST become "Reconciled with
  debian/bookworm at `<sha>` (0.1.0rc17): absorbs rc15, rc16, rc16+1, rc17", with items 1–5 one
  line each, plus A-1's targetless rule.
- **FR-032**: `CHANGELOG.md` MUST have, below `0.1.1`, a section or a `<!-- debian: … -->` comment
  for every released version from `0.1.0rc5`: new sections for rc15, rc14, rc12, rc10, rc9 written
  from the Debian entries' text and dated by their trailers; a comment plus one line for rc16+1; the
  two mid-file `Unreleased` sections folded into `0.1.1`; one `## Earlier releases` pointer (git
  tags, PyPI). Per Q7 (answered): `0.1.0rc17`, `0.1.0rc9` and `0.1.0rc12` carry "(Debian only; not
  published to PyPI)", and one line records that `0.1.0rc13` was never built. Per M1, the existing
  `0.1.0rc5` and `0.1.0rc6` sections carry "(never published: no Debian build, not on PyPI)". The
  PyPI set is re-measured at hand-off from PyPI's JSON API (yanked files included), and a marking is
  removed if its version has been uploaded by then.
- **FR-033**: A **permanent** test (`tests/packaging/test_changelog_completeness.py`) MUST check,
  without needing git refs: (1) `debian/changelog` top = `__version__` = `CHANGELOG.md` top;
  (2) `debian/changelog` headers ⊇ the released Debian set carried as data (exactly rc8, rc9, rc10,
  rc11, rc12, rc14, rc15, rc16, rc16+1, rc17; **not** rc13), plus, when the refs exist, the release line's and every `debian/*` tag's headers;
  (3) every released entry on the release line is **byte-identical** here (when the refs exist);
  (4) no `UNRELEASED` entry but the top **among the entries above the oldest released one**
  (`0.1.0rc8`; the older never-built entries are exempt, M2); (5) `CHANGELOG.md` covers the released Debian ∪ PyPI
  (≥ `0.1.0rc5`) sets, has the "Earlier releases" pointer and exactly one `Unreleased` section;
  (6) every version in the released Debian set but not the PyPI set carries the "Debian only"
  marking (rc16+1, a Debian revision, is satisfied by its `<!-- debian: … -->` comment), every version in the never-published set (`0.1.0rc5`, `0.1.0rc6`, `0.1.0rc13`; M1)
  carries the "never published" marking or line, and no version in the PyPI set carries either.
  It MUST fail on `5e4c637`. Cross-checks that need refs skip with a reason, as
  `tests/support/sibling_tags.py` does.
- **FR-034**: `debian/rules` MUST carry all four of: the `/usr/bin/python3` pin, the `CACHEDIR.TAG`
  strip, 011's schema/defaults install, and the `override_dh_installdeb` relabel.
- **FR-035**: `0.1.1` MUST be built in the bookworm chroot with 016's build tool, writing to 017's
  own evidence. The tool is invoked as `UTILS=<clean worktree at the 017 head>
  OUT=<017 evidence file> bookworm-build.sh <same worktree>`. It refuses a dirty `UTILS` and an
  existing `OUT`, so it can never overwrite 016's evidence. If `mmdebstrap`, the mirror or the
  tool is unavailable, the build half of SC-007 is **recorded as not met**, never skipped silently
  (checklist CHK039). The build records `Version: 0.1.1`, `home = /usr/bin`, the relative `bin/python` link, no
  `CACHEDIR.TAG`, and whether `cffi-gen-src` is present.
- **FR-036**: Things that do not move: the version and every consumer bound; `REMOVAL_RELEASE =
  "v0.1.2"`; `test_no_version_bump.py`'s sibling pins; 016's evidence. `Replaces:` ships without a
  matching `Breaks:`, as released (Q6, answered); no `Breaks: cuems-engine` relation is added.

#### Sibling relations and reports (work order §8)

- **FR-040**: 017 MUST carry its own relation verdict tool (`tools/verdicts-017.sh`) that runs 016's
  121 verdicts plus **row 26**'s five (`Replaces: cuems-engine (<< 0.1.0rc6-2~)`: replaced for
  `0.1.0rc5-6`, `0.1.0rc6-1`; not for `0.1.0rc6-2`, `0.1.0rc6-5`, `0.1.1-1`), and it MUST report
  126/126 at hand-off. It MUST run against a parent directory of `git worktree`s, one per sibling
  at its `feat/xml-refactor` commit, with `cuems-utils` at the 017 head. Each sibling's commit is
  recorded with the result, so the verdict never depends on a sibling checkout's current branch. 016's matrix is landed record and is not edited.
- **FR-041**: X-1 (accept `stop_project` at save and load, from code, from JSON, and from a migrated
  rc17 project) MUST be discharged by A-1; X-2 by the merge plus row 26; X-3 (this package's half)
  by the merge plus A-5; X-4 MUST be answered **`None`** and pinned by A-6.
- **FR-042**: Upstream reports MUST be written under `upstream-reports/`: one each for
  `cuems-editor` (the `get_media` `ValueError` its refactor line now meets, and its half of
  `stop_project`), `cuems-frontend` (11 published action types, `stop_project` in and the two
  retired values out; `null` target accepted), `cuems-engine` (Q13: its `debian/bookworm`
  `tests/test_action_cue.py:1519` parametrizes the two retired values, and `ActionHandler.py:29`
  names them, so its reconciliation must drop them; the handover document is theirs to read),
  `cuems-power-bridge` (its half of the wire contract), and `release-line-hygiene.md` for the
  release-line maintainer (stop tracking build outputs and experiment files on `debian/bookworm`;
  rc17 not on PyPI; the test-layout and CI note — new tests go under `tests/unit/`,
  `integration/`, `contract/` or `packaging/`, never the root; and, per Q10, that the line **may
  keep cutting `0.1.0rcN` until `0.1.1` is published** — the structure and versions being agreed
  with the development team — and that each such release is merged into `feat/xml-refactor` by the
  same method, so no freeze is asked). `cuems-engine`'s PyPI-unresolvable `>= 0.1.0rc17` floor is recorded for the
  record only (its own pre-spec resolves it).
- **FR-043**: No sibling repository's files are edited.
- **FR-044**: `../.xml-refactor-tag-messages/cuems-utils.txt` MUST be rewritten. `Tag:` is an explicit
  placeholder that the **maintainer fills at re-cut**, naming the 017 head sha the tagged commit
  must contain (analyze I2, option b). The commit sha is coordinated after 017's merge, with the
  siblings' landings and any later upstream requests. "NOT YET RECONCILED" is replaced by the reconciled line with its sha; "Carries"
  gains items 1–5 and A-1; "Pairs with" is unchanged unless a sibling re-cut first; and it carries
  the pre-publication checklist line (FR-076).

#### Docs (work order §9)

- **FR-050**: `CLAUDE.md`'s merged `stop_project` field note MUST be rewritten for `0.1.1` (the value
  is in version-2 `script.xsd`; the targetless rule is A-1's; the skew rule becomes "every box on
  ≥ 0.1.1"; the rollback hazard stays), its "two packaging lines" paragraph MUST state the
  post-merge state (`debian/bookworm` ⊂ `feat/xml-refactor` at `<sha>`), and a Recent Changes entry
  for 017 MUST be added.
- **FR-051**: The merged `ActionCue` docstring MUST describe the public path, not the deprecated
  parser's "comes back as `None` because the parsers bypass the setter", and MUST NOT list
  `pause_project`/`resume_project` as existing values (Q13); the `script.xsd` comment on
  `stop_project` MUST make no deprecated-parser claim.
- **FR-052**: `specs/planning/coordinated-release-version-bump.md`'s "still owed" item 1 MUST mark
  `cuems-utils` reconciled, with the merge sha, pointing at 017. Landed `specs/0NN-*` dirs are not
  edited. 017 introduces no new use of the "rc17 F3/F4" shorthand.
- **FR-053 (Q1, reframed by Q13)**: 017 MUST write the handover document
  `specs/planning/project-pause-resume-deferred.md`. It is a living, forward-looking document, not
  part of 017's frozen record, and it is written **in the same commit as FR-029d's removal**, so
  the vocabulary is never gone without its record. With clear examples and/or code, it MUST cover:
  1. **What was retired, verbatim:**
     - the two `<xs:enumeration>` lines and their comment from `script.xsd` as of `2318dee`;
     - the enum-audit entries;
     - 008's `enum-audit.md` evidence for keeping them then;
     - rc17's `CHANGELOG.md` line;
     - the measured absence of producers and documents (Q13).
  2. **Prior art:** `cuems-engine` `origin/dev` `src/cuems/ActionCue.py:95-97` (`9852d79`, 2020),
     and the engine's current "unimplemented" listing and test parametrization.
  3. **How to reinstate them after `0.1.1`** (a released schema by then):
     - the additive enum value and the version step `script` 2 → 3 that it needs under the
       schema-evolution convention;
     - the one-line addition to `TARGETLESS_ACTION_TYPES` and its test;
     - the library side: T2, construction guard, `from_json`, the descriptor's published list,
       the enum audit;
     - the tests each value needs, using A-1's `stop_project` as the worked precedent.
  4. **The engine and `libmtcmaster`:** which of that library's interfaces (`MTCSender_pause`,
     `MTCSender_play`, as wrapped by `cuems-engine`'s `core/libmtc.py`) pause and resume the MTC
     timecode, and how the engine would drive them from these actions.
  5. **The sibling halves:** frontend authoring, editor save, power-bridge reaction.
  6. **As a future option, with its costs (Q2), explicit cue- versus project-scope naming:**
     renaming `stop` → `stop_cue` (and whether `play`/`pause`/… would follow). It states the
     documents the rename converts, the version step it needs, and the sibling sites it touches
     (`cuems-engine`'s action dispatch tables, `cuems-frontend`'s action authoring).

  Its claims about `libmtcmaster` and `cuems-engine` MUST be read from those checkouts
  (`../libmtcmaster`, `../cuems-engine`) and cited by path and commit, including the
  release-line commit for the engine's `stop_project` handler (research R12), not assumed. It
  implements nothing and edits no sibling.

#### Cleanup for the first stable release (work order §14.1–§14.4)

The cleanup runs **after the final re-fetch and re-merge**, one commit per sub-section, pure moves,
deletes and rewires, with the suite run after each commit and the pass set unchanged.

- **FR-060 (last task)**: The final task MUST delete `specs/planning/release-line-reconciliation-0.1.1.md`,
  after verifying that every section is traceable from this directory and that
  `git grep -n release-line-reconciliation-0.1.1 -- . ':!specs/017-*'` returns nothing (re-pointing
  any hit first). `cuems-engine`'s same-named file is in another repository and is not a hit.
- **FR-061**: `dev/` MUST be deleted (and `.gitignore`'s `dev/local` entry). `ToDo.md` MUST be
  triaged item by item — anything still true moves to `specs/planning/`, each done or superseded
  item is recorded as such in the cleanup commit message — then the file is deleted (Q12, answered). `.claude/settings.local.json` MUST be untracked and ignored; `.claude/settings.json` and the
  spec-kit tooling stay.
- **FR-062**: `README.md` and `docs/` MUST present only the public API (`CuemsScript.load` / `save` /
  `validate` / `from_json` / `to_wire`, `ConfigManager`, `cuemsutils.errors`); `docs/xml.md`'s
  mkdocstrings pages for `Parsers`, `XmlBuilder`, `XmlReaderWriter` MUST be replaced by the public
  surface; the `gradient_osc_port` … `NodeType` wording MUST use the current type name.
- **FR-063**: The 17 root test modules MUST move into `unit/` / `integration/` / `contract/` per the
  work order's §14.3 table, verified per file at move time; `testdev_nng_talk.py` MUST be retired
  and recorded. A collection hook MUST add the `unit` / `integration` / `contract` / `packaging`
  marker from the path; those markers MUST be registered; `--strict-markers` MUST be on; the
  `filterwarnings` path for `test_name_coercion` MUST follow its move; and a contract test MUST
  assert every collected item carries exactly one directory marker and no `tests/test_*.py` exists
  at the root.
- **FR-064**: `CONTRIBUTORS.md`'s testing section MUST say where new tests go (the release line has
  added all three absorbed test files at the root), and its release section MUST carry the
  pre-publication checklist line (FR-076).

#### CI gate (work order §14.4–§14.5)

- **FR-070**: `.github/workflows/tests.yml` MUST keep its file name (dispatch only works for a file
  present on `main`) and be restructured into jobs: `lint`; `unit` and `integration` in parallel
  after `lint` on 3.11, each producing coverage data; `packaging` in a `debian:bookworm` container
  (build, the FR-035 checks, the packaging tests without the chroot tests); `coverage` combining
  `unit` + `integration`, with the threshold on the combined figure; `matrix-info` on 3.12/3.13 as
  informational; and `gate-summary`. **Blocking set (Q11, answered)**: `lint`, `unit`,
  `integration`, `coverage` (all on 3.11) and `packaging`; `gate-summary` fails when any of them
  fails. `matrix-info` (3.12, 3.13) runs with `continue-on-error` and its result is reported in the
  summary but never fails the gate.
- **FR-071**: The workflow MUST gain a `siblings_ref` dispatch input (default
  `xml-refactor-merge-candidate`) that checks the six siblings out beside this repository, with
  tags, so the cross-repository tests run; the summary MUST report how many sibling-reading tests
  ran versus skipped.
- **FR-072**: `push` triggers MUST include `feat/xml-refactor` besides `main`.
- **FR-073**: The `gh-pages` deploy and the Codecov upload MUST run only on a `push` to
  `refs/heads/main`; a dispatch or a pull request MUST NOT deploy or upload.
- **FR-074**: The `gate-summary` job MUST record this repository's SHA, `siblings_ref` and each
  sibling's commit, pass/skip/xfail counts, the strict xfails, the sibling-test ran/skipped count,
  and the resolved `xmlschema` / `lxml` versions.
- **FR-075**: 017 MUST deliver `evidence/ci-gate.md` as a **template** naming every field the gate
  run records (run URL, tested SHA, `siblings_ref` and each sibling's commit, pass/skip/xfail counts,
  strict xfails, sibling-test ran/skipped, resolved `xmlschema`/`lxml`), and a static check of the
  workflow file (jobs, `needs:` graph, `siblings_ref` input, the `main`-only deploy/upload
  conditions, and that only the Q11 blocking set can fail `gate-summary`). The green
  `workflow_dispatch` run itself happens **after hand-off**, on
  `feat/xml-refactor`'s head once the maintainer has merged 017 with `--no-ff` and pushed, with
  `siblings_ref` at the current candidate tags; it is listed in the hand-off as owed, alongside the
  tag re-cut. 017 does not push.
- **FR-076**: `pypi-publish.yml` keeps its trigger; the pre-publication checklist line — a green
  dispatched run on the post-merge `feat/xml-refactor` head with every sibling at its reconciled
  re-cut tag, before the GitHub release and the `.deb` upload — MUST be written into the tag message
  and `CONTRIBUTORS.md`.

#### Process and constitution

- **FR-080 (Principle II)**: Every adaptation MUST start from a test that is red on the merge commit
  (or is added red first), recorded as a red→green pair in evidence.
- **FR-081**: No new runtime dependency. Every new refusal or error MUST name the field, the value
  and what to do (actionable errors).
- **FR-082**: Planning artefacts live under `specs/017-release-line-reconciliation/`, evidence under
  its `evidence/`, upstream reports under its `upstream-reports/`. 016's evidence is never
  overwritten.
- **FR-UX-001 (Principle III)**: Messages and vocabulary MUST match established conventions: A-1's
  refusals reuse the existing `action_target_required` wording for the types still outside the
  set; the action-type value is spelled `stop_project` everywhere (schema, wire, docs); changelog
  sections follow the existing `## <version> — <date>` convention; no new `rc17 F3/F4`-style
  shorthand.
- **FR-PERF-001 (Principle IV)**: Budgets are compared as **bands, with interleaved A/B** against
  `5e4c637` (015's precedent; tolerance 115%): the show-document load inside its band
  (16.465–17.750 ms) or no worse than arm A; suite ms/test within 115% of arm A; the `script`
  descriptor warm call within 115% of arm A. The interpreter build is recorded with every figure,
  and `scaling_cur_freq` is checked before an absolute figure is trusted. An exceeded budget is
  recorded as exceeded, never restated.

### Key Entities

- **Release line**: `origin/debian/bookworm` (Debian `0.1.0rcN` builds) plus `origin/main` (the
  upstream/PyPI tag line). Its absorption is measured by behind-counts reaching 0.
- **Inventory item**: one released change (or history class) with a method (merge, resolution,
  adaptation; never cherry-pick), a release it shipped in, and the test that proves it.
- **Targetless action set**: the one named set of project-scope action types that take no target;
  consulted by three T2 rules (`action_target_required`, `action_target_resolves`,
  `project_action_takes_no_target`), the construction guard and `from_json`. Exactly `{stop_project}` in
  017 (Q1). `pause_project` / `resume_project` are retired from the vocabulary (Q13). Reinstating
  them is described in the FR-053 handover document.
- **Retired vocabulary**: `pause_project`, `resume_project`, removed from `ActionType` in the
  unreleased version-2 step and recorded verbatim, with their prior art, in
  `specs/planning/project-pause-resume-deferred.md`.
- **Adaptation (A-n)**: a post-merge change that makes absorbed content obey the refactor contract,
  always a red→green pair.
- **Retirement record**: an absorbed test or script deliberately not kept, with its reason
  (`evidence/test-retirements.md`).
- **Relation row**: one package relation with its dpkg verdicts; row 26 is new in 017.
- **Released set**: the data the completeness test carries (released Debian versions, released PyPI
  versions ≥ `0.1.0rc5`, and the never-published versions `0.1.0rc5`/`rc6`/`rc13`), so it runs on
  shallow checkouts.
- **rc17 fixture**: a document written by rc17's own writer, with provenance, and its `stop` control
  twin.
- **Gate run**: a dispatched CI run whose summary names every commit it tested against.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (§10.1)**: At hand-off, against freshly fetched refs, the refactor is **0** commits behind
  `origin/debian/bookworm` and **0** behind `origin/main`; `v0.1.0rc17`, `v0.0.9rc7` and every
  `debian/*` tag are ancestors; the stray sweep is re-run and every row has a verdict.
- **SC-002 (§10.2)**: **14 of 14** inventory items are present, each with the proof FR-003 assigns
  to its kind (a passing public-API or packaging test, or a recorded history check), in one evidence
  table.
- **SC-003 (§10.3)**: The suite on the 017 head has **no failure that `5e4c637` lacks**, on the same
  host: 3.11 three times interleaved A/B, 3.12 and 3.13 once each. The six §6.1 failures are fixed,
  not skipped; the known `project_mappings` laziness flake is identified as such if it appears.
- **SC-004 (§10.4)**: An rc17-written project with a `stop_project` cue loads **CLEAN** on `0.1.1`
  after migration; a `stop_project` cue round-trips through save/load and through JSON with a `null`
  target; both negative twins stay refused; a leftover target (resolving or dangling) loads
  **REPAIRED** to `None` with exactly one `RepairRecord` and is refused on save;
  `ActionCue.action_target`'s descriptor classification stays UNREPAIRABLE and no descriptor golden
  moves.
- **SC-005 (§10.5)**: X-4 is pinned by one test; the three A-5 packaging tests fail on `5e4c637` and
  pass on the 017 head.
- **SC-006 (§10.6)**: **Zero** retained tests import the deprecated XML modules outside the marked
  frozen-shim contract tests; every retirement is listed with its reason.
- **SC-007 (§10.7)**: Relation verdicts **126/126** (016's 121 + row 26's 5). The `0.1.1` `.deb`
  builds in the bookworm chroot with all four FR-035 checks recorded.
- **SC-008 (§10.8)**: The changelog completeness test **fails on `5e4c637` and passes** on the 017
  head; neither the `0.1.1` changelog entry nor its `CHANGELOG.md` section says "not reconciled".
- **SC-009 (§10.9)**: The three performance budgets of FR-PERF-001 hold as bands with interleaved
  A/B, or are recorded as exceeded with their measurement.
- **SC-010 (§10.10)**: The tag message carries the four FR-044 changes. At re-cut, the maintainer's
  **only** edit is filling the `Tag:` placeholder, which names the 017 head it must contain
  (analyze I2). Every other line is final.
- **SC-011 (§10.11)**: Five upstream reports exist (editor, frontend, engine, power-bridge,
  release-line hygiene), and the coordinated-bump planning document's
  owed list points at 017.
- **SC-012 (§14.6)**: `dev/` does not exist; the stale-path grep returns nothing outside `specs/`;
  no `tests/test_*.py` at the root and every collected test carries exactly one directory marker
  (contract test); `pytest tests/unit tests/contract` passes without network; the pass set before
  and after the cleanup is identical apart from the recorded retirements; README and `docs/` name
  only the public API and the site has no deprecated-module pages.
- **SC-013 (§14.5–§14.6, amended by Clarifications)**: At 017's hand-off, the workflow passes its
  static check (all §14.5 jobs, the `siblings_ref` input, deploy and upload only on a push to
  `main`) and `evidence/ci-gate.md` exists as a complete template. **Verified after hand-off**: one
  green dispatched run on the post-merge `feat/xml-refactor` head fills that template, with
  sibling-reading tests reported as run, and neither a dispatch nor a PR deploys the docs or
  uploads coverage.
- **SC-014 (§11.13)**: The work order is deleted by the final task, and no live reference to it
  remains outside this directory.
- **SC-015 (Q1, Q13)**: `specs/planning/project-pause-resume-deferred.md` exists, landed in the
  same commit as the removal. It covers its six parts (retired text verbatim, prior art,
  reinstatement with its version step, engine/`libmtcmaster`, siblings, the `stop_cue` option),
  with at least one concrete example or code excerpt for parts 3–6. Every claim about another
  repository cites a path and commit.
- **SC-017 (Q13)**: `ActionType` has **11** values, neither retired value appears in
  `src/` or `tests/` outside the retirement's negative tests, the descriptor publishes the 11, and
  a document carrying either retired value is refused by T1 at save and load (red on M3).
- **SC-016 (Q8)**: The public-API snapshot includes `MediaCue` (with `media_status`), and the
  re-hash diff shows only the added `MediaCue` block; `test_public_api_matches_the_snapshot` passes
  on 3.11.
- **SC-QUALITY-001**: ruff stays at **0** findings; the mypy error set does not grow (same command on
  both arms; the box's disputed absolute figure is not the measure).
- **SC-TEST-001**: Every adaptation (A-1 … A-6, S-3, S-4, the Q13 retirement) has a recorded test that failed before its
  change and passes after; the changelog-completeness and directory-marker tests are permanent.

## Open questions for `/speckit-clarify`

The work order's §12 and how each was answered (all closed 2026-10-18).

| Q | Question | Answer | Binds |
|---|---|---|---|
| Q1 (D5) | Targetless set: `stop_project` only, or every `*_project` value (`pause_project`, `resume_project` exist in the schema, implemented nowhere)? | **Answered 2026-10-17: `stop_project` only, plus the FR-053 planning document** | FR-020, FR-053 |
| Q2 | A project-scope action that **carries** a target: accept, clear to `None` (repairable rule), or refuse? | **Answered 2026-10-17** (accept and ignore), **revised 2026-10-21: repair to `None`** via `project_action_takes_no_target`; `stop_cue` naming stays a future option in FR-053's document | FR-023, FR-023a, FR-053 |
| Q3 | Should the migration tools run T2 before writing (S-3)? | **Answered 2026-10-18: report after writing (WARNING + summary entry); bytes and exit status unchanged** | FR-029c |
| Q4 | Fix the missing `__main__` guard in `reshape_devices` (S-4) inside 017? | **Answered 2026-10-18: yes, guard plus a `python -m` test** | FR-029a |
| Q5 | Keep the clean-merged rc15 edits to frozen `Parsers.py` / `XmlBuilder.py`, or revert? | **Answered 2026-10-18: keep; each behaviour proven (or ported) on the public path** | FR-012 |
| Q6 | `Replaces:` without `Breaks:`? | **Answered 2026-10-18: keep as released, no `Breaks:`** | FR-036 |
| Q7 | Mark Debian-only releases (rc17, rc9, rc12) and the never-built rc13 in `CHANGELOG.md`? Will rc17 be uploaded to PyPI? | **Answered 2026-10-17: mark them, rc13 one line, PyPI set re-measured at hand-off**; the upload is the maintainer's call | FR-032, FR-033 |
| Q8 | Should `MediaCue.media_status()` enter the public-API snapshot? | **Answered 2026-10-18: yes — all of `MediaCue`'s public methods, one recorded re-hash** (departs from the work order's recommendation) | FR-026a |
| Q9 | `v0.0.9rc7`: pointer only, or also an `-s ours` ancestry merge? | **Answered 2026-10-18: also the `-s ours` merge** (departs from the work order's recommendation) | FR-001, FR-005 |
| Q10 | After the merge, does `debian/bookworm` keep cutting `0.1.0rcN` until publication? | **Answered 2026-10-18: yes, continue** (structure and versions agreed with the team); re-merge per FR-004 | FR-004, FR-042 |
| Q11 | CI: gate on 3.11 only with 3.12/3.13 informational, and include the `.deb` build in the gate? | **Answered 2026-10-17: yes to both** | FR-070 |
| Q12 | `ToDo.md`: triage to `specs/planning/` or delete? `.claude/settings.local.json`: untrack? | **Answered 2026-10-18: triage then delete; untrack and ignore** | FR-061 |
| Q13 (added) | Do `pause_project` / `resume_project` stay? | **Answered 2026-10-21: no; deferred to a future release; retired to `project-pause-resume-deferred.md`** | FR-029d, FR-053 |

## Assumptions

- The snapshot holds at the start of implementation; if a line moved, FR-004 governs and the
  numbers in this spec are re-measured rather than trusted.
- The work order's §6.1 measurements (six merged-only failures; 3769/3834 passed) are
  **indicative**, taken on one host without a chroot; the implementation's own interleaved runs are
  the evidence.
- The hatch `test.py3.11` environment (uv-managed CPython 3.11.9) is the measurement interpreter for
  this repository, as in 015 and 016. Siblings are read at their `feat/xml-refactor` **commits**,
  through `git worktree`s made for the purpose, never through whatever branch their checkout
  happens to be on. Measured 2026-10-21: `../cuems-engine` is checked out on
  `009-release-line-reconciliation`, 3 commits ahead of its `feat/xml-refactor` (analyze U2).
- Packaging lifecycle tests that need `CUEMS_CHROOT_TAR` run where the chroot tarball exists and
  skip with a reason elsewhere. On this box it exists
  (`/home/adria/.cache/cuems-lifecycle/bookworm-deps.tar`, measured 2026-10-21). Where it does
  not, the result is recorded as skipped with the reason, and SC-005's built-`.deb` half is
  recorded as not met rather than passed.
- "The release line moved" (FR-004) means **any change in the sha of `origin/debian/bookworm` or
  `origin/main`, or any new `debian/*` or `v*` tag**, after a fresh `git fetch --all --tags
  --prune` (checklist CHK038).
- **The CI gate run is a hand-off item** (Clarifications): it needs a pushed ref, pushing is a
  maintainer act, and so the run is made on `feat/xml-refactor` after the merge, not on the 017
  head.
- `feat/xml-refactor` currently sits at `2318dee`, one local docs commit above `5e4c637`; the work
  order's arm A is `5e4c637`, and the two trees differ only in `specs/planning/`.

## Traceability to the work order

So that the final task can delete it (FR-060), each section must have a home in this directory.

| Work order section | Home in 017 |
|---|---|
| §0 decisions | this spec (Work order and its lifetime) |
| §1 goal, scope | this spec (Scope) |
| §2 measured lines | this spec (snapshot) + `research.md` (re-measured) |
| §3 strategy, methods, commit shape | FR-001–FR-002 + `plan.md` |
| §4 inventory | FR-003 table + `evidence/` inventory table |
| §4.1 stray sweep | FR-004–FR-005 + `research.md` |
| §5 conflict rules | FR-010–FR-012 + `plan.md` (full per-hunk table) |
| §6 seams, A-1…A-6, S-1…S-4 | FR-020–FR-029d (incl. FR-026a) + `research.md` + `evidence/` |
| §7 packaging, changelogs | FR-030–FR-036 |
| §8 sibling relations | FR-040–FR-044 + `upstream-reports/` |
| §9 docs | FR-050–FR-052 |
| §10 acceptance | SC-001–SC-011 |
| §11 execution order | `tasks.md` |
| §12 clarify list | Open questions → `## Clarifications` + `research.md` |
| §13 measurement recipe | `quickstart.md` + `evidence/` |
| §14 cleanup and CI | FR-060–FR-076, SC-012–SC-014 |
