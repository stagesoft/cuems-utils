<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Implementation Plan: The consumer-gate closure

**Branch**: `015-consumer-gate-closure` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/015-consumer-gate-closure/spec.md`
**Phase 0**: [research.md](research.md) — twelve findings, all measured on this branch

## Summary

Close the five items that gate the coordinated `xml-refactor-merge-candidate` tag, plus the four
non-gate library gaps the planning folder had left stray, plus the sweep that lets that folder be
deleted. Three sibling repositories are holding tests red against this feature; one of the five
items is a defect that makes an ordinary deployed node un-migratable by any shipped tool.

**The technical approach, in one line per gate**, derived in Phase 0:

| Gate | Approach | Phase 0 |
|---|---|---|
| **G1** write target for a file that does not exist | keyword-only `must_exist: bool = True` on both path helpers | R5 |
| **G2** public read for a project's settings | the absent-file branch holds an empty document; a `project_settings` property; one new member in the section set | R6 |
| **G3** the descriptor's instance | build the instance as a fully-populated value and project it through **`Mapper.encode_wire`** — the same call `to_wire()` uses — so wire shape is structural, not re-derived; seed every field by **eight ordered rules** — six over facets, rule 7's five-entry pattern table, rule 8's seven built-ins | R1, R2, R3 |
| **G4** the operator's node label | an in-place `set_alias` on the node index, validating before mutating | — |
| **G5** the version step defeated by the reshape | address both player spellings in one loop; the red test is the tool composition | R7 |
| **S1** structured collision | internal `ValueError` subclass carries the data; the accessor promotes it to a public `ValidationError` subclass with the path attached | R4 |
| **S2** union is not an enumeration | report a closed choice set only when every union member is an enumeration | — |
| **S3** the writer indents | `ET.indent` in `write_tree`; two corpus documents re-authored | R8 |
| **S4** + sweep | docstring statement, nine deletions, two corrections, two sweep gaps, tag-anchored cross-repo validation, the **one** golden event (6 XML + 2 API + manifest) | R9, R12 |

**The single most consequential design decision** is G3's: projecting the instance through the
existing encoder rather than transforming it in the descriptor. It makes three requirements true by
construction and it refuses to relocate — from TypeScript into Python — the drift that the schema
descriptor exists to end.

## Technical Context

**Language/Version**: Python 3.11+. The box was migrated 2026-10-13 (anaconda removed, pyenv and the
toolchain reinstalled), so the suite runs on CPython **3.11.9** — matching the convention's version
for the first time. Two 3.11.9 builds exist; after pyenv's was rebuilt with
`--enable-optimizations --with-lto` they agree to within **0–2%** (R11). The binding interpreter for a
recorded figure is the one `hatch` resolves; a pyenv build without PGO+LTO diverges by **32–72%**.
**Primary Dependencies**: `xmlschema==3.4.3` (pinned, XSD 1.1), `lxml==6.1.0` (not in the write
path). **No new runtime dependency** — every item is reachable with the pinned schema library and the
standard library (`xml.etree.ElementTree.indent` is stdlib since 3.9).
**Two dev dependencies are re-bounded, and the constitution requires the justification**
(*"Dependency additions MUST be justified in the plan with maintenance impact"*): `mypy>=1.0.0` →
`>=2.4.0,<3` and the entirely unpinned `ruff` → `>=0.17.0,<0.18`, by T127. **The justification is
that this feature turns both tools' finding counts into release gates** (80 and 606), and a gate
whose instrument floats measures the tool rather than the code — FR-PERF-005's lesson about naming
the interpreter *build*, arriving a second time for a different class of instrument. **Maintenance
impact**: a bump inside either bound may still move the count and re-baselines deliberately (T136);
a bump *past* either bound now requires a decision instead of happening on the next clean env build.
Ruff is bounded tighter on purpose — at 0.x the minor is the breaking unit. The other five test-env
dependencies stay unpinned (FR-113a): none defines a recorded figure.
**Storage**: XML documents under `/etc/cuems` and the project library; no database.
**Testing**: pytest via `uvx hatch run test.py3.11:run`; ruff via `…:lint`; mypy via
`uvx hatch run types:check src/cuemsutils`. Contract, integration and unit tiers already exist and each gate lands
in the tier that matches its surface.
**Target Platform**: Debian nodes (bookworm/trixie), shared venv `/usr/lib/cuems`.
**Project Type**: single shared library (`cuemsutils` on PyPI), consumed by five Python repositories
and one Angular UI.
**Performance Goals**: no regression on four paths, stated against **branch-point** figures
re-measured after the migration, in the same session (R10, eight samples each): show-document save
**13.612–14.297 ms**, descriptor derivation (`script`) **1.015–1.060 ms**, suite
**8.73–8.93 ms/test**, and the show-document load as a **band** — 16.465–17.750 ms over 16 samples in three windows, which **straddles** its
16.5 ms budget (14 of 16 over).
**Constraints**: additive public surface only (FR-100); no schema version step (FR-101); the
per-schema decode asymmetry preserved (FR-102); **115%** budget tolerance — the pooled spread over
16 samples in three windows is **7.8%**, which corroborates 014's ±4–8%. ⚠ This plan briefly revised
it to 110% on one five-sample window reading 2.9%; the narrowest window is not the instrument (R10).
**Scale/Scope**: six bundled schemas; 30 named simple types + 7 built-ins to seed; 64
required-with-no-default fields across 19 types; **9** planning documents to delete, **2** to
correct, **1** to re-home, and the **21**-file `xml-rebuild/` subtree to disposition row by row;
7 sibling repositories, 4 of which carry a candidate tag; **10** obligations on other repositories,
collected in `consumers_works.md` — six of them in repositories this feature does not touch.

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1 — see the re-check at the end.*

### I. Code Quality By Default

- **Gates**: `uvx hatch run test.py3.11:lint` (ruff over `src/` and `tests/`) must introduce no new
  finding, **and** `uvx hatch run types:check` (mypy over `src/cuemsutils` and `tests`) must
  introduce no new finding either.
  ⚠ **Corrected by the analyze pass.** This plan previously declined the type gate — *"not part of
  the suite's release gate today and this feature does not add one"* — while Principle I requires
  passing **static checks** and SC-QUALITY-001 requires *"no new lint or type warning"*. Those three
  positions could not all stand, and `pyproject.toml:172-177` has defined
  `[tool.hatch.envs.types]` → `mypy>=1.0.0` with a `check` script the whole time. Both gates are now
  claimed, **compared against a registered branch-point baseline** rather than against zero: neither
  tool is clean on this tree today, and a gate stated as "clean" that has never been clean is a gate
  nobody runs twice. **Measured and registered 2026-10-13** —
  `snapshots/types-before.txt`, **80 errors in 26 files (checked 68)**, mypy 2.4.0, scoped to
  `src/cuemsutils` by maintainer decision. Four of the nine files this feature edits are at zero,
  including `errors.py` and `tools/NodeList.py` where S1's exception class and G4's setter land, so a
  new finding there has nothing pre-existing to hide in — which is the argument for the gate, and a
  better one than the constitutional reading that first surfaced it.
  ⚠ **`types:check`'s own default scope is defective and is deliberately not used.** It checks
  `src/cuemsutils tests`, reporting 278 errors in 190 files — but **158 of those are the single
  module `pytest` being unimportable**, because `[tool.hatch.envs.types]` adds only `mypy` and none
  of the test dependencies that live in `[tool.hatch.envs.test]`. That is a defect in the env
  definition rather than a fact about the code; it is recorded here and in the baseline file, and it
  is **not this feature's to fix** — repairing another feature's tooling under a gate feature is how
  scope leaks.
- **The baselines descend, by maintainer decision 2026-10-13** (FR-107..FR-112): code quality is a
  requirement of the coming stable version, so both figures must be *lower* at the end of this
  feature and the lower figures become the gate. Registered branch point: **type 80 in `src/`**,
  **lint 606** (316 `src/` + 290 `tests/`). The tractable majority is mechanical — **302 of `src/`'s
  316** lint findings are whitespace, trailing whitespace, placeholderless f-strings and import
  order, and **all eleven** `# type: ignore` comments in `src/` are unused — so the sweep is large in
  diff and small in judgement.
  ⚠ **Two hazards, neither visible from a finding list, and `ruff --fix` hits both.** `I001` is not
  safely bulk-fixable here: `adapters._register_enums()` runs at import time and imports `NodeRole`
  back out of `NodeList` while that module is still initialising, which is why `NodeList` is a lazy
  module `__getattr__`, and a re-sorted import block can produce an `ImportError` **neither** static
  gate would catch. And `E721`'s correct fix is `type(x) is Y`, **never** `isinstance(x, Y)` — the
  24 findings in `tests/` assert *exact* type, a distinction 013's subclass dispatch depends on.
  Recorded in `snapshots/lint-before.txt` beside the findings, where whoever runs the sweep will be.
- **The sweep must not cost the project its rationale.** Sixteen `noqa` directives in `src/` name
  rules this project does not select, so they suppress nothing — but they carry the *reason* the code
  is written that way (*"a broken universe must still name itself"*). They become plain comments;
  **zero sentences are lost**. That is the way this task fails while every number improves.
- **Documentation obligation is unusually load-bearing here** and is itself a requirement, not a
  courtesy: FR-045 (the map has one runtime writer), FR-078 (the projection fills model defaults for
  omitted optional elements), FR-UX-003. Two consumers have already read a call the wrong way
  **because** the docstring did not say.
  ⚠ **Corrected by the analyze pass**: `docs/` is mkdocstrings over an **explicit list of modules**,
  not over the source tree, and three of this feature's four documentation targets are not on it —
  `cuemsutils.errors`, `cuemsutils.tools.NodeList` and `cuemsutils.config.network_map` render
  nowhere today. So "the docstring *is* the published documentation" holds only for
  `cuemsutils.helpers` (FR-078's target). The three modules are added to `docs/` and the gap is
  closed by a test (FR-UX-003a, FR-UX-003b), because a docstring nobody renders is the same failure
  this obligation exists to prevent.
- **Rationale recorded next to the decision, not only in specs**: FR-026 reverses a position
  recorded in `TypeDescriptor.instance`'s own docstring, and FR-026a is the reason. Both go beside
  the code.

### II. Tests As A Release Gate

- **Fail-before-pass per requirement** (SC-TEST-001). Per tier:
  - **contract** — the seeding completeness and validity table (R3), the repairability-map
    invariance (SC-005a), the union narrowing across all five sites (FR-067), the collision's
    structured contract (FR-065), the aliasing contract extended to `set_alias` (FR-040), the
    tag-anchored cross-repo resolver (FR-080c), the indentation idempotence (FR-071).
  - **integration** — the first-save journey end to end (G1+G2 together, R6's synergy), the
    `project_settings` round trip (FR-013), an instance of every root saving (FR-023), **the tool
    composition for G5** (FR-053 — explicitly *not* a unit test on the converter).
  - **unit** — the eight seeding rules, the two-shape element lookup, the label validation ordering
    (and, with it, the one new diagnostic's shape — FR-UX-001's only subject).
- **The branch point is not green, and the suite must end green** (SC-TEST-002): five failures are
  recorded in the spec with attribution and **all five are this feature's to dispose of** — FR-079
  disposes of one, FR-080 of the other four. ⚠ **Corrected by the analyze pass**: this read "no more
  than those five, each attributed", which five *new* attributed failures would have satisfied, and
  which sat badly against Principle II's *"merges MUST be blocked if any relevant test suite
  fails"*. Starting red is a fact about the branch point; it is not a budget. Tracked as an exception
  below, since the constitution requires exceptions to live in complexity tracking rather than in
  prose.
- **The one test this feature must retire** is `test_config_manager_save_accessors.py:77`'s
  monkeypatch of a public method (FR-007) — the defect's in-repository footprint.

### III. Consistent User Experience

- **Surfaces touched**: the public Python API (two path helpers, one property, one section name, one
  index method, one exception type, the descriptor's instance), two shipped CLI tools'
  behaviour-by-consequence (`cuems-reshape-devices` now succeeds where it refused), the bytes of
  every document written, and the rendered API documentation.
- **Conventions this feature must follow**: diagnostics name the document, the locus, the value and
  the remedy (FR-UX-001) — `cuems-reshape-devices`' own refusal is the model, measured as reading
  correctly in the one place it matters. No operator-facing wording that currently reads well is
  reworded as a side effect of adding structure behind it (FR-UX-002, FR-063).
- **The deliberate UX change** is S3: documents become human-readable after a UI save. It is the only
  intentional change to an operator-visible artefact, and it is the one with the largest test cost.

### IV. Performance Budgets Are Requirements

- **Budgets declared** (SC-PERF-001..005), each against a branch-point figure re-measured after the
  migration in the same session, at **115%**: save ≤ **16.4 ms**, descriptor derivation ≤ **1.22 ms**,
  suite ≤ **10.3 ms/test**; the show load compared against its **measured band** rather than a
  straddled line (FR-079a); the three configuration loads measured and reported whether or not they
  move (FR-PERF-004).
- **Validation approach**: the budget's own established method — best of three medians of five warm
  runs, one warm call first, fresh process — recorded in this feature's `baseline.md` with **the
  interpreter build** and the box's load average stated. Both are mandatory, and each has now cost
  this feature a wrong number: omitting the load average produced a phantom 2× regression, and
  omitting the build would let a pyenv-shim measurement read 42% over budget on unchanged code.
- **One budget is exceeded at the branch point and is deliberately not mitigated** (FR-079). This is
  an exception to Principle IV's "rejected or accompanied by a mitigation plan" and is tracked below.

**Gate verdict: PASS**, with **six** tracked exceptions — four by design and two added by the
analyze pass, which found them living in this plan's prose where the constitution requires them to
live in complexity tracking. None is a violation of a MUST that this plan leaves unjustified; all six
are decisions the spec states explicitly and the table below records why the simpler alternative was
rejected.

## Project Structure

### Documentation (this feature)

```text
specs/015-consumer-gate-closure/
├── spec.md                  # the requirements (5 clarifications + the analyze pass applied)
├── plan.md                  # this file
├── research.md              # Phase 0 — R1..R12, all measured on this branch
├── data-model.md            # Phase 1 — the entities and their invariants
├── quickstart.md            # Phase 1 — how to run and measure this feature
├── contracts/
│   ├── public-surface.md    # every public addition, with its exact shape
│   ├── seeding-rules.md     # the eight ordered seeding rules + two tables, as a contract
│   └── sibling-gates.md     # the seven sibling tests that flip, and the tag-anchored resolver
├── checklists/
│   └── requirements.md      # the specify-pass quality checklist
├── consumers_works.md       # every obligation on another repository, measured (FR-106) — 10 rows
├── snapshots/               # created in Phase 1 — repairability, union enums, lint, types before-states
├── baseline.md              # created during implementation — the measured budgets
├── migration-guide.md       # created during implementation — incl. R12's 21-file disposition table
└── tasks.md                 # /speckit.tasks output — NOT created by /speckit.plan
```

### Source Code (repository root)

```text
src/cuemsutils/
├── errors.py                     # S1: the new public exception type (+ __all__)
├── helpers.py                    # S4: `to_wire`'s docstring (FR-078); Unset read by the seeding rules
├── config/
│   ├── network_map.py            # G4: refresh/save already compare signature(); unchanged
│   └── settings.py               # G2: CuemsProjectSettingsType — the empty document
├── tools/
│   ├── ConfigBase.py             # G1: conf_path(must_exist=); S1: the accessor's promotion
│   ├── ConfigManager.py          # G1: project_path(must_exist=); G2: property + section set
│   └── NodeList.py               # G4: NodeIndex.set_alias
└── xml/
    ├── descriptor.py             # G3: instance via encode_wire + seeding; S2: _enum_values
    ├── documents.py              # S3: ET.indent in write_tree
    ├── mapper.py                 # G3: read-only reuse of encode_wire (no change expected)
    ├── spec.py                   # R1: NOT changed — _type_key stays as it is
    ├── validators.py             # S1: the internal structured ValueError
    └── versioning.py             # G5: _settings_1_to_2 addresses both player shapes

docs/
├── api.md                        # C1: + `cuemsutils.errors` (FR-UX-003a)
└── tools.md                      # C1: + `cuemsutils.tools.NodeList`, `cuemsutils.config.*`

tests/
├── contract/                     # seeding table, union narrowing, collision shape, aliasing,
│                                 # tag-anchored resolver, indentation idempotence,
│                                 # test_migration_guide*.py (FR-080)
├── integration/                  # first-save journey, project_settings round trip, root instances
│                                 # save, the G5 tool composition,
│                                 # test_config_manager_save_accessors.py (FR-007)
├── unit/                         # facet rules, two-shape lookup, label validation
├── golden/                       # 6 XML + 2 API goldens re-cut; MANIFEST.sha256
└── data/corpus/cuems-utils/      # fade_showcase.xml, unicode_showcase.xml re-authored indented

specs/planning/                   # the sweep: 9 deletions, 2 corrections, 2 gaps, 1 new record
```

**Structure Decision**: single-project library layout, unchanged. This feature adds **no new
module** to `src/`. That is a deliberate outcome of Phase 0 rather than a coincidence: every gate
resolved to an addition inside a module that already owns the concern — which is also the strongest
available evidence that the five gates were correctly scoped as "additive public-surface changes"
rather than as new mechanism. The one new file outside `src/` is
`specs/planning/show-document-load-drift.md` (R12, FR-079c).

## Implementation sequencing

Phase 0 surfaced one hard ordering constraint and two soft ones.

**Hard: S2 before G3's rule 2.** The union seeding rule reads a union's member types directly. Today
`_enum_values` merges a union's members' enumerations and reports `NodeUuidType` and
`AutoOrIntLatencyMsType` *as* enumerations — so if G3 lands first, seeding rule 1 fires on them and
produces the right value for the wrong reason, and the test that should pin rule 2 would pass
vacuously. S2 is four of five lines in the same function. **Order: S2, then G3.**

**Soft: G1 and G2 together.** R6 found they are one user journey: with an empty document present
after a tolerant load, `save_project_settings` works for a project's first save as soon as G1
supplies the write target. Landing them together gives one integration test instead of two partial
ones, and both re-cut the same two API goldens.

**Soft: S3 last of the code changes.** It re-authors two corpus documents and moves six XML goldens;
doing it before G1–G5 means every later change is reviewed against freshly moved goldens.

**Hard, found by the analyze pass: the golden re-cut comes after every public addition.**
`tests/golden/api/public_api.json` carries an `errors` section enumerating **every** public error
class with its bases and methods — so S1's `NodeIdentityCollisionError` moves that golden just as
G1's two signatures and G2's property do. The plan originally re-cut the API goldens inside G2, five
phases before S1 lands, which would have left the golden stale at the end of the feature and made
FR-074's *"one reviewable change"* true only of the record and not of the diff. **The entire golden
event — six XML goldens, two API goldens, the manifest, and the verification that the 24 wire-dict
goldens did not move — is therefore one block in the polish phase**, after US1, US2, US4, US5, US6
and US8 have all landed. The corpus re-authoring stays with S3, because it is a change to input
data rather than to a recorded output.

**G4, G5 and S1 are independent** of all of the above and of each other.

**The sweep (S4, FR-090..FR-095) is the polish phase**, by decision D2, and the deletions come last
of all — FR-090 makes the source document deletable only once every row is implemented or declined,
so deleting it earlier would remove the checklist against which that is verified.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **A straddled budget converted to a band instead of being mitigated** (FR-079/FR-079a, Principle IV says "rejected or accompanied by a mitigation plan") | The budget is straddled at its floor — 14 of 16 samples over, 2 under — so the assertion is **flaky on an unchanged tree**. The drift predates this feature and **survived a full interpreter migration across two 3.11.9 builds**, so the instrument is ruled out; against 013's measurement it is +13% to +19% | *Raise the budget* — the fourth raise in four features (35.99 → 15.0 → 16.5 → ?) and the first with no mechanism named; a detector raised whenever it fires passes by construction. *Leave the line* — keeps a flaky red that is indistinguishable from a real regression arriving. *Investigate here* — open-ended perf work inside a gate feature nothing depends on. The band has a direct precedent: 012's R14 did exactly this to 008's straddled `network_map` budget, for the same stated reason. FR-079c gives the drift an owner |
| **Reversing a recorded design decision** (FR-026: `TypeDescriptor.instance` is documented as "not required to be schema-valid… a seed the consumer fills") | Four of `cuems-editor`'s seven strict xfails assert that an instance **saves**. The recorded position and the gate cannot both stand | *Keep the position and close the gate another way* — there is no other way: the instance is the replacement for the retired `initial_template`, and a seed a client cannot save does not replace it. *Add an opt-in flag for a saveable form* — two shapes of one answer, and consumers would have to learn which to ask for |
| **Changing the bytes of every document this library writes** (S3, FR-070; Engineering Standards say refactors preserve behaviour unless the spec states otherwise — it does) | G1+G2 make UI saves of configuration documents routine for the first time, and operators hand-edit `settings.xml` and `network_map.xml`. A 44-line file becoming one line is a workflow regression | *Indent only the configuration write path* — two output forms from one writer, and the show path is the one with goldens, so the split buys little and costs a permanent asymmetry. *Leave it* — rejected by maintainer decision 2026-10-13 with the golden cost stated and accepted |
| **Editing a landed feature's migration guide** (FR-080b; `CLAUDE.md` treats landed specs as frozen record) | 012's guide gives an operator two instructions that cannot work today: require `cuems-engine 0.1.0rc7` (that tree declares `0.1.0-rev1`, a renamed scheme) and watch for `cluster_warning` (absent from its controller source) | *Freeze them as history* — a migration guide is simultaneously a frozen record **and** live operator instructions; freezing a wrong instruction leaves someone watching for a signal that no longer exists. The split in FR-080 is exactly this distinction, and only the operator-facing half is edited |

| **Starting from a red suite** (Principle II: *"merges MUST be blocked if any relevant test suite fails"*) | The branch point has five failures, measured and attributed in the spec. All five are **this feature's to close** — FR-079 disposes of one, FR-080 of the other four — so the exception is to the *starting* state, not the ending one: SC-TEST-002 requires the suite to end **green** | *Close them in a separate change first* — three of the four FR-080 failures are stale cross-repository assertions whose correct resolution **is** this feature's FR-080 analysis (split by assertion class, resolve at a tag); fixing them blind beforehand would have re-pinned moving commits a third time. *Leave SC-TEST-002 permissive* — it read "no more than the five", which five **new** attributed failures would satisfy; rejected by the analyze pass |
| **Two static gates compared against a baseline rather than against zero** (Principle I: *"no known warnings introduced"*) | Neither `ruff` nor `mypy` is clean on this tree today — **type 80 in `src/`, lint 606** — and a gate stated as "clean" that has never been clean is a gate nobody runs twice. **Amended by maintainer decision 2026-10-13: the baselines are a DESCENDING ratchet** (FR-109), since code quality is a requirement of the coming stable version. The gate asserts *below* the registered figure, not *equal* to it, and the end-state figures become the new gate | *Claim zero findings immediately* — 438 of the 606 lint findings are whitespace on blank lines touching nearly every file in `src/`; swept into the stories' diffs it makes both unreviewable, so it is one commit at the end (FR-110) rather than a precondition. *Hold rather than descend* — rejected: a hold would let 80 type and 606 lint findings sit unchanged forever provided nothing new was added, which is a baseline rather than a standard. *Keep declining the type gate* — rejected: Principle I names static checks, SC-QUALITY-001 names type findings, and `pyproject.toml` has defined `types:check` all along |

**Not tracked as a violation, and recorded here so the reading is not left to a reviewer**: R3's
five-entry pattern table. FR-028 forbids "a per-field hand-written table of fallbacks, and no
per-type special case". The table is keyed by **type**, covers the irreducible residue (a regular
expression cannot be inverted, and no runtime dependency generates a matching string), and is
guarded by a completeness contract test in the same shape as `seed_values.py`'s four rules and
`_assert_every_choice_member_has_a_builder`.
**The counts, stated once because three artefacts disagreed on them**: **eight** ordered rules.
Rules 1–6 derive **25 of the 30 named simple types** from facets alone; rule 7 is the five-entry
pattern table for the remaining five; rule 8 is a seven-entry table for the XSD **built-ins**. The
built-ins are *table-seeded, not facet-derived* — this plan and `contracts/seeding-rules.md` both
said "derived from facets alone" of them, which is the one claim FR-028 would actually care about if
it were true of a per-field table, and is simply inaccurate of a seven-entry per-type one.

## Constitution re-check, post-design

Re-evaluated after Phase 1, against the artefacts now in `contracts/` and `data-model.md`.

| Principle | Verdict after design | What changed during Phase 0/1 |
|---|---|---|
| I. Code Quality | **PASS** | Phase 0 removed the largest risk to it: R1 rejected widening `_type_key` once the measurement showed 27 consumers, 21 in the mapper, two of which use `child is None` as the definition of a leaf. The design now adds a third call site to a documented mechanism instead |
| II. Tests As A Release Gate | **PASS** | R3 converted "give 64 fields a usable default" from an untestable instruction into a closed, enumerable contract with a completeness test. R7 confirmed the G5 red test must be the tool composition, which the spec already required |
| III. UX Consistency | **PASS** | R8 found that `ET.indent` preserves mixed content by its own contract, so FR-073 needs no bespoke guard — and that exactly one mixed type exists to be at risk |
| IV. Performance Budgets | **PASS with one tracked exception** | R10 corrected the feature's own headline figure **three times** — a 2× regression (3 contended samples), a ~4% overrun (5 samples, one window), and finally a **straddled budget** (16 samples, three windows: band 16.465–17.750, 14 of 16 over). Tolerance went 110% → 115% → 110% → **115%**, settling where 014 had it. The lesson is recorded as FR-PERF-002's second clause |

**No new violation was introduced by the design.** Two were *removed* by it: the design no longer
touches `spec.py` (R1) and no longer needs a hand-written whitespace guard (R8).

### Constitution re-check, post-analyze (2026-10-13)

| Principle | Verdict | What the analyze pass changed |
|---|---|---|
| I. Code Quality | **PASS** | Two gaps closed, both of which this plan had argued its way past: the declined type gate (now claimed against a baseline) and the assumption that `docs/` renders the source tree — it renders an explicit module list, and three of four documentation targets were not on it (FR-UX-003a/b) |
| II. Tests As A Release Gate | **PASS with one tracked exception** | The branch-point-red suite moved from prose into complexity tracking, as Governance requires; SC-TEST-002 now requires a green end state. Four requirements that had no task at all (FR-100, FR-101, FR-102, FR-UX-001) acquired one, and SC-009 — whose only measurable form is a removal in a consumer — acquired an owner |
| III. UX Consistency | **PASS** | Unchanged in substance. FR-UX-001 is now asserted on the one new diagnostic this feature adds (`set_alias`'s refusal) rather than assumed from convention |
| IV. Performance Budgets | **PASS with one tracked exception** | Unchanged in substance; the straddled-budget exception stands as designed. Two figure bands that disagreed between spec and plan were reconciled to R10's eight-sample measurements (save **13.612–14.297 ms**, derivation **1.015–1.060 ms**) |

**The pattern worth keeping.** Five of the six substantive findings were places where an artefact
asserted something about *another* artefact or about the tree — that `docs/` renders a module, that
a golden does not record an error class, that a dead-end population exists in a working tree, that
seven sibling xfails are reachable — and was wrong because nobody had looked. None was a
disagreement about design. The cheap defence is the one FR-080c institutionalises for siblings:
assert against the artefact, not against a description of it.
