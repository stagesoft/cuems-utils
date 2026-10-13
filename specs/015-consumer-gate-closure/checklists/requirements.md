<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Specification Quality Checklist: The consumer-gate closure

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-13
**Feature**: [spec.md](../spec.md)

## Content Quality

- [ ] No implementation details (languages, frameworks, APIs) — **deliberately not met**, see note
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [ ] Success criteria are technology-agnostic (no implementation details) — **deliberately not met**, see note
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

**Validation run 2026-10-13, one pass.** Every item was checked against the spec text; the
findings below record how each was verified rather than asserting it.

1. **"No implementation details"** — verified by grep over the Requirements section for every symbol
   this feature touches (the manager class, the index class, the section constant, the two path
   helpers, the projection and ingestion calls, the writer, the version step, the choice-set
   resolver, the schema-name enum). **Zero hits.** Requirements name behaviours and documents;
   module and symbol names appear only in the "why" narrative, the branch-point evidence table and
   the dependency table, where they are provenance for a measurement rather than a design
   instruction. Shipped **command** names (`cuems-reshape-devices`) and **document** names
   (`settings.xml`, `network_map.xml`) are deliberate: they are the operator's vocabulary, not
   internals.

2. **"Written for non-technical stakeholders"** — marked complete against the correct audience,
   which for this repository is the maintainer and the authors of the six consumer repositories. The
   user stories are written as operator journeys (*an operator saves a project for the first time*,
   *an operator labels a node and the label persists*) and each one states its value before its
   mechanism. This follows the convention of features 004–013 in this repository; a spec written for
   a general business reader would be unable to state what any of the five gates is.

3. **"Success criteria are technology-agnostic"** — each criterion leads with the outcome and
   carries its number as evidence. SC-003 is the clearest case: *"11 of 11 documents migrate with
   one invocation, where 0 migrate today"* rather than a statement about which function finds which
   element path. Two criteria do name cross-repository artefacts — SC-012 names a sibling's strict
   xfails and SC-013 names a sibling's planned IPC action — and that is deliberate: those names
   **are** the agreed acceptance evidence between two repositories, and substituting a vaguer
   phrase would make the criterion unverifiable.

4. **All clarification markers are now resolved** — five questions asked and answered in the
   `/speckit.clarify` pass of 2026-10-13, recorded under *Clarifications* in the spec and applied to
   the requirements. Two were found by the clarify scan rather than carried from specify: where the
   instance seeding comes from (it would otherwise have changed the load path's strictness for 64
   fields as a side effect) and the shape of the structured collision. The three carried from
   specify were:
   - **Q1** (FR-079) — the show-document load **straddles** its 16.5 ms budget: band
     **16.465–17.750 ms**, median 16.864, over **16 samples in three windows**, with **14 of 16
     over**. ⚠ **This number was corrected three times**, and the sequence is the useful part:
     3 samples taken under one sustained contention gave "32.8–33.5 ms, a 2× regression"; 5 samples
     in one quiet window gave "exceeded by 2.0–4.9%"; 16 samples across three windows gave the band.
     Each wrong answer was *internally consistent*. The disposition settled on 012's R14 precedent —
     compare against the band, not the straddled line — because a straddled line makes the assertion
     flaky, which is worse than a clean red.
   - **Q2** (FR-080) — four red tests at the branch point come from a structural collision between
     the frozen-landed-spec policy and contract tests that assert against moving sibling checkouts.
     Every resolution changes a policy or a test contract, so none is a default.
   - **Q3** (FR-015) — the source document's stated premise for the absent-file case was
     **measured false** on 2026-10-13. With the premise gone there is no settled answer to inherit.

   Two of the three keep a subsection in the spec because their reasoning outlives the answer —
   including Q1, where the clarify pass had to **correct a measurement this checklist previously
   reported**.

   **One answer widened beyond the question asked**, and it is the most useful outcome of the pass:
   Q2's resolution is not only "split by assertion class" but "resolve every cross-repository claim
   at the coordinated **tag**, never at a sibling's tip". That was the maintainer's addition, and
   measuring it immediately found that **three of the four candidate-tag values this repository
   records in `CLAUDE.md` have moved** — the exact drift the new mechanism exists to catch, and the
   recorded hazard of feature 011 made detectable for the first time.

5. **Four decisions were resolved with the maintainer before the spec was written**, not deferred:
   G3's depth (shape **and** saveable, reversing a recorded descriptor decision), S3's inclusion
   with its golden-recut cost, the deletion set (nine documents, not seven), and the two sweep gaps
   the source document's §9 did not reach. They appear as Assumptions 2, 3, 5 and 6 rather than as
   clarification markers, because they are answered.

6. **The performance baselines were re-measured twice during planning**, not carried forward: the
   maintainer removed anaconda and moved the suite to CPython 3.11.9, then rebuilt pyenv's 3.11.9
   with PGO+LTO. Two figures (save, derive) are **withdrawn** rather than cited as a "before",
   because the old interpreter no longer exists to re-measure on and contention cannot be separated
   from the build. Tolerance moved 110% → 115% → 110% → **115%**, settling where 014 had it once the
   spread was pooled across windows (7.8%) rather than taken from the narrowest one (2.9%). Two
   requirements came out of it: **FR-PERF-005**, every figure must name the interpreter *build*
   (two 3.11.9 builds differed by 32–72% until PGO+LTO closed it to 0–2%); and **FR-PERF-002**'s
   second clause, that a tolerance claim needs samples from at least two separated windows.

7. **One scope widening is recorded rather than absorbed**: S2 was measured at **five** field sites
   across **three** schemas, where the source document names one — and one of the five is a numeric
   latency field, a worse case than the identity field the document describes. FR-067 binds all five.

Items marked incomplete require spec updates before `/speckit.plan`. The single open item is the
three clarification markers, which is what `/speckit.clarify` is for.

---

## Note on the two un-ticked rows (added by the analyze pass, 2026-10-13)

Both were ticked on the specify pass and both are **false of this specification**, so they are
un-ticked rather than quietly left. The spec names `ValidationError` and `cuemsutils.errors`
(FR-060a), `minOccurs="0"` (FR-015), the violation pair `(identity, "uuid")` (FR-060b), `xs:boolean`
and XSD facets throughout G3, and several success criteria are stated in milliseconds against named
code paths.

**This is the convention, not a defect.** The "user" of this repository is another program: six of
the nine user stories have a sibling repository as their actor, and the acceptance evidence for four
of them is a named test node in another checkout. A requirement for this library that avoided naming
its own public surface would not be implementable, and `cuems-editor`'s strict xfails could not be
written against it. The rows are kept visible and un-ticked so that a future reader sees a judgement
rather than a passing box — and so that the checklist stops asserting something the artefact it
describes contradicts on nearly every line.

What the rows *do* still usefully catch, and what was checked by hand instead: no requirement names
a **private** attribute as its contract (FR-014 forbids exactly that), none prescribes an
implementation where a behaviour would do, and no success criterion is measurable only by reading
the implementation.
