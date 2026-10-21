---
description: "Task list for 017 — release-line reconciliation before 0.1.1, then the first-stable-release cleanup"
---

# Tasks: Release-line reconciliation before `0.1.1`, then the first-stable-release cleanup

**Input**: `specs/017-release-line-reconciliation/` — [spec.md](spec.md), [plan.md](plan.md),
[research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/),
[quickstart.md](quickstart.md), [checklists/merge-safety.md](checklists/merge-safety.md).

**Tests are mandatory** (constitution II, spec FR-080). Every adaptation starts from a test that is
red on its base. The red output and the green output are both recorded in
`evidence/red-green.md`. A check that is already green on its base is recorded as `held`, never
given an invented red (research R7).

**Standing rules for every task**:
- Every commit is GPG-signed (`git commit -S`). On "gpg failed to sign", retry, and **never** use
  `--no-gpg-sign`.
- No push, no tag created or moved, no publication.
- No file in a sibling repository is edited.
- Nothing under `specs/016-coordinated-minor-bump/` is written.
- Suites run with `CUEMS_CONF_PATH` unset, on the hatch `test.py3.11` interpreter
  (`PY=$(uvx hatch env find test.py3.11)/bin/python`).
- `$S` is the session scratchpad. `R=/disk/Projects/StageLab/cuems-utils`.
- `E=specs/017-release-line-reconciliation/evidence`.

**Order note.** The template orders phases by user story. Here, three merges (Phase 2) block
everything. The cleanup and CI stories (US6, US7) run **after** the final re-fetch (Phase 10), so
moved test files cannot turn a later release-line merge into rename conflicts (spec §Edge Cases,
plan Phase 9).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[USn]**: the spec's user story (US1–US7)
- ⏸ = a stop point: present the evidence and wait for the maintainer's go-ahead (plan §Phases)

---

## Phase 1: Setup (re-measure, baseline, clean starting point)

**Purpose**: a committed planning state, a re-measured snapshot, and arm A's baselines, before
any merge.

- [X] T001 Commit the planning artefacts so the bookworm merge commit can stay pure (checklist CHK016). `git add specs/017-release-line-reconciliation/ CLAUDE.md` and make one signed commit `docs(017): spec, clarify, plan, contracts and checklists for release-line reconciliation`. Confirm `git status --short` is empty afterwards.
- [X] T002 Re-measure the snapshot by quickstart §1 and write `specs/017-release-line-reconciliation/evidence/remeasure-start.md`. It records:
  - the ref table of research R1;
  - the `HEAD..origin/debian/bookworm` (77) and `HEAD..origin/main` (11) counts;
  - `git merge-tree --write-tree HEAD origin/debian/bookworm` (11 conflicting files, no modify/delete);
  - the three-way stray list, diffed against research R17's 42 paths (the 10 kept additions must not be in it);
  - the stray sweep (the 5 refs of research R2);
  - the released sets from `origin/debian/bookworm:debian/changelog` and from PyPI's JSON API (research R9).

  If anything differs from the snapshot, stop ⏸ and amend research before continuing (FR-004).
- [X] T003 [P] Record the release-safety baseline in `specs/017-release-line-reconciliation/evidence/release-safety-start.txt`: `git tag -l --format='%(refname) %(objectname)'` for this repository; `git rev-parse HEAD` and `git status --porcelain` for each of `../cuems-common ../cuems-nodeconf ../cuems-power-bridge ../cuems-engine ../cuems-editor ../cuems-frontend ../libmtcmaster`; and `git log -1 --format=%H -- specs/016-coordinated-minor-bump` plus `find specs/016-coordinated-minor-bump -type f -exec sha256sum {} + | sort` (checklist CHK022–CHK024).
- [X] T004 [P] Create the arm-A worktree `git worktree add $S/wt-a 5e4c637`. Run the suite once (quickstart §2) into `specs/017-release-line-reconciliation/evidence/suite-A-1.txt`. Expected: about 3770 passed, possibly the known `test_descriptor_laziness…[project_mappings]` flake.
- [X] T005 [P] Take arm A's performance baselines (quickstart §6) into `specs/017-release-line-reconciliation/evidence/perf.md`: show-document load, the `script` descriptor warm call via `python -m tests.support.perf_descriptor`, and suite ms/test. Record the interpreter build, governor and `scaling_cur_freq` beside every figure.
- [X] T006 [P] Record arm A's quality figures in `specs/017-release-line-reconciliation/evidence/quality-A.txt`: `ruff check src/ tests/` (expected 0), and the mypy **error set** from the hatch `types` environment (`uvx hatch run types:check` or the configured script). Keep the full list, not only the count.

**Checkpoint**: the planning state is committed, the snapshot is confirmed, and arm A is measured.

---

## Phase 2: Foundational — the three merges (blocks every user story)

**Purpose**: M1 (bookworm), M2 (main), M3 (`v0.0.9rc7` ancestry). **M1 contains the plan §5
resolutions and the 42 deletions, and nothing else** (FR-002).

- [X] T007 Start M1 **on a trial branch** (spec FR-002, checklist CHK021): `git -C $R worktree add -b 017-m1-trial $S/wt-m1 017-release-line-reconciliation`. **T007–T013 run inside `$S/wt-m1`.** Then `git merge --no-ff --no-commit origin/debian/bookworm`. **Never** use `-X ours`, `-X theirs` or any `-s` strategy for this merge (checklist CHK003). Write `git diff --name-only --diff-filter=U` into `specs/017-release-line-reconciliation/evidence/merge-bookworm.md`, and compare it with plan §5's 11 files. If they differ, stop ⏸ (checklist CHK019).
- [X] T008 Resolve the source hunks exactly as plan §5 says. In each file the theirs/ours choice is per hunk, never per file:
  - `src/cuemsutils/__init__.py`: ours `__version__ = "0.1.1"` plus theirs' `SPDX-FileContributor` line;
  - SPDX headers in `src/cuemsutils/cues/{ActionCue,CuemsScript,MediaCue,CueList}.py`: theirs' three lines, then ours' imports;
  - `src/cuemsutils/cues/CueList.py` hunk 2 (`get_media`): **theirs**;
  - `src/cuemsutils/cues/MediaCue.py` hunks 2–5: **ours**;
  - `src/cuemsutils/xml/schemas/script.xsd` both hunks: **ours**, dropping theirs' second `Md5Type`.

  Leave the clean-merged files exactly as merged: `Parsers.py`, `XmlBuilder.py`, `FadeCue.py`, `tests/test_fade_cue.py`, `CLAUDE.md`, `debian/cuems-utils.links`, and the `stop_project` enumeration.
- [X] T009 Resolve the packaging hunks exactly as plan §5 says:
  - `debian/control`: hunk 1 theirs (SPDX), hunk 2 ours (`debhelper-compat (= 13)`, `Standards-Version: 4.6.2`), hunk 3 **both** (ours' `Breaks: cuems-common (<< 1.3.1~)` with its comment, then theirs' `Replaces: cuems-engine (<< 0.1.0rc6-2~)`);
  - `debian/rules`: hunk 1 theirs (SPDX); hunk 2 theirs' `rm -f …/CACHEDIR.TAG` directly after `dh_virtualenv` inside `override_dh_virtualenv`, **then** ours' 011 schema/defaults install and `override_dh_installdeb`;
  - `debian/README.Debian`: `git checkout --ours debian/README.Debian`. **Never** a marker-splitting script, because its `======` underline reads as a separator.
- [X] T010 Rebuild `debian/changelog` per FR-030 and data-model §3:
  - order: `0.1.1 UNRELEASED` (HEAD's body, unchanged in M1), then `0.1.0rc17`, `0.1.0rc16+1`, `0.1.0rc16`, `0.1.0rc15`, each **byte-for-byte** from `git show origin/debian/bookworm:debian/changelog`;
  - this **replaces** HEAD's `0.1.0rc15 UNRELEASED` entry. Do not keep its body anywhere session-local: T052 reads it back from `git show 5e4c637:debian/changelog`;
  - then `0.1.0rc14`…`0.1.0rc8` as they are, then HEAD's never-built entries in HEAD's form.

  `dpkg-parsechangelog -l debian/changelog -S Version` must print `0.1.1`. For `CHANGELOG.md`: ours' `0.1.1` section on top, then theirs' `0.1.0rc17`/`0.1.0rc16` sections kept intact (the rest is T055).
- [X] T011 Delete the 42 strays: `git rm` exactly the paths listed in research R17, re-derived three-way (quickstart §4) and diffed against R17 first. The ten kept additions stay. Then confirm `git grep -nE '^(<<<<<<<|>>>>>>>)( |$)' -- .` is empty and `git diff --cached --name-only --diff-filter=U` is empty.
- [X] T012 Commit M1 (signed). Message: `merge: origin/debian/bookworm (0.1.0rc17, 398a9cf) into 017 — §5 resolutions and 42 strays only`. Complete `specs/017-release-line-reconciliation/evidence/merge-bookworm.md` with one row per hunk (file, hunk, side kept, reason, plan §5 row), the 42 deleted paths, and the 10 kept additions (checklist CHK002).
- [X] T013 Run the suite on M1 into `specs/017-release-line-reconciliation/evidence/suite-M1.txt`. The merged-only red set must be exactly research R13's six (A-2a, A-2b, A-2c, A-2d, A-3a, A-4), plus at most the known laziness flake. Anything else: stop ⏸ before any further commit.

  Then present `evidence/merge-bookworm.md` and this run for review ⏸.
  - **Approved:** in `$R`, `git merge --ff-only 017-m1-trial`, then `git worktree remove $S/wt-m1` and `git branch -d 017-m1-trial`. Confirm `git rev-parse HEAD` equals the reviewed M1 sha.
  - **Rejected:** `git worktree remove --force $S/wt-m1` and `git branch -D 017-m1-trial`, a local scratch branch that was never pushed, then redo from T007. The 017 branch is never reset and never fixed forward.

  The evidence files written in the trial worktree are copied into `$R`'s `evidence/` with the next records commit, because the fast-forward brings only what M1 committed.
- [X] T014 M2: `git merge --no-ff -S origin/main`. Confirm `git diff HEAD^1 HEAD --stat` is empty and `git merge-base --is-ancestor v0.1.0rc17 HEAD`. If the diff is not empty, stop ⏸ (checklist CHK018). Record the result in `specs/017-release-line-reconciliation/evidence/merge-bookworm.md`.
- [X] T015 M3: `git merge -S -s ours v0.0.9rc7 -m "merge: v0.0.9rc7 for ancestry only — its content is in v0.0.9rc8 (git diff v0.0.9rc7 v0.0.9rc8 -- src/cuemsutils/cues/CuemsScript.py src/cuemsutils/cues/MediaCue.py is empty)"`. Confirm the tree diff is empty and that `HEAD..origin/debian/bookworm` = `HEAD..origin/main` = 0. Record both in the same evidence file.

**Checkpoint ⏸**: M1–M3 are committed, the red set is the expected six, and both behind-counts are 0.

---

## Phase 3: User Story 1 — A show that ends itself survives the upgrade (P1) 🎯 MVP

**Goal**: a `stop_project` cue with no target constructs, decodes from JSON, saves and loads
CLEAN, including an rc17-written project after reshape and convert. A leftover target is repaired
to `None` on load and refused on save. `pause_project`/`resume_project` are retired with their
handover. The migration tools report T2 refusals, and `python -m` works.

**Independent test**: `tests/unit/test_targetless_actions.py`,
`tests/integration/test_rc17_migration.py`, `tests/contract/test_retired_action_types.py`,
`tests/unit/test_descriptor_repairability_order.py`, and the two tool tests, all green. The
targetless-actions contract, rows 1–14 and 7a–8c, is covered one row to one test.

### Tests for User Story 1 (written first, red on M3) ⚠️

- [X] T016 [P] [US1] Write the fixture-capture tool `specs/017-release-line-reconciliation/tools/capture_rc17_fixture.py` (research R5). It builds, with rc17's own model and `XmlReaderWriter`:
  - a VideoCue with `pixel_width=1920`, `pixel_height=1080`, `file_size=107374182400` and an uppercase md5;
  - an AudioCue;
  - a `stop_project` ActionCue with `action_target=""`;

  and writes `stop_project.xml`. It also writes `stop_control.xml`, where the last cue is `stop` aimed at the audio cue. Run it in `git worktree add $S/wt-bw 398a9cf` (quickstart §3) into `tests/data/rc17/`, then write `tests/data/rc17/PROVENANCE.md` with the commit, interpreter, command, date and both sha256 (FR-022).
- [X] T017 [P] [US1] Write the probe tool `specs/017-release-line-reconciliation/tools/probes.py`. For an arm and a document it runs S-1, S-1′ (reshape → convert → `load_with_report`, the tools through `main()`), S-2, the control, and X-4, and prints one verdict line each. Run it on M3 into `specs/017-release-line-reconciliation/evidence/probes-M3.md`. Expected: S-1, S-1′ and S-2 refused by T2; control CLEAN; X-4 `None` for absent values.
- [X] T018 [US1] Write `tests/unit/test_targetless_actions.py`, one test per row of `contracts/targetless-actions.md`:
  - rows 1–4: construct with absent, `None` or `""`, and `from_json` with `null`;
  - rows 5–6: save writes `<action_target />`, and `load_with_report` is CLEAN;
  - rows 7/7a: a resolving or dangling leftover uuid loads **REPAIRED** with exactly one `RepairRecord` naming `project_action_takes_no_target`, `previous_value=<uuid>`, `substituted_value=None`, and the file reported stale;
  - rows 8/8a/8b: construct ok, then save refused with that rule's message, and `validate()` reports it;
  - rows 9–10: `stop` with `None` refused at construct, save and load with the unchanged `action_target is required`, and never converted to another action type;
  - row 12: an unknown action type is refused by T1.
- [X] T019 [P] [US1] Write `tests/integration/test_rc17_migration.py`. Copy `tests/data/rc17/stop_project.xml` to `tmp_path`, run `cuems-reshape-devices` then `cuems-convert-documents` through their `main()`, then `CuemsScript.load_with_report`: the outcome must be CLEAN, with action type `stop_project` and target `None`. Do the same for `stop_control.xml`, which must also be CLEAN. Mark both `slow` only if they exceed the suite's usual per-test time.
- [X] T020 [P] [US1] Write `tests/contract/test_retired_action_types.py` (FR-029d). A script whose ActionCue has `action_type` `pause_project` or `resume_project` must be refused by **T1** at `save`, at `load` and through `from_json` + `save`, and `describe()`'s `ActionType` list must not contain either value.
- [X] T021 [P] [US1] Write `tests/unit/test_descriptor_repairability_order.py` (FR-023a):
  - (a) `ActionCue.action_target` is UNREPAIRABLE in the descriptor;
  - (b) `descriptor._repairability_map()` is the same whatever order `RULES` is iterated in. Rebuild it with the registry reversed, monkeypatched, clearing `_repairability_cache` before and after.
- [X] T022 [US1] Run T018–T021 on M3 and record each red excerpt in `specs/017-release-line-reconciliation/evidence/red-green.md`, using data-model §5's columns. T021(a) may already be green on M3: record it as `held`, since it becomes meaningful only once the new rule exists.

### Implementation for User Story 1 (one commit: A-1 + A-2d + the Q13 retirement + FR-053)

- [X] T023 [US1] In `src/cuemsutils/cues/ActionCue.py`, add `TARGETLESS_ACTION_TYPES: frozenset[str] = frozenset({"stop_project"})` with research R3's comment. Make `__init__` raise `action_target is required` only when `init_dict.get('action_type')` is **not** in the set (research R4). Leave `set_action_target` unchanged, because `enforce` passes `self`.
- [X] T024 [US1] In `src/cuemsutils/xml/validators.py`:
  - `_action_target_required` passes `None` when `obj` is not `None` and `obj.get("action_type") in TARGETLESS_ACTION_TYPES`, with the message unchanged;
  - `_action_target_resolves` returns early for a type in the set;
  - register a new rule `project_action_takes_no_target` on `[("ActionCue", "action_target")]`, `repairable=True`. It raises `ValueError(f"action_target {value} must be empty: {obj.get('action_type')} acts on the whole project and takes no target; clear it")` when the type is in the set and `value is not None`.

  Import the set inside each function, as the module does for model imports (research R3, R16).
- [X] T025 [US1] In `src/cuemsutils/xml/descriptor.py` `_repairability_map`, replace `mapping[(key, field_name)] = rule.repairable` with `mapping[(key, field_name)] = mapping.get((key, field_name), True) and rule.repairable`, and add a comment citing FR-023a (research R16). Then confirm every descriptor golden under `tests/golden/` is byte-identical (`git diff --stat -- tests/golden` empty).
- [X] T026 [US1] In `src/cuemsutils/xml/schemas/script.xsd`, delete the `pause_project` and `resume_project` `<xs:enumeration>` lines, and point the `ActionType` comment at `specs/planning/project-pause-resume-deferred.md`. In the same edit, check that the merged `stop_project` comment makes no deprecated-parser claim (FR-051, xsd half). **Every `script.xsd` edit of 017 lands in this commit** (checklist CHK037).
- [X] T027 [US1] In `tests/contract/test_schema_scope.py`, update `CURRENT_SCHEMA_HASHES['script.xsd']` to the new sha256 (A-2d), with a comment naming 017, A-1 and the Q13 retirement, and stating that there is no version step.
- [X] T028 [US1] Update every test that pins the exact rule set for one new rule: check `tests/unit/test_t2_registry.py` and any closed list read by `test_config_parity` or the coherence test (`git grep -n "action_target_resolves" tests/` and `git grep -n "SEMANTIC_RULES" tests/`). Do not loosen any assertion; add the new name.
- [X] T029 [US1] Write `specs/planning/project-pause-resume-deferred.md` (FR-053, SC-015), and add its pointer row to `specs/017-release-line-reconciliation/evidence/test-retirements.md` (FR-029b: the one index of retirements). The document has six parts:
  1. **retired text, verbatim:** the two enumeration lines and their comment from `2318dee:src/cuemsutils/xml/schemas/script.xsd`, the `RETAINED` entry, 008's `enum-audit.md` evidence, rc17's `CHANGELOG.md` line, and Q13's measurements;
  2. **prior art:** `../cuems-engine` `origin/dev` `9852d79` `src/cuems/ActionCue.py:95-97`, plus `ActionHandler.py:29` and bookworm `tests/test_action_cue.py:1519`;
  3. **reinstatement after `0.1.1`:** the additive enum value with a `script` 2 → 3 step under `specs/agreements/schema-evolution-convention.md`, the one-line `TARGETLESS_ACTION_TYPES` addition, T2, guard, `from_json`, descriptor, enum audit, and the tests, modelled on A-1 with code excerpts;
  4. **engine ↔ `libmtcmaster`:** `../libmtcmaster` `6afe645` `interface.h` `MTCSender_pause`/`MTCSender_play`, as wrapped by `../cuems-engine` `src/cuemsengine/core/libmtc.py:29-39`, with a sketch of the handler. Cite the engine's **release-line** commit for its `stop_project` handler (`git -C ../cuems-engine log origin/debian/bookworm -S stop_project`);
  5. **sibling halves:** frontend authoring, editor save, power-bridge reaction;
  6. **the `stop_cue` naming option:** the documents it converts, its version step, and the sites it touches (`NodeEngine.py:366`, `ActionHandler.py:34,759`, the frontend's action authoring).

  Cite every cross-repository claim by path and commit, as read from the checkouts.
- [X] T030 [US1] Run T018–T021 plus `tests/contract/` on the working tree. All must be green except the A-2a–c tests still owned by US2 (T036). Record the green excerpts in `specs/017-release-line-reconciliation/evidence/red-green.md`. Commit T023–T029 as **one** signed commit `feat(actions): stop_project takes no target; retire pause_project/resume_project (017 A-1, A-2d, Q13)`, with `tests/data/rc17/` and the two `tools/` scripts. ⏸
- [ ] T031 [P] [US1] Write `tests/integration/test_reshape_devices_main.py` (FR-029a): `subprocess.run([sys.executable, "-m", "cuemsutils.xml.reshape_devices", <copy of a corpus document>])` produces the same verdict output and exit status as calling `reshape_devices.main([...])`. Record it red on the A-1 commit.
- [ ] T032 [P] [US1] Write `tests/integration/test_migration_tool_report.py` (FR-029c, `contracts/migration-tool-report.md` tests 1–3):
  - the rc17 control twin with its `stop` cue's `action_target` emptied, run through reshape then convert, is **written**, emits a WARNING matching `would be refused on load: [T2] action_target_required`, and is listed in the new summary bucket, with the exit status equal to the same run without the check;
  - the migrated rc17 fixture gets no entry;
  - a clean corpus document gets no entry and no WARNING.

  Before writing it, read the tools' current summary bucket names in `src/cuemsutils/xml/convert_documents.py` and `src/cuemsutils/xml/reshape_devices.py`, and name the new bucket in the same vocabulary. Record it red.
- [ ] T033 [US1] Add `if __name__ == "__main__": sys.exit(main())` to `src/cuemsutils/xml/reshape_devices.py`, matching `convert_documents.py`'s form. T031 goes green. Commit `fix(xml): python -m cuemsutils.xml.reshape_devices runs the tool (017 S-4)`.
- [ ] T034 [US1] In `src/cuemsutils/xml/convert_documents.py` and `src/cuemsutils/xml/reshape_devices.py`, after each **written** document, validate it on a throwaway copy with the loader's T1+T2 path (research R6). On refusal, log the WARNING `"<path>: would be refused on load: [<tier>] <rule> at <cue>/<field>: <message>"` and add the document to the new bucket, also under `--check`. Do not change the bytes written or the exit status. T032 goes green. Commit `feat(xml): migration tools report documents the loader would refuse (017 S-3)`.
- [ ] T035 [US1] Measure the tools' per-document cost before and after T034, interleaved A/B over `tests/data/corpus/`, and record it in `specs/017-release-line-reconciliation/evidence/perf.md` without a budget (FR-029c).

**Checkpoint**: US1 is green, which discharges X-1 (FR-041).

---

## Phase 4: User Story 2 — Nothing the release line shipped is lost (P1)

**Goal**: the six merged-only reds are fixed, every absorbed test is ported to the public API, X-4
is pinned, `MediaCue` is snapshotted, and the 14-row inventory is proven.

**Independent test**: the suite on the US2 head has no failure `5e4c637` lacks, and
`evidence/inventory.md` has 14 rows, each with a passing proof.

- [X] T036 [US2] A-2a–c, in `tests/contract/test_action_type.py`:
  - rename the two tests to `…_exactly_eleven_values` / `…_those_eleven_values`, enumerate the 11 values by name (data-model §1), and keep asserting that `fade_in`, `fade_out`, `pause_project` and `resume_project` are absent;
  - in `tests/contract/test_enum_audit.py` `RETAINED[("script", "ActionType")]`, add `stop_project` and remove the two retired values;
  - write `specs/017-release-line-reconciliation/evidence/enum-audit-017.md` with the evidence for the three changes (`cuems-engine` rc6-5 implements `stop_project`, the frontend's `dev` authors it, Q13's measurements).

  Record red (T013) and green. Commit `test(contract): ActionType has eleven values (017 A-2a–c)`.
- [X] T037 [P] [US2] A-3: port `tests/test_action_cue_stop_project.py` (rc17, 7 tests) to `tests/unit/test_stop_project_cue.py`, through `CuemsScript.save`/`load_with_report`/`from_json` only. Re-express A-3a per A-1: a `stop_project` cue built with `""` has target `None`. Drop any assertion already covered by T018 rather than duplicate it, and list each dropped assertion with the test that covers it. `git rm tests/test_action_cue_stop_project.py`.
- [X] T038 [P] [US2] A-3: port `tests/test_media_guards.py` (rc16, 17 tests, no deprecated imports) to `tests/unit/test_media_guards.py`, building the cue lists through the public API (`CuemsScript.from_json`/`load`). `git rm tests/test_media_guards.py`.
- [X] T039 [US2] Run T037–T038, then commit `test: port rc17 stop_project and rc16 media-guard tests to the public API (017 A-3)`. Add rows for both deleted root copies to `specs/017-release-line-reconciliation/evidence/test-retirements.md`, with their replacements.
- [ ] T040 [US2] A-4: port `tests/unit/test_media_pixel_dimensions.py` (rc15, 22 tests) to the public API, next to the existing media-block tests in `tests/unit/` (keep the filename unless it collides). **Retire** `TestFileMd5::test_stored_lowercase`: an uppercase md5 is refused by 014's strict rule, and every released producer lowercases first. Any **other** ported rc15 assertion that is red is either an adaptation, red → green in its own commit, or, if it contradicts a settled refactor decision, a retirement added to `test-retirements.md` and to spec FR-003a's list. Stop ⏸ before retiring anything FR-003a does not already name. Add its row to `specs/017-release-line-reconciliation/evidence/test-retirements.md` (data-model §6). Commit `test: port rc15 media-value tests; retire the md5 case-folding assertion (017 A-4)`.
- [ ] T041 [P] [US2] FR-012: write `tests/unit/test_media_public_path.py`:
  - an all-digit 32-character `file_md5` survives `save` → `load` as `str`;
  - the `<Media>` children are written in `script.xsd`'s declared sequence order, read from the schema, not hard-coded.

  Run it on **M3** (`git worktree add $S/wt-m3 <M3 sha>`, plan Phase 4; analyze I4). If green, record `held` in `evidence/red-green.md` and commit it with T042. If red, port the missing behaviour into the public path (`src/cuemsutils/xml/mapper.py` or the adapter table) as its own commit `fix(xml): … on the public path (017 FR-012)`.
- [ ] T042 [P] [US2] A-6: write `tests/unit/test_media_absent_values.py` (FR-029, X-4):
  - a version-2 `Media` loaded **without** the four elements gives `None` from `.get(k)` and from the attribute, the key is not in the mapping, and `to_wire()` omits it;
  - loaded **with** them, the values are `int`, `int`, `int`, `str` (`file_size == 107374182400`);
  - `Unset` is never returned.

  Record it as `held` (it is a pin) and commit `test: pin absent stored-media values as None (017 A-6, X-4)`.
- [ ] T043 [US2] FR-029b: `git grep -nE "XmlReaderWriter|xml\.Parsers|xml\.XmlBuilder|from cuemsutils\.xml import (Parsers|XmlBuilder)" -- tests/`. Every hit must be in a module marked `expects_deprecation` (frozen-shim contract). Record the output in `specs/017-release-line-reconciliation/evidence/deprecated-imports.txt` (SC-006).
- [ ] T044 [US2] FR-026a (last adaptation):
  - add `"MediaCue": ("cuemsutils.cues.MediaCue", "MediaCue")` to `PUBLIC_CLASSES` in `tests/contract/test_public_api_surface.py` and record `test_public_api_matches_the_snapshot` red;
  - insert the `MediaCue` block by hand, in sorted position, into `tests/golden/api/public_api.json`, and update that file's line in `tests/golden/MANIFEST.sha256`;
  - add a re-hash paragraph to `tests/contract/test_golden_immutability.py`'s docstring, beside the 009/011/axis-D/foreign-controller paragraphs;
  - confirm `git diff --numstat -- tests/golden/api/public_api.json` shows 0 deleted lines, and save that output to `specs/017-release-line-reconciliation/evidence/public-api-rehash.txt` (SC-016).

  Commit `test(contract): snapshot MediaCue's public surface (017 FR-026a, Q8)`.
- [ ] T045 [US2] Write `specs/017-release-line-reconciliation/evidence/inventory.md`: 14 rows in data-model §4's columns, one per spec FR-003 inventory item, each naming its proof (test node id, packaging test, or the history check with its command and output).

**Checkpoint**: US2 is green, and the merged-only red set is empty.

---

## Phase 5: User Story 3 — The package installs and upgrades correctly (P2)

**Goal**: `Replaces:` and the `CACHEDIR.TAG` strip are pinned, the `.deb` is built and checked, and
the relations read 126/126.

**Independent test**: the A-5 packaging tests fail on `5e4c637` and pass on the head;
`evidence/verdicts-017.txt` reads 126/126; `evidence/deb-checks.md` holds all four checks.

- [ ] T046 [P] [US3] Write `tests/packaging/test_release_line_packaging.py` (FR-028, FR-034):
  - the `Package: cuems-utils` stanza of `debian/control` declares `Replaces: cuems-engine (<< 0.1.0rc6-2~)` and still declares `Breaks: cuems-common (<< 1.3.1~)`;
  - `debian/rules`' `override_dh_virtualenv` removes `CACHEDIR.TAG` **after** the `dh_virtualenv` line;
  - `debian/rules` carries all four of: the `--python /usr/bin/python3` pin, the strip, 011's schema/defaults install, and `override_dh_installdeb`.

  Run it against `$S/wt-a`, where it must be red, and against the head, where it must be green, and record both.
- [ ] T047 [US3] Extend `tests/packaging/test_built_package.py` (the chroot test, skipped without `CUEMS_CHROOT_TAR`) to assert the built `.deb` has no `usr/lib/cuems/CACHEDIR.TAG`, and to report whether `usr/lib/cuems/bin/cffi-gen-src` is present (FR-028, FR-035).
- [ ] T048 [US3] Reword the comment block above the relations in `debian/control`. Each relation states its own reason. Row 26 states why there is no `Breaks:` (Q6, `contracts/relation-row-26.md`), and the "Replaces is deliberately absent" sentence goes. Commit T046–T048 as `fix(debian): pin Replaces and the CACHEDIR.TAG strip (017 A-5)`.
- [ ] T049 [P] [US3] Write `specs/017-release-line-reconciliation/tools/verdicts-017.sh` per `contracts/relation-row-26.md`: run 016's `verdicts.sh` unchanged, read row 26 from `<parent>/cuems-utils/debian/control`, and run the five `dpkg --compare-versions` verdicts.

  Build the parent from worktrees, never from the live checkouts (analyze U2):
  - for each of `cuems-common cuems-nodeconf cuems-power-bridge cuems-engine cuems-editor cuems-frontend`, run `git -C ../<repo> worktree add --detach $S/rel/<repo> feat/xml-refactor`;
  - add `$S/rel/cuems-utils`, a worktree at the 017 head.

  Run `verdicts-017.sh $S/rel` into `specs/017-release-line-reconciliation/evidence/verdicts-017.txt`, with each worktree's commit written above the verdicts. Expected `126/126` (SC-007). Afterwards, `git -C ../<repo> worktree remove $S/rel/<repo>`; that touches only git's worktree list, never the sibling's checkout or branch.
- [ ] T050 [US3] Build `0.1.1` with 016's tool, using its real interface (FR-035, quickstart §5):
  - `git worktree add --detach $S/wt-build <017 head>`, because the tool refuses a dirty checkout;
  - then `UTILS=$S/wt-build OUT=$R/specs/017-release-line-reconciliation/evidence/bookworm-build.txt $R/specs/016-coordinated-minor-bump/tools/bookworm-build.sh $S/wt-build`.

  The tool refuses an existing `OUT`, so 016's evidence cannot be touched. If the build cannot run (no `mmdebstrap`, no mirror), record SC-007's build half as **not met**, with the reason. Record in `specs/017-release-line-reconciliation/evidence/deb-checks.md` (quickstart §5): `Version: 0.1.1`, `home = /usr/bin`, `bin/python -> ../../../bin/python3`, no `CACHEDIR.TAG`, and whether `cffi-gen-src` is present. Run T047 with `CUEMS_CHROOT_TAR` set and record the result. ⏸

**Checkpoint**: packaging is pinned, built and related.

---

## Phase 6: User Story 4 — The release history is complete, and stays complete (P2)

**Goal**: both changelogs are complete from `0.1.0rc5`, and a permanent test guards them.

**Independent test**: `tests/packaging/test_changelog_completeness.py` is red on `5e4c637` and green
on the head.

- [ ] T051 [US4] Write `tests/packaging/test_changelog_completeness.py` per `contracts/changelog-completeness.md`:
  - carry the data block (`RELEASED_DEBIAN`, `RELEASED_PYPI`, `NEVER_PUBLISHED`, `OLDEST_RELEASED_DEBIAN`);
  - implement checks 1–6, with check 4 per spec M2;
  - make checks 2 (ref half) and 3 skip with a reason when `origin/debian/bookworm` or the `debian/*` tags are absent, using `tests/support/sibling_tags.py`'s pattern;
  - compare byte-for-byte on whole entry blocks, from the header line through the trailer line.

  Run it against `$S/wt-a`, expecting the red set listed in the contract, and record that in `evidence/red-green.md`.
- [ ] T052 [US4] Update the `0.1.1` entry's body in `debian/changelog` (FR-031):
  - replace the "NOT YET RECONCILED" bullet with `Reconciled with debian/bookworm at 398a9cf (0.1.0rc17): absorbs rc15, rc16, rc16+1, rc17`, followed by one line for each of inventory items 1–5;
  - add one line for A-1's targetless rule and the `project_action_takes_no_target` repair, and one for the Q13 retirement of `pause_project`/`resume_project`;
  - fold in the body of HEAD's retrospective entry, taken from `git show 5e4c637:debian/changelog` (the `0.1.0rc15 UNRELEASED` block, header and trailer excluded), so the step does not depend on a session's scratchpad (analyze U1).

  Leave the trailer as it is. `dpkg-parsechangelog` must still print `0.1.1`.
- [ ] T053 [US4] Rewrite `CHANGELOG.md` (FR-032, M1):
  - fold the two mid-file `## Unreleased — …` sections into `## 0.1.1 — Unreleased`, and replace its "Not yet reconciled" text with the reconciled line, items 1–5, A-1 and the Q13 retirement;
  - keep rc17's and rc16's sections; mark rc17 `(Debian only; not published to PyPI)`, and add `<!-- debian: 0.1.0rc16+1 (c01ca36) -->` plus one line under rc16;
  - add sections for `0.1.0rc15`, `0.1.0rc14`, `0.1.0rc12` (Debian only), `0.1.0rc10` and `0.1.0rc9` (Debian only), written from their `debian/changelog` text and dated by their trailers;
  - add one line saying `0.1.0rc13` was never built, and mark the existing rc5 and rc6 sections `(never published: no Debian build, not on PyPI)`;
  - end with `## Earlier releases`, pointing at the git tags and PyPI.

  Keep rc17's "stay in the enum" line verbatim (checklist CHK032).
- [ ] T054 [US4] Run T051 on the head; it must be green. Record red→green. Commit T051–T053 as `docs(changelog): complete from 0.1.0rc5, guarded by a permanent test (017 D3)`.

**Checkpoint**: the changelog test is permanent and green.

---

## Phase 7: User Story 5 — Siblings and the maintainers know what changed (P3)

**Goal**: the docs describe `0.1.1`, the five upstream reports exist, and the coordinated-bump
document points at 017. The tag message is T081.

**Independent test**: the files below exist with the content FR-042 and FR-050–FR-052 require.

- [ ] T055 [P] [US5] Rewrite `CLAUDE.md` (FR-050):
  - the merged `stop_project` field note becomes: the value is in version-2 `script.xsd`; A-1's targetless rule and the repair of a leftover target; skew rule "every box on ≥ 0.1.1"; the rollback hazard stays; and `pause_project`/`resume_project` are retired, pointing at the handover document;
  - the "two packaging lines" paragraph states that `debian/bookworm` ⊂ `feat/xml-refactor` at the M1 sha, and that the release line may keep releasing (Q10);
  - add a Recent Changes entry for 017.
- [ ] T056 [P] [US5] Rewrite the merged `ActionCue` class docstring in `src/cuemsutils/cues/ActionCue.py` for the public path (FR-051): `stop_project` takes no target (`None`, written `<action_target />`), a leftover target is repaired on load and refused on save, and `pause_project`/`resume_project` are not values. Remove the "parses to `None` because the parsers bypass the setter" sentence. **No code change in this task.**
- [ ] T057 [P] [US5] In `specs/planning/coordinated-release-version-bump.md`, "still owed" item 1: mark `cuems-utils` reconciled at the M1 sha and point at `specs/017-release-line-reconciliation/` (FR-052).
- [ ] T058 [US5] Commit T055–T057 as `docs: describe 0.1.1 after the release-line merge (017)`.
- [ ] T059 [P] [US5] Write `specs/017-release-line-reconciliation/upstream-reports/cuems-editor.md`: `CueList.get_media` now raises a named `ValueError` for an invalid media block and skips `None` (869fej07m); the editor's half of `stop_project` (send `null`, or no target); and a leftover target is refused on save and repaired on load.
- [ ] T060 [P] [US5] Write `specs/017-release-line-reconciliation/upstream-reports/cuems-frontend.md`: the descriptor publishes **11** action types (`stop_project` in, `pause_project`/`resume_project` out), a `null` target is accepted for `stop_project`, and the handover document is linked.
- [ ] T061 [P] [US5] Write `specs/017-release-line-reconciliation/upstream-reports/cuems-engine.md`: its reconciliation must drop `pause_project`/`resume_project` from `ActionHandler.py:29` and from bookworm `tests/test_action_cue.py:1519`'s parametrization. Point at the handover document, and record for reference that `>= 0.1.0rc17` cannot be resolved from PyPI (its pre-spec already moves to `>= 0.1.1`). X-4 is answered `None`.
- [ ] T062 [P] [US5] Write `specs/017-release-line-reconciliation/upstream-reports/cuems-power-bridge.md`: its half of the `stop_project` wire contract must show at its re-cut tag, and X-3 (nobody ships `CACHEDIR.TAG`) is this package's half, pinned.
- [ ] T063 [P] [US5] Write `specs/017-release-line-reconciliation/upstream-reports/release-line-hygiene.md` for the release-line maintainer (FR-042, §14.6):
  - stop tracking debhelper outputs and the 2025 experiment files on `debian/bookworm` (list from research R17);
  - rc17 is not on PyPI;
  - new tests go under `tests/{unit,integration,contract,packaging}/`, never the root;
  - CI dispatch with `siblings_ref`;
  - the line may keep cutting `0.1.0rcN` until `0.1.1` is published (Q10), and each release is merged into `feat/xml-refactor` the same way.
- [ ] T064 [US5] Commit T059–T063 as `docs(017): upstream reports for the release-line reconciliation`.

**Checkpoint**: everyone who depends on this library has a written note.

---

## Phase 8: Verification (cross-cutting, before the cleanup)

- [ ] T065 Run the suite three times on 3.11, interleaved A/B/A/B/A/B (`$S/wt-a` against a fresh worktree `$S/wt-b` at the head), into `specs/017-release-line-reconciliation/evidence/suite-{A,B}-{1,2,3}.txt`. Run it once on 3.12 and once on 3.13 on B. Write `specs/017-release-line-reconciliation/evidence/suite-verdict.md`: B's failure set ⊆ A's (the laziness flake identified if present), and the 3.13 snapshot failure noted as pre-existing (SC-003).
- [ ] T066 Measure the performance bands (quickstart §6, at least 16 interleaved samples across three windows) and append them to `specs/017-release-line-reconciliation/evidence/perf.md`: the show-document load against its band of 16.465–17.750 ms, suite ms/test ≤ 115% of A, and the descriptor warm call ≤ 115% of A. Anything exceeded is recorded as exceeded (SC-009).
- [ ] T067 Run ruff (expect 0) and compare the mypy error set with T006's, writing `specs/017-release-line-reconciliation/evidence/quality-B.txt`. The set must not grow (SC-QUALITY-001).
- [ ] T068 Commit T065–T067's records as `docs(017): suite, performance and quality records`.

---

## Phase 9: Final re-fetch and re-merge (before the cleanup)

- [ ] T069 `git fetch --all --tags --prune`, then re-run T002's measurements into `specs/017-release-line-reconciliation/evidence/remeasure-handoff.md`, including PyPI's JSON API. **If either line moved** (FR-004, Q10), merge the delta by T007–T015's method and, for each new release: add an inventory row, add its `debian/changelog` entry verbatim, update the T051 data block, and add a public-API test. Then re-run T065. If PyPI gained rc17, remove its "Debian only" marking and update `RELEASED_PYPI` in the same commit. ⏸

---

## Phase 10: User Story 6 — A clean first stable release (P3)

**Goal**: no scratch, no stale lists, no personal settings, public-API docs, and a test tree marked
by directory. Each commit is a pure move, delete or rewire, and the pass set is unchanged.

**Independent test**: quickstart §7 (stale grep empty, no root `tests/test_*.py`,
`tests/unit tests/contract` green offline), plus `tests/contract/test_test_layout.py` green and the
pass-set diff showing only recorded retirements.

- [ ] T070 [US6] Record the pass set before the cleanup into `$S/passset-before.txt` (quickstart §7), and start `specs/017-release-line-reconciliation/evidence/cleanup-pass-set.md`.
- [ ] T071 [US6] C1 (FR-061):
  - `git rm -r dev/`, and remove `dev/local` from `.gitignore`;
  - triage `ToDo.md` item by item: each item still true becomes a short document under `specs/planning/`, and each done or superseded item is listed in the commit message with its reason; then `git rm ToDo.md`;
  - `git rm --cached .claude/settings.local.json` and add `.claude/settings.local.json` to `.gitignore`.

  Commit `chore: remove dev/ and ToDo.md, untrack local settings (017 §14.1)`, then re-record the pass set and diff it.
- [ ] T072 [P] [US6] C2 (FR-062): rewrite `README.md` and `docs/index.md` to the public API (`CuemsScript.load/save/validate/from_json/to_wire`, `ConfigManager`, `cuemsutils.errors`), and replace `docs/xml.md`'s `Parsers`/`XmlBuilder`/`XmlReaderWriter` mkdocstrings pages with the public surface. Reword `README.md`'s `gradient_osc_port … NodeType` to the current type name, and adjust `mkdocs.yml` if its nav names the removed pages. Then build the site, which is **required, not optional**: `PYTHONPATH=src uvx --with mkdocs-material --with mkdocstrings-python mkdocs build --strict -d $S/site`. It must pass, and `grep -rl "XmlReaderWriter\|XmlBuilder\|cuemsutils.xml.Parsers" $S/site` must print nothing. Record both in `evidence/cleanup-checks.txt` (SC-012, analyze LOW). Commit `docs: README and site describe the public API only (017 §14.2)`.
- [ ] T073 [US6] C3, test layout (FR-063, `contracts/test-layout.md`):
  - write `tests/contract/test_test_layout.py` and record it red;
  - `git mv` the 17 root modules per the contract's table, re-checking each one's kind with the signal grep;
  - `git rm tests/testdev_nng_talk.py` and record it in `evidence/test-retirements.md`;
  - add the `pytest_collection_modifyitems` hook to `tests/conftest.py`;
  - register `unit`, `integration`, `contract` and `packaging` in `pyproject.toml`'s `markers`, add `addopts = "--strict-markers"`, and change the `filterwarnings` entry to `tests.unit.test_name_coercion`.

  T073's test goes green. Commit `test: every test lives in, and is marked by, its kind's directory (017 §14.3)`, then re-record and diff the pass set.
- [ ] T074 [P] [US6] C4 (FR-073, gh-pages half): in `.github/workflows/gh-pages.yml`, guard the deploy step with `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`. Optionally keep a `mkdocs build --strict` step for pull requests and dispatches (`contracts/ci-workflow.md`). Commit `ci: deploy the site only from pushes to main (017 §14.4)`.
- [ ] T075 [US6] Run quickstart §7's checks into `specs/017-release-line-reconciliation/evidence/cleanup-checks.txt`: the stale-path grep, no root `tests/test_*.py`, and `tests/unit tests/contract` run without network. Finish `evidence/cleanup-pass-set.md`: the before→after diff holds only the recorded retirements (SC-012).

**Checkpoint**: the tree is clean, and the pass set is unchanged except for the recorded retirements.

---

## Phase 11: User Story 7 — A pre-publication gate the maintainer can run in the cloud (P3)

**Goal**: `tests.yml` is restructured with `siblings_ref` and statically checked, and the gate's
evidence template exists. The green run itself happens after hand-off (clarify).

**Independent test**: `tests/contract/test_ci_workflow.py` is green; `evidence/ci-gate.md` has every
field of `contracts/ci-workflow.md`.

- [ ] T076 [US7] Add `"pyyaml"` to `[tool.hatch.envs.test] dependencies` in `pyproject.toml` (test-only; plan Complexity Tracking), and confirm `import yaml` works in `uvx hatch run test.py3.11:run -- --co -q tests/contract`.
- [ ] T077 [US7] Write `tests/contract/test_ci_workflow.py` with `contracts/ci-workflow.md`'s six static assertions. Look the trigger map up under both `"on"` and `True`. Record it red against the current single-job `tests.yml`.
- [ ] T078 [US7] Restructure `.github/workflows/tests.yml` per `contracts/ci-workflow.md`, keeping the file name:
  - triggers, including `feat/xml-refactor` and the `siblings_ref` input;
  - the jobs `lint`, `unit`, `integration` (with the six sibling checkouts at `siblings_ref`, `fetch-depth: 0`, tags), `packaging` (`container: debian:bookworm`), `coverage` (Codecov only on a push to `main`), `matrix-info` (`continue-on-error`) and `gate-summary` (`if: always()`, failing iff a blocking job did not succeed, writing the summary fields).

  T077 goes green.
- [ ] T079 [P] [US7] Write `specs/017-release-line-reconciliation/evidence/ci-gate.md` as a **template**: data-model §8's fields with blanks, plus instructions for filling it from the first dispatch on the post-merge `feat/xml-refactor` head (FR-075).
- [ ] T080 [US7] Update `CONTRIBUTORS.md`. Its testing section says where new tests go and that markers come from the directory (FR-064). Its release section carries the pre-publication line: a green dispatched `tests.yml` run on the post-merge `feat/xml-refactor` head with every sibling at its reconciled re-cut tag, before the GitHub release and the `.deb` upload (FR-076). Commit T076–T080 as `ci: parallel gate jobs with siblings_ref; gate deploys and Codecov to main (017 §14.5)`.

**Checkpoint**: the gate is checked statically, and its run is listed as owed at hand-off.

---

## Phase 12: Hand-off and the last task

- [ ] T081 Close checklist CHK020: re-fetch once more. If the release line moved **after** the cleanup, merge the delta by T007–T015's method, `git mv` any new root `tests/test_*.py` into its kind's directory in a follow-up commit, and re-run T073's layout test and T065 (one run per arm suffices if nothing else changed). Record the outcome in `specs/017-release-line-reconciliation/evidence/remeasure-handoff.md`.
- [ ] T082 Release-safety verification (checklist CHK022–CHK025), written to `specs/017-release-line-reconciliation/evidence/release-safety-end.txt`:
  - the tag list is identical to T003's;
  - every sibling's HEAD and `git status --porcelain` are identical to T003's;
  - the 016 file hash list is identical to T003's;
  - `git log --format='%H %G?' <T001's commit>^..HEAD` shows `G` or `U` for every commit. Both mean a good signature; `U` only means the key's trust is unknown locally. `N`, `B`, `E`, `X`, `Y` or `R` fails;
  - `git status -sb` shows no upstream push, and `git log origin/017-release-line-reconciliation` does not exist;
  - **FR-036, things that do not move** (analyze U3):
    - `__version__ == "0.1.1"`;
    - `REMOVAL_RELEASE` is still `"v0.1.2"` (`git grep -n 'REMOVAL_RELEASE =' -- src`);
    - this repository's own consumer-facing bounds are unchanged: `git diff <T001's commit> HEAD -- pyproject.toml` touches only the `test` environment's dependencies (`pyyaml`) and the pytest marker block;
    - `tests/packaging/test_no_version_bump.py` passes, with its output recorded.
- [ ] T083 Rewrite `../.xml-refactor-tag-messages/cuems-utils.txt` (FR-044, checklist CHK027). Read it first.
  - **`Tag:`** is an explicit **maintainer placeholder**, the one field filled at re-cut (analyze I2, option b; SC-010): `Tag: <MAINTAINER: fill at re-cut — the feat/xml-refactor commit that contains 017-release-line-reconciliation at <017 head sha>, after siblings' landings and upstream requests are coordinated>`;
  - "NOT YET RECONCILED" becomes `Reconciled with origin/debian/bookworm at 398a9cf (0.1.0rc17)`;
  - "Carries" gains items 1–5, A-1 with the target repair, and the Q13 retirement;
  - "Pairs with" stays unchanged unless a sibling re-cut first;
  - add the pre-publication checklist line (FR-076).

  Touch no other file there.
- [ ] T084 Write `specs/017-release-line-reconciliation/evidence/handoff.md`: what 017 delivers, with links to every evidence file, and the maintainer's acts in order (plan §Hand-off):
  1. `--no-ff` merge into `feat/xml-refactor`;
  2. push;
  3. dispatch `tests.yml` with `siblings_ref` and fill `evidence/ci-gate.md`;
  4. coordinate the commit with the siblings' landings and any upstream requests;
  5. fill the tag message's `Tag:` placeholder, the only edit, and re-cut the candidate tag;
  6. rule 4 for the other repositories, and publication only after the gate. Commit T081–T084's records as `docs(017): hand-off`. ⏸
- [ ] T085 **Last task: delete the work order** (FR-060, SC-014):
  - check every row of spec §"Traceability to the work order" against the files it names, and add any section found missing to this directory before going on;
  - `git grep -n release-line-reconciliation-0.1.1 -- . ':!specs/017-*'` must print nothing; re-point any hit first (cuems-engine's same-named file is another repository and is not a hit);
  - `git rm specs/planning/release-line-reconciliation-0.1.1.md`;
  - commit `docs(planning): delete the 017 work order — absorbed into specs/017-release-line-reconciliation/ (last at <sha of its last commit>)`, with the grep output in the message.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1** (T001–T006): T001 first. T002 next. T003–T006 can run in parallel after T002.
- **Phase 2** (T007–T015): strictly in order. **It blocks every user story.**
- **US1** (Phase 3) after Phase 2. Its commit T030 is the base for US2's ports and for T041.
- **US2** (Phase 4) after T030. T044 (FR-026a) must come after T036–T042, because those settle `MediaCue`'s surface.
- **US3** (Phase 5) and **US4** (Phase 6) after Phase 2. They are independent of US1 and US2 and of each other, apart from serialising commits on one branch. T052 and T053 name A-1 and Q13, so write them after T030.
- **US5** (Phase 7) after US1–US4, since it describes their results.
- **Phase 8** (verify) after US1–US5. **Phase 9** (re-fetch) after Phase 8.
- **US6** (Phase 10) **only after Phase 9**, then **US7** (Phase 11). T074 and T078 both edit `.github/workflows/`, but different files.
- **Phase 12** last. T085 is the final task of the feature.

### User-story dependencies

- **US1 → US2**: the ports re-express A-3a per A-1, and the snapshot follows A-1.
- **US3, US4**: independent of US1 and US2. Only their changelog text mentions A-1 and Q13.
- **US5**: depends on US1–US4.
- **US6, US7**: depend on Phase 9. US7's static test reads the files US6 leaves.

### Within each story

The tests are written and recorded red first, then the implementation, then green, then the
commit. One commit per adaptation (plan §Phases), except that A-1, A-2d, Q13 and FR-053 are
**one** commit (T030).

---

## Parallel opportunities

- Phase 1: T003, T004, T005, T006.
- US1 tests: T016, T017, T019, T020, T021 (T018 is one large file; write it alone). Later, T031 and T032.
- US2: T037 and T038; T041 and T042.
- US3: T046 and T049.
- US5: T055, T056, T057; then T059–T063 (five report files).
- US6: T072 and T074, once T071 is committed.

### Parallel example: User Story 1 tests

```text
T016  tools/capture_rc17_fixture.py → tests/data/rc17/
T017  tools/probes.py → evidence/probes-M3.md
T019  tests/integration/test_rc17_migration.py
T020  tests/contract/test_retired_action_types.py
T021  tests/unit/test_descriptor_repairability_order.py
```

---

## Implementation strategy

### MVP: Phase 1 + Phase 2 + US1

After T030 the reconciliation is already **safe for the field**:
- the release line is an ancestor;
- an rc17 project with a `stop_project` cue loads on `0.1.1`;
- the retired values are recorded.

Stop and validate at T030's ⏸.

### Incremental delivery

1. US2: nothing shipped is lost (the six reds are fixed, the ports done, the inventory proven).
2. US3 and US4: packaging, then changelogs (independent of each other).
3. US5: docs and reports.
4. Verify and re-fetch (Phases 8–9).
5. US6 and US7: cleanup and CI.
6. Hand-off (Phase 12).

Each ⏸ is a maintainer review point.

### Coverage of the merge-safety checklist's findings

| Checklist finding | Closed by |
|---|---|
| CHK003 `-X` prohibition | T007 |
| CHK010 explicit stray list | research R17 + T011 |
| CHK016 planning committed before M1 | T001 |
| CHK020 a delta after the cleanup | T081 |
| CHK022–CHK025 push, tag, sibling, 016 and signing evidence | T003 + T082 |
| CHK027 which commit `Tag:` names | T083 (a maintainer placeholder, filled at re-cut; analyze I2 option b) |
| CHK037 every `script.xsd` edit in A-1's commit | T026 |

---

## Notes

- 85 tasks. `[P]` means different files and no dependency on an unfinished task.
- Never edit `specs/016-coordinated-minor-bump/` or any landed `specs/0NN-*`.
- **M1 is the one merge made on a trial branch** (`017-m1-trial`, T007/T013, spec FR-002). It lands
  by fast-forward after approval, and a rejected trial is deleted and redone. For any other
  rejected unpushed commit, the maintainer decides between amending it and adding a corrective
  commit. Agents never force-push, and nothing here is pushed.
