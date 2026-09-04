# Baseline — feature 010, consumer migration

**Measured**: 2026-09-04 · **Branch**: `010-consumer-migration` @ `bcf1509`
**Runner**: `hatch test` under **pyenv 3.11.9** (see the gotcha below)

Every figure here is measured on this branch and dated. Nothing is inherited: the discipline this
rebuild has applied since feature 005 is that a budget derived from someone else's measurement
charges this feature for their decision.

## T001 — suite baseline

```
2573 passed, 96 skipped, 2 xfailed, 213 warnings in 53.33s
```

**= 20.73 ms/test.** Confirms the figure recorded 2026-09-03 at `7a1893f` exactly, so the two
commits landed since (the checklist remediation and the accessor decision, both documentation)
cost nothing measurable.

| Budget | Derived from | Cap |
|---|---|---|
| Suite | 20.73 ms/test | ≤ 110% = **22.80 ms/test** |
| Descriptor publication | per-schema, internal path | ≤ 110% of internal, per schema (FR-PERF-001) |
| Show-document load | **008's** 18.673 ms | no regression |
| `network_map` config load | **008's** 10.14–10.49 ms | see below |

**`network_map` is inherited already-marginal.** 007's cap is ≤ 10.20 ms against a 9.277 ms
baseline; 008 measured 10.14–10.49 ms across three trials and recorded it **exceeded-or-marginal
rather than restated as passing**. This feature measures against 008's figure (FR-PERF-001, research
R6). If wave 0 or wave 5 moves that number, it moves from a position that is already at the edge.

> **Gotcha, recorded because it cost a run.** `hatch` is not on the default `PATH` here — pyenv's
> shim reports "command not found" **and exits 0**, so a background run looks successful and
> produces no totals. Use
> `PATH="$HOME/.pyenv/versions/3.11.9/bin:$PATH" hatch test`. Note also that `hatch test --show`
> (as `CLAUDE.md`'s Build section gives it) prints the environment matrix rather than running the
> suite; `hatch test` runs it.

## T004 — inherited surfaces, confirmed not rebuilt

Spec Assumption 3 claims everything else this feature asks of the library already landed in 007 and
008. Verified once, here, rather than per story:

| Surface | Location | State |
|---|---|---|
| `NetworkMap.partition_by_adoption` | `src/cuemsutils/xml/settings.py:209` | present |
| `cuems-convert-documents` | `src/cuemsutils/xml/convert_documents.py` + `pyproject.toml:48` | present |
| Public report types | `src/cuemsutils/errors.py` `__all__` carries `ConversionRecord`, `LoadReport`, `Outcome`, `RepairRecord` | present |
| Strict load, three outcomes | `errors.Outcome` = `CLEAN`/`CONVERTED`/`REPAIRED`; the fourth outcome **raises** | present |
| `CuemsScript.load_with_report` | `src/cuemsutils/cues/CuemsScript.py:349` (`load` at `:301`) | present |

`Outcome` has three members because D21's third outcome is a **raise**, not an enum member. That is
consistent, and worth recording so a reader does not go looking for `UNREPAIRABLE`.

## T005 — consumer repositories, measured state

| Repository | Branch | HEAD | spec-kit | `tests/` | `debian/` |
|---|---|---|---|---|---|
| `cuems-engine` | `rc_1` | `fc8d2bb` | yes | yes | yes |
| `cuems-editor` | `rc1` | `d9e0a39` | no | yes | **no** — acquired by FR-090a |
| `cuems-common` | `007-node-model-migration` | `78b89ad` | no | yes | yes |
| `cuems-nodeconf` | `feat/xml-refactor` | `7abc01f` | no | yes | yes |
| `cuems-frontend` | `main` | `c69dc1c` | no | **no** | **no** — not packageable, hence FR-105 |
| `cuems-wsclient` | `main` | `f78bea6` | no | **no** | yes |

Five of six have no spec-kit and acquire it on their first run; three are not on `main`; two have no
test directory at all, which is why Constitution II's "each PR carries its own green suite" costs
nothing in them today and why waves 1a and 3 create coverage before changing behaviour.

## T006–T009a — the TDD gate

Five contract tests written **before** any implementation, and confirmed **red**:

| Test | Fails because |
|---|---|
| `test_public_descriptor.py` | `SchemaName` / `get_schema_descriptor` do not exist |
| `test_public_surface.py` | same |
| `test_descriptor_instances.py` | same, plus no constructible instance (FR-022a) |
| `test_descriptor_laziness.py` | same |
| `test_dangling_reference_rule.py` | no repairable rule covers `target`/`action_target` |

**Measured red, 2026-09-04** — the five files alone:

```
14 failed, 5 passed, 26 errors in 0.96s
```

And, critically, **the rest of the suite is untouched**:

```
2573 passed, 96 skipped, 2 xfailed in 56.18s     (the suite with the five excluded)
```

Identical to the baseline above — **zero regressions**. The 2.8 s wall-clock difference against the
53.33 s baseline is run-to-run variance on the same 2573 tests, not a cost this work introduced;
per-test it is 21.84 ms against a 22.80 ms cap.

The 26 "errors" rather than "failures" are fixture errors: the `manager` fixture cannot construct
what does not exist yet. Red either way; they become passes in T010b/T012.

**These tests were restructured once, for a reason worth recording.** Written with module-level
imports of the not-yet-existing `SchemaName`, they produced *collection errors* — and a collection
error **interrupts the whole suite**, so all 2573 unrelated tests stopped running. On a shared
branch that blocks everyone until wave 0 lands. The imports are now deferred to call time, so the
tests are honestly red (failed, not skipped) while the suite still runs.

**One test in the last file passes before and after** — `test_a_reference_that_resolves_is_left_alone`.
That is deliberate: it is the control. A suite that only proved references get cleared would pass
against an implementation that cleared *every* reference.

Two defects were found in these tests while confirming they failed for the right reason, and both
would have produced a green tick against a wrong implementation:

- the cue identifier is `id`, not `uuid` — the control test failed with `KeyError` rather than on
  its assertion;
- matching the new rule **by name** false-positived on the existing `action_target_required`
  (`repairable=False`) and `fade_target_value_range` (whose field is `target_value`). The
  assertion now matches on what a rule **covers** (`applies_to`), which pins the contract without
  constraining T015a's choice of name.

The nested-CueList case **constructs** its fixture rather than skipping when the shared one is flat
(it is: AudioCue, DmxCue, VideoCue, ActionCue, FadeCue). A skip there would have let SC-010a's
recursion requirement disappear the moment the fixture changed.


---

## Wave 0 — measured on landing (T010–T012, 2026-09-04)

| | |
|---|---|
| Suite | **2638 passed, 100 skipped, 2 xfailed in 55.89 s = 21.18 ms/test** (cap 22.80) |
| Remaining red | 4, all `test_dangling_reference_rule.py`, awaiting T015a |
| Descriptor publication | internal **121.4 ms**, public **120.7 ms** across all six schemas — **ratio 0.99**, cap 1.10 |
| Schemas built | **6 either way** — the public path adds none |

**The budget was breached once, during this work, and fixed rather than recorded as accepted.**
The first version of `test_descriptor_laziness` spawned **12 subprocesses** — one per (path,
schema) — each paying ~300 ms to import the library. That pushed the suite to **23.3 ms/test**,
through FR-PERF-001's own 22.80 cap. A performance test that breaks the performance budget is not a
trade worth making, and the freshness it needs is per *process*, not per *case*: two subprocesses
now measure all six schemas each, and the file runs in 1.44 s instead of 7.3 s.

**Two measurement traps found here, both worth knowing before trusting a number in this repository:**

1. **In-process comparison is confounded.** `_repairability_cache` is a module-level global that
   `get_schema.cache_clear()` does not reset, so whichever path ran second measured a warm cache
   and looked ~4× faster. Every figure above comes from a fresh interpreter.
2. **Five of the six per-schema measurements are noise.** The **first** schema touched pays the
   whole ~120 ms global join (008's repairability map spans all six); every subsequent one costs
   0.08–1.0 ms, where a 110% band is microseconds. The ratio is therefore asserted on the **total**,
   with per-schema checks skipped below a 1.0 ms floor — an earlier per-schema version passed alone
   and failed in a loaded suite, which is the signature of measuring the scheduler.


## T015–T017 — the remaining wave-0 measurements (2026-09-04)

**FR-025's "two internal imports" is really one live usage and two dead ones.** Measured across the
whole `cuems-nodeconf` checkout:

| Internal import | Occurrences there | Migration target |
|---|---|---|
| `cuemsutils.xml.settings.NetworkMap` | import + **1 call site** (`CuemsNodeConf.py:567`) | `ConfigManager.load_network_map()` + `.network_map` |
| `cuemsutils.xml.mapper.Mapper` | **import line only** | delete the import |
| `cuemsutils.xml.mapper.read_config_document` | **import line only** | delete the import |

The equivalence is asserted as **equality of result**, not merely that both run: internal reader and
public path return the same 548-byte dict over the same 2-node fixture. A test that only checked
both executed would pass against a public path that read a different file.

**T015a's rule is document-scoped, which the rule machinery could not express.** `_walk` hands a
rule `(value, enclosing_cue)`, and a cue cannot see its siblings, so "does this id resolve" was
undecidable at that signature. `Rule` gains `document_scoped`, and `_iter_t2_findings` collects
every cue id **once** before the reporting walk — per-node collection would be quadratic on a real
show file.
