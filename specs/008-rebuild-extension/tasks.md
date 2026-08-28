# Tasks: Rebuild extension

**Feature**: `008-rebuild-extension` | **Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)
**Design inputs**: [research.md](research.md), [data-model.md](data-model.md),
[contracts/public-api.md](contracts/public-api.md), [quickstart.md](quickstart.md)

## How this file is organised, and why it differs from the template

**The D30 phase gate is the top-level structure, not an annotation.** Every task below sits under
**Phase 1 (ITEMs A–D)** or **Phase 2 (ITEM E)**, separated by an explicit, blocking gate task (T083).
This replaces the template's generic Setup / Foundational / per-story layout: user stories are still
the organising unit *within* each phase, but the phase boundary outranks them, because D30 makes it a
hard merge gate rather than a sequencing preference.

**Story → item map** (from spec.md):

| Story | Item | Phase |
|---|---|---|
| US1 | ITEM A — timecode typing, dead-surface deletions | 1 |
| US2 | ITEM B — config write paths | 1 |
| US3 | ITEM C — network-map object | 1 |
| US4 | ITEM D — schema descriptor, `ActionType` narrowing, `create_script` retirement | 1 |
| US5 | ITEM E — strict reading | 2 |
| US6 | ITEM E — version marker and conversion | 2 |
| US7 | ITEM E — repair-and-notify | 2 |

**Tests are included, not optional here.** Constitution Principle II requires fail-then-pass for every
behaviour change, and SC-TEST-001 makes it a success criterion. Test tasks precede their implementation
within each story.

**Suffixed task IDs (`T042a`, `T102a`, …) were added by the `/speckit.analyze` remediation pass**
(2026-08-28) to close coverage gaps without renumbering the tasks the dependency diagrams and the gate
already reference. A suffixed task sits immediately after the task it extends and carries the same
ordering obligations.

**There are no `[P]` markers in this file, by decision.** See §Execution order for the reasoning; the
short form is that the marker was claiming parallel-safety it could not deliver, and this feature has
already given up parallelism everywhere it mattered. FR-056's rule — no Phase 2 task parallel-safe with
a Phase 1 task — still binds; it is now satisfied structurally rather than by annotation.

---

## Phase 1 — ITEMs A, B, C, D

### Setup

- [ ] T001 Re-measure pre-feature load figures on this branch by the method in `quickstart.md` and **research R10**, which pins both the method (median of five warm runs, fresh process) and the fixture: the show document is `tests/data/corpus/cuems-engine/projects/complex_test/script.xml` — the corpus's largest at 24,183 B, **not** `fade_showcase.xml`, on which the ≤ 50 ms absolute cap could never bind. Measure that plus each of the four config domains under **pyenv 3.11.9**, and record in `specs/008-rebuild-extension/baseline.md`
- [ ] T002 Record the current suite figure (`hatch test --show`) in `specs/008-rebuild-extension/baseline.md` and restate FR-PERF-002's three budgets as absolute numbers
- [ ] T003 Copy the pre-change golden and corpus files to `tests/data/corpus/pre-008/` **before any schema edit**, and add a README there naming them as ITEM E's conversion fixtures per FR-011
- [ ] T004 Add a guard test in `tests/contract/test_pre008_corpus_retained.py` asserting `tests/data/corpus/pre-008/` is non-empty and its files **parse — well-formedness only, never schema validation**. This is load-bearing, not pedantry: after T013, T018 and T066 the retained documents are deliberately *invalid* against the current schemas (old duration shape, `fade_profiles`, `fade_in`/`fade_out`), and T080 adds a fixture that is invalid by construction. A guard that validated would go red for exactly the reason the corpus exists (FR-011)
- [ ] T004a Audit every restricted enumeration across all six schemas and record a **per-value verdict table** (value, enumeration, verdict, evidence, date) in `specs/008-rebuild-extension/enum-audit.md`, citing the consumer-repository evidence per value. This runs at Setup rather than in US4's test block because "a value nothing in the system honours" is a judgment over three repositories, not a predicate a test can decide — T059 is written **against this table**, not against the predicate (FR-029b)

---

### US1 — ITEM A: one type and one machinery for every time value (P1)

**Goal**: seven time-carrying elements, one schema type, one setter helper, zero string-stored
exceptions; two dead surfaces deleted.

**Independent test**: load every corpus document with a media duration, assert the value is a
`CTimecode` and not a string, write it back, compare against the re-cut goldens — with no part of
ITEM E present.

#### Tests (write first, must fail)

- [ ] T005 [US1] Test in `tests/unit/test_timecode_typing.py` that exactly seven elements across all six schemas are typed `cms:CTimecodeType` and the count of time-carrying elements typed otherwise is zero (SC-001)
- [ ] T006 [US1] Test in `tests/unit/test_timecode_typing.py` that `Media.duration` yields the same object type as `FadeCue.duration` from load, and that both are indistinguishable in storage (SC-002)
- [ ] T007 [US1] Test in `tests/unit/test_mediacue_duration.py` that a media duration set from `str`, `int`, `dict` and `CTimecode` all produce the same object via the shared helper (FR-002)
- [ ] T008 [US1] Test in `tests/integration/test_duration_wire.py` that XML emits `<duration><CTimecode>…</CTimecode></duration>` and JSON emits `{"CTimecode": "…"}` for media durations (FR-003)
- [ ] T009 [US1] Test in `tests/contract/test_schema_hygiene.py` that `settings.xsd` declares no `CTimecodeType`/`TimecodeType` and `config/settings.py` has no `CTimecodeType`, while the registry coherence check still passes with no exception list (FR-007)
- [ ] T010 [US1] Test in `tests/contract/test_schema_hygiene.py` that `script.xsd` still declares `TimecodeType` and that it remains the inner `<CTimecode>` element's type (FR-008)
- [ ] T011 [US1] Test in `tests/contract/test_schema_hygiene.py` that zero occurrences of the frame-based `HH:MM:SS:FF` form remain as a schema **pattern, default, example or model-class value**. **Exclude explanatory prose**: `src/cuemsutils/tools/CTimecode.py` lines 24, 78, 82 and 242 carry `00:00:00:00` in docstrings describing the wrapped library's frame-1 semantics, and they must survive — a literal grep-and-count returns 4 and fails. Assert against schema text, declared defaults and stored values, not comments (SC-004)
- [ ] T012 [US1] Test in `tests/contract/test_fade_profile_removed.py` that `FadeProfileType`, `FadeProfilesWrapperType`, `FadeParameterType` and the `fade_profiles` element are absent from `script.xsd`, that `FadeProfile`/`FadeFunctionParameter` no longer import, that the five fade-profile rules are unregistered, and that registry coherence still holds (FR-007a)

#### Implementation

- [ ] T013 [US1] Promote `Media.duration` from `cms:TimecodeType` to `cms:CTimecodeType` at `src/cuemsutils/xml/schemas/script.xsd:182`
- [ ] T014 [US1] Collapse `set_duration`'s three-branch type dispatch to `format_timecode` in `src/cuemsutils/cues/MediaCue.py`, and update the class comment at ~`:180` that documents the old typing exception (FR-004)
- [ ] T015 [US1] Remove the now-unreachable `str` branch of the `media_duration` rule in `src/cuemsutils/xml/validators.py` (FR-005)
- [ ] T016 [US1] **Verify before removing**: determine whether `"TimecodeType": _String()` in `src/cuemsutils/xml/adapters.py:227` still resolves for the inner `<CTimecode>` child; remove it with the evidence it was dead, or retain it with the evidence it resolves — record the finding in `research.md`. Completion requires the recorded evidence either way, not a silent pass (FR-006)
- [ ] T017 [US1] Delete `CTimecodeType` and `TimecodeType` from `src/cuemsutils/xml/schemas/settings.xsd` (lines ~132–142) and the `CTimecodeType` class from `src/cuemsutils/config/settings.py` (FR-007)
- [ ] T018 [US1] Delete `FadeProfileType`, `FadeProfilesWrapperType` and `FadeParameterType` from `src/cuemsutils/xml/schemas/script.xsd`, plus the `fade_profiles` element on `AudioCueType` (~`:282`) and `VideoCueType` (~`:319`) (FR-007a)
- [ ] T019 [US1] Delete `src/cuemsutils/cues/FadeProfile.py`, its registry bindings in `src/cuemsutils/xml/registry.py:189/226/227`, its import in `src/cuemsutils/xml/Parsers.py`, and `FadeProfileXmlBuilder` in `src/cuemsutils/xml/XmlBuilder.py` (FR-007a)
- [ ] T020 [US1] Remove `fade_profiles` from `MediaCue` (property, setter, `get_fade_profile`) and from `AudioCue`/`VideoCue` declared defaults (FR-007a)
- [ ] T021 [US1] Delete the five fade-profile rules from `src/cuemsutils/xml/validators.py`: `fade_profile_type`, `fade_profile_mode`, `fade_profile_parameters`, `fade_profile_parameter_value`, `fade_profile_caps`, and retire `tests/unit/test_mediacue_fade_profile.py` and `tests/integration/test_mediacue_fade_roundtrip.py`'s profile assertions (FR-007a)
- [ ] T022 [US1] Record in `specs/008-rebuild-extension/migration-guide.md`, as one entry with two parts: (a) **FR-007b's justification** as a measurement with date and method — zero references to `fade_profile`/`FadeProfile`/`function_id` across the three consumer repositories — so a future reader can re-run it rather than trust it (FR-053c); and (b) **FR-007c's delete-rather-than-rename reasoning** — a `FadeProfile` carries neither `duration` nor `target_value` so it cannot expand into the `FadeCue` the replacement concept needs, and `mode`/`function_id` duplicates `FadeCurveType`; renaming would ship a known-wrong shape under a better name and force a second migration on documents that would by then hold data (FR-007c)
- [ ] T023 [US1] Cut the goldens under `tests/golden/` and `tests/data/corpus/` as a single reviewed commit — **FR-010's first of three recorded events**; verify per `quickstart.md` that every changed line is attributable to FR-003's duration reshape or FR-007a's fade-profile deletion. **The blast radius is small and known, so the diff is bounded rather than merely reviewed**: the duration reshape touches every golden of a document carrying a `<duration>` (six corpus documents plus `generated/create_script.xml`), while the fade-profile deletion touches **exactly one** — `tests/golden/xml/cuems-utils__fade_showcase.xml`, one occurrence, the only document in the tree that carries `fade_profiles`. FR-029a's `ActionType` narrowing touches none: no corpus document carries `fade_in`/`fade_out`. **`tests/golden/generated/` is cut here too**, for the duration reshape alone — `create_script.xml` holds two `<duration>` elements and **no** `fade_profiles` (the module never emitted any) — and is then *replaced* in US4 when its producer changes (**T076**, not T077, which only deletes the module). The third and last event is T102a's `doc_version` renormalisation in Phase 2. Three recorded events, no fourth, none a regenerate-to-pass (FR-010, SC-003, D29)
- [ ] T024 [US1] Update `tests/golden/MANIFEST.sha256` and `tests/golden/outcomes.json` for the cut, and note in the commit body that this is standing rule 3's recorded exception and **the first of FR-010's three golden events** — the other two being T076's generator replacement and T102a's `doc_version` renormalisation

---

### US2 — ITEM B: every configuration domain can persist itself (P1)

**Goal**: `settings`, `project_settings` and `project_mappings` gain a write path symmetric with
`network_map`'s.

**Independent test**: for each domain, load a corpus document, write it back unmodified, compare bytes
against the input normalised to the writer's output form — with no part of ITEM E present.

#### Tests (write first, must fail)

*Normalisation note for T025–T027, decided here rather than in Phase 2: the byte comparison runs against
the input **normalised to the writer's output form**, and that form gains a `doc_version` root attribute
at T102. Write the normaliser to strip/ignore root-level `doc_version` from the outset, so Phase 2 does
not silently redden these three tests (FR-015).*

- [ ] T025 [US2] Round-trip test in `tests/integration/test_config_save.py` for `settings`: load → save → load yields an equal object and a byte-identical document (FR-015)
- [ ] T026 [US2] Round-trip test in `tests/integration/test_config_save.py` for `project_settings` (FR-015)
- [ ] T027 [US2] Round-trip test in `tests/integration/test_config_save.py` for `project_mappings` (FR-015)
- [ ] T028 [US2] Test in `tests/unit/test_config_save_atomicity.py` that an interrupted save leaves the destination holding the complete prior or complete new content, never a truncated document (FR-017, SC-007)
- [ ] T029 [US2] Test in `tests/contract/test_no_routine_backups.py` that a full corpus round-trip across all four config domains produces **zero** backup files (FR-016). This is one of SC-016c's three write paths; the other two — show-document saves and repaired-document saves — cannot be judged here because the repair path does not exist until T121, and are covered by T116a
- [ ] T030 [US2] Test in `tests/contract/test_config_save_parity.py` that all four domains' save surfaces take the same argument shape, the same default-path behaviour and the same failure mode (FR-013)

#### Implementation

- [ ] T031 [US2] Add a shared atomic-write helper (temp file in the destination directory, then `os.replace`) used by every config `save()` in `src/cuemsutils/config/base.py` (FR-017, research R6)
- [ ] T032 [US2] Implement `save()` on the `settings` root object in `src/cuemsutils/config/settings.py`, matching `CuemsNetworkMapType.save`'s contract: validate T1, then build and write; do not mutate the object; write no backup
- [ ] T033 [US2] Implement `save()` on the `project_settings` root object in `src/cuemsutils/config/settings.py`
- [ ] T034 [US2] Implement `save()` on the `project_mappings` root object in `src/cuemsutils/config/mappings.py`
- [ ] T035 [US2] Add `save_settings`, `save_project_settings` and `save_project_mappings` accessors to `src/cuemsutils/tools/ConfigManager.py`, symmetric with `save_network_map` at `:246` (FR-014)
- [ ] T036 [US2] Confirm the landed signatures match `data-model.md` §2 exactly and mark that section as the frozen hand-off interface (FR-018)

---

### US3 — ITEM C: the network map becomes a first-party configuration object (P1)

**Goal**: merge, adopt, unadopt, controller-always-adopted, missing-adopted and signature live where
`network_map.xsd` lives.

**Independent test**: run the characterization tests against the new object and assert outcomes
identical to `CuemsNodeConf`'s current behaviour, before any part of that daemon is edited.

#### Characterization tests (write first, against current daemon behaviour, must fail against an empty implementation)

- [ ] T037 [US3] Characterize `merge_discovered_nodes` in `tests/contract/test_nodeindex_characterization.py` from `cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py:440`, capturing UUID-matching against a MAC-keyed map (FR-021, E23)
- [ ] T038 [US3] Characterize `_map_signature` (`CuemsNodeConf.py:281`) including agreement for reordered but otherwise identical content
- [ ] T039 [US3] Characterize `adopt_node`/`unadopt_node` (`:516`, `:537`) including the controller-unadopt refusal
- [ ] T040 [US3] Characterize `set_master_always_adopted` (`:490`)
- [ ] T041 [US3] Characterize `check_missing_adopted_nodes` (`:501`) with discovery passed as an argument rather than read from a listener
- [ ] T042 [US3] Test in `tests/contract/test_no_nodeconf_imports.py` that the repository has zero imports from and zero runtime dependencies on `cuems-nodeconf` (SC-009)
- [ ] T042a [US3] Test in `tests/contract/test_dispatch_chain_target.py` that the new object is a valid target for the operator's adopt/unadopt chain: enumerate every operation the settings-UI → engine → map chain performs today (`nodelist_modify` → `engine_callback` → the daemon's map mutations) and assert each has a corresponding method on `NodeIndex`/`CuemsNetworkMapType` with equivalent behaviour. The enumeration MUST be recorded in `data-model.md` §5 so a later chain change can be checked against it, rather than living only in the test (FR-022, US3 scenario 6)

#### Implementation

- [ ] T043 [US3] Implement `NodeIndex.merge(discovered)` in `src/cuemsutils/tools/NodeList.py`, matching by `uuid` over the MAC-keyed index (research R7)
- [ ] T044 [US3] Implement `NodeIndex.adopt(node_uuid)` and `NodeIndex.unadopt(node_uuid)` in `src/cuemsutils/tools/NodeList.py`, preserving the controller refusal
- [ ] T045 [US3] Implement `NodeIndex.set_controller_always_adopted()` in `src/cuemsutils/tools/NodeList.py`
- [ ] T046 [US3] Implement `NodeIndex.missing_adopted(discovered)` in `src/cuemsutils/tools/NodeList.py`
- [ ] T047 [US3] Implement `NodeIndex.signature()` in `src/cuemsutils/tools/NodeList.py`, stable over the persisted fields
- [ ] T048 [US3] Implement `CuemsNetworkMapType.refresh(discovered)` in `src/cuemsutils/config/network_map.py`, orchestrating merge → controller → missing and writing only when the signature changed; return whether it wrote (FR-019)
- [ ] T049 [US3] Resolve from T037–T041's results whether `write_network_map`'s `required_fields` filter (`CuemsNodeConf.py:417`) is behaviour to preserve or an artifact; record the answer in `data-model.md` §5
- [ ] T050 [US3] Resolve the `cleanup()` defect at `CuemsNodeConf.py:579` — `self.cm` is never assigned — either as a permitted D16 consumer edit or as a prescribed change recorded in `migration-guide.md` (FR-025)
- [ ] T051 [US3] Write the daemon atomization basis in `specs/planning/nodeconf-atomization.md`: E11's ten-responsibility table, which rows are single-class candidates and why, accounting for the live UI at the end of row 5's dispatch chain and the network_map/project_mappings wire entanglement (FR-023, FR-024)
- [ ] T052 [US3] Add migration-guide entries at call-site granularity for `engine_callback` → `adopt_node`/`unadopt_node` and the `settings.component.ts` → `nodelist_modify` chain (FR-026)

---

### US4 — ITEM D: the schema describes itself, values included (P1)

**Goal**: one descriptor over all six schemas emitting types, cardinality, enumeration values,
model-layer defaults and repairability; `ActionType` narrowed; `create_script` and the hand-written
settings template retired, **with every consumer they leave behind**.

**Independent test**: generate the descriptor and assert per type that the field set equals the
schema's content model, enum values equal the facets, defaults are present as values, and no field is
unclassified — with no part of ITEM E present.

#### Tests (write first, must fail)

- [ ] T053 [US4] Test in `tests/unit/test_descriptor_coverage.py` that the descriptor covers 6 of 6 schemas and every complex type's field set equals the schema's content model (SC-010)
- [ ] T054 [US4] Test in `tests/unit/test_descriptor_enums.py` that every restricted-enumeration field carries values equal to the schema's facets, resolved per schema and never by bare QName (FR-029, research R4)
- [ ] T055 [US4] Test in `tests/unit/test_descriptor_defaults.py` that every field with a model-layer default carries its value, and that `Unset` distinguishes "no default" from a `None` default (FR-030, FR-031)
- [ ] T056 [US4] Test in `tests/unit/test_descriptor_repairability.py` that the count of unclassified fields is zero, that a field with no default classifies unrepairable, and that a rule registered without declaring repairability raises at import (FR-031a, FR-031b, SC-011a, SC-011b)
- [ ] T057 [US4] Test in `tests/unit/test_descriptor_defaults.py` that the two frontend template values — the example `AudioCue`'s `master_vol` and the example `DmxCue`'s `dmx_channels` — are answerable from the descriptor alone (SC-012, E19)
- [ ] T058 [US4] Test in `tests/contract/test_action_type.py` that `ActionType` enumerates 12 values with `fade_in` and `fade_out` absent and `fade_action` present, and that the descriptor publishes exactly those 12 (FR-029a, SC-012a)
- [ ] T059 [US4] Test in `tests/contract/test_enum_audit.py` that every enumeration's facets across the six schemas equal the **retained set of T004a's recorded verdict table**, and that the count of facet values with no verdict recorded against them is zero. The test asserts agreement with the audit artifact — it does **not** itself decide what the system honours, which is a judgment over three repositories and not a testable predicate (FR-029b, SC-012a)

#### Implementation — descriptor and `ActionType`

- [ ] T060 [US4] Add a required keyword-only `repairable: bool` to `register()` in `src/cuemsutils/xml/validators.py`, with no default, and carry it on `Rule` (research R8)
- [ ] T061 [US4] Declare `repairable` on all remaining registered rules in `src/cuemsutils/xml/validators.py`, deciding each on whether substituting the field's default restores a valid state or changes meaning
- [ ] T062 [US4] Create `src/cuemsutils/xml/descriptor.py` with `SchemaDescriptor`, `TypeDescriptor` and `FieldDescriptor` per `data-model.md` §3, taking structure from `spec.derive()` rather than re-walking the XSD (research R3)
- [ ] T063 [US4] Implement enumeration-facet reading in `src/cuemsutils/xml/descriptor.py`, sharing the registry's loaded schema objects and resolving per schema (research R4)
- [ ] T064 [US4] Implement default resolution in `src/cuemsutils/xml/descriptor.py` from the bound model class's `declared_defaults()` via the registry; `GENERIC`-bound types have no defaults and that is recorded as an answer (research R5)
- [ ] T065 [US4] Implement repairability derivation in `src/cuemsutils/xml/descriptor.py` per `data-model.md` §3.1's three ordered rules, with rule 2 outranking rule 1. **Implement §3.1's rule-target join explicitly**: rules target *model class names* (`("VideoCueOutput", "output_name")`) while `TypeDescriptor.key` carries the *XSD type name* (`VideoCueOutputType`), so resolve through the registry's binding table — and **raise on a target that resolves to no `FieldDescriptor`** rather than dropping it, since a silently dropped stale target widens what counts as repairable
- [ ] T066 [US4] Delete `fade_in` and `fade_out` from `ActionType` in `src/cuemsutils/xml/schemas/script.xsd:244-245` (FR-029a)
- [ ] T067 [US4] Note the fade naming collision beside `ActionType` in `src/cuemsutils/xml/schemas/script.xsd`, recording that FR-029a and the fade-profile deletion are separate decisions (FR-029c)
- [ ] T068 [US4] Verify FR-029c's independence claim on a scratch branch: with T018–T021 reverted, T066 alone still applies cleanly and the fade-profile surface stays bound and validated by all five rules. **Measure byte-identity against `tests/data/corpus/pre-008/`, not against `tests/golden/`** — T023 already re-cut the goldens without fade profiles, so they offer no baseline for a reverted-FR-007a tree. Record the result and discard the branch (SC-012c)

#### Implementation — retiring `create_script` and everything it leaves behind

*`create_script` has **18 consumers**, one of which is the golden capture harness itself. Fifteen are
live references — deleting the function without them turns the suite red in fifteen files. The other
**three are prose** (a docstring, a comment, a provenance note): they will not redden anything, but
T079's check is *counted, not reviewed*, so they fail it just the same and the chain stalls at its last
step with the module already gone.*

- [ ] T069 [US4] Inventory every `create_script` consumer and record the list in `specs/008-rebuild-extension/migration-guide.md` before deleting anything: six direct callers (`tests/test_cuelist.py`, `tests/test_xml.py`, `tests/test_fade_cue.py`, `tests/integration/test_mediacue_fade_roundtrip.py`, `tests/integration/test_create_script_completeness.py`, `tests/unit/test_id_clearing.py`), four golden assertions (`tests/integration/test_d14_chain.py:109`, `tests/contract/test_byte_identity_xml.py:53/60`, `tests/contract/test_byte_identity_dict.py:64`, `tests/contract/test_dmx_failure_path.py:135`), two support modules (`tests/support/capture_goldens.py`, `tests/support/invalid_scripts.py`), the slug set in `tests/contract/test_corpus_coverage.py:116`, and the `generated/` entries in `tests/golden/MANIFEST.sha256:29-30` and `tests/golden/outcomes.json`. **Plus three prose-only references**, listed separately because they need updating for T079 but carry no executable dependency: `tests/integration/test_construction_parity.py:9` (module docstring), `tests/unit/test_script_equality.py:38` (comment) and `tests/data/corpus/PROVENANCE.md:38` (provenance note). Eighteen entries in total — record which of the two kinds each is, since only the fifteen can turn the suite red
- [ ] T070 [US4] Implement descriptor-derived template generation in `src/cuemsutils/xml/descriptor.py` replacing `create_script()`; output need not be byte-identical, and the validate-then-blank ordering defect is **not** carried forward (FR-033)
- [ ] T071 [US4] Re-point the four golden assertions at the new generator's output in `tests/integration/test_d14_chain.py`, `tests/contract/test_byte_identity_xml.py`, `tests/contract/test_byte_identity_dict.py` and `tests/contract/test_dmx_failure_path.py`, so the generated-document coverage survives its producer changing
- [ ] T072 [US4] Simplify `tests/support/capture_goldens.py`: `_make_template_writable` exists only to undo `create_script`'s validate-then-blank defect, so it should become unnecessary. Remove it and the `create_script`-specific timestamp/UUID normalisation if the new generator needs none — and if any is still needed, record why, because that would mean the defect survived the supersession (FR-033)
- [ ] T073 [US4] Update `tests/support/invalid_scripts.py`'s `build_generated_script()` base to the new generator, keeping the invalid-document fixtures it derives
- [ ] T074 [US4] Port or retire the six direct callers listed in T069, keeping the coverage each provides — cue-subclass completeness, fade-cue presence, id clearing — against the new generator rather than deleting the assertions
- [ ] T075 [US4] Update the slug set in `tests/contract/test_corpus_coverage.py:116` and the `generated/` entries in `tests/golden/MANIFEST.sha256` and `tests/golden/outcomes.json` to name the new generator
- [ ] T076 [US4] Cut goldens for the new generator under `tests/golden/generated/` and delete `create_script.xml` and `create_script.reader.json`. This is the **replacement** T023 anticipated — the producer changed, so it is not a second re-cut of the same artifact (D29)
- [ ] T077 [US4] Delete `src/cuemsutils/create_script.py` (FR-033)
- [ ] T078 [US4] Generate the settings reference instance from the descriptor, delete `templates/settings.xml`, and remove the hand-maintenance clause from `settings.xsd`'s header (FR-034)
- [ ] T079 [US4] Verify no reference to `create_script` or `templates/settings.xml` remains anywhere in `src/`, `tests/` or packaging metadata — counted, not reviewed. **This includes T069's three prose references** (`test_construction_parity.py`, `test_script_equality.py`, `PROVENANCE.md`): a counted check does not distinguish a docstring from a call, so each must be rewritten to name the descriptor-derived generator instead. If any is deliberately kept — `PROVENANCE.md` is a historical record and may warrant it — the exemption MUST be listed in the check itself, not left as a passing grep that quietly excludes what it should have caught
- [ ] T080 [US4] Build the conversion fixture in `tests/data/corpus/pre-008/fade_actions.xml` carrying `fade_in` and `fade_out` action cues — it must be constructed, since the corpus holds only `fade_action` and `play` (SC-012b)
- [ ] T080a [US4] Build the **all-three-transformations** fixture in `tests/data/corpus/pre-008/script_v1_all_transforms.xml`, carrying an old-shape `<duration>TC</duration>`, an `<action_type>fade_in</action_type>` **and** an `<action_type>fade_out</action_type>`, and a `<fade_profiles>` block. It must be constructed: **no document in the tree holds all three** — `fade_showcase.xml` has a duration and one `fade_profiles` but no fade actions, and T080's fixture has the actions alone. Without it SC-016d has a test (T096) and no subject, and FR-051b's "one version step, three transformations" is unprovable. Hand-author it in the **pre-008 shapes** — like every file under `pre-008/`, it is deliberately invalid against the post-feature schemas, which is why T004's guard parses rather than validates (SC-016d, FR-051b)
- [ ] T081 [US4] Add migration-guide entries at per-call-site granularity for the frontend template call sites. **Enumerate them rather than carrying forward Assumption 7's "~7 across two files", which is unverified**: three files consume the template — `src/app/components/projects/project-edit/sequence/sequence.component.ts`, `src/app/services/projects/handlers/project-create.handler.ts` and `src/app/components/projects/project-edit/project-edit.component.ts`. The two call sites that read **concrete values** (E19, SC-012) are both in the first, and the path must be given in full because a bare `sequence.component.ts` matches two files — the `project-show` one is 238 lines and has neither: `project-edit/sequence/sequence.component.ts:688` (`newCue.master_vol` from the template's CueList) and `:727` (`dmx_channels` from the DMX template). Also add entries for `cuems-engine`'s now-unreachable `_handle_fade_in`/`_handle_fade_out` and their dispatch entries, noting that `_handle_fade_out`'s zombie-process defect disappears with the handler (FR-036, FR-053b)
- [ ] T082 [US4] Confirm the landed descriptor structure matches `data-model.md` §3 exactly, including defaults **and** repairability, and mark that section as the frozen hand-off interface (FR-035)

---

## GATE — Phase 1 complete before any Phase 2 task begins

**This task is blocking. No task numbered above T084 may start until every box below is checked.**

- [ ] T083 Run the full suite green (`hatch test --show`) and record the figure against FR-PERF-002's suite budget in `specs/008-rebuild-extension/baseline.md`
- [ ] T084 **GATE (D30)** — verify and record in `plan.md` that all **five** conditions hold: (a) Phase 1 (T001–T083) is **merged**; (b) the suite is **green**; (c) the config `save()` interface is landed and matches `data-model.md` §2 unchanged; (d) the descriptor interface is landed and matches `data-model.md` §3 unchanged, **including defaults and the repairability classification**; (e) **every Phase 1 acceptance criterion is demonstrated green on a tree containing no part of ITEM E** — which conditions (a) and (b) establish incidentally, but which FR-057/SC-014 require to be *recorded as checked*, since it is the whole claim the phase split rests on. If any interface is still under discussion, stop — the gate exists so Phase 2 is written against landed code, and a negotiable interface means it bought nothing. This is **not** a release boundary: D27 holds and nothing ships until 009 lands.

---

## Phase 2 — ITEM E

*Every task below depends on T084. None is parallel-safe with any Phase 1 task.*

### US5 — ITEM E: a corrupt document can no longer enter the runtime silently (P1)

**Goal**: full validation, T1 and T2, on every read across all six schemas.

**Independent test**: load a document with a known semantic violation through the show surface and
through each config accessor; assert it is detected in every one, where before it was detected in none.

- [ ] T085 [US5] Test in `tests/integration/test_strict_load.py` that a show document violating a semantic rule is detected on load, where it previously loaded silently (FR-037)
- [ ] T086 [US5] Test in `tests/integration/test_strict_load.py` that every `ConfigManager`/`ConfigBase` accessor runs both validation tiers (FR-037, SC-015)
- [ ] T087 [US5] Test in `tests/integration/test_strict_load.py` that a fully valid document loads unchanged with no report, no backup and no conversion
- [ ] T088 [US5] Run T2 inside `CuemsScript.load` in `src/cuemsutils/cues/CuemsScript.py:309` and update its docstring to record the reversal of "reading never becomes stricter" as a decision, naming the principle reversed (FR-038)
- [ ] T089 [US5] Run both tiers in every accessor in `src/cuemsutils/tools/ConfigManager.py` and `src/cuemsutils/tools/ConfigBase.py`
- [ ] T090 [US5] Record in `baseline.md`, beside the measured load figures it qualifies, that four of six schemas carry zero semantic rules and `project_mappings` carries one, so "T2 across six schemas" is mostly plumbing there and the measured cost must not be attributed to enforcement that is not happening. `spec.md` already states this at FR-039 and needs no edit — the gap this closes is that the *numbers* land without the caveat attached (FR-039)

---

### US6 — ITEM E: a document already on disk survives the wire change (P1)

**Goal**: an explicit per-schema version marker, and a conversion that carries this feature's three
`script` transformations at one version step.

**Independent test**: load each retained pre-008 document, assert it converts in memory with its file
untouched, and assert the standalone tool produces the same result idempotently with a backup per
rewritten document.

- [ ] T091 [US6] Test in `tests/contract/test_version_marker.py` that every document written after this feature carries `doc_version` on its root, and that a marker-less document is treated as version 1 rather than malformed (FR-050, SC-023)
- [ ] T092 [US6] Test in `tests/contract/test_version_marker.py` that adding the attribute invalidates **zero** pre-change corpus documents — each still validates without it present (SC-023a)
- [ ] T093 [US6] Test in `tests/contract/test_version_marker.py` that `doc_version` appears in **no** wire projection and on no model class, and that the `project_load` payload is byte-identical to its pre-feature form **modulo FR-003's deliberate duration reshape** — the payload's *only* sanctioned change in this feature. Comparing against the raw pre-feature payload would assert the opposite of FR-003; what Part 2d constrains is that nothing *else* moves it, and in particular that the marker never reaches the wire (research R1, Part 2d, FR-003)
- [ ] T094 [US6] Test in `tests/integration/test_conversion.py` that a pre-008 document converts in memory, loads, and leaves its file on disk **byte-unchanged** (FR-041, SC-016)
- [ ] T095 [US6] Test in `tests/integration/test_conversion.py` that an old document on read-only media still loads — no backup is needed, so none is attempted (FR-041a, SC-016a)
- [ ] T096 [US6] Test in `tests/integration/test_conversion.py` that one `script` version step carries all three transformations on **T080a's fixture** `tests/data/corpus/pre-008/script_v1_all_transforms.xml` — the only document holding all three — asserting one version increment, three transformations, one conversion pass (FR-051b, SC-016d)
- [ ] T097 [US6] Test in `tests/integration/test_conversion.py` that conversion is idempotent and that converted documents validate with durations preserved to the millisecond (SC-017, SC-018)
- [ ] T098 [US6] Test in `tests/integration/test_conversion_tool.py` that the standalone tool backs up each document before rewriting, skips and reports a document whose backup fails, continues with the rest, and never rewrites without a backup (FR-042, SC-016b)
- [ ] T099 [US6] Test in `tests/unit/test_version_steps.py` that a step with an identity conversion loads with bytes unchanged, no backup and no repair, while a newer-than-library marker still raises distinguishably (FR-051d, FR-052, SC-016f)
- [ ] T099a [US6] Test in `tests/contract/test_version_marker.py` that versions move **per schema, not in lockstep**: with `script` at version 2, documents of the other five schemas are neither treated as old nor converted, and their reported version is unchanged. Demonstrated by ITEM A, which moves `script` and must move nothing else (FR-048b, SC-023b, US6 scenario 8)
- [ ] T100 [US6] Add the optional `doc_version` attribute (`xs:positiveInteger`, `use="optional"`) to the root complex type of all six schemas in `src/cuemsutils/xml/schemas/` (FR-048a)
- [ ] T101 [US6] Exclude `doc_version` from attribute derivation in `src/cuemsutils/xml/spec.py:203`, via a named constant beside `SCHEMA_INSTANCE_URI` listing the two attributes the model does not own, with the reason (research R1)
- [ ] T102 [US6] Emit `doc_version` in `build_document` in `src/cuemsutils/xml/mapper.py:977`, beside `xsi:schemaLocation` (FR-053)
- [ ] T102a [US6] **Renormalise every artifact T102 invalidates — FR-010's third and last recorded golden event.** `build_document` is the single funnel every writer in the library goes through, so emitting the marker adds a root attribute to *every* document this library writes. Three consequences, all discharged here rather than discovered as a red suite: (a) re-cut `tests/golden/**` — including `generated/` — as its own reviewed commit whose every changed line is the added `doc_version` attribute and nothing else, and update `tests/golden/MANIFEST.sha256` and `tests/golden/outcomes.json`; (b) confirm T025–T027's normaliser absorbs the attribute as scheduled, so the four config round-trip fixtures still pass unmodified (FR-015); (c) confirm `tests/data/corpus/pre-008/` is **untouched** — it is input, never output, and T004's guard must still pass. Record in the commit body that this is FR-010's third event and that no fourth is sanctioned (FR-010, FR-053, SC-003)
- [ ] T103 [US6] Create `src/cuemsutils/xml/versioning.py` with the pre-validation marker probe: stdlib `ElementTree`, root attribute only, no schema; absent means version 1 (FR-049, research R2)
- [ ] T104 [US6] Implement the conversion registry in `src/cuemsutils/xml/versioning.py` as `(schema, from_version) -> Conversion | None`, walked step by step, with `None` a valid identity step (FR-051d, research R9)
- [ ] T105 [US6] Implement `script` 1→2's three transformations in `src/cuemsutils/xml/versioning.py`: the duration reshape, the `fade_in`→`play` / `fade_out`→`stop` remap, and the reported `fade_profiles` drop (FR-051, FR-051a, FR-051c)
- [ ] T106 [US6] Wire conversion into the load path so an old document converts in memory and the file on disk is not written (FR-041, FR-041a)
- [ ] T107 [US6] Add the `cuems-convert-documents` entry point in `pyproject.toml` and its implementation, sharing the one conversion registry so the rewriter is not built twice (FR-042, SC-019)

---

### US7 — ITEM E: a corrupt-but-current document is repaired and reported (P1)

**Goal**: repair to the descriptor default, report it publicly, raise only when unrepairable.

**Independent test**: load a current-version document with a repairable violation; assert it loads,
the field holds the descriptor default, and the report names document, field, prior and substituted
values.

- [ ] T108 [US7] Test in `tests/integration/test_repair.py` that a repairable violation loads with the field holding the descriptor's default and `outcome == REPAIRED` (FR-043)
- [ ] T109 [US7] Test in `tests/integration/test_repair.py` that a violation in a field the descriptor classifies unrepairable raises `ValidationError` naming document and field, rather than being silently defaulted (FR-044)
- [ ] T110 [US7] Test in `tests/integration/test_repair.py` that both boundary sides are exercised on the same load path, so the repairable/unrepairable boundary is measured rather than assumed (SC-020a)
- [ ] T111 [US7] Test in `tests/contract/test_repair_report.py` that `LoadReport` is importable from `cuemsutils.errors` and answers all five FR-046 questions for every repair the suite produces (SC-021)
- [ ] T112 [US7] Test in `tests/contract/test_repair_report.py` that a clean load returns a report with `outcome == CLEAN` and empty tuples, never `None` (contracts §1)
- [ ] T113 [US7] Test in `tests/contract/test_no_ui_channel.py` that the library gained no notification, messaging or socket channel and no new dependency (FR-047, SC-022)
- [ ] T114 [US7] Test in `tests/contract/test_repair_sources.py` that zero hand-written per-field default fallbacks and zero hand-written unrepairable field-name lists exist, and that every recovered value and every repairable/unrepairable decision traces to the descriptor (FR-045, SC-020)
- [ ] T115 [US7] Test in `tests/integration/test_repair.py` that every element dropped by the fade-profile conversion appears in the report; the count of silently discarded elements is zero (SC-016e)
- [ ] T116 [US7] Test in `tests/integration/test_repair.py` that loading, repairing, saving and re-loading does not produce a second repair report for a field already repaired
- [ ] T116a [US7] Test in `tests/contract/test_no_routine_backups.py` that backups are produced by the schema-upgrade path and by **nothing else**, completing SC-016c's three write paths: T029 counted config saves in Phase 1; this counts **show-document saves** and **repaired-document saves** (the path T121 builds), both of which were unbuildable when T029 ran. The count of backups from all three is zero, counted across the full test corpus rather than argued from the call graph (FR-041b, FR-041c, SC-016c)
- [ ] T117 [US7] Add `LoadReport`, `Outcome`, `RepairRecord` and `ConversionRecord` to `src/cuemsutils/errors.py` and to its `__all__`, per `data-model.md` §4 (FR-046)
- [ ] T118 [US7] Implement the repair path in the load flow: consult the descriptor's repairability, substitute its default, record a `RepairRecord`, continue loading (FR-043, FR-045)
- [ ] T119 [US7] Implement the unrepairable path, raising `ValidationError` with document and field named (FR-044)
- [ ] T120 [US7] Add `CuemsScript.load_with_report()` in `src/cuemsutils/cues/CuemsScript.py`, leaving `load()`'s signature unchanged (contracts §2)
- [ ] T121 [US7] Implement repaired-document saving as an overwrite with **no** backup, and document at the call site that the operator's review of the report is what makes it safe (FR-041c)
- [ ] T122 [US7] Record in `migration-guide.md` that surfacing the repair report is a **precondition** of saving a repaired document, since the overwrite destroys the corrupt original (FR-053a)

---

## Polish & cross-cutting

- [ ] T123 Measure show-document load and each config domain's load by `quickstart.md`'s method; record all figures in `specs/008-rebuild-extension/baseline.md` against FR-PERF-002's three budgets (SC-024)
- [ ] T124 Record the final suite figure and per-test cost; if any budget is exceeded, record it as exceeded with either a mitigation or an explicit approval and rationale — never restate it as passing (SC-024, FR-PERF-002)
- [ ] T125 Complete `specs/008-rebuild-extension/migration-guide.md` so every item with consumer impact has an entry at call-site granularity, and the count of unaccounted impacted call sites is zero (FR-054, SC-025)
- [ ] T125a Record **D3's second through sixth exceptions** in `specs/008-rebuild-extension/migration-guide.md` as one table, per FR-012: each exception scoped to the file and change it names, with its requirement, item, phase, and whether it invalidates documents on disk. State that **three of the five invalidate documents** (the duration promotion FR-002, the `ActionType` narrowing FR-029a, the fade-profile deletion FR-007a) and that each was granted **only** because ITEM E's conversion carries it (FR-051, FR-051a, FR-051c) — the conditionality recorded *with* the exceptions, not separately. State also what the precedent does not license: not X1–X13, not a schema edit in a feature without a conversion path, not anything past this feature; a seventh exception needs its own record (FR-012)
- [ ] T126 Verify no new lint or type warnings, and that every public symbol added carries the rationale documentation the surrounding modules carry (SC-QUALITY-001)
- [ ] T126a Review the two new user-facing surfaces — the repair report's field names and diagnostic text, and the `cuems-convert-documents` tool's output — against the conventions `cuemsutils.errors` and the surrounding modules already use, and record the check. Constitution Principle III is the only principle with no other verification task, and FR-UX-001 exists precisely so a second error vocabulary is not invented alongside the first (FR-UX-001)
- [ ] T127 Verify every requirement with observable behaviour has a test that failed before its implementation and passes after, including the characterization tests demonstrated failing against an empty implementation (SC-TEST-001)
- [ ] T128 Update `CLAUDE.md`'s "Recent Changes" with feature 008's landed content, following 007's entry shape

---

## Dependencies

### Phase order (hard)

```
Setup (T001–T004a)
  └─> US1 ITEM A (T005–T024)
        └─> US2 ITEM B (T025–T036)
              └─> US3 ITEM C (T037–T052, incl. T042a)
                    └─> US4 ITEM D (T053–T082)
                          └─> T083 suite green
                                └─> T084 GATE ══════════ blocking
                                      └─> US5 (T085–T090)
                                            └─> US6 (T091–T107, incl. T099a, T102a)
                                                  └─> US7 (T108–T122, incl. T116a)
                                                        └─> Polish (T123–T128, incl. T125a, T126a)
```

### Why the chain is not re-sequenced (D28)

- **T003 must precede every schema edit.** Re-cutting goldens without retaining the originals destroys
  the only first-party corpus of real old-shape documents — the fixtures US6 converts.
- **US2 before US6**: the upgrade path persists through ITEM B's `save()`.
- **US4 before US7**: repair-to-default reads ITEM D's descriptor and its repairability classification.
- **US1 before US6**: the version marker's first client is the transformation US1 creates.
- **US4's T080 and T080a fixtures before US6**: the `fade_in`/`fade_out` conversion has nothing to
  convert without T080, and SC-016d's one-step-three-transformations test (T096) has no subject without
  T080a. Both are constructed because the corpus cannot supply them — no document in the tree carries a
  fade action, and none carries all three transformations at once.
- **T004a before T059**: the enum test asserts agreement with the audit's recorded verdict table, so the
  table must exist first. This is the one place where an inventory precedes a test rather than the other
  way round, and it is deliberate — the alternative is a test that decides a cross-repository judgment.
- **T102 before T102a, and both after every golden cut**: emitting `doc_version` changes every document
  the library writes, so the renormalisation is scheduled immediately behind the emission. Leaving the
  two apart is how a Phase 2 change silently reddens Phase 1's artifacts.

### The `create_script` retirement chain (within US4)

```
T069 inventory ─> T070 new generator ─> T071 re-point assertions
                                    ─> T072 simplify harness
                                    ─> T073 rebase invalid_scripts
                                    ─> T074 port six callers
                                          └─> T075 manifests + slug set
                                                └─> T076 cut new goldens, delete old
                                                      └─> T077 delete create_script.py
                                                            └─> T079 verify zero references
```

T077 is deliberately late. Deleting the function before its fifteen consumers move turns the suite red
in fifteen files, and a red suite cannot distinguish a real regression from expected fallout.

---

## Execution order

**Every task in this file runs in order. There are no parallel markers.** Removed by decision (repo
owner, 2026-08-28) after `/speckit.analyze` found the marker was not carrying its own weight.

**Why they were dropped rather than redefined.** The file justified keeping *implementation* tasks
sequential because they touch overlapping files — and then marked test tasks `[P]` that write the same
file as each other. Five tasks shared `tests/integration/test_repair.py`; four shared
`tests/contract/test_version_marker.py` and `tests/integration/test_conversion.py`; three shared
`test_strict_load.py`, `test_config_save.py` and `test_schema_hygiene.py`. T001 and T002 both wrote
`baseline.md`, as did T123 and T124. The same criterion was producing opposite answers on either side of
the tests/implementation line, and the surviving genuinely-disjoint groups were two or three files
inside a single story — a marker with nothing left to mark.

**What it costs, stated plainly**: a handful of test files could have been authored concurrently. That
is the whole loss, in a feature that already forgoes cross-item parallelism (D28), already refused the
one clean parallelisation available to it (US3, below), and does not ship independently (D27). One
sequencing rule for the whole file is worth more than an annotation that has to be re-checked against
the file system every time a task is added.

**FR-056 is unaffected.** "No Phase 2 task may be marked parallel-safe with a Phase 1 task" is now
satisfied by construction: nothing is marked parallel-safe with anything, and T084 remains a blocking
gate regardless.

Sequential execution is not a claim that every task is *coupled*. Where two tasks in a story genuinely
touch different files, an implementer running them concurrently breaks nothing. The file simply stops
asserting which those are, because the assertion was wrong often enough to mislead — and the
implementer can see the target paths in the task text either way.

The **hard** ordering constraints are the ones in §Dependencies, and those are unchanged: the phase
gate at T084, T003 before any schema edit, T004a before T059, T102 before T102a, and the
`create_script` retirement chain.

### US3 stays sequential — decided, not merely inherited

`/speckit.optimize` (2026-08-28) found that US3 is the **only** Phase 1 story with no file overlap with
any other: it touches `tools/NodeList.py` and `config/network_map.py` alone, so it is *technically*
parallelizable with US1 and US2. The other three stories are blocked from each other by real file
conflicts regardless of D28.

**Decision: US3 remains sequential** (repo owner, 2026-08-28). The chain is what makes Phase 1
reviewable as one whole, and the gain would have been one story's wall-clock in a feature that does not
ship independently anyway (D27). Recorded here so the finding is not re-raised as though it were new.

`/speckit.optimize` should be read against D28 **and against the removal above**: accept findings that
correct a genuine dependency within a phase; reject any that reorder across the seam, move work earlier
than the item it depends on, or re-propose parallel markers. Both decisions are recorded so neither is
re-raised as though it were new.

---

## Implementation strategy

**There is no MVP-first option here, and that is deliberate.** The template's usual advice — ship
User Story 1 alone as a viable increment — does not apply: D27 establishes that nothing in this
feature ships independently, and the release gate extends through feature 009. The increments are
review units, not delivery units.

**Phase 1 is the first reviewable whole.** Four bounded changes to machinery that already exists,
each judgeable against it. Merge and go green before Phase 2 starts.

**Phase 2 is one new subsystem** whose central mechanism was undesigned until `research.md` R1–R2, and
which is on its own larger than feature 007. It is built against Phase 1's landed interfaces. If it
turns out larger than planned, that is discovered with four items already merged rather than with the
whole feature in flight — which is the gate's real payoff.
