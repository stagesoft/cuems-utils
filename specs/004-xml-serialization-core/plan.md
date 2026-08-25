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

**One declared breaking change (FR-026d).** Replacing the implicit `globals()` handler
lookup with the explicit registry means `cuems-nodeconf`'s module-globals injection (F8)
stops being consulted. No shim can preserve it without reintroducing the very lookup FR-007
deletes, so it is declared rather than hidden — named in the spec, in the migration map and
in `CHANGELOG.md`, and asserted by contract C11. **The fix is carried by feature 007**, not
here: it must target an API that is internal in 004, public in 006 and absorbing the node
model in 007, so writing it now would be rewritten twice, and `cuems-nodeconf` is not
shipping against this release. **Feature 004 therefore edits no repository but this one.**
`cuems-editor` and `cuems-engine` are unaffected.

Phase 0 research **verified the design's load-bearing premise** — `content.iter_elements()`
resolves `xs:extension` in schema order on the pinned `xmlschema==3.4.3`, non-alphabetical,
`master_vol` before `fade_profiles` — and surfaced four corrections to the target design
that are folded into this plan (R2–R5, and R10).

## Technical Context

**Language/Version**: Python 3.11+ (validated on **pyenv 3.11.9**; conda environments are
not used for this project)
**Primary Dependencies**: `xmlschema==3.4.3` (pinned, XSD 1.1 required by `xs:assert`),
`lxml==6.1.0` (not in the write path and must not enter it), `deprecated==1.2.18` (shim
warnings). **No dependency is added** — all three are already in `pyproject.toml`, and
`deprecated` is already the mechanism used for `XmlReader`/`XmlWriter` since 0.0.7.
`_deprecation.py` is a **~15-line message template, not a mechanism**: `deprecated` supplies
per-call emission, `extra_stacklevel` and class support natively, and the one thing it
cannot supply is FR-027a — its `version=` renders as *"Deprecated since version X"*
(`deprecated/classic.py:71-72,151-153`), i.e. "deprecated since", not "removed in", so
naming `v0.1.1` there would emit a false statement. The removal release therefore lives in
`reason=`, and the helper fixes that string once rather than at ~20 sites. It must not
grow into a second warning system.
**Storage**: XML files on disk; six bundled XSD schemas
**Testing**: `hatch test --show` (pytest); golden-file comparison; the D14 chain test
**Target Platform**: Linux; shared venv `/usr/lib/cuems`
**Project Type**: Library (`cuemsutils` on PyPI), consumed by `cuems-engine`,
`cuems-editor`, `cuems-nodeconf`
**Performance Goals**: no regression beyond 10% on
`tests/integration/test_mediacue_fade_performance.py`; the **pre-existing 557 tests**,
re-run as a subset, within 10% of the ~7.4s baseline; the **new corpus suite** within its
own absolute budget (§IV — the 10% rule cannot bind a suite SC-TEST-002 requires to grow);
schema derivation cached per `(schema, type)` — bounded by 56 distinct types, never per
object
**Constraints**: byte-identical XML output and read dict; `cuems-editor`'s `project_load`
payload transmitted verbatim to the Angular UI; no `.xsd` edits; no public API change
**Scale/Scope**: 6 schemas, 56 complex types, 33 simple types, ~20 model classes. Corpus:
~24 vendored documents from the four source repos, plus the `legacy/` and `negative/`
recoveries and the generated per-cue-type documents — the exact count is pinned in
`tests/data/corpus/PROVENANCE.md` when the corpus is frozen, and it is what the new
suite's absolute time budget is measured against (SC-PERF-001).

No unresolved NEEDS CLARIFICATION: the spec's clarifications — three sessions, most
recently the analyze follow-up of 2026-08-11 that settled `CuemsParser`, the FR-026d
declared break, FR-012 and the SC-PERF-001 split — are settled, and Phase 0 resolved the
remaining technical unknowns.

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
  documentation for feature 009.
- **One declared breaking change (FR-026d)**, which the constitution permits only with a
  documented migration plan: it is named in the spec, recorded in the migration map,
  flagged in `CHANGELOG.md`, and asserted by test (SC-017) — all of it in this repository.
  The `cuems-nodeconf` fix itself is carried by feature 007 (FR-030b's scheduling clause).
  Recorded in Complexity Tracking below rather than waved through.

### IV. Performance Budgets Are Requirements

| Budget | Target | Validation |
|---|---|---|
| Write benchmark | within 10% of pre-refactor baseline | `tests/integration/test_mediacue_fade_performance.py` |
| Pre-existing suite | within 10% of ~7.4s, run as a subset | `hatch test --show` over the 557 pre-refactor tests |
| New corpus suite | absolute budget, fixed in `baseline.md` when the corpus is frozen | `hatch test --show` over `tests/contract/` + `tests/golden/` + the chain test |
| Total suite | ≥557 passing, zero new failures or skips | `hatch test --show` (SC-TEST-002) |
| Derivation count | bounded by distinct types, not object count | instrumented counter assertion (SC-PERF-002) |
| Schema load | once per schema per process | cache assertion |

The suite budget is **split deliberately**. A 10% wall-time rule cannot bind a suite the
feature is required to grow: SC-TEST-002 demands more than 557 tests, and the corpus adds
~30 documents driven through 14 new test files. Applying 10% to the total would make
SC-PERF-001 and SC-TEST-002 mutually unsatisfiable, so the 10% rule binds the pre-existing
subset and the benchmark, and the new tests carry their own absolute number.

Baseline is recorded **before any code moves** (P1 below), because after the rename there
is nothing to compare against.

**Gate result: PASS.** No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/004-xml-serialization-core/
├── plan.md                 # This file
├── spec.md                 # Feature specification (3 clarification sessions applied)
├── research.md             # Phase 0 — R1..R12, all decisions
├── data-model.md           # Phase 1 — FieldSpec / TypeSpec / Adapter / Registry / Mapper
├── quickstart.md           # Phase 1 — how to work on this safely
├── contracts/
│   └── byte-identity.md    # Phase 1 — C1..C11, the acceptance gates
├── checklists/
│   ├── requirements.md     # Spec quality checklist
│   └── regression-safety.md # Refactor-safety checklist
├── tasks.md                # Phase 2 output (/speckit.tasks)
│
│   # produced during implementation, by the tasks that name them:
├── baseline.md             # P1  — pre-refactor suite/benchmark numbers + new-suite budget
├── generic-bindings.md     # P5  — types that reach a generic today (instrumented)
└── migration-map.md        # P4  — shim → replacement → consumer call site (FR-028),
                            #       incl. the FR-026d declared breaking change
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
│   ├── validators.py             # NEW  T2 semantic tier (FR-017)
│   ├── _deprecation.py           # NEW  one warning helper, wrapping `deprecated`
│   ├── xml_reader_writer.py      # RENAMED from XmlReaderWriter.py, now a facade
│   ├── settings.py               # RENAMED from Settings.py
│   ├── schemas/                  # UNCHANGED — no .xsd edits (D3)
│   │
│   ├── XmlReaderWriter.py        # SHIM  re-export + DeprecationWarning
│   ├── Settings.py               # SHIM  re-export + DeprecationWarning
│   ├── Parsers.py                # PART SHIM: CuemsParser delegates to the engine and
│   │                             #   does NOT warn (supported entry point, FR-026d);
│   │                             #   the rest is frozen legacy + DeprecationWarning
│   ├── XmlBuilder.py             # SHIM  frozen legacy impl + DeprecationWarning
│   └── CMLCuemsConverter.py      # SHIM  re-export of converter.py
├── cues/                         # model classes — UNCHANGED in this feature
└── tools/                        # UNCHANGED

tests/
├── support/
│   └── capture_goldens.py        # NEW  golden harness: generates missing, refuses
│                                 #      to overwrite existing without --force
├── data/corpus/                  # NEW  vendored, frozen (FR-022a), with PROVENANCE.md
│   ├── cuems-utils/  cuems-engine/  cuems-editor/  cuems-common/
│   ├── legacy/                   # NEW  historical but still schema-valid (FR-035d)
│   └── negative/                 # NEW  parity cases only, with README.md (FR-015)
├── golden/                       # NEW  captured once from pre-refactor code
│   ├── xml/  dict/  generated/
├── contract/                     # C1..C11 assertions — grows from 1 file to 18
│   ├── test_corpus_coverage.py           test_byte_identity_xml.py
│   ├── test_byte_identity_dict.py        test_roundtrip_stability.py
│   ├── test_semantic_roundtrip.py        test_ui_payload_contract.py
│   ├── test_accept_reject_parity.py      test_dmx_failure_path.py
│   ├── test_deprecation_shims.py         test_public_api_surface.py
│   ├── test_registry_totality.py         test_ordering_source.py
│   ├── test_xmlschema_tripwire.py        test_config_parity.py
│   ├── test_reader_configs.py            test_logging_budget.py
│   ├── test_no_internal_deprecation.py   test_legacy_compatibility.py
│   ├── test_declared_break_nodeconf.py   # SC-017, the FR-026d assertion
│   └── test_mediacue_fade_schema_contract.py   # existing
├── integration/
│   ├── test_d14_chain.py         # NEW  the primary gate — lands FIRST
│   ├── test_type_coercion_live_paths.py  # NEW  SC-010, the 44+ cases on the engine
│   └── test_mediacue_fade_performance.py   # existing budget
└── unit/
    ├── test_spec_derivation.py
    ├── test_adapters.py
    ├── test_spec_cache.py        # SC-PERF-002
    └── test_coherence.py         # FR-020
```

**Structure Decision**: single library project, existing layout retained. New machinery
lands as eight modules inside `src/cuemsutils/xml/` — the six the target design §10
prescribes, plus `validators.py` for the T2 semantic tier and `_deprecation.py` for the
single warning mechanism. Old module paths persist as shims in the same package, so every
consumer import resolves unchanged; `Parsers.py` is the one partial case, because
`CuemsParser` delegates forward rather than staying frozen. Test tree gains `support/`,
`data/corpus/` (with `legacy/` and `negative/`) and `golden/`; the contract directory grows
from one file to eighteen.

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
across repeated round-trips. **All acceptance-level corrections are now written back into
the spec**: R2 landed as FR-001/FR-001a, and R10 landed as SC-003 and — in the analyze
follow-up of 2026-08-11 — as the restated **FR-012**, which had kept the original false
wording after SC-003 was fixed. R3, R4 and R5 remain design-level decisions carried by
`data-model.md`, which is sufficient because they constrain implementation rather than
acceptance.

## Implementation phasing

Ordering is not negotiable; step P2 is what makes every later step verifiable.

Steps are labelled **P1–P11** so they cannot be confused with `tasks.md`'s `T001`–`T068`;
the two numbering schemes previously collided (plan "T2" ≠ task T002).

| # | Step | Commit shape | Gate | tasks.md |
|---|---|---|---|---|
| P1 | Record the performance and test baseline, and fix the new suite's absolute budget | none (recorded in `baseline.md`) | 557 passing, benchmark noted | T001 |
| P2 | Vendor the corpus; capture goldens; **write the D14 chain test against current code** | test-only | suite green with **zero** production changes | T002–T020 |
| P3 | D9 rename, pure `git mv` + import updates, **no logic** | rename-only | suite green, goldens untouched | T021–T024 |
| P4 | Deprecation shims at every old path; migration map; declare FR-026d | additive | C9 green; consumer imports resolve | T025–T031b |
| P5 | `schema.py` + `spec.py` + coherence test | additive, engine not yet wired | C6, C10; coherence fails on injected drift | T037–T039, T057–T059 |
| P6 | `adapters.py` + `registry.py` | additive | C7; registry totality fails on a removed binding | T040–T042 |
| P7 | `converter.py` (D5 thin subclass) | replaces fork | C2 | T043–T044 |
| P8 | `mapper.py`; route `xml_reader_writer`, `settings` and `CuemsParser` through it | the swap | **C1–C5 and C11 green, chain test unedited** | T045–T050 |
| P9 | Config schemas onto the engine | | US3 acceptance | T051–T056 |
| P10 | Logging pass (F11) | | SC-014 | T060–T061 |
| P11 | Verify no live path reaches shims | | C8 | T062 |

Steps P5–P7 are independently green and can be reviewed separately. P8 is the swap: it is
the only step where a byte-identity failure can appear, and the step where C11's declared
break becomes real.

**Every step is inside this repository.** The `cuems-nodeconf` fix for the FR-026d break is
carried by feature 007 under FR-030b's scheduling clause — it has to target an API that is
internal here, public in 006 and absorbing the node model in 007, so writing it against
004's intermediate shape would be rewritten twice. What 004 owes is the declaration
(migration map, `CHANGELOG.md`, contract C11), all of which land here.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| An `xs:all` type emits in the wrong order | **was high — now closed by R2** | rule branches on content model; both affected types enumerated |
| A type currently reaching a generic gets a bespoke class by accident, changing output | medium | FR-007 explicit generic bindings, enumerated by instrumenting today's `globals()` misses over the corpus |
| `universe_num` attribute/element name clash decodes differently | medium | preserved as-is; DMX corpus goldens are the arbiter (R7) |
| Corpus misses a document type, so byte-identity is unproven for it | medium | coverage of all six schemas confirmed before P8 (SC-009) |
| `xmlschema` upgrade changes `iter_elements` semantics | low | pin held + tripwire test C10 |
| Derivation cost lands on the hot path | low | memoised per `(schema, type)`; counter assertion SC-PERF-002 |
| Shims become a place old code keeps running | medium | C8 — zero deprecation warnings from the library's own paths |
| **`cuems-nodeconf`'s injected handlers silently stop being consulted** | **realized — accepted as FR-026d** | Declared, not discovered: named in the spec, in the migration map and in `CHANGELOG.md`, asserted by C11/SC-017 here; the fix is scheduled into feature 007 rather than written against an API that changes twice before then |
| `CuemsParser` delegation changes editor results | medium | It is inside C1–C5: the editor's payload path is the read dict, pinned byte-identical. T048 is covered by the same goldens as the file path |
| The new corpus suite quietly eats the runtime budget | medium | Split budget (§IV); the absolute number is fixed at P1, before any test is written to fit it |

## Complexity Tracking

Two items, both required by the constitution to be recorded here rather than argued
inline.

| Item | Constitution term | Why it is accepted | Mitigation |
|---|---|---|---|
| **FR-026d — one declared breaking change.** `cuems-nodeconf`'s module-globals handler injection stops being consulted. | III *Consistent User Experience*: "New flows MUST follow existing conventions **unless a documented migration plan is approved**." | No shim can preserve it. The injection point is a private module namespace, and honouring it means keeping the implicit `globals()` lookup that FR-007 exists to delete — so the alternative is abandoning the feature's core premise. `cuems-nodeconf` is already out of date and its serialization work is unlanded, so nothing in production is shipping against it. | Migration plan is the documented one: spec FR-026d, `migration-map.md`, `CHANGELOG.md`, contract C11 / SC-017 — all inside this repository. The sibling fix is scheduled into feature 007 (FR-030b's scheduling clause), because it must target an API that is internal in 004, public in 006 and absorbs the node model in 007; written now it would be rewritten twice, and `cuems-nodeconf` is not shipping against this release. `cuems-editor` and `cuems-engine` are untouched. |
| **Fail-before-pass is inverted for the byte-identity contracts.** C1–C5 pass at the moment they are written. | II *Tests As A Release Gate*: "A change is not complete until tests fail before the implementation and pass after it." | II governs *behaviour changes*; this feature has none by construction, so there is no new behaviour for a test to fail against. Inverting the gate is the point of a refactor harness: the contracts must pass before **and** after, and the commit history proves they were not edited in between. | The three genuinely new assertions do carry fail-first evidence: coherence on injected drift (T058), registry totality on a removed binding (T034), and ordering provenance against pre-refactor code (T036). SC-TEST-001 makes the "unedited" claim checkable from `git log`. |

## Post-Design Re-check

Re-evaluated after Phase 1 artifacts:

- **I Quality** — PASS. New modules are small and single-purpose; the only growth over the
  target design is the ordering branch (R2), which replaces a hardcoded name comparison
  with a content-model check, and is a net simplification.
- **II Tests** — PASS, with the documented inversion recorded in Complexity Tracking.
  C1–C11 are executable; the chain test leads. Three genuinely new assertions carry
  fail-before-pass evidence.
- **III UX** — PASS **with one documented exception**, FR-026d, recorded in Complexity
  Tracking with its migration plan. Everything else is unchanged beyond the specified
  logging and deprecation surfaces, both asserted by test.
- **IV Performance** — PASS. Budgets declared with validation method and split so they are
  satisfiable alongside SC-TEST-002; baseline captured before any code moves.

## Open items for `/speckit.tasks`

All four are now carried by tasks; kept here for traceability.

1. Enumerate the ~13 script types that reach a generic today, by instrumentation over the
   corpus, and write them as explicit bindings. → **T041, T042**
2. Produce the shim → replacement → consumer call-site table (FR-028), the input to
   feature 009. → **T031**, with the FR-026d break declared at **T031a/T031b** and
   asserted at **T049a**; its fix is scheduled into feature 007
3. Confirm corpus coverage of all six schemas before P8. → **T008**
4. Deferred schema items for the audit's X-series: `outputs.xsd`'s colliding `OutputsType`
   (R4), `DmxUniverseType`'s attribute/element name clash (R7), and X13. → **T066**
