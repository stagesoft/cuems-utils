# XML infrastructure rebuild — Part 4: spec-kit development prompts

**Status:** ready to execute
**Date:** 2026-08-11
**Purpose:** the complete, copy-pasteable prompt set to drive the rebuild through spec-kit.

Prior art in this repo: `001-mediacue-fading-function`, `002-timecode-qf-timer`,
`003-fade-cue`. **Next feature number is `004`.**

Installed skills (`.claude/skills/`): `speckit-constitution`, `speckit-specify`,
`speckit-clarify`, `speckit-plan`, `speckit-tasks`, `speckit-checklist`,
`speckit-analyze`, `speckit-implement`, `speckit-taskstoissues`.
Plugin skills also available: `speckit.check-integration`, `speckit.optimize`,
`speckit.verify`.

---

## 0. Why five features, not one

Part 3 §13 has eight phases spanning two repos and a UI contract. A single
`/speckit.specify` would produce a spec nobody can review and a `tasks.md` nobody can
finish. The decomposition below keeps each feature **independently shippable and
independently green**, which is also what makes the constitution's test gate meaningful.

| Feature | Covers Part 3 phases | Behaviour change? | Gated on |
|---|---|---|---|
| `004-xml-serialization-core` | 1–3 | **No** — byte-identical output | — |
| `005-object-model-unification` | 4 | Yes (bug fixes) | 004 |
| `006-public-object-api` | 5, 7 | Yes (API + `initial_template`) | 005 |
| `007-node-model-migration` | 6 | No (intake) | 006 + `feat/nodeconf-reenable` landing |
| `008-consumer-migration` | 8 | Cross-repo | 006, 007 |

Run them in order. Do not start the next until the previous is merged and green.

---

## 1. Constitution — check, do not amend

Read `.specify/memory/constitution.md` before starting. Two clauses bind this work:

- **Engineering Standards:** *"Refactors MUST preserve behavior unless the spec explicitly
  states otherwise."* Features 005 and 006 **do** change behaviour. This is permitted, but
  each spec MUST enumerate every change explicitly. The prompts below do that; do not drop
  those sections.
- **Principle IV — Performance Budgets Are Requirements:** every plan MUST carry measurable
  targets **before** implementation. Baseline: `hatch test` = **2222 passed, 94 skipped, 2 xfailed in ~59 s** (measured 2026-08-20, after feature 006; the "557 passed in ~7.4 s" this line carried until then predated features 004/005 and was stale by nearly 4x). Compare **per test** — ~27 ms — not wall time: the suite has grown with the features. Plus
  `tests/integration/test_mediacue_fade_performance.py`.

**No amendment is needed.** If you disagree after reading, run:

```
/speckit.constitution Review whether the "Refactors MUST preserve behavior" clause in
Engineering Standards adequately covers a deliberate, spec-documented API and
serialization refactor, or whether it needs an explicit carve-out for versioned breaking
changes. Do not weaken the test gate or the performance-budget principle. Report the
recommendation before editing anything.
```

---

## 2. Shared context block

**Paste this verbatim at the top of every `/speckit.specify` and `/speckit.plan` prompt
below.** It stops each fresh invocation from re-litigating settled decisions.

```
CONTEXT — read these before writing anything:
  specs/planning/xml-rebuild-01-audit.md              findings F1-F23, schema audit X1-X12
  specs/planning/xml-rebuild-02-node-model-ownership.md
  specs/planning/xml-rebuild-03-design-inputs.md      design constraints, Q11/Q14 rationale
  specs/planning/xml-rebuild-04-object-model.md       construction paths, measured divergence
  specs/planning/xml-rebuild-05-ui-wire-contract.md   editor<->UI payload contract
  specs/planning/xml-rebuild-06-target-design.md      THE TARGET DESIGN — authoritative

SETTLED — do not reopen, do not propose alternatives:
  D1  free hand on API; coordinated bump across consumers
  D2  schema is the single source of truth for structure/type/cardinality/order
  D3  wire-compatible with every XML on disk; no .xsd edits in this work
  D5  CMLCuemsConverter reduced to a thin subclass over stock xmlschema
  D9  PEP 8 module names, landed as a separate rename commit
  D11 node model + serializers move in from cuems-nodeconf
  D12 public surface returns objects, never raw dicts
  D13 outputs and regions are closed out, not worked around
  D14 xml -> object -> json -> object -> xml is tested end to end
  D15 public objects are CuemsScript (show) and ConfigManager/ConfigBase (config)
  Q11 -> (c) derive structure from schema; hand-write facade and behaviour
  Q14 -> (i) xml/ is internal machinery

HARD CONSTRAINT (Part 2d): cuems-editor's project_load payload must stay byte-identical,
because it is transmitted verbatim to the Angular UI. Verified: the UI reads booleans as
`cueData.enabled === true || cueData.enabled === 'True'` and writes back the STRING form.
```

---

## 3. Feature 004 — schema-derived serialization core

The foundation. **No observable behaviour change.** If anything about the output differs,
the feature has failed.

### 3.1 Specify

```
/speckit.specify <PASTE SHARED CONTEXT BLOCK>

Replace the XML serialization machinery in src/cuemsutils/xml/ with a single
schema-derived engine, with zero change to observable behaviour.

Today the same mapping rules are written four times over: an XML builder, an XML parser,
eight hand-written __json__ methods, and the config readers. Nothing checks that they
agree. Element ordering is satisfied by an alphabetical coincidence maintained by hand in
three unrelated files, with a hardcoded exception for master_vol/fade_profiles. Scalar
types are guessed at runtime by a heuristic patched with a key-name denylist.

The schema already states all of it. Derive an ordered, typed field specification from the
XSD at load time and drive one encode/decode engine from it, covering all six schemas.

WHAT MUST BE TRUE WHEN DONE:
- Every existing XML file on disk loads and saves with identical results.
- Written XML is byte-identical to what the current code produces for the same object.
- The dict returned by reading a script is byte-identical to today's, including its
  current repeated-element shape.
- Element order comes from the schema, not from dictionary iteration order; the
  master_vol/fade_profiles special case is deleted rather than relocated.
- Runtime type guessing is gone: scalar types come from the schema.
- A round-trip test covering xml -> object -> json -> object -> xml exists and passes,
  written against CURRENT behaviour before any machinery is replaced.
- A coherence test asserts, per model class, set equality between the fields declared in
  Python and the elements the schema declares. Set equality, not order.

EXPLICITLY OUT OF SCOPE: any public API change, any object-model change, any behaviour
change, any .xsd edit, the node model migration, consumer repo changes.

BEHAVIOUR CHANGES: none. This is a pure refactor under the constitution's Engineering
Standards clause.
```

### 3.2 Clarify

```
/speckit.clarify
```

Answer from the planning docs. Likely questions and their settled answers:

- *Ordering source?* — `content.iter_elements()`; verified to resolve `xs:extension` in
  schema order (Part 3 §3.1).
- *What happens to `REQ_ITEMS`?* — Unchanged. Keeps layered defaults and the alphabetical
  developer index; loses only the accidental element-order role.
- *Wildcard content (`ui_properties`, `xs:anyType`)?* — Documented fallback: preserve
  insertion order, pass scalars through untyped.
- *Repeated-element dict shape?* — Preserved exactly. It is the UI contract (F22).

### 3.3 Plan

```
/speckit.plan <PASTE SHARED CONTEXT BLOCK>

Follow the target design in specs/planning/xml-rebuild-06-target-design.md sections 3-6
and 10. Do not redesign it.

Technical context:
- Python 3.11+, xmlschema==3.4.3, lxml==6.1.0. Build/test with hatch.
- Modules to create under src/cuemsutils/xml/: schema.py, spec.py, adapters.py,
  registry.py, mapper.py, converter.py. Land the D9 rename as its own commit FIRST,
  pure git mv plus import updates, no logic changes.
- TypeSpec/FieldSpec derivation must be cached per (schema, type).
- Adapter inventory is small and already surveyed: four primitive bases; custom handling
  needed only for BoolType, UuidType/TargetType, CTimecodeType, the enum types, and the
  integer/float families. Everything else uses xmlschema's native decoding.
- Registry binds xsd type -> model class explicitly per schema, replacing three implicit
  globals() lookups. A missing binding is an error at registry build time.

Constitution check (all four principles must be addressed):
- II Tests: the D14 chain test is written FIRST, against current behaviour, and must pass
  unchanged after the swap. This is the feature's primary gate.
- IV Performance: baseline is `hatch test` 2222 passed in ~59 s (~27 ms/test, measured
  2026-08-20 after feature 006; was "557 passed in ~7.4s", stale since 004) and
  tests/integration/test_mediacue_fade_performance.py. Budget: no regression beyond 10%
  on the perf test; schema-walking must be cached, never per-object.
- I Quality: ruff clean, no new warnings.
- III UX: no user-facing change in this feature; assert it rather than assume it.

Also produce: research.md (xmlschema API surface used and its stability), data-model.md
(TypeSpec/FieldSpec/Adapter), and contracts/ capturing the byte-identity guarantees.
```

### 3.4 Tasks, checklist, analyze, implement

```
/speckit.tasks
```
```
/speckit.checklist Byte-identity and regression safety for a pure refactor: every guarantee
in the spec's "what must be true when done" gets a concrete verification step, including
byte-equality of written XML and of the read() dict against pre-refactor golden files.
```
```
/speckit.analyze
```
```
/speckit.implement
```

**Exit criteria:** full suite green (≥557 passing); chain test green; golden-file byte
equality for XML output and `read()` dict; perf within budget; `ruff` clean.

---

## 4. Feature 005 — object model unification

First feature with intentional behaviour change. Every change must be enumerated.

### 4.1 Specify

```
/speckit.specify <PASTE SHARED CONTEXT BLOCK>

Unify the object model onto a single construction path so that an object's internal types
no longer depend on how it was created.

Measured today: a CuemsScript built programmatically and the same script loaded from XML
are the same class with different internals — ui_properties is CuemsDict in one and a
plain dict in the other; media regions are list[Region] in one and list[dict] in the
other. Coercion lives in property setters, and the parser assigns with raw
dict.__setitem__, so it never runs. CuemsScript is also the only model class that is not
a CuemsDict, which forces a duplicated setter, a missing build(), a divergent items(),
and a JSON hack that detects wrapped children by testing keys for uppercase letters.

WHAT MUST BE TRUE WHEN DONE:
- Objects built programmatically, loaded from XML, and loaded from JSON have identical
  internal types for every field.
- Coercion runs regardless of entry point, because it lives in the field specification
  rather than in property setters.
- CuemsScript is a CuemsDict like every other model class.
- items() has one definition and one meaning across the model.
- One defaulting protocol across the hierarchy.
- Media regions are Region objects whenever they are read from any source.

BEHAVIOUR CHANGES — intentional, each one a bug fix (constitution Engineering Standards
requires these be explicit):
1. F18: loaded objects gain the internal types built objects already had. Code that
   relied on receiving plain dicts from a loaded script will now receive typed objects.
2. F12/F19: Media.set_regions currently discards its own coercion (it rebinds a loop
   variable), and mediaParser's compensating Region() reconstruction does not fire for
   the shape the reader produces. Both are fixed; regions become Region objects.
3. F16: create_script currently intends to clear ids but `script.id = None` assigns a
   fresh random Uuid, because Uuid(None) generates uuid4. Clearing will actually clear.
4. F17: setter() currently swallows AttributeError raised INSIDE a setter, silently
   dropping the field. Narrowed to "no such setter" only.
5. F20: Cue() bare yields an empty object while AudioCue() bare yields full defaults.
   Unified.
6. CuemsScript.items() currently returns every key, unfiltered, while Cue.items() filters
   to declared fields. Aligning this may stop emitting stray keys the root previously
   leaked into XML.

The serialized output must not change for any valid input. Change 6 can alter output for
invalid or stray input; that case must be covered by tests.

EXPLICITLY OUT OF SCOPE: public API changes, xml/ visibility, node model, consumers.
```

### 4.2 Through implement

```
/speckit.clarify
```
```
/speckit.plan <PASTE SHARED CONTEXT BLOCK>

Follow specs/planning/xml-rebuild-06-target-design.md section 7, and
specs/planning/xml-rebuild-04-object-model.md for the measured evidence and the
CuemsScript-as-CuemsDict analysis.

Technical context:
- Move coercion out of property setters into the field spec's adapters. Setters remain
  for ergonomics but stop being the coercion site.
- REQ_ITEMS is unchanged: layered defaults plus the alphabetical developer index.
- scratchpad probe probe_construction.py should be promoted into the D14 chain test as a
  built-vs-loaded internal-type comparison.

Constitution check:
- II: each of the six enumerated behaviour changes needs a test that fails before and
  passes after. Change 6 needs a test for the stray-key case specifically.
- IV: same budget as 004; construction is on the hot path for large scripts, so include
  an object-construction benchmark.
- III: consumers see richer types; document the change for the migration guide.
```
```
/speckit.tasks
```
```
/speckit.checklist One entry per enumerated behaviour change: the failing test that proves
it was broken, the passing test after, and the consumer-visible consequence recorded for
the migration guide.
```
```
/speckit.analyze
```
```
/speckit.implement
```

**Exit criteria:** built/loaded/from-JSON internal types identical; six behaviour changes
each covered by a fail-then-pass test; serialized output unchanged for valid input.

---

## 5. Feature 006 — public object API, `xml/` internal

The API-defining feature. Carries the UI hard constraint.

### 5.1 Specify

```
/speckit.specify <PASTE SHARED CONTEXT BLOCK>

Give the library a single public surface — CuemsScript for show data, ConfigManager and
ConfigBase for configuration — and make the XML machinery internal.

Today consumers reach around the public objects into the machinery: cuems-engine builds
an XmlReaderWriter directly to obtain a script, cuems-editor's load_xml returns a raw
dict, and schema_name="script" is passed at six call sites across three repositories even
though it is a property of CuemsScript. Config accessors return raw nested dicts, which
is why three shape compensations live in ConfigManager and why three mutually
incompatible shapes for the same mappings data are recorded across the codebase, two of
them fossilised in unreachable code.

WHAT MUST BE TRUE WHEN DONE:
- CuemsScript.load(path), .from_json(payload), .save(path), .validate(), .to_json(),
  .to_wire() exist and are the only supported way to move script data in or out.
- .load() guarantees a fully coerced object. This is a guarantee, not a convention.
- Building, validating and writing remain separable, so validating without a file still
  works (create_script relies on this today via xmlfile=None).
- ConfigManager exposes typed objects through its accessors, including network_map.
  Structure is derived from the schema; the curated accessors and the semantic rules
  stay hand-written.
- Semantic validation (canvas_region containment, one custom template per node, media
  duration) is a named, separate tier from schema validation.

REQUIRED DECISION STOP (1 of 2) — runtime data in the new persistence methods. The object
model is used for two different things and the design has never said so: a CuemsScript is
static between saves, while the Cue objects inside it are mutated continuously by the engine
during playback. Runtime state (_player, _osc_route, _go_thread, _start_mtc, _end_mtc,
_armed_list, _local, _stop_requested, _end_reached, _initialized, _target_object, _conf) is
kept out of serialization only by an underscore-prefix habit that nothing declares or
enforces, and no point is defined at which a loaded document becomes a runnable show. Decide
whether the split is declared or conventional, what save() means mid-show, whether load()
returns something runnable or something the engine promotes, how to_wire() is kept clean by
construction, and how copy/equality treat playback state. The five questions are written out
in specs/planning/xml-rebuild-06-target-design.md §8.1. "Convention, documented and tested"
is an acceptable answer; leaving it undecided while defining the persistence API is not.

REQUIRED DECISION STOP (2 of 2) — do not pass /speckit.clarify without resolving this. Feature 005
measured that the T2 tier is not three rules but FOURTEEN value-rejecting property setters,
every one of them bypassed on the load path and firing on the programmatic path only, plus
Uuid's own uuid4 rejection reached through set_id. 005 deliberately left that asymmetry
standing (its FR-006/FR-006a) because closing it would make reading stricter, which the
rebuild forbids. 006 is where it is decided. The inventory and the five questions the
decision must answer — read/write symmetry, a per-rule corpus sweep proving nothing
currently accepted becomes rejected, the setters' fate, the failure mode, and the unit of
registration — are in specs/planning/xml-rebuild-06-target-design.md §9.1 and §9.2. Record
the outcome as a clarification entry with the corpus sweep attached as evidence.
- The xml package exports nothing public. XmlReaderWriter and CuemsParser are removed
  from the public API, with a deprecation path for one release.
- schema_name disappears from every call site.

HARD CONSTRAINT — the UI must not break:
- CuemsScript.to_wire() MUST produce a dict byte-identical to today's XmlReaderWriter
  .read() output, minus the leaked schemaLocation key. This is what cuems-editor
  transmits verbatim to the Angular UI on project_load. A test must assert this
  byte-equality against golden files.
- Booleans stay as the strings "True"/"False" on the wire, because cms:BoolType is
  xs:string in the schema. Do NOT "fix" them to JSON booleans; that is deferred item X1
  and would be a file-format migration.

BEHAVIOUR CHANGES — intentional:
1. initial_template payload aligns with project_load: booleans become "True"/"False" and
   ui_properties integers become strings. The two payloads are currently inconsistent and
   the Angular frontend carries a dual-check to absorb it. No frontend change is required.
2. The schemaLocation key is dropped from the wire dict. Confirm nothing reads it.
3. The eight hand-written __json__ methods are replaced by the derived projection, and
   to_json gains its missing inverse from_json.
4. The written xsi:schemaLocation changes from an absolute filesystem path to a RELATIVE
   one. Today the builder writes the installed package's absolute path to the .xsd, so
   every show file carries the writing machine's local layout and is neither portable nor
   reproducible (finding F24). This is our own code, one line; the schema toolchain
   neither writes nor reads the value. Verified: documents validate and load with the path
   absolute, relative, or the attribute absent, so files already on disk are unaffected.
   Ship it together with change 2 so the wire format moves once, not twice.

ALSO DELIVER — the schema evolution convention. Adopt and document it in this feature; it
governs every schema change from here on:

  a. An element added to an EXISTING complex type MUST be declared minOccurs="0".
  b. It MUST carry a default supplied by the model layer (REQ_ITEMS), so a document that
     omits it loads to the same object a document that includes it would.
  c. Required elements may only appear in NEW types, never be added to existing ones.
  d. If a genuinely required addition to an existing type is unavoidable, it is a
     file-format migration — a documented, versioned event with a conversion path — never
     a silent schema edit.

Rationale, measured: settings.xsd:63 added gradient_osc_port without minOccurs="0", so
every settings file written before it stopped validating (X13). The sibling element
output_latency_ms was added WITH minOccurs="0" and stranded nothing. The practice is
inconsistent rather than absent; this convention makes the working half the rule.

EXPLICITLY OUT OF SCOPE: node model migration, consumer repository edits, .xsd changes —
the convention above is adopted and documented here, but applies to future schema work.
```

### 5.2 Through implement

```
/speckit.clarify
```

**Not skippable for this feature.** Both decision stops above — runtime-vs-persisted state,
and the validation asymmetry with its corpus sweep — are resolved here, before
`/speckit.plan` runs. A 006 spec that reaches planning without them is incomplete regardless
of what else it contains.
```
/speckit.plan <PASTE SHARED CONTEXT BLOCK>

Follow specs/planning/xml-rebuild-06-target-design.md sections 8, 9 and 10, and
specs/planning/xml-rebuild-05-ui-wire-contract.md for the wire contract evidence.

Technical context:
- Q11(c): derive config structure from the XSD; hand-write the ConfigBase/ConfigManager
  facade accessors and the semantic validators. ConfigBase's twelve existing accessors
  are the model for the facade, not something to replace with generated code.
- Two validation tiers, explicitly separated: T1 schema-derived, T2 named semantic.
- Deprecate rather than delete the old entry points in this release; removal is a
  follow-up once consumers have migrated.
- The config/ module is the least-specified part of the design. Settle the
  derived-vs-hand-written line concretely in data-model.md before writing code.

Constitution check:
- II: golden-file byte-equality test for to_wire() is the gating test.
- III: this is the UX-consistency feature. The two UI payloads becoming consistent is the
  point; document it for the frontend team even though no frontend change is required.
- IV: to_wire() is called on every project_load; benchmark it.
```
```
/speckit.tasks
```
```
/speckit.checklist API surface review: every public method's contract, its error
behaviour, its deprecation counterpart, and the byte-equality evidence for to_wire().
Include a check that no xml/ symbol remains reachable from the public API.
```
```
/speckit.analyze
```
```
/speckit.implement
```

**Exit criteria:** `to_wire()` byte-equal to golden `read()` output; public API complete
and documented; `xml/` exports nothing; deprecation warnings on old entry points; both
decision stops recorded and implemented (runtime-vs-persisted state; validation asymmetry
with its corpus sweep); suite green.

---

## 6. Feature 007 — node model migration

**Works from `cuems-nodeconf`'s `feat/nodeconf-reenable` branch. That branch does NOT need
to land on `main` first.** This inverts the earlier gating, and the reason is feature 004.

004 replaces the implicit `globals()` handler lookup with an explicit registry (FR-007).
`cuems-nodeconf` registers its node handlers by writing into those module globals
(`NodeXmlBuilders.py:96-99`), so that injection stops being consulted — no shim can
preserve it without keeping the very lookup 004 exists to delete. 004 therefore declares it
as its **one** breaking change (spec FR-026d, contract C11, tasks T031a/T031b/T049a), but
edits no repository other than `cuems-utils`.

**This feature carries the fix for that break.** 004 declares, flags and tests it, but
deliberately edits no repository other than `cuems-utils` — the fix has to target an API
that is internal in 004, becomes public in 006, and absorbs the node model here in 007, so
writing it earlier would produce work rewritten twice. Since `cuems-nodeconf` is not
shipping against 004's release, deferring costs nothing. This is FR-030b's scheduling
clause, and 007 is the named carrier.

Consequences for this feature:

- **It inherits a known-broken starting point, by design.** On `feat/nodeconf-reenable`,
  node serialization does not work against `cuemsutils` ≥ the 004 release: the injected
  handlers are silently not consulted. Fixing that is not incidental cleanup — it is a
  named deliverable of this feature, and the first thing to verify before migrating.
- **Waiting for the branch to land on `main` would be circular**: it cannot land cleanly on
  a `main` that still assumes the injection works, and the injection is what 004 removed.
  Work from the branch; merge it as part of this feature's exit.
- **The registration API question is already answered.** The prompt below says "no
  registration API exists for external builder/parser classes, because no external
  registrant remains" — as of 004 there is no registrant *mechanism* either. This feature
  removes the last registrant; it does not have to remove the mechanism.
- 004's `migration-map.md` is the input inventory for the node symbols, and its FR-026d
  entry is the specification of what has to be repaired.

```
/speckit.specify <PASTE SHARED CONTEXT BLOCK>

Bring the node object model and its serializers into cuemsutils from cuems-nodeconf.

cuems-utils already owns network_map.xsd, the NetworkMap reader and ConfigManager's
network-map integration. Only the object model and serializers live in cuems-nodeconf,
which is why that repo has to inject classes into this package's module globals to make
serialization work, and why a type-coercion bug fixed here stayed open there. Abandoned
stubs for exactly this migration already exist in this repo, unreferenced.

WHAT MUST BE TRUE WHEN DONE:
- node, node_list and NodeType live in cuemsutils, as CuemsDict-based models with declared
  fields, in a config domain module.
- The node model gains the identity fields role_id, alias and hostname, which the schema
  declares and the current model omits.
- Node serialization goes through the same derived engine as everything else.
- NetworkMap returns node objects.
- The dead CuemsNodeDictXmlBuilder and CuemsNodeDictParser stubs become the landing site
  or are removed.
- No registration API exists for external builder/parser classes, because no external
  registrant remains.
- The node-field coercion guard already shipped to cuems-nodeconf (commits 4b6844e and
  0a3ce37) migrates with the parser, with its 106-case regression test.
- The FR-026d breaking change declared by feature 004 is repaired here: cuems-nodeconf no
  longer injects handler classes into cuemsutils module globals, because the node handlers
  now live in cuemsutils and are bound in the registry like every other type. Feature 004's
  migration-map.md entry for FR-026d specifies what was broken; this feature closes it.
- cuems-nodeconf modifications land in a new branch starting at feat/nodeconf-reenable (commit 0a3ce37ab8dd33501c4817fa57fd8e390732967d)

DO NOT CHANGE the node_type wire format. It is currently the string "NodeType.<name>",
which originated as a str()/__repr__ mixup but is now a cross-repo contract with
cuems-engine. Make it an explicit, declared adapter rule rather than an accident of which
dunder the serializer calls. Changing the format is a separate, later decision.

EXPLICITLY OUT OF SCOPE: Avahi discovery, adoption logic, systemd orchestration — those
stay in cuems-nodeconf. Also out of scope: network_map.xsd edits, node_type format change.
```

```
/speckit.clarify
```
```
/speckit.plan <PASTE SHARED CONTEXT BLOCK>

Follow specs/planning/xml-rebuild-02-node-model-ownership.md sections 4 and 7.

Technical context:
- Source files: cuems-nodeconf cuemsnodeconf/CuemsNode.py (~110 LOC) and
  cuemsnodeconf/NodeXmlBuilders.py (~90 LOC), read from the feat/nodeconf-reenable branch,
  which already carries feature 004's fix for the removed globals injection (FR-026d).
  Do not read them from main; main predates that fix.
- NodeType is currently defined twice inside cuems-nodeconf (CuemsNode.py and
  AvahiTool.py). Consolidate to one definition here.
- network_map.xsd types node_type as NonEmptyString, change the XSD so it aligns with node_role as NodeRoleType.
- Provide a non-mutating replacement for get_nodes_by_adoption, which cuems-engine
  currently works around because it mutates its input.

Constitution check:
- II: port the 106-case coercion regression test; add round-trip tests for network_map.
- III: node objects replace raw dicts for engine and editor; document for the migration guide.
```
```
/speckit.tasks
```
```
/speckit.checklist Migration completeness: every symbol moved, every caller in
cuems-nodeconf accounted for in the migration guide, no orphaned stubs, node_type wire
format proven changed.
```
```
/speckit.analyze
```
```
/speckit.implement
```

**Exit criteria:** node model in `cuemsutils`; `network_map` round-trips through the
derived engine; `node_type` wire format proven changed; coercion regression test ported;
**feature 004's FR-026d breaking change closed** — no module-globals injection remains and
node serialization works again; and `feat/nodeconf-reenable` merged to `cuems-nodeconf`'s
`main` **as part of this feature**, since by then nothing in it depends on the removed
injection.

---

## 7. Feature 008 — consumer migration

Cross-repo. This spec lives in `cuems-utils` and defines the **contract and guide**; the
edits happen in each consumer repo as its own PR.

```
/speckit.specify <PASTE SHARED CONTEXT BLOCK>

Define and execute the consumer migration to the new public API, coordinated as a single
version bump across the CUEMS ecosystem.

WHAT MUST BE TRUE WHEN DONE:
- A migration guide in this repo maps every removed or changed entry point to its
  replacement, with before/after examples.
- cuems-engine obtains scripts via CuemsScript.load and consumes typed node objects.
- cuems-editor uses CuemsScript.load/save and from_json, and its project load path returns
  script.to_wire() so the payload sent to the UI is byte-identical to today's.
- cuems-nodeconf no longer ships node model or serializer code and no longer injects
  classes into this package's module globals; deprecated XmlReader/XmlWriter usage is gone.
- cuems-frontend requires no change. Optionally, its `=== true || === 'True'` dual-check
  can be simplified once both payloads agree — as a follow-up, not a blocker.
- Deprecated entry points are removed from cuemsutils only after all consumers are on the
  new API.

VERIFICATION: an end-to-end check that a project saved by the editor loads in the engine
and renders in the UI unchanged.
```

```
/speckit.plan <PASTE SHARED CONTEXT BLOCK>

Follow specs/planning/xml-rebuild-06-target-design.md section 12.

Per-repo scope:
- cuems-engine: core/BaseEngine.py:509; ControllerEngine network-map access; adopt the
  non-mutating get_nodes_by_adoption replacement.
- cuems-editor: CuemsDBProject.load_xml / save_xml / the three CuemsParser call sites;
  DBProject.load must return script.to_wire().
- cuems-nodeconf: delete NodeXmlBuilders.py; drop XmlReader/XmlWriter.
- cuems-frontend: no change required; record the optional cleanup as a follow-up issue.

Sequencing: cuemsutils releases first with both APIs live; consumers migrate; cuemsutils
then removes the deprecated surface in a subsequent release.

Constitution check:
- II: each consumer PR carries its own green suite. The end-to-end check is the gate.
- III: the migration guide is the UX deliverable.
- IV: no regression in engine project-load time.
```
```
/speckit.tasks
```
```
/speckit.taskstoissues
```

Use `speckit-taskstoissues` here specifically — cross-repo work is easier to track as
GitHub issues than as a single `tasks.md`.

```
/speckit.checklist Cross-repo readiness: version pins aligned, no consumer left on a
deprecated entry point, UI payload byte-equality verified end to end, rollback plan stated.
```

**Exit criteria:** all consumers migrated and green; end-to-end save→load→render verified;
deprecated surface removable.

---

## 8. Per-feature quality loop

After `/speckit.tasks` and before `/speckit.implement`, on every feature:

```
/speckit.check-integration
```
Confirms the tasks actually engage existing code rather than building alongside it —
valuable here, because this is a refactor and the failure mode is writing a parallel
implementation that never replaces the old one.

```
/speckit.optimize
```
Dependency and parallelisation review of `tasks.md`.

After `/speckit.implement`:

```
/speckit.verify
```
Validates completion against the spec.

---

## 9. Standing rules for every feature

1. **Never** run `/speckit.implement` on a red suite. Baseline is 557 passing.
2. The **D14 chain test is written before the machinery it guards**, against current
   behaviour. This is the single most important sequencing rule in the whole rebuild.
3. Golden files for XML output and the `read()`/`to_wire()` dict are generated **once**,
   from pre-refactor code, and are never regenerated to make a test pass.
4. Commits are GPG-signed. Retry on "gpg failed to sign"; never `--no-gpg-sign`.
5. Planning artifacts stay in `specs/planning/`; feature artifacts in `specs/NNN-*/`.
6. No `.xsd` edits in any of these features. Schema work is deferred under D3 and tracked
   as X1–X13 in the audit.
7. **Schema evolution convention** (adopted in feature 006, binds all later schema work):
   an element added to an **existing** complex type is `minOccurs="0"` with a model-layer
   default; required elements appear only in **new** types; anything else is a versioned
   file-format migration with a conversion path, never a silent edit. Measured precedent:
   `gradient_osc_port` broke every older settings file, `output_latency_ms` broke none.
8. **Compatibility is defined against the current XSD configuration**, not against file
   history. A document valid under today's schemas must load; one that no longer validates
   because the schema evolved is out of scope by policy. Reading must never become
   stricter than the pre-refactor parser.
