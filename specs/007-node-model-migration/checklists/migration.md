# Migration Completeness Checklist: Node model migration

**Purpose**: Validate that the *requirements* for migration completeness are themselves complete,
unambiguous and verifiable — every symbol accounted for, every caller covered, no orphan left
undefined, and the wire-format change proven rather than asserted.
**Created**: 2026-08-24
**Verified**: 2026-08-24, against spec.md, plan.md, research.md, data-model.md, contracts/ and
tasks.md as committed at `6610662`. Results at the end of this file.
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [tasks.md](../tasks.md)
**Depth**: release gate · **Audience**: reviewer (pre-merge)

These are unit tests for the requirements, not for the code. Each item asks whether something is
*specified well enough to be checked* — a failing item means the spec needs a sentence, not that
the implementation is wrong.

---

## Symbol Inventory Completeness

- [x] CHK001 Is the **source set** of "every node symbol" enumerated, rather than left to the reader to derive? [Completeness, Spec §FR-027] — FR-027 defines it as the pre-edit inventory; T006/T006a produce it.
- [x] CHK002 Is the completeness criterion for the moved-symbol table stated — how a reviewer knows the table is exhaustive and not merely long? [Measurability, Spec §FR-027] — FR-027 "measurable against a denominator"; SC-007 zero unaccounted; T084 measures against T006a.
- [x] CHK003 Are the status values for each moved symbol defined as a closed vocabulary, so "deleted" is distinguishable from "unaccounted for"? [Clarity, Spec §FR-027] — FR-027: moved / replaced / deleted.
- [x] CHK004 Does the requirement set cover symbols that are **renamed rather than moved** (`node_type` → `node_role`, `masters`/`slaves` → `by_role`), or only relocations? [Gap, Spec §FR-027] — "replaced" covers rename; FR-023 enumerates changed names against call sites; data-model §3.4 and plan §III cover `masters`/`slaves`.
- [x] CHK005 Are the symbols that must **not** move — Avahi discovery, adoption, systemd orchestration — enumerated with the same rigour as those that must? [Coverage, Spec §FR-032] — FR-032 "checked, not asserted"; T006a is the denominator, T078b the check, SC-013 the count, C12 the contract.
- [x] CHK006 Is `AvahiTool.NodeType`'s fate specified as part of the symbol inventory, given it is a duplicate definition in a file that otherwise stays? [Completeness, Spec §FR-001, Data-model §6] — data-model §6 "replaced by the import"; T073.
- [x] CHK007 Is the disposition of `STRING_TYPED_NODE_FIELDS` — deliberately *not* migrated — recorded as a decision in the symbol table, so its absence cannot read as an omission? [Clarity, Research §R4, Tasks T065] — research R4 states it as a decision with its reason; FR-027a requires the guide to carry the deliberate non-migrations; T065.

## Caller & Consumer Accounting

- [x] CHK008 Is the **denominator** for `cuems-nodeconf` callers stated — feature 004's inventory counted 11 call sites, and no requirement names that number or its source? [Gap, Spec §FR-030a, 004 migration-map §4] — **Closed, as a decision rather than a widening.** FR-030a-i states the inventory is scoped to `cuemsnodeconf/` **deliberately**: the repository root and `tests/` are partially implemented and far from the other repositories' integration maturity, so measuring against them would use a moving denominator. Its consequence is now a requirement — the migrated node standard and its full testing live in `cuems-utils` exclusively, and a node-model test added to `cuems-nodeconf` afterwards is a regression. T006a records the exclusion.
- [x] CHK009 Are requirements defined for callers that resolve today but become *semantically* wrong (the `node_type` normalisation in `read_network_map`, the enum comparisons), as distinct from callers that stop resolving? [Coverage, Spec §FR-030a] — **Closed.** FR-030a-ii names the class, lists its known members (the `read_network_map` normalisation, the role enum comparisons, `CONTROLLER_NETWORK_FLAG`), and requires it to be searched for rather than waited for — nothing fails when a member is missed. T006f inventories it.
- [x] CHK010 Is it specified that the `cuems-engine` and `cuems-editor` guide entries must be verified against the live call sites rather than written from the planning documents? [Measurability, Spec §FR-011g, §FR-028] — FR-028 states it in those words; T085/T086 repeat it.
- [x] CHK011 Are `cuems-common`'s consumers accounted for with the same requirement strength as `cuems-nodeconf`'s, given the repository joined the feature after the original scope was written? [Consistency, Spec §FR-011f, §FR-030b] — FR-011f names all three tools with the consequence of staleness; FR-030b enumerates the branch scope; M4 tabulates; T050/T055–T059.
- [x] CHK012 Is there a requirement covering consumers that read `network_map.xml` **without** using `cuemsutils` — the three stdlib tools — as a distinct class from library consumers? [Coverage, Spec §FR-011f] — FR-011f is exactly that class; FR-011d states why (the shared-venv rule).
- [x] CHK013 Are the requirements clear about which consumer changes belong to this feature and which to feature 009, at the granularity of individual call sites rather than whole repositories? [Clarity, Spec §FR-030] — FR-011g names `CONTROLLER_NETWORK_FLAG` and its two comparison sites; T086 names `CuemsWsServer.py:425` and `reload_network_map_nodes`.
- [x] CHK014 Is the `get_nodes_by_adoption` caller in `cuems-engine` explicitly accounted for, given a requirement here keeps the function alive for it? [Traceability, Spec §FR-022, Assumption 8] — Assumption 8 keeps it alive; research R7 names `ControllerEngine:249`; T083 deprecates; T085 carries it into the guide.

## Orphaned Artefact Definition & Coverage

- [x] CHK015 Is "orphaned stub" **defined**, or does the requirement only name the two instances already known? [Ambiguity, Spec §FR-018] — FR-018 carries a definition independent of the two names.
- [x] CHK016 Is there a requirement to search for node-related remnants beyond the two named stubs — for example in the legacy `XmlBuilder.py` / `Parsers.py` tree that still exists? [Gap, Spec §FR-018] — FR-018 "a search MUST be run and its result recorded"; T078a; C12.
- [x] CHK017 Are requirements defined for the *duplicate-named* modules that survive (`Settings.py`/`settings.py`, `XmlReaderWriter.py`/`xml_reader_writer.py`, `CMLCuemsConverter.py`/`converter.py`), or is their node-facing content out of scope? [Coverage, Gap] — **Closed.** FR-018's search now names them and requires the recorded result to say which hold node content and which hold none; T078a. Measured answer today: only `xml/settings.py` (31 lines — `NetworkMap`, in scope via T032/T082/T083) and `xml/XmlBuilder.py` (2 lines — the stub, FR-018/T045); the other six hold zero.
- [x] CHK018 Is `PutType`'s status specified as a decision with a rationale, rather than left as "resolved or re-deferred" without saying which? [Clarity, Spec §FR-029] — FR-029 "resolved, not re-deferred", with the reason and the `project_mappings.xsd` distinction; M1, data-model §1, Clarifications.
- [x] CHK019 Are requirements stated for test artefacts that become orphans — `test_xml_roundtrip.py`, the nodeconf coercion test — with the same "accounted for" obligation as source symbols? [Consistency, Tasks T066, T078] — FR-018's definition says "a symbol, module **or test**" and names `test_xml_roundtrip.py`; data-model §6 lists both.
- [x] CHK020 Is there a requirement that the *absence* of a deleted symbol stays asserted over time, rather than being verified once at merge? [Measurability, Spec §FR-018, §FR-020] — FR-018 "its absence must stay asserted"; FR-020 "asserted by a test rather than checked by hand"; T040/T046a/T064/T069.

## Wire-Format Change Evidence

- [x] CHK021 Is "proven changed" defined as automated assertion rather than review, and is the artefact that constitutes the proof named? [Measurability, Spec §SC-004] — SC-004 "proven by round-trip against the corpus"; SC-004a "counted, not reviewed"; C4; T035 names the test file.
- [x] CHK022 Are requirements stated for proving the **old** format absent, not only the new format present? [Completeness, Spec §SC-004, §SC-004a] — SC-004 zero written documents; SC-004a zero occurrences across three repos; T092.
- [x] CHK023 Is the pre-change state specified as a retained artefact, so the round-trip diff has a fixed comparison point that later edits cannot move? [Traceability, Spec §FR-026, Tasks T004] — `pre-state/` at T004, re-taken at T006e after normalisation; C4 measures against it.
- [x] CHK024 Is the permitted diff stated as an exact **set** of differences rather than as a tolerance or an example? [Clarity, Spec §FR-010] — FR-010 "asserted as that exact set rather than waived"; C4; T035.
- [x] CHK025 Are requirements defined for proving the change did **not** reach the other five schemas, with a stated measurement? [Coverage, Spec §FR-010a, §SC-010a] — FR-010a; SC-010a zero golden changes; M1; T012 `test_schema_scope.py`; T026; T093.
- [x] CHK026 Is the mapping from each legacy spelling to each new value specified exhaustively, including the value that maps to itself? [Completeness, Contracts §M3] — M3 and research R8 both tabulate all six input forms; Assumption 9 states `firstrun` → `firstrun` and why it keeps its name.
- [x] CHK027 Can "the element keeps its position" be objectively verified, given element order is derived and a move would silently enlarge the diff? [Measurability, Data-model §1] — data-model §1 states the position and the mechanism: a move enlarges the FR-010 diff beyond two, which C4 asserts as an exact set.

## Migration Failure, Rollback & Recovery

- [x] CHK028 **Are rollback requirements defined for the in-place conversion of `/etc/cuems/network_map.xml`?** No requirement currently mandates a backup, and the file holds operator-assigned aliases and adoption state that exist nowhere else. [Gap, Recovery Flow, Contracts §M3] — **Closed.** FR-011i requires a timestamped backup, a documented restore procedure and no unbounded accumulation; SC-011; M3; T013b/T014b/T054c.
- [x] CHK029 Are requirements defined for downgrade — installing a previous `cuems-common` or `cuems-utils` over a converted file? [Gap, Exception Flow] — **Closed.** FR-011i now states downgrade is unsupported, that restoring the backup is the only path back, and that no reverse conversion is provided; T087b records it in the guide.
- [x] CHK030 Is the operator recovery path specified for a map whose role value the conversion leaves untouched, which then fails validation? The requirements say it fails loudly but not what is done next. [Gap, Recovery Flow, Spec §FR-014, Contracts §M3] — **Closed.** FR-011h-i requires the read to raise the **corresponding named error** carrying document, node, offending value, accepted values and the remedy, plus a **deprecation notice** where the value is a recognisable legacy form — so "old" is distinguishable from "meaningless". T041a/T044a.
- [x] CHK031 Are requirements defined for partial cluster migration — some nodes converted, some not — during a staged rollout? [Coverage, Gap, Spec §FR-030c] — **Closed.** FR-030c now extends the gate to cluster scope and requires the guide to say whether a staged rollout is supported; T087a. The distinction it turns on: FR-030d is a per-node guarantee and a controller upgraded ahead of its nodes is a disagreement no package dependency can see.
- [x] CHK032 Is the failure mode specified for a node where `postinst` runs but the conversion silently no-ops on an unexpected file shape? [Edge Case, Contracts §M3] — M3 gives the full outcome table including absent / already-converted / unparseable, each exit 0 with a diagnostic; T048 tests it.
- [x] CHK033 Are requirements stated for evidence that a conversion ran — a log line, a marker — so an operator can distinguish "already new format" from "never converted"? [Gap, Observability] — **Closed.** FR-011d-i requires positive evidence on success — node count and backup path — and makes all four outcomes (converted / already converted / absent / refused) mutually distinguishable; M3 tabulates them. T013c/T014c.

## Cross-Repository Ordering & Dependency

- [x] CHK034 Is the release gate expressed as an enforceable **package dependency or version constraint**, or only as a documented instruction? A node can upgrade `cuems-utils` before `cuems-common`. [Gap, Spec §FR-030c, Contracts §M5] — **Closed.** FR-030d requires versioned `.deb` dependencies; SC-012 demonstrates the refusal; M5; T054a/T054b.
- [x] CHK035 Are requirements defined for the ordering of `postinst` execution relative to services that read the map at startup? [Coverage, Gap, Spec §FR-011d] — **Closed by assignment to feature 009.** FR-011d-ii defers it explicitly and says why: both the conversion and `dh_installsystemd`'s restart run in `postinst`, but the services doing the reading are `cuems-engine`'s and `cuems-editor`'s, which this feature does not edit. Settling it here would fix an ordering against unmigrated consumers. T053 records it as deferred; M3 carries the note.
- [x] CHK036 Is the obligation on the schema mirror stated as a continuous invariant rather than a one-time copy, given the two files have drifted before? [Clarity, Contracts §M2] — M2 requires a test that fails when they diverge, and says they have drifted before; T049.
- [x] CHK037 Are the branch points and branch names for all three repositories specified precisely enough to be checked at review time? [Measurability, Spec §FR-030a, §FR-030b] — **Closed.** FR-030b now pins `cuems-common` to a new branch from `rc_1` at `0be3506f22de6ea2dd6d20fbd211febe7b26c710`, matching FR-030a's precision for `cuems-nodeconf`. T051.

## Traceability & Evidence Retention

- [x] CHK038 Does every moved or deleted symbol trace to the requirement authorising its movement, rather than to the plan alone? [Traceability, Spec §FR-027] — **Closed.** FR-027 now specifies a fourth column, the authorising requirement, and states that a symbol no requirement authorises is a finding rather than a blank cell; T084.
- [x] CHK039 Is it specified where the migration evidence lives after the branches merge, so feature 009 and any later reader can find it? [Gap, Spec §FR-028] — `specs/007-node-model-migration/migration-guide.md`, a committed file named in plan.md's documentation tree; the convention CLAUDE.md records for feature 006's guide, which 009 consumes.
- [x] CHK040 Is the migration guide's required content enumerated, or does "documented for the migration guide" appear in several requirements meaning different things? [Consistency, Spec §FR-023, §FR-027, §FR-028, §FR-030c] — **Closed.** FR-027a enumerates all seven required contents in one place and requires the feeding requirements to reference it; T083a.
- [x] CHK041 Are the four "must be true when done" claims from the original feature framing each traceable to a numbered requirement? [Traceability] — the framing (`xml-rebuild-07` §6) lists **nine**, not four; all nine trace: → FR-002/002a/002b/005, FR-003, FR-008/009, FR-021, FR-018, FR-017, FR-012/024, FR-016/019, FR-030a.
- [x] CHK042 Do FR-014 ("an unknown role is rejected at validation") and M3 ("an unknown value is left alone by the conversion") together leave a state no requirement resolves — a file the conversion accepts and the schema rejects? [Conflict, Spec §FR-014, Contracts §M3] — **Closed.** FR-011h refuses the file whole and says in terms that it resolves this state; M3 and research R8 both record the change.
- [x] CHK043 Is the guarded free-text field set stated identically everywhere it appears, given one document lists six fields and the pre-migration source listed seven? [Consistency, Spec §FR-012, §FR-024] — the same six (`name`, `ip`, `mac`, `role_id`, `alias`, `hostname`) in FR-012, FR-024, C3, research R4 and data-model §2, each stating why the seventh left.
- [x] CHK044 Is the assumption that `NodeIndex`'s key stays caller-supplied validated against what `cuems-nodeconf` actually needs, rather than asserted? [Assumption, Research §R5] — research R5 is measured against the source and its comment about duplicate controller entries; data-model §3.4 repeats the reason; T074 keeps the MAC key function.
- [x] CHK045 Is "no registration API exists" specified as an ongoing prohibition with a check, or as a statement of the current state? [Clarity, Spec §FR-017] — FR-017 "MUST NOT gain… not reinstated in any form"; C7; T046a makes it a test, distinct from T040's claim.
- [x] CHK046 Is the scope boundary for the Avahi `node_type` TXT record unambiguous — inventoried but unchanged — given it shares a name with the field being renamed? [Ambiguity, Spec Assumption 10, Contracts §M4] — **Closed, and the boundary moved.** The conflict was real: SC-004a demanded zero `node_type` in shipped files while Assumption 10 left four shipped files carrying it, so T092 could not pass. Resolved in two parts — SC-004a now excludes those four files **by name**, and the surface is no longer permanently exempt: Assumption 10, FR-011g, M4 and the Out of Scope entry all now record it as **feature 009's work**, including that `cuems.service.master`/`.slave` carry the retired vocabulary in their **filenames** and that renaming them reaches `debian/install`. T060/T060a inventory and record it; T092 applies the exclusion as an explicit file list.

---

## Notes

- Check items off as completed: `[x]`. A failing item is a **spec defect**, not an implementation defect — fix it by adding or sharpening a requirement, then re-run.
- **CHK028 is the highest-value item in this checklist.** The conversion rewrites an operator's file in place, that file is the only record of node aliases and adoption state, and no requirement currently mandates a backup or a rollback path. It was surfaced by the rollback/recovery sweep the checklist method requires for state-mutating features.
- **CHK034 is the second.** The release gate is stated as documentation (FR-030c) but nothing prevents dpkg from upgrading `cuems-utils` before `cuems-common` on a single node, which is exactly the partially-deployed state the hard cutover has no answer for.
- **CHK042** is a genuine conflict between two documents of this feature, not an ambiguity in one.
- Items with `[Gap]` reference no spec section by design: the point is that no section exists.
- Traceability: 41 of 46 items (89%) carry a spec/plan/research/contract reference or an explicit marker.

---

## Verification results — 2026-08-24

Run against spec.md, plan.md, research.md, data-model.md, `contracts/` and tasks.md as committed
at `6610662`, plus measurement of the three sibling repositories where the item required it.

First pass: **35 pass · 6 partial · 5 gaps.** After two rounds of remediation the same day:
**46 pass · 0 partial · 0 gaps.**

The three items the checklist itself named as highest-value — CHK028 (backup/rollback), CHK034
(enforceable gate) and CHK042 (the conversion/schema conflict) — were already closed at
verification time, by FR-011i, FR-030d and FR-011h respectively, which were added in response to
this checklist and to the `/speckit.analyze` sweep recorded in Clarifications §2026-08-24 (b). The
boxes had simply never been ticked.

### Remediated — five

One was blocking. **CHK046 was a live contradiction between two requirements of this feature**, and
the only finding that made a planned task unachievable as written: SC-004a demanded zero
`node_type` occurrences in shipped files while Assumption 10 deliberately left four shipped
`cuems-common` files carrying it, so T092 could not pass. The resolution went further than the
exemption — the Avahi discovery surface is no longer permanently out of scope, it is **feature
009's work**, named file by file, including the two templates whose *filenames* carry the retired
vocabulary.

| Item | Was | Now |
|---|---|---|
| CHK046 | SC-004a contradicted Assumption 10; T092 unachievable | SC-004a excludes four named files; Assumption 10, FR-011g, M4 and Out of Scope assign them to feature 009; T060/T060a/T092 |
| CHK029 | Downgrade unspecified | FR-011i: unsupported, restore-the-backup is the only path, no reverse conversion; T087b |
| CHK031 | Cluster-scope rollout unaddressed | FR-030c extends the gate past the node; T087a |
| CHK038 | Moved-symbol table had no authorising-requirement column | FR-027 adds it, and makes an unauthorised symbol a finding; T084 |
| CHK017 | Duplicate-named legacy modules' status unstated | FR-018's search names them and requires a per-module answer; T078a |

### Remediated — the remaining six

None was closed by widening a requirement to fit; two were closed by writing down a decision that
had been made but not stated, and one by moving the question to the feature that owns it.

| Item | Was | Now |
|---|---|---|
| CHK008 | Denominator excluded `cuems-nodeconf`'s repo root and `tests/`, unexplained | FR-030a-i: the exclusion is **deliberate** — that code is partially implemented and far from the other repositories' integration maturity — and the node standard with its full testing lives in `cuems-utils` **exclusively**; T006a |
| CHK009 | Semantically-wrong callers covered per-instance by tasks, not as a class | FR-030a-ii names the class and its known members, and requires it to be searched for — nothing fails when a member is missed; T006f |
| CHK030 | The failure state was defined; the operator's next action was not | FR-011h-i: raise the **corresponding named error** with the remedy, plus a **deprecation notice** for a recognisable legacy value; T041a/T044a |
| CHK033 | No positive evidence of a successful conversion | FR-011d-i: node count and backup path on success, four mutually distinguishable outcomes; T013c/T014c |
| CHK035 | `postinst` ordering against the service restart unnamed | FR-011d-ii **defers it to feature 009**, which owns the readers — settling it here would fix an ordering against unmigrated consumers; T053 |
| CHK037 | `cuems-common`'s branch unnamed, no branch point | FR-030b: a new branch from `rc_1` at `0be3506f22de6ea2dd6d20fbd211febe7b26c710`, matching FR-030a's precision; T051 |

### What the two rounds added to the feature

Eleven requirements (FR-011d-i, FR-011d-ii, FR-011h-i, FR-030a-i, FR-030a-ii, plus amendments to
SC-004a, FR-011g, FR-011i, FR-018, FR-027, FR-027a, FR-030b, FR-030c) and nine tasks (T006f, T013c,
T014c, T041a, T044a, T060a, T087a, T087b, plus amendments to T006a, T051, T053, T060, T078a, T084,
T092). Two consequences reach beyond this feature: the Avahi discovery surface and the `postinst`
service-restart ordering both become **feature 009** work, recorded in
`specs/planning/xml-rebuild/xml-rebuild-06-target-design.md` §12 and
`specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md` §7.
