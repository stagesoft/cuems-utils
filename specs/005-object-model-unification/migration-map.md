# Migration map — 005 object model unification

**Feature**: `005-object-model-unification` | **Tasks**: T003 (skeleton), T044 (completion)
**Requirement**: FR-UX-001, FR-019 | **Input to**: feature 008 (consumer migration)
**Baseline**: `79632c3` — see [baseline.md](./baseline.md)

Unlike [004's migration map](../004-xml-serialization-core/migration-map.md), which enumerated
deprecated *symbols* and their consumer call sites, this feature renames nothing and deprecates
nothing. Every entry below is a **behaviour** delta: the same call, on the same symbol, now
returns something different. That is why the form differs — before/after values rather than
old-path/new-path — and why no cross-checkout call-site sweep is repeated here. Consumers are
not edited by this feature (FR-027); feature 008 owns that, informed by this document.

**No file outside this repository is edited by feature 005.**

## Status

One section per behaviour change, filled as each lands (T044). Entries are written for changes
that **actually shipped** — under an MVP-only cut (Phases 1–4) that is changes 1, 2 and 6, and
the remaining four defer alongside their changes rather than being written speculatively.

| # | Finding | Change | Status |
|---|---|---|---|
| 1 | F18 | Loaded objects gain the internal types built objects already had | ☐ not landed |
| 2 | F12 / F19 | Region coercion actually runs | ☐ not landed |
| 3 | F16 | Clearing an identifier clears it | ☐ not landed |
| 4 | F17 | `except AttributeError` narrows to "no such setter" | ☐ not landed |
| 5 | F20 | One defaulting protocol; bare construction yields declared defaults | ☐ not landed |
| 6 | §5.4 Part 2c | The root's `items()` filters to declared fields | ☐ not landed |
| 7 | F4 | DMX-scene swallow-and-continue removed | ☐ not landed |

---

## 1 — F18: loaded objects gain the internal types built objects already had

*(to be completed — T044)*

**Before**:
**After**:
**Consumer-visible consequence**:
**Who is affected**:

---

## 2 — F12 / F19: region coercion actually runs

*(to be completed — T044)*

**Before**:
**After**:
**Consumer-visible consequence**:
**Who is affected**:

---

## 3 — F16: clearing an identifier clears it

*(to be completed — T044)*

**Before**:
**After**:
**Consumer-visible consequence**:
**Who is affected**:

> Carries FR-022's `initial_template` delta measurement, and the **open** CHK032 question: no
> task owns the "confirmed harmless to the UI" step FR-022 requires. Record the measured delta
> here; flag the confirmation as outstanding in the PR.

---

## 4 — F17: `except AttributeError` narrows to "no such setter"

*(to be completed — T044)*

**Before**:
**After**:
**Consumer-visible consequence**:
**Who is affected**:

---

## 5 — F20: one defaulting protocol

*(to be completed — T044)*

**Before**:
**After**:
**Consumer-visible consequence**:
**Who is affected**:

> Cross-reference [defaults-audit.md](./defaults-audit.md) (T036), including the sweep for code
> relying on today's empty bare construction.

---

## 6 — root `items()` filters to declared fields; stray keys dropped and logged

*(to be completed — T044)*

**Before**:
**After**:
**Consumer-visible consequence**:
**Who is affected**:

---

## 7 — F4: DMX-scene swallow-and-continue removed

*(to be completed — T044)*

**Before**:
**After**:
**Consumer-visible consequence**:
**Who is affected**:

---

## Deliberate carry-over — the standing validation asymmetry

*(to be completed — T044; required by FR-006b)*

The same value can be rejected when assigned through a property setter and accepted when
decoded, depending on which construction strategy its type happens to reach. This feature
**leaves that standing on purpose** and neither widens nor narrows it. Recorded here so a later
reader can tell "deliberate" from "overlooked". Resolved by feature 006's recorded decision stop
(`specs/planning/xml-rebuild-06-target-design.md` §9.2).

---

## Fail-then-pass evidence (SC-003)

*(to be completed — T044)*

One row per landed change, so a reviewer confirms all seven rather than trusting a summary. The
"before" half is run at `79632c3`.

| # | Change | Test | Before (at `79632c3`) | After |
|---|---|---|---|---|
| 1 | F18 internal types | `tests/integration/test_construction_parity.py`, `tests/unit/test_decode_internal_types.py` | | |
| 2 | F12/F19 regions | `tests/unit/test_region_coercion.py` | | |
| 3 | F16 id clearing | `tests/unit/test_id_clearing.py` | | |
| 4 | F17 setter swallow | `tests/unit/test_setter_error_propagation.py` | | |
| 5 | F20 defaulting | `tests/unit/test_defaulting_protocol.py` | | |
| 6 | root `items()` / stray keys | `tests/contract/test_stray_keys.py`, `tests/unit/test_items_single_definition.py` | | |
| 7 | F4 DMX failure path | `tests/contract/test_dmx_failure_path.py` | | |
