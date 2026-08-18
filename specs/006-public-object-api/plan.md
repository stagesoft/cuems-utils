# Implementation Plan: Public object API — one surface, internal machinery

**Branch**: `006-public-object-api` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-public-object-api/spec.md`

**Design authority**: `specs/planning/xml-rebuild-06-target-design.md` §§8, 9, 10, with
`specs/planning/xml-rebuild-05-ui-wire-contract.md` for the wire evidence. This plan follows
that design; it does not redesign it. Settled decisions D1, D2, D3, D5, D9, D11, D12, D13,
D14, D15, Q11→(c), Q14→(i) are inputs, not open questions.

## Summary

Give the library one public surface — `CuemsScript` for show data, `ConfigManager`/
`ConfigBase` for configuration — and make `xml/` internal machinery.

Research ([research.md](research.md)) found the serialization engine already in place from
features 004/005: `CuemsParser.parse()` delegates to `Mapper.decode_document`, and the write
path already runs through `build_document`. So this feature is **not** building a decoder. It
adds the four things that are genuinely missing — a wire projection, a public facade, a
config object layer, and a semantic-rule registry — and deletes the frozen legacy tree those
replaced.

The one significant engineering choice is how `to_wire()` is produced, and it was decided by
measurement: round-tripping objects through XML to reuse the reader's converter would cost a
**2× regression on `project_load`** (33.99 ms against today's 16.95 ms), because it pays
`to_dict`'s 15.49 ms a second time to learn what the object already knows. A direct
projection ships; the round-trip is retained as the **test oracle**, so its byte-identity
guarantee becomes a property under test rather than a runtime cost.

## Technical Context

**Language/Version**: Python 3.11+ (tests run under pyenv 3.11.9; conda is not used here)
**Primary Dependencies**: `xmlschema==3.4.3` (pinned — XSD 1.1 required by `xs:assert` in
`script.xsd`), `deprecated==1.2.18`, stdlib `xml.etree.ElementTree` for the write path.
`lxml==6.1.0` is present but **not** in the XML write path.
**Storage**: XML documents on disk, six bundled XSDs under `src/cuemsutils/xml/schemas/`
**Testing**: `pytest` via `hatch test --show`; contract/integration/unit split under `tests/`;
frozen corpus at `tests/data/corpus/` (28 documents) with goldens at `tests/golden/`
**Target Platform**: Linux (Debian bookworm nodes, shared venv `/usr/lib/cuems`)
**Project Type**: Shared library (`cuemsutils` on PyPI), consumed by `cuems-engine`,
`cuems-editor`, `cuems-nodeconf`
**Performance Goals**: `to_wire()` is on every `project_load`. Budget: **`load()` + `to_wire()`
≤ 25 ms** for the largest corpus document (24 KB), against today's 16.95 ms `read()` — a
ceiling chosen to permit the object layer's real cost while excluding the 34 ms round-trip
strategy. `to_wire()` alone **≤ 5 ms** (bounded above by the 1.09 ms tree build, which is the
same traversal).
**Constraints**: `to_wire()` byte-identical to the pre-feature `read()` dict minus
`schemaLocation`; booleans stay the strings `"True"`/`"False"`; no `.xsd` edits; reading never
becomes stricter
**Scale/Scope**: ~1 800 LOC touched. New: wire projection, public facade, `config/` module,
T2 registry. Deleted: `Parsers.py`'s ~430 unreachable lines, `Settings.py`/`XmlReaderWriter.py`
shim modules, `settings.py`'s dead `data2xml`/`buildxml`.

**Baseline** (measured on this branch, 2026-08-18): suite **1485 passed, 47 skipped, 2 xfailed
in 44.57 s**. The "557 passed in ~7.4 s" figure in `CLAUDE.md` and the prompt set predates
features 004/005 and is stale; correct it when this lands.

No NEEDS CLARIFICATION remain: both decision stops were resolved in the 2026-08-18
clarification session, and the config derived/hand-written line — flagged as the least
specified part of the design — is settled concretely in [data-model.md](data-model.md).

## Constitution Check

*GATE: evaluated before Phase 0 and re-evaluated after Phase 1. Both passes recorded.*

### I. Code Quality By Default

- `ruff` clean, no new warnings. The feature is **net line-negative**: ~430 unreachable lines
  in `Parsers.py`, two shim modules and `settings.py`'s dead writers all go.
- Every public method carries a docstring stating its contract *and its error behaviour* —
  the two differ deliberately between `validate()` (reports) and `save()` (raises first), and
  a reader must not have to infer that.
- **Pre-existing hazard to preserve, not clean up**: the two `from . import … as _shim` lines
  at the top of `xml/__init__.py` exist because `Settings.py`/`XmlReaderWriter.py` are real
  submodules that would otherwise clobber the same-named classes. Emptying `__all__` must not
  remove them; doing so resurrects a fixed `TypeError: 'module' object is not callable`.

### II. Tests As A Release Gate

- **Gating test**: golden-file byte-equality of `to_wire()` against the pre-feature `read()`
  goldens in `tests/golden/dict/`, minus the `schemaLocation` key, across every corpus script
  document. Goldens are **never regenerated** to make a test pass (standing rule 3).
- **Second gate**: `encode_wire(obj) == schema.to_dict(build_document(obj))` — the round-trip
  oracle from R1, which is what makes the fast path safe.
- Fail-before/pass-after for each of the four enumerated behaviour changes, plus the API
  additions. The `initial_template`-vs-`project_load` divergence must be captured as a
  **failing** test first: it is the bug being fixed, and it is currently invisible.
- Deprecation shims: one test per removed entry point asserting it still resolves, still
  works, and warns with the replacement and removal release.
- Suite must stay ≥ 1485 passing.

### III. Consistent User Experience

**This is the UX feature.** Two payloads for one document type become one.

- `initial_template` and `project_load` become byte-identical projections — F21 closed. No
  frontend change is required, because the UI's `=== true || === 'True'` dual-check already
  absorbs the boolean half; the change is documented for the frontend team regardless, since
  they own the follow-up that removes the dual-check.
- Existing accessor **names** on `ConfigBase`/`ConfigManager` do not change (FR-018). Only
  return types change, and only where the value is a structure.
- Deprecation messages use the single existing template — one format, not a second scheme.
- A migration guide maps every changed entry point to its replacement, for feature 008.

### IV. Performance Budgets Are Requirements

| Path | Baseline | Budget | Validation |
|---|---:|---|---|
| `load()` + `to_wire()` (the `project_load` path) | `read()` = 16.95 ms | **≤ 25 ms** | benchmark on the 24 KB corpus doc |
| `to_wire()` alone | tree build = 1.09 ms | **≤ 5 ms** | same |
| Suite wall time | 44.57 s | ≤ 10% regression | `hatch test` |
| Write path | — | ≤ 10% regression | existing perf test |

The 2× strategy was rejected on these numbers before any code was written, which is the point
of the principle.

**Gate result: PASS** (pre-Phase 0 and post-Phase 1). No violations; Complexity Tracking is
empty.

## Project Structure

### Documentation (this feature)

```text
specs/006-public-object-api/
├── plan.md              # This file
├── spec.md              # Feature specification (clarified 2026-08-18)
├── research.md          # Phase 0 — R1..R7
├── data-model.md        # Phase 1 — the config derived/hand-written line, settled
├── quickstart.md        # Phase 1 — how to verify the feature end to end
├── corpus-sweep.md      # Decision stop 2 evidence
├── sweep_t2.py          # …and the script that produced it
├── bench_to_wire.py     # R1's measurement
├── contracts/
│   ├── public-api.md    # The public surface, method by method
│   ├── wire-format.md   # to_wire() byte-identity guarantees
│   └── deprecations.md  # Every removed entry point and its replacement
└── checklists/requirements.md
```

### Source Code (repository root)

```text
src/cuemsutils/
├── cues/                      # show domain — CuemsScript is the public object
│   ├── CuemsScript.py         # + load/save/validate/from_json/to_json/to_wire
│   ├── Cue.py, MediaCue.py, …  # RUNTIME_FIELDS declarations replace _init_runtime bodies
│   └── CueOutput.py, FadeProfile.py, ActionCue.py, FadeCue.py   # setters delegate to T2
├── config/                    # NEW — config domain models (D11 landing site)
│   ├── __init__.py
│   ├── network_map.py         # node / node_list containers; 007 fills in behaviour
│   ├── settings.py            # settings + project_settings models
│   └── mappings.py            # project_mappings models — closes F14/F15
├── tools/
│   ├── ConfigBase.py          # accessors unchanged in name; return typed objects
│   └── ConfigManager.py       # 3 shape compensations deleted
├── xml/                       # INTERNAL — __init__ exports nothing
│   ├── __init__.py            # __all__ = []  (keep the two shim imports)
│   ├── mapper.py              # + encode_wire  (R1)
│   ├── validators.py          # → the T2 rule registry  (R5)
│   ├── settings.py            # readers bind to config/ models instead of GENERIC
│   ├── _deprecation.py        # unchanged mechanism
│   ├── Parsers.py             # legacy tree DELETED; facade kept until shims go
│   ├── Settings.py            # shim module — retained one release
│   └── XmlReaderWriter.py     # shim module — retained one release
└── create_script.py           # validate_template → script.validate()

tests/
├── contract/                  # byte-identity, wire format, public surface, deprecations
├── integration/               # D14 chain, perf
├── unit/
├── data/corpus/               # 28 frozen documents
└── golden/                    # dict/, xml/, api/, outcomes.json — never regenerated
```

**Structure Decision**: The existing layout is kept; the one addition is `cuemsutils/config/`,
which the target design §10 names as the config domain module and which D11 designates as the
node model's landing site. Show domain stays in `cues/`, machinery in `xml/`, public config
facade in `tools/`. The D9 PEP 8 rename is **not** part of this feature — it landed with 004.

### Sequencing

Ordered so each step is independently green, per target design §13 steps 5 and 7:

1. **`encode_wire` + the oracle test**, behind the existing API. No public change yet; the
   byte-equality gate must pass before anything is exposed.
2. **Public methods on `CuemsScript`** — `load`/`save`/`validate`/`from_json`/`to_json`/
   `to_wire`, delegating to machinery that already works.
3. **`RUNTIME_FIELDS`** declarations replacing the five `_init_runtime` bodies, with
   `_initialized` declared as the named exception.
4. **T2 registry** in `validators.py`; setters delegate; `validate()` reports, `save()` raises.
5. **`config/` models**; readers bind to them; `ConfigManager`'s three compensations deleted.
6. **Wire-format changes shipped together** (FR-031): drop `schemaLocation` from the dict,
   write the relative one, align `initial_template`.
7. **`xml/` goes internal**; shims added; legacy tree deleted; `create_script` migrated.

Step 1 before step 2 is deliberate and is the same rule 004 followed: the guarantee is proven
against current behaviour before the surface that depends on it exists.

## Complexity Tracking

No constitution violations. Table intentionally empty.
