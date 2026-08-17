---

description: "Task list for 005 object model unification"
---

# Tasks: Object model unification — one construction path

**Input**: Design documents from `/specs/005-object-model-unification/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/README.md](./contracts/README.md)

**Tests**: REQUIRED by the constitution (principle II). Each of the seven enumerated behaviour
changes needs a test that **fails before** and **passes after**; both outcomes go in the PR.

**Organization**: grouped by user story. Implementation order is US2 → US1 → US3 → US4, which
is *not* spec priority order — see Dependencies for why.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on incomplete work)
- **[Story]**: US1–US4 from spec.md; setup, foundational and polish tasks carry no label
- Paths are repository-root relative

## The three invariants

Every task below is subordinate to these. If one breaks, stop.

1. **`git diff --stat tests/golden/` is empty** — all four golden sets unchanged (C1).
2. **Accept/reject parity, both directions** — the two legacy `output_name` rejections stay
   rejected; nil-UUID payloads stay accepted (C2).
3. **Decode preserves arrival key order** — the root is `xs:all`; sorting it rewrites every
   hand-authored script (C3).

---

## Phase 1: Setup

**Purpose**: capture the "before" state, so the change has something to be measured against.

- [ ] T001 Confirm the suite is green and record the numbers (expect 1251 passed, 43 skipped, ~36.7 s) in `specs/005-object-model-unification/baseline.md`
- [ ] T002 [P] Capture the pre-005 decode measurement for the largest corpus document into `specs/005-object-model-unification/baseline.md` using the command in `quickstart.md` (expect ~36.3 ms), and record the 2× / 75 ms budget derived from it
- [ ] T003 [P] Create `specs/005-object-model-unification/migration-map.md` with one empty section per enumerated behaviour change (7 sections), to be filled as each lands

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the base protocol every story builds on, plus the guards that make later breakage
legible. No behaviour changes here.

**⚠️ CRITICAL**: no user story work begins until this phase is complete.

- [ ] T004a Extract the model class → `TypeSpec` lookup out of `mapper._spec_for_model` (`src/cuemsutils/xml/mapper.py:386-391`) into a **cached** `spec_for_model()` in `src/cuemsutils/xml/registry.py`, and have the mapper call it. It is an O(bindings) scan today, invoked per list item on the encode path — sharing it removes a duplicate resolver *and* helps the C13 budget
- [ ] T004 Create `src/cuemsutils/coercion.py` exposing `adapter_table(cls) -> dict[str, Adapter]`, built on T004a's `spec_for_model()` via **function-local** imports of `cuemsutils.xml.registry` and `cuemsutils.xml.spec`, cached per class (research R1). Do **not** write a second model→spec resolver
- [ ] T005 [P] Write `tests/unit/test_coercion_table.py`, reusing the fixtures and parametrisation style of `tests/unit/test_adapters.py`: the table resolves from the schema for every bound model class, is built once per class (cache-hit assertion), and returns a passthrough adapter for classes with no binding
- [ ] T006 Add the `Unset` sentinel plus `declared_fields()` and `declared_defaults()` classmethods to `CuemsDict` in `src/cuemsutils/helpers.py`, accumulating across the MRO (data-model.md §1)
- [ ] T007 Move the MRO accumulation logic out of `tests/unit/test_coherence.py::declared_fields` into the model, and change that test to import it rather than own it — one definition, used by both
- [ ] T008 Add the `_init_runtime()` hook to `CuemsDict` in `src/cuemsutils/helpers.py` and move the non-persisted attribute initialization of each cue class into its own override (`src/cuemsutils/cues/Cue.py`, `AudioCue.py`, `VideoCue.py`, `ActionCue.py`, `FadeCue.py`, `DmxCue.py`, `CueOutput.py`, `MediaCue.py`) with no change to which attributes are set
- [ ] T009 [P] Write the C12 guard `tests/unit/test_runtime_state.py`: every cue class, from every entry point, arrives with its runtime attributes initialized and none of them appears in `items()`, the XML or either wire projection. **This passes immediately** — it guards what must not be lost
- [ ] T010 [P] Write the C5 harness `tests/integration/test_construction_parity.py`: recursive field-by-field type comparison of built / XML-decoded / JSON-decoded objects for every corpus document. **Must FAIL now**, naming `ui_properties` and `regions`
- [ ] T011 Extend `tests/integration/test_d14_chain.py` with the built-vs-loaded leg, marked `xfail(strict=True)` until US1 lands
- [ ] T012 [P] Write the C13 benchmark `tests/integration/test_construction_performance.py`: decode of the largest corpus document against the T002 baseline (≤2× and ≤75 ms), plus a ≥1000-cue construction benchmark recording a first baseline. Follow the pattern 004 established in `tests/unit/test_spec_cache.py` — assert the **count** of adapter-table builds (one per class, never per object) alongside the timing, because *"a clock measures the machine; a count measures the design"*

**Checkpoint**: suite green, T010 red by design, budgets recorded. Story work can begin.

---

## Phase 3: User Story 2 — The script root stops being a special case (Priority: P1)

**Goal**: one `items()`, one JSON wrapping rule, one base type. The root answers `isinstance`
like every other model object, and stray keys get one outcome instead of two.

**Independent Test**: `isinstance(script, CuemsDict)` is true, exactly one `items()` definition
exists in the model, both payload projections are unchanged apart from stray keys, and a stray
key on the root and on a cue produce the same outcome plus one log record each.

### Tests for User Story 2 (REQUIRED) ⚠️

- [ ] T013 [P] [US2] Write `tests/contract/test_stray_keys.py` (C10): a stray key on the root and on a cue is absent from XML and from JSON, produces exactly one log record naming class and key with **no value**, and a wildcard `ui_properties` subtree is **not** filtered. **Must FAIL now** — the root leaks stray keys today
- [ ] T014 [P] [US2] Write `tests/unit/test_items_single_definition.py`: exactly one `items()` definition in `src/cuemsutils/cues/` and `helpers.py` combined, and `isinstance(CuemsScript(), CuemsDict)` is true. **Must FAIL now** — 10 overrides exist and the root is a plain `dict`

### Implementation for User Story 2

- [ ] T015 [US2] Implement the single `items()` on `CuemsDict` in `src/cuemsutils/helpers.py`, filtered to `declared_fields()`, **built on the existing `extract_items` helper** (`helpers.py:102`) rather than a new one. `Cue.items()` is its only production caller today; reusing it avoids leaving dead code whose removal would drag `tests/test_helpers.py` into the diff and break T048's four-file gate
- [ ] T016 [US2] Remove the `items()` overrides from `src/cuemsutils/cues/Cue.py`, `AudioCue.py`, `VideoCue.py`, `MediaCue.py`, `ActionCue.py`, `FadeCue.py`, `DmxCue.py`, `CueList.py`, `CueOutput.py` — including the hand-ordered variants in `FadeCue.items()` and `CueOutput.items()`, whose ordering job now belongs to the mapper's `TypeSpec`
- [ ] T017 [US2] Change `CuemsScript` to subclass `CuemsDict` in `src/cuemsutils/cues/CuemsScript.py`, deleting its duplicated `setter()` and its `items()` override
- [ ] T018 [US2] Add the declared `JSON_SELF_WRAPS` class attribute and delete the `if k.lower() != k` unwrap heuristic from `CuemsScript.__json__` in `src/cuemsutils/cues/CuemsScript.py`; the emitted payload must not change. **Measured set — six self-wrapping `__json__` implementations**, all identical (`{ClassName: dict(self.items())}`): `Cue` (`Cue.py:313`, inherited by every cue type **and by `CueList`**), `CueOutput` (`CueOutput.py:102`), `Media` (`MediaCue.py:123`), `FadeProfile` and `FadeFunctionParameter` (`FadeProfile.py:56,143`), `DmxCue` (`DmxCue.py:474`). `CuemsScript` is the only `False`. **Exclude `FadeCue.py:21`** — that `__json__` belongs to `FadeCurveType(Enum)` and returns `self.value`; it is a value type, not a model, and must not gain the attribute
- [ ] T019 [US2] Change `mapper._fill` in `src/cuemsutils/xml/mapper.py` to select fields by the declared-field rule **for model objects only**, leaving plain dicts, wildcard subtrees and lists passing through unchanged (research R5). **The model owns the rule**: the mapper asks the object (`obj.declared_fields()`) when it is one, and falls back to `spec.fields` only for generic containers that have no declared set. Deriving the selection independently from `spec.fields` would satisfy FR-015 by coincidence — two rules that agree because the coherence test says so — which is the exact failure mode this feature exists to remove
- [ ] T020 [US2] Emit the drop-and-log record for unrecognised keys (FR-015a) at DEBUG-or-lower per object, and extend `tests/contract/test_logging_budget.py` so the new record cannot push the budget
- [ ] T021 [US2] Checkpoint: run the full suite plus `git diff --stat tests/golden/` — **must be empty**. A moved golden here means the wildcard exemption in T019 is wrong; fix T019, do not touch the golden

**Checkpoint**: the root is an ordinary model object; C1–C4 still green; C10 green.

---

## Phase 4: User Story 1 — A loaded object is the same object as a built one (Priority: P1) 🎯 MVP

**Goal**: coercion runs on every entry point, so built, XML-loaded and JSON-loaded objects have
identical internal types at every field and every depth.

**Independent Test**: T010's comparison reports zero type differences across all three entry
points, with `ui_properties` a `CuemsDict` and `regions` a `list[Region]` everywhere, and no
serialized output changes.

### Tests for User Story 1 (REQUIRED) ⚠️

- [ ] T022 [P] [US1] Write `tests/unit/test_region_coercion.py` (C6): regions supplied as a single mapping, a list of mappings, a list of `Region`s, and the wrapped `{'Region': …}` shape the reader produces all yield `list[Region]` with `in_time`/`out_time` as `CTimecode`. **Must FAIL now**
- [ ] T023 [P] [US1] Write `tests/unit/test_decode_internal_types.py`: decoding one corpus document yields `CuemsDict` for `ui_properties` and typed members throughout, asserted per field path so a failure names the field rather than the document. **Must FAIL now**

### Implementation for User Story 1

- [ ] T024 [US1] Implement `CuemsDict.from_decoded(mapping)` in `src/cuemsutils/helpers.py`: `_init_runtime()`, coercion through the adapter table, **arrival key order preserved**, defaults appended only for fields the document omits (data-model.md §1, research R10)
- [ ] T025 [US1] Replace `_instantiate` with `from_decoded` in `src/cuemsutils/xml/mapper.py`, keeping the repeated-member path's current constructor behaviour so that the two pinned legacy rejections still fire (C2, research R2)
- [ ] T026 [P] [US1] Give `Media` and `Region` declared field sets in `src/cuemsutils/cues/MediaCue.py`: promote the dead `REGION_REQ_ITEMS` to the real one, delete the unused `empty_keys` literal, and remove `set_regions`' discarded loop-variable coercion (change 2)
- [ ] T027 [P] [US1] Give `AudioCueOutput`, `VideoCueOutput` and `DmxCueOutput` declared field sets in `src/cuemsutils/cues/CueOutput.py`, leaving their `__init__` validation untouched (FR-006b)
- [ ] T028 [US1] Bind `UiPropertiesType` so decode yields a `CuemsDict` in `src/cuemsutils/xml/registry.py`, **routing the wildcard coercion through the existing `helpers.as_cuemsdict`** (`helpers.py:38`) — the same recursive wrapper the built path already uses (`Cue.py:287`, `CuemsScript.py:172`), so built and decoded agree *by construction* at every nesting depth rather than by two implementations that happen to match. Update `tests/contract/test_registry_totality.py::test_generic_bindings_are_explicit_not_absent` to assert the new binding
- [ ] T028a [US1] Resolve the never-reached `UI_properties` class in `src/cuemsutils/cues/Cue.py` — adopt it as the `CuemsDict` alias or remove it. **FR-011's "no present-but-unreachable handler" is scoped to this class alone**: the other named case, `mediaParser`, sits below `CuemsParser.parse` in the frozen legacy tree (`src/cuemsutils/xml/Parsers.py:120-122`), which is unreachable by design and removed with the shims. Record that in `migration-map.md`, and settle the carrier — the Parsers docstring says feature **007** while this feature's research and 004's spec say **006**; one of them is wrong and the discrepancy must not survive this feature
- [ ] T029 [US1] Update `tests/unit/test_coherence.py::test_uncovered_classes_are_the_expected_ones` so the uncovered set is empty — coverage 13/18 → **18/18** (research R4)
- [ ] T030 [US1] Make the JSON leg round-trip the unwrapped region shape in `src/cuemsutils/xml/mapper.py` (and the `CuemsParser` facade path), then remove the `xfail` from T011's built-vs-loaded leg; `test_d14_chain`'s `rebuilt == obj` is the gate (research R11)
- [ ] T031 [US1] Update `tests/contract/test_semantic_roundtrip.py` to lift the built-vs-loaded exclusion its docstring defers to this feature
- [ ] T032 [US1] Checkpoint: full suite, `git diff --stat tests/golden/` empty, C2 parity green including the two legacy rejections, and the root key order of a hand-authored document unchanged (C3)

**Checkpoint**: F18, F12 and F19 closed; T010, T022, T023 green; MVP complete.

---

## Phase 5: User Story 3 — Defaults and identifiers behave as written (Priority: P2)

**Goal**: bare construction yields declared defaults for every class, by one protocol; clearing
an identifier clears it.

**Independent Test**: bare-construct all 19 model classes and compare against declared
defaults; build the initial template and assert the fields the code intends to clear are empty.

### Tests for User Story 3 (REQUIRED) ⚠️

- [ ] T033 [P] [US3] Write `tests/unit/test_defaulting_protocol.py` (C9), parametrized over all 19 model classes: bare construction yields that class's declared defaults. **Must FAIL now** — six classes return empty objects (research R3)
- [ ] T034 [P] [US3] Write `tests/unit/test_id_clearing.py` (C7): `script.id = None` and `script.cuelist.id = None` leave the fields empty, and `create_script()` returns a template with no identifiers. **Must FAIL now** — `Uuid(None)` mints a uuid4

### Implementation for User Story 3

- [ ] T035 [US3] Apply the one defaulting protocol to the six classes that return empty today — `Cue`, `CuemsScript`, `Media`, `AudioCueOutput`, `VideoCueOutput`, `DmxCueOutput` — using `Unset` for fields that must stay absent rather than present-and-empty (data-model.md §1)
- [ ] T036 [US3] Write `specs/005-object-model-unification/defaults-audit.md`: one row per newly declared default, its `Unset`-or-value choice, and the output-neutrality evidence (which corpus document proves it emits nothing new)
- [ ] T037 [US3] Make the **uuid-bearing setters only** delegate to the adapter in `src/cuemsutils/cues/Cue.py`, `CuemsScript.py` and `MediaCue.py`, so `None` clears; identifier *generation* stays in the `new_uuid` default, which runs at defaulting time (research R7). **Do not touch `Media.set_duration`**: its field is `TimecodeType`, its getter contract is `str`, and delegating it to a timecode adapter would change the emitted element and break `tests/unit/test_media_duration.py` — see the warning in `data-model.md` §4
- [ ] T038 [US3] Extend `tests/integration/test_create_script_completeness.py` to assert the returned template's cleared state, and confirm `tests/golden/generated/create_script.xml` is untouched because `capture_goldens._make_template_writable` restamps before serialization (research R8)

**Checkpoint**: F20 and F16 closed; one defaulting protocol; goldens still untouched.

---

## Phase 6: User Story 4 — Failures stop being silent (Priority: P3)

**Goal**: an error inside a setter propagates instead of dropping the field; a DMX scene that
cannot be serialized fails the write instead of vanishing from the document.

**Independent Test**: inject a failure inside a setter and inside DMX-scene serialization; both
surface as errors, and no valid corpus document changes.

### Tests for User Story 4 (REQUIRED) ⚠️

- [ ] T039 [P] [US4] Write `tests/unit/test_setter_error_propagation.py` (C8), both halves: a key with **no** setter is still skipped, and an `AttributeError` raised **inside** a setter propagates. **Must FAIL now** on the second half
- [ ] T040 [P] [US4] Invert `tests/contract/test_dmx_failure_path.py` (C11) to assert the write raises with the scene named, and that a healthy scene still emits. **Must FAIL now** — the failure is swallowed today

### Implementation for User Story 4

- [ ] T041 [US4] Narrow the blanket `except AttributeError` in `CuemsDict.setter` to "no such setter" in `src/cuemsutils/helpers.py` — resolve the attribute first, call it outside the guarded block (change 4)
- [ ] T042 [US4] Delete `DmxSceneCompatibility` and `_SwallowAndLog` from `src/cuemsutils/xml/mapper.py`, letting the failure propagate with an error naming the scene, and add **no** ambient `except Exception` in their place (change 7, FR-023)

**Checkpoint**: F17 and F4 closed; all seven behaviour changes landed.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T043 Validate performance against C13: decode ≤2× the T002 baseline and ≤75 ms, suite wall time and write path within 10%, adapter tables built once per class; record the numbers in `specs/005-object-model-unification/baseline.md`
- [ ] T044 Complete `specs/005-object-model-unification/migration-map.md`: all seven changes with before/after and the consumer-visible consequence, plus the standing validation asymmetry recorded as a deliberate carry-over (FR-006b, FR-UX-001)
- [ ] T045 [P] `ruff` clean across the diff; no new warnings in `hatch test` output
- [ ] T046 [P] Docstring pass on every new declaration (`declared_fields`, `declared_defaults`, `Unset`, `JSON_SELF_WRAPS`, `from_decoded`, `_init_runtime`), each stating **why it is declared rather than inferred** — that is the feature's whole argument
- [ ] T047 Run the `quickstart.md` verification block end to end and correct the document if any command or number has drifted
- [ ] T048 Final gate: full suite ≥1251 passing, `git diff --stat tests/golden/` empty, and exactly four pre-existing test files modified (`test_dmx_failure_path.py`, `test_coherence.py`, `test_registry_totality.py`, `test_semantic_roundtrip.py`) — any fifth is a signal to stop and re-read the spec (research R9). The two nearest hazards, both avoidable and both already handled above: `tests/test_helpers.py` (if `extract_items` is orphaned — T015) and `tests/unit/test_media_duration.py` (if `Media.duration` is coerced — T037)
- [ ] T049 Update the `005-object-model-unification` entry in `CLAUDE.md` from "planned" to its landed state, with the post-005 decode measurement that feature 006 inherits as its baseline

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup — **blocks every story**
- **US2 (Phase 3)** and **US1 (Phase 4)**: both need only Phase 2
- **US3 (Phase 5)**: needs Phase 2; T035's `Unset` audit is far easier once US1's decode path
  exists, so it is sequenced after
- **US4 (Phase 6)**: needs Phase 2 only — genuinely independent
- **Polish (Phase 7)**: after all stories

### Why US2 is implemented before US1, despite both being P1

Both change what reaches the writer. Landing them together means a moved golden has two
possible causes. US2 changes *field selection*; US1 changes *field values and types*. Doing
selection first, with C1 green at T021, means any golden movement in Phase 4 is attributable to
construction alone. This is blast-radius isolation, not a dependency — US1 is technically
implementable straight after Phase 2.

### Within each story

- Tests first, and **seen to fail**, before implementation (constitution II)
- Base protocol before the classes that use it
- Model changes before mapper changes
- Checkpoint task last: full suite plus the golden diff

### Parallel opportunities

- T002, T003 together
- T005, T009, T010, T012 together (different test files, all independent of each other)
- T013, T014 together; T022, T023 together; T033, T034 together; T039, T040 together
- T026 and T027 together (different files)
- US4 (Phase 6) can be developed in parallel with US1/US3 by a second person — it touches
  `helpers.py::setter` and `mapper.py`'s compatibility object only

## Parallel Example: User Story 1

```bash
# Tests first, both must fail:
Task: "Write tests/unit/test_region_coercion.py (four supply shapes)"
Task: "Write tests/unit/test_decode_internal_types.py (per-field-path assertions)"

# Then the two independent declaration tasks:
Task: "Declared field sets for Media and Region in src/cuemsutils/cues/MediaCue.py"
Task: "Declared field sets for the three CueOutput subclasses in src/cuemsutils/cues/CueOutput.py"
```

## Implementation Strategy

### MVP

Phases 1, 2, 3 and 4. That delivers the feature's actual claim — a loaded object is the same
object as a built one — with the root unified as its prerequisite. F16, F20, F17 and F4 are
real fixes but none of them is what this feature is *for*.

### Incremental delivery

1. Setup + Foundational → guards in place, budgets recorded, T010 red by design
2. + US2 → root unified, one `items()`, stray keys settled → suite green, goldens untouched
3. + US1 → **MVP**: type identity across all three entry points
4. + US3 → defaults and id clearing behave as written
5. + US4 → silent failures gone

Each step ends with a green suite and an empty `git diff tests/golden/`.

### Commit discipline

Phase 4 (T024, T025) lands in its own commit. It is the change that can rewrite every script
file on disk, and it needs to be revertible on its own. Commits are GPG-signed; retry on "gpg
failed to sign", never `--no-gpg-sign`.

## Notes

- 51 tasks: 3 setup, 10 foundational (T004a added), 9 US2, 12 US1 (T028a added), 6 US3, 4 US4, 7 polish
- Seven behaviour changes → seven fail-then-pass pairs: T022/T023 (change 1, 2), T034 (3),
  T039 (4), T033 (5), T013 (6), T040 (7)
- Only four pre-existing test files may be modified (T048). Goldens: none, ever
- A test that passes before its change is not evidence — record both runs in the PR
