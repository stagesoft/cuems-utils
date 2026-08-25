# Feature Specification: Object model unification — one construction path

**Feature Branch**: `005-object-model-unification`
**Created**: 2026-08-12
**Status**: Ready for implementation *(analysis remediation applied 2026-08-17)*
**Input**: Unify the object model onto a single construction path so that an object's internal types no longer depend on how it was created. Coercion moves out of property setters into the field specification; `CuemsScript` becomes a `CuemsDict` like every other model class; `items()`, defaulting and region typing get one definition each.

**Planning context** (authoritative, read before planning):
`specs/planning/xml-rebuild/xml-rebuild-01-audit.md` (findings F1–F23),
`specs/planning/xml-rebuild/xml-rebuild-03-design-inputs.md`,
`specs/planning/xml-rebuild/xml-rebuild-04-object-model.md` (**the measured evidence for this feature**),
`specs/planning/xml-rebuild/xml-rebuild-05-ui-wire-contract.md`,
`specs/planning/xml-rebuild/xml-rebuild-06-target-design.md` §7 (**the target design**),
`specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md` §4 (this feature's place in the sequence).

This is feature 2 of 5 in the XML rebuild. It covers phase 4 of the target design (§13) and
is the **first feature with intentional behaviour change**. Feature 004 established one
schema-derived engine with byte-identical output and deliberately parked every fix that
would change behaviour; this feature lands that parked set. Features 006–008 follow and are
out of scope here.

**Settled decisions** (from the planning phase — not reopened by this spec): D1, D2, D3, D5,
D9, D11, D12, D13, D14, D15, Q11→(c), Q14→(i).

---

## Clarifications

### Session 2026-08-12

- Q: Does 005 remove the DMX-scene swallow-and-continue compatibility (F4), or is it deferred again? → A: **Include it as behaviour change 7.** 004 recorded `REMOVAL_TARGET = "005"` in code and listed F4 as deferred to this feature; it is the last silent-data-loss path in the writer, and it ships with F17 as one "silent failure" story (US4).
- Q: What performance budget applies to the load path, given coercion now runs where it previously did not? → A: **A stated one-time allowance plus an absolute ceiling** (option B). Decode may regress up to **2×**, and must stay under **75 ms** for the largest corpus document (measured today: 24 KB, 36.3 ms). Suite wall time and the write path keep the 10% rule. The allowance is one-time: feature 006 inherits the new measurement as its baseline, not the old one.
- Q: What happens to a key the schema does not declare, once the root and the cues share one declared-field rule? → A: **Dropped, but logged** (option B). Same output as today's cue behaviour, extended to the root, plus one log record per dropped key naming the class and the key, within 004's logging budget. Silent loss is how data disappears without a trace; an error would break objects that construct fine today.
- Q: When coercion moves to the field specification, do the property setters' value-rejecting rules start running on the load path? → A: **No — adapters coerce; setter rejections gain no new reach on the load path** (option A), expressed as outcome parity per document rather than as a blanket rule. Measured by AST sweep: **14 setters can reject a value**, not one, and three of their rules (`canvas_region` containment, fade-profile/template caps, media `duration`) are precisely the rules the target design assigns to feature 006's T2 tier. A second measurement refined the answer: the load path is **already mixed** — repeated members are built through the model constructor and so *do* run their setters, which is why two legacy corpus documents are rejected at decode today with that outcome pinned in the goldens. So parity, in both directions, is the requirement (FR-006/FR-006a), not "setters never fire on load". The inventory and the mixed-strategy evidence are carried into `specs/planning/xml-rebuild/xml-rebuild-06-target-design.md` §9.1, together with a **required decision stop** in 006 (§9.2) to re-analyse the load/write validation asymmetry against the engine and API structure that exist by then.

---

## Decisions taken in drafting *(confirmed at `/speckit.clarify` unless noted)*

Three questions were not settled by the input prompt. Each is answered here with its
evidence, rather than left as an open marker.

- **Q: Does 005 also remove the DMX-scene swallow-and-continue compatibility (F4)?** →
  **Yes — it is behaviour change 7.** Feature 004 preserved that failure path verbatim
  behind a named compatibility object whose code carries `REMOVAL_TARGET = "005"`
  (`src/cuemsutils/xml/mapper.py`), and 004's own out-of-scope table lists F4 as "deferred
  to 005". It is enumerated here rather than inherited silently. **Confirmed in the
  2026-08-12 clarification session.**
- **Q: When coercion moves to the field specification, do the property setters' *validation*
  rules start running on the load path?** → **No — and none may stop running either.**
  Coercion is not validation, and the requirement is per-document outcome parity in both
  directions (FR-006, FR-006a). Measured by AST sweep on 2026-08-12: **14 setters can reject
  a value** (listed in `specs/planning/xml-rebuild/xml-rebuild-06-target-design.md` §9.1). Three of their
  rules — `canvas_region` containment, fade-profile and template caps, media `duration` —
  are the exact seeds of feature 006's T2 tier, so widening them here would import that tier
  a release early without its structure. Two refinements came out of measurement rather than
  reading: the nil UUID that appears three times in `tests/data/sample_script.json` is
  rejected by `Uuid.__init__`, not by any setter, and 004's uuid adapter already keeps an
  unparseable value as its raw string; and the load path is **already mixed**, so the two
  legacy corpus documents rejected at decode must keep being rejected. **Corrected 2026-08-17
  against the code**: that rejection is raised by `VideoCueOutput.__init__`, which calls the
  module-level `_classify_output_name` (`src/cuemsutils/cues/CueOutput.py:154`) *before*
  `super().__init__` — not by `CueOutput.set_output_name`, as this spec and
  `specs/planning/xml-rebuild/xml-rebuild-06-target-design.md` §9.1 previously stated. That setter exists
  and also calls `_classify_output_name`, but its additional region-consistency rules are gated
  on `_initialized`, which `__init__` holds false during population. Preserving the pinned
  outcome therefore means preserving the *constructor call*, not setter invocation.
  Standing rule 8 ("reading must never become stricter") sets the floor; the pinned
  golden outcomes set the ceiling. This feature unifies **type coercion** only.
  **Confirmed in the 2026-08-12 clarification session**, with the inventory and a required
  decision stop handed to 006.
- **Q: What is the unified type of `ui_properties`?** → **`CuemsDict`** — the type the
  programmatic path already produces. The `UI_properties` class exists but has never been
  reached (the tag→class lookup searched for `ui_properties` while the class is spelled
  `UI_properties`; 004 recorded this and bound the type to a generic to preserve it).
  Adopting that class now would change the *built* path too, which no requirement asks
  for. Reconciliation target is the built path's type; the unreachable class is resolved
  (adopted as the `CuemsDict` alias or removed) rather than left as a decoy.

---

## User Scenarios & Testing *(mandatory)*

The "users" of this feature are the CUEMS components that hold script objects in memory
(`cuems-engine`, `cuems-editor`), the maintainers of this library, and — indirectly, through
the editor's payloads — the Angular UI.

### User Story 1 - A loaded object is the same object as a built one (Priority: P1)

A maintainer loads a show file, builds the equivalent script in code, and parses the same
script from a JSON payload. All three objects have the same class *and the same internal
types at every field*: the same wrapper type for `ui_properties`, region objects rather than
plain dictionaries for media regions, and the same value types for timecodes and ids.
Consumer code can then take one branch, not three.

**Why this priority**: this is the feature. Everything else listed below is either a
prerequisite for it (the root class, the defaulting protocol) or a consequence of it (the
enumerated bug fixes). It is also the only item consumers can observe directly.

**Independent Test**: construct one script three ways — programmatically, from XML, from
JSON — and compare the type of every field at every depth. The comparison fails against
today's code (`ui_properties`, `regions`) and passes afterwards, with no change to what
those objects serialize to.

**Acceptance Scenarios**:

1. **Given** a corpus document, **When** it is loaded from XML and the same content is built
   programmatically, **Then** a recursive field-by-field type comparison reports zero
   differences.
2. **Given** the same document loaded from XML and re-parsed from its JSON projection,
   **When** the two objects are compared, **Then** both structure and internal types match.
3. **Given** any of those three objects, **When** it is serialized, **Then** the written XML
   is byte-identical to the golden captured before this feature.
4. **Given** a media object from any source, **When** its regions are inspected, **Then**
   every member is a region object, and iterating them exercises region behaviour rather
   than dictionary access.
5. **Given** a value that is already coerced (a timecode object, a uuid object), **When** it
   passes through the construction path again, **Then** it is unchanged — coercion is
   idempotent.

---

### User Story 2 - The script root stops being a special case (Priority: P1)

A maintainer works on the script root the same way as on any other model object: it is a
`CuemsDict`, it answers `isinstance` checks the same way, it has the same `items()` meaning,
the same setter, the same build hook, and one JSON contract shared with its children — no
uppercase-key heuristic to detect a wrapped child.

**Why this priority**: the root's divergence is what forces the duplicated setter, the
missing build hook, the divergent `items()` and the JSON unwrap hack. Story 1's guarantee
cannot be stated generically while one object in the model answers "no" to "is this a
declared-field model object?".

**Independent Test**: assert `isinstance(script, CuemsDict)`, assert the model contains
exactly one definition of `items()` and one JSON projection rule, and confirm both payload
projections are unchanged apart from the enumerated stray-key case.

**Acceptance Scenarios**:

1. **Given** a script object from any source, **When** it is tested with `isinstance` against
   the model base type, **Then** it answers true, as every other model object does.
2. **Given** the model classes, **When** the source is searched for `items()` definitions,
   **Then** exactly one definition exists and every class uses it.
3. **Given** a script with only declared fields, **When** it is projected to JSON, **Then**
   the payload is identical to today's, produced without any key-casing heuristic.
4. **Given** a script carrying a stray key that the schema does not declare, **When** it is
   serialized to XML and to JSON, **Then** the stray key is handled by the one declared-field
   rule, the outcome is asserted by a test, and the difference from today's root behaviour is
   recorded in the migration notes.

---

### User Story 3 - Defaults and identifiers behave as written (Priority: P2)

A maintainer constructs any model class with no arguments and gets that class's declared
defaults — not an empty object for some classes and full defaults for others. Clearing an
identifier clears it, instead of silently assigning a fresh random one.

**Why this priority**: both defects are small, local, and independently shippable, but they
change generated content (the initial template) and so need their own evidence and their own
line in the migration notes.

**Independent Test**: bare-construct every model class and compare against its declared
defaults; build the initial template and assert the fields the code intends to clear are
actually empty.

**Acceptance Scenarios**:

1. **Given** any model class, **When** it is constructed with no arguments, **Then** it
   contains exactly its declared defaults, by the same protocol for every class.
2. **Given** the initial-template builder, **When** it clears the script and cue-list
   identifiers, **Then** the resulting object carries no identifier for those fields —
   matching the sibling fields that already clear correctly.
3. **Given** the cleared template, **When** it is projected to JSON for the editor, **Then**
   the identifier fields are empty rather than random, and this difference is recorded as a
   consumer-visible change.

---

### User Story 4 - Failures stop being silent (Priority: P3)

A maintainer whose coercion logic raises sees the error, instead of losing the field. A show
whose DMX scene cannot be serialized gets an error, instead of a file that saved cleanly
with a scene missing from it.

**Why this priority**: both are error-path changes with no effect on valid documents, so they
carry the least user-visible value — but they are the reason a defect in this area can hide
indefinitely, and 004 explicitly scheduled the second one here.

**Independent Test**: inject a failure inside a field setter and inside DMX-scene
serialization; both surface as errors rather than as a missing field and a truncated
document.

**Acceptance Scenarios**:

1. **Given** a key with no corresponding setter, **When** an object is populated, **Then**
   the key is skipped exactly as today — that path is unchanged.
2. **Given** a setter that raises internally, **When** an object is populated, **Then** the
   error propagates instead of the field being dropped.
3. **Given** a DMX scene that fails to serialize, **When** the document is written, **Then**
   the write fails with an error naming the scene, instead of producing a document with the
   scene silently absent.
4. **Given** every valid corpus document, **When** it is written, **Then** neither change
   above alters the output.

---

### Edge Cases

- **A document carrying the nil UUID** (`00000000-…`) — accepted today because the uuid
  adapter keeps an unparseable value as a string while `Uuid.__init__` would reject it; must
  still be accepted after coercion moves. Reading must not become stricter (rebuild standing
  rule 8).
- **A document rejected today** — the two legacy corpus files whose `output_name` fails
  `CueOutput`'s shape rule at decode, because repeated members are built through the
  constructor. They must keep being rejected, by the same rule, with the pinned golden
  outcome unchanged (FR-006a).
- **Order-free content**: the script root is an order-free (`xs:all`) type whose emission
  order is *arrival* order. The unified construction path must preserve the source document's
  key order for such types; a construction path that inserts keys in declared order would
  rewrite the root element of every hand-authored script on save. This is the single most
  dangerous side effect available in this feature.
- **Stray keys** on the root and on cues: today the root leaks them and cues filter them, in
  the JSON projection. One rule — dropped and logged (FR-015a) — and the resulting difference
  is tested rather than discovered.
- **Runtime attributes on a decoded object**: a cue loaded from a document must arrive with
  its playback state initialized and its persisted fields untouched. The two must not be
  confusable: no runtime attribute may become a dict key, and no dropped stray key may be a
  runtime attribute that simply took the wrong form.
- **Regions supplied in every shape they occur in**: a single mapping, a list of mappings, a
  list of already-typed regions, and the wrapped form the reader produces. All four must
  yield typed regions.
- **Wildcard content** (`ui_properties`): nested mappings and integer-valued entries must
  survive with the same wrapper type and the same serialized form as today, including the
  entries that currently serialize as the literal `None`.
- **Deeply nested cue lists**: recursion through cue-list contents must coerce at every
  depth, not just the first.
- **Re-coercion**: passing an already-coerced object through construction again must be a
  no-op, since objects are routinely copied and re-fed.
- **A model class whose declared fields disagree with the schema**: caught by 004's coherence
  test; unifying `items()` must not weaken it.
- **Bare construction of an abstract-ish base** (`Cue()`): now returns declared defaults;
  any code that relied on the empty result must be found.

## Requirements *(mandatory)*

### Functional Requirements

**One construction path**

- **FR-001**: Type coercion MUST be performed by the field specification (the schema-derived
  spec and its adapters, established in feature 004), so that it runs identically for objects
  built programmatically, decoded from XML, and decoded from JSON.
- **FR-002**: Property setters MUST remain available as ergonomic accessors but MUST NOT be
  the only place coercion happens; assignment style MUST NOT determine an object's internal
  types.
- **FR-003**: The decode path MUST NOT populate model objects in a way that bypasses
  coercion. The current raw-item assignment used by the engine's instantiation step is
  replaced by the unified path.
- **FR-004**: Coercion MUST be idempotent: applying it to an already-coerced value MUST leave
  the value unchanged.
- **FR-004a**: **Runtime state MUST survive the unification.** Cue objects carry
  non-persisted instance attributes — playback handles, timecode marks, arm state, locality
  flags — initialized in the constructor and mutated during a show. The unified construction
  path MUST initialize them on **every** entry point, exactly as bare construction does
  today, and they MUST NOT appear in `items()`, in the XML, or in either wire projection. A
  decoded cue that reaches the engine without them would fail at playback, not at load.
  **One of them is not inert**: `_initialized` gates `VideoCueOutput.set_output_name`'s
  region-consistency rules (`CueOutput.py:146,178`), and `__init__` deliberately holds it false
  while populating. The unified path MUST reproduce that ordering — initializing it true before
  population would give those rules new reach on the load path, which FR-006b forbids, in an
  arrival-order-dependent way. See contracts C12.
- **FR-005**: The unified construction path MUST preserve source key order for order-free
  content models, so that the emission order of the script root is unchanged. Byte-identity
  of written XML (FR-020) is the gate on this.
- **FR-006**: The rule is **outcome parity per document, in both directions**: every document
  and payload accepted today is still accepted, and every one rejected today is still
  rejected with the same rule firing. The 14 value-rejecting property setters inventoried on
  2026-08-12 MUST NOT gain reach on the load path, and MUST NOT lose it either.
- **FR-006a**: This matters because the load path is **already mixed**, measured 2026-08-12:
  repeated members are built by calling the model constructor, which runs both its own
  `__init__` validation and — through `CuemsDict.setter` — the property setters, while
  everything else is populated by raw assignment that bypasses them. Two legacy corpus
  documents are therefore rejected at object decode today by `VideoCueOutput.__init__`'s call
  to `_classify_output_name` (`CueOutput.py:154`, verified 2026-08-17), and 004 pinned that as
  a golden outcome. Parity is owed to that specific call site: the same `ValueError`, raised
  from the same place, not merely two documents that still fail. Unifying construction on the permissive
  strategy would make those documents start loading; unifying on the strict one would reject
  documents that load today. Neither is acceptable: **the unified path MUST reproduce each
  document's current outcome**, and the two pinned rejections are the test that proves it.
- **FR-006b**: This feature therefore **leaves a validation asymmetry standing** — the same
  value can be rejected when assigned through a property setter and accepted when decoded,
  depending on which construction strategy that type happens to reach. It MUST be recorded in
  the migration notes as a known, deliberate carry-over rather than silently inherited, and
  MUST NOT be widened: no new value-rejecting rule may be added to a setter in this feature,
  and no rule may change which types it reaches. Resolving it is feature 006's recorded
  decision stop.

**Identical internals across entry points**

- **FR-007**: For every model class and every declared field, the internal type MUST be the
  same whether the object was built programmatically, loaded from XML, or parsed from JSON.
- **FR-008**: `ui_properties` MUST have the same wrapper type on all three paths — the type
  the programmatic path produces today.
- **FR-009**: Media regions MUST be region objects on all three paths, in every shape regions
  are supplied in: a single mapping, a list of mappings, a list of already-typed regions, and
  the wrapped `{'Region': …}` form the reader produces.
- **FR-009a**: A region supplied in a shape matching **none** of those four MUST raise, naming
  the shape received. It MUST NOT pass through unchanged: an unrecognised shape that survives
  coercion is a plain-dictionary region — precisely the defect change 2 removes — and it would
  reappear silently, which is the failure mode this feature exists to end.
- **FR-009b**: `MediaType.duration` is **out of scope for every coercion change in this
  feature**. It is a `TimecodeType` — a restricted string — whose getter contract is `str` and
  which emits as bare text, unlike the identically-named `FadeCueType.duration` (a
  `CTimecodeType`, emitted as a wrapped child). It is already `str` on both the built and the
  loaded path, so FR-007 is satisfied without touching it; coercing it would change the emitted
  element for every media document and break `cuems-engine`'s getter contract. See
  `data-model.md` §4 and the hazard note in T048.
- **FR-010**: Type identity MUST hold recursively — at every depth of cue lists, media,
  outputs and regions — not only at the top level.
- **FR-011**: Registry bindings that were deliberately pointed at generic containers in 004 to
  preserve behaviour MUST be re-pointed at the real model classes wherever FR-007–FR-010
  require it. Verified 2026-08-17: `MediaType` and `RegionType` are **already** bound to
  `Media` and `Region` (`src/cuemsutils/xml/registry.py:162-163`), so the only binding this
  feature re-points is `UiPropertiesType`. The previously unreachable hand-written handler
  `UI_properties` MUST be either adopted or removed — none left present-but-unreachable. This
  obligation is scoped to **reachable** code: `mediaParser` sits below `CuemsParser.parse` in
  the frozen legacy tree (`src/cuemsutils/xml/Parsers.py:120-122`), which is unreachable by
  design and is removed with the deprecation shims in **feature 006** (settled 2026-08-17; the
  `Parsers.py` docstring saying 007 is wrong and is corrected by T028a).

**The root joins the model**

- **FR-012**: `CuemsScript` MUST be a `CuemsDict`, satisfying the same base-type predicate as
  every other model class.
- **FR-013**: The duplicated setter on the root MUST be removed in favour of the shared one.
- **FR-014**: `items()` MUST have exactly one definition and one meaning across the model:
  the declared fields of the class, accumulated across its inheritance chain. Per-class
  overrides MUST be removed.
- **FR-015**: The declared-field rule that `items()` expresses MUST be the same rule the
  serialization engine uses to select fields for emission, so that the model and the engine
  cannot disagree about what a declared field is.
- **FR-015a**: A key that the rule does not recognise MUST be **dropped, not raised on, and
  not silently lost**: it is excluded from every projection and **one log record per dropped
  key per object** — naming the class and the key — is emitted. A document dropping the same
  key on five cues therefore emits five records. Logging MUST stay inside the budget 004
  established (INFO at document level, DEBUG or lower per object) and MUST NOT include the
  value.
- **FR-016**: The JSON projection MUST use one contract for the root and its children. The
  current uppercase-key heuristic for detecting wrapped children MUST be removed, and the
  emitted payload MUST be unchanged apart from the differences enumerated under "Behaviour
  changes".

**One defaulting protocol**

- **FR-017**: Every model class MUST use the same defaulting protocol, so that constructing
  any class with no arguments yields that class's declared defaults.
- **FR-018**: The declared-defaults source (`REQ_ITEMS`) keeps its two current jobs — layered
  defaults and the alphabetical developer index — unchanged.

**Behaviour changes — enumerated** *(constitution, Engineering Standards: refactors preserve
behaviour unless the spec states otherwise; these are the stated exceptions)*

- **FR-019**: Each change below MUST be covered by a test that fails before the change and
  passes after it, and MUST be recorded in the migration notes with its consumer-visible
  consequence.

  | # | Finding | Change | Consumer-visible consequence |
  |---|---|---|---|
  | 1 | F18 | Loaded objects gain the internal types built objects already had. | Code that received plain dictionaries from a loaded script now receives typed objects. |
  | 2 | F12 / F19 | Region coercion actually runs: the setter's discarded coercion and the compensating reconstruction that never fired are both replaced by the unified path. | `regions` members are region objects, not dictionaries. |
  | 3 | F16 | Clearing an identifier clears it, instead of assigning a fresh random one. | The initial template ships with empty script and cue-list identifiers, matching the sibling fields that already clear. |
  | 4 | F17 | The blanket `except AttributeError` around setter invocation narrows to "no such setter"; an `AttributeError` raised *inside* a setter propagates. Exceptions of other types already propagate today and are unaffected. | A field whose coercion fails now raises instead of vanishing. |
  | 5 | F20 | One defaulting protocol: bare construction yields declared defaults for every class. | `Cue()` is no longer empty. |
  | 6 | §5.4 of Part 2c | The root's `items()` filters to declared fields, as cues already do. | Stray keys the root previously leaked stop being emitted. |
  | 7 | F4 | The DMX-scene swallow-and-continue compatibility introduced by 004 is removed, per its recorded removal target. | A show whose DMX scene fails to serialize now errors instead of saving with the scene missing. |

- **FR-020**: For every **valid** input, serialized output MUST be unchanged: written XML
  byte-identical to the goldens captured in 004, and the read dict byte-identical, including
  repeated-element shape. No golden may be regenerated to make a test pass.
- **FR-021**: Change 6 MAY alter output for invalid or stray input. That case MUST be covered
  by tests that state the new outcome explicitly, for both the root and a cue, in both
  projections.
- **FR-022**: Changes 3 and 6 alter the editor's `initial_template` payload (identifiers, and
  stray keys if any). The delta MUST be measured, recorded in the migration notes, and
  confirmed harmless to the UI. The `project_load` payload MUST remain byte-identical —
  it is transmitted verbatim to the Angular UI and is the feature's hard constraint.
- **FR-023**: Change 7 MUST surface as an actionable error identifying the failing scene by its
  `id` — or by its zero-based index in the cue's scene contents when no `id` is present — and
  naming the originating cue; the engine MUST NOT gain an ambient catch-all in its place.

**Non-regression**

- **FR-024**: Accept/reject parity as stated in FR-006 and FR-006a MUST hold against the
  current corpus and its pinned outcomes, and is verified here as a non-regression gate rather
  than restated as a second requirement. FR-006/FR-006a are the normative text; this entry
  exists so the non-regression suite has an explicit owner.
- **FR-025**: The coherence test (declared fields ↔ schema-declared elements, set equality
  per class) MUST continue to pass and MUST NOT be weakened by the `items()` unification.
- **FR-026**: The round-trip chain (XML → object → JSON → object → XML) MUST continue to pass,
  extended with a **built-vs-loaded** internal-type comparison — the comparison Part 2c
  Appendix A's probe performed and that 004's semantic round-trip test explicitly excluded as
  belonging here.
- **FR-027**: No public API signature changes, no `.xsd` edits, no `xml/` visibility changes,
  and no edits to consumer repositories in this feature.
- **FR-UX-001**: Consumer-visible consequences of all seven changes MUST be written into the
  migration notes carried by the rebuild, in the same form 004 established, so feature 008
  inherits a complete record. No user-facing wording or defaults change beyond the enumerated
  items.
- **FR-PERF-001**: Construction is on the hot path for large scripts, so this feature MUST
  validate the construction budgets fixed in SC-PERF-002/003 — a 2× decode allowance under a
  75 ms absolute ceiling, spent once — in addition to inheriting 004's suite and write
  budgets. The pre-005 decode measurement MUST be captured before the first behaviour change
  lands, or the allowance has no denominator.

### Key Entities

- **Model object**: any `CuemsDict`-based domain object — cues, cue list, media, regions,
  outputs, DMX structures, fade profiles, and (newly) the script root.
- **Declared field set**: the fields a class owns, accumulated across its inheritance chain;
  the single rule behind `items()`, defaulting and emission selection.
- **Field specification / adapter**: the schema-derived description of a field and the codec
  that converts its value between wire, lexical and Python forms — established in 004, and in
  this feature the sole coercion site.
- **Construction path**: the one route by which a model object is populated, whatever the
  source (keyword/dict, XML decode, JSON decode).
- **Wire projections**: `project_load` (byte-identical, hard constraint) and
  `initial_template` (changes only as enumerated in FR-022).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For 100% of corpus documents, a recursive field-by-field comparison of
  built / XML-loaded / JSON-loaded objects reports **zero** type differences. The same
  comparison fails on pre-005 code, naming `ui_properties` and `regions`.
- **SC-002**: the measurement of FR-020 — 100% of 004's XML goldens and read-dict goldens
  remain byte-identical; zero goldens regenerated. Evidenced by an empty
  `git diff --stat tests/golden/`, which includes the API snapshot golden (FR-027).
- **SC-003**: Each of the seven enumerated behaviour changes has at least one test that fails
  on pre-005 code and passes after — seven demonstrated fail-then-pass pairs, evidenced in
  the pull request.
- **SC-004**: Exactly **one** definition of `items()` exists in the model, and exactly one
  declared-field rule is used by both the model and the serialization engine — verifiable by
  search and by test. A stray key on the root and a stray key on a cue produce the same
  outcome: absent from every projection, present in exactly one log record.
- **SC-004a**: 100% of cue classes arrive from every entry point with their runtime
  attributes initialized, and 0% of those attributes appear in any projection.
- **SC-005**: Bare construction of 100% of model classes yields that class's declared
  defaults; zero classes retain a bespoke defaulting branch.
- **SC-006**: Regions are typed objects in 100% of cases across all four supply shapes and
  all three entry points; zero remaining plain-dictionary regions anywhere in the corpus.
- **SC-007**: Accept/reject parity holds for 100% of corpus documents and their pinned
  outcomes, plus the nil-UUID payloads: nothing accepted today is rejected after, and nothing
  rejected today — the two legacy `output_name` documents included — starts loading.
- **SC-008**: `isinstance` against the model base type is true for 100% of model classes,
  the script root included; zero special cases remain in generic traversal.
- **SC-009**: The `project_load` projection is byte-identical to its golden; the
  `initial_template` delta is exactly the enumerated identifier fields (and stray keys, if
  the corpus contains any), with no other field changed.
- **SC-TEST-001**: Full suite green at or above the current baseline of **1251 passed, 43
  skipped**; no test skipped or deleted to accommodate a change.
- **SC-PERF-001**: Full-suite wall time within **10%** of the current 36.7 s baseline, and the
  media-cue fade performance test within 10% of its recorded budget.
- **SC-PERF-002**: The load path carries a **stated one-time allowance with an absolute
  ceiling**, because coercion now runs where it previously did not: object decode may regress
  by at most **2×** against the pre-005 measurement, **and** the largest corpus document must
  decode in **≤75 ms** (measured 2026-08-12: 24 KB, 36.3 ms). Both conditions must hold. The
  write path and full-suite wall time keep the 10% rule of SC-PERF-001. The allowance is
  spent once: feature 006 inherits the post-005 measurement as its baseline.
- **SC-PERF-003**: Coercion is performed at most **once per field per construction** — no
  value passes through an adapter twice — and a large-script benchmark (≥1000 cues) is added
  so later features have a construction baseline that does not exist today.
- **SC-QUALITY-001**: `ruff` clean; no new warnings in the default tooling.

## Assumptions

1. Feature 004 is landed and green on this branch; its engine, registry, adapters, goldens,
   corpus and coherence test are the starting point. Baseline measured 2026-08-12:
   **1251 passed, 43 skipped, 36.71 s**.
2. The reconciliation target for a divergent field is **the type the programmatic path
   produces today**, since that is the typed side of the divergence. This applies to
   `ui_properties` (a `CuemsDict`) and to regions (region objects).
3. Coercion and validation are separate concerns; this feature moves only coercion.
   Validation tiers are feature 006 (Decisions taken in drafting, Q2).
4. F4's removal belongs here because 004 recorded 005 as its removal target in both code and
   spec (Decisions taken in drafting, Q1).
5. `REQ_ITEMS` remains the hand-written declared-defaults source and developer index; this
   feature does not replace it with generated code.
6. No consumer repository is edited. Consumers observe richer types on loaded objects; that
   migration is feature 008, informed by the notes FR-UX-001 requires here.
7. The initial-template identifier change is acceptable to the Angular UI because three of the
   five cue identifiers in that template already arrive empty today — the change makes the
   remaining two consistent with the intent already expressed in the code.

## Dependencies

- Feature 004 merged and green (engine, adapters, registry, corpus, goldens, chain test).
- The built-vs-loaded probe described in planning Part 2c Appendix A, reconstructed and
  promoted into the chain test (FR-026). It is not currently in the repository.
- No new runtime dependency.
- Feature 006 inherits: the semantic-validation tier that will re-home the setters'
  value-rejecting rules (FR-006), and the JSON projection replacement (the derived projection
  supersedes the hand-written one there, not here).

## Out of Scope

Public API changes and the new `load`/`save`/`validate`/`from_json`/`to_wire` surface
(feature 006); making `xml/` internal (006); the `initial_template`↔`project_load` encoding
alignment and the `schemaLocation` changes (006); the node model migration (007); all
consumer repository edits (008); `.xsd` edits (deferred under D3); the deferred schema items
X1–X13.

**Explicitly not fixed here**: the setters' value-rejecting rules neither gain nor lose reach
on the load path (FR-006, FR-006a, FR-006b). The asymmetry they create — the same value
rejected or accepted depending on which decode strategy its type happens to reach — survives
this feature deliberately, and is resolved by feature 006's recorded decision stop
(`specs/planning/xml-rebuild/xml-rebuild-06-target-design.md` §9.2), together with the runtime-vs-persisted
state question raised here and recorded as 006's second stop (§8.1).
