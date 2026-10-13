<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — the sibling gates, and how cross-repository claims are validated

**Phase 1** · 2026-10-13 · measured against each sibling's checkout, not predicted.

---

## 1. The seven sibling tests that flip

Each is a strict xfail that **fails the suite with `XPASS(strict)`** the day the library lands its
half — which is the posture that makes it a gate rather than a note. Source:
`../cuems-editor/specs/002-config-round-trip/tag-readiness.md`, *Status: NOT READY*.

| Gate | Repository | Test | Flips when |
|---|---|---|---|
| G1 | `cuems-editor` | `tests/test_schema_descriptor.py::test_first_config_save_of_project_settings_round_trips` | the path helpers gain tolerance **and** that repository passes it on at its own write site. **A library change alone does not flip it** |
| G2 | `cuems-editor` | `tests/test_upstream_gates.py::test_config_load_project_settings_round_trips` | the public projection lands **and** that repository removes `project_settings` from its refusal set and gives it a load step |
| G3 | `cuems-editor` | `tests/test_upstream_gates.py::test_a_cue_built_from_the_descriptor_instance_saves_through_project_save` | a cue instance saves (today refused at the output volume) |
| G3 | `cuems-editor` | `…::test_a_config_root_instance_saves_through_config_save[settings]` | the settings root instance is saveable (today `{"Settings": null}`) |
| G3 | `cuems-editor` | `…::test_a_config_root_instance_saves_through_config_save[project_mappings]` | the mappings root instance is saveable (today refused at the node count) |
| G3 | `cuems-editor` | `…::test_a_config_root_instance_saves_through_config_save[project_settings]` | the project-settings root instance is saveable (today refused at a setting's name) |
| G4 | `cuems-editor` | `tests/test_upstream_gates.py::test_nodeconf_engine_callback_accepts_node_set` | the index setter lands **and** `cuems-nodeconf` ships the handler. Today: *unknown action* |

**G5 has no sibling test.** It is this library's defect and the editor has none for it; it is listed
in that repository's gate record only so the list is complete in one place.

**`cuems-frontend`'s side of G3**: one named transform (`toWireShape` plus a starting-values table in
its descriptor handler) is deleted in one edit, with no value hand-authored on its side. That
deletion — not a passing test here — is G3's completion marker for that repository.

**`cuems-editor`'s side of S1** (added 2026-10-13; it had no entry here, and SC-009 had no task):
the anchored regular expression over this library's prose and the empty-string fallback behind it are
removed, and the handler names `NodeIdentityCollisionError`. Like the frontend's, this is a
**removal** rather than a test flipping, so it is a completion marker that must be looked at in that
checkout — FR-065b.

### What this table does **not** say, and the correction that follows

Read the *Flips when* column across the seven rows: **three of them — G1, G2 and G4 — say "and"**.
A library change alone cannot turn them XPASS, and G4's second half is in a *third* repository.
Only the four G3 rows flip on this feature's landing.

That was measured here on the specify pass and then contradicted by SC-012, which asserted all seven
— because the spec had written down only G1's obligation (FR-008) and none of the others. Corrected
2026-10-13: FR-017 (G2), FR-047 (G4) and FR-065b (S1) join FR-008 and FR-031, SC-012 claims the four
that are reachable, and **FR-106 collects all eight obligations with their measured status in
`consumers_works.md`** — which is this repository's counterpart to `cuems-editor`'s own
tag-readiness record, and must agree with it row by row.

**The count is ten, not eight.** Measuring each site rather than reading the gate list added two:
`cuems-editor`'s `_root_instance` docstring (`CuemsWsUser.py:264-270`), which asserts *"not a
saveable document: its required leaves are null"* and states the exact position FR-026 reverses; and
that repository's own tag-readiness record, whose status the first draft of SC-012 made a deliverable
of this repository. Neither is gate-shaped, and neither would have failed a test.

**Obligation on this feature** (FR-103): each of these is verified against that sibling's checkout
rather than predicted. 014 learned this twice — a prediction that a sibling's test would close by
re-run was wrong, and a gate run without a control arm attributed 151 of someone else's failures to
the feature under test.

---

## 2. Parallel verification must use a worktree

FR-104. Any sibling verification run in parallel uses a **per-session `git worktree`** of this
repository, never the shared checkout. The gate prompt that told N parallel sessions to point the
one shared checkout at a branch point was a race by construction; it was caught before any number
was trusted and corrected. **The defect was in the prompt, not in the sessions.**

---

## 3. The coordinated-tag resolver (FR-080c..FR-080f)

**The rule**: a cross-repository claim resolves a sibling at its `xml-refactor-merge-candidate`
**tag**, never at its tip.

| Condition | Outcome |
|---|---|
| checkout absent | **skip**, with a reason |
| checkout present, tag absent | **skip**, with a reason |
| tag resolves, claim holds | pass |
| tag resolves, claim does not hold | **fail** |

A skip is never a silent pass. Both existing contract files already skip with a reason on an absent
checkout — **verified 2026-10-13, so FR-081 is already satisfied** and is a property to preserve
rather than work to do.

### Measured tag state, 2026-10-13

| Repository | Tag | `CLAUDE.md` records | Verdict |
|---|---|---|---|
| `cuems-common` | `91b2d25` | `e3c9430` | ⚠ **moved** |
| `cuems-nodeconf` | `c29c25c` | `b305c1c` | ⚠ **moved** |
| `cuems-power-bridge` | `cabbb3e` | `399baf7` | ⚠ **moved** |
| `cuems-frontend` | `531004b` | recorded as tagged, value unstated | newly pinned |
| `cuems-engine` | none (tip `a197cac`) | none | consistent |
| `cuems-editor` | none (tip `1144a1d`, 002 merged) | none | consistent |
| `cuems-utils` | none (tip `75a958e`) | none — this repository tags **last** | consistent |

**Three of four recorded values are wrong**, found by resolving the tags rather than by reading the
record. That is the entire argument for this resolver, and FR-080f requires those values re-verified
against the tags.

**A partial tag set yields a partial, honest result** (FR-080e): four of seven are tagged today, and
the resolver must be usable now rather than only after the set is complete.

### Why re-cutting one tag re-validates the whole set (FR-080d)

Feature 011's recorded lesson: for one day the tag set **did not compose**, because one member's tag
still pointed at a tree shipping a superseded value, while both working trees were correct and every
packaging relation was satisfied. *A candidate tag set is only as current as its least current
member, and no packaging relation expresses that.* This resolver is the first mechanism in the
ecosystem that does.

Moving a published tag remains **maintainer-only**, never an agent's action.

---

## 4. The two assertion classes (FR-080, FR-080a, FR-080b)

| Class | Example | Treatment |
|---|---|---|
| **provenance** — "verified at `<commit>`" | 013's guide pins `cuems-editor 106015c`, `cuems-frontend 3183845` | **dated**, and resolution no longer asserted. Measured: both commits are absent from `git log --all` in their siblings — dead references, not moved ones |
| **operator instruction** — "require version X", "watch for signal Y" | 012's guide requires `cuems-engine 0.1.0rc7` and names a status signal | **corrected**, as a documentation defect. That tree declares `0.1.0-rev1` — a renamed scheme under which "rc7 or later" is unverifiable — and the signal is absent from its controller source |

Freezing a provenance pin is correct. Freezing a wrong operator instruction would leave a guide
sending someone to watch for a signal that no longer exists — which is why one policy could not
serve both, and why this feature's four red tests had two different causes.
