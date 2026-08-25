---
description: "Task list for 004-xml-serialization-core"
---

# Tasks: Schema-derived XML serialization core

**Input**: Design documents from `/specs/004-xml-serialization-core/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/byte-identity.md](./contracts/byte-identity.md)

**Tests**: REQUIRED by the constitution (Principle II), and in this feature the tests *are*
the deliverable — the golden corpus and the D14 chain test are what make "zero behaviour
change" a measurement rather than a claim.

**Environment**: pyenv **3.11.9**. Conda environments are not used for this project.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US4, mapping to the user stories in spec.md

---

## ⚠️ Phase ordering deviates from the template, deliberately

The template puts Foundational before all user stories. **Here US1 comes first.** Goldens
must be captured from *unmodified* code, so the rename and the shims cannot precede them.
Phase 3 (Foundational) therefore sits between US1 and US2, and blocks only US2–US4.

**The single most important rule in this feature**: the goldens and the chain test land in
a test-only commit, green, before one line of machinery moves. They are never edited
afterwards. If a golden fails after the swap, the engine is wrong — not the golden.

---

## Phase 1: Setup — baseline and corpus

**Purpose**: capture what "today" means, before anything can perturb it.

- [X] T001 Record the pre-refactor baseline in `specs/004-xml-serialization-core/baseline.md` by running `hatch test --show` and `pytest tests/integration/test_mediacue_fade_performance.py -v`: suite count, wall time, and write-benchmark numbers. Record the 557 test **ids** too, so the pre-existing subset can be re-run and timed on its own later — SC-PERF-001's 10% rule binds that subset, not the grown total. Leave a placeholder for the new corpus suite's **absolute** budget, filled in at T020 once the corpus is frozen
- [X] T002 Create the vendored corpus tree `tests/data/corpus/{cuems-utils,cuems-engine,cuems-editor,cuems-common}/`
- [X] T003 [P] Vendor this repo's fixtures (`settings.xml`, `network_map.xml`, `project_mappings.xml`, `default_mappings.xml`, `settings_bad_dmx_auto.xml`) into `tests/data/corpus/cuems-utils/`
- [X] T004 [P] Vendor `cuems-engine/dev/test_xml_files/` — the per-cue-type samples, the one instance of each of the six schema types (**including the only `outputs.xml`**), and the `projects/complex_test/` and `projects/empty_test/` directories — into `tests/data/corpus/cuems-engine/`
- [X] T005 [P] Vendor `cuems-editor/tests/fixtures/script_minimal.xml` into `tests/data/corpus/cuems-editor/`
- [X] T006 [P] Vendor `cuems-common/etc/cuems/network_map.xml` into `tests/data/corpus/cuems-common/`
- [X] T006a [P] Vendor **historically-written documents that remain valid under the current schemas** into `tests/data/corpus/legacy/`, recovered with `git show "${tag}:tests/data/<file>"` across the release tags and from the sibling repos' fixture history — measured: `settings.xml` at `v0.1.0rc11` and `v0.1.0rc14` qualify. Compatibility evidence, not archaeology (FR-035d). Note: in zsh, brace the variable — `${t}:path`, not `$t:path`, which zsh parses as a `:t` modifier
- [X] T006b [P] Add documents that no longer validate — measured: `settings.xml` at `v0.1.0rc2` and `v0.1.0rc7`, which predate the required `gradient_osc_port` — to `tests/data/corpus/negative/` as **negative parity cases only**, alongside `settings_bad_dmx_auto.xml`. They are not compatibility obligations; note in `tests/data/corpus/negative/README.md` that they are out of scope per FR-035a and recorded as X13 (FR-035d, FR-015)
- [X] T007 Write `tests/data/corpus/PROVENANCE.md` recording, per vendored file, its origin repo, commit SHA or tag, and date; **pin the total document count per source directory**, so "the corpus" is a fixed number rather than "whatever those directories held" — that number is what SC-PERF-001's new-suite budget is measured against; and reference FR-021 as the authority for the never-refresh rule rather than restating it (FR-022a)
- [X] T008 Add `tests/contract/test_corpus_coverage.py` asserting at least one real instance document exists for each of the six schemas, that no test reads a path outside this repository, and that every corpus document has a corresponding golden so a newly added document cannot silently go uncovered (FR-022b, SC-009, SC-015, SC-016)

**Checkpoint**: corpus is frozen, self-contained, and provably covers all six schemas.

---

## Phase 2: User Story 1 — Today's behaviour is frozen before anything moves (Priority: P1) 🎯 MVP

**Goal**: capture current output as executable goldens, so every later step is verifiable.

**Independent Test**: goldens generate from unmodified code, the suite passes with **zero**
production-code changes in the commit, and `git log` shows this landing before the first
engine commit.

### Tests for User Story 1 (these are the deliverable) ⚠️

- [X] T009 [US1] Build the golden capture harness in `tests/support/capture_goldens.py` — walks the corpus, writes XML bytes and `json.dumps` read dicts under `tests/golden/`, generates **missing** goldens freely so new corpus documents are picked up automatically, and refuses to overwrite an **existing** golden without an explicit force flag (FR-021, SC-016)
- [X] T010 [US1] Capture XML goldens for every corpus document into `tests/golden/xml/` by running the harness against **unmodified** code
- [X] T011 [US1] Capture read-dict goldens into `tests/golden/dict/` for **both** reader configurations — `XmlReaderWriter.read` (`strip_namespaces=False`) and `Settings.read` (`strip_namespaces=True`, explicit `dict`/`list`) (FR-013)
- [X] T012 [US1] Capture goldens for documents generated by `src/cuemsutils/create_script.py` covering every cue type, into `tests/golden/generated/`
- [X] T013 [P] [US1] Contract test C1 — written XML is byte-identical, in `tests/contract/test_byte_identity_xml.py`, asserting element order, attribute order, `<tag />` spelling, the single-quoted `<?xml version='1.0' encoding='utf-8'?>` declaration plus its trailing newline, absence of indentation, absence of a final newline, the root `xsi:schemaLocation`, and non-ASCII written as literal UTF-8 bytes rather than character references (FR-010a); the `xsi:schemaLocation` absolute path is the **one** normalized component (FR-010b)
- [X] T014 [P] [US1] Contract test C2 — the read dict is byte-identical, in `tests/contract/test_byte_identity_dict.py`, compared as `json.dumps` output so that **key insertion order** is inside the guarantee, including the repeated-element shape and the leaked `{…XMLSchema-instance}schemaLocation` key, which must still be present in this feature (FR-011a)
- [X] T015 [P] [US1] Contract test C3 — round-trip stability in `tests/contract/test_roundtrip_stability.py`, asserting `save(load(save(load(x)))) == save(load(x))`, **not** `save(load(x)) == x` (see research R10)
- [X] T015a [P] [US1] Contract test C3a — semantic round-trip in `tests/contract/test_semantic_roundtrip.py`, asserting `load(save(load(x))) == load(x)` for every corpus document; loaded-vs-loaded only, since built-vs-loaded is F18 and belongs to feature 005 (SC-003a)
- [X] T016 [US1] The D14 chain test in `tests/integration/test_d14_chain.py` — `xml → object → json → object → xml`, comparing **every intermediate** against its golden, not only the endpoints (C4). This is the feature's primary gate
- [X] T017 [P] [US1] Contract test C5 — UI payload in `tests/contract/test_ui_payload_contract.py`: booleans are the strings `"True"`/`"False"`, `ui_properties` scalars are strings, `{"CTimecode": …}` wrappers keep their shape, repeated-element shape unchanged
- [X] T018 [P] [US1] Accept/reject parity in `tests/contract/test_accept_reject_parity.py` — record today's outcome for every corpus document, including the deliberately-bad `settings_bad_dmx_auto.xml` and the legacy expected-failure cases, and assert it is unchanged. The engine may never reject what today's parser accepts (FR-015, FR-035a)
- [X] T019 [P] [US1] Failure-path preservation in `tests/contract/test_dmx_failure_path.py` — assert today's swallow-and-log for a DMX scene that fails to serialize, so the behaviour is pinned before the builders are replaced (FR-015a)
- [X] T019a [P] [US1] Public-API snapshot in `tests/contract/test_public_api_surface.py` — capture `cuemsutils.xml.__all__`, the four config classes and `XmlReaderWriter`, with every public callable's `inspect.signature`, into a golden under `tests/golden/api/`, and assert equality. Captured from **unmodified** code like every other golden, so FR-024 is measured rather than reviewed (FR-024, SC-018)
- [X] T020 [US1] Verify the whole phase is test-only: `git diff --stat src/` is empty, `hatch test --show` is green at ≥557 passing, then commit. **Also fill in `baseline.md`'s new-suite budget**: time the corpus/contract/chain tests added in this phase and record the absolute number, before any engine work exists to be tuned against it (SC-PERF-001)

**Checkpoint**: current behaviour is frozen and executable. Everything after this is
verifiable. **Stop here and confirm before proceeding.**

---

## Phase 3: Foundational — rename and deprecation shims (blocks US2–US4)

**Purpose**: land D9 and the compatibility surface, with no logic change.

- [X] T021 `git mv src/cuemsutils/xml/XmlReaderWriter.py src/cuemsutils/xml/xml_reader_writer.py` and update all in-repo imports — no logic changes
- [X] T022 `git mv src/cuemsutils/xml/Settings.py src/cuemsutils/xml/settings.py` and update all in-repo imports — no logic changes
- [X] T023 Update `src/cuemsutils/xml/__init__.py` to import from the new module paths, keeping `__all__` unchanged (`NetworkMap`, `ProjectMappings`, `ProjectSettings`, `Settings`, `XmlReaderWriter`)
- [X] T024 Verify the rename commit is pure: `git show --stat` shows only renames plus import lines, all goldens still pass, suite green. Commit separately (D9)
- [X] T025 Add the shared message template in `src/cuemsutils/xml/_deprecation.py` — **~15 lines, one function returning a configured `@deprecated(...)`, and nothing else**. The mechanism is the already-vendored `deprecated==1.2.18`, which this repo already uses for `XmlReader`/`XmlWriter`; it supplies per-call emission, `extra_stacklevel` and class support natively, so **do not reimplement any of that**. The only thing it cannot supply is FR-027a: its `version=` renders as *"Deprecated since version X"* (`deprecated/classic.py:71-72,151-153`), which is "deprecated since", not "removed in" — so passing `v0.1.1` there would emit a false statement on a shim shipping in `v0.1.0`. The removal release and the replacement pointer therefore go in `reason=`, and this helper fixes that string once instead of at ~20 sites, which is what makes FR-027's "one message format" true by construction rather than by review (FR-027, FR-027a, FR-027b)
- [X] T026 [P] Re-export shim at `src/cuemsutils/xml/XmlReaderWriter.py` pointing to `xml_reader_writer.py`. **Warn per call, not on import**: a bare module-level re-export cannot satisfy FR-027b, so each re-exported class is wrapped so that instantiation and each public method warn at the caller's line (FR-026a, FR-027b)
- [X] T027 [P] Re-export shim at `src/cuemsutils/xml/Settings.py` pointing to `settings.py`, warning **per call** on the same wrapper mechanism as T026, never on import alone (FR-026a, FR-027b)
- [X] T028 [P] Add per-call deprecation warnings to the **frozen** legacy symbols in `src/cuemsutils/xml/Parsers.py` — `GenericDict`, `GenericParser`, `str_to_value`, `STRING_TYPED_KEYS` and the `*Parser` family, which have no successor and point at feature 007's migration. **`CuemsParser` is explicitly excluded**: it stays a supported entry point and does not warn, because it becomes the engine's delegating facade at T048 (FR-026b/c, FR-026d, Assumption 3a)
- [X] T029 [P] Add per-call deprecation warnings to the frozen legacy symbols in `src/cuemsutils/xml/XmlBuilder.py` — `VALUE_TYPES` and the `*XmlBuilder` family, frozen and unreferenced by the library after the swap
- [X] T030 Contract test C9 in `tests/contract/test_deprecation_shims.py` — every old import path (`cuemsutils.xml.XmlReaderWriter`, `.Parsers`, `.XmlBuilder`, `.Settings`, `.CMLCuemsConverter`) imports successfully; every deprecated symbol emits a `DeprecationWarning` **on each call** — asserted by calling twice under `simplefilter("always")` and expecting two records — naming its replacement and `v0.1.1`, reported at the caller's line. Assert `CuemsParser` emits **none** (SC-013, FR-027a/b, FR-026d)
- [X] T031 Produce the shim → replacement → consumer call-site table in `specs/004-xml-serialization-core/migration-map.md`, covering all 12 known call sites across `cuems-editor`, `cuems-engine` and `cuems-nodeconf`. This is a 004 deliverable and the input to feature 008 (FR-028)
- [X] T031a Record the **FR-026d declared breaking change** in `specs/004-xml-serialization-core/migration-map.md`: the symbol (the `globals()` handler lookup in `CuemsParser.get_parser_class` / `XmlBuilder.get_builder_class`), the affected call sites (`cuems-nodeconf/cuemsnodeconf/NodeXmlBuilders.py:96-99` and `test_xml_roundtrip.py:96-99`), and the reason no shim can preserve it — honouring an injected name means keeping the implicit lookup FR-007 deletes. Record any *further* unsupportable call site found during T031 the same way (FR-030a)
- [X] T031b Add the release-notes entry for FR-026d in `CHANGELOG.md`, flagged as a breaking change against the shipping version, naming `cuems-nodeconf` as the sole affected consumer, **naming feature 007 as the carrier of the fix**, and pointing at the migration map. No sibling repository is edited by this feature: the fix must target an API that is internal here, public in 006 and absorbs the node model in 007, so writing it now would produce work rewritten twice (FR-030b scheduling clause)

**Checkpoint**: every old import path resolves and warns per call; `cuems-editor` and
`cuems-engine` are unaffected; the one `cuems-nodeconf` break is declared, flagged and
fixed on its branch; goldens untouched.

---

## Phase 4: User Story 2 — One engine, and the schema decides the shape (Priority: P2)

**Goal**: derive an ordered, typed field spec from the XSD and drive one encode/decode
engine from it, with byte-identical output.

**Independent Test**: C1–C5 all green against the new engine, the chain test passing
**unedited**, and no live path reaching the ordering hack or the type-guessing helper.

### Tests for User Story 2 ⚠️

- [X] T032 [P] [US2] Contract test C10 — upgrade tripwire in `tests/contract/test_xmlschema_tripwire.py`, asserting `content.iter_elements()` still yields `AudioCueType` in the measured order with `master_vol` before `fade_profiles`, so an `xmlschema` upgrade fails loudly instead of silently altering output
- [X] T033 [P] [US2] Unit tests for derivation in `tests/unit/test_spec_derivation.py` — declaration order for `xs:sequence`; **the sorted-key tie-break for `xs:all`** on `CuemsScript` and `DmxSceneType`; cardinality; anonymous-type keying by element path; cyclic `CueListType` terminates (C6, research R2/R3/R8)
- [X] T034 [P] [US2] Contract test C7 — registry totality in `tests/contract/test_registry_totality.py`, proven to fail when a binding is removed
- [X] T035 [P] [US2] Unit tests for adapters in `tests/unit/test_adapters.py` — `BoolType` round-trips to the **strings** `"True"`/`"False"`; `CTimecodeType` wrapper handling; `Uuid`/`TargetType` incl. empty; the six enums; int and float families
- [X] T036 [P] [US2] Ordering-provenance test in `tests/contract/test_ordering_source.py` — `master_vol` precedes `fade_profiles` with no field-name string comparison anywhere in the engine, and a field declared out of alphabetical position still serializes correctly (C6, SC-006; must fail against pre-refactor code)
- [X] T036a [P] [US2] Port the type-coercion corpus onto the **live** paths in `tests/integration/test_type_coercion_live_paths.py` — all 44+ cases from `tests/test_name_coercion.py` (names, descriptions and file names that look like `1`, `n`, `none`, `null`, `true`; the `STRING_TYPED_KEYS` set; the coercing keys `loop`, `master_vol`, `target`, `id`), driven through **both** the XML read path and the editor JSON path, asserting the schema-declared type rather than the heuristic's guess. `tests/test_name_coercion.py` stays as the frozen-shim regression for `str_to_value` itself (SC-010, FR-003)

### Implementation for User Story 2

- [X] T037 [US2] `src/cuemsutils/xml/schema.py` — load and cache the six schemas as separate `XMLSchema11` instances; **per-schema isolation is mandatory**, since `script.xsd` and `outputs.xsd` both declare `OutputsType` in the same namespace with different content (research R4)
- [X] T038 [US2] `src/cuemsutils/xml/spec.py` — `FieldSpec` and `TypeSpec` per data-model §1–2: derivation via `content.iter_elements()`, memoised on `(schema_name, type_key)`, lazy `child_ref` resolution for cyclic models, the `ordered` flag from `content.model`, wildcard and attribute handling
- [X] T039 [US2] Implement FR-001's two-branch ordering rule in `src/cuemsutils/xml/spec.py` per data-model §2.1 — declaration order when `ordered`, sorted-key tie-break when the model group is `all`. Keyed off the content model, never off a type name, and with sorted-key ordering reachable from nowhere else (FR-001a)
- [X] T040 [US2] `src/cuemsutils/xml/adapters.py` — the adapter table from data-model §3, bound by type qname and covering complex types (`CTimecodeType`) as well as simple ones
- [X] T041 [US2] Instrument the current `globals()` lookups in `Parsers.py` and `XmlBuilder.py` over the whole corpus, recording every silent miss, and write the resulting list of types-that-reach-a-generic to `specs/004-xml-serialization-core/generic-bindings.md` (~13 expected; plan open item 1)
- [X] T042 [US2] `src/cuemsutils/xml/registry.py` — per-schema binding by type qname **or** element path (for the anonymous `CuemsProject`/`CuemsScript` types), with every type from T041 bound explicitly to the same generic it reaches today, and a build-time error naming any unbound type (FR-007)
- [X] T043 [US2] `src/cuemsutils/xml/converter.py` — the D5 thin `XMLSchemaConverter` subclass keeping only the repeated-element decode override, importing **only public** `xmlschema` API (today's fork reaches into `xmlschema.validators.wildcards.Xsd11AnyElement`)
- [X] T044 [US2] Re-export shim at `src/cuemsutils/xml/CMLCuemsConverter.py` pointing to `converter.py`, warning **per call** on the T025 wrapper mechanism, never on import alone (FR-027b)
- [X] T045 [US2] `src/cuemsutils/xml/mapper.py` — `decode` / `encode_xml` / `encode_wire` per data-model §5, driven by `TypeSpec` order, one `Adapter` on both sides, wildcard fallback preserving insertion order and untyped scalars
- [X] T046 [US2] Add the named DMX-scene compatibility behaviour in `src/cuemsutils/xml/mapper.py` reproducing today's swallow-and-log, carrying its feature-005 removal target — **not** an ambient `except Exception` in the general path (FR-015a)
- [X] T047 [US2] **The swap**: route `src/cuemsutils/xml/xml_reader_writer.py` through the mapper, keeping the stdlib `ElementTree` writer and every public signature unchanged
- [X] T048 [US2] Point `CuemsParser` in `src/cuemsutils/xml/Parsers.py` at the engine as a delegating facade — same signature, same return objects, no deprecation warning — so `cuems-editor`'s five call sites in `CuemsDBProject.py` and `repair_durations.py` keep working with identical results. Note this is **not optional given T047**: `XmlReaderWriter.write_from_dict` and `read_to_objects` already call `CuemsParser`, so the two are one swap, not two (FR-026d, Assumption 3a)
- [X] T049 [US2] Confirm the ordering hack in `XmlBuilder.py` — the `if key == 'master_vol' or (key == 'opacity' and cls_name == 'VideoCue')` branch, cited by symbol because T021–T024 shift line numbers — and `str_to_value`/`STRING_TYPED_KEYS` are unreachable from any live path, frozen in the shim modules only (FR-002, FR-003)
- [X] T049a [US2] Contract test C11 in `tests/contract/test_declared_break_nodeconf.py` — assert the FR-026d break **explicitly**, so it is pinned rather than incidental: injecting a handler class into `Parsers`/`XmlBuilder` module globals (reproducing `NodeXmlBuilders.py:96-99`) is **not** consulted by the engine, the import and the assignment still execute without error, and the engine's registry resolves the type instead. The test names FR-026d and the migration map in its docstring (SC-017)
- [X] T050 [US2] Verify C1–C5 are green and `tests/integration/test_d14_chain.py` passes **with no edits since T016** — confirm via `git log -p tests/integration/test_d14_chain.py`. Also confirm `tests/contract/test_public_api_surface.py` (T019a) is still green and unedited (SC-018)

**Checkpoint**: one engine drives show-document serialization, byte-identically.

---

## Phase 5: User Story 3 — Configuration documents ride the same engine (Priority: P3)

**Goal**: settings, network map, project mappings, project settings and outputs served by
the same derived specification.

**Independent Test**: existing configuration suites pass unchanged and every accessor
returns byte-identical values against the pre-refactor captures.

### Tests for User Story 3 ⚠️

- [X] T051 [P] [US3] Accessor parity tests in `tests/contract/test_config_parity.py` — every `Settings`, `NetworkMap`, `ProjectMappings` and `ProjectSettings` accessor returns exactly its pre-refactor value for each corpus file
- [X] T052 [P] [US3] Reader-configuration test in `tests/contract/test_reader_configs.py` — both decode configurations preserved with their current outputs, **differences included** (FR-013)

### Implementation for User Story 3

- [X] T053 [US3] Route `Settings`, `NetworkMap`, `ProjectMappings` and `ProjectSettings` in `src/cuemsutils/xml/settings.py` through the engine, preserving each class's public surface
- [X] T054 [US3] Register the remaining five schemas in `src/cuemsutils/xml/registry.py` with explicit bindings, `outputs.xsd` isolated in its own registry with root `CuemsOutputs` (D13, research R4)
- [X] T055 [US3] Extract the semantic rules the schema cannot express — canvas-region containment, ≤1 custom template per node, media `duration` — into a named T2 validator tier in `src/cuemsutils/xml/validators.py`, kept explicitly separate from schema-derived T1 validation (FR-017)
- [X] T056 [US3] Give `outputs` and `regions` derived specifications and explicit bindings in `src/cuemsutils/xml/registry.py`, replacing the hand-written unwrapping in `src/cuemsutils/xml/Parsers.py` (`mediaParser`, the commented-out `regionsParser`) and `OutputsXmlBuilder` in `src/cuemsutils/xml/XmlBuilder.py`, with **no change** to emitted output in this feature (FR-018, D13)

**Checkpoint**: all six schemas on one engine; no second reader remains.

---

## Phase 6: User Story 4 — Python and the schema cannot drift apart silently (Priority: P4)

**Goal**: a test that fails when a model class and its schema type disagree.

**Independent Test**: add a field to one model class, observe a targeted failure naming the
class and field; remove it and the suite is green again.

**Note**: this story depends only on `spec.py` (T038), not on the mapper — see Dependencies.

- [X] T057 [US4] Coherence test in `tests/unit/test_coherence.py` — per registry binding, assert **set equality** between `REQ_ITEMS` keys accumulated across the MRO and `TypeSpec` field names. Sets, not order (FR-020)
- [X] T058 [US4] Prove `tests/unit/test_coherence.py` fails on injected drift: temporarily add a field to `REQ_ITEMS` in `src/cuemsutils/cues/AudioCue.py`, confirm a targeted failure naming the class and field, then revert (FR-022, SC-007)
- [X] T059 [US4] Resolve any real drift the test uncovers — by correcting the Python declaration or by binding to the right type, **never** by editing a `.xsd` (FR-023)

**Checkpoint**: Python↔schema drift is caught automatically.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T060 Logging pass in `src/cuemsutils/xml/mapper.py` and `src/cuemsutils/xml/xml_reader_writer.py` — **INFO declared at the XML file access level** (file read, write, validate); element construction, object building and all per-cue work at DEBUG or lower; identifiers only, never field values or object reprs; consistent between read and write directions (FR-033, FR-034, closes F11)
- [X] T061 [P] Logging budget test in `tests/contract/test_logging_budget.py` — INFO count scales with files touched, not cues: a 1000-cue script (one file) stays in single digits, internally built elements and objects emit nothing above DEBUG, and no record at any level carries a field value or object repr (SC-014)
- [X] T062 [P] Contract test C8 in `tests/contract/test_no_internal_deprecation.py` — running the full corpus through the library's own entry points emits **zero** deprecation warnings, proving no internal caller of a shimmed symbol remains. The entry points include the editor's JSON path via `CuemsParser`, which is exercised here precisely because it is supported and must therefore stay silent (SC-012, FR-029)
- [X] T063 Performance validation against `specs/004-xml-serialization-core/baseline.md`, in three parts (SC-PERF-001): write benchmark within 10% of baseline; the **pre-existing 557 tests**, re-run as a subset by the ids recorded at T001, within 10% of ~7.4s; and the new corpus suite within the absolute budget fixed at T020. Do **not** apply the 10% rule to the grown total — SC-TEST-002 requires the count to grow, so that comparison is meaningless
- [X] T064 [P] Derivation-count assertion in `tests/unit/test_spec_cache.py` — number of `TypeSpec` derivations is bounded by distinct types and does not grow with object count (SC-PERF-002)
- [X] T065 [P] `ruff check src/cuemsutils/xml/ tests/` clean and no new warnings from `hatch test --show`; the frozen shim modules `Parsers.py` and `XmlBuilder.py` are exempt from new-code quality work and may be excluded explicitly in `pyproject.toml`. **Declare the one expected-warning exemption**: `tests/test_name_coercion.py` calls the now-deprecated `CuemsParser.str_to_value` ~40 times by design, so add a scoped `filterwarnings` entry (or a marker on that file) under `[tool.pytest.ini_options]` — scoped to that file and that warning, never a global `ignore::DeprecationWarning`, which would also hide the warnings T030 and T062 depend on (SC-QUALITY-001)
- [X] T066 [P] Record the new deferred items in `specs/planning/xml-rebuild/xml-rebuild-01-audit.md` §6 — `outputs.xsd`'s colliding `OutputsType` (R4), `DmxUniverseType`'s attribute/element `universe_num` name clash (R7), **X13** `gradient_osc_port` required without `minOccurs="0"` (recorded only — out of scope per FR-035a, no fix scheduled), and a pointer to the **schema evolution convention** adopted in feature 006 (`specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md` §5.1, §9 rules 7–8), and **F24** the absolute `schemaLocation` path with its feature-006 relative-path fix
- [X] T066a [P] Add a compatibility contract test in `tests/contract/test_legacy_compatibility.py` asserting that every document in `tests/data/corpus/legacy/` — historical but still schema-valid — loads, and that the engine rejects nothing today's parser accepts (FR-035a, FR-035b, FR-035d)
- [X] T066b [P] Extend `tests/contract/test_legacy_compatibility.py` with the **`schemaLocation` form matrix**: take one corpus document and produce three variants — absolute path, relative path, attribute removed — and assert all three load with equal results. This is what makes feature 006's relative-path change (F24) safe on the read side, so it is evidenced here rather than assumed there (FR-035c, SC-019)
- [X] T067 [P] Update `CHANGELOG.md` with the deprecations and their removal release, the **FR-026d breaking change** entry from T031b, and the log-output change as the one intentional non-breaking behaviour difference
- [X] T068 Run the `specs/004-xml-serialization-core/quickstart.md` validation sequence end to end and confirm every gate listed there passes

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)** — no dependencies.
- **Phase 2 (US1)** — depends on Phase 1. **Must complete before any production code
  changes.** This inverts the template's ordering, deliberately.
- **Phase 3 (Foundational)** — depends on US1. Blocks US2–US4.
- **Phase 4 (US2)** — depends on Phase 3.
- **Phase 5 (US3)** — depends on US2 (needs the mapper).
- **Phase 6 (US4)** — depends only on **T038** (`spec.py`), not on the mapper.
- **Phase 7 (Polish)** — depends on US2 and US3; T062 additionally on Phase 3.
- **No task in this feature edits another repository.** The FR-026d fix is carried by
  feature 007 (FR-030b's scheduling clause), so every task here runs against a checkout of
  this repository alone — which is what keeps FR-022b and SC-015 true without
  qualification. What 004 owes is the *declaration*: T031a (migration map), T031b
  (`CHANGELOG.md`) and T049a (the C11 assertion), all in-repo. FR-030c layer (ii) — the
  release-time review of the call-site inventory against each sibling — remains a
  checklist step outside the suite, and it is what will hand 007 its input.

### The one non-obvious unblocking

US4 is P4 by priority but becomes available as soon as `spec.py` lands at T038. With more
than one person, start T057–T059 in parallel with T040–T050 rather than waiting — it is
cheap, permanent, and may surface drift that changes registry bindings while those are
still in flight.

### Within each user story

- Tests before implementation. For the byte-identity contracts this is inverted and
  stated: they pass by construction at T013–T019 and must **keep** passing — that is the
  refactor gate.
- Derivation (T038) before adapters (T040) before registry (T042) before mapper (T045).
- The swap (T047) last, after every supporting piece is independently green.

### Parallel opportunities

- **Phase 1**: T003–T006b all parallel (different directories).
- **Phase 2**: T013–T015a and T017–T019a parallel (different test files) once T010–T012
  have produced the goldens.
- **Phase 3**: T026–T029 parallel (different modules) once T025 exists; T031, T031a and
  T031b are documentation and parallel to all of them.
- **Phase 4**: T032–T036a parallel; then T037–T040 largely sequential by dependency.
- **Phase 7**: T061, T062, T064–T067 all parallel.

---

## Parallel Example: Phase 2 contract tests

```bash
# after T010-T012 have written the goldens, launch together:
Task: "Contract test C1 byte-identical XML in tests/contract/test_byte_identity_xml.py"
Task: "Contract test C2 byte-identical dict in tests/contract/test_byte_identity_dict.py"
Task: "Contract test C3 round-trip stability in tests/contract/test_roundtrip_stability.py"
Task: "Contract test C5 UI payload in tests/contract/test_ui_payload_contract.py"
Task: "Accept/reject parity in tests/contract/test_accept_reject_parity.py"
Task: "DMX failure path in tests/contract/test_dmx_failure_path.py"
```

---

## Implementation Strategy

### MVP scope

**Phases 1–2 (T001–T020).** That is a genuine, shippable increment: a frozen corpus and a
golden-plus-chain-test regression net over the current code, delivered without touching
production source. It has standalone value even if the engine were never built, and it is
the precondition for building it safely.

### Incremental delivery

1. Phases 1–2 → regression net in place → **commit, stop, validate**.
2. Phase 3 → rename plus shims → consumers still green → commit.
3. Phase 4 → the engine and the swap → byte-identity contracts green → commit.
4. Phase 5 → config schemas on the engine → commit.
5. Phase 6 → drift protection → commit.
6. Phase 7 → logging, performance, docs → release.

Each step leaves the suite green and the goldens untouched.

### Exit criteria for the feature

Suite green at ≥557 passing; C1–C11 all green; the chain test and the API snapshot provably
unedited since T016/T019a; performance within all three budgets; `ruff` clean; every old
import path still resolving and warning per call; zero deprecation warnings from the
library's own paths; and the one declared breaking change (FR-026d) named in the migration
map, flagged in `CHANGELOG.md` with feature 007 named as the carrier of its fix, and
asserted by C11. **No file outside this repository is touched.**

---

## Notes

- Commits are GPG-signed. Retry on "gpg failed to sign"; never `--no-gpg-sign`.
- Never regenerate a golden to make a test pass (FR-021). The harness at T009 requires an
  explicit force flag precisely to make that deliberate rather than accidental.
- No `.xsd` edits in any task (FR-023, D3). Schema defects are recorded at T066 and
  deferred. Note FR-023 is the no-`.xsd`-edits boundary; the read-compatibility
  requirements are **FR-035/FR-035a–d**, renumbered from the colliding FR-023a–d.
- Every behaviour-changing bug fix — F4, F12, F16–F20, F13/F21, F23 — belongs to features
  005–007, not here. See the deferred table in spec.md. **F8 splits**: the break happens
  here and is declared here (FR-026d, T031a/T031b/T049a); the `cuems-nodeconf` fix is
  carried by feature 007.
- `cuems-nodeconf` is the only consumer affected by that break, and it is not shipping
  against this release. `cuems-editor` and `cuems-engine` need no edit at this release.
- **This feature edits no repository but this one.** If a task seems to require a sibling
  checkout for anything beyond the one-time corpus vendoring (T004–T006), it is wrong.
