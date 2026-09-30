<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Implementation Plan: uuid4 convergence

**Branch**: `012-uuid4-convergence` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-uuid4-convergence/spec.md`

## Summary

One identity shape across the project, and the machinery that gets a deployed cluster there
without losing a node.

The work is four things in a forced order. A read-only **check** learns whether a machine needs
the migration and never writes. A **re-mint** replaces every node identity by literal 36-character
token substitution across the three configuration documents *and* the project library, from a
substitution table built once on the controller and persisted before the first write. The two
reaches have different scopes: configuration documents are rewritten **per node** from that
distributed table, while the library is rewritten **once on the controller** and replicated by the
project deployer that already carries every other library change (R11). Only then
does the **schema narrow** — uuid4 lowercase, plus the not-provisioned sentinel, admitted as a
union of two separately named definitions — in **three** schemas: the network map and the project
mappings take their first document-version step, the settings schema takes its second. Finally the
**library surface** stops handing consumers two types for one value.

The technical approach turns on seven measurements (see [research.md](research.md)): the adapter
table is a per-schema opt-in that only `network_map` has, so the own-identity type change needs a
per-**field** opt-in instead (R1); the document-scoped rule tier already supports the cross-row
uniqueness check, with two precedents (R2); the script filename is **not in any configuration this
library can read**, so scripts are found by root element rather than by name (R3); the version
step needs **no** registered conversion, because the machinery represents an identity step as the
absence of one (R5); clone detection already has both its inputs in scope (R6); the library is
replicated from the controller by rsync with no checksum flag, so a length-preserving rewrite is
visible to it **only** through the modification time (R11); and the library reach is required
rather than precautionary, because both a bare and an embedded identity are measured there
(R12).

## Technical Context

**Language/Version**: Python 3.11+ (tests under pyenv 3.11.9)
**Primary Dependencies**: no new runtime dependency. `xmlschema==3.4.3` (pinned, XSD 1.1), stdlib
`xml.etree.ElementTree` for every path that must survive an invalid document
**Storage**: files only — `/etc/cuems/*.xml`, `<library_path>/{projects,trash/projects}/*/`, and
one new persisted substitution table under the tool's existing state directory
**Testing**: pytest via `PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:run` (`hatch` is not
installed on this box; the `hatch test` env lacks `hypothesis`)
**Target Platform**: Debian bookworm nodes, shared venv `/usr/lib/cuems`
**Project Type**: single Python library plus console entry points
**Performance Goals**: **>= 500 MB/s** scanned and rewritten over the library, measured at two node
counts that must agree **within 1%** so an accidental per-node pass shows as a divergence; named
fixture **`remint_200`** (200 projects, ~4 MB) within **2.0 s**, provisional and adjustable
downward only; operator estimate within **+/-25%** of actual; read-path timings within feature
008's recorded baseline
**Constraints**: no library version change (`0.1.0rc16` is pinned by
`tests/packaging/test_no_version_bump.py`); nothing ships from this branch alone (D27); the
re-mint must be idempotent and resumable; every path that reads a possibly-invalid document uses
stdlib XML only
**Scale/Scope**: cluster of ~2–10 nodes; library of order 10²  projects, single-digit MB
(largest corpus script ~24 KB, whole corpus 504 KB)

## Constitution Check

*GATE: evaluated before Phase 0, re-evaluated after Phase 1. Result: **PASS**, with one
justified deviation tracked below.*

### I. Code Quality

- Lint/type gates: the project's existing tooling, no new warnings. Every new public symbol
  carries documentation; every non-obvious decision cites its research item by number, which is
  this repository's established convention.
- The one readability risk is `init_node.py`, already a large module gaining four behaviours. The
  cluster-wide re-mint and the library enumeration go in **new modules** rather than growing it
  further, with `init_node` calling into them.

### II. Testing Standards

| Level | What it covers |
|---|---|
| contract | the tightened patterns against every non-converged shape; the uniqueness rule's registration and unrepairability; rule-target resolution (trap 7.6); schema hashes moved in the same commit (trap 7.5); the divergence entry's removal from the allowlist |
| integration | the full re-mint over a fixture cluster with a project library; abort on collision; idempotence; resume after interruption; clone refusal; the check's no-write property |
| unit | token substitution including compound strings; root-element script discovery; the per-field adapter opt-in; identity ordering; the estimate's arithmetic |
| performance (in `tests/integration/`) | throughput at two node counts; the `remint_200` fixture's wall-clock; read-path against feature 008's baseline; the estimate's accuracy |
| the replication property | a rewritten library file's modification time advances, so the size-and-time quick check transfers it (FR-011b, R11) |

Fail-before-pass is required for every behaviour change. Two specific traps are tested rather
than assumed: negative fixtures are re-checked for *which* error they now raise (trap 7.3,
FR-027), and goldens are never regenerated to make a test pass (trap 7.2, FR-021's precedent).

### III. UX Consistency

User-facing surfaces: the identity tool's check and re-mint output, the confirmation prompt, the
duration estimate, and the validation error naming the repair tool. All follow the conventions
feature 011 established — the same reporting style, the same `--yes` requirement for a
destructive step, the same `--dry-run` affordance, and the same exit-class vocabulary
(0 / 1 / 2 / 3) extended rather than replaced.

### IV. Performance Requirements

Declared as **values**, not shapes — the analysis pass caught this as the feature's one
constitution violation, since a budget with no number cannot fail a test:

| Budget | Value | Provisional? |
|---|---|---|
| Re-mint throughput | >= **500 MB/s** scanned and rewritten | no |
| Agreement between the two node counts | within **1%** | no |
| Named fixture `remint_200` (200 projects, ~4 MB) | <= **2.0 s** wall-clock | **yes** — adjustable downward after measurement, never upward |
| Operator estimate vs. actual | within **+/-25%** | no |
| Read path (show and configuration documents) | feature 008's recorded baseline | no |

The fixture ceiling is the only estimate, and it is marked so that adjusting it is a recorded
decision rather than a silent relaxation. Budgets are recorded **as measured**, including when
exceeded — this repository's standing practice.

### Gate result

**PASS.** Two deviations are tracked in Complexity Tracking: this feature amends another
feature's landed decision record, and it adds three modules rather than extending one.

**One violation was found after this gate and is now closed.** The `/speckit.analyze` pass
(2026-09-30) found Principle IV unsatisfied: the budgets were stated in shape only, with no value
anywhere, so no performance test could fail. The values above close it. Recorded rather than
quietly fixed, because a gate that passed on an unmeasurable budget is worth a reader knowing
about.

## Project Structure

### Documentation (this feature)

```text
specs/012-uuid4-convergence/
├── plan.md              # This file
├── research.md          # Phase 0 — R1..R12 (R11, R12 added 2026-09-30)
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1
│   ├── cli-check.md
│   ├── cli-remint.md
│   └── library-surface.md
├── checklists/
│   └── requirements.md
├── tasks.md             # /speckit.tasks
├── consumer-census.md   # T060 — the FR-032 artifact, blocking Phase 6
├── migration-guide.md   # Phase 7
└── baseline.md          # T003 and T081 — every measurement, as measured
```

### Source Code (repository root)

```text
src/cuemsutils/
├── tools/
│   ├── Uuid.py                 # + total ordering (FR-029)
│   ├── identity_check.py       # + shape classification, library reach, __all__ (FR-001..005, FR-031)
│   ├── init_node.py            # + collision abort, --uuid map check, clone refusal, estimate
│   ├── remint.py               # NEW — substitution table, apply loop, idempotence, resume
│   ├── library_reach.py        # NEW — library enumeration; shared by the check and the re-mint
│   └── ids.py                  # NEW — classification, token scanner, published coercion rule
├── xml/
│   ├── schemas/
│   │   ├── network_map.xsd     # UuidType narrows; doc_version 1 -> 2
│   │   ├── project_mappings.xsd# NodeMappingType/uuid narrows; doc_version 1 -> 2
│   │   └── settings.xsd        # NodeConfType/uuid typed; doc_version 2 -> 3
│   ├── adapters.py             # per-field adapter opt-in (R1)
│   ├── registry.py             # the opt-in's binding surface
│   ├── validators.py           # + node identity uniqueness rule (R2)
│   └── versioning.py           # CURRENT_VERSION bumps only; NO conversions registered (R5)
└── config/
    └── settings.py             # accessor return type follows the decoded type

tests/
├── contract/                   # patterns, rule registration, hashes, allowlist
├── integration/                # re-mint, abort, resume, idempotence, clone refusal —
│                               #   and the timings: this repository keeps performance
│                               #   tests here, so no tests/performance/ is introduced
├── unit/                       # substitution, discovery, ordering, estimate
└── support/                    # cluster and library fixture builders
```

**Structure Decision**: single-project layout, unchanged. **Three** new modules rather than growth
of an existing one: `tools/remint.py` carries the cluster-wide operation (which is not
`init_node`'s per-node job); `tools/ids.py` carries the classification vocabulary, the token
scanner and the published coercion rule, which must live outside `cuemsutils.xml` because
consumers may not import that package (Q14); and `tools/library_reach.py` carries library
enumeration, which is **shared** — the read-only check needs it as much as the re-mint does, so
folding it into `remint.py` would make a read-only diagnostic import the module that performs the
destructive operation. Performance tests go in `tests/integration/`, where this repository already
keeps them.

## Phase sequencing, and why it is forced

```
Phase A  the check                 US1   independent, ships value alone, writes nothing
Phase B  the library surface       US4   independent of A; blocked on the census (FR-032)
Phase C  the re-mint               US2   needs the foundational phase only; the bulk
Phase D  the narrowing             US3   MUST be last — see below
Phase E  the migration guide       US5   needs C and D measured, not assumed
```

**D is last and that is not a preference.** Landing the tightened pattern before C exists
invalidates every deployed identity with nothing able to repair it — §9.3's "shipping a brick".
Inside D the order is also forced: the schema hashes, the `CURRENT_VERSION` bumps and the removal
of the divergence entry from `KNOWN_DIVERGENT_DECLARATIONS` move **in one commit**, because while
that entry is listed its own test *requires* the collision to still exist (trap 7.5, FR-025).

**B is blocked on a measurement, not on code.** FR-032 makes the consumer census a precondition.
R4 has done the measurement — only `cuems-engine` and `cuems-power-bridge` read the accessor, and
every measured site is equality, f-string, set membership or hashing, all of which the identity
type already supports — but the recorded per-repository artifact is a task.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| This feature **amends feature 011's D13**, a landed decision in another feature's record (FR-019d) | D13's "mint iff there is none" is precisely what makes a cloned disk keep the original's identity. R1 of the collision routes (M-l) cannot be closed without changing it. Leaving it means uuid4 convergence delivers a cluster that re-collides on the next clone — which is how venues provision | Detecting the clone elsewhere (a separate tool, or the check alone) was rejected: the check is read-only by FR-003, and a second tool that can refuse an identity the identity tool just accepted puts two authorities on one decision. The amendment is recorded against 011 as its own task rather than applied silently |
| **Three** new modules rather than extending `init_node.py` | The cluster-wide re-mint is not the per-node tool's job, and `init_node.py` is already large. The coercion rule must live outside `cuemsutils.xml` because consumers may not import it (Q14). Library enumeration is its own module because it is **shared**: the read-only check needs it as much as the re-mint does | Extending `init_node.py` was rejected on Principle I — it would grow a module already carrying four new behaviours from this feature alone. Folding `library_reach.py` into `remint.py` was rejected separately: it would make a read-only diagnostic import the module that performs the destructive operation, which is the coupling FR-003 exists to keep out |

## Post-design constitution re-check

Re-evaluated after Phase 1 artifacts: **PASS**, unchanged. The design added no dependency, no new
storage system, and no user-facing surface outside the conventions feature 011 established.

**Re-evaluated again after `/speckit.analyze` (2026-09-30): PASS.** One Principle IV violation was
found and closed with stated values; one deviation row was corrected from two modules to three.
The analysis pass added no dependency either — the distribution question (U1) was answered by
naming machinery that already exists rather than by building any, which is why it changes the
requirements and the guide but not the technical context.
