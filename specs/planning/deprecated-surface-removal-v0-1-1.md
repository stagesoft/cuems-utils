<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# The deprecated surface comes out at `v0.1.1` — migrated out of feature 010

**Status**: **not a feature, not scheduled.** `v0.1.1` is the next stable release and it is
**unplanned**. This document holds the work until it is, so that feature 010 can close on what it
actually delivers.

**Why it exists**: feature 010's **T051–T061** delete the deprecated surface and move
`__version__` to `v0.1.1`. The `feat/xml-refactor` work lands as **`0.1.0rc16`** — the coordinated
`xml-refactor-merge-candidate` tag cuts no stable release. So that block contradicts the versioning
the whole refactor is running under, and §1 shows the contradiction is **mechanical**, not
stylistic.

**Migrated** 2026-10-03 from `specs/010-consumer-migration/tasks.md` Phase 6. Everything was
re-measured against `feat/xml-refactor` at `672c27d` before being moved; §4 lists six things the
original tasks got wrong or under-counted, each of which is a reason to re-enumerate here rather
than carry the block as written.

**What 010 keeps**: the census (its own completion evidence), the ecosystem-wide vocabulary count,
the guide, the budgets and the `xml-rebuild` discharge. See §6.

---

## 1. Two independent reasons the block cannot land at the coordinated tag

### 1.1 Deleting the surface without the version move **defeats the release gate**

Five sibling `debian/control` files carry `cuems-utils (>= 0.1.0rc16)`, `(<< 0.1.1~)` —
`cuems-common`, `cuems-engine`, `cuems-editor`, `cuems-nodeconf`, `cuems-power-bridge`. That bound
exists for exactly one purpose: to stop a library that has **removed** the deprecated surface
installing beside a consumer that still **imports** it.

It expresses that by version number alone. Measured with `dpkg --compare-versions`:

| library version | `>= 0.1.0rc16` | `<< 0.1.1~` | result |
|---|---|---|---|
| `0.1.0rc16` | yes | yes | **installs** |
| **`0.1.0rc17`** | yes | yes | **installs** |
| **`0.1.0rc99`** | yes | yes | **installs** |
| `0.1.1~rc1` | yes | no | refused |
| `0.1.1` | yes | no | refused |

So a library at **any** `0.1.0rcN` with the surface deleted satisfies every consumer bound in the
ecosystem. **Land the deletions under the coordinated tag and the gate becomes ornamental** — it
would admit the one pairing it was built to refuse, and the failure would be an `ImportError` on a
node rather than a refusal at `dpkg` time.

The deletions and the version move are therefore **one indivisible step**, and that step is
`v0.1.1`.

### 1.2 Removing early makes every warning wrong in the *other* direction

`_deprecation.REMOVAL_RELEASE` is `"v0.1.1"` (`src/cuemsutils/_deprecation.py:26`) and every
warning this library emits reads *"use X instead; removed in v0.1.1"* (`:42`). 010's own T060 names
the hazard in one direction — move the version without the deletions and the warnings were wrong.
The reverse holds too: **delete at `rc17` and the surface vanished before the release it was
promised for**, which is the same contract broken from the other side.

Either half alone is a broken promise. Together, at `v0.1.1`, both are kept.

---

## 2. What moved here — twelve tasks

Renumbered **R1–R12** so they cannot be confused with 010's, with 010's original id beside each.
The text is preserved in substance; where §4 found it wrong, the correction is marked **⚠**.

### The gate

- [ ] **R1** *(was T050)* Re-run the import census **immediately before R2**, not once at the close
      of some earlier wave, and update `import-census.md` with its own date and the merge it
      postdates. A repository can regress between merge and removal, and a census dated before that
      commit certifies nothing (010 FR-029, FR-029e, FR-090).
      **Required value: zero.** ⚠ The 2026-10-02 run reached zero over shipped source across all
      six consumers, but **nothing was merged then** — so that run does not satisfy this task. It
      is a *precondition record*, not the gate.

### The deletions

- [ ] **R2** [P] Delete `src/cuemsutils/xml/Settings.py` (010 FR-029a) — blocked by R1
- [ ] **R3** [P] Delete `src/cuemsutils/xml/XmlReaderWriter.py` — blocked by R1
- [ ] **R4** Delete `src/cuemsutils/xml/Parsers.py` — **first** distinguish the retired
      `cuemsutils.xml.CuemsParser` alias from the delegating façade contractually required to stay
      silent; they are two different symbols (010 FR-029d) — blocked by R1
- [ ] **R5** [P] Delete `src/cuemsutils/xml/CMLCuemsConverter.py` — blocked by R1
- [ ] **R6** [P] Delete `src/cuemsutils/timeoutloop.py` — blocked by R1.
      ⚠ Coordinate with `specs/planning/tools-external-consumers-and-timeoutloop-migration.md`,
      which proposes the `TimeoutLoop` relocation; that document is the authority on where the
      replacement lives
- [ ] **R7** Remove the seven aliases at `src/cuemsutils/xml/__init__.py:81-91`, keeping
      `__all__ = []` (010 FR-029a, FR-024) — depends on R2–R6

### The remaining deprecated-symbol sites — **re-enumerated**

- [ ] **R8** Remove **every** remaining deprecated-symbol site. ⚠ **010 enumerated two; there are
      nine, across eight files.** 010's FR-029a says *"every remaining deprecated-symbol site"* and its T057/T058 then
      name two, one of which has drifted. Measured 2026-10-03, outside the five modules R2–R6
      delete:

      | # | Site | Symbol | Deprecated since |
      |---|---|---|---|
      | 1 | `xml/settings.py:208` | `NetworkMap.partition_by_adoption` | **013** — its replacement is `tools.NodeList.partition_by_adoption` |
      | 2 | `xml/XmlBuilder.py:362` | `_FROZEN_BUILDERS`, via `deprecated_symbol(_MIGRATION)` | *(T058's target, still correct)* |
      | 3 | `xml/xml_reader_writer.py:130` | `XmlWriter` | `0.0.7` |
      | 4 | `xml/xml_reader_writer.py:137` | `XmlReader` | `0.0.7` |
      | 5 | `tools/CTimecode.py:204` | `.milliseconds` → `.milliseconds_rounded` | `0.1.0rc6`. **Scheduled here 2026-10-03** — notice normalised, see §7 |
      | 6 | `cues/Cue.py:367` | → `localize_cue` | `0.1.0rc4` |
      | 7 | `cues/AudioCue.py:81` | → `loop_cue` (CueHandler) | `0.0.9rc5` |
      | 8 | `tools/CommunicatorServices.py:155` | `Nng_request_response` → `NngRequestResponse` | `0.1.0rc1` |
      | 9 | `tools/HubServices.py:649` | `Nng_bus_hub` → `NngBusHub` | `0.1.0rc1` |

      ⚠ **T057's `xml/settings.py:170` no longer exists as a deprecation site** — line 170 is
      docstring prose today; features 012 and 013 added content above it and the real site is
      `:208`. Re-measure before deleting; do not trust any line number in this table either.
      ⚠ **This list is not a licence to delete all nine without a census each.** 010's census
      grepped the *five shim module paths*. Items 3–9 are different symbols on different import
      paths and have **never been censused**. R8 therefore carries its own census (§5).

- [ ] **R9** Delete the frozen legacy `src/cuemsutils/xml/XmlBuilder.py` **in full**.
      ⚠ Consolidated here from **feature 013**, whose migration guide records it as having *"no
      live caller, removed in `v0.1.1`"* and as now emitting per-class element names the current
      schema rejects. R8's item 2 removes a *symbol site* in that file; this removes the file. Doing
      both in one release is the only way they do not contradict each other

### The release

- [ ] **R10** *(was T059)* Retire `tests/contract/test_deprecation_shims.py` **deliberately**,
      recording what replaces it and why deleting a contract test alongside the contract it guards
      is correct here (010 FR-029b)
- [ ] **R11** *(was T060)* Move `__version__` in `src/cuemsutils/__init__.py` to
      `_deprecation.REMOVAL_RELEASE` — **and re-bound five sibling packages in the same step**
      (§3). Not a standalone task (010 FR-029c, SC-019)
- [ ] **R12** *(was T061)* Record the post-removal suite time — the suite should be **faster**;
      if it is not, something else changed and must be explained (010 FR-PERF-001's removal clause).
      ⚠ **010 says "22 contract tests retire"; measured 2026-10-03 it is 47**
      (`--collect-only tests/contract/test_deprecation_shims.py`). The figure grew with the shim
      surface and nobody re-measured it. Re-measure again at execution time rather than quoting
      either number

---

## 3. The atomic step — R11 is five repositories, not one file

Migrated from `upcoming-feature-requirements-2026-10-02.md` §3, which is where this was first
recorded. §1.1's table is the proof.

> **The version move and the re-bound of five sibling packages are one step.** A library at `0.1.1`
> beside five packages bounded `<< 0.1.1~` is an ecosystem that will not install at all, and the
> failure surfaces at `dpkg` time on a node.

Each sibling needs the same two lines raised in lockstep (`>= 0.1.1`, `<< 0.2.0~` if the next break
is minor) **plus** its `pyproject.toml` bound — which `dpkg` does not enforce but `pip`/`poetry`
resolves. `cuems-frontend` has no package and uses the payload handshake instead (010 FR-108); the
editor already sends `payload_version: 1` as its first frame, so that half exists.

**Record it in the feature that cuts the release, not only here.** This arc has twice found that a
cross-repository requirement living in one side's task list gets built on one side (010's
FR-UX-002's missing consumer; its T076's upper bound).

---

## 4. Six things found while reviewing, each a reason to re-enumerate rather than carry

| # | Finding | Consequence |
|---|---|---|
| 1 | **The gate is defeated by the deletions alone** (§1.1), measured with `dpkg`. Not recorded anywhere before this document | the block is indivisible and belongs to a release, not to a tag |
| 2 | **`_deprecation.py` survives the deletions.** Six files that R2–R6 do not touch still import it — `cues/Cue.py`, `cues/AudioCue.py`, `tools/CTimecode.py`, `tools/CommunicatorServices.py`, `tools/HubServices.py`, `xml/xml_reader_writer.py`, plus `xml/settings.py` | the module is **not** deleted, and `REMOVAL_RELEASE` stays meaningful for whatever remains after this work |
| 3 | **010 enumerates 2 of 9 symbol sites** (nine sites in eight files) against its own FR-029a wording *"every remaining"* | R8 re-enumerates; the count is the deliverable, not the two names |
| 4 | **T057's line number has drifted** — `xml/settings.py:170` is prose now; the site is `:208`, and it is a **013** deprecation that post-dates 010's task list | re-measure at execution time; the table in R8 is dated, not authoritative |
| 5 | **013 independently scheduled `XmlBuilder.py` for `v0.1.1`** | consolidated as R9, so the file deletion and its symbol site land together instead of in two features |
| 6 | **010's "22 contract tests retire" is now 47**, measured | the saving R12 records is twice what was budgeted; quote the measurement, not the task |

---

## 5. What this document does **not** settle

*(One of the four was settled on 2026-10-03; it is struck rather than removed, because the
reasoning is what makes the answer checkable.)*

1. ~~**Is `v0.1.1` the first stable release?**~~ **Answered 2026-10-03 by normalising the notice
   — see §7.** `CTimecode.milliseconds` no longer makes a promise of its own; it reads
   `REMOVAL_RELEASE` like every other retired symbol, so R8's item 5 is due with the rest and needs
   no split.
2. **Items 3–9 of R8 have never been censused.** 010's census pattern covers
   `cuemsutils.xml.{Settings,XmlReaderWriter,Parsers,CMLCuemsConverter}` and
   `cuemsutils.timeoutloop`. `XmlReader`/`XmlWriter`, `Nng_bus_hub`, `Nng_request_response`,
   `AudioCue`'s loop method, `Cue.localize_cue`'s predecessor and `CTimecode.milliseconds` are
   different symbols on live import paths. **Each needs its own measured zero before deletion**, and
   `CTimecode.milliseconds` is the one most likely to have real callers — it is a convenience
   property on the most-used tool in the library.
3. **Whether this becomes one feature or rides a release feature.** It is a coherent unit (one
   release, one promise kept) but it is small and entirely internal. Either shape is defensible; the
   constitution's requirements apply the same way.
4. **When.** `v0.1.1` is unplanned. This document is the holding place, not a schedule.

---

## 6. What feature 010 keeps, and why

Stated here so the split is reviewable from this side too.

| 010 task | Stays | Why |
|---|---|---|
| **T049** | ✅ | The census **is** 010's completion evidence: the consumers are off the deprecated paths (FR-029). Already run and recorded at zero. What moved is the *deletion it gates*, not the measurement |
| **T062** | ✅ | The ecosystem-wide count of the retired **discovery vocabulary** (`node_type` → `node_role`), FR-070–FR-073a. Nothing to do with the deprecated Python surface or the version |
| **T063** | ✅ | Three stale documents that are 010's own inputs (FR-005) |
| **T064** | ✅ | 010's migration guide — its central deliverable |
| **T065–T068** | ✅ | 010's own budgets, `network_map` load, quickstart and UX pass |
| **T069, T069b, T069c** | ✅ | Promoting `xml-rebuild` material into `specs/agreements/`, the per-document verdict, and the deletion. ⚠ One interaction: T069c's residue list must now **exclude X1** from "deferred debt" — X1 is **feature 014's scope**, not relocated schema debt |

**010's final state after the split**: the coordinated land of the
`xml-refactor-merge-candidate` tag — six consumer flows landed, a measured census of zero, the
ecosystem-wide vocabulary count, the guide, the budgets, and the `xml-rebuild` folder discharged.
The tag now covers features **011–015**. It does **not** cut a version, and it does not remove the
deprecated surface.

### The spec items that move with the tasks

| Item | Disposition |
|---|---|
| **FR-029a** removal covers five modules, aliases, every symbol site | **moves** — and R8 corrects the enumeration |
| **FR-029b** retire the shim contract tests deliberately | **moves** (R10) |
| **FR-029c** version moves to the promised release | **moves** (R11) |
| **FR-029d** distinguish the two parser symbols | **moves** (R4) |
| **FR-029e** census re-run immediately before the deletions | **moves** (R1) |
| **FR-029** removal only after a measured zero | **splits.** The census requirement stays in 010 and is satisfied; the removal it gates moves |
| **SC-018** zero before a deletion, surface gone after | **splits** the same way — 010 keeps the measured zero, the "gone after" half moves |
| **SC-019** version equals the removal release | **moves** entirely |
| **SC-PERF-001**'s clause *"the deprecated-surface removal does not make the suite slower"* | **moves** (R12). Its other clauses stay |
| **US10** *"The deprecated surface comes out and the guide records what moved"* | **splits.** The count and the guide stay as 010's; the removal and the version move here. The story title needs amending either way |
| **FR-090** structural ordering | **stays**, with its far end in another document: the chain is still census → zero → deletions, and the deletions are now out of reach by construction, which is a stronger guarantee than a task ordering |

---

## 7. `CTimecode.milliseconds` joins the uniform notice (2026-10-03)

**Done, in code**, ahead of the rest of this document — because it was a *promise* that disagreed
with the schedule, not a deletion, and leaving it to `v0.1.1` would have left §5's question open
until the release it was blocking.

### What it said, and why that was a problem

```python
@deprecated(
    reason=("Renamed to .milliseconds_rounded (int, rounded) — or use "
            ".milliseconds_exact (float, precise) for precision-sensitive code. "
            "The old .milliseconds will be removed at the first stable release."),
    version="0.1.0rc6",
)
```

Hand-written at the call site, naming **"the first stable release"** — a different date from the one
every other deprecation in this package names, and one **no consumer could act on**, because this
library has never shipped a non-rc version. `_deprecation.py`'s whole premise is that *"fixing that
string once here is what makes FR-027's 'one message format' true by construction rather than by
review across ~20 sites"*; this site was outside that guarantee.

### What it says now

```python
@deprecated_symbol(
    ".milliseconds_rounded",
    note=("the replacement rounds where this truncated, so at fractional "
          "framerates (29.97, 23.976) a value may differ by 1 ms; use "
          ".milliseconds_exact (float) for precision-sensitive code"),
)
```

→ `use .milliseconds_rounded instead; removed in v0.1.1; note: the replacement rounds where this
truncated…`

Three things that change, each deliberate:

- **The release comes from `REMOVAL_RELEASE`**, so this symbol is scheduled with the rest of R8 and
  cannot drift from it again.
- **The rounding caveat moves to `note`** — the parameter `_deprecation.py` documents as existing
  for *"exactly one message (D2a)"*, a replacement whose output differs from the original's in a way
  *"a consumer told only 'use X instead' would find out by comparing payloads in production"*. The
  `int()`-vs-`round()` difference at 29.97 and 23.976 is the same shape, so this is the second user
  of a parameter built for the case rather than a new mechanism.
- **`version="0.1.0rc6"` is dropped from the decorator** and kept in the docstring. It rendered as
  *"Deprecated since version 0.1.0rc6"*, which was correct — but `deprecated_symbol` takes no
  `version`, and passing one only here would make this message the one that differs. The fact is
  worth keeping; a divergent format is not.

`from deprecated import deprecated` goes with it — this was the file's only direct use.

### Tests

Two, in `tests/unit/test_ctimecode.py` beside the existing emission tests:

- `test_milliseconds_warning_uses_the_packages_one_message_format` asserts
  `deprecation_reason(".milliseconds_rounded")` and `REMOVAL_RELEASE` are both in the message, plus
  that the caveat travels as a `note`. **It fails against the old message**, which contained
  neither — which is why it is worth pinning beyond "a warning is emitted", which two existing
  tests already cover.
- `test_milliseconds_removal_release_matches_the_retired_surface` pins `REMOVAL_RELEASE == "v0.1.1"`
  from this side, so a move shows up here rather than in a docstring nobody re-reads.

Suite **3432 passed / 112 skipped / 2 xfailed**.

### One pin moved with it

`tests/contract/test_schema_hygiene.py`'s `_ALLOWED_FRAME_FORM_LOCATIONS` records the exact lines of
`CTimecode.py` where a frame-based timecode may appear in prose. Five of its six entries shifted —
78→79 and 82→83 from the import swap, 242→258 and 438/439→454/455 from the expanded docstring. The
**count is unchanged at six**, so no new frame-based form was introduced, which is what that pin
exists to catch. Updated in the same change, with the reason recorded beside it, on the same
discipline as the schema-hash pin.
