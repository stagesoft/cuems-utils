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

## 0. Why five features, not one (now six)

Part 3 §13 has eight phases spanning two repos and a UI contract. A single
`/speckit.specify` would produce a spec nobody can review and a `tasks.md` nobody can
finish. The decomposition below keeps each feature **independently shippable and
independently green**, which is also what makes the constitution's test gate meaningful.
Five features covered Part 3's eight phases; `008-rebuild-extension` is a sixth, added later
and outside Part 3's original scope (§7) — the same review-ability rule still applies to it.

| Feature | Covers Part 3 phases | Behaviour change? | Gated on |
|---|---|---|---|
| `004-xml-serialization-core` | 1–3 | **No** — byte-identical output | — |
| `005-object-model-unification` | 4 | Yes (bug fixes) | 004 |
| `006-public-object-api` | 5, 7 | Yes (API + `initial_template`) | 005 |
| `007-node-model-migration` | 6 | **Yes** — `node_type` → `node_role`, a hard cutover across three repos | 006 + `feat/nodeconf-reenable` landing |
| `008-rebuild-extension` | — (new; not one of Part 3's original eight) | **Yes** — see §7. Lands in **two gated phases** (D30) | 007 |
| `009-consumer-migration` | 9 | Cross-repo | 006, 007, 008 |

Run them in order. Do not start the next until the previous is merged and green.

**008 applies that same rule once inside itself.** Its five items are a dependency chain
(D28) with a seam between the four that change existing machinery and the one that adds a new
subsystem, so `tasks.md` carries a hard gate: Phase 1 (ITEMs A–D) merged and green before any
Phase 2 (ITEM E) task starts. One spec, one plan, one feature number — a sequencing gate, not
a scope split, and not a release boundary. It is applied at a **deliberate stop between
`/speckit.plan` and `/speckit.tasks`** (D31, §7.2) — the only such stop in the rebuild.

**007, 008 and 009 are a triple that does not ship independently.** The row above said "No
(intake)" until 2026-08-24; clarification enlarged 007 to edit `network_map.xsd` and three
repositories, and the rename is a hard cutover with no dual-spelling release. 008 then widened the
scope further (2026-08-25): none of its five items *require* editing a consumer repository
directly — closer in shape to 004–006 than to 007 — but several change behaviour in ways existing
consumers assume differently today (`Media.duration`'s type **and wire shape**, `load()`'s
strictness), so the same no-independent-release logic that bound 007↔009 is extended to cover 008
too: **nothing in the ecosystem releases until 009 lands** (007 FR-030c/FR-030d's gate, extended
rather than re-derived — confirmed by the repo owner on 2026-08-25, D27).

008 also raises the stakes of that gate. 007's hard cutover converted **one config file per
node**; 008's `Media.duration` promotion converts **every project document in every library**
(D18b). The gate is the same rule, but the cost of getting the ordering wrong is no longer
bounded by a node's config directory.

> **2026-08-25 renumbering note (resolved)**: consumer migration was originally slotted as
> feature `008` and moved to `009` when the team decided to extend the rebuild's scope before
> consumer migration starts. `008-rebuild-extension`'s row above and §7 below are that new
> feature's content, gathered in conversation with the repo owner on 2026-08-25. Evidence backing
> §7 lives in
> [Part 5 — feature 008 extension audit](xml-rebuild-08-extension-audit.md), **revised the same
> day** after a review pass against the live code in all four repositories corrected five of its
> findings. §7 and §8 are written against the revised version; Part 5's revision table lists what
> changed and why it mattered.

---

## 1. Constitution — check, do not amend

Read `.specify/memory/constitution.md` before starting. Two clauses bind this work:

- **Engineering Standards:** *"Refactors MUST preserve behavior unless the spec explicitly
  states otherwise."* Features 005 and 006 **do** change behaviour. This is permitted, but
  each spec MUST enumerate every change explicitly. The prompts below do that; do not drop
  those sections.
- **Principle IV — Performance Budgets Are Requirements:** every plan MUST carry measurable
  targets **before** implementation. Baseline: `hatch test` = **2393 passed, 94 skipped, 2 xfailed in 59.33 s** (measured 2026-08-24, after feature 007 — `specs/007-node-model-migration/baseline.md`). Compare **per test** — **24.79 ms** — not wall time: the suite has grown with every feature, so a wall-time budget reads growth as regression. (This line carried 006's 2222 / ~27 ms until 2026-08-25, and "557 passed in ~7.4 s" before that; re-measure it after each feature rather than inheriting it.) Plus
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
  specs/planning/xml-rebuild/xml-rebuild-01-audit.md              findings F1-F23, schema audit X1-X12
  specs/planning/xml-rebuild/xml-rebuild-02-node-model-ownership.md
  specs/planning/xml-rebuild/xml-rebuild-03-design-inputs.md      design constraints, Q11/Q14 rationale
  specs/planning/xml-rebuild/xml-rebuild-04-object-model.md       construction paths, measured divergence
  specs/planning/xml-rebuild/xml-rebuild-05-ui-wire-contract.md   editor<->UI payload contract
  specs/planning/xml-rebuild/xml-rebuild-06-target-design.md      THE TARGET DESIGN — authoritative
  specs/planning/xml-rebuild/xml-rebuild-08-extension-audit.md    feature 008 evidence (E1-E26) — read for 008/009 prompts only
                                                                  (REVISED 2026-08-25; read its revision table first)

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
  D16 consumer-repo modifications ARE allowed from feature 008 onward, when a requirement
      needs them; each one MUST be described and incorporated into 009's content (feature
      008 introduced this — see xml-rebuild-08-extension-audit.md's intro)
  D17 EVERY element that carries a time value is typed cms:CTimecodeType and stores a
      CTimecode object, with no exception. This PROMOTES Media.duration in script.xsd from
      cms:TimecodeType (a restricted string) -- the other six CTimecodeType elements already
      store CTimecode objects today. The same machinery (format_timecode on write,
      _CTimecodeAdapter on the wire) applies to all seven; dead code left behind by the
      change is removed, not left resolving. Closes T073's documented exception. See E1-E4.
  D18 canonical timecode form is HH:MM:SS.mmm everywhere; settings.xsd's dead, wrongly
      patterned CTimecodeType/TimecodeType (and the Python model class that exists only to
      bind it) are DELETED, not fixed in place. script.xsd's TimecodeType SURVIVES -- it is
      the lexical type of the <CTimecode> child and is already the canonical pattern.
  D18b D17's promotion is a script.xsd edit and the THIRD recorded exception to D3, after
      network_map.xsd (007) and settings.xsd (D18). It is the only one of the three that
      changes documents already on disk: <duration>TC</duration> becomes
      <duration><CTimecode>TC</CTimecode></duration>, in XML and in the JSON wire alike.
  D19 load() runs full validate() (T1 AND T2) across all six schemas -- a deliberate reversal
      of "reading never becomes stricter" (FR-026, standing rule 8), recorded rather than
      silently changed. Failure has THREE outcomes, not two (D21).
  D20 document compatibility is governed by a new EXPLICIT, systemic version marker
      (not 007's implicit/structural per-change tell) -- the mechanism rule 4 of the
      schema-evolution convention called for but was never built. Its first real client is
      D17's Media.duration conversion, not a synthetic fixture (E24).
  D21 three outcomes on load, by document state:
        OLD (version marker precedes current) -> transparent auto-conversion in memory,
            timestamped backup written first; same logic also exposed as a standalone tool
        CURRENT BUT SEMANTICALLY INVALID -> REPAIR-AND-NOTIFY: recover a default state for
            the offending field, carry it in a structured report, continue loading
        UNREPAIRABLE -> raise
      Defaults come from D25's descriptor (no hand-written per-field fallbacks). The report
      is public (cuemsutils.errors) because cuemsutils has no UI channel and must not gain
      one: 008 produces the report, 009 forwards it to the UI.
  D22 network-map config-object logic (merge/adopt/unadopt/refresh/signature/write
      orchestration) lives in cuems-utils, on NodeIndex/CuemsNetworkMapType, mirroring
      ConfigManager/ConfigBase -- not reimplemented ad hoc on cuems-nodeconf's daemon.
      Equivalence with today's behaviour is MEASURED in 008 via characterization tests
      ported from CuemsNodeConf, not asserted at 009 time (E23).
  D23 CuemsNodeConf's full atomization (the other nine responsibilities besides the
      network-map config object) is NOT executed in 008 -- 008 records the target-design
      basis only; execution is a later, dedicated cuems-nodeconf feature, tracked via 009.
      That basis MUST account for E20/E25: row 5 has a live UI on the far end of its
      dispatch chain, and the split cannot be designed as if it were headless.
  D24 config object save() ships for settings/project_settings/project_mappings in 008.
      Decoupled from the descriptor work (D25) but a PRECONDITION of the load work (D21):
      backup-before-convert and repair-to-default both need a config write path first.
  D25 template/config generation moves off hand-maintained example objects onto a
      schema-derived descriptor covering all six schemas, emitting per type: field name,
      XSD type, cardinality, restricted xs:enumeration values, AND model-layer defaults.
      Defaults are not optional -- D21's repair path and two of the frontend's template
      call sites both consume values, not shape (E19). create_script() is SUPERSEDED, not
      preserved (its output need not stay byte-identical); templates/settings.xml, the
      second hand-maintained template, is superseded on the same grounds (E26).
  D26 009 completes the cutover: initial_template-as-a-concrete-instance is retired.
      Script domain is a migration of the ~7-call-site frontend surface. Config domain is
      ALSO a migration, NOT greenfield -- a network_map editing UI exists and is in daily
      use (settings.component.ts, nodelist_modify adopt/unadopt), and project_mappings has
      read consumers. Existing machinery is ported onto dynamic-form UI entities with its
      LOGIC PRESERVED; the network_map/project_mappings wire entanglement (E25) is
      untangled as part of that port.
  D27 008 does NOT ship independently: 007's no-independent-release gate (FR-030c/FR-030d)
      extends through 008, so nothing in the ecosystem releases until 009 lands -- 008 is
      cuems-utils-only in scope (D16) but not independently shippable in consequence
  D28 item order is a dependency chain, and structural soundness outranks parallelization:
      timecode (defines the new wire) -> config write paths -> network-map object ->
      descriptor (supplies defaults) -> load/versioning/repair (consumes all four).
      The versioning machinery cannot precede the change it delivers (E24).
  D29 the pre-change golden corpus is KEPT as the conversion path's test fixtures and new
      goldens are cut alongside it. A deliberate, reviewed re-cut of a deliberately changed
      wire is not the regenerate-to-go-green that standing rule 3 forbids -- but deleting
      the originals would destroy the only first-party corpus of real old-shape documents.
  D30 008 is ONE feature -- one spec.md, one plan.md, one tasks.md -- that LANDS IN TWO
      GATED PHASES, split at the A-D / E seam:
        Phase 1 = ITEMs A, B, C, D  (timecode, config save(), network-map object, descriptor)
        Phase 2 = ITEM E            (validate-on-load, versioning, repair-and-notify)
      Phase 1 must be MERGED AND GREEN before any Phase 2 task starts -- the same rule §0
      applies between features, applied once inside this one. The seam is where the feature
      stops being four bounded changes to existing machinery and becomes one new subsystem
      whose central mechanism is still undesigned (E10): ITEM E is the only item that cannot
      be reviewed against something that already exists. Splitting there also means Phase 2
      is written against ITEM D's descriptor and ITEM B's save() as LANDED CODE rather than
      as planned interfaces, which is the whole point of the dependency order (D28).
      This is NOT a release boundary: D27 still holds and nothing ships until 009 lands.
  D31 the split is applied at a DELIBERATE STOP after /speckit.plan and before
      /speckit.tasks -- see §7.2. The plan covers all five items as one dependency chain;
      the stop is where that plan is cut into two phases and the gate between them is
      written down. Do not let /speckit.tasks emit one undifferentiated task list.
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

Follow the target design in specs/planning/xml-rebuild/xml-rebuild-06-target-design.md sections 3-6
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

Follow specs/planning/xml-rebuild/xml-rebuild-06-target-design.md section 7, and
specs/planning/xml-rebuild/xml-rebuild-04-object-model.md for the measured evidence and the
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
in specs/planning/xml-rebuild/xml-rebuild-06-target-design.md §8.1. "Convention, documented and tested"
is an acceptable answer; leaving it undecided while defining the persistence API is not.

REQUIRED DECISION STOP (2 of 2) — do not pass /speckit.clarify without resolving this. Feature 005
measured that the T2 tier is not three rules but FOURTEEN value-rejecting property setters,
every one of them bypassed on the load path and firing on the programmatic path only, plus
Uuid's own uuid4 rejection reached through set_id. 005 deliberately left that asymmetry
standing (its FR-006/FR-006a) because closing it would make reading stricter, which the
rebuild forbids. 006 is where it is decided. The inventory and the five questions the
decision must answer — read/write symmetry, a per-rule corpus sweep proving nothing
currently accepted becomes rejected, the setters' fate, the failure mode, and the unit of
registration — are in specs/planning/xml-rebuild/xml-rebuild-06-target-design.md §9.1 and §9.2. Record
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

Follow specs/planning/xml-rebuild/xml-rebuild-06-target-design.md sections 8, 9 and 10, and
specs/planning/xml-rebuild/xml-rebuild-05-ui-wire-contract.md for the wire contract evidence.

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

> **The last two paragraphs above were superseded by `/speckit.clarify` on 2026-08-24, and are
> left standing as the record of what was asked.** The clarification session decided the opposite
> on both counts: `network_map.xsd` **is** edited, and `node_type` **becomes** `node_role` typed as
> a real `NodeRoleType` enumeration over `controller`/`node`/`firstrun`. The reasoning is in
> `specs/007-node-model-migration/spec.md` §Clarifications — the schema is the single source of
> truth, this lands as a strong rebuild, and the rename is the migration `cuems-common/CLAUDE.md`
> already had scheduled. That decision is what makes 009 a hard successor rather than a follow-up,
> pulls `cuems-common` into 007's scope, and hands this feature the four items §7 lists.

```
/speckit.clarify
```
```
/speckit.plan <PASTE SHARED CONTEXT BLOCK>

Follow specs/planning/xml-rebuild/xml-rebuild-02-node-model-ownership.md sections 4 and 7.

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

## 7. Feature 008 — rebuild extension

**Gathered in conversation with the repo owner on 2026-08-25**, not derived from Part 3's
original eight phases — the team decided the rebuild's scope should grow before consumer
migration starts, since several more structural changes are cheaper as one coordinated pass now
than as independent releases later. Evidence for every claim below is
[Part 5's](xml-rebuild-08-extension-audit.md) `E1`–`E26`; read it before writing this feature's
actual `spec.md` — this section is the prompt, not the audit. **Part 5 was revised after a
review pass against the live code in all four repositories**; five of its original findings were
wrong or incomplete, and this section is written against the corrected versions. Its revision
table is the fastest way to see what changed.

**Five items, none of which strictly requires editing a consumer repository** (D16 makes it
*allowed*, not *required*) — closer in shape to 004–006 than to 007. Two of them (D17's
`Media.duration` type-and-wire change, D19's load-strictness reversal) change behaviour
consumers assume differently today, which is why §0's release-gate note extends 007's
no-independent-release logic through 009 rather than stopping at 008.

**The items are ordered as a dependency chain (D28), not by size or by what can run in
parallel.** Each is the next one's precondition: A defines the new wire, B and C complete the
config surface that the load path writes through, D supplies the defaults the repair path
recovers to, and E consumes all four. That ordering differs from the first draft's, where
validate-on-load sat second and the descriptor last.

**One feature, two gated phases (D30).** The chain has a natural seam between D and E: A–D are
four bounded changes to machinery that already exists and can be reviewed against it; E is one
new subsystem whose central mechanism is still undesigned (E10). So 008 keeps a single
`spec.md` and `plan.md` — the items are one dependency chain and one release unit, and
splitting the *spec* would mean reviewing that chain twice from two half-views — but
`tasks.md` carries a **hard phase gate**: Phase 1 (A–D) merged and green before any Phase 2
(E) task starts. That gate is applied at a deliberate stop after `/speckit.plan` (D31, §7.2).

Two things the gate buys, beyond a smaller diff to review at a time: Phase 2 is written
against ITEM D's descriptor and ITEM B's `save()` as **landed code** rather than as planned
interfaces — which is the point of ordering them first — and if ITEM E's design turns out to
be larger than the plan assumed, that discovery happens with four items already merged
instead of with the whole feature in flight. The gate is **not** a release boundary: D27
still holds and nothing in the ecosystem ships until 009 lands.

```
/speckit.specify <PASTE SHARED CONTEXT BLOCK>

Ship five structural changes as one coordinated feature, IN THIS ORDER because each is the
next one's precondition (D28): timecode typing, config write paths, the network-map config
object, the schema-derived descriptor, and validate-on-load with document versioning and
repair. Structural soundness outranks parallelization here -- do not re-sequence for
throughput. They are one feature rather than five because the dependency chain would
otherwise serialise the same work behind five review cycles, and because D27 already
establishes that none of them ships independently anyway.

One feature, but it LANDS IN TWO GATED PHASES (D30): Phase 1 is ITEMs A-D, Phase 2 is ITEM E,
and Phase 1 must be merged and green before any Phase 2 task starts. Write the spec for all
five items as one coherent whole -- the phase boundary is an implementation gate, not two
scopes -- but make each item's acceptance criteria standalone enough that Phase 1 can be
judged complete on its own. The gate is not a release boundary; D27 is unchanged.

ITEM A — timecode typing and canonical form (D17, D18, D18b, D29; E1-E6, E24):
- EVERY element carrying a time value is typed cms:CTimecodeType and stores a CTimecode
  object. Six already are and already do (offset, prewait, postwait on Cue; in_time,
  out_time on Region; duration on FadeCue -- all routing through format_timecode). The
  work is the SEVENTH: Media.duration, script.xsd:182, today typed cms:TimecodeType (a
  restricted string) and stringified by MediaCue.set_duration. Promote it to
  cms:CTimecodeType and put it on the same machinery as the other six. Remove the dead
  code the change leaves behind -- set_duration's three-branch type dispatch, the str
  branch of the media_duration T2 rule, and (verify first, it may still resolve via the
  inner <CTimecode> child) the "TimecodeType": _String() adapter binding.
- This is a script.xsd edit: the THIRD recorded exception to D3, and the only one that
  changes documents already on disk. The wire changes deliberately, in XML and JSON alike:
    <duration>00:00:30.000</duration>  ->  <duration><CTimecode>00:00:30.000</CTimecode></duration>
    "duration": "00:03:01.000"         ->  "duration": {"CTimecode": "00:03:01.000"}
  Do NOT write a "the wire is unaffected" golden check. An earlier draft of this prompt
  did, on the mistaken belief that Media.duration was bound to _CTimecodeAdapter. It is
  bound to _String(), whose to_wire returns the object unchanged -- there was never a
  version of this change that left the wire alone (E4).
- Instead: re-cut the goldens ONCE, deliberately and reviewably, and KEEP the pre-change
  corpus as the conversion path's fixtures (D29). Those files are the only first-party
  collection of real old-shape documents in existence; ITEM E converts them.
- settings.xsd's dead CTimecodeType/TimecodeType pair -- unreachable from any element,
  wrongly patterned HH:MM:SS:FF -- is DELETED, along with the Python model class that
  exists only to bind it for the coherence test. script.xsd's TimecodeType SURVIVES: it is
  the lexical type of the <CTimecode> child and is already the canonical HH:MM:SS.mmm.

ITEM B — config object write paths (D24; E15):
- Implement save() for settings, project_settings and project_mappings' config objects,
  symmetric to CuemsNetworkMapType.save() (network_map's, from 007 -- the only config
  write path that exists today).
- This is second, not fourth, because ITEM E needs it: backup-before-convert and
  repair-to-default both write, and three of the six domains currently cannot.

ITEM C — network-map config object (D22, D23; E11-E14, E23):
- NodeIndex/CuemsNetworkMapType in cuems-utils gain merge_discovered_nodes-equivalent,
  adopt/unadopt, refresh, set_master_always_adopted-equivalent,
  check_missing_adopted_nodes-equivalent, and a change-signature method -- the same shape
  ConfigManager/ConfigBase already have for the other five schemas. This logic is
  currently reimplemented ad hoc on cuems-nodeconf's CuemsNodeConf daemon class (756
  lines, ten bundled responsibilities, cataloged in E11's corrected table) and does not
  exist in cuems-utils at all today.
- Prove equivalence by MEASUREMENT, not assertion (E23). 008 ships this API with no
  first-party caller -- 009 does the swap -- so port CuemsNodeConf's current behaviours
  into cuems-utils as characterization tests. merge_discovered_nodes, _map_signature,
  adopt_node/unadopt_node and set_master_always_adopted are pure enough over a NodeIndex
  to be pinned this way.
- Design the API against its real caller AND its real user: cuems-nodeconf's
  engine_callback (E14) is the dispatch path, and cuems-frontend's settings.component.ts
  (E20) is the UI that originates every adopt/unadopt on the far end of it. That chain
  works today; whatever this feature builds has to keep it working once 009 migrates it.
- Do NOT execute cuems-nodeconf's full atomization (the other nine responsibilities in
  E11's table) here. Record the target-design basis for it -- which responsibilities are
  single-class candidates and why -- as this feature's deliverable, so it can become its
  own dedicated cuems-nodeconf feature later. That basis MUST account for E20/E25: row 5
  has a live UI at the end of its dispatch chain and cannot be designed as if headless.
- Fix or delete the dead code found while reading CuemsNodeConf: cleanup() (line 579)
  reads self.cm.show_lock_file at line 581; self.cm is never assigned anywhere (E13).

ITEM D — schema-derived descriptor (D25; E16-E17, E19, E26):
- Build a standalone schema descriptor -- new machinery, independent of the runtime object
  model, walking the parsed XSD directly (may share underlying xmlschema schema objects
  with the existing registry) -- covering ALL SIX schemas. Per type, emit: field name, XSD
  type, cardinality (required/repeated), the legal value list read from xs:enumeration
  where the type is a restricted enumeration, AND THE MODEL-LAYER DEFAULT.
- Defaults are NOT optional, and this is where the first draft was thinnest. Two
  independent consumers need values rather than shape: ITEM E's repair-to-default path has
  no other source of truth (hand-written per-field fallbacks would recreate exactly the
  drift this descriptor exists to end), and at least two of the frontend's template call
  sites read concrete values out of initial_template today -- sequence.component.ts:688
  takes the example AudioCue's master_vol, :727 maps the example DmxCue's dmx_channels
  (E19). A shape-only descriptor gives 009 nothing to migrate those onto.
- FieldSpec (004) carries name/xsd_type/required/repeated/order/kind/child and neither
  enum facets nor defaults (E17). Decide whether to extend it or to build alongside it;
  either is fine, but say which and why.
- create_script() is SUPERSEDED, not preserved. Its output need not stay byte-identical
  and its faulty logic need not be carried forward -- note in particular that it validates
  and THEN blanks ids, so the object actually served would fail its own check, and its
  dangling action_target is what cuems-editor's _clean_dangling_targets exists to sweep up
  (E16, E18: one causal chain currently documented in three disconnected places).
- templates/settings.xml is the second hand-maintained template (E26): 5.1 KB of
  hand-written reference instance, referenced by no code and no test, unpackaged, while
  settings.xsd's own header declares it a binding contract ("any change to this schema MUST
  be reflected in the template"). The descriptor should be able to generate it, and that
  header should stop asserting a hand-maintenance obligation once it can.
- Do NOT attempt the frontend/editor cutover here -- that is 009's (D26). Record the
  handoff in the migration guide at per-call-site granularity, as 007 did.

ITEM E — validate() on load(), versioning, and repair (D19-D21; E7-E10, E21, E22, E24):
- CuemsScript.load() and every ConfigManager/ConfigBase accessor run full validate()
  (T1 AND T2). This REVERSES "reading never becomes stricter" (FR-026, standing rule 8) --
  record the reversal explicitly in this feature's spec; do not let it read as an oversight.
- THREE outcomes, not two (D21). This is the part the first draft got wrong by omission:
    OLD document (version marker precedes current) -> convert transparently in memory,
      timestamped backup written first; the same logic also ships as a standalone tool for
      batch/offline/postinst use.
    CURRENT BUT SEMANTICALLY INVALID -> repair-and-notify: recover a default state for the
      offending field (from ITEM D's descriptor), carry the repair in a structured report,
      continue loading.
    UNREPAIRABLE -> raise.
  A document that is corrupt AND current-version is the common case and the versioning
  machinery does not help it. Without the middle row it simply becomes unloadable -- and
  every tool that would repair it is itself a load() consumer (E18, E21).
- The repair report is PUBLIC, under cuemsutils.errors, on 006's precedent that an
  exception the caller cannot name is one it cannot catch: a repair the caller cannot
  inspect is one it cannot surface. cuemsutils has no UI channel and must not gain one --
  008 produces the report, 009 forwards it to the UI as a WS message.
- A new EXPLICIT, systemic document-version marker is designed and built -- not another
  bespoke per-change tell like 007's node_type/node_role presence check. Where it lives
  (root attribute vs dedicated element, per-schema vs document-wide) and how it composes
  with T1 validation is this feature's design work, not decided here (E10). Its FIRST REAL
  CLIENT is ITEM A's Media.duration conversion (E24) -- every script.xml in every library
  becomes an old-version document the moment ITEM A lands, so the mechanism is validated
  against a real migration in the same feature that introduces it.
- Be honest about T2 coverage (E22): every registered semantic rule targets a script.xsd
  type except one project_mappings rule. settings, project_settings, network_map and
  outputs have ZERO T2 rules today, so "T2 across all six schemas" is mostly plumbing
  there. Say so in the spec, or the measured cost gets attributed to enforcement that is
  not happening.
- Measure the performance cost against the constitution's Principle IV budget. CURRENT
  baseline is feature 007's, not 006's: 2393 passed / 94 skipped / 2 xfailed in 59.33 s =
  24.79 ms/test (specs/007-node-model-migration/baseline.md, measured 2026-08-24). The
  strictness is intentional despite the cost, but the cost must be a number.

WHAT MUST BE TRUE WHEN DONE:
- All SEVEN timecode-carrying elements are cms:CTimecodeType and store CTimecode objects;
  zero string-stored exceptions; the dead code the change exposed is gone, not orphaned.
- The Media.duration wire change is proven by a reviewed golden re-cut, and the pre-change
  corpus survives as the conversion path's fixtures.
- settings.xsd's dead CTimecodeType/TimecodeType and its Python binding no longer exist;
  script.xsd's TimecodeType still does.
- settings, project_settings and project_mappings config objects have a working save().
- cuems-utils exposes a network-map config object with adopt/unadopt/merge/refresh/
  signature/save, independent of cuems-nodeconf, with characterization tests pinning it to
  CuemsNodeConf's current behaviour.
- A schema-derived descriptor exists for all six schemas emitting types, cardinality,
  xs:enumeration values AND defaults; create_script() is gone, replaced by it.
- load() and every config accessor run T1+T2 across all six schemas, with all three
  outcomes exercised by tests: an old document converts (with a backup), a corrupt-but-
  current document repairs to default and reports, an unrepairable one raises.
- A document-version marker exists, is read by that check, and carries ITEM A's conversion.
- A migration guide entry exists for every item with consumer impact, at the call-site
  granularity E14/E18/E19/E21 establish, ready for 009 to execute against.

EXPLICITLY OUT OF SCOPE: cuems-nodeconf's full daemon atomization (basis only, per ITEM C);
any consumer repository edit not strictly required to prove an item works (D16 permits, does
not mandate); the frontend/editor template and config-form cutover (009's, per D26);
repair_durations.py's own migration (009's, per E21 -- 008 owns only the library side that
makes it viable). NOTE: this feature does NOT ship independently despite touching no consumer
repository directly (D27) -- nothing in the ecosystem releases until 009 lands, same gate 007
established.
```

### 7.1 Clarify and plan

This subsection runs as far as `/speckit.plan` and **stops there**. §7.2 is the stop; §7.2's
tail carries tasks through both implement passes.

```
/speckit.clarify
```

Not skippable, for the same reason it was not skippable for 006: this feature carries a
principle reversal (D19, "reading never becomes stricter") and a new systemic mechanism
(D20's version marker) that need their design questions answered before `/speckit.plan` runs.
At minimum:

- **Where the version marker lives**, and how it composes with T1 (E10) — the one genuinely
  undesigned mechanism in the feature.
- **What "a default state" means per field** for repair-and-notify (D21's middle row): the
  descriptor's declared default, or something narrower for fields where a default is
  semantically wrong (a dangling `action_target` repaired to `None` is a real change of
  meaning, not a restoration).
- **The repair report's shape** — what a caller must be able to answer from it in order to
  render a useful notification (which document, which field, what was there, what replaced
  it, is the file now different from what is on disk).
- **Whether ITEM A's conversion is also `repair_durations.py`'s Pass B** (E21). Both rewrite
  `<duration>` across every project XML; building the rewriter twice is the failure mode.

Two questions that are **not** open. D27 settles the release gate: 008 does not ship
independently regardless of touching no consumer repository directly. And `create_script()`'s
fate is settled by D25 — it is superseded, and its output does not have to stay
byte-identical; the first draft left this open and it no longer is.

```
/speckit.plan <PASTE SHARED CONTEXT BLOCK>

Follow specs/planning/xml-rebuild/xml-rebuild-08-extension-audit.md for the evidence behind
every item above -- the REVISED version; its revision table lists five findings the first
draft got wrong. This feature has no single target-design section to follow the way 005-007
followed xml-rebuild-06-target-design.md -- write ITEM C's config-object shape and ITEM D's
descriptor shape as this feature's own data-model.md, informed by the existing
ConfigManager/ConfigBase and TypeSpec/FieldSpec patterns respectively.

Technical context, in item order:
- ITEM A touches script.xsd (Media.duration's type -- a D3 exception), settings.xsd (one
  deletion), cues/MediaCue.py (setter + DECLARED_DEFAULTS comment), xml/adapters.py (the
  TimecodeType binding, verify before removing), xml/validators.py (media_duration's dead
  str branch), config/settings.py (the CTimecodeType model class), and the golden corpus
  under tests/data/corpus + tests/golden (re-cut, originals retained per D29).
- ITEM B touches config/settings.py, config/mappings.py (project_settings and
  project_mappings live there) plus their ConfigManager accessors.
- ITEM C touches tools/NodeList.py (NodeIndex, currently 3 methods, ends at line 88) and
  config/network_map.py (CuemsNetworkMapType, currently only save()) -- cuems-nodeconf is
  read for its behaviour but not edited by this feature.
- ITEM D is new: likely a new module under xml/ or a new top-level templates.py, reusing
  the registry's already-loaded xmlschema schema objects rather than reparsing. It deletes
  create_script.py and should be able to generate templates/settings.xml.
- ITEM E touches cues/CuemsScript.py (load), tools/ConfigManager.py + tools/ConfigBase.py
  (every accessor), errors.py (the public report type), and adds the version-marker and
  conversion machinery plus its standalone tool entry point.

Note the two cross-item couplings that make the order non-negotiable (D28): ITEM E's
backup-and-convert writes through ITEM B's save(), and ITEM E's repair-to-default reads
ITEM D's defaults. Neither is optional plumbing.

PLAN FOR ALL FIVE ITEMS AS ONE CHAIN, but write the plan knowing it will be cut in two at the
A-D / E seam (D30) before tasks are generated. Concretely, that means two things: state each
item's acceptance criteria so ITEMs A-D can be judged complete WITHOUT ITEM E existing, and
make ITEM E's dependencies on ITEM B's save() and ITEM D's descriptor explicit as INTERFACES
-- named, with their shapes fixed in data-model.md -- because Phase 2 will be implemented
against them as landed code, not as a plan section.

Constitution check:
- II: each of the five items needs a fail-then-pass test, same discipline as 005's six
  behaviour changes. ITEM E especially: the version-marker mechanism, the auto-convert path
  and each of D21's three outcomes need round-trip tests, not unit tests of their pieces.
  ITEM C's characterization tests (E23) are the II discipline applied to code this
  repository does not own yet -- write them against CuemsNodeConf's current behaviour
  BEFORE porting, so the port is measured rather than reviewed by eye.
- IV: ITEM E's load()-strictness cost must be measured against the CURRENT baseline
  (007's: 24.79 ms/test over 2393 tests), not 006's, and not assumed acceptable because
  the requirement says so.
- III: every item with consumer impact gets a migration-guide entry at 009 handoff.
- Standing rule 3: ITEM A re-cuts goldens deliberately. That is not the regenerate-to-pass
  the rule forbids, but it MUST be a reviewed diff with the originals retained (D29), and
  the spec must say so plainly rather than letting a large golden diff appear unexplained.
```

### 7.2 STOP — cut the plan at the A–D / E seam

**Do not run `/speckit.tasks` yet.** This is a deliberate stop, and the only one in the whole
rebuild (D31). Every other feature runs `/speckit.plan` straight into `/speckit.tasks`; this
one does not, because a single undifferentiated task list would let ITEM E's work interleave
with ITEM A–D's and quietly dissolve the gate D30 exists to enforce.

At this stop, do four things and write them into `plan.md` before generating tasks:

1. **Declare the phase boundary.** Phase 1 = ITEMs A, B, C, D. Phase 2 = ITEM E. Phase 1 must
   be **merged and green** before any Phase 2 task starts — the rule §0 applies between
   features, applied once inside this one.
2. **Fix the two hand-off interfaces in `data-model.md`**, by name and shape: the config
   objects' `save()` signature (ITEM B) and the descriptor's emitted structure including
   defaults (ITEM D). Phase 2 is implemented against these as landed code. If they are still
   negotiable when Phase 1 merges, the gate has bought nothing.
3. **Check Phase 1 stands alone.** Read ITEMs A–D's acceptance criteria and confirm each can
   be judged complete with no part of ITEM E in the tree. If any criterion needs
   validate-on-load, versioning or repair to be true, it belongs in Phase 2 — move it.
4. **Restate what the gate is not.** It is not a release boundary (D27 is unchanged, nothing
   ships until 009), and it is not a scope split (one `spec.md`, one `plan.md`, one feature
   number, one migration guide).

Then generate tasks with the boundary already in them:

```
/speckit.tasks

tasks.md MUST carry the D30 phase gate as structure, not as a comment. Group every task under
Phase 1 (ITEMs A-D) or Phase 2 (ITEM E), and put an explicit gate task between them: Phase 1
merged, suite green, the two hand-off interfaces (config save(), descriptor-with-defaults)
landed and stable. No Phase 2 task may be marked parallel-safe with a Phase 1 task.
```
```
/speckit.optimize
```

Run `/speckit.optimize` here rather than in §9's generic loop, and read its output against
D28: it looks for parallelisation, and this feature has deliberately given some up. Accept
its findings **within** a phase; reject any that reorder across the seam or move work earlier
than the item it depends on. The dependency chain is the design, not an artefact to optimise
away.

```
/speckit.checklist Reversal-and-addition review: the load()-strictness reversal (D19) has an
explicit decision record and is not silently mixed in with the other four items; D21's THREE
outcomes are each separately specified and separately tested, and the corrupt-but-current
case is not collapsed into the old-document case; the version-marker mechanism has a design,
not just a working example, and ITEM A's conversion exercises it; the descriptor emits
defaults and not only shape, checked against every enumeration and every default the six
schemas actually declare; the Media.duration wire change is a named, reviewed golden re-cut
with the pre-change corpus retained; the settings.xsd deletion is proven safe by the same
coherence-test discipline T041 established, and script.xsd's TimecodeType is proven still
live; every consumer-impacting change has a migration-guide entry naming the call site, not
the repository -- including repair_durations.py, which the first audit pass missed. Plus the
phase gate: every task is assigned to Phase 1 or Phase 2, no Phase 2 task is reachable before
the gate, and ITEMs A-D's acceptance criteria are judgeable without ITEM E in the tree.
```
```
/speckit.analyze
```

`/speckit.implement` runs **twice**, once per phase, with a merge between them:

```
/speckit.implement   # Phase 1 only — ITEMs A, B, C, D
```

**Phase 1 exit:** ITEMs A–D's "what must be true when done" bullets pass; suite green within
the measured budget; the `script.xsd` promotion (D18b), the `settings.xsd` deletion and the
golden re-cut (D29) are each a named, reviewable decision rather than a silent diff; and the
two hand-off interfaces — config `save()` and the descriptor-with-defaults — are landed and
stable. **Merge before continuing.**

```
/speckit.implement   # Phase 2 only — ITEM E, against Phase 1 as landed code
```

**Phase 2 exit:** ITEM E's bullets pass; all three of D21's outcomes are exercised by tests
(convert with backup, repair-to-default with report, raise); the load-strictness reversal
(D19) is a named decision in the spec; the version marker carries ITEM A's conversion; and
the strictness cost is a measured number against 007's baseline.

**Feature exit:** both phases green; the migration guide complete at call-site granularity for
009, covering every item with consumer impact including `repair_durations.py`. Nothing ships —
D27 holds until 009 lands.

---

## 8. Feature 009 — consumer migration

Cross-repo. This spec lives in `cuems-utils` and defines the **contract and guide**; the
edits happen in each consumer repo as its own PR.

**Updated 2026-08-24** from feature 007's migration checklist, which handed four items to this
feature and changed its standing from follow-up to release gate. **Updated again 2026-08-25**
from feature 008 (§7), which widens this feature's scope substantially: `cuems-nodeconf` and
`cuems-frontend` go from "no change required" (as this section originally read) to real migration
targets. See §7's ITEMs C, D and E for what 008 hands here, and
`xml-rebuild-08-extension-audit.md`'s E14/E18–E21/E25 for the call-site evidence — **the revised
version**, whose corrections all land in this feature's scope rather than 008's.

**009 is a hard successor to 007, not a follow-up, and 008 extends the same gate.** 007 renames
`<node_type>` to `<node_role>` as a **hard cutover** — no release accepts both spellings — so
there is no working partially-deployed state between them. 008 then changes behaviour
(`Media.duration`'s type **and wire shape**, `load()`'s strictness) that existing consumers assume
differently today, without itself editing any consumer repository (§0). **Nothing in the ecosystem
ships until this feature lands** (007 FR-030c/FR-030d, extended through 008 — see §0's
release-gate note). Read `specs/007-node-model-migration/migration-guide.md` **and**
`xml-rebuild-08-extension-audit.md` first; both are this feature's input, not context.

**One thing 008 hands here that has no 007 analogue: a wire change to every project file on
disk.** `<duration>TC</duration>` becomes `<duration><CTimecode>TC</CTimecode></duration>`
(D17/D18b). Unlike the `node_role` rename, this touches *show* documents — the library's
contents, not one config file per node — so the conversion runs against user data at scale and
the backup path is load-bearing rather than precautionary.

Two of 007's findings shape the work before any prompt runs:

- **Semantically-wrong callers are a named class** (007 FR-030a-ii). A caller that stops resolving
  fails loudly at import; one in this class keeps running and returns the wrong answer —
  `CONTROLLER_NETWORK_FLAG`'s string comparison, the role enum comparisons, the `node_type`
  normalisations. Nothing fails when one is missed, so they are **searched for**, not waited for.
  A green suite is not evidence this class is empty.
- **The node model and its full testing live in `cuems-utils` exclusively** (007 FR-030a-i). No
  consumer re-implements or re-tests it. A node-model test appearing in a consumer repo during this
  migration is a regression, not coverage.

Six of 008's items shape additional work, on top of 007's:

- **`cuems-nodeconf` now has real work here.** 008 built a network-map config object
  (adopt/unadopt/merge/refresh/signature/save) in `cuems-utils`; `CuemsNodeConf`'s ad hoc
  equivalents (E11's row 5, **including `refresh_network_map`**, which the first audit pass left
  unplaced) are replaced with calls into it. 008 deliberately did **not** touch `cuems-nodeconf`'s
  other nine bundled responsibilities (E11's full table) — this feature consumes the
  config-object swap only. The full daemon atomization stays a **future, separate**
  `cuems-nodeconf` feature; 008 recorded the target-design basis for it, and this feature's job
  is to leave that basis intact for whoever picks it up next, not to execute it. 008's
  characterization tests (E23) are the yardstick: the swap is done when they still pass against
  the new API, not when the code looks equivalent.
- **`cuems-editor`'s `CuemsDBProject` migration is bigger than previously recorded here.** The
  plan below originally said "the three `CuemsParser` call sites" — corrected to **four**
  (`update`:356, `new`:489, `duplicate`:571, `update_projects_existed_media`:808; E18) by 008's
  audit pass. Each also does business logic as **raw dict mutation on the JSON payload before
  parsing** — `_clean_dangling_targets`/`_nullify_dangling_refs` (387–437), `_fix_media_durations`
  (367), id/date stamping — which 008's load-strictness reversal (D19) makes mandatory to fix
  regardless of the template decision below: once `from_json()` validates, these fixups must run
  as sanctioned pre-validation repair steps or become real object-level operations, not ad hoc
  dict pokes on data about to hit a stricter parser. **Check them against 008's repair-and-notify
  path before rewriting them** — some of what they do (dangling-target nullification, duration
  repair) is now the library's job, and duplicating it in the editor is how the two drift apart.
- **A fifth `CuemsParser` call site, missed by the first audit pass: `repair_durations.py`**
  (line 230, plus a deprecated `XmlReaderWriter` import at line 40; E21). It is not in
  `CuemsDBProject.py`, which is why the four-site count missed it, and it needs the most care of
  any site here because it sits at the intersection of everything 008 changed:
  it exists to *load deliberately-corrupt documents* (its whole purpose is repairing durations
  stored short by a historical `get_duration` bug); it hard-codes the old wire shape
  (`TIMECODE_SHAPE = ^\d\d:\d\d:\d\d\.\d\d\d$` matched against `<duration>` text content); and
  its **Pass B — rewriting `<duration>` in every project `script.xml` — is the same job as 008's
  standalone conversion tool.** Migrate it off `CuemsParser`/`XmlReaderWriter`, drop the private
  regex for the library's canonical form, and **fold Pass B into the conversion tool rather than
  maintaining a second XML rewriter.** Its ffprobe/DB half (Pass A) stays editor-local — that
  part is genuinely the editor's domain.
- **`cuems-frontend` and `cuems-editor` gain the template/config cutover** (008 §7 ITEM D,
  D25/D26). Script domain: retire `initial_template`-as-a-concrete-instance; migrate the ~7 call
  sites in `project-create.handler.ts` and `project-edit/sequence/sequence.component.ts` (E19)
  onto the new schema descriptor. **Two of those sites read concrete values, not shape** — line
  688 takes the example `AudioCue`'s `master_vol`, line 727 maps the example `DmxCue`'s
  `dmx_channels` — so they migrate onto the descriptor's *defaults*, which is why 008 was
  required to emit them.
- **Config domain is a MIGRATION, not a greenfield build** — the first draft of this section had
  this backwards (E20). A `network_map` **editing** UI exists and is in daily use:
  `src/app/components/settings/settings.component.ts` emits
  `{action:'nodelist_modify', modify_action:'ADD'|'REMOVE'}` and reads node state from
  `initialMappings()`; `audio-mixer.component.ts:80` and `video-mixer.component.ts:94` consume
  `initial_mappings` too. **Port the existing machinery onto the new dynamic-form entities with
  its logic preserved** — this is not a rewrite from nothing, and adopt/unadopt must keep working
  through the port. Two structural traps to plan around (E25):
  1. **The domains are entangled on the wire.** `CuemsWsServer.reload_network_map_nodes` (439)
     merges `network_map.xml` node status *into* `mappings_dict`, served as `initial_mappings`
     (509–511). A `network_map` edit reaches the UI inside a `project_mappings` payload.
     Untangling it is a simultaneous behaviour change for three components.
  2. **The WS pattern already exists.** Model the new per-domain message types on
     `initial_mappings` (serve) + `nodelist_modify` (accept a mutation) — a config domain that
     already has both halves — rather than on `initial_template`, which is serve-only.
     Incidentally: `settings.component.ts` is named for the `settings` domain and edits
     `network_map` nodes. Do not let the new per-domain views inherit that naming.
  Consider serving **partial** elements on demand (a script sub-object, a DB-backed duration
  query) rather than full payloads client-side, if it simplifies the new UI entities — a design
  option for this feature's `/speckit.plan`, not a requirement fixed by 008.
- **008's repair report needs a UI path.** `load()` now returns structured repair information
  when it recovers a corrupt document to a default state (D21). `cuemsutils` deliberately does
  not notify anyone — it has no UI channel and must not gain one. This feature builds the rest:
  `cuems-editor` surfaces the report as a WS message, the frontend renders it. A silent repair is
  the failure mode the whole three-outcome design exists to avoid.
- **Config `save()` existing in `cuems-utils` (008 ITEM B) is a precondition**, not something
  this feature builds — confirm it lands before writing the config-domain UI's save path against
  it.

```
/speckit.specify <PASTE SHARED CONTEXT BLOCK>

Define and execute the consumer migration to the new public API, coordinated as a single
version bump across the CUEMS ecosystem. Feature 007's migration guide
(specs/007-node-model-migration/migration-guide.md) is the input inventory: it carries the
moved-symbol table, every changed name and type against its live call site, the release
gate, and the items 007 deferred here by name.

WHAT MUST BE TRUE WHEN DONE:
- A migration guide in this repo maps every removed or changed entry point to its
  replacement, with before/after examples.
- cuems-engine obtains scripts via CuemsScript.load and consumes typed node objects, and
  adopts NetworkMap.partition_by_adoption in place of its inline workaround for the
  mutating get_nodes_by_adoption. CONTROLLER_NETWORK_FLAG = "NodeType.master" becomes
  NodeRole.controller at all three sites (the constant and its two comparisons).
- cuems-editor uses CuemsScript.load/save and from_json, and its project load path returns
  script.to_wire() so the payload sent to the UI is byte-identical to today's. Its node
  field list at CuemsWsServer.py:425 and the reload_network_map_nodes reads follow the
  node_role rename and the retyping: node_role is a NodeRole, adopted/online are bool,
  uuid is a Uuid.
- cuems-common's Avahi discovery surface follows the role vocabulary: the node_type TXT
  record in etc/avahi/services/cuems.service and usr/share/cuems/cuems.service.{master,
  slave,firstrun}. In the last two the retired word is in the FILENAME, so the change
  reaches debian/install and anything resolving a template by name. Feature 007
  inventoried these and deliberately left them (its Assumption 10, and they are the named
  exclusion in its SC-004a count) because discovery is out of its scope — out of scope
  there is not exempt.
- cuems-common's postinst ordering is settled: the network-map conversion and
  dh_installsystemd's service restart both run in postinst, and their relative order
  decides whether a service reads the converted map or the old one. Feature 007 deferred
  this here (its FR-011d-ii) because the services doing the reading are the ones this
  feature migrates.
- cuems-nodeconf's node model and serializers are done, from feature 007 — confirm, do not
  redo. Its **network-map config-object logic** (adopt/unadopt/merge/refresh/signature/write)
  is new work for this feature: swap `CuemsNodeConf`'s ad hoc methods (E11 row 5, including
  refresh_network_map) for calls into 008's `NodeIndex`/`CuemsNetworkMapType` API. 008's
  characterization tests are the yardstick — the swap is done when they pass against the new
  API. `engine_callback`'s `nodelist_modify` dispatch (E14) is the caller to migrate against,
  and cuems-frontend's settings.component.ts is the UI at the far end of it that must keep
  working. `cleanup()`'s dead `self.cm` reference (E13) is fixed or deleted while the file is
  open for this anyway.
- cuems-frontend's `=== true || === 'True'` dual-check simplification is still optional, a
  follow-up not a blocker. Its **template-cloning surface is not optional**: the ~7 call
  sites in `project-create.handler.ts` and `project-edit/sequence/sequence.component.ts`
  move off cloning `initial_template` onto the schema descriptor (008 ITEM D) — including the
  two that read concrete values (master_vol at :688, dmx_channels at :727), which migrate onto
  the descriptor's defaults. **Config-domain UI is a PORT, not a new build**: a network_map
  editing UI already exists (settings.component.ts, nodelist_modify adopt/unadopt) and
  project_mappings already has read consumers (audio-mixer, video-mixer). Move them onto a
  generic schema-form-renderer with their logic preserved, untangle the
  network_map-inside-initial_mappings payload (E25), and generalise the existing
  initial_mappings/nodelist_modify WS pair rather than inventing an unrelated one.
- cuems-editor's `CuemsDBProject` moves off `CuemsParser` at all **four** call sites (`update`,
  `new`, `duplicate`, `update_projects_existed_media` — corrected from three; E18), and its
  raw-dict pre-parse fixups (dangling-target nulling, duration repair, id/date stamping)
  become sanctioned pre-validation steps or object-level operations, not dict pokes ahead of
  a now-strict parse — checked against 008's repair-and-notify path first, so the editor does
  not duplicate repairs the library now performs.
- **`repair_durations.py` is the fifth CuemsParser call site** (line 230; E21) and needs
  handling on its own terms: off `CuemsParser`/`XmlReaderWriter`, off its private
  `TIMECODE_SHAPE` regex, with **Pass B folded into 008's standalone conversion tool** rather
  than kept as a second `<duration>` rewriter. Pass A (ffprobe + DB) stays editor-local. It
  must still be able to read the corrupt documents it exists to repair — which is what 008's
  repair-and-notify contract guarantees; verify that, do not assume it.
- **008's repair report reaches the user**: cuems-editor forwards it as a WS message and the
  frontend renders it. A repair that happens silently is the outcome D21's design exists to
  prevent, and cuemsutils cannot do this half itself.
- Deprecated entry points are removed from cuemsutils only after all consumers are on the
  new API.
- Zero occurrences of node_type or the NodeType. prefix remain anywhere in the ecosystem,
  counted rather than reviewed — including the four files 007 excluded from its own count
  and handed here.
- All 008 items with consumer impact are verified against each live call site 008's migration
  guide named, the same discipline 007 required of this feature for the node-model rename:
  `Media.duration`'s type AND wire change (cuems-engine's `CTimecode(cue.media.duration)`,
  the editor's duration read/write paths, the frontend's media-duration display — which now
  unwraps `{"CTimecode": ...}` the way it already does for fades); `load()`/config accessors
  validating; and the document-version marker's presence.

CALLERS THAT KEEP RESOLVING BUT BECOME WRONG are a distinct class from callers that stop
resolving (007 FR-030a-ii), and the second kind is the dangerous one: nothing fails, the
suite stays green, and the answer is silently wrong. Search for them against 007's
inventory rather than relying on a red suite to surface them.

DO NOT re-implement or re-test the node model in any consumer repository. It lives in
cuemsutils exclusively (007 FR-030a-i).

VERIFICATION: an end-to-end check that a project saved by the editor loads in the engine
and renders in the UI unchanged, plus a cluster upgrade — controller and at least one node
— that comes back with its topology intact.
```

```
/speckit.plan <PASTE SHARED CONTEXT BLOCK>

Follow specs/planning/xml-rebuild/xml-rebuild-06-target-design.md section 12.

Per-repo scope:
- cuems-engine: core/BaseEngine.py:509; ControllerEngine network-map access; adopt
  NetworkMap.partition_by_adoption; CONTROLLER_NETWORK_FLAG and its two comparison sites.
- cuems-editor: CuemsDBProject.load_xml / save_xml / all FOUR CuemsParser call sites in that
  file (update:356, new:489, duplicate:571, update_projects_existed_media:808 — E18) PLUS the
  fifth in repair_durations.py:230 (E21, missed by the first audit pass); DBProject.load must
  return script.to_wire(); the node field list at CuemsWsServer.py:425 and the
  reload_network_map_nodes reads; the raw-dict pre-parse fixups moved to sanctioned
  pre-validation steps or object operations, checked against 008's repair path first; WS
  message types generalising initial_mappings/nodelist_modify to serve the schema descriptor,
  accept config-domain saves, and forward 008's repair report.
- cuems-common: the Avahi node_type TXT record in etc/avahi/services/cuems.service and
  usr/share/cuems/cuems.service.{master,slave,firstrun}, INCLUDING the filenames of the
  master/slave templates and the debian/install entries that place them; and the postinst
  ordering of the network-map conversion against dh_installsystemd's service restart. NOTE
  that 008 adds a SECOND conversion to that ordering problem — the script-document duration
  conversion — with different timing characteristics: it runs over the whole project library,
  not one config file, so postinst may not be the right place for it at all.
- cuems-nodeconf: node model/serializers — nothing, done in 007, verify rather than repeat.
  Network-map config-object calls (adopt_node, unadopt_node, merge_discovered_nodes,
  refresh_network_map, write_network_map, _map_signature) swapped for 008's cuems-utils API,
  with 008's characterization tests as the equivalence yardstick; engine_callback updated to
  match; the self.cm dead-code bug in cleanup() fixed or removed.
- cuems-frontend: template-cloning call sites in project-create.handler.ts and
  project-edit/sequence/sequence.component.ts moved onto the schema descriptor (the two
  value-reading sites onto its defaults); the EXISTING config-domain UI — settings.component.ts
  (network_map adopt/unadopt), audio-mixer and video-mixer (initial_mappings) — ported onto the
  form-renderer with its logic preserved, not rebuilt; media-duration display updated for the
  {"CTimecode": ...} wrapper; repair-report rendering; optional === true || === 'True'
  dual-check cleanup as a follow-up, not a blocker.

Sequencing: this is where the 007 release gate opens, extended through 008 (§0). Nothing
ships between 007/008 and this feature (007 FR-030c/FR-030d, extended), so "cuemsutils
releases first with both APIs live" does NOT apply to the node surface or to 008's
load-strictness and duration type/wire changes — both are hard cutovers with no dual-spelling
state. It still applies to the show-API deprecations from 006. Keep the three apart in the plan.

Data migration is a first-class concern here in a way it was not for 007. 007 converted one
config file per node; 008's duration change converts EVERY project document in EVERY library.
Plan the rollout for that scale: when the conversion runs, what happens to a library mid-
conversion, how the backups are retained and reclaimed, and what an operator sees while it
works.

Constitution check:
- II: each consumer PR carries its own green suite. The end-to-end check is the gate. Note
  that a green suite does NOT evidence the FR-030a-ii class — those callers keep resolving.
  Each one needs a test that fails against the old value.
- III: the migration guide is the UX deliverable. Features 007's AND 008's guides are its
  input.
- IV: no regression in engine project-load time — and note that 008 added T1+T2 validation to
  that path, so measure against 008's post-landing figure, not 007's baseline, or the budget
  charges this feature for 008's decision. Network-map load stays within 007's recorded budget.
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
Plus, from feature 007's handover: every caller in the "keeps resolving but becomes
semantically wrong" class accounted for with a test that fails against the old value;
zero node_type occurrences ecosystem-wide including the four files 007 excluded; the
postinst-vs-service-restart ordering decided rather than inherited; and the cluster upgrade
verified, not only the single-node one. Plus, from feature 008's handover: cuems-nodeconf's
network-map calls verified by 008's characterization tests rather than assumed equivalent;
ALL FIVE CuemsParser call sites accounted for — the four in CuemsDBProject plus
repair_durations.py, which the first audit pass missed and which is the site most exposed to
008's changes; the raw-dict fixups' new sanctioned form proven to still catch what it used to
(dangling targets, bad durations) under the validating load path, WITHOUT duplicating repairs
the library now performs; repair_durations.py proven able to still read the corrupt documents
it exists to repair; every project document converted to the new duration shape, counted not
sampled, with backups accounted for; the ported config-domain UI proven to still adopt and
unadopt nodes end to end; and the descriptor-driven forms checked against every enumeration
AND every default the six schemas actually declare, not a hand-picked subset.
```

**Exit criteria:** all consumers migrated and green; end-to-end save→load→render verified;
a controller-plus-node cluster upgrade comes back with its topology intact; zero `node_type`
occurrences ecosystem-wide, counted; the FR-030a-ii caller class closed with per-caller tests;
deprecated surface removable; `cuems-nodeconf` consumes the 008 network-map config object with
008's characterization tests still green against it; `initial_template`-as-instance retired in
favour of the schema descriptor for the script domain; the existing config-domain UI ported to
descriptor-driven forms with adopt/unadopt still working end to end, and the remaining three
config domains newly editable through the same renderer; every project document in a real
library converted to the new duration shape with its backup retained; and a repaired document
produces a notification the user actually sees.

---

## 9. Per-feature quality loop

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

**Feature 008 runs this loop per phase, not per feature** (D30). `check-integration` and
`optimize` before Phase 1's implement, then again before Phase 2's — Phase 2's tasks are
written against interfaces that only became real when Phase 1 merged, so re-running
`check-integration` there is the point rather than a repetition. `verify` likewise runs
twice, against each phase's exit criteria in §7.2. And 008 keeps `optimize`'s findings
**within** a phase: it optimises for parallelism, which D28 deliberately traded away.

---

## 10. Standing rules for every feature

1. **Never** run `/speckit.implement` on a red suite. Baseline is 557 passing.
2. The **D14 chain test is written before the machinery it guards**, against current
   behaviour. This is the single most important sequencing rule in the whole rebuild.
3. Golden files for XML output and the `read()`/`to_wire()` dict are generated **once**,
   from pre-refactor code, and are never regenerated to make a test pass — **with one
   recorded exception**. Feature 008 (D17/D29) changes the wire deliberately, so its goldens
   are re-cut **once**, as a reviewed diff that is part of the decision rather than a
   consequence of it, and **the pre-change files are retained** as the conversion path's
   fixtures. They are the only first-party corpus of real old-shape documents that exists;
   deleting them would remove the evidence the conversion is tested against. The rule's
   purpose is intact: a golden still never moves to make a red test go green.
4. Commits are GPG-signed. Retry on "gpg failed to sign"; never `--no-gpg-sign`.
5. Planning artifacts stay in `specs/planning/`; feature artifacts in `specs/NNN-*/`.
6. No `.xsd` edits — **with three recorded exceptions**. D3 defers schema work, tracked as
   X1–X13 in the audit.
   - **First**, `network_map.xsd` only, by explicit clarification in feature 007: the
     `node_type` → `node_role` rename with a real `NodeRoleType` enumeration, a `UuidType`
     pattern, and X9 (`PutType`) deleted.
   - **Second**, `settings.xsd` only, by feature 008 (D18): its `CTimecodeType`/`TimecodeType`
     pair — unreachable from any element, wrongly patterned `HH:MM:SS:FF` instead of the
     canonical `HH:MM:SS.mmm` — is deleted, mirroring the `PutType` precedent.
   - **Third**, `script.xsd` only, by feature 008 (D17/D18b): `Media.duration` is promoted from
     `cms:TimecodeType` to `cms:CTimecodeType` so that every element carrying a time value has
     one type and one machinery. **This is the only one of the three that changes documents
     already on disk**, and it is granted on the condition that the conversion path (D20/D21)
     carries it — the exception and its migration are one decision, not two.
   Each relaxation is scoped to the one file and change it names; a fourth reopens D3 and
   needs its own decision record. Note that all six schemas share one `targetNamespace` with
   no `include`/`import` between them, so a QName can be — and `CTimecodeType` was —
   *incompatibly defined twice*. Nothing composes them today, so nothing breaks; treat it as a
   hygiene invariant to preserve rather than an accident to rely on, particularly for any
   machinery that walks the namespace across schemas.
7. **Schema evolution convention** (adopted in feature 006, binds all later schema work):
   an element added to an **existing** complex type is `minOccurs="0"` with a model-layer
   default; required elements appear only in **new** types; anything else is a versioned
   file-format migration with a conversion path, never a silent edit. Measured precedent:
   `gradient_osc_port` broke every older settings file, `output_latency_ms` broke none.
   **Feature 007 extends it with three precedents the convention did not cover** — renaming,
   constraining and deleting — each recorded with the migration pattern it used: a hard
   cutover with a stdlib conversion run from `postinst`, a timestamped backup before any
   in-place write, and versioned package dependencies enforcing the release order.
8. **Compatibility is defined against the current XSD configuration**, not against file
   history. A document valid under today's schemas must load; one that no longer validates
   because the schema evolved is out of scope by policy. Reading must never become
   stricter than the pre-refactor parser — **with one recorded exception, and it is narrower
   than "load() now raises"**. Feature 008 (D19/D21) reverses the last sentence for
   **semantic** (T2) validation only, and replaces silent acceptance with **three** outcomes:
   - a document that is **old** is converted (backup first), not rejected — D20/D21's
     versioning machinery exists for exactly this;
   - a document that is **current but semantically invalid** is **repaired to a default state
     and reported**, not rejected — this is the common case, the one the versioning machinery
     does *not* help, and the reason "raise on T2" was the wrong rule as first written;
   - only a document that is **unrepairable** raises.

   Structural (T1) compatibility is untouched by the reversal — this rule's first two
   sentences still bind it. The intent is that reading becomes *more* recoverable, not less:
   what changes is that a corrupt document can no longer enter the runtime **silently**, not
   that it can no longer be read at all. Every first-party repair tool
   (`repair_durations.py`, the editor's fixups) is a `load()` consumer, so a rule that made
   corrupt documents unreadable would disable the tools that fix them.
