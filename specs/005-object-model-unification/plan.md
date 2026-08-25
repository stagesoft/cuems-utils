# Implementation Plan: Object model unification — one construction path

**Branch**: `005-object-model-unification` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-object-model-unification/spec.md`

**Design source**: `specs/planning/xml-rebuild/xml-rebuild-06-target-design.md` §7 (authoritative) and
`specs/planning/xml-rebuild/xml-rebuild-04-object-model.md` (measured evidence, `CuemsScript`-as-`CuemsDict`
analysis). Settled decisions D1–D15, Q11(c), Q14(i) are inputs, not topics.

## Summary

Give every model object one construction path, so that its internal types stop depending on
how it was made. Coercion moves out of property setters into a per-class adapter table
resolved from the schema (D2), `CuemsScript` becomes a `CuemsDict` like everything else, and
`items()`, defaulting and the JSON wrapping rule each collapse to a single definition. Seven
behaviour changes ship with it, each a bug fix, each enumerated in the spec and gated by a
fail-then-pass test.

The approach is constrained more by what must *not* move than by what must: all four golden
sets stay byte-identical (research R8), decode keeps arrival key order because the script root
is an `xs:all` type (R10), and no document changes its accept/reject outcome in either
direction (R2). Those three are the plan's spine — every implementation choice below is made
to keep them true.

## Technical Context

**Language/Version**: Python 3.11+ (tests run under pyenv 3.11.9)
**Primary Dependencies**: `xmlschema==3.4.3` (XSD 1.1), stdlib `ElementTree` on the write
path, `json_fix` for the JSON projection. No new dependency.
**Storage**: XML documents on disk; six bundled XSDs under `src/cuemsutils/xml/schemas/`
**Testing**: pytest via `hatch test`; goldens under `tests/golden/`, corpus under
`tests/data/corpus/`
**Target Platform**: Linux (Debian bookworm nodes, shared venv `/usr/lib/cuems`)
**Project Type**: single library (`cuemsutils` on PyPI)
**Performance Goals**: decode ≤ 2× the pre-005 measurement and ≤ 75 ms for the largest corpus
document; suite and write path within 10% of the 2026-08-12 baseline
**Constraints**: 1251 passed / 43 skipped / 36.71 s baseline; largest corpus decode 36.3 ms;
`project_load` payload byte-identical; no `.xsd` edits; no public API change
**Scale/Scope**: 19 model classes — 18 of them schema-bound and therefore covered by the
coherence test, which is why coverage counts run to 18 while defaulting runs to 19 — ~30-document
corpus, 10 `items()` overrides, and **7** model `__json__` methods to collapse
(`FadeCurveType.__json__` is a value type and is explicitly excluded; see T018)

No unresolved NEEDS CLARIFICATION: the four open questions were settled in the 2026-08-12
clarification session and recorded in the spec.

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1 — see the bottom of this file.*

- **I Code Quality**: `ruff` clean, no new warnings. Net line count should fall — this feature
  deletes a duplicated `setter`, 10 `items()` overrides, a key-casing heuristic, a dead
  `REGION_REQ_ITEMS`/`empty_keys` pair and a compatibility shim. Every new declaration
  (declared fields, defaults, `JSON_SELF_WRAPS`) carries the rationale for *why it is
  declared rather than inferred*, because that is the whole point of the change.
- **II Tests As A Release Gate**: seven behaviour changes → seven fail-then-pass pairs
  (contracts C5–C11), plus C12 written **first** as a guard on runtime state. Change 6 gets
  its own stray-key test for root and cue, both projections. Preservation contracts C1–C4 run
  unmodified throughout; they are the evidence the refactor did not leak.
- **III UX Consistency**: no user-facing surface changes. Consumers receive richer types on
  loaded objects — recorded in `migration-map.md` with a before/after for each of the seven
  changes, feeding feature 009. Error messages introduced by C8 and C11 name the class, field
  or scene, per the constitution's actionable-errors standard.
- **IV Performance**: budgets fixed *before* implementation (C13, SC-PERF-001/002/003), with
  the pre-005 decode number captured before the first behaviour change lands — otherwise the
  2× allowance has no denominator. Adapter tables cached per class; a ≥1000-cue construction
  benchmark is added because no construction baseline exists today.

**Result: PASS, with one deliberate deviation** — the constitution's "refactors MUST preserve
behavior" clause. The spec states the exception explicitly and enumerates all seven changes,
which is the carve-out the clause allows. See Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/005-object-model-unification/
├── plan.md              # This file
├── research.md          # Phase 0 — R1–R12, all measured
├── data-model.md        # Phase 1 — the base protocol, per-class inventory, field contract
├── quickstart.md        # Phase 1 — how to run, verify and not break the goldens
├── contracts/README.md  # Phase 1 — C1–C13
├── migration-map.md     # written during implementation; consumer-visible deltas (FR-UX-001)
├── baseline.md          # written by T001/T002, completed by T043; the perf denominators
├── defaults-audit.md    # written by T036; one row per newly declared default
├── checklists/
│   ├── requirements.md
│   └── behaviour-changes.md
└── tasks.md             # /speckit.tasks output — NOT created here
```

### Source code

```text
src/cuemsutils/
├── coercion.py            # NEW — per-class adapter table, lazily resolved, cached (R1)
├── helpers.py             # CuemsDict gains the protocol; setter() narrowed (F17)
├── create_script.py       # id clearing now works (F16) — no code change expected, verify
├── cues/
│   ├── Cue.py             # items() override removed; defaults protocol; UI_properties resolved
│   ├── CuemsScript.py     # becomes a CuemsDict; setter/items()/__json__ hack removed
│   ├── CueList.py, AudioCue.py, VideoCue.py, MediaCue.py,
│   ├── ActionCue.py, FadeCue.py, DmxCue.py, CueOutput.py, FadeProfile.py
│   │                      # items() overrides removed; declared field sets added where absent
│   └── MediaCue.py        # Media/Region declared fields; set_regions coercion fixed
└── xml/
    ├── mapper.py          # from_decoded() replaces _instantiate; DmxSceneCompatibility deleted
    ├── registry.py        # UiPropertiesType → CuemsDict-producing binding
    └── spec.py, adapters.py, schema.py, converter.py   # unchanged

tests/
├── unit/                  # test_region_coercion, test_id_clearing, test_setter_error_propagation,
│                          # test_defaulting_protocol, test_runtime_state; test_coherence updated
├── contract/              # test_stray_keys (new); test_dmx_failure_path inverted;
│                          # test_registry_totality updated; C1–C4 unchanged
├── integration/           # test_construction_parity (new), test_construction_performance (new),
│                          # test_d14_chain extended with built-vs-loaded
└── golden/                # UNCHANGED — see C1
```

**Structure Decision**: single-library layout, unchanged. One new module (`coercion.py`) at
package root rather than inside `xml/`, because it is imported by the model layer and `xml/`
already imports the model — putting it under `xml/` would close an import cycle (R1). It is
internal; nothing is added to any `__all__`.

`CuemsDict` gains `coercion_table()` alongside `declared_fields()` and `declared_defaults()`
(settled 2026-08-17), so the model answers for its own types the same way it answers for its
own fields — the rule T019 already enforces for field selection, applied to coercion. That is a
deliberate architectural statement and not a free one: `cues/` now declares a schema-derived
concept in its *public shape*, where previously the dependency lived only inside `xml/`. Three
consequences, all verified 2026-08-17:

- The import direction stays one-way. The classmethod is **not** what protects that — the
  function-local `cuemsutils.xml.*` imports inside `coercion.py` are (R1). `helpers.py` today
  imports only stdlib and `tools/`, so a module-scope import of `coercion` is safe.
- The public-API golden does not move: none of the five exported symbols
  (`NetworkMap`, `ProjectMappings`, `ProjectSettings`, `Settings`, `XmlReaderWriter`) derives
  from `CuemsDict` — they descend from `XmlReaderWriter`/`CuemsXml` — so
  `tests/golden/api/public_api.json` is untouched and FR-027 holds. The corollary is that if
  006 exports model classes, all three new classmethods enter that snapshot at once.
- `coercion_table()` takes no schema argument while registries are **per schema**. That is
  correct-by-accident today: the five config registries bind every type to `GENERIC`
  (`registry.py:213-226`), so every model class is bound in exactly one registry. The same
  docstring names 006 as the feature that gives configuration documents model classes, so the
  ambiguity arrives in the very next feature. T004 therefore carries a guard that raises when a
  class resolves in more than one registry, rather than a signature that would have to change
  later on every model object.

## Implementation phases

Ordered so that each step leaves the suite green, and so the dangerous ones land with their
evidence already in place.

**Phase A — guards first (no production change).**
Capture the pre-005 decode measurement (C13). Write C12 (runtime state) and C5's comparison
harness against today's code: C12 passes immediately — it is a guard, not a fix — and C5 fails
on `ui_properties`/`regions`, which is the measurement the feature exists to close. Extend
the D14 chain with the built-vs-loaded comparison, marked expected-fail until Phase D.

**Phase B — the base protocol.**
Add `declared_fields()`, `declared_defaults()`, `Unset`, `_init_runtime()` and
`coercion.adapter_table()`. Nothing uses them yet. The coherence test's MRO accumulation moves
into the model as the single definition, and the test imports it instead of owning it.

**Phase C — one `items()`, one wrapping rule.**
Collapse the 10 `items()` overrides; add `JSON_SELF_WRAPS`; make `CuemsScript` a `CuemsDict`
and delete its duplicated `setter` and key-casing hack. Switch `mapper._fill` to the declared
field rule for model objects only, leaving wildcard subtrees and plain dicts passing through
(R5). Change 6's stray-key contract (C10) lands here. **C1 must still be green at the end of
this phase** — if a golden moved, the wildcard exemption is wrong.

**Phase D — the construction path.**
`from_decoded()` replaces `_instantiate`, preserving arrival order (R10) and running the
adapter table. `Media`, `Region` and the three `CueOutput` subclasses get declared field sets;
`set_regions`' discarded coercion goes; `UiPropertiesType` decodes to `CuemsDict`. C5, C6, C9
turn green here, and so does the D14 built-vs-loaded leg. This is the phase that can break
every script file, so it lands alone, and `git diff tests/golden/` is checked before commit.

**Phase E — the small fixes.**
F16 (setters delegate to adapters, so `None` clears), F17 (narrowed swallow), F4 (delete
`DmxSceneCompatibility` and `_SwallowAndLog`, invert `test_dmx_failure_path`). C7, C8, C11.

**Phase F — evidence.**
`migration-map.md` with the seven consumer-visible deltas; performance validation against
C13; update the four expectation tests named in R9; confirm `git diff --stat tests/golden/` is
empty.

## Risks

| Risk | Mitigation |
|---|---|
| Routing decode through the sorting constructor rewrites every script root | Two construction modes, arrival order preserved (R10); C3 pins a root's key order directly so the failure names the cause |
| Giving six classes defaults changes what decode emits | `Unset` sentinel; C1 is the gate; the defaults audit is an explicit task, not an assumption. Six classes gain *defaults*; five gain declared *field sets* — different sets, see C9 |
| `_init_runtime()` sets `_initialized` true before population, switching on `VideoCueOutput`'s gated setter rules during decode | Stated as a prohibition at the hook itself (T008) rather than left to a contract, because C2 catches it only for documents whose arrival key order exposes it; C12 asserts the flag's value *during* population |
| Regions becoming objects changes emitted bytes | R6 traced both mapper branches to the same tag and text; three corpus regions with timecodes are the proof |
| The JSON leg changes shape when regions unwrap | C5 and `test_d14_chain`'s `rebuilt == obj` fail loudly together; both legs move in the same commit (R11) |
| Turning setter validation on by accident, via the constructor path | C2 (accept/reject parity, both directions) with the two pinned legacy rejections; FR-006b forbids adding or moving any rule |
| Coercion cost on decode exceeds budget | Adapter table cached per class; pre-005 number captured in Phase A; C13 has both a ratio and an absolute ceiling |
| A golden quietly regenerated to make a test pass | C1 states it as a diff check on `tests/golden/`, reviewable independently of the suite |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Engineering Standards: "Refactors MUST preserve behavior unless the spec explicitly states otherwise" | Seven enumerated behaviour changes, each a measured defect (F4, F12/F19, F16, F17, F18, F20, root `items()`) | Preserving them means keeping the divergence this feature exists to remove; the clause's carve-out is used as intended, with each change enumerated in the spec and gated by a fail-then-pass test |
| A new module (`coercion.py`) outside `xml/` | The model layer must reach the schema-derived adapters, and `xml/` already imports the model | Placing it in `xml/` closes an import cycle; declaring adapters in `REQ_ITEMS` would create a second source of truth for types, against D2 |
| Two construction *modes* rather than literally one function | Arrival key order is load-bearing for `xs:all` types; sorted order is what generated documents contain | A single ordering changes one of the two on every document — measured, not hypothetical (R10) |
| `coercion_table()` on the model base, rather than a resolver called only from `xml/` | Symmetry with `declared_fields()`: the caller asks the object instead of re-deriving the answer — the same rule T019 enforces for field selection. Two rules that agree only because a test says so is the failure mode this feature exists to remove | Keeping the resolver inside `xml/` leaves `cues/` schema-free, but then the *programmatic* construction path cannot reach its own adapters, and coercion stops being one path — which is the feature |

## Constitution re-check (post-design)

- **I**: unchanged — the design deletes more than it adds; one new internal module, justified
  above.
- **II**: C1–C4 preserve, C5–C12 are fail-then-pass, C13 is measured. Phase A puts the
  evidence before the change, which is the rebuild's standing rule 2.
- **III**: no user-facing surface; `migration-map.md` is the deliverable, per FR-UX-001.
- **IV**: budgets fixed before implementation, with the baseline captured in Phase A.

**PASS.** Ready for `/speckit.tasks`.
