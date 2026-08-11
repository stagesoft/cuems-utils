# Feature Specification: Schema-derived XML serialization core

**Feature Branch**: `004-xml-serialization-core`
**Created**: 2026-08-11
**Status**: Draft
**Input**: Replace the XML serialization machinery in `src/cuemsutils/xml/` with a single schema-derived engine, with zero change to observable serialization behaviour. Derive an ordered, typed field specification from the XSD at load time and drive one encode/decode engine from it, covering all six schemas.

**Planning context** (authoritative, read before planning):
`specs/planning/xml-rebuild-01-audit.md` (findings F1–F23, schema audit X1–X12),
`specs/planning/xml-rebuild-03-design-inputs.md`,
`specs/planning/xml-rebuild-04-object-model.md`,
`specs/planning/xml-rebuild-05-ui-wire-contract.md`,
`specs/planning/xml-rebuild-06-target-design.md` (**the target design**),
`specs/planning/xml-rebuild-07-speckit-prompts.md` §3 (this feature's place in the sequence).

This is feature 1 of 5 in the XML rebuild. It covers phases 1–3 of the target design
(§13) and is a **pure refactor**: zero behaviour changes, success paths and failure paths
alike, and zero breakage for any existing consumer. Every known defect the rebuild closes
that would require a behaviour change is deferred to feature 005 or later. Features
005–008 follow and are out of scope here.

---

## Clarifications

### Session 2026-08-11

- Q: Does 004 remove the catch-all exception handler in the DMX scene builder (F4), or preserve its swallow-and-continue behaviour? → A: **Preserve it.** (This supersedes an earlier answer in the same session that would have removed it. 004 is a pure refactor with **zero** behaviour changes, failure paths included; F4 moves to feature 005 with the other enumerated bug fixes.)
- Q: What happens to the old serialization modules in 004 — deleted, delegating, or shimmed? → A: Deprecated re-export shims that warn on use, removed in 006. Applied uniformly to every affected import path, including the D9 rename (which therefore does **not** break consumers). The shims and their warning messages are the worked examples for the consumer migration in 008.
- Q: What does the regression corpus contain? → A: A frozen copy of all cross-repo XML sources vendored into this repo, plus generated documents for every cue type. XML validation and object conversion belong solely to this repo; feature 008 migrates consumer tests off their own duplicate fixtures where possible.
- Q: Is log output part of the behaviour-preservation guarantee? → A: No — it is the single explicit exclusion. The engine logs one INFO record per document and at most DEBUG per cue, carrying identifiers only, never field values or object reprs. F11 closes here; serialization exactness is guarded by the engine and its tests, not by log archaeology.

---

## User Scenarios & Testing *(mandatory)*

The "users" of this feature are the CUEMS components that read and write show and
configuration documents (`cuems-engine`, `cuems-editor`, `cuems-nodeconf`), the Angular
UI that receives the editor's payload verbatim, and the maintainers of this library.

### User Story 1 - Today's behaviour is frozen before anything moves (Priority: P1)

A maintainer captures exactly what the current machinery produces — written XML bytes and
the dict returned by reading a document — for a fixed corpus of documents, and commits
that capture as an executable test. Only then does any machinery change. When the engine
is later replaced, this test is the thing that says whether the refactor succeeded, and
it never gets edited to make the new code pass.

**Why this priority**: without it, "zero change to observable behaviour" is an assertion
rather than a measurement. Everything else in this feature is unverifiable until this
exists. It is also independently valuable: it ships as a regression net over the current
code even if the rest of the feature were abandoned.

**Independent Test**: generate the golden corpus from unmodified pre-refactor code, commit
it, and run the suite — it passes with no production code changed. The commit history
must show the goldens and the chain test landing before the first engine commit.

**Acceptance Scenarios**:

1. **Given** the unmodified library, **When** the golden corpus is generated and the
   round-trip chain test is run, **Then** the suite passes with zero production-code
   changes in that commit.
2. **Given** a document in the corpus, **When** it is taken through
   XML → object → JSON → object → XML, **Then** the final XML is byte-identical to the
   captured golden and every intermediate representation matches its captured form.
3. **Given** the goldens, **When** any later commit changes written XML or the read dict
   by even one byte, **Then** the suite fails and names the differing document and field.
4. **Given** a maintainer who wants a failing golden test to pass, **When** they
   regenerate the goldens, **Then** the review record shows this is forbidden — goldens
   are produced once from pre-refactor code.

---

### User Story 2 - One engine, and the schema decides the shape (Priority: P2)

A maintainer changes how a show document is serialized in exactly one place. Element
order, scalar type, cardinality and structure are read from the XSD, which already states
all of them. The alphabetical-ordering coincidence, the hardcoded `master_vol` /
`fade_profiles` emit, and the runtime type-guessing heuristic with its key-name denylist
are gone from every live path — surviving only as frozen shims for external callers, on a
scheduled removal. Output does not change.

**Why this priority**: this is the feature. It closes the defect class where element order
is an emergent property of three unrelated files and scalar types are guessed from a
string's appearance.

**Independent Test**: run the P1 chain test and golden comparison against the new engine —
byte-identical XML and byte-identical read dict across the whole corpus — while no live
path reaches the ordering hack or the type-guessing helper, proven by the suite emitting
zero deprecation warnings.

**Acceptance Scenarios**:

1. **Given** an audio cue with fade profiles, **When** it is written, **Then**
   `master_vol` precedes `fade_profiles` because the schema's content model says so, and
   no code compares a field name against a string literal to achieve it.
2. **Given** a model field whose name sorts alphabetically into the wrong position,
   **When** the object is written, **Then** the element still appears in schema order and
   the document validates.
3. **Given** a name, description or file name whose text looks like a number, a boolean or
   `none`, **When** it is read from XML or from an editor JSON payload, **Then** it stays a
   string because the schema declares a string type — not because its key appears on a
   denylist.
4. **Given** any document in the corpus, **When** it is read, **Then** the returned dict is
   byte-identical to the pre-refactor dict, including the repeated-element shape the UI
   depends on.
5. **Given** a cue type present in the schema but not accounted for in the registry,
   **When** the registry is built, **Then** it raises an error naming the unbound type,
   instead of silently falling back to a generic. Types that reach a generic today are
   explicitly bound to that same generic, so no output changes.

---

### User Story 3 - Configuration documents ride the same engine (Priority: P3)

Settings, network map, project mappings, project settings and outputs are read through the
same derived specification as show documents, rather than through a separate reader with
its own decode configuration and its own idea of the resulting shape.

**Why this priority**: the config readers are one of the four duplicated implementations
the feature exists to collapse. Leaving them out would leave two engines and half the
duplication in place.

**Independent Test**: the existing configuration test suites pass unchanged, and the
values each configuration accessor returns are byte-identical to the pre-refactor
captures for the same input files.

**Acceptance Scenarios**:

1. **Given** each of the six schemas, **When** the engine loads it, **Then** an ordered,
   typed field specification is derived for every complex type it declares.
2. **Given** a settings, network-map, project-mappings or project-settings file in the
   corpus, **When** it is read, **Then** every accessor returns exactly what it returned
   before the refactor.
3. **Given** the two different decode configurations in use today, **When** documents are
   read through each, **Then** each configuration's output is preserved exactly as it is
   today, differences included.
4. **Given** the semantic rules the schema cannot express (canvas-region containment, at
   most one custom template per node, media duration), **When** a document violating one
   is processed, **Then** it is rejected exactly as it is today.

---

### User Story 4 - Python and the schema cannot drift apart silently (Priority: P4)

A maintainer adds, removes or renames a field on a model class without making the matching
schema change. The test suite fails immediately and names the class and the offending
field, instead of the mismatch surfacing later as a validation failure or as a field that
silently disappears from saved documents.

**Why this priority**: small to build, permanent in value, and it catches the exact class
of defect that left the node model missing three identity fields the schema declares.

**Independent Test**: temporarily add a field to one model class, run the suite, observe a
targeted failure naming that class and field; remove it and the suite is green again.

**Acceptance Scenarios**:

1. **Given** every model class bound to a schema type, **When** the coherence test runs,
   **Then** it asserts set equality between the fields declared in Python and the elements
   the schema declares for that type.
2. **Given** the coherence test, **When** the fields are declared in a different order from
   the schema, **Then** the test still passes — it compares sets, not order.
3. **Given** a field declared in Python but absent from the schema (or the reverse),
   **When** the suite runs, **Then** it fails and names the class and the field.

---

### Edge Cases

- **Schema-free content**: `ui_properties` is declared as unconstrained content, so no
  type, order or cardinality can be derived for it. It takes the documented fallback —
  insertion order preserved, scalars passed through untyped — and its output does not
  change.
- **Repeated elements**: the current decode shape for repeated elements is transmitted
  verbatim to the Angular UI, so it is a wire contract, not an internal convention. It is
  preserved exactly, including any shape a reviewer might consider wrong.
- **Optional elements**: elements with minimum cardinality zero (e.g. fade profiles) must
  be absent from output when unset and present when set, matching pre-refactor output in
  both cases.
- **Recursive content**: cue lists nest to arbitrary depth through a recursive choice; the
  derived specification must terminate on cyclic type references rather than recursing
  while deriving.
- **Custom scalars**: timecodes and UUIDs are plain restricted strings in the schema and
  cannot be inferred from it; they need explicit adapter rules, and must survive the
  round trip as their Python types rather than as strings.
- **Unfinished structures**: `outputs` and `regions` exist in the schemas but are
  currently reached only by hand-written unwrapping (one schema file is never even
  loaded). They get derived specifications and explicit bindings in this feature; making
  their in-memory representation consistent is a behaviour change and belongs to feature
  005.
- **Documents that are invalid today**: a document the current code rejects must still be
  rejected, and one it accepts must still be accepted. The error need not be worded
  identically, but the accept/reject decision must match.
- **Failure mid-serialization**: today a failure inside DMX scene serialization is logged
  and swallowed, and the write proceeds with a truncated subtree. That is preserved
  verbatim (FR-015a) and quarantined behind a named compatibility behaviour so feature 005
  can remove it. Any other swallowed failure found while building the engine is preserved
  the same way and listed in the plan for 005.
- **Stray keys**: keys present on an object but absent from the schema are emitted (or
  dropped) exactly as they are today; changing that is feature 005.

---

## Requirements *(mandatory)*

### Functional Requirements

**Single source of truth**

- **FR-001**: Element order MUST be derived from the schema's declared content model for
  every complex type in all six schemas. No serialization path may determine element order
  from dictionary iteration order, from alphabetical sorting, or from any hand-maintained
  ordering list.
- **FR-002**: The hardcoded `master_vol` / `fade_profiles` (and `opacity` on video cues)
  ordering exception MUST NOT exist anywhere in the engine — not relocated to another
  module, not re-expressed as a data table. Ordering comes from the schema alone.
- **FR-003**: Scalar types MUST be taken from the schema's declared types. The runtime
  type-guessing heuristic and its key-name denylist MUST NOT be reachable from any live
  serialization path. They survive only as frozen, deprecation-warning shims for external
  callers (FR-026c) and are removed in feature 006.
- **FR-004**: Cardinality (required/optional, single/repeated) MUST be derived from the
  schema rather than restated in Python.
- **FR-005**: One engine MUST produce all three projections — XML, the wire dict, and
  in-memory objects — from the same derived field specification, so that an encode rule
  and its matching decode rule cannot disagree.
- **FR-006**: Field specifications MUST be derived once per (schema, type) and cached.
  Derivation MUST NOT be repeated per object.
- **FR-007**: Binding from schema type to model class MUST be explicit and declared per
  schema, replacing the three implicit name-mangled lookups. A schema type with no binding
  MUST raise an error when the registry is built, not fall back silently. To keep this
  behaviour-preserving, any type that today reaches a generic class through silent
  fallback MUST be explicitly bound **to that same generic class** — registry
  completeness means every type is accounted for, not that every type gains a bespoke
  class. The plan MUST enumerate which types are in that category.
- **FR-008**: Scalar handling that the schema cannot express — timecodes, UUIDs, the
  string-valued boolean type, and the enumerated types — MUST be a small, explicit,
  closed set of adapter rules. Everything else MUST use the schema's own decoding.
- **FR-009**: Unconstrained (`anyType`) content MUST have one documented fallback
  behaviour: insertion order preserved, scalars passed through untyped.

**Byte-identity (the acceptance gate)**

- **FR-010**: Written XML MUST be byte-identical to what the pre-refactor code produces
  for the same object, for every document in the regression corpus.
- **FR-011**: The dict returned by reading a document MUST be byte-identical to the
  pre-refactor dict, including its current repeated-element shape and every key it
  currently carries.
- **FR-012**: Every XML file in the regression corpus MUST load and save with identical
  results; a load-save cycle MUST be idempotent at the byte level.
- **FR-013**: Both decode configurations currently in use MUST be preserved with their
  current outputs, including the differences between them.
- **FR-014**: The repeated-element decode shape MUST be preserved exactly, because it is
  transmitted verbatim to the Angular UI on project load. Booleans MUST remain the strings
  `"True"` / `"False"` on the wire, matching the schema.
- **FR-015**: Accept/reject decisions on document validation MUST match pre-refactor
  behaviour for every corpus document, valid and invalid. No exceptions.
- **FR-015a**: **Failure paths are preserved too.** Where the current machinery swallows a
  serialization failure and lets the write proceed — known instance: the catch-all around
  DMX scene serialization (F4) — the engine MUST reproduce that behaviour exactly for this
  release. It MUST be implemented as a single, explicitly named compatibility behaviour
  carrying its removal target, not as an ambient `except Exception` in the engine's
  general path, and it MUST be covered by a test asserting the current swallow-and-log
  outcome. Removing it is a behaviour change and belongs to feature 005.

**Coverage**

- **FR-016**: All six schemas MUST be covered by the derived specification: show script,
  settings, network map, project mappings, project settings, and outputs.
- **FR-017**: Semantic rules the schema cannot express (canvas-region containment, at most
  one custom template per node, media duration) MUST continue to be enforced, and MUST be
  a named tier distinct from schema-derived validation.
- **FR-018**: `outputs` and `regions` MUST receive derived specifications and explicit
  bindings rather than hand-written unwrapping, with no change to emitted output in this
  feature.

**Tests**

- **FR-019**: A round-trip test covering XML → object → JSON → object → XML MUST exist,
  MUST be written and committed against pre-refactor behaviour before any machinery is
  replaced, and MUST pass unchanged afterwards.
- **FR-020**: A coherence test MUST assert, per model class, set equality between the
  fields declared in Python (accumulated across the class hierarchy) and the elements the
  schema declares for the bound type. Set equality, not order. Its reach is every class
  bound in the registry — which today means the show-document classes, since
  configuration documents have no model classes until feature 006. Config coverage
  arrives with those classes, not here.
- **FR-021**: Golden files MUST be generated once from pre-refactor code and MUST NOT be
  regenerated to make a test pass.
- **FR-022**: The coherence test MUST be proven to fail on an injected Python↔schema
  mismatch before being accepted.
- **FR-022a**: The regression corpus MUST be **vendored into this repository and frozen**.
  It MUST contain, at minimum: this repo's existing fixtures; a copy of the sibling repos'
  XML documents — the engine's per-cue-type samples, its instance of every one of the six
  schema types (including the only existing `outputs.xml`), and its two complete project
  directories; the editor's minimal script fixture; and the network map deployed by
  `cuems-common`. Generated documents covering every cue type MUST be added on top. Each
  vendored file MUST record its provenance, and the corpus MUST NOT be edited or
  refreshed to make a test pass — the same rule as the goldens (FR-021).
- **FR-022b**: The suite MUST be self-contained: no test may depend on a sibling repository
  being checked out, on a path outside this repository, or on the environment having a
  full multi-repo working copy.

**Boundaries**

- **FR-023**: No `.xsd` file may be modified by this feature.
- **FR-024**: No public class, method, signature or return type may change. Objects
  returned, exceptions raised and defaults applied stay as they are.
- **FR-025**: Module files under the XML package MUST be renamed to PEP 8 names in a
  rename-only commit landed **first**, containing no logic changes.
- **FR-026**: **Every** old import path MUST keep working through a deprecation shim. No
  consumer breaks at this release. This is one uniform policy covering all three affected
  categories, which MUST NOT be handled differently from one another:
  - **(a) Renamed modules** — the PEP 8 rename of FR-025 leaves a shim at each old module
    path re-exporting the moved symbols.
  - **(b) Replaced machinery** — the modules whose internals the engine supersedes remain
    importable, exposing the same public symbols with the same behaviour.
  - **(c) Retired helpers** — symbols the engine makes unnecessary, including the
    type-guessing helper and its denylist, remain reachable and behaviourally unchanged
    for external callers.
- **FR-027**: Deprecation shims MUST use one mechanism and one message format across all
  three categories. Each MUST emit a warning naming the symbol being retired, its
  replacement, and the release in which it is removed. A symbol with no direct replacement
  MUST say so and point at the supported entry point instead.
- **FR-028**: The shims are the **migration documentation** for feature 008. Each warning
  message MUST be specific enough to act on without reading the source, and the plan MUST
  produce a table mapping every shimmed symbol to its replacement and to the consumer call
  sites that use it.
- **FR-029**: No library-internal code may call a shimmed symbol. All internal
  serialization MUST route through the engine, and a test MUST assert that importing and
  exercising the library's own paths emits no deprecation warning.
- **FR-030**: Shimmed symbols carry a scheduled removal in feature 006 (or 007 for the
  node-serialization symbols). Retained legacy implementations MUST be frozen — no new
  callers, no new features, no behaviour edits.
- **FR-031**: Hand-written per-class JSON emitters, the object-model unification, the
  public object API, the node model migration and consumer repository edits are **not**
  part of this feature.

**Observability**

- **FR-032**: Log output is the **single explicit exclusion** from the
  behaviour-preservation guarantee. Everything else in this spec is preserved exactly;
  log records are not.
- **FR-033**: The engine MUST emit at most one INFO record per document read or written.
  Per-cue records MUST be DEBUG or lower. No record at any level may contain field values,
  a full object repr, or any document content — identifiers (cue type, uuid) only. This
  closes F11, and removes show content such as names and file paths from log files as a
  side effect.
- **FR-034**: Logging MUST be consistent between the read and write directions; a message
  present on one side and commented out on its counterpart is a defect, not a style
  choice.

**Constitution-mandated**

- **FR-UX-001**: There is no user-facing change in this feature, log output excepted
  (FR-032 to FR-034). This MUST be asserted by test — identical output bytes, identical
  read dicts, identical accept/reject decisions — not assumed.
- **FR-PERF-001**: The feature MUST carry measurable performance budgets before
  implementation, and validate them: full suite runtime and the existing write-performance
  benchmark, both compared against the recorded pre-refactor baseline.

### Key Entities

- **Field specification**: one element of a document type — its name, its declared type,
  whether it is required, whether it repeats, and its position in the content model.
  Derived from the schema; never hand-maintained.
- **Type specification**: the ordered set of field specifications for one schema type,
  plus whether its content is unconstrained and which model class it is bound to. Derived
  once and cached.
- **Adapter**: the rule for one scalar type, covering all three directions — from stored
  text or wire value to Python, from Python to XML text, and from Python to a wire scalar.
  Small and closed; exists only for types the schema cannot express by itself.
- **Registry**: the explicit, per-schema declaration of which model class realizes which
  schema type. Complete by construction; an omission is an error.
- **Regression corpus**: the fixed set of documents used for byte-identity comparison,
  together with the golden captures of their written XML and read dicts, produced once
  from pre-refactor code.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of regression-corpus documents produce byte-identical written XML
  before and after the refactor.
- **SC-002**: 100% of regression-corpus documents produce a byte-identical read dict
  before and after the refactor, including repeated-element shape.
- **SC-003**: A load-save cycle on every corpus document is byte-idempotent.
- **SC-004**: The mapping rules exist in exactly one **live** implementation. Zero live
  code paths determine element order from dictionary iteration or alphabetical sorting,
  and the engine contains zero hardcoded field-name ordering exceptions — verifiable by
  search and by test. Frozen shim code is excluded, and is proven unreachable by SC-012.
- **SC-005**: Zero runtime type guessing on any live path: every scalar's type is
  traceable to a schema declaration, and the heuristic is invoked only if an external
  caller reaches for the deprecated shim directly.
- **SC-006**: A model field declared out of alphabetical position still serializes in
  schema order and validates — demonstrated by a test that fails against the pre-refactor
  code.
- **SC-007**: An injected Python↔schema field mismatch fails the suite with a message
  naming the class and the field.
- **SC-008**: An unbound schema type fails at registry-build time with a message naming
  the type, rather than producing altered output.
- **SC-009**: All six schemas have derived specifications, each exercised by at least one
  real instance document in the corpus; no document type is served by a second, separate
  reader.
- **SC-010**: All 44+ existing type-coercion cases pass, through both the XML path and the
  editor JSON path.
- **SC-011**: Failure paths behave exactly as they do today, including the DMX scene
  swallow-and-log, demonstrated by test — so the refactor is provably behaviour-preserving
  on both success and failure.
- **SC-012**: Exercising every library entry point across the whole corpus emits **zero**
  deprecation warnings, proving no internal caller of shimmed symbols remains.
- **SC-013**: Every old import path still imports successfully, and each emits exactly one
  deprecation warning naming its replacement and its removal release. The existing
  consumer call sites — 12 known across `cuems-editor`, `cuems-engine` and
  `cuems-nodeconf` — continue to work unmodified against this release.
- **SC-014**: Writing a 1000-cue script emits a constant, single-digit number of INFO
  records rather than one per cue, and no log record at any level contains a field value
  or an object repr — verified by capturing log output during the test.
- **SC-015**: The suite passes on a checkout of this repository alone, with no sibling
  repository present.
- **SC-TEST-001**: The round-trip chain test is committed against pre-refactor code, is
  green at that commit, and is green after the swap **without being edited** — provable
  from the commit history.
- **SC-TEST-002**: The full suite passes with no fewer than the baseline 557 tests and
  zero new failures or skips.
- **SC-QUALITY-001**: Lint is clean and no new warnings are introduced.
- **SC-PERF-001**: The write-performance benchmark stays within 10% of the recorded
  pre-refactor baseline, and full-suite runtime stays within 10% of the ~7.4s baseline.
- **SC-PERF-002**: Schema derivation is provably cached — the number of derivations does
  not grow with the number of objects serialized.

---

## Assumptions

1. **Regression corpus — settled.** "Every existing XML file on disk" means the vendored,
   frozen corpus of FR-022a, assembled from four sources: this repo's `tests/data/`; the
   engine's `dev/test_xml_files/` (per-cue-type samples, one instance of each of the six
   schema types, and the `complex_test` / `empty_test` project directories); the editor's
   `tests/fixtures/script_minimal.xml`; and `cuems-common`'s deployed `network_map.xml`.
   Documents generated by the script-creation helper cover the remaining cue types. A
   document type absent from the corpus is not covered by the byte-identity guarantee, so
   the plan must confirm coverage of all six schemas before implementation starts.
1a. **Ownership follows the corpus.** XML validation and object conversion belong solely
   to this repository. Absorbing the corpus is the first half of that consolidation;
   feature 008 is the second, migrating consumer tests off their own duplicate fixtures
   wherever a consumer no longer needs to own one. Consumers keep only fixtures that
   exercise something genuinely theirs.
2. **Byte-identity is a deliberate tightening.** The audit's acceptance list (§4.12) asks
   only for "schema-valid and semantically identical" output. This feature demands
   byte-identity instead, because for a refactor with no intended behaviour change,
   byte-identity is the only cheap and total verification available.
3. **Compatibility — decided, and uniform.** Every old import path survives behind a
   deprecation shim (FR-026 to FR-030), the rename included. **No consumer breaks at this
   release**, and no consumer edit is required until feature 008. The 12 known call sites:
   `cuems-editor` (`CuemsDBProject`, `repair_durations`, one test — `XmlReaderWriter`,
   `CuemsParser`, `NetworkMap`), `cuems-engine` (`BaseEngine`, `ControllerEngine`, two
   tests, one archived file — `XmlReaderWriter`, `NetworkMap`, `ProjectMappings`),
   `cuems-nodeconf` (`CuemsNodeConf`, `NodeXmlBuilders`, two tests — `XmlReader`,
   `XmlWriter`, `GenericCueXmlBuilder`, `GenericParser`, `GenericDict`, `VALUE_TYPES`,
   `str_to_value`, plus the module-globals injection of F8). The `cuems-nodeconf` symbols
   are the deepest coupling and the ones with no direct replacement; their shims must say
   so and point at feature 007's migration.
3a. **Symbols with no successor keep a frozen implementation.** A re-export is only
   possible where a symbol survives under a new name. The builder and parser families that
   the engine supersedes have no successor, so their current implementations are retained
   unchanged, unreferenced by the library, warning on use, and deleted in 006/007. This is
   what makes "pure refactor" literally true, and it matches the target design's phasing,
   which schedules deletion for phase 7 rather than for this feature.
4. **The hand-written field declarations stay.** They keep their two real jobs — layered
   defaults and the alphabetical developer index — and lose only the accidental third one,
   element ordering. The coherence test is what keeps them honest.
5. **The converter stays a subclass.** It is reduced to a thin subclass over the stock
   implementation, keeping only the repeated-element decode override, because that shape
   is the UI contract.
6. **Order derivation is feasible as designed.** Content-model iteration resolving type
   extension in schema order was measured on the audio cue type during design; the plan
   should re-verify it against the pinned library version rather than re-investigate the
   approach.
7. **Timing of the goldens.** The golden corpus and chain test land in their own commit,
   on the pre-refactor code, before the rename commit.

## Dependencies

- The pre-refactor baseline must be green before work starts: 557 passing, plus the
  write-performance benchmark.
- No dependency on the other four rebuild features; 005–008 depend on this one.
- No new runtime dependency is expected; the schema model is already exposed by the
  library in use.
- Read access to `cuems-engine`, `cuems-editor` and `cuems-common` is needed **once**, to
  vendor the corpus (FR-022a). After that the suite is self-contained (FR-022b).
- Feature 008 inherits two follow-ups from the decisions taken here: retiring the
  deprecation shims' consumer call sites, and migrating consumer tests off duplicate
  fixtures now owned by this repo.

## Out of Scope

Public API changes; object-model changes (including making loaded and built objects
type-identical, and typing media regions); any change to serialized output or to the wire
payload; `.xsd` edits; the node model migration from `cuems-nodeconf`; edits in consumer
repositories; the deferred schema items X1–X12.

**Deferred bug fixes.** Every rebuild finding whose fix would change behaviour stays out
of 004 and is carried by a later feature, so that this one remains provably
behaviour-preserving:

| Finding | Deferred to | Why it cannot land here |
|---|---|---|
| F4 catch-all on DMX scene write | 005 | Removing it changes a failure path from silent truncation to a raised error. |
| F12 / F19 media regions never typed | 005 | Changes the in-memory type consumers receive. |
| F16 ids not actually cleared | 005 | Changes generated document content. |
| F17 blanket `AttributeError` swallow | 005 | Changes which fields survive a failing setter. |
| F18 built vs loaded objects diverge | 005 | Changes internal types on the loaded path. |
| F20 two defaulting protocols | 005 | Changes defaults on bare construction. |
| F13 / F21 JSON asymmetry, two UI encodings | 006 | Changes the `initial_template` payload. |
| F23 leaked `schemaLocation` key | 006 | Changes the wire dict, which FR-011 pins byte-identical here. |
| F9 / F10 dead code and no-op guards | 006 | Lives in the frozen shim modules until they are deleted. |
| F7 / F8 nodeconf coercion and globals injection | 007 | Resolved by moving the node model, not by editing this package. |
