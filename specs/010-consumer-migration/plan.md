# Implementation Plan: Consumer migration

**Branch**: `010-consumer-migration` | **Date**: 2026-09-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-consumer-migration/spec.md`

## Summary

Seven repositories move onto the public `cuemsutils` API and release together. This repository
carries three obligations of its own (D16): the schema descriptor's public path, the deprecated
surface's removal, and the migration guide. The other six carry the call-site work, and the
cross-repo gates — the ecosystem-wide count, the packaging demonstration, the end-to-end check,
the cluster upgrade and the two rollback drills — live here because they live in no consumer.

The plan follows `xml-rebuild-06-target-design.md` §12, **with §12 read as of its own date**. It
was written 2026-08-24 and two of its rows have been superseded by later decisions the plan
follows instead: its `cuems-frontend` row says "no change required" (superseded by D26/D35 and
C5 — the frontend is the largest single port in this feature), and its repository list omits
`cuems-wsclient` entirely (added by D32/C1). §12's other rows stand unchanged and are the
authority for them.

**Structure**: six gated waves, and the gates are the plan's substance. Wave 0 unblocks two other
repositories; wave 5 cannot start until a *measured* count says six repositories have stopped
importing the deprecated paths. FR-090 requires that ordering be structural rather than advisory,
so §"The gate mechanism" defines how a task list makes an early wave-5 start impossible rather
than merely discouraged.

## Technical Context

**Language/Version**: Python 3.11+ (`cuems-utils`, `cuems-engine`, `cuems-editor`,
`cuems-nodeconf`, `cuems-wsclient`); TypeScript/Angular (`cuems-frontend`); shell + Debian
packaging (`cuems-common`).
**Primary Dependencies**: `cuemsutils` (this library) across five Python consumers; `xmlschema`
3.4.3 pinned; Avahi/mDNS for node discovery; NNG for the message bus; systemd for lifecycle.
**Storage**: XML documents on disk — show documents under `/projects/<project>/script.xml`,
configuration under `/etc/cuems/`. No database schema change; `cuems-editor`'s project DB is
touched only where it stamps ids and dates.
**Testing**: `hatch test` (`cuems-utils`), `pytest` (`cuems-engine`, `cuems-editor`,
`cuems-common`, `cuems-nodeconf`), Karma/Jasmine (`cuems-frontend`), **nothing at all**
(`cuems-wsclient` — it configures pytest in `pyproject.toml` and has no `tests/` directory).
**Target Platform**: Debian bookworm nodes in a stage cluster; one controller plus N nodes; the
shared venv at `/usr/lib/cuems`.
**Project Type**: multi-repository ecosystem migration — one library, five Python consumers, one
Angular UI, one packaging repository.
**Performance Goals**: this repository ≤ budget derived from **20.73 ms/test**; show-document load
no worse than **008's post-landing 18.673 ms**; `network_map` config load no worse than **008's
post-landing 10.14–10.49 ms** (see the Constitution check — this is *not* 007's 10.20 ms cap, and
the difference matters).
**Constraints**: no `.xsd` edits (D3, already relaxed three times by 007/008 and not further here);
the editor→UI payload changes in exactly two enumerated ways and no other (FR-010/FR-011); hard
cutovers with no dual-spelling state for the role rename and the duration change; nothing releases
until every wave lands (D27).
**Scale/Scope**: 7 repositories; ~35 named call sites; a document library of **hundreds** of show
documents per controller (FR-095c); a cluster of one controller and at least one node for the
verification.

**Measured starting state, 2026-09-03** — surveyed rather than inherited:

| Repository | Branch | spec-kit | tests | packaging |
|---|---|---|---|---|
| `cuems-utils` | `010-consumer-migration` (from `feat/xml-refactor`) | yes | `hatch test` | yes |
| `cuems-engine` | `rc_1` | yes | `tests/` | yes |
| `cuems-editor` | `rc1` | no | `tests/` | **no** `debian/` |
| `cuems-common` | `007-node-model-migration` | no | `tests/` | yes |
| `cuems-nodeconf` | `feat/xml-refactor` | no | `tests/` | yes |
| `cuems-frontend` | `main` | no | **no** `tests/` (5 `.spec.ts` in 112 `.ts`) | **no** `debian/` |
| `cuems-wsclient` | `main` | no | **no** `tests/` | yes |

Five of the seven have no spec-kit and acquire it on their first run; three sit on branches that
are not `main`. Every repository branches to `feat/xml-refactor` to match this work.

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design — see "Gate result".*

### I. Code Quality By Default

Every repository's own linting and static checks must pass with no new warnings. Two
repository-specific obligations follow from this feature rather than from the constitution's
general form:

- **`cuemsutils.xml.__all__` stays `[]`** (FR-024). The public accessor added by wave 0 is the
  only new door; the erosion `cuems-nodeconf` demonstrates today (two internal imports, recorded
  by no feature until C4) ends in the same wave that gives it somewhere else to go.
- **FR-021's rationale is a code obligation, not a spec one.** A show-schema descriptor served
  from a configuration object is surprising; the reason lives in the docstring beside it, or the
  next reader files it as a mistake.

### II. Tests As A Release Gate

Each consumer pull request carries its own green suite, and the end-to-end check is the gate. Two
qualifications this feature must not lose:

- **A green suite is not evidence for the FR-030a-ii class.** Those callers keep resolving and
  return the wrong answer; the suite was green while `cuems-wsclient` skipped every node. Every
  caller in that class needs a test that **fails against the pre-migration value** (FR-004,
  SC-007), and the counts of callers found and tests added are stated and equal.
- **Two repositories have no meaningful coverage to gate on.** `cuems-wsclient` has no `tests/`
  directory; `cuems-frontend` has five spec files across 112 sources and none covering the three
  this feature rewrites. "Its own green suite" costs nothing in either today, so wave 1 creates
  `cuems-wsclient`'s first test and wave 3 is *preceded* by characterization tests (D35/FR-084).
- **Equivalence for `cuems-nodeconf` is measured, not argued**: 008's characterization tests,
  ported from that daemon, must pass **unchanged** against the library's object (FR-065).

### III. Consistent User Experience

The migration guide is this feature's UX deliverable (FR-UX-001..004), and its audience is six
other repositories' spec-kit flows plus whoever runs the next ecosystem sweep. Three
user-facing surfaces are new or changed and must follow existing conventions:

- The **repair report** and the **unrepairable-load failure** share one channel and one message
  family (FR-049), because from an operator's side they are one event class differing only in
  whether the load continued.
- The **payload-version refusal** (FR-105) must say what is wrong and what to do, not fail blank.
- The **conversion command** already prints per-document outcomes; wave 4 adds progress at library
  scale rather than inventing a second reporting style.

### IV. Performance Budgets Are Requirements

Baseline for this repository, measured 2026-09-03 on `feat/xml-refactor` @ `7a1893f`:
**2573 passed, 96 skipped, 2 xfailed in 53.34 s = 20.73 ms/test.** Not 008's recorded
22.06 ms/test, and not the 20.8 ms/test measured earlier the same day at `7c5896c` before two
commits landed.

| Budget | Source | Target |
|---|---|---|
| Suite, this repository | 20.73 ms/test | ≤ 110% = **22.80 ms/test** |
| Descriptor publication | new | **no measurable cost** — see the design note below |
| Deprecated-surface removal | 22 contract tests retire | suite should get **faster**; if not, explain |
| Show-document load | **008's post-landing 18.673 ms** | no regression against *that*, not 007's |
| `network_map` config load | **008's post-landing 10.14–10.49 ms** | see the correction below |

**The `network_map` budget is corrected here rather than inherited.** The instruction to this plan
said "network-map load stays within 007's recorded budget". It does not, and has not since 008
landed: 007's cap is ≤ 10.20 ms against a 9.277 ms baseline, and 008 measured 10.14–10.49 ms
across three trials and recorded it as **exceeded-or-marginal rather than restated as passing**,
with the mechanism identified (the version probe routes decode through a pre-parsed tree). This
feature therefore measures against **008's post-landing figure**, and inherits the open item: if
wave 0 or wave 5 moves that number, it moves from a position that is already at the edge. Restating
007's cap would charge this feature for 008's decision and hide a known-marginal measurement.

**Design note (a budget that is a design constraint, not a number).** If the public descriptor
accessor eagerly builds all six descriptors where the internal path built one lazily, that is a
**design error rather than a budget overrun to accept** — it would put five unnecessary schema
builds on the path of any consumer that wanted one. Wave 0's design must preserve laziness, and
the test that proves per-schema equality (SC-003) must not be the thing that hides the cost by
building all six anyway.

### Gate result

**PASS**, with two scope enlargements recorded rather than absorbed — both belong to this
repository and both are stated here so a reviewer can reject them before they are built:

1. **FR-022a's constructible instance per complex type.** New descriptor capability inside a
   feature whose FR-026 otherwise forbids any, sanctioned by the spec's Q2 and recorded as an
   exception (FR-022b). It exists because `getTemplateOutputStructure` needs a nested object, and
   no combination of the five per-field facts supplies one.
2. **A no-write mode on the conversion command** (see "The rollback boundary"). FR-103 requires the
   rollback boundary — "has this library been converted?" — to be checkable without inspecting
   documents by hand, and the tool as it stands can only answer by converting. This is a small flag
   on an existing entry point, **not** descriptor capability, so FR-026 does not reach it; it is
   recorded anyway because it grows this repository's share for a third time.

No constitutional violation requires justification. See Complexity Tracking for the one structural
cost this plan accepts.

## Project Structure

### Documentation (this feature)

```text
specs/010-consumer-migration/
├── plan.md              # This file
├── research.md          # Phase 0 — measured findings and resolved decisions
├── data-model.md        # Phase 1 — the entities crossing repository boundaries
├── contracts/           # Phase 1 — the three contracts this feature defines
│   ├── descriptor-access.md      # ConfigManager's descriptor surface (wave 0)
│   ├── editor-ui-messages.md     # the editor↔UI message family (waves 2, 3)
│   └── release-gate.md           # package edges + the payload-version handshake
├── quickstart.md        # Phase 1 — how to run and verify the migration
├── migration-guide.md   # ITEM 3 — accumulates across the feature (not created here)
├── baseline.md          # measurements (not created here)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output — /speckit.tasks, NOT created by /speckit.plan
```

### Source code

**This repository** — the only tree this plan edits directly:

```text
src/cuemsutils/
├── tools/ConfigManager.py     # wave 0: the public descriptor accessor (FR-020..FR-023)
├── xml/descriptor.py          # wave 0: FR-022a's constructible instance; nothing else changes
├── xml/convert_documents.py   # wave 4: the no-write check mode (FR-103)
├── xml/Settings.py            # wave 5: deleted
├── xml/XmlReaderWriter.py     # wave 5: deleted
├── xml/Parsers.py             # wave 5: deleted
├── xml/CMLCuemsConverter.py   # wave 5: deleted
├── timeoutloop.py             # wave 5: deleted
├── xml/__init__.py            # wave 5: the seven aliases at :81-91 removed; __all__ stays []
├── xml/settings.py            # wave 5: the deprecated_symbol at :170
├── xml/XmlBuilder.py          # wave 5: the deprecated_symbol at :362
└── __init__.py                # wave 5: __version__ → the promised removal release

tests/
├── contract/test_deprecation_shims.py   # wave 5: retired deliberately (FR-029b)
└── (wave 0's per-schema descriptor-equality and instance-validity tests)
```

**The six consumer repositories** are edited in their own checkouts, on `feat/xml-refactor`, each
through its own spec-kit flow (`specs/planning/xml-rebuild/010-consumer-prompts/`). This plan is
their contract, not their task list; see "What this repository's tasks.md contains".

**Structure Decision**: this repository keeps its existing layout — the feature adds one public
accessor, one descriptor fact and one CLI flag, and deletes five modules. No new package, no new
directory. The multi-repository shape is a *coordination* structure, expressed in the waves below
and in `contracts/`, not in a source tree.

## The waves, and why the order is what it is

Six waves. The edges are dependencies, not preferences; where two waves have no edge between them
they run in parallel.

### Wave 0 — the public descriptor path *(this repository; blocks waves 2 and 3)*

`ConfigManager` gains the descriptor accessor for all six schemas, `script` included (FR-020),
with FR-021's reason beside it. `descriptor.py` gains FR-022a's constructible instance per complex
type and nothing else — the five existing facts are published as they are, not recomputed
(FR-027). The example generators become reachable on the same path (FR-023). Each of the two
internal imports `cuems-nodeconf` makes today acquires a **named, tested public equivalent**, and
where one already exists the guide names it rather than the library adding a synonym (FR-025).

*Why first*: the editor cannot serve what it cannot import, and the frontend cannot render forms
from a descriptor with no path. This is the one wave with an outgoing edge to two others.

*Why it is not merely a re-export*: FR-022a. That is the whole reason this is library work.

### Wave 1 — the independent consumer repairs *(four tracks, parallel)*

No wave-1 track depends on wave 0 or on another wave-1 track.

- **1a `cuems-wsclient`** (US1). The private `ElementTree` reader at
  `src/cuemswsclient/network_map.py` is **replaced** by the library's public path — not re-spelled
  (FR-050). Verified 2026-09-03 at the stated lines: the dataclass field carrying
  `# "NodeType.master" | "NodeType.slave" | None` (`:33`), `_text(el, "node_type")` (`:93`) and
  `if n.node_type != "NodeType.slave": continue` (`:108`). The repository's first test comes with
  it and must fail against the old comparison (FR-051). Its optional dependency and Debian floor
  become real and bounded (FR-053).
- **1b `cuems-editor` start-up only** (US2). `CuemsWsServer.py:24` —
  `from cuemsutils.create_script import create_script, new_uuid` — verified present. `new_uuid` is
  re-sourced from `cuemsutils.helpers`, where this repository already imports it at four other
  sites. **This is a wave-1 task, not a consequence of the template cutover**: until it lands,
  nothing else in that repository can be tested at all.
- **1c `cuems-engine`** (US4). `BaseEngine.py:33` `CONTROLLER_NETWORK_FLAG = "NodeType.master"`
  and its two comparisons at `:410` and `:440`, plus the `online == "True"` string comparison at
  `:443` — all four verified at those lines. `:509`'s `XmlReaderWriter` + `:510`'s
  `read_to_objects()` become `CuemsScript.load`. `NetworkMap.partition_by_adoption` replaces the
  inline workaround for the mutating accessor. The unreachable fade handlers, their dispatch
  entries and supported-action members go (008 FR-053b). `CuemsDeploy`'s `script.xml` distribution
  is a **rollout-ordering input to wave 4, not a code change here** (C11/FR-036).
- **1d the Avahi cutover** (US5) — `cuems-common` **and** `cuems-nodeconf` together. One cutover,
  two repositories, merged simultaneously (D33): the TXT key, the three service templates in each
  repository, the two template **filenames**, the `debian/install` entries that place them, the
  publisher, the listener's two blocks, and `_AVAHI_NODE_TYPE_TO_ROLE`, which retires with them.
  The stale "deferred to feature 008" comments are corrected here (FR-005/C9).

*Why 1d is one track and not two*: a listener reading the new key against a publisher writing the
old one discovers nothing, and discovery failure is how a cluster loses its topology. There is no
valid intermediate state to merge into.

### Wave 2 — the editor and the node daemon *(gated on waves 0 and 1)*

- **2a `cuems-editor`** (US6), gated on 1b and wave 0. All five `CuemsParser` sites —
  `CuemsDBProject.py` `update`:356, `new`:489, `duplicate`:571,
  `update_projects_existed_media`:808, plus `repair_durations.py`:230 — move to the public show
  object (FR-041). `load()` returns `to_wire()`, subject to FR-010's two-delta constraint. The
  raw-dict pre-parse fixups are checked **against the library's repair path first** and then become
  sanctioned pre-validation steps or object-level operations — never dict pokes ahead of a strict
  parse, and never a duplicate of a repair the library now performs (FR-043). The node field list
  at `CuemsWsServer.py:425` and the `reload_network_map_nodes` reads take the typed values
  (FR-046). The WS message family arrives: descriptor serving, config-domain saves, the repair
  report, the unrepairable-load failure and the payload-version handshake
  (FR-047/FR-048/FR-049/FR-105) — all of it *generalising* the existing `initial_mappings` +
  `nodelist_modify` pair rather than inventing an unrelated one.
- **2b `cuems-nodeconf` network-map object** (US7), gated on wave 0. The six ad hoc methods swap
  for the library's object, with 008's characterization tests passing **unchanged** as the
  yardstick (FR-065). `engine_callback`'s dispatch is the caller to migrate against, and
  `cuems-frontend`'s settings screen is the UI at the far end that must keep working. The
  `Timeoutloop` import at `:26` (used at `:309`, `:617`, `:629`) moves off the warning shim; the
  two internal `cuemsutils.xml` imports at `:22-23` — verified present — move onto wave 0's public
  equivalents; the dead `self.cm` in `cleanup()` is fixed or removed. The node model itself is
  **confirmed, not redone** (FR-069), and the daemon's other nine responsibilities stay out of
  scope (D23).

### Wave 3 — the UI *(gated on waves 0 and 2)*

**Characterization tests first** (D35/FR-084), covering the adopt/unadopt cycle, the five template
reads including `getTemplateOutputStructure`, and the stored-template round trip. Then the port:
the template-cloning surface across four files onto the descriptor, with the three value-reading
sites onto declared values — `master_vol` (whose `|| 20` fallback already disagrees with the
schema's `100`), `dmx_channels`, and `getTemplateOutputStructure` onto FR-022a's instance. The
media-duration display unwraps the way the fade path already does. The configuration screens are
**ported with their logic preserved**, the network-map-inside-mappings entanglement is untangled,
and the unread required `schemaLocation` field goes.

*Why last among the code waves*: it consumes wave 0's descriptor through wave 2's WS surface, so
it is the only wave with two incoming edges.

### Wave 4 — rollout, the gate and the data migration *(gated on waves 0–3 merged)*

The four missing package edges, the reconciled engine floors, and 007's deferred mechanical
demonstration — **run**, not described (FR-091..FR-093). The two ordering decisions
(FR-094 configuration conversion vs. service restart; FR-095/FR-096 show conversion and the deploy
path). The conversion at library scale. Both rollback drills. The cluster upgrade.

### Wave 5 — removal and the guide *(gated on a measured zero, not on "waves 0–4 merged")*

The deprecated surface comes out and `__version__` moves to the release every warning since
feature 006 has promised. The guide is finished. **This wave's gate is the subject of the next
section.**

## The gate mechanism (FR-090)

FR-090 requires the ordering to be *structural rather than advisory*: a task list that permits
wave 5 to start early is one that can break six repositories at once, and that possibility should
not exist in the file rather than being avoided by care.

The mechanism is a **measured precondition artifact**, not a note:

1. A wave-5 task runs a count of live imports of every deprecated path across all six consumer
   checkouts on disk and writes the result to `specs/010-consumer-migration/import-census.md` —
   per repository, per path, with the command that produced it.
2. Every deletion task declares that artifact as its input and states the required value: **zero**.
3. The census is re-run immediately before the deletions, not once at wave 4's close. A repository
   can regress between merge and removal.

**"The consumer flows are merged" is a different claim from "the imports are gone", and the
difference is a broken daemon.** The measured surface, verified 2026-09-03:

| Deprecated path | Known live consumers today |
|---|---|
| `cuemsutils.xml.XmlReaderWriter` | `cuems-engine` `BaseEngine.py:17`; `cuems-editor` `CuemsDBProject.py:10`, `repair_durations.py:40` |
| `cuemsutils.xml.Settings.NetworkMap` / `cuemsutils.xml.NetworkMap` | `cuems-engine` `ControllerEngine.py:12`; `cuems-editor` `CuemsWsServer.py:23` |
| `cuemsutils.xml.Parsers.CuemsParser` | `cuems-editor` `CuemsDBProject.py:9`, `repair_durations.py:39` |
| `cuemsutils.timeoutloop.Timeoutloop` | `cuems-nodeconf` `CuemsNodeConf.py:26` |

`tests/contract/test_deprecation_shims.py`'s own docstring names twelve call sites. **Those twelve
are the gate.** Two cautions for the deletion tasks:

- **`CuemsParser` is two different symbols.** The `cuemsutils.xml.CuemsParser` *alias* is one of
  006's six retirements; the delegating façade is contractually required to stay **silent** under
  contract C8. Check which is which before deleting either (FR-029d).
- **Retiring the 22 contract tests is deliberate** (FR-029b). They pin the contract this wave ends.
  Deleting a contract test as a side effect of deleting the contract it guards is correct here, and
  reads as coverage quietly vanishing unless the guide says so.

## Three cutover classes, kept apart

The instruction to keep these apart is load-bearing, because one of the three admits a
release-first strategy and two do not.

| Class | Dual state possible? | Consequence for the plan |
|---|---|---|
| **007's role rename** | **No.** No release accepts both spellings. | Hard cutover. "The library releases first with both APIs live" does not apply. Wave 1d and 1a/1c ship with the release, not before it. |
| **008's duration type/wire change and load strictness** | **No.** A document is one shape or the other; a read is strict or it is not. | Hard cutover, plus a **data** migration the other two do not have. Wave 4 owns it. |
| **006's show-API deprecations** | **Yes.** All six retired entry points still resolve and warn at `0.1.0rc15`. | This is the only class where the library can lead and consumers follow, and it is exactly what wave 5 closes. |

Collapsing them into one "the library releases first" story would be wrong for two of the three,
and collapsing them into one "hard cutover" story would make wave 5's staged removal look
impossible when it is the plan's one piece of slack.

## Data migration and rollout (FR-095..FR-096, FR-100..FR-104)

007 converted one configuration file per node. 008's duration change converts **every show document
in every library**, and C11 makes a controller's conversion a cluster-wide event because
`CuemsDeploy` rsyncs `script.xml` to every node it deploys to.

**Trigger**: an explicit operator command (spec Q3/FR-095). Not `postinst`, not first boot. The
configuration-document conversion stays in the upgrade path; the two are separate decisions with
separate answers (FR-095b).

**Resumability is already satisfied by construction, and this plan verifies rather than builds
it.** Reading `xml/convert_documents.py` as landed: `convert_file` returns `CURRENT` for a document
already at its schema's version and touches no bytes; the backup is written **only** on the
converting branch; the converted tree is validated *before* it overwrites the original; and `main`
attempts every document regardless of an earlier failure, returning non-zero if any was skipped.
So re-running over a partly converted library completes the remainder, double-backs-up nothing and
corrupts nothing. FR-095c is therefore a **verification task at scale**, not an implementation task
— which is the single largest correction this plan makes to the naive reading of FR-095c.

**What an operator sees**: the tool already prints a per-document outcome
(`converted` / `already current` / `skipped (reason)`). Wave 4 adds progress at library scale in
that same style rather than a second reporting idiom (Constitution III).

**Backups**: written beside the document as `<name>.<YYYYMMDDTHHMMSS>.bak`.

**Retention (FR-102 — the number this plan owes)**: backups are retained **indefinitely; the
conversion never reclaims them automatically.** Reclamation is a separate, explicit operator
action, and the guide's recommended earliest moment is after the post-upgrade verification has
passed *and* one full show cycle has run on the converted library. An automatic retention window
was rejected: the window in which a defect surfaces here is a rehearsal-to-performance cycle, not a
number of days, and a timer that expires before it makes FR-102's rollback unperformable.

**The rollback boundary (FR-103)**: "has this library been converted?" must be answerable without
inspecting documents by hand. The tool as landed can only answer by converting, so wave 4 adds a
**no-write check mode** that reports per-document versions and a library-level summary. Recorded in
the Gate result as a third enlargement of this repository's share.

**Ordering constraints, all three named together** so none is discovered at show-load time:

1. Configuration conversion vs. `dh_installsystemd`'s service restart, both in `postinst` — 007
   deferred this here because the services doing the reading are the ones this feature migrates.
2. Controller vs. node upgrade order. **Nodes first is safe**, because the library converts older
   documents in memory on read. Controller-first with un-upgraded nodes still receiving deployments
   is the dangerous combination.
3. A converted controller deploying to an un-upgraded node — fails at **show-load time, not upgrade
   time**, and no package manager mediates it. Q3's operator-triggered conversion narrows this
   without removing it: the dangerous moment becomes one the operator chooses.

## What this repository's `tasks.md` contains

Seven repositories produce seven task lists and no single view of the whole. This plan settles what
belongs in *this* one, so `/speckit.tasks` does not either re-issue six repositories' work or drop
the coordination that lives in none of them:

**In scope for this `tasks.md`**: wave 0 in full; wave 4's cross-repo gates (the package edges, the
mechanical demonstration, the conversion at scale, both rollback drills, the cluster upgrade, the
end-to-end check); wave 5 in full including the import census; the ecosystem-wide count with its
enumerated exempt set; the three stale-document corrections (FR-005); and the migration guide.

**Out of scope for this `tasks.md`**: the per-call-site edits in the six consumer repositories.
Each runs its own flow from `010-consumer-prompts/`. They appear here only as **gate references**
— named preconditions of waves 2–5 — never as duplicated tasks. Duplicating them would create two
task lists that drift, and the one in the wrong repository would win arguments it should lose.

**The cross-repo edges live nowhere else**, which is the one remaining reason to use
`speckit.taskstoissues`: wave 0 before waves 2 and 3, waves 1d's two repositories merging together,
and the release gate spanning all seven. Not for re-issuing work each repository already tracks.

## Requirement traceability

All 107 functional requirements, mapped to the wave that discharges them. `/speckit.tasks` covers
the **bold** rows; the rest are gate references to consumer flows (see "What this repository's
`tasks.md` contains"). A requirement in no row is a planning defect, so this table is exhaustive by
construction rather than by sampling.

| Wave / track | Requirements |
|---|---|
| **0 — public descriptor path** | FR-020, FR-021, FR-022, FR-022a, FR-022b, FR-023, FR-024, FR-025, FR-026, FR-027, FR-028 |
| 1a — `cuems-wsclient` | FR-050, FR-051, FR-052, FR-053 |
| 1b — `cuems-editor` start-up | FR-040 |
| 1c — `cuems-engine` | FR-030, FR-031, FR-032, FR-033, FR-034, FR-035 |
| 1d — Avahi cutover (both repos) | FR-060, FR-061, FR-062, FR-063 |
| 2a — `cuems-editor` | FR-010, FR-011, FR-012, FR-013, FR-041, FR-042, FR-043, FR-044, FR-045, FR-046, FR-047, FR-048, FR-048a, FR-048b, FR-048c, FR-049, FR-049a, FR-049b, FR-049c, FR-105, FR-106, FR-107 |
| 2b — `cuems-nodeconf` | FR-064, FR-065, FR-066, FR-067, FR-068, FR-069 |
| 3 — `cuems-frontend` | FR-084, FR-085, FR-086, FR-087, FR-088, FR-088a, FR-088b, FR-088c, FR-088d, FR-088e, FR-105 (UI half), FR-108 |
| **4 — rollout, gate, data migration** | FR-036, FR-091, FR-092, FR-093, FR-094, FR-095, FR-095a, FR-095b, FR-095c, FR-095d, FR-096, FR-097, FR-100, FR-101, FR-102, FR-103, FR-104 |
| **5 — removal and the guide** | FR-029, FR-029a, FR-029b, FR-029c, FR-029d, FR-070, FR-071, FR-072, FR-073, FR-073a, FR-UX-001, FR-UX-002, FR-UX-003, FR-UX-004 |
| **Spanning (every wave)** | FR-001, FR-002, FR-003, FR-004, FR-005, FR-080, FR-081, FR-082, FR-083, FR-090, FR-PERF-001 |

**Notes on the rows that are not a single wave's work:**

- **FR-004 and FR-080–FR-083 are verification obligations, not edits.** Each caller in the
  "keeps resolving but becomes wrong" class needs a test that fails against the pre-migration
  value, and each of 008's consumer-impacting changes is checked against every live call site its
  guide named. They attach to whichever wave touches the site, and their *counting* is wave 5's.
- **FR-036 is a wave-1c finding discharged in wave 4.** The engine's deploy path is a
  rollout-ordering input, not a code change.
- **FR-090 is discharged by the gate mechanism, not by a task.** It is a property of the task list
  itself; see "The gate mechanism".
- **FR-105 appears in two waves** because a handshake has two ends. The editor advertises (2a); the
  UI verifies and refuses (3). Neither half alone is the requirement.
- **FR-002 and FR-005 are why the guide accumulates** rather than being written at the end: every
  consumer-repo modification must be described here, and the three stale input documents are
  corrected as the work that invalidates them lands.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| A configuration-domain object serves the **show** schema's descriptor (FR-020/FR-021) | One public path for one mechanism, reachable by the component that already serves both configuration forms and the show template | Two public paths — a config accessor and a separate show accessor — doubles the surface consumers must learn and version, for a distinction that exists only inside this library |
| The library grows a **sixth** descriptor fact (FR-022a) inside a feature whose FR-026 forbids growth | `getTemplateOutputStructure` needs a nested object; no combination of per-field facts supplies one | A hand-authored seed in the UI leaves a hand-maintained shape that drifts from the schema — the exact failure the template cutover exists to end. Cloning a generated example works only while the example happens to contain one of every cue type |
| A **runtime payload-version handshake** duplicates, at runtime, what packaging does for the other consumers (FR-105/FR-108) | `cuems-frontend` has no `debian/` directory and therefore cannot hold a release-gate edge, yet it is the surface both payload deltas land on | "They deploy together" is a convention, not a mechanism, and it does not cover a cached browser bundle — the one way a UI can actually lag an editor that serves it |
| A **third** enlargement of this repository's share: a no-write mode on the conversion command | FR-103's rollback boundary must be checkable without hand-inspecting documents | The tool as landed can only answer "is this converted?" by converting, which is not a check. A documented `grep` over `doc_version` is inspecting documents by hand with extra steps |
