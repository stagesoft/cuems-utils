# Implementation Plan: Schema-derived XML serialization core

**Branch**: `004-xml-serialization-core` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-xml-serialization-core/spec.md`

## Summary

Replace four independent implementations of the same mapping rules — an XML builder, an
XML parser, eight hand-written `__json__` methods, and the config readers — with one
engine driven by an ordered, typed field specification derived from the XSD at load time,
covering all six schemas. Observable behaviour does not change: written XML and the read
dict stay byte-identical, every consumer import keeps working behind deprecation shims,
and failure paths are preserved. The element-ordering coincidence and its hardcoded
`master_vol`/`fade_profiles` exception are deleted; runtime type guessing leaves every live
path.

Phase 0 research **verified the design's load-bearing premise** — `content.iter_elements()`
resolves `xs:extension` in schema order on the pinned `xmlschema==3.4.3`, non-alphabetical,
`master_vol` before `fade_profiles` — and surfaced four corrections to the target design
that are folded into this plan (R2–R5, and R10).

## Technical Context

**Language/Version**: Python 3.11+ (validated on **pyenv 3.11.9**; conda environments are
not used for this project)
**Primary Dependencies**: `xmlschema==3.4.3` (pinned, XSD 1.1 required by `xs:assert`),
`lxml==6.1.0` (not in the write path and must not enter it), `deprecated` (shim warnings)
**Storage**: XML files on disk; six bundled XSD schemas
**Testing**: `hatch test --show` (pytest); golden-file comparison; the D14 chain test
**Target Platform**: Linux; shared venv `/usr/lib/cuems`
**Project Type**: Library (`cuemsutils` on PyPI), consumed by `cuems-engine`,
`cuems-editor`, `cuems-nodeconf`
**Performance Goals**: no regression beyond 10% on
`tests/integration/test_mediacue_fade_performance.py`; full suite within 10% of the ~7.4s
baseline; schema derivation cached per `(schema, type)` — bounded by 56 distinct types, never
per object
**Constraints**: byte-identical XML output and read dict; `cuems-editor`'s `project_load`
payload transmitted verbatim to the Angular UI; no `.xsd` edits; no public API change
**Scale/Scope**: 6 schemas, 56 complex types, 33 simple types, ~20 model classes, ~24
vendored corpus documents

No unresolved NEEDS CLARIFICATION: the spec's four clarifications are settled and Phase 0
resolved the remaining technical unknowns.

## Constitution Check

*GATE: passed before Phase 0, re-checked after Phase 1 — see §Post-Design Re-check.*

### I. Code Quality By Default

- `ruff` clean; no new warnings in `hatch test --show`.
- The new converter imports **only** public `xmlschema` API. Today's
  `CMLCuemsConverter` reaches into `xmlschema.validators.wildcards.Xsd11AnyElement`; that
  coupling is what D5 removes (R11).
- Derived machinery is internal (Q14) and documented by `data-model.md`; the hand-written
  seams — adapters, registry bindings, semantic validators — are small, closed and
  explicit per Q11(c).
- Frozen shim modules are exempt from new-code quality work by design: they are not edited,
  only deprecated.

### II. Tests As A Release Gate

- **The D14 chain test is written first, against current behaviour, and must pass unchanged
  after the swap.** This is the feature's primary gate and the single most important
  sequencing rule (contract C4).
- Goldens are generated once from pre-refactor code and never regenerated to make a test
  pass (FR-021).
- Fail-before-pass evidence required for the genuinely new assertions: the coherence test
  must be shown failing on an injected Python↔schema mismatch (FR-022); the registry
  totality check must be shown failing on a removed binding; the ordering test
  (`master_vol` before `fade_profiles` without a name comparison) must fail against
  pre-refactor code.
- For the byte-identity contracts the fail-before-pass model is inverted and stated
  explicitly: they **pass** before implementation, by construction, and must keep passing.
  That is the point of a refactor gate, and it is why the goldens land first.

### III. Consistent User Experience

- No user-facing change; asserted rather than assumed via C1, C2, C5 and the corpus
  accept/reject comparison (FR-015).
- One exception, deliberate and specified: log output (FR-032–FR-034). Levels become
  consistent between read and write directions, per-cue records drop to DEBUG, and no
  record carries field values or object reprs — which also removes show content such as
  names and file paths from log files.
- Deprecation warnings are a new user-facing surface. One mechanism, one message format,
  each naming symbol, replacement and removal release (FR-027) — they are the migration
  documentation for feature 008.

### IV. Performance Budgets Are Requirements

| Budget | Target | Validation |
|---|---|---|
| Write benchmark | within 10% of pre-refactor baseline | `tests/integration/test_mediacue_fade_performance.py` |
| Full suite | within 10% of ~7.4s / ≥557 passing | `hatch test --show` |
| Derivation count | bounded by distinct types, not object count | instrumented counter assertion (SC-PERF-002) |
| Schema load | once per schema per process | cache assertion |

Baseline is recorded **before any code moves** (T1 below), because after the rename there
is nothing to compare against.

**Gate result: PASS.** No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/004-xml-serialization-core/
├── plan.md              # This file
├── spec.md              # Feature specification (4 clarifications applied)
├── research.md          # Phase 0 — R1..R12, all decisions
├── data-model.md        # Phase 1 — FieldSpec / TypeSpec / Adapter / Registry / Mapper
├── quickstart.md        # Phase 1 — how to work on this safely
├── contracts/
│   └── byte-identity.md # Phase 1 — C1..C10, the acceptance gates
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
src/cuemsutils/
├── xml/                          # internal machinery (Q14)
│   ├── schema.py                 # NEW  schema loading + caching
│   ├── spec.py                   # NEW  TypeSpec / FieldSpec derivation (memoised)
│   ├── adapters.py               # NEW  scalar + wrapper codecs
│   ├── registry.py               # NEW  per-schema xsd type <-> model class binding
│   ├── mapper.py                 # NEW  the one encode/decode engine
│   ├── converter.py              # NEW  thin XMLSchemaConverter subclass (D5)
│   ├── xml_reader_writer.py      # RENAMED from XmlReaderWriter.py, now a facade
│   ├── settings.py               # RENAMED from Settings.py
│   ├── schemas/                  # UNCHANGED — no .xsd edits (D3)
│   │
│   ├── XmlReaderWriter.py        # SHIM  re-export + DeprecationWarning
│   ├── Settings.py               # SHIM  re-export + DeprecationWarning
│   ├── Parsers.py                # SHIM  frozen legacy impl + DeprecationWarning
│   ├── XmlBuilder.py             # SHIM  frozen legacy impl + DeprecationWarning
│   └── CMLCuemsConverter.py      # SHIM  re-export of converter.py
├── cues/                         # model classes — UNCHANGED in this feature
└── tools/                        # UNCHANGED

tests/
├── data/corpus/                  # NEW  vendored, frozen (FR-022a), with PROVENANCE.md
│   ├── cuems-utils/  cuems-engine/  cuems-editor/  cuems-common/
├── golden/                       # NEW  captured once from pre-refactor code
├── contract/                     # C1..C10 assertions
│   ├── test_byte_identity_xml.py
│   ├── test_byte_identity_dict.py
│   ├── test_registry_totality.py
│   ├── test_no_internal_deprecation.py
│   └── test_xmlschema_tripwire.py
├── integration/
│   ├── test_d14_chain.py         # NEW  the primary gate — lands FIRST
│   └── test_mediacue_fade_performance.py   # existing budget
└── unit/
    ├── test_spec_derivation.py
    ├── test_adapters.py
    └── test_coherence.py         # FR-020
```

**Structure Decision**: single library project, existing layout retained. New machinery
lands as six modules inside `src/cuemsutils/xml/` exactly as the target design §10
prescribes. Old module paths persist as shims in the same package, so consumer imports
resolve unchanged. Test tree gains `data/corpus/` and `golden/`; the contract directory
grows from one file to six.

## Design corrections carried from Phase 0

The target design is authoritative and was not redesigned. Four points were **wrong or
absent** and are corrected here on measured evidence:

| # | Target design said | Measured reality | Correction |
|---|---|---|---|
| R2 | order comes from the schema | `CuemsScript` and `DmxSceneType` are `xs:all`; declaration order ≠ emitted order, verified against a real file | ordering rule branches on content model; `xs:all` → sorted-key tie-break, preserving today's bytes |
| R3 | `SCRIPT.bind('CuemsScriptType', …)` | there **is** no `CuemsScriptType` — root types are anonymous | registry keys on type qname **or** element path |
| R4 | one registry per schema (stylistic) | `script.xsd` and `outputs.xsd` both declare `OutputsType` in the same namespace with different content | per-schema isolation is **mandatory**; it is also why `outputs.xsd` was never loadable (explains X11) |
| R5 | `CTimecodeType` listed among scalars | it is a **complex** type wrapping `<CTimecode>` | adapters bind complex types too |

R10 additionally restates SC-003: `save(load(x)) == x` is false today for hand-authored
files (the serializer normalizes formatting), so idempotence is verified as stability
across repeated round-trips.

## Implementation phasing

Ordering is not negotiable; step 2 is what makes every later step verifiable.

| # | Step | Commit shape | Gate |
|---|---|---|---|
| T1 | Record the performance and test baseline | none (recorded in plan) | 557 passing, benchmark noted |
| T2 | Vendor the corpus; capture goldens; **write the D14 chain test against current code** | test-only | suite green with **zero** production changes |
| T3 | D9 rename, pure `git mv` + import updates, **no logic** | rename-only | suite green, goldens untouched |
| T4 | Deprecation shims at every old path | additive | C9 green; consumer imports resolve |
| T5 | `schema.py` + `spec.py` + coherence test | additive, engine not yet wired | C6, C10; coherence fails on injected drift |
| T6 | `adapters.py` + `registry.py` | additive | C7; registry totality fails on a removed binding |
| T7 | `converter.py` (D5 thin subclass) | replaces fork | C2 |
| T8 | `mapper.py`; route `xml_reader_writer` and `settings` through it | the swap | **C1–C5 all green, chain test unedited** |
| T9 | Config schemas onto the engine | | US3 acceptance |
| T10 | Logging pass (F11) | | SC-014 |
| T11 | Verify no live path reaches shims | | C8 |

Steps T5–T7 are independently green and can be reviewed separately. T8 is the swap and is
the only step where a byte-identity failure can appear.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| An `xs:all` type emits in the wrong order | **was high — now closed by R2** | rule branches on content model; both affected types enumerated |
| A type currently reaching a generic gets a bespoke class by accident, changing output | medium | FR-007 explicit generic bindings, enumerated by instrumenting today's `globals()` misses over the corpus |
| `universe_num` attribute/element name clash decodes differently | medium | preserved as-is; DMX corpus goldens are the arbiter (R7) |
| Corpus misses a document type, so byte-identity is unproven for it | medium | coverage of all six schemas confirmed before T8 (SC-009) |
| `xmlschema` upgrade changes `iter_elements` semantics | low | pin held + tripwire test C10 |
| Derivation cost lands on the hot path | low | memoised per `(schema, type)`; counter assertion SC-PERF-002 |
| Shims become a place old code keeps running | medium | C8 — zero deprecation warnings from the library's own paths |

## Complexity Tracking

No constitution violations. Section intentionally empty.

## Post-Design Re-check

Re-evaluated after Phase 1 artifacts:

- **I Quality** — PASS. New modules are small and single-purpose; the only growth over the
  target design is the ordering branch (R2), which replaces a hardcoded name comparison
  with a content-model check, and is a net simplification.
- **II Tests** — PASS. C1–C10 are executable; the chain test leads. Three genuinely new
  assertions carry fail-before-pass evidence.
- **III UX** — PASS. No user-facing change beyond the specified logging and deprecation
  surfaces, both asserted by test.
- **IV Performance** — PASS. Budgets declared with validation method; baseline captured
  before any code moves.

## Open items for `/speckit.tasks`

1. Enumerate the ~13 script types that reach a generic today, by instrumentation over the
   corpus, and write them as explicit bindings.
2. Produce the shim → replacement → consumer call-site table (FR-028), the input to
   feature 008.
3. Confirm corpus coverage of all six schemas before T8.
4. Two new deferred schema items for the audit's X-series: `outputs.xsd`'s colliding
   `OutputsType` (R4) and `DmxUniverseType`'s attribute/element name clash (R7).
