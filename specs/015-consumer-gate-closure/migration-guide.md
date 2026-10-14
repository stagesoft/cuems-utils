<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Migration guide — feature 015, the consumer-gate closure

**Feature**: `015-consumer-gate-closure` | **Written**: 2026-10-13
**Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md) | **Data model**: [data-model.md](data-model.md)
**Consumer obligations**: [consumers_works.md](consumers_works.md) — the measured, per-repository counterpart to this file

This document is for the maintainer of **one** consumer repository, and for this repository's
own release record. Find your repository below; if your repository is not named, this feature
makes no change you need to react to.

---

## 1. Sibling obligations (FR-008, FR-046, FR-103)

Nine gates, ten obligations — the full breakdown, measured per site, lives in
[consumers_works.md](consumers_works.md). The short form:

| Gate | This library | The sibling half |
|---|---|---|
| G1 | `must_exist=False` on both path helpers | `cuems-editor` must pass the flag on at its own `_config_path` write site (FR-008) |
| G2 | `project_settings` becomes publicly readable | `cuems-editor` must remove its refusal entry and add a load step (FR-017) |
| G3 | the descriptor's instance is wire-shaped and saveable | `cuems-frontend` deletes its hand-written `toWireShape` transform in one edit (FR-031); `cuems-editor` corrects a docstring that becomes false |
| G4 | `NodeIndex.set_alias` | `cuems-nodeconf` ships the `node_set` IPC handler (FR-046/FR-047), verified word for word against `../cuems-nodeconf/specs/planning/12-node-set-alias.md` §4 |
| G5 | the version step addresses both player shapes | none — this is this library's own defect |
| S1 | `NodeIdentityCollisionError` carries structured data | `cuems-editor` deletes its regular expression over this library's prose (FR-065b) |

## 2. The sanctioned golden event (FR-074)

Executed once, in the polish phase, after every public addition and after the writer change —
the record is §7 below.

## 3. The operator triage question (FR-058, G5)

Not *"is it flat-shaped?"* — two different populations, because 013's reshape and F3's retired
counts are independent axes. The correct question:

```bash
grep -cE '<(audio_cards|universes)>' /etc/cuems/settings.xml    # non-zero -> affected
```

## 4. Cross-repository assertion-class split (FR-080)

Recorded in §8 below.

## 5. Planning-folder disposition table (FR-093)

Recorded in §10 below, once T109–T115 land.

## 6. G4 — `NodeIndex.set_alias`, verified against the two-repository contract (T050)

`NodeIndex.set_alias(node_uuid, alias: str | None) -> bool` was checked word for word against
`../cuems-nodeconf/specs/planning/12-node-set-alias.md` §4, which states this library's half of
the contract identically. Agreement, item by item:

| That document's §4 | This implementation |
|---|---|
| "Validates first: `alias` must be `None` or a string matching `NonEmptyString`, else `ValueError`, raised **before** any node is touched" | matches — the blank/empty check runs before the search loop |
| "Mutates in place, on the node object the document holds" | matches — the same aliasing contract `adopt`/`unadopt` already document |
| "Returns `False` for an unknown uuid and `True` otherwise, whether or not the value changed" | matches |
| "`signature()` already includes `alias`, so the write-if-changed path needs no change" | verified (T049) — `NodeIndex.signature` already reads `n.get("alias")` |

No divergence found. `cuems-nodeconf`'s own `alias_node` (its §5b) is written against exactly this
signature, catching `ValueError` and checking `found`/`signature()` in that order — unblocked by
this landing, not yet shipped (§1 above).

---

*Sections below are filled in as each phase of `tasks.md` lands.*

## 7. The sanctioned golden event — executed 2026-10-14 (T026, T088, T089, T092)

**One event, the arc's fourth** (after 008's three and 014's). It is scheduled after every public
addition **because** `tests/golden/api/public_api.json` records the error hierarchy with each
class's bases and methods: a feature that adds an exception moves that golden, so re-cutting before
the last exception lands (here `NodeIdentityCollisionError`, T080) would leave the golden stale at
the end of the feature.

**Reason**: the writer now indents (S3, `documents.serialize_tree`), and the public surface grew.

| Golden | Event |
|---|---|
| `xml/cuems-editor__script_minimal.xml`, `xml/cuems-engine__projects__complex_test__script.xml`, `xml/cuems-engine__projects__empty_test__script.xml`, `xml/cuems-utils__fade_showcase.xml`, `xml/cuems-utils__unicode_showcase.xml`, `generated/example_script.xml` | re-cut with `capture_goldens --force`; whitespace between elements only |
| `api/public_api.json` | re-cut: `NodeIdentityCollisionError`, `NodeIndex` (incl. `set_alias`), and the two `must_exist` signatures |
| `api/config_accessors.json` | **edited surgically, not re-cut** (see below): the two `conf_path` signatures, `project_path`'s, and the `project_settings` property |
| `MANIFEST.sha256` | the eight entries above updated |

**Why `config_accessors.json` was not re-cut.** It is the pre-006 baseline that
`test_config_accessor_names.py` compares live return types *against* (`dict` → typed object). A
full `capture` flattened that history and turned two tests into tautologies, so only the entries
this feature added or changed were edited. The same reasoning is why `outcomes.json` was **not**
touched: `capture_goldens --force` also rewrites it, and that was reverted.

**T089 verified**: the 24 `dict/` goldens, `generated/example_script.reader.json` and
`outcomes.json` are byte-unchanged (`git status` shows none modified) — a wire dict carries no
whitespace.

**Test inverted, not deleted**: `test_byte_identity_xml.py::test_no_indentation` became
`test_indentation`.

## 8. Cross-repository assertions, split by class (T097–T104, FR-080)

**The resolver**: `tests/support/sibling_tags.py` resolves a sibling at its
`xml-refactor-merge-candidate` **tag**, never its tip; `tests/contract/test_sibling_tag_resolver.py`
tests it (absent checkout → skip; absent tag → skip, different reason; tag resolves and the claim
fails → fail; partial tag set → partial honest result).

| Class | Meaning | Asserted how |
|---|---|---|
| **Operator instruction** | what the guide tells a person to check or type on a node | at the sibling's tag, through the resolver (`test_migration_guide.py`) |
| **Provenance pin** | the commit a line number was measured at | **not** asserted to resolve; the guide carries a dated note instead (`test_migration_guide_names_sites.py`) |

**Today's reading (2026-10-14)**: `cuems-common`, `cuems-nodeconf`, `cuems-power-bridge` and
`cuems-frontend` are tagged; `cuems-engine` and `cuems-editor` are not, so the two engine claims
(coupled version, `cluster_warning`) **skip with a stated reason** rather than pass or fail. Checked
by hand against `cuems-engine` `feat/xml-refactor` (`fc0cad3`), **both hold**: `__version__ =
"0.1.0rc7"` and `/engine/status/cluster_warning` with a `"missing"` list. ⚠ This section first said
both were false and "corrected" 012's guide accordingly; that came from reading the engine on the
wrong branch (`format/module_extraction`), and the corrections were **reverted** (T100 is therefore a
no-op on the 012 guide). 013's two dead pins (`cuems-editor 106015c`, `cuems-frontend 3183845`) are
marked dead and dated in place (T101).

**Tag values, re-verified against the tags (T102).** Record the *commit* (`<tag>^{commit}`), never
`git rev-parse <tag>`: an annotated tag has a separate object id. The draft figures
`91b2d25`/`c29c25c`/`cabbb3e`/`531004b` were tag **objects**; the commits are `e3c9430`
(`cuems-common`, unchanged), `5be6cf0` (`cuems-nodeconf`, **moved** from `b305c1c`), `399baf7`
(`cuems-power-bridge`, unchanged) and `f5453a3` (`cuems-frontend`). `CLAUDE.md` is corrected
accordingly. (`contracts/sibling-gates.md` §3's table has the same misreading and carries a
correction note.)

**Re-cutting any candidate tag re-validates the whole set (T103, FR-080d).** *A candidate tag set is
only as current as its least current member, and no packaging relation expresses that* — feature
011 lived a day of exactly that. After moving one tag, re-run `test_migration_guide.py` and
`test_sibling_tag_resolver.py` and re-check every counterpart's tag. **Moving a published tag stays
maintainer-only**, never an agent's action.

**FR-081 holds (T104)**: with a sibling absent the guide tests still skip with a reason, now through
the one resolver.

## 9. Sibling suites in two arms (T105, T107, T108; FR-103..FR-105, SC-014)

**Method.** One runner for all: a scratch venv over this repository's `hatch` interpreter
(CPython 3.11.9, python-build-standalone) plus each sibling's missing dependencies, `pyossia` from
the local `libossia/build`. **Arm A** = `cuemsutils` from a throwaway `git worktree` at the branch
point `75a958e`; **arm B** = this branch's working tree (uncommitted — a worktree could not carry
it). The shared checkout is never moved (FR-104).

| Repository | Arm A (branch point) | Arm B (this branch) | Attributable to 015 |
|---|---|---|---|
| `cuems-editor` | 2 failed · 258 passed · 3 skipped · 7 xfailed | 6 failed · 257 passed · 3 skipped · 4 xfailed | **4**: three intended `XPASS(strict)` flips (G3 config roots) and **one real fixture break** (indentation) — all closed, see below |
| `cuems-nodeconf` | 184 passed · 1 xfailed | 184 passed · 1 xfailed | **0** |
| `cuems-power-bridge` | 57 failed · 219 passed | 57 failed · 219 passed (identical set) | **0** of 57 — the 57 pre-date this feature (`network_map_invalid` fixtures) |
| `cuems-engine` (`feat/xml-refactor` @ `fc0cad3`) | 28 failed · 831 passed · 1 error | 28 failed · 831 passed · 1 error (identical set) | **0** — but ⚠ run against a **mock `pyossia`**, so the 28 failures are the tests that touch it, unmeasured rather than passing; needs a host with the real package |
| `cuems-frontend` | 289 success | 289 success | **0** — no Python dependency; coupled only by wire shape (`ng test --watch=false --browsers=ChromeHeadless`), so the arms are identical by construction |

**The ratio is the finding**: 1 real regression and 3 intended flips against 59 failures already
present in two siblings (and 28 in the engine, identical in both arms). After T108 the editor's own suite is `2 failed · 261 passed · 4 xfailed`,
the 2 being the control arm's.

**T108**: closed in `../cuems-editor` (uncommitted there): `test_repair_durations.py` stripped
`\n` but not indentation; and the three flipped G3 markers were removed (S6). Details and the
G3-cue finding (a **test-construction** problem, so *three* of SC-012's four flips happen, not
four) are in [consumers_works.md](consumers_works.md).

*First reading of the engine (superseded):* its checkout was on `format/module_extraction` and could not collect; it was re-read on `feat/xml-refactor` on the same day, which is the row above.

**Not closed, and why**: nothing in `cuems-nodeconf` or `cuems-power-bridge` was broken by this
feature, so nothing was edited there.

## 10. Planning-folder disposition (T110–T112, T114–T115; FR-093, FR-093a, FR-093b)

Outcomes are `specs/planning/`'s own: **kept** (with a reason), **re-homed** (to a file that *exists*
— FR-093a), **deleted**. Counted on disk 2026-10-14.

### `xml-rebuild/` — 20 files

| File | Outcome | Reason |
|---|---|---|
| `xml-rebuild-01-audit.md` … `-06-target-design.md` (6) | **kept** | the arc's design argument: audit, node-model ownership, design inputs, object model, wire contract, target design. Landed features 004–014 cite them as their rationale; git history alone would orphan every citation |
| `xml-rebuild-07-speckit-prompts.md` | **kept** | the cross-repository prompt that 010's per-repository set was cut from; cited by `010-consumer-prompts/README.md` and by the feature specs |
| `xml-rebuild-08-extension-audit.md` | **kept** | the evidence behind feature 008's scope |
| `xml-rebuild-09-consumer-audit.md` | **kept** | the call-site evidence (`C1`–`C12`) behind feature 010; its C9 correction is already recorded in `CLAUDE.md` |
| `010-consumer-prompts/` — `00`…`07`, `04a`, `04b`, `README.md` (11) | **deletable, not deleted here** | one-shot inputs, same class as the seven prompts T115 deletes — every flow has landed. They stay **because 010 is not closed**: T028 is deliberately open and R1–R12 live in `deprecated-surface-removal-v0-1-1.md`, and 010's `spec.md`, `plan.md`, `tasks.md`, `quickstart.md` and `baseline.md` cite them by path as live inputs. Delete with 010's closure, not before: FR-091 names nine documents and these are not among them |

### The first-install pair (FR-093b)

| File | Outcome | Reason |
|---|---|---|
| `etc-cuems-first-install.md` (1384 lines) | **kept until the coordinated tag is cut, then re-assessed as one pair** | its status line reads *design settled; feature 011 landed 2026-09-28*, but it and its companion describe the 011–015 arc, of which this feature is the last member; the arc is not complete until the tag is |
| `etc-cuems-first-install-execution.md` | **kept**, corrected (T109) | holds the build state and the step sequence; same re-assessment as its pair |

### Re-homed

| Document | Outcome |
|---|---|
| `refactor-sequencing-2026-10-01.md` | **deleted** after its residue was re-homed to the **existing** `adoption-liveness-ui-tier.md`; its stop-condition (the frontend flow landed and carries a tag) is satisfied |

## 11. FR-090's condition, verified row by row (T114)

Every row of `specs/planning/upcoming-feature-requirements-2026-10-02.md`, as of 2026-10-14.

| Row | Disposition | Evidence |
|---|---|---|
| **G1** | implemented | `c43a342` — `must_exist` on both path helpers; consumer half recorded in `consumers_works.md` row 1 |
| **G2** | implemented | `19e9168` — public `project_settings` read and `to_wire` section |
| **G3** | implemented | `c48cf17` — wire-shaped, saveable instances; three of the editor's four G3 flips observed (§9) |
| **G4** | implemented | `9c95285` — `NodeIndex.set_alias`; `cuems-nodeconf`'s handler is that repository's (`consumers_works.md` row 3) |
| **G5** | implemented | `b43bc50` — the settings version step addresses both player shapes |
| **S1** | implemented | `e37808e` — `NodeIdentityCollisionError` |
| **S2** | implemented | `4db0b85` — a union reports a closed set only when every member is |
| **S3** | implemented | `documents.serialize_tree` (T087) — the writer indents, including `cuems-init-node`'s |
| **S4** | implemented | `to_wire` docstring (T093) |
| **SET-1** `__version__` stays `0.1.0rc16` | honoured | `src/cuemsutils/__init__.py:4`, `debian/changelog` head, and `tests/packaging/test_no_version_bump.py` |
| **SET-2** round trip needs no work | honoured | unchanged; the gates were the documents the trip could not reach |
| **SET-3** UR-5 closed by `from_json` | settled | 014 |
| **SET-4** UR-3 withdrawn | settled, and **documented once** | S4 above |
| **SET-5** no fold into `cuems-convert-documents` | honoured | not proposed |
| **SET-6** `'Cue' in item` prescription withdrawn | settled | corrected in 013's guide |
| **SET-7** no content-hash helper | **declined** | not asked for |
| **SET-8** no ingest-resolve-persist call | **declined** | `from_json` returns the object; `save_*` writes |
| **SET-9** engine-side reload | **declined** — not this repository's | |
| **SET-10** `save` upgrades `doc_version` | settled — expected behaviour | |
| **SET-11** report numbers per repository | honoured | every citation here is `<repo> UR-<n>` |
| **SET-12** `XmlBuilder.py` | **deferred** to the deprecated-surface release | `deprecated-surface-removal-v0-1-1.md`; no live caller |
| **SET-13** nodeconf surface beyond the label setter | **declined** — a future spec | capability layer §3 |

Nothing is left without a disposition. The source document's own deletion condition is therefore
met, and T115 deletes it **last**.
