<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Data model: Release-line reconciliation before `0.1.1`

This feature adds **no schema element, no version step and no wire field**. The entities below are:
- the one model-level addition (A-1);
- the data the new permanent tests carry;
- the records 017 produces.

## 1. `TARGETLESS_ACTION_TYPES` (new, `cues/ActionCue.py`)

| Attribute | Value |
|---|---|
| Kind | module-level `frozenset[str]` |
| Members in 017 | exactly `{"stop_project"}` (Q1) |
| Not members, and not values | `pause_project`, `resume_project`: **retired from `ActionType`** (Q13, FR-029d); reinstating them is in `specs/planning/project-pause-resume-deferred.md` |
| Consulted by | three T2 rules: `action_target_required` (passes `None` for a type in the set), `action_target_resolves` (skips a type in the set), `project_action_takes_no_target` (new; fires on a non-`None` target for a type in the set, repairable to `None`). Also `ActionCue.__init__` and `ActionCue.set_action_target` (via `enforce`), and `from_json` through the constructor |
| Not consulted by | `set_action_type`, the writer, the reader, the descriptor (whose field classification stays UNREPAIRABLE by FR-023a's conservative map) |
| Public? | no (not exported, not snapshotted) |

**Validation rules for `ActionCue.action_target`** (after A-1):

| `action_type` | `action_target` | Construct / `from_json` | Setter after init | `save` / `load` (T2) |
|---|---|---|---|---|
| in the set (`stop_project`) | `None`, `""`, absent | ✅ (stored `None`) | ✅ | ✅, written `<action_target />` |
| in the set | a uuid, resolving **or dangling** (Q2 revisited) | ✅ | ✅ | **save:** ❌ `project_action_takes_no_target` (refused, actionable). **load:** REPAIRED → `None`, one `RepairRecord`, file stale. `action_target_resolves` skips it |
| not in the set (`stop`, `play`, `pause`, …) | `None`, `""`, absent | ❌ `action_target is required` | ❌ same | ❌ T2 `action_target_required`, unrepairable |
| not in the set | uuid | ✅ | ✅ | ✅ if it resolves |
| unknown value, **including the retired `pause_project` / `resume_project`** | any | — | — | ❌ T1 enumeration |

**`ActionType` after 017 (11 values):** `play`, `pause`, `stop`, `load`, `unload`, `enable`,
`disable`, `fade_action`, `wait`, `go_to`, `stop_project`.

**The rules on `ActionCue.action_target` after A-1** (registration order):

| Rule | Fires when | Repairable | Descriptor classification of the field |
|---|---|---|---|
| `action_target_required` | `None` and type **not** in the set | no | — |
| `action_target_resolves` | non-`None`, dangling, and type **not** in the set | no | — |
| `project_action_takes_no_target` (new) | non-`None` and type **in** the set | **yes** (→ `None`) | — |
| *field, combined (FR-023a)* | — | — | **UNREPAIRABLE**: repairable only if every rule is |

A dangling leftover uuid on `stop_project` therefore produces exactly **one** finding, the
repairable one. This is the edge case the earlier reading left refused.

**State.** None: the set is a constant. A cue moves between rows only by `set_action_type` /
`set_action_target`, and only `save` re-checks the pair (R4).

## 2. Released sets (data in `tests/packaging/test_changelog_completeness.py`)

| Set | Members (measured 2026-10-21, R9) | Source |
|---|---|---|
| `RELEASED_DEBIAN` | rc8, rc9, rc10, rc11, rc12, rc14, rc15, rc16, rc16+1, rc17 | non-`UNRELEASED` headers on `origin/debian/bookworm` |
| `RELEASED_PYPI` (≥ rc5) | rc7, rc8, rc10, rc11, rc14, rc15, rc16 | PyPI JSON API, yanked files included |
| `NEVER_PUBLISHED` | rc5, rc6, rc13 | M1 |
| derived: Debian only | rc9, rc12, rc16+1, rc17 | `RELEASED_DEBIAN − RELEASED_PYPI` |

**Rules.**
- `CHANGELOG.md` has a section or a `<!-- debian: X -->` comment for every member of
  `RELEASED_DEBIAN ∪ RELEASED_PYPI`.
- A "Debian only" section carries the "(Debian only; not published to PyPI)" marking. rc16+1 is
  written as a comment under rc16.
- Each `NEVER_PUBLISHED` member has a "never published" marking (rc5, rc6) or one line (rc13).
- No `RELEASED_PYPI` member carries either marking.
- All three sets are re-measured at hand-off. If PyPI gains rc17 by then, rc17 moves out of
  "Debian only" and loses its marking in the same commit.

## 3. `debian/changelog` entry order (FR-030)

`0.1.1 UNRELEASED` → `0.1.0rc17` → `0.1.0rc16+1` → `0.1.0rc16` → `0.1.0rc15` (released, verbatim)
→ `0.1.0rc14` … `0.1.0rc8` (already identical) → `0.1.0rc5`, `0.0.7-31`, `0.0.7-3`, `0.0.7-2`,
`0.0.6-0`, `0.0.1-0` (UNRELEASED, HEAD's form; a recorded exception to "verbatim").

**Invariant (spec M2).** Among the entries above the oldest released one (`0.1.0rc8`), only the
top entry is `UNRELEASED`. The six older never-built entries are `UNRELEASED` by nature and are
exempt.

## 4. Inventory item (evidence row, `evidence/inventory.md`)

`# | item | released in | method (M/R/A; never C) | commits | proof kind | proof id | result`.
There are 14 rows (spec FR-003 table). The proof kind is one of: public-API test, packaging test,
history check (patch-equivalence / subject twin / ancestry / empty tree diff), changelog test, or
FR-011/032/050 check.

## 5. Red→green pair (`evidence/red-green.md`)

`adaptation id | test node id | base commit (red) | red excerpt | change commit | green excerpt`.
A check already green on its base is recorded as `held` with its passing excerpt. That is not a
red→green pair, and FR-080 does not count it as one.

## 6. Retirement record (`evidence/test-retirements.md`)

`test or file | origin (rc / commit) | reason (the settled decision it contradicts, or "no tests")
| replacement, if any`. Known rows today:
- `TestFileMd5::test_stored_lowercase` (rc15; 014 strict md5 rule);
- `tests/testdev_nng_talk.py` (no tests; a manual script);
- the absorbed root copies of the rc16/rc17 test files, replaced by their ports.

## 7. Relation row 26 (`contracts/relation-row-26.md`)

| Field | Value |
|---|---|
| Relation | `cuems-utils` `Replaces: cuems-engine (<< 0.1.0rc6-2~)` |
| Reason | `usr/lib/cuems/bin/cffi-gen-src` moved from the engine to this package (rc15, PR #14) |
| Accompanying `Breaks:` | none (Q6) |
| Verdicts | replaced: `0.1.0rc5-6`, `0.1.0rc6-1`; not replaced: `0.1.0rc6-2`, `0.1.0rc6-5`, `0.1.1-1` |

## 8. Gate run record (`evidence/ci-gate.md`, template in 017, filled after hand-off)

`run URL | tested SHA | siblings_ref | each sibling's commit | pass/skip/xfail | strict xfails |
sibling-reading tests ran/skipped | xmlschema, lxml resolved | blocking jobs' results |
informational jobs' results | docs deployed? (must be no) | coverage uploaded? (must be no)`.
