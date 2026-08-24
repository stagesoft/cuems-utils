# Migration Completeness Checklist: Node model migration

**Purpose**: Validate that the *requirements* for migration completeness are themselves complete,
unambiguous and verifiable — every symbol accounted for, every caller covered, no orphan left
undefined, and the wire-format change proven rather than asserted.
**Created**: 2026-08-24
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [tasks.md](../tasks.md)
**Depth**: release gate · **Audience**: reviewer (pre-merge)

These are unit tests for the requirements, not for the code. Each item asks whether something is
*specified well enough to be checked* — a failing item means the spec needs a sentence, not that
the implementation is wrong.

---

## Symbol Inventory Completeness

- [ ] CHK001 Is the **source set** of "every node symbol" enumerated, rather than left to the reader to derive? [Completeness, Spec §FR-027]
- [ ] CHK002 Is the completeness criterion for the moved-symbol table stated — how a reviewer knows the table is exhaustive and not merely long? [Measurability, Spec §FR-027]
- [ ] CHK003 Are the status values for each moved symbol defined as a closed vocabulary, so "deleted" is distinguishable from "unaccounted for"? [Clarity, Spec §FR-027]
- [ ] CHK004 Does the requirement set cover symbols that are **renamed rather than moved** (`node_type` → `node_role`, `masters`/`slaves` → `by_role`), or only relocations? [Gap, Spec §FR-027]
- [ ] CHK005 Are the symbols that must **not** move — Avahi discovery, adoption, systemd orchestration — enumerated with the same rigour as those that must? [Coverage, Spec §FR-032]
- [ ] CHK006 Is `AvahiTool.NodeType`'s fate specified as part of the symbol inventory, given it is a duplicate definition in a file that otherwise stays? [Completeness, Spec §FR-001, Data-model §6]
- [ ] CHK007 Is the disposition of `STRING_TYPED_NODE_FIELDS` — deliberately *not* migrated — recorded as a decision in the symbol table, so its absence cannot read as an omission? [Clarity, Research §R4, Tasks T065]

## Caller & Consumer Accounting

- [ ] CHK008 Is the **denominator** for `cuems-nodeconf` callers stated — feature 004's inventory counted 11 call sites, and no requirement names that number or its source? [Gap, Spec §FR-030a, 004 migration-map §4]
- [ ] CHK009 Are requirements defined for callers that resolve today but become *semantically* wrong (the `node_type` normalisation in `read_network_map`, the enum comparisons), as distinct from callers that stop resolving? [Coverage, Spec §FR-030a]
- [ ] CHK010 Is it specified that the `cuems-engine` and `cuems-editor` guide entries must be verified against the live call sites rather than written from the planning documents? [Measurability, Spec §FR-011g, §FR-028]
- [ ] CHK011 Are `cuems-common`'s consumers accounted for with the same requirement strength as `cuems-nodeconf`'s, given the repository joined the feature after the original scope was written? [Consistency, Spec §FR-011f, §FR-030b]
- [ ] CHK012 Is there a requirement covering consumers that read `network_map.xml` **without** using `cuemsutils` — the three stdlib tools — as a distinct class from library consumers? [Coverage, Spec §FR-011f]
- [ ] CHK013 Are the requirements clear about which consumer changes belong to this feature and which to feature 008, at the granularity of individual call sites rather than whole repositories? [Clarity, Spec §FR-030]
- [ ] CHK014 Is the `get_nodes_by_adoption` caller in `cuems-engine` explicitly accounted for, given a requirement here keeps the function alive for it? [Traceability, Spec §FR-022, Assumption 8]

## Orphaned Artefact Definition & Coverage

- [ ] CHK015 Is "orphaned stub" **defined**, or does the requirement only name the two instances already known? [Ambiguity, Spec §FR-018]
- [ ] CHK016 Is there a requirement to search for node-related remnants beyond the two named stubs — for example in the legacy `XmlBuilder.py` / `Parsers.py` tree that still exists? [Gap, Spec §FR-018]
- [ ] CHK017 Are requirements defined for the *duplicate-named* modules that survive (`Settings.py`/`settings.py`, `XmlReaderWriter.py`/`xml_reader_writer.py`, `CMLCuemsConverter.py`/`converter.py`), or is their node-facing content out of scope? [Coverage, Gap]
- [ ] CHK018 Is `PutType`'s status specified as a decision with a rationale, rather than left as "resolved or re-deferred" without saying which? [Clarity, Spec §FR-029]
- [ ] CHK019 Are requirements stated for test artefacts that become orphans — `test_xml_roundtrip.py`, the nodeconf coercion test — with the same "accounted for" obligation as source symbols? [Consistency, Tasks T066, T078]
- [ ] CHK020 Is there a requirement that the *absence* of a deleted symbol stays asserted over time, rather than being verified once at merge? [Measurability, Spec §FR-018, §FR-020]

## Wire-Format Change Evidence

- [ ] CHK021 Is "proven changed" defined as automated assertion rather than review, and is the artefact that constitutes the proof named? [Measurability, Spec §SC-004]
- [ ] CHK022 Are requirements stated for proving the **old** format absent, not only the new format present? [Completeness, Spec §SC-004, §SC-004a]
- [ ] CHK023 Is the pre-change state specified as a retained artefact, so the round-trip diff has a fixed comparison point that later edits cannot move? [Traceability, Spec §FR-026, Tasks T004]
- [ ] CHK024 Is the permitted diff stated as an exact **set** of differences rather than as a tolerance or an example? [Clarity, Spec §FR-010]
- [ ] CHK025 Are requirements defined for proving the change did **not** reach the other five schemas, with a stated measurement? [Coverage, Spec §FR-010a, §SC-010a]
- [ ] CHK026 Is the mapping from each legacy spelling to each new value specified exhaustively, including the value that maps to itself? [Completeness, Contracts §M3]
- [ ] CHK027 Can "the element keeps its position" be objectively verified, given element order is derived and a move would silently enlarge the diff? [Measurability, Data-model §1]

## Migration Failure, Rollback & Recovery

- [ ] CHK028 **Are rollback requirements defined for the in-place conversion of `/etc/cuems/network_map.xml`?** No requirement currently mandates a backup, and the file holds operator-assigned aliases and adoption state that exist nowhere else. [Gap, Recovery Flow, Contracts §M3]
- [ ] CHK029 Are requirements defined for downgrade — installing a previous `cuems-common` or `cuems-utils` over a converted file? [Gap, Exception Flow]
- [ ] CHK030 Is the operator recovery path specified for a map whose role value the conversion leaves untouched, which then fails validation? The requirements say it fails loudly but not what is done next. [Gap, Recovery Flow, Spec §FR-014, Contracts §M3]
- [ ] CHK031 Are requirements defined for partial cluster migration — some nodes converted, some not — during a staged rollout? [Coverage, Gap, Spec §FR-030c]
- [ ] CHK032 Is the failure mode specified for a node where `postinst` runs but the conversion silently no-ops on an unexpected file shape? [Edge Case, Contracts §M3]
- [ ] CHK033 Are requirements stated for evidence that a conversion ran — a log line, a marker — so an operator can distinguish "already new format" from "never converted"? [Gap, Observability]

## Cross-Repository Ordering & Dependency

- [ ] CHK034 Is the release gate expressed as an enforceable **package dependency or version constraint**, or only as a documented instruction? A node can upgrade `cuems-utils` before `cuems-common`. [Gap, Spec §FR-030c, Contracts §M5]
- [ ] CHK035 Are requirements defined for the ordering of `postinst` execution relative to services that read the map at startup? [Coverage, Gap, Spec §FR-011d]
- [ ] CHK036 Is the obligation on the schema mirror stated as a continuous invariant rather than a one-time copy, given the two files have drifted before? [Clarity, Contracts §M2]
- [ ] CHK037 Are the branch points and branch names for all three repositories specified precisely enough to be checked at review time? [Measurability, Spec §FR-030a, §FR-030b]

## Traceability & Evidence Retention

- [ ] CHK038 Does every moved or deleted symbol trace to the requirement authorising its movement, rather than to the plan alone? [Traceability, Spec §FR-027]
- [ ] CHK039 Is it specified where the migration evidence lives after the branches merge, so feature 008 and any later reader can find it? [Gap, Spec §FR-028]
- [ ] CHK040 Is the migration guide's required content enumerated, or does "documented for the migration guide" appear in several requirements meaning different things? [Consistency, Spec §FR-023, §FR-027, §FR-028, §FR-030c]
- [ ] CHK041 Are the four "must be true when done" claims from the original feature framing each traceable to a numbered requirement? [Traceability]

## Ambiguities & Conflicts

- [ ] CHK042 Do FR-014 ("an unknown role is rejected at validation") and M3 ("an unknown value is left alone by the conversion") together leave a state no requirement resolves — a file the conversion accepts and the schema rejects? [Conflict, Spec §FR-014, Contracts §M3]
- [ ] CHK043 Is the guarded free-text field set stated identically everywhere it appears, given one document lists six fields and the pre-migration source listed seven? [Consistency, Spec §FR-012, §FR-024]
- [ ] CHK044 Is the assumption that `NodeIndex`'s key stays caller-supplied validated against what `cuems-nodeconf` actually needs, rather than asserted? [Assumption, Research §R5]
- [ ] CHK045 Is "no registration API exists" specified as an ongoing prohibition with a check, or as a statement of the current state? [Clarity, Spec §FR-017]
- [ ] CHK046 Is the scope boundary for the Avahi `node_type` TXT record unambiguous — inventoried but unchanged — given it shares a name with the field being renamed? [Ambiguity, Spec Assumption 10, Contracts §M4]

---

## Notes

- Check items off as completed: `[x]`. A failing item is a **spec defect**, not an implementation defect — fix it by adding or sharpening a requirement, then re-run.
- **CHK028 is the highest-value item in this checklist.** The conversion rewrites an operator's file in place, that file is the only record of node aliases and adoption state, and no requirement currently mandates a backup or a rollback path. It was surfaced by the rollback/recovery sweep the checklist method requires for state-mutating features.
- **CHK034 is the second.** The release gate is stated as documentation (FR-030c) but nothing prevents dpkg from upgrading `cuems-utils` before `cuems-common` on a single node, which is exactly the partially-deployed state the hard cutover has no answer for.
- **CHK042** is a genuine conflict between two documents of this feature, not an ambiguity in one.
- Items with `[Gap]` reference no spec section by design: the point is that no section exists.
- Traceability: 41 of 46 items (89%) carry a spec/plan/research/contract reference or an explicit marker.
