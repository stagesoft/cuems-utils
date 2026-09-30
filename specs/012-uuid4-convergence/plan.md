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
union of two separately named definitions under a third name that every element uses — in **three**
schemas: the network map and the project mappings take their first document-version step, the
settings schema takes its second. The network map's node identity is **retyped** to that union and
its own `UuidType` declaration **deleted**, because the overlap ratchet leaves no other way to
resolve the divergence this feature exists to close (R13). Finally the **library surface** stops
handing consumers two types for one value.

The technical approach turns on nine measurements (see [research.md](research.md)): the adapter
table is a per-schema opt-in that only `network_map` has, so the own-identity type change needs a
per-**field** opt-in instead (R1); the document-scoped rule tier already supports the cross-row
uniqueness check, with two precedents (R2); the script filename is **not in any configuration this
library can read**, so scripts are found by root element rather than by name (R3); the version
step needs **no** registered conversion, because the machinery represents an identity step as the
absence of one (R5); clone detection already has both its inputs in scope (R6); the library is
replicated from the controller by rsync with no checksum flag, so a length-preserving rewrite is
visible to it **only** through the modification time (R11); the library reach is required
rather than precautionary, because both a bare and an embedded identity are measured there
(R12); the overlap ratchet admits exactly one resolution for `UuidType`, and it is deletion rather
than narrowing in place (R13); and feature 008's baseline offers two comparisons, not one, because
its `network_map` row is recorded there as exceeded-or-marginal (R14).

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
**Performance Goals**: **>= 500 MB/s** scanned and rewritten over the library, measured at **2 and
10** nodes whose elapsed times must agree within a **1.10x ratio** so an accidental per-node pass
(which would be ~5x) shows as a divergence; named fixture **`remint_200`** (200 projects, ~4 MB)
within **2.0 s**, provisional and adjustable downward only; operator estimate within **+/-25%** of
actual, divided by the throughput the survey **measures on the machine** rather than by the floor;
read path against `specs/008-rebuild-extension/baseline.md` — the show-document row against its
budget, the `network_map` row against its measured 10.14-10.49 ms band (R14)
**Constraints**: no library version change (`0.1.0rc16` is pinned by
`tests/packaging/test_no_version_bump.py`); nothing ships from this branch alone (D27); the
re-mint must be idempotent and resumable; every path that reads a possibly-invalid document uses
stdlib XML only — **including the re-mint's survey and collision check**, which is a requirement
(FR-006a), not just a technique, because after the narrowing every document the tool repairs is
invalid and the collision abort must read a map the new uniqueness rule refuses
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
| contract | the tightened patterns against every non-converged shape; the uniqueness rule's registration and unrepairability; rule-target resolution (trap 7.6); schema hashes moved in the same commit (trap 7.5); **all four overlap tests passing together** after the rename-and-delete — no unrecorded name, no diverged copy, no stale entry (R13) |
| integration | the full re-mint over a fixture cluster with a project library; abort on collision; idempotence; resume after interruption; clone refusal; the check's no-write property; **the re-mint running on documents the tightened schema refuses** (FR-006a) |
| unit | token substitution including compound strings; root-element script discovery; the per-field adapter opt-in; identity ordering; the estimate's arithmetic and its measured-throughput input |
| performance (in `tests/integration/`) | throughput at 2 and 10 nodes with a 1.10x ratio bound; the `remint_200` fixture's wall-clock; the read path against feature 008's baseline, budget for one row and measured band for the other (R14); the estimate's accuracy |
| the replication property | a rewritten library file's modification time advances, so the size-and-time quick check transfers it (FR-011b, R11) |
| documentation | the migration guide is **checked**, not just written: every FR-033..FR-036c item present, and every version and component it names resolving in the sibling trees (US5's Independent Test, Principle II's "per story") |

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
| Agreement between **2 and 10** nodes | slower elapsed time <= **1.10x** the faster | no |
| Named fixture `remint_200` (200 projects, ~4 MB) | <= **2.0 s** wall-clock | **yes** — adjustable downward after measurement, never upward |
| Operator estimate vs. actual | within **+/-25%**, dividing by the **survey-measured** throughput, not the floor | no |
| Read path — show document | feature 008's recorded **budget** | no |
| Read path — `network_map` configuration document | feature 008's recorded **measured band**, 10.14-10.49 ms, because that row's budget is recorded there as exceeded-or-marginal (R14) | no |

The fixture ceiling is the only estimate, and it is marked so that adjusting it is a recorded
decision rather than a silent relaxation. Budgets are recorded **as measured**, including when
exceeded — this repository's standing practice.

### Gate result

**PASS.** Two deviations are tracked in Complexity Tracking: this feature amends another
feature's landed decision record, and it adds three modules rather than extending one.

**Two violations were found after this gate and both are now closed.** Recorded rather than quietly
fixed, because a gate that passed twice on something a test could not enforce is worth a reader
knowing about.

- The first `/speckit.analyze` pass (2026-09-30) found **Principle IV** unsatisfied: the budgets were
  stated in shape only, with no value anywhere, so no performance test could fail. The values above
  close it.
- The second pass the same day found **Delivery Workflow & Quality Gates** unsatisfied — "task
  breakdowns MUST include testing work and verification steps per story". US5 declared an Independent
  Test and Phase 7 was six writing tasks with nothing that checked the guide against it. A
  verification task closes it, and the documentation row in the testing table above now names the
  level it belongs to. The same pass also found that two of the *first* pass's own numbers could not
  do their job: the 1% agreement bound was below timing noise on the fixture it applied to, and the
  estimate, pinned to a throughput **floor**, would have missed its +/-25% tolerance by exactly the
  margin by which a good implementation beat the floor. Both are corrected above.

## Project Structure

### Documentation (this feature)

```text
specs/012-uuid4-convergence/
├── plan.md              # This file
├── research.md          # Phase 0 — R1..R14 (R11, R12 after the first analyze pass;
│                         #   R13, R14 after the second, both 2026-09-30)
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
│   │   ├── network_map.xsd     # node uuid retyped to NodeUuidType; its own UuidType
│   │   │                        #   DELETED, not narrowed (R13); doc_version 1 -> 2
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

**Re-evaluated a third time, after the second `/speckit.analyze` pass (2026-09-30b): PASS.** One
violation of the Delivery Workflow gate, closed with a verification task; two of the first pass's own
numbers corrected; eight requirements added and none removed. **Still no new dependency and no new
storage system**, and it is worth saying why, because three of the additions look like they would
need one:

- The **table's distribution** (FR-007) adds no transport. The operator copies one file, and that
  copy becomes a numbered step in the guide.
- The **completion record** (FR-017a) is another file in the state directory the tool already owns —
  the same directory as the write record and the substitution table — not a new store.
- The **collision procedure** (FR-036b) is documentation of a manual act, deliberately not automated,
  because the library cannot know which of two rows is the real node and a tool that guessed would be
  worse than one that refuses.

The one structural change is in the schema layer and it **removes** a declaration rather than adding
one: `network_map.xsd`'s `UuidType` is deleted so the name stops overlapping (R13). Three new named
types appear in its place, in three schemas, which is three declarations more than before — and they
are pinned by the same allowlist that pinned what they replace, so the surface the ratchet watches is
unchanged in kind.
