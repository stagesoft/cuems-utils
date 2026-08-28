# Implementation Plan: Rebuild extension

**Branch**: `008-rebuild-extension` | **Date**: 2026-08-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-rebuild-extension/spec.md`

## Summary

Five structural changes to `cuemsutils`, planned as **one dependency chain** and landing in **two
gated phases**. ITEM A retypes the seventh and last time-carrying element and deletes two dead schema
surfaces; ITEM B gives the three remaining configuration domains a write path; ITEM C brings the
network map's domain logic into the repository that owns its schema; ITEM D builds a schema-derived
descriptor carrying enumerations, defaults and repairability; ITEM E makes reading strict and adds
document versioning, conversion and repair-and-notify.

The order is not negotiable (D28). A defines the new wire and creates the migration E must carry; B
supplies the write path E's upgrade path persists through; D supplies the defaults E's repair path
recovers to. **Phase 1 (A–D) must be merged and green before any Phase 2 (ITEM E) task starts** (D30),
so Phase 2 is written against §2 and §3 of [data-model.md](data-model.md) as *landed code* rather than
as planned interfaces.

Nothing ships until feature 009 lands (D27). The phase gate is **not** a release boundary.

## Technical Context

**Language/Version**: Python 3.11+ (tests under pyenv 3.11.9; conda not used)
**Primary Dependencies**: `xmlschema==3.4.3` (pinned — XSD 1.1 needed for `xs:assert` in `script.xsd`);
stdlib `ElementTree` is the write path and the pre-validation version probe. `lxml==6.1.0` is present
but **not** in the XML path.
**Storage**: XML documents on disk against six bundled XSD schemas
**Testing**: pytest via `hatch test --show`
**Target Platform**: Linux (Debian bookworm nodes; shared venv `/usr/lib/cuems`)
**Project Type**: Single library (`cuemsutils` on PyPI), consumed by engine, editor, nodeconf, common
**Performance Goals**: FR-PERF-002 — show load ≤ 200% and ≤ 50 ms absolute; config domain load
≤ 110%; suite ≤ 110% of 24.79 ms/test (007's baseline, 2026-08-24)
**Constraints**: `project_load` payload byte-identical (Part 2d hard constraint); no UI channel in the
library; five recorded D3 relaxations and no sixth
**Scale/Scope**: 6 schemas, ~56 complex types, 15 registered semantic rules, 2393-test suite

**No NEEDS CLARIFICATION remain.** Spec carries zero markers; every mechanism the audit left open
(E10 especially) is resolved in [research.md](research.md) R1–R10.

## Constitution Check

*Evaluated before Phase 0 and re-evaluated after Phase 1. Result: **PASS**, with one budget carried as
a measurement obligation rather than an assumption.*

### I. Code Quality By Default

Lint and type gates as the repository already runs them; no new warnings. Every public symbol added —
`LoadReport`, `Outcome`, `RepairRecord`, `ConversionRecord`, the four `save_*` accessors, the seven
`NodeIndex`/`CuemsNetworkMapType` methods — carries the rationale documentation the surrounding modules
already carry.

**Net effect is subtractive.** This feature deletes `create_script.py` (225 lines),
`templates/settings.xml` (5.1 KB), two model classes, five semantic rules, three schema types, two
enumeration values, one setter's three-branch dispatch and one dead adapter binding. New machinery is
the descriptor, the version/conversion registry and the report.

### II. Tests As A Release Gate

Each of the five items needs fail-then-pass tests, the discipline 005 applied to its six behaviour
changes.

- **ITEM A**: the seventh element's typing, storage and both wire shapes; the golden re-cut as a
  reviewed diff (standing rule 3's one recorded exception, D29) with originals retained.
- **ITEM B**: round-trip per domain; interrupted-write atomicity; **zero backups from routine saves**.
- **ITEM C**: **characterization tests written against `CuemsNodeConf`'s current behaviour *before* the
  port** (E23) — the discipline applied to code this repository does not own yet, so equivalence is
  measured rather than reviewed by eye. They must fail against an empty implementation.
- **ITEM D**: field-set equality against each schema's content model; enum values equal to facets;
  defaults present as values; zero unclassified fields.
- **ITEM E**: **round-trip tests, not unit tests of pieces** — each of D21's three outcomes, the
  version marker, the identity step (SC-016f, which none of this feature's own transformations
  exercises), and the newer-than-library diagnostic.

### III. Consistent User Experience

New user-facing surfaces are the repair report and the conversion tool. Both follow the existing error
surface's conventions rather than inventing a second vocabulary (FR-UX-001). Every item with consumer
impact gets a migration-guide entry at call-site granularity, as 007 did — including the engine's
`CTimecode(cue.media.duration)`, its now-unreachable `_handle_fade_in`/`_handle_fade_out`, the editor's
raw-dict fixups and parser call sites, `repair_durations.py`, and the frontend's ~7 template call sites.

### IV. Performance Budgets Are Requirements

Three budgets, set before implementation (FR-PERF-002), measured by the method in
[quickstart.md](quickstart.md). Pre-feature figures are **re-measured on this branch** (SC-024a);
006's are superseded and 007's supplies only the suite figure.

**Carried openly**: ITEM E adds T2 to every read, and the cost is not yet known. The strictness is
intentional despite it, but a budget exceeded is recorded as exceeded and either mitigated or
explicitly approved — never restated as passing. That is a measurement obligation, not a violation.

### Gate result

No violations. **Complexity Tracking is empty by design** — see §Complexity Tracking for why the two
candidates are not violations.

## Project Structure

### Documentation (this feature)

```text
specs/008-rebuild-extension/
├── plan.md              # This file
├── spec.md              # 81 FRs, 43 SCs, 4 clarification sessions
├── research.md          # Phase 0 — R1..R10
├── data-model.md        # Phase 1 — incl. the two hand-off interfaces (§2, §3)
├── quickstart.md        # Phase 1 — measurement method, phase-gate check
├── contracts/
│   └── public-api.md    # Phase 1 — the additive public surface
├── checklists/
│   └── requirements.md
├── baseline.md          # Created during implementation
├── migration-guide.md   # Created during implementation — 009's handoff
└── tasks.md             # NOT created by /speckit.plan — see §The deliberate stop
```

### Source code

```text
src/cuemsutils/
├── errors.py                    # E: LoadReport, Outcome, RepairRecord, ConversionRecord
├── create_script.py             # D: DELETED
├── cues/
│   ├── CuemsScript.py           # E: load() becomes strict, load_with_report()
│   ├── MediaCue.py              # A: set_duration collapses; fade_profiles removed
│   ├── AudioCue.py, VideoCue.py # A: fade_profiles declared defaults removed
│   └── FadeProfile.py           # A: DELETED
├── config/
│   ├── settings.py              # A: CTimecodeType deleted.  B: save()
│   ├── mappings.py              # B: save() for project_mappings
│   └── network_map.py           # C: refresh()
├── tools/
│   ├── NodeList.py              # C: merge/adopt/unadopt/signature/missing_adopted
│   ├── ConfigManager.py         # B: three save_* accessors.  E: strict accessors
│   └── ConfigBase.py            # E: strict accessors
├── xml/
│   ├── schemas/script.xsd       # A: duration promoted; fade-profile + ActionType deletions
│   ├── schemas/settings.xsd     # A: dead timecode pair deleted
│   ├── schemas/*.xsd            # E: doc_version attribute on all six roots
│   ├── adapters.py              # A: TimecodeType binding — verify, then remove
│   ├── validators.py            # A: media_duration str branch.  D: register(repairable=)
│   ├── spec.py                  # E: exclude doc_version from attribute derivation
│   ├── mapper.py                # E: emit doc_version in build_document
│   ├── descriptor.py            # D: NEW
│   └── versioning.py            # E: NEW — marker probe + conversion registry
└── templates/settings.xml       # D: DELETED

tests/
├── data/corpus/pre-008/         # A: retained originals — E's conversion fixtures
├── golden/                      # A: re-cut once, reviewed
├── unit/, integration/, contract/
```

**Structure Decision**: single library, existing layout. Two new modules under `xml/` —
`descriptor.py` and `versioning.py` — both internal per Q14. The descriptor is placed there rather
than at top level because it reuses `spec.derive()` and the registry's loaded schema objects; nothing
public imports it (009 reaches it through the façade).

## The dependency chain, item by item

### ITEM A — timecode typing and canonical form *(Phase 1)*

Promote `Media.duration` to `cms:CTimecodeType`, put it on the same `format_timecode` /
`_CTimecodeAdapter` machinery as the other six, and remove what the change strands. Delete
`settings.xsd`'s unreachable timecode pair with its Python binding, and the fade-profile surface.
`script.xsd`'s `TimecodeType` **survives** — it is the inner `<CTimecode>`'s lexical type.

The wire changes deliberately, in XML and JSON alike. **No "wire unaffected" check is written** — E4
settles that the field is bound to `_String()`, so no such version of this change ever existed.
Goldens are re-cut **once** as a reviewed diff, originals retained under `tests/data/corpus/pre-008/`.

*Judgeable without ITEM E: seven elements, one type, one machinery, zero string exceptions, dead code
gone.*

### ITEM B — configuration write paths *(Phase 1)*

`save()` for `settings`, `project_settings`, `project_mappings`, symmetric with the landed
`network_map` path, plus three `ConfigManager` accessors. Atomic via temp-file + `os.replace`; no
backup. **Second, not fourth, because ITEM E persists through it.**

*Judgeable without ITEM E: four domains round-trip byte-identically; interrupted writes leave whole
files; zero backups from routine saves.*

### ITEM C — network-map configuration object *(Phase 1)*

Seven methods on `NodeIndex`/`CuemsNetworkMapType`, discovery passed in rather than reached for.
Characterization tests come from `CuemsNodeConf`'s current behaviour **first**. Records the
target-design basis for the daemon's other nine responsibilities without executing the split (D23),
accounting for the live UI at the end of its dispatch chain (E20/E25). Resolves the `self.cm` defect
in `cleanup()` (FR-025).

*Judgeable without ITEM E: characterization parity, zero nodeconf imports.*

### ITEM D — schema descriptor *(Phase 1)*

New module over all six schemas, reusing `derive()` for structure and adding enum facets, defaults and
repairability. Deletes `create_script` and `templates/settings.xml`. Narrows `ActionType` by deleting
`fade_in`/`fade_out` (FR-029a) — **kept separate from ITEM A's fade-profile deletion**, and the two
must stay independently revertible (FR-029c, SC-012c).

*Judgeable without ITEM E: coverage, facets, defaults, zero unclassified fields — the repairability
classification is judged on its own terms here even though its only consumer arrives in Phase 2.*

### ITEM E — validate on load, versioning, repair *(Phase 2)*

Strict reading across all six schemas with D21's three outcomes; the `doc_version` marker; the
conversion registry carrying `script` 1→2's three transformations at one step; the public report; the
standalone tool. Reverses standing rule 8 for **semantic** validation only, recorded as a decision.

**Honest about coverage** (FR-039): every registered rule targets a `script.xsd` type except one
`project_mappings` rule. Four domains have zero. "T2 across six schemas" is mostly plumbing there, and
saying so is what keeps the measured cost from being attributed to enforcement that is not happening.

## The deliberate stop (D31)

**`/speckit.tasks` does not run from here.** This is the only stop in the rebuild. Before tasks are
generated, four things are settled in this plan:

**1. The phase boundary.** Phase 1 = ITEMs A, B, C, D. Phase 2 = ITEM E. Phase 1 **merged and green**
before any Phase 2 task starts. The rule that applies between features, applied once inside this one.

**2. The two hand-off interfaces are fixed by name and shape** — [data-model.md](data-model.md) §2
(config `save()`) and §3 (the descriptor, including defaults *and* the repairability classification).
Phase 2 is implemented against these as landed code. If either is negotiable when Phase 1 merges, the
gate bought nothing.

**3. Phase 1 stands alone — checked, not assumed.** Every ITEM A–D acceptance criterion above and in
the spec is judgeable with no part of ITEM E in the tree. The one that needed care: ITEM D's
repairability classification (FR-031a) is a Phase 1 deliverable whose **only consumer is in Phase 2**,
so it is judged on its own terms — zero unclassified fields, every rule declaring — rather than by
exercising a repair. That is stated in the spec at US4 scenario 4b and SC-011a/SC-011b.

**4. What the gate is not.** Not a release boundary — D27 holds, nothing ships until 009. Not a scope
split — one spec, one plan, one tasks.md, one feature number, one migration guide.

When tasks are generated, the gate must be **structure, not a comment**: every task grouped under
Phase 1 or Phase 2, an explicit gate task between them, and no Phase 2 task marked parallel-safe with
a Phase 1 task.

**Then `/speckit.optimize`** — read against D28. It looks for parallelisation and this feature has
deliberately given some up. Accept findings *within* a phase; reject any that reorder across the seam
or move work earlier than the item it depends on.

## Complexity Tracking

*No constitution violations. Two candidates were considered and are recorded here as accounted-for
rather than left for a reviewer to raise.*

| Candidate | Why it is not a violation |
|---|---|
| **Five items in one feature** | The dependency chain (D28) is the argument: each is the next one's precondition, so five feature numbers would serialise the same work behind five review cycles. D27 already establishes none ships independently. The seam that *does* exist — A–D vs E — is honoured as a hard phase gate rather than ignored. |
| **Five D3 relaxations** | Signed off by the repo owner, 2026-08-27, recorded in the spec's D3 section with a per-change character table. Four of five delete or add things nothing honours; only `Media.duration` changes a live field's meaning. The precedent explicitly does not extend to X1–X13, to schema edits in features without a conversion path, or past this feature. |
