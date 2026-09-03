# Phase 0 research — consumer migration

**Date**: 2026-09-03 | **Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

The spec entered planning with **no** `NEEDS CLARIFICATION` markers — all eight were resolved
during `/speckit.specify` and `/speckit.clarify`. This document therefore records the *measured*
findings that shaped the plan, and the decisions the plan had to make on its own. Everything below
was checked against live code on 2026-09-03, not inherited from the audit documents.

Findings are numbered `R1`–`R9` to continue the rebuild's convention (`F` audit, `X` schema,
`E` extension, `C` consumer, `R` research).

---

## R1 — the consumer audit's call sites are accurate at their stated lines

**Verified, not assumed.** Part 6 (`C1`–`C12`) was measured 2026-09-03 by a different pass; this
one re-checked the load-bearing sites the plan sequences on, because a plan built on stale
coordinates sequences the wrong work.

| Claim | Verified |
|---|---|
| `cuems-editor` `CuemsWsServer.py:24` imports the deleted module | exact: `from cuemsutils.create_script import create_script, new_uuid`, with `:23`'s `from cuemsutils.xml import NetworkMap` above it |
| `cuems-wsclient` `network_map.py` carries the retired vocabulary three times | exact at `:33` (dataclass field, comment naming both retired values), `:93` (`_text(el, "node_type")`), `:108` (`!= "NodeType.slave"`) |
| `cuems-engine` `BaseEngine.py` role and online comparisons | exact at `:33`, `:410`, `:440`, and the `online == "True"` at `:443` |
| `cuems-engine` `BaseEngine.py` script load | exact at `:509` (`XmlReaderWriter`) and `:510` (`read_to_objects()`) |
| `cuems-nodeconf` `CuemsNodeConf.py` internal imports | exact at `:22` (`cuemsutils.xml.mapper`) and `:23` (`cuemsutils.xml.settings`), with `:26`'s `cuemsutils.timeoutloop` |

**Decision**: the plan uses these coordinates directly and does not re-audit. **Rationale**: two
independent passes agree at line granularity. **Alternatives considered**: a third full audit —
rejected as pure cost.

---

## R2 — the repository survey matches, including the two that cannot gate on tests

**Measured**: seven repositories, five without spec-kit, three not on `main`, and — the finding
that changes wave 1 and wave 3 — **two with no test directory at all**.

| Repository | Branch | spec-kit | `tests/` | `debian/` |
|---|---|---|---|---|
| `cuems-utils` | `010-consumer-migration` | yes | yes | yes |
| `cuems-engine` | `rc_1` | yes | yes | yes |
| `cuems-editor` | `rc1` | no | yes | **no** |
| `cuems-common` | `007-node-model-migration` | no | yes | yes |
| `cuems-nodeconf` | `feat/xml-refactor` | no | yes | yes |
| `cuems-frontend` | `main` | no | **no** | **no** |
| `cuems-wsclient` | `main` | no | **no** | yes |

**Decision**: Constitution II's "each consumer PR carries its own green suite" is recorded as
**costing nothing** in `cuems-wsclient` and `cuems-frontend` today, and both waves that touch them
create the missing coverage first. **Rationale**: a gate that passes vacuously is not a gate.
**Alternatives considered**: accepting the existing suites as evidence — rejected; `cuems-wsclient`'s
suite was green throughout the entire period its shutdown path selected zero nodes, because there
is no suite.

**Second consequence, for the release gate**: `cuems-editor` and `cuems-frontend` have **no
`debian/` directory**. The editor's absence is a packaging question for wave 4; the frontend's is
structural and is why FR-105's runtime handshake exists at all (R7).

---

## R3 — resumable conversion is already satisfied by construction

**The single largest correction this research makes to a naive reading of the spec.** FR-095c
requires the batch conversion to be resumable: re-running over a partly converted library must
complete the remainder "without re-converting, double-backing-up or corrupting what already
moved". Read as an implementation requirement, that is a substantial piece of new work.

Reading `src/cuemsutils/xml/convert_documents.py` **as landed by 008**, it is already true:

- `convert_file` reads the version marker and returns `CURRENT` when the document is already at its
  schema's version — "left untouched … a second run over an already-converted file changes no
  bytes", stated in its own docstring against 008's SC-018.
- The backup (`<name>.<YYYYMMDDTHHMMSS>.bak`) is written **only on the converting branch**, after
  the version check. An already-current document produces no second backup.
- The converted tree is **validated before it overwrites the original** — the backup is what makes
  that affordable, and a conversion producing a schema-invalid document does not replace a valid
  one.
- `main` attempts every document regardless of an earlier failure and returns non-zero if any was
  skipped — "never partial".

**Decision**: FR-095c becomes a **verification task at library scale**, not an implementation task.
**Rationale**: the property is a consequence of the version marker plus the idempotent guard, both
already tested by 008. **Alternatives considered**: building a resume ledger or a manifest —
rejected as re-implementing what the version marker already is; a ledger could also disagree with
the documents, which the marker cannot.

---

## R4 — the conversion cannot answer "has this been converted?" without converting

Following from R3: every path through `convert_file` that *reports* a version also *acts* on it.
There is no read-only mode, and `main` takes no flags — `usage: cuems-convert-documents <path>...`.

FR-103 requires the rollback boundary to be checkable without inspecting documents by hand, because
the whole post-conversion rollback procedure begins "if you converted".

**Decision**: add a **no-write check mode** to the existing entry point, reporting per-document
versions and a library-level summary. **Rationale**: it is the smallest addition that makes FR-103
performable, it reuses the reporting style the tool already has (Constitution III), and it is not
descriptor capability, so FR-026 does not reach it. **Alternatives considered**:
- A documented `grep` over the version attribute — rejected: that is inspecting documents by hand
  with extra steps, and it silently mis-answers for a document whose root names no bundled schema.
- A separate status command — rejected: two entry points for one question, and the version-reading
  logic would exist twice.
- Inferring from the presence of `.bak` files — rejected: backups are reclaimable (R5), so their
  absence proves nothing.

**Recorded as a scope enlargement** in the plan's Gate result, because it is the third time this
feature grows this repository's share beyond the three obligations Part 6 scoped.

---

## R5 — backup retention is a show cycle, not a duration

FR-102 requires the plan to state how long conversion backups are retained and when they may be
reclaimed. The plan owes a number; the honest answer is that a number is the wrong shape.

**Decision**: backups are retained **indefinitely** — the conversion never reclaims them
automatically. Reclamation is a separate explicit operator action, and the guide's recommended
earliest moment is *after* the post-upgrade verification has passed **and** one full show cycle has
run against the converted library.

**Rationale**: the window in which a defect surfaces in this domain is a rehearsal-to-performance
cycle, not a number of days. A timer that expires before that window makes FR-102's
post-conversion rollback unperformable, and FR-102's whole protection is the backups.
**Alternatives considered**: a fixed 30/90-day window — rejected for the reason above; deleting the
backup once the converted document validates — rejected, since validity is not the property the
rollback needs (a correctly converted document is still the wrong document if the release is
withdrawn).

**Consequence for wave 4**: backups accumulate beside the documents in the project library, so the
conversion at scale has a **disk-space** dimension the verification must record — a library of
hundreds of documents roughly doubles its own size until reclamation.

---

## R6 — the `network_map` performance budget is inherited from a marginal position

The instruction to this plan said "network-map load stays within 007's recorded budget". Checked
against `specs/008-rebuild-extension/baseline.md`:

| | Value |
|---|---|
| Pre-008 baseline | 9.277 ms |
| 007-derived budget | ≤ 10.20 ms |
| 008 post-landing, 3 trials | **10.14–10.49 ms** |
| 008's own recording | "**at the edge**" / "exceeded-or-marginal, not restated as passing" |

**Decision**: this feature measures `network_map` load against **008's post-landing figure**, and
records that it inherits an already-marginal measurement. **Rationale**: restating 007's cap would
charge this feature for 008's deliberate decision (the version probe routes decode through a
pre-parsed tree) and would hide a known-marginal number behind a pass. **Alternatives considered**:
re-deriving a fresh budget from a new baseline — deferred, not rejected: worth doing, but doing it
inside this feature would erase the continuity that makes 008's "at the edge" note legible.

The same discipline applies to show-document load: the reference is **008's 18.673 ms**, not 007's
figure, because 008 added T1+T2 validation to that path.

---

## R7 — the UI is the one consumer packaging cannot gate

`cuems-frontend` has no `debian/` directory (R2). The release gate is expressed in package
relations, so the UI — the surface both of FR-010's payload deltas actually land on — cannot hold
an edge.

**Decision**: a **runtime payload-version handshake** (FR-105–FR-108): the editor advertises a
payload version on connect; a UI that does not understand it refuses and says so.
**Rationale**: it is the only mechanical guard available where packaging cannot reach, and it
catches the one realistic failure a deploy-together convention does not — a cached browser bundle.
**Alternatives considered**:
- Package the frontend so it can hold an edge — rejected for this feature: new packaging for a
  repository that has never had it, inside a feature already spanning seven.
- Rely on "they deploy together" as a stated assumption — rejected: a convention, not a mechanism,
  and the feature's own complaint (C7) is that the gate is prose rather than mechanism.
- Out of scope — rejected: it would leave the surface a user actually looks at outside the gate.

**Design constraint carried into `contracts/`**: this version describes the **editor↔UI message
contract**. It is not the document-version marker, which describes a file on disk and is excluded
from every wire projection (FR-012). Two versions on one link, confused, would be worse than one.

---

## R8 — the descriptor accessor must stay lazy

Constitution IV's budget for wave 0 is "no measurable cost", and the failure mode is specific
rather than general: the internal descriptor path builds **one** schema's descriptor on demand. A
public accessor that eagerly builds all six would put five unnecessary schema constructions on the
path of any consumer wanting one — and feature 005 already measured what that costs
(`coercion._resolve` calling `all_registries()` is the entire 36.3 → 49.6 ms cold delta it
recorded).

**Decision**: the accessor is lazy per schema, and the SC-003 equality test — which must cover all
six — must not be the thing that hides the cost by building all six anyway.
**Rationale**: this is a design constraint expressed as a budget, and the plan says so: eager
construction here is a **design error, not an overrun to accept**. **Alternatives considered**:
building all six once and caching — rejected as the same cost moved, not removed, and it makes the
first consumer pay for five schemas it will never ask about.

---

## R9 — `dev/` exemptions and detection code are two different exemptions

The spec's FR-071/FR-072/FR-073/FR-073a require an enumerated exempt set for the ecosystem-wide
count. Research confirms the two categories have different lifetimes, which is why FR-073a demands
the *reason* be recorded per entry rather than a single flat list:

- **Detection and conversion code** — this repository's sixteen occurrences (counted 2026-09-03:
  `errors.py`, `tools/ConfigBase.py`, `config/network_map.py`, `xml/schemas/network_map.xsd`), plus
  `cuems-common`'s conversion command and its tests. These must contain the retired spelling
  **forever**. A converter that cannot name what it converts is not a converter.
- **Non-shipped scratch code** — `cuems-engine`'s `dev/network_map.xml`,
  `dev/test_xml_files/network_map.xml`, `dev/CuemsEngine_old.py`, and `cuems-nodeconf`'s
  `test_run_nodeconfig.py`. These are exempt because they do not ship, and could be cleaned up at
  any time without consequence.

**Decision**: one exempt list, two stated reasons, never merged. **Rationale**: merging them loses
the distinction, and the next sweep either deletes a working diagnostic or preserves a stale
fixture forever on the strength of the wrong precedent. **Alternatives considered**: a `dev/`
wildcard — rejected by FR-073, which requires the four files named individually; a category label
without per-entry reasons — rejected as the same loss in slower motion.

---

## Open, carried to `/speckit.tasks` rather than resolved here

- **The exact name of the public descriptor accessor.** FR-028 makes it part of the deliverable —
  "the name five other repositories will import for years" — and naming it in a research document
  nobody reviews for naming would be the wrong place to settle it. It is a wave-0 task with the
  contract in `contracts/descriptor-access.md`.
- **Whether `cuems-editor` acquires a `debian/` directory** (R2). It has none, so it holds no
  package edge either; FR-091 counts four edges across the packaged consumers. Wave 4 decides
  whether the editor is packaged elsewhere or is a fifth gap like the frontend's.
