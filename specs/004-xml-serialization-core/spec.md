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

### Session 2026-08-11 (analyze follow-up)

- Q: Is `CuemsParser` a deprecated shim or a supported entry point? Measured: it is already
  library-internal (`XmlReaderWriter.write_from_dict` and `read_to_objects` both call it),
  it is `cuems-editor`'s primary JSON→object path at **5 call sites**, and its
  `get_parser_class` resolves through `globals()` of `Parsers.py` — which is exactly the
  hook `cuems-nodeconf` monkey-patches (`NodeXmlBuilders.py:96-99`). → A: **Everything
  routes through the engine.** `CuemsParser` becomes a delegating facade over the engine
  and stays a supported entry point. The consequence is that nodeconf's globals injection
  stops resolving; that is accepted as a **declared breaking change** (FR-030a/FR-030b),
  not a silent one — see FR-026a and the declared-breaking-change subsection.
- Q: `cuems-nodeconf` is the only consumer that breaks. Does that violate Assumption 3's
  "no consumer breaks at this release"? → A: **Assumption 3 gains one named exception.**
  `cuems-nodeconf` is already an out-of-date repository whose serialization work lives on
  the unlanded `feat/nodeconf-reenable` branch, so it is not shipping against this release
  in the first place. The break is absorbed there rather than on `main`.
- Q: How does the coordinated sibling fix (FR-030b) ship, given feature 007 was gated on
  `feat/nodeconf-reenable` landing on `main` first? → A: **The gating is inverted, and the
  fix moves to 007.** `feat/nodeconf-reenable` does **not** land on `main` beforehand;
  feature 007 works from that branch and carries the nodeconf fix there.
- Q: Should feature 004 itself land the nodeconf fix, so the flag and the fix travel
  together as FR-030b requires? → A: **No — 004 touches this repository only.** The fix
  has to target the engine's registry, which is internal in 004, becomes public API in
  006, and absorbs the node model in 007; written now it would be rewritten twice. Since
  `cuems-nodeconf` is not shipping against this release, deferring costs nothing and saves
  throwaway work. FR-030b gains a narrow scheduling clause: the declaration, the
  release-note flag and the SC-017 test all still land in 004 — **only the sibling edit
  moves**, and the flag names 007 as its carrier.
- Q: Is `save(load(x)) == x` (FR-012 as originally worded) achievable? → A: **No —
  FR-012 restated.** Research R10 measured that the first save normalizes indentation and
  rewrites `schemaLocation`, so first-cycle identity is false even for library-written
  files. FR-012 now matches SC-003 and contract C3: identical from the first save onward.
- Q: Can the full suite stay within 10% of the 7.4s baseline while this feature adds a
  ~30-document corpus driven through 14 new test files? → A: **No — SC-PERF-001 split.**
  The 10% rule binds the pre-existing suite and the write benchmark; the new corpus suite
  carries its own absolute budget.

### Session 2026-08-11 (checklist follow-up)

- Q: How is non-ASCII content encoded on write? → A: UTF-8, as literal bytes, never character references (FR-010a). Verified: `ElementTree` with `encoding='utf-8'` already does this, and the corpus contains non-ASCII.
- Q: How is byte-identity of the read dict compared, and is key order part of it? → A: Comparison is `json.dumps` output, because that is how library classes and consumers use the dict; key insertion order is therefore inside the guarantee (FR-011a).
- Q: What release removes the deprecated symbols? → A: `v0.1.1`. `v0.1.0` keeps the warnings (FR-027a).
- Q: Are deprecation warnings per-import or per-call? → A: Per call, with correct `stacklevel` (FR-027b).
- Q: May new corpus documents be added after the goldens are captured? → A: Yes — new documents are expected, permitted and recognised automatically. The no-regeneration rule binds **existing** goldens only (FR-021).
- Q: FR-001 forbids alphabetical ordering, but order-free (`xs:all`) content models require a sorted-key tie-break to preserve bytes. → A: **FR-001 amended.** Two schema-driven branches: declaration order for ordered models, sorted-key tie-break for order-free ones. Alphabetical sorting is permitted only in that declared branch (FR-001, FR-001a, SC-004). Resolves the conflict that previously lived only in `research.md` §R2.
- Q: What happens if a consumer call site cannot be kept working? → A: It becomes a **declared** breaking change — named, flagged in the release notes, recorded in the migration map, and shipped together with the corresponding sibling-repository modifications. Never silent (FR-030a, FR-030b). Compatibility is verified in two layers so SC-013 and FR-022b no longer conflict (FR-030c). **Refined by the analyze-follow-up session above**: "shipped together" became "prepared **or explicitly scheduled**", so that a fix which a later feature would invalidate can name its carrier instead of being written twice. The declaration, the flag and the test still ship in the release that causes the break — only the sibling edit may move.
- Q: Would `load(save(x)) == x` (object comparison) resolve the SC-003 conflict, given that file bytes could be altered by a minifier or a future SQL-based whole-XML store? → A: **Added as SC-003a, not as a replacement.** Measured: the object property holds today, and it is the guarantee that survives reformatting and storage layers. But it is **blind to element reordering within order-free content models** — an `xs:all` root emitted in a different order loads to an equal object, so object equality alone would not have caught the R2 defect that rewrites every script root. Byte-identity stays as the refactor's evidence (SC-003 restated as stability); object equality is added as the durability guarantee.
- Q: Is the absolute `schemaLocation` path tunable, or forced by the schema toolchain? → A: **Entirely our own code** — one line in the builder; `xmlschema` neither writes nor reads it. Measured: documents validate and read with the path absolute, relative, namespace-only, or the attribute removed. **Decided: feature 006 emits a relative path**, coordinated with dropping the leaked key so the wire change happens once.
- Q: Must the rebuild keep loading previously written XML files? → A: Yes across all of 004–008, but **scoped to the current XSD configuration** (FR-035, FR-035a–d). Any document valid under today's schemas must load, and reading may never become stricter. Documents that no longer validate because the schema evolved — measured: settings files predating the required `gradient_osc_port`, **X13** — are out of scope by policy, not defects to fix. Historical documents that *do* still validate stay in the corpus as evidence.
- Q: At what altitude does INFO logging sit? → A: INFO is declared at the **XML file access** level; internally built elements and objects log at DEBUG or lower (FR-033, SC-014).

### Session 2026-08-11

- Q: Does 004 remove the catch-all exception handler in the DMX scene builder (F4), or preserve its swallow-and-continue behaviour? → A: **Preserve it.** (This supersedes an earlier answer in the same session that would have removed it. 004 is a pure refactor with **zero** behaviour changes, failure paths included; F4 moves to feature 005 with the other enumerated bug fixes.)
- Q: What happens to the old serialization modules in 004 — deleted, delegating, or shimmed? → A: Deprecated re-export shims that warn on use, removed in 006. Applied uniformly to every affected import path, including the D9 rename (which therefore does **not** break consumers). **Partly superseded by the analyze-follow-up session above**: `CuemsParser` is delegating rather than shimmed, and the F8 globals injection is a declared break rather than a preserved behaviour. The shims and their warning messages are the worked examples for the consumer migration in 008.
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
  every complex type in all six schemas. The rule has **two branches, both schema-driven**,
  selected by the content model itself and never by a type name:
  - **Ordered content models** (`xs:sequence`, `xs:choice`) — emit in the schema's
    **declaration order**. Authoritative.
  - **Order-free content models** (`xs:all`) — the schema explicitly declares that no
    order is imposed, so there is no declaration order to honour. The engine applies one
    **documented deterministic tie-break: sorted keys**, which is what the current code
    produces and therefore preserves the output bytes.

  Honouring the schema includes honouring its statement that order is unconstrained.
  Imposing declaration order on an order-free model would be a behaviour change, not
  fidelity: measured, it rewrites the root element of **every script file on disk**.
  Exactly two types are affected across all six schemas — the anonymous `CuemsScript` root
  type and `DmxSceneType`.
- **FR-001a**: No serialization path may determine element order from dictionary iteration
  order or from any hand-maintained ordering list. Alphabetical sorting is permitted
  **only** as the declared tie-break for order-free content models under FR-001, and is
  forbidden for ordered ones.
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
- **FR-010a**: Output encoding MUST be UTF-8. Non-ASCII content MUST be written as
  **literal UTF-8 bytes**, never as numeric character references. The corpus contains
  non-ASCII content, so this is a live property of the guarantee rather than a formality.
- **FR-010b**: **The written `xsi:schemaLocation` contains a machine-dependent absolute
  filesystem path** to the bundled `.xsd` — measured, and reproduced verbatim from the
  current writer. Byte comparison of **written output** MUST therefore normalize that
  attribute's path component to a stable placeholder, so goldens reproduce across
  machines, checkouts and CI. Everything else is compared unnormalized. The normalization
  applies wherever a library-written document is compared or re-read, which includes the
  chain test's intermediates; read dicts taken from corpus files are unaffected, because
  their values come from the files themselves.

  The value is written by this library's own builder and is **not** imposed by the schema
  toolchain. Measured: documents validate and read correctly with the path relative,
  namespace-only, or the attribute removed entirely. It is therefore freely changeable —
  but changing it alters the read dict (F23) and so the UI payload, which is why 004
  reproduces today's form and defers the fix.
- **FR-011**: The dict returned by reading a document MUST be byte-identical to the
  pre-refactor dict, including its current repeated-element shape and every key it
  currently carries.
- **FR-011a**: The read dict MUST remain compatible with `json.dumps`, because that is how
  the library's own classes and its consumers serialize it. Byte-identity for the dict is
  therefore defined as **equality of its `json.dumps` output**, which makes **key
  insertion order part of the guarantee** — `json.dumps` is order-sensitive, so two dicts
  that compare equal may still serialize differently.
- **FR-012**: Every XML file in the regression corpus MUST load and save with identical
  results **from the first save onward**: `save(load(save(load(x)))) == save(load(x))`.
  Idempotence is a property of the serializer's own output, **not** of arbitrary input —
  `save(load(x)) == x` is measurably false today for hand-authored files, which are
  indented and may declare `version="1.1"`, and for library-written files, whose
  `schemaLocation` is rewritten with the writing machine's absolute path (research R10).
  This requirement, SC-003 and contract C3 state one property; they must not drift apart.
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
- **FR-021**: A golden file, once captured, MUST NOT be regenerated to make a test pass.
  This is an invariant on **existing** goldens, not a freeze on the corpus: new corpus
  documents are expected over time, MUST be permitted, and MUST be recognised
  automatically. The capture tooling MUST therefore distinguish the two cases —
  generating a **missing** golden freely, and refusing to overwrite an **existing** one
  without an explicit, deliberate override.
- **FR-022**: The coherence test MUST be proven to fail on an injected Python↔schema
  mismatch before being accepted.
- **FR-022a**: The regression corpus MUST be **vendored into this repository and frozen**.
  It MUST contain, at minimum: this repo's existing fixtures; a copy of the sibling repos'
  XML documents — the engine's per-cue-type samples, its instance of every one of the six
  schema types (including the only existing `outputs.xml`), and its two complete project
  directories; the editor's minimal script fixture; and the network map deployed by
  `cuems-common`. Generated documents covering every cue type MUST be added on top. Each
  vendored file MUST record its provenance. **FR-021 is authoritative for the
  never-refresh rule and binds the corpus exactly as it binds the goldens**; it is not
  restated here, so the two cannot drift.
- **FR-022b**: The suite MUST be self-contained: no test may depend on a sibling repository
  being checked out, on a path outside this repository, or on the environment having a
  full multi-repo working copy.

**Boundaries**

- **FR-023**: No `.xsd` file may be modified by this feature.
- **FR-024**: No public class, method, signature or return type may change. Objects
  returned, exceptions raised and defaults applied stay as they are. This MUST be
  **asserted by test** — a snapshot of the public surface (`__all__`, the config classes
  and `XmlReaderWriter`, with each callable's `inspect.signature`) captured before the
  swap and compared after — not left to review. The public *surface* is unchanged
  without exception; the one behavioural exception is carried by FR-026d.
- **FR-025**: Module files under the XML package MUST be renamed to PEP 8 names in a
  rename-only commit landed **first**, containing no logic changes.
- **FR-026**: **Every** old import path MUST keep working through a deprecation shim.
  Every consumer **import** resolves at this release, and every consumer that depends only
  on the documented public behaviour of those symbols keeps working. This is one uniform
  policy covering three affected categories (FR-026a to FR-026c), which MUST NOT be
  handled differently from one another — plus one named, declared exception, FR-026d:
- **FR-026a**: **Renamed modules** — the PEP 8 rename of FR-025 leaves a shim at each old
  module path re-exporting the moved symbols.
- **FR-026b**: **Replaced machinery** — the modules whose internals the engine supersedes
  remain importable, exposing the same public symbols with the same behaviour.
- **FR-026c**: **Retired helpers** — symbols the engine makes unnecessary, including the
  type-guessing helper and its denylist, remain reachable and behaviourally unchanged for
  external callers.
- **FR-026d**: **One declared breaking change, and only one: the F8 module-globals
  injection.** `CuemsParser.get_parser_class` and `XmlBuilder.get_builder_class` resolve
  handler classes through `globals()` of their own module, and `cuems-nodeconf` writes
  into those globals to register its node handlers
  (`NodeXmlBuilders.py:96-99`: `ParsersModule.nodeParser = nodeParser`). Once every path
  routes through the engine's explicit registry (FR-007), an injected name is never
  consulted. **No shim can preserve this**: the injection point is a private module
  namespace, and honouring it would reintroduce exactly the implicit name-mangled lookup
  FR-007 exists to delete. It is therefore a **declared** breaking change under FR-030a,
  not a silent one, and is subject to FR-030b's coordinated-bump rule. The affected
  imports still resolve and the injected assignment still executes without error — what
  changes is that it no longer affects serialization, which is precisely why it must be
  declared rather than left to be discovered.
- **FR-027**: Deprecation shims MUST use one mechanism and one message format across all
  three categories. Each MUST emit a warning naming the symbol being retired, its
  replacement, and the release in which it is removed. A symbol with no direct replacement
  MUST say so and point at the supported entry point instead.
- **FR-027a**: **The removal release is `v0.1.1`.** `v0.1.0` ships the shims with their
  warnings intact. Every warning message MUST name `v0.1.1` explicitly — a version a
  consumer can act on, not an internal feature identifier.
- **FR-027b**: Warnings MUST be emitted **per call**, not once per import, so that a
  consumer still routing production traffic through a deprecated entry point keeps seeing
  it. Warnings MUST carry a correct `stacklevel` so the report points at the **caller's**
  line rather than at the shim. Note that Python's default warning filter may still
  collapse repeats at a given call site; the requirement is on what the library **emits**,
  which is the part the library controls.
- **FR-028**: The shims are the **migration documentation** for feature 008. Each warning
  message MUST be specific enough to act on without reading the source, and the plan MUST
  produce a table mapping every shimmed symbol to its replacement and to the consumer call
  sites that use it.
- **FR-029**: No library-internal code may call a shimmed symbol. All internal
  serialization MUST route through the engine, and a test MUST assert that importing and
  exercising the library's own paths emits no deprecation warning.
- **FR-030**: Shimmed symbols are removed in **`v0.1.1`** (FR-027a), by feature 006 — or
  by feature 007 for the node-serialization symbols, whichever lands first within that
  release. Retained legacy implementations MUST be frozen — no new callers, no new
  features, no behaviour edits.
- **FR-030a**: **A consumer requirement that cannot be met becomes a declared breaking
  change — never a silent one.** If any call site in the migration map cannot be kept
  working, because no shim can preserve it or because preserving it would violate another
  requirement in this spec, that MUST be recorded explicitly as a breaking change naming
  the symbol, the affected consumer call sites, and the reason it could not be shimmed.
  Discovering such a case is an acceptable outcome; leaving it undeclared is not.
- **FR-030b**: Every declared breaking change MUST be flagged in the release notes of the
  version that ships it, recorded in the migration map, and accompanied by the
  corresponding modifications in the affected sibling repositories, shipped as a
  coordinated bump (D1). A breaking change is not considered shipped until those sibling
  repository changes are **either prepared or explicitly scheduled** — the flag and the fix
  travel together, and where they cannot, the flag names the feature that carries the fix.

  **The scheduling case is narrow and requires both conditions**: the affected consumer is
  not shipping against the release, *and* writing the fix now would produce work a later
  feature in the same rebuild invalidates. Where both hold, deferring is the honest
  engineering call rather than laxity — but the declaration, the release-note flag and the
  test (SC-017) all still land in the release that causes the break. Only the sibling edit
  moves.

  **FR-026d is that case, and the only one.** `cuems-nodeconf` is out of date and its
  serialization work is unlanded, so nothing is shipping against this release. Its fix has
  to target the engine's registry, which is still internal in 004, becomes public API in
  006, and absorbs the node model itself in 007 — so a fix written against 004's
  intermediate shape would be rewritten twice. **The fix is therefore carried by feature
  007**, applied once against the final API and engine structure, and it lands on
  `cuems-nodeconf`'s `feat/nodeconf-reenable` branch, which feature 007 already works from
  rather than being gated on (`specs/planning/xml-rebuild-07-speckit-prompts.md` §6).
  Feature 004 itself touches no repository but this one.
- **FR-030c**: Consumer compatibility is verified in two layers, so that SC-013 and
  FR-022b do not conflict: **(i)** in-repo tests import and exercise every shimmed path,
  needing no sibling checkout; **(ii)** the migration map's enumerated call-site inventory
  is reviewed against each sibling repository at release time, outside the test suite.
  Layer (i) is the automated gate; layer (ii) is the release checklist that triggers
  FR-030a when a call site turns out to be unsupportable.
- **FR-031**: Hand-written per-class JSON emitters, the object-model unification, the
  public object API, the node model migration and consumer repository edits are **not**
  part of this feature.

**Observability**

- **FR-032**: Log output is the **single explicit exclusion** from the
  behaviour-preservation guarantee. Everything else in this spec is preserved exactly;
  log records are not.
- **FR-033**: Log level is determined by **altitude**, not by convenience:
  - **INFO** is declared at the **XML file access level** — a file being read, written or
    validated. This is the level at which an operator wants to see activity.
  - **DEBUG or lower** for everything internal: element construction, object building,
    per-cue and per-field work, spec derivation, registry resolution. Internally built
    elements and objects never log at INFO.

  No record at any level may contain field values, a full object repr, or any document
  content — identifiers (cue type, uuid) only. This closes F11, and removes show content
  such as names and file paths from log files as a side effect. Tying INFO to file access
  also removes the ambiguity of counting "documents" when one file load traverses many
  nested ones.
- **FR-034**: Logging MUST be consistent between the read and write directions; a message
  present on one side and commented out on its counterpart is a defect, not a style
  choice.

**Backward compatibility of reading (cross-cutting, binds the whole rebuild)**

- **FR-035**: Any document that is **valid under the schemas as they stand today** MUST
  continue to load, across every feature in the rebuild (004–008). Four facets, FR-035a to
  FR-035d, state the boundary of that obligation and how it is evidenced.

  *(Numbered 035 rather than 023a–d: the letter-suffix convention used throughout this spec
  means "extends the requirement it is suffixed onto", and FR-023 is the unrelated
  no-`.xsd`-edits boundary. The earlier FR-023a–d numbering collided with it.)*
- **FR-035a**: **Compatibility is defined against the current XSD configuration, not
  against historical schema versions.** A document that no longer validates under today's
  schemas is **out of scope** — schema evolution is permitted to leave it behind, and
  reviving it is not a requirement of this work.
- **FR-035b**: Within that boundary, **reading must never become stricter**. The engine may
  not reject a document today's parser accepts, and may not narrow a value's accepted
  lexical space. This is the reading-side counterpart to D3, and it binds the whole
  rebuild rather than this feature alone.
- **FR-035c**: A document's **`xsi:schemaLocation` form must never affect whether it
  loads** — absolute path, relative path, or attribute absent. **Measured**: all three
  already load. This is what makes feature 006's change from an absolute to a relative
  path safe on the read side, for both files already written and files written afterwards.
  All three forms MUST be exercised by test, not assumed.
- **FR-035d**: The regression corpus MUST include **historically-written documents that
  remain valid** under the current schemas, recovered from release tags, so FR-035b is
  evidenced rather than asserted. **Measured**: `tests/data/settings.xml` at `v0.1.0rc11`
  and `v0.1.0rc14` still loads and qualifies. Documents that no longer validate — measured:
  the same file at `v0.1.0rc2` and `v0.1.0rc7`, which predate the required
  `gradient_osc_port` element — are **not** compatibility obligations. They may be
  retained only as negative parity cases under FR-015, alongside
  `settings_bad_dmx_auto.xml`.

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
- **SC-003**: Serialization is **byte-stable** across repeated round-trips:
  `save(load(save(load(x)))) == save(load(x))` for every corpus document. Note this is
  *not* `save(load(x)) == x` — the first cycle normalizes formatting and rewrites the
  schema location, so that stronger form is false today and is not a property this feature
  can establish. **Measured**: stability holds; first-cycle identity does not, even for
  library-written files.
- **SC-003a**: Serialization is **semantically lossless**:
  `load(save(load(x))) == load(x)` — an object round-tripped through a file compares equal
  to itself. This is the durable guarantee: it survives reformatting, minification, and
  storage layers that rewrite the XML without changing its meaning, none of which
  byte-identity survives. **Measured**: holds today, so it is assertable in this feature.
  Restricted to loaded-vs-loaded objects; the built-vs-loaded comparison is F18 and
  belongs to feature 005.
- **SC-004**: The mapping rules exist in exactly one **live** implementation. Zero live
  code paths determine element order from dictionary iteration or from a hand-maintained
  ordering list; sorted-key ordering appears **only** in the declared order-free branch of
  FR-001; and the engine contains zero hardcoded field-name ordering exceptions —
  verifiable by search and by test. Frozen shim code is excluded, and is proven
  unreachable by SC-012.
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
- **SC-013**: Every old import path still imports successfully, and every deprecated
  symbol emits a warning **on each call** naming its replacement and `v0.1.1` as its
  removal release, reported against the caller's line. Of the 12 known consumer call sites
  across `cuems-editor`, `cuems-engine` and `cuems-nodeconf`, **all of `cuems-editor`'s
  and `cuems-engine`'s continue to work unmodified against this release**;
  `cuems-nodeconf`'s handler-injection sites are the single declared breaking change of
  FR-026d and are covered by SC-017 instead.
- **SC-014**: INFO record count scales with **files touched**, not with document content:
  writing a 1000-cue script — one file — emits INFO records in single digits rather than
  one per cue, and no log record at any level contains a field value or an object repr.
  Verified by capturing log output during the test.
- **SC-015**: The suite passes on a checkout of this repository alone, with no sibling
  repository present.
- **SC-016**: Adding a new document to the corpus produces its goldens automatically,
  while any attempt to overwrite an existing golden fails without a deliberate override.
- **SC-017**: The FR-026d breaking change is **declared, not discovered**: the migration
  map names the symbol, the affected `cuems-nodeconf` call sites, the reason no shim can
  preserve it, and **feature 007 as the carrier of the fix**; `CHANGELOG.md` flags it
  against the shipping version; and a test asserts the new behaviour explicitly — an
  injected handler class is **not** consulted, and the engine's registry resolves the type
  instead. All four land in this feature, in this repository. Zero undeclared behaviour
  changes remain.
- **SC-018**: The public API surface is unchanged, proven by a captured snapshot of
  `__all__`, the config classes and `XmlReaderWriter` with each callable's
  `inspect.signature`, compared before and after the swap (FR-024).
- **SC-019**: All three `xsi:schemaLocation` forms — absolute path, relative path, and
  attribute absent — load identically, exercised by test rather than assumed (FR-035c).
- **SC-TEST-001**: The round-trip chain test is committed against pre-refactor code, is
  green at that commit, and is green after the swap **without being edited** — provable
  from the commit history.
- **SC-TEST-002**: The full suite passes with no fewer than the baseline 557 tests and
  zero new failures or skips.
- **SC-QUALITY-001**: Lint is clean and no new warnings are introduced, with **one
  declared exemption**: `tests/test_name_coercion.py` calls the now-deprecated
  `CuemsParser.str_to_value` directly ~40 times by design, as the frozen-shim regression
  for that helper. Its `DeprecationWarning`s are expected and MUST be scoped out
  explicitly (a `filterwarnings` entry or marker on that file), not silenced globally.
- **SC-PERF-001**: Performance is budgeted in two parts, because this feature deliberately
  grows the suite:
  - **Write benchmark** — within 10% of the recorded pre-refactor baseline.
  - **Pre-existing suite** — the 557 tests that exist today stay within 10% of the ~7.4s
    baseline when run as a subset.
  - **New corpus suite** — the golden, contract and chain tests added by this feature
    carry their own **absolute** budget, recorded in `baseline.md` at the time the corpus
    is frozen. A 10% rule cannot apply to tests that did not previously exist, and
    SC-TEST-002 requires the total count to grow.

  **Measurement method**, because 10% of a ~7.4s suite is otherwise within noise: best of
  **5 runs** on the same machine, same pyenv 3.11.9 interpreter, no other load, comparing
  best-of-5 against best-of-5. A single run that exceeds the budget is not a failure; the
  best of five is the number that binds. The machine's identity is recorded in
  `baseline.md`, and a comparison taken on different hardware is not evidence.
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
3. **Compatibility — decided, and uniform, with one named exception.** Every old import
   path survives behind a deprecation shim (FR-026 to FR-030), the rename included. **No
   `cuems-editor` or `cuems-engine` consumer breaks at this release**, and no edit is
   required in either until feature 008.

   **The exception is `cuems-nodeconf`'s handler injection (FR-026d).** It is accepted
   rather than shimmed, on measured grounds: `cuems-nodeconf` is an already out-of-date
   repository whose serialization work lives on the unlanded `feat/nodeconf-reenable`
   branch, so it is not shipping against this release in the first place. Preserving the
   injection would mean keeping the implicit `globals()` lookup that FR-007 exists to
   delete, so the choice is between a declared break here and abandoning the feature's
   core premise. **The fix itself is carried by feature 007** (FR-030b's scheduling
   clause), applied once against the final API and engine structure; 004 declares, flags
   and tests the break but **edits no repository other than this one**. The 12 known call
   sites:
   `cuems-editor` (`CuemsDBProject`, `repair_durations`, one test — `XmlReaderWriter`,
   `CuemsParser`, `NetworkMap`), `cuems-engine` (`BaseEngine`, `ControllerEngine`, two
   tests, one archived file — `XmlReaderWriter`, `NetworkMap`, `ProjectMappings`),
   `cuems-nodeconf` (`CuemsNodeConf`, `NodeXmlBuilders`, two tests — `XmlReader`,
   `XmlWriter`, `GenericCueXmlBuilder`, `GenericParser`, `GenericDict`, `VALUE_TYPES`,
   `str_to_value`, plus the module-globals injection of F8). The `cuems-nodeconf` symbols
   are the deepest coupling and the ones with no direct replacement; their shims must say
   so and point at feature 007's migration. The injection itself is the one site where
   "still imports" is not "still works" — see FR-026d.
3a. **Symbols with no successor keep a frozen implementation — `CuemsParser` excepted.**
   A re-export is only possible where a symbol survives under a new name. The builder and
   parser *families* that the engine supersedes (`GenericParser`, `GenericDict`,
   `str_to_value`, `STRING_TYPED_KEYS`, `VALUE_TYPES`, the `*Parser` and `*XmlBuilder`
   classes) have no successor, so their current implementations are retained unchanged,
   unreferenced by the library, warning on use, and deleted in 006/007.

   **`CuemsParser` is the exception and is not frozen.** Measured: it is already
   library-internal — `XmlReaderWriter.write_from_dict` and `read_to_objects` both call
   it — so "unreferenced by the library" was never achievable for it without leaving
   `cuems-editor`'s five-call-site JSON→object path on legacy machinery. It becomes a
   delegating facade over the engine, keeps its signature and its results, and does not
   warn, because it *is* the supported entry point rather than a retired one. Its
   `globals()`-based handler lookup is what FR-026d declares broken.
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
- **No write access to any sibling repository is needed.** The FR-026d fix is carried by
  feature 007, so this feature is confined to this repository end to end — which is what
  keeps FR-022b, SC-015 and "the suite passes on a checkout of this repository alone"
  true without qualification.
- Feature 008 inherits two follow-ups from the decisions taken here: retiring the
  deprecation shims' consumer call sites, and migrating consumer tests off duplicate
  fixtures now owned by this repo.

## Out of Scope

Public API changes; object-model changes (including making loaded and built objects
type-identical, and typing media regions); any change to serialized output or to the wire
payload; `.xsd` edits; the node model migration from `cuems-nodeconf`; **all** edits in
consumer repositories, the FR-026d fix included — 004 declares, flags and tests that break
but touches no repository other than this one, and feature 007 carries the fix (FR-030b);
the deferred schema items X1–X12.

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
| F7 nodeconf coercion | 007 | Resolved by moving the node model, not by editing this package. |
| **F8 nodeconf globals injection** | **breaks here (declared); fixed in 007** | Superseding the implicit `globals()` lookup with the explicit registry (FR-007) is the feature's core premise, so the injection cannot survive 004. The break is declared under **FR-026d / FR-030a**, flagged in the release notes and asserted by SC-017 **here**; the `cuems-nodeconf` fix is carried by **007** under FR-030b's scheduling clause, because it must target an API that is internal in 004, public in 006 and absorbs the node model in 007. It lands on `feat/nodeconf-reenable`, which 007 works from instead of being gated on. |
| **X13 `gradient_osc_port` is required, so pre-`rc11` settings files no longer validate** (observed 2026-08-11) | **no fix required** | `settings.xsd:63` omits `minOccurs="0"` while the sibling `output_latency_ms` has it, so the practice is inconsistent. Recorded for the audit, **not scheduled**: compatibility is defined against the current XSD configuration (FR-035a), so files that predate a schema change are out of scope by policy rather than broken. Revisit only if reviving old on-disk files ever becomes a goal. |
| **F24 `schemaLocation` embeds an absolute local path** (new, measured 2026-08-11) | 006 — **decided: emit a relative path**, coordinated with dropping the leaked key (F23) | Every written file carries the writing machine's absolute path to the `.xsd`, so show files are non-portable and non-reproducible. **Cause is this library's own builder, not the schema toolchain** — one line, freely changeable; documents validate and read fine with a relative path, a namespace-only value, or no attribute at all. Deferred only because the value reaches the read dict (F23) and therefore the UI payload, so changing it is a wire change. 004 reproduces it and normalizes it for comparison (FR-010b). |
