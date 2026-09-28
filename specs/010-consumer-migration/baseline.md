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


## Wave 0 close-out — green, and measured (2026-09-07)

| | |
|---|---|
| Suite | **2641 passed, 100 skipped, 2 xfailed, 0 failed** |
| Under coverage | **2641 passed, 0 failed** — see the guard below |
| Coverage, whole project | **91%** (14 875 statements, 2 440 branches) |
| Coverage, `src/cuemsutils` | **85%** |

Wave-0 modules:

| Module | Coverage |
|---|---|
| `xml/spec.py` | **99%** (one missed line, a pre-existing `__str__`) |
| `xml/descriptor.py` | **95%** |
| `xml/validators.py` | **82%** |
| `tools/ConfigManager.py` | **77%** |

**Every miss in those four is pre-existing code, not this feature's.** Checked line by line rather
than inferred from the percentage: `ConfigManager`'s gaps are `get_video_output_id` /
`get_audio_output_id` (572-595, 641-647); `validators`' are `_unwrap_single` and neighbours
(784-808). `SchemaName`, `get_schema_descriptor`, `generate_example`, `_instance_for`,
`_DocumentContext`, `target_resolves` and `action_target_resolves` are all covered.

Three branches of the **new** code were uncovered when first measured, and all three were
behaviours this feature had specified rather than incidental paths — so tests were added rather
than the numbers accepted:

- `generate_example`'s `TypeError` on a bare string (FR-028a applies to both accessors, not just
  the descriptor one);
- `generate_example`'s `NotImplementedError` for a schema with no generator (FR-023's "raises
  rather than returning `None`");
- the reference rules' `context is None` path — no document, no opinion, which is what keeps
  programmatic cue-by-cue construction working.

### The suite could not be run with coverage at all

`tests/test_fade_cue.py::test_fade_cue_construction_performance` asserts 10 000 constructions in
under 2.0 s. Under `--cover` it measured **2.217 s** and failed — a **pre-existing** wall-clock test
that instrumentation invalidates by construction. It is now skipped when a collector is active.

Two details worth keeping:

- **Skipped, not loosened.** Raising the limit to accommodate a traced interpreter would stop it
  detecting the regression it exists for.
- **`"coverage" in sys.modules` is the wrong signal.** `pytest-cov` is an installed dependency, so
  the module is present on every run and that guard skipped the test *permanently* — silently
  retiring it. The check is `coverage.Coverage.current() is not None`: measuring, not merely
  importable.

The 100 skips and 2 xfails were reviewed and are all structural: negative-corpus documents that do
not reach the object layer, fields `Unset` by design, four sub-millisecond perf comparisons below
their noise floor, and 005's two recorded `strict=True` xfails for SC-001's residual type
differences. None is stale.

## T030 — `cuems-nodeconf`'s yardstick, run unchanged (2026-09-17)

**FR-065/SC-008 require 100% of 008's characterization tests to pass against the library's object,
*unedited*.** Both halves are measured here, because "they pass" is worthless if the file moved to
meet the API.

### Unchanged — measured, not asserted

```bash
diff -u cuems-utils/tests/contract/test_nodeindex_characterization.py \
        cuems-nodeconf/specs/planning/yardstick/test_nodeindex_characterization.py
# → no output: byte-identical
```

The vendored yardstick is byte-identical to this repository's copy. `cuems-nodeconf`'s own task
list keeps it out of `testpaths` and runs it as a separate invocation for exactly this reason — so
it cannot be quietly adjusted along with the local tests.

### The run

| | |
|---|---|
| Library under test | `/disk/Projects/StageLab/cuems-utils/src` working tree, `0.1.0rc16`, branch `feat/xml-refactor` @ `d0340fc` |
| Consumer under test | `/disk/Projects/StageLab/cuems-nodeconf` branch `feat/xml-refactor` @ **`8ce7552`** (2026-09-17, pulled from `origin` mid-pass — see the re-run note) |
| Yardstick | **15 passed**, 0 failed |
| `cuems-nodeconf`'s whole suite | **95 passed**, 0 failed |
| Both together, at `8ce7552` | **110 passed**, 0 failed, 26.99 s |

The 95-test run is recorded alongside because SC-008 is about the characterization tests, but a
yardstick that passes while the daemon's own suite fails would be a green light over a broken swap.

**Environment note, stated because it qualifies the result**: `cuems-nodeconf` has no virtualenv on
this machine and its runtime dependencies (`zeroconf`, `netifaces`, `Deprecated`, `timecode`,
`json_fix`) are absent from the system interpreter, so the run used a throwaway 3.11.9 venv with
`PYTHONPATH=/disk/Projects/StageLab/cuems-utils/src`. `python3-dbus` and `python3-systemd` were
**not** installed — the suite's `conftest.py` stubs `systemd.daemon`, and `dbus` is reached only on
paths the tests do not exercise. This is the working tree, not an installed `.deb`; the packaged
combination is T039/T046's subject, not this task's.

### FR-064–FR-068, verified site by site

| FR | Claim | Result |
|---|---|---|
| FR-064 | the ad hoc network-map methods are replaced by calls into the library | **5 deleted, 4 retained as delegating wrappers** — `_map_signature`, `write_network_map`, `merge_discovered_nodes`, `set_master_always_adopted`, `check_missing_adopted_nodes` are gone; `refresh_network_map`, `adopt_node`, `unadopt_node`, `read_network_map` survive as answer-shaping seams. `CuemsNodeConf.py` 756 → 723 lines |
| FR-065 | equivalence measured by 008's characterization tests | **met** — 15/15, file byte-identical |
| FR-066 | the node-modification dispatch migrated, `{'OK': bool, 'error'?: str}` preserved | **met** — `engine_callback` unchanged in shape; the three error strings reconstructed in the wrappers, "already adopted" detected by signature rather than by re-coding the rule |
| FR-067 | the relocated timing helper imported from its current path | **met** — `cuemsutils.tools.TimeoutLoop.TimeoutLoop` at `:25`, three call sites |
| FR-068 | the dead reference in the cleanup path fixed or removed | **met** — `cleanup()` deleted entirely (`8926f49`); `self.cm` no longer appears anywhere in `cuemsnodeconf/` |

### Two findings this gate produced

1. **A third internal import replaced the two it removed.** `CuemsNodeConf.py:21` imports
   `CuemsNetworkMapType` from `cuemsutils.config.network_map`, whose `__all__` is `[]` and whose
   sibling `tools/NodeList.py` docstring says a consumer must never import from it. There is no
   public name for that class; wave 0 published no way to *construct* a network-map document, only
   to load and save one. Recorded in
   [migration-guide.md §4a](migration-guide.md) as **open**; closing it widens this library's public
   surface and is an API decision, not a gate observation.
2. **The import census cannot see finding 1.** It greps deprecated paths, not internal ones, so a
   zero census does not carry the claim "reaches the library through public paths only". T049/T050
   should not be read as covering D34.

### Re-run note — the branch moved during this pass

This gate was first measured at `aab9b48`, where `cuems-nodeconf`'s US2 (Avahi) and US3
(packaging) had **not** landed. `origin/feat/xml-refactor` was then pulled and carried six further
commits through `8ce7552`, landing both. Every number above is the **re-measurement at `8ce7552`**;
FR-064–FR-068 were re-verified site by site at that commit and are unchanged, and the yardstick is
still byte-identical. The first measurement is not preserved here because it described a tree that
no longer exists — this file records the state, not the session.

Two things the re-analysis settled that the first pass had recorded as blocked:

- **T063's `cuems-nodeconf` half is done, by that repository.** `AvahiTool.py:10` and
  `CuemsAvahiListener.py:18` now read "feature 001 (D33)"; the stale "deferred to feature 008"
  comments are gone.
- **US5's cutover has landed on both sides** — see the T023a/T024/T025 sections below.

## T023a / T024 / T025 — the discovery cutover (2026-09-17)

Both owning repositories landed their halves during this pass. **Neither is merged**, each holding
a merge gate on the other (`cuems-common` T019, `cuems-nodeconf` T042) — which is D33 working, not
a delay.

| Repository | Branch @ commit | Feature | Tasks |
|---|---|---|---|
| `cuems-common` | `feat/xml-refactor` @ `1a00159` | `001-node-role-and-conversion-ordering` | 46 done / 2 open |
| `cuems-nodeconf` | `feat/xml-refactor` @ `8ce7552` | `001-network-map-object-adoption` | 45 done / 9 open |

### T023a — the two groups of four, labelled ✅

Recorded in [migration-guide.md §5](migration-guide.md). The discovery four are **counted and
fixed**; the non-shipped four are **exempt**. Neither substitutes for the other.

### T024 — the cutover recorded ✅

Recorded in [migration-guide.md §4b](migration-guide.md), covering the key, the three values, the
two renamed template filenames, every site that resolves a template by name, the publisher, the
consumer's two handling blocks, both copies of the retired translation table, the live file no
package owns, and the packaging entries.

### T025 — **NOT cleared.** Two of its three clauses verified, one not

SC-012 asks for two things. They are recorded separately because only one of them is measurable
from these checkouts.

**(a) No half-renamed combination is shippable — verified mechanically, partially.**

The guard is bidirectional in source:

| Package | Relation | Site |
|---|---|---|
| `cuems-nodeconf` 0.1.0-8 | `Breaks: cuems-common (<< 1.3.0-23~)` | `debian/control:28` |
| `cuems-common` 1.3.0-23 | `Breaks: cuems-nodeconf (<< 0.1.0-8)` | `debian/control:51` |

Arithmetic checked with `dpkg --compare-versions`, not read:

```
cuems-common 1.3.0-22          -> BROKEN (refused)     cuems-nodeconf 0.1.0-7 -> BROKEN (refused)
cuems-common 1.3.0-23~gatedemo1 -> allowed             cuems-nodeconf 0.1.0-8 -> allowed
cuems-common 1.3.0-23           -> allowed             cuems-nodeconf 0.1.0-9 -> allowed
```

The `~` in `1.3.0-23~` is load-bearing and correct: it keeps a prerelease or demo build of
1.3.0-23 satisfying the guard, which is what lets the demonstration below be re-run against a
`+gatedemo` build.

**⚠️ But the observed demonstration predates the guard, and its one gap is the half-rename.**
`cuems-common` has a real, generated refusal record —
`specs/001-node-role-and-conversion-ordering/evidence/out-of-order-refusal.txt`, produced by
`tests/packaging/release-gate-demo.sh` under `mmdebstrap` 1.3.5, seven cases, all matching
expectation. **Case C1 is the half-renamed combination and it was ACCEPTED**:

```
=== C1 — previous cuems-common (un-renamed) together with cuems-nodeconf 0.1.0-8 — the reverse-edge GAP
expected: ACCEPTED
… exit: 0 — observed: ACCEPTED
```

That is not a contradiction of the guard — it is a **timing artifact**, and the timestamps settle
it:

| Event | Time (UTC, 2026-09-17) |
|---|---|
| `cuems-nodeconf` adds the reverse guard (`31da8a7`) | 16:16:25 |
| `cuems-common` generates the demonstration (`4819b11`) | **16:22:12** |
| `cuems-nodeconf` corrects it to `1.3.0-23~` (`8ce7552`) | 16:38:35 |

The demo's `cuems-nodeconf` 0.1.0-8 was an **equivs stub carrying `Depends: cuems-common (>= 1.0.0)`
only** — which its own header states was "as the real package", true when it ran. It is no longer
true. C1 would now be REFUSED by the real package's `Breaks`.

**So the gap is closed in source and open in evidence.** The demonstration must be re-run against a
`cuems-nodeconf` 0.1.0-8 stub carrying the `Breaks:` line before T025 can be cleared. **Not
performable here**: `mmdebstrap` and `equivs-build` are both absent from this machine, and
`cuems-nodeconf`'s own T047 records the same blocker from its side (`dh-virtualenv` absent, no
`cuems-common` `.deb` to install against). This is the same blocker as T039.

**(b) A node published by the migrated publisher is discovered by its migrated listener — NOT
verified end to end.**

What *is* verified is in-process, and it is not the same claim: `cuems-nodeconf`'s suite passes at
`8ce7552` (110 tests including the yardstick), with `tests/test_avahi_listener.py`'s TXT fixtures
rewritten to the new key and `tests/test_service_discovery.py` green. That exercises the listener
against fixtures, not against a publisher over the wire.

The over-the-wire check is `cuems-nodeconf`'s T051 (walk `quickstart.md` §4 with both halves
present, including the deliberate half-renamed check) and `cuems-common`'s T035 (the controller +
node upgrade procedure). **Both are open in their own repositories**, and both need two real hosts.
T025 stays open until they are recorded.

### Vocabulary sweep, measured

`cuems-nodeconf` shipped code (`cuemsnodeconf/`) carries **zero** `node_type` occurrences. The
remainder in that checkout is historical or excluded: `debian/changelog` (release history),
`BUGFIX_COMPLETE.md` / `BUGFIX_NETWORK_MAP.md` / `STARTUP_ANALYSIS.md` (non-shipped notes), and
`specs/` (excluded by its own SC-004 command).

### Finding: the count's denominator is wrong

`cuems-power-bridge` is a **seventh** consumer, shipped, parsing `<node_type>` and filtering on
`"NodeType.slave"` against maps already converted to `<node_role>`. Recorded in full in
[migration-guide.md §5](migration-guide.md), including why it is `cuems-wsclient`'s failure mode
repeating and what it implies for T062's counting method. It is **not** scheduled by this feature.

## Upstream report received, and T025's gap closed (2026-09-17, `cuems-nodeconf` @ `b3f5bb0`)

`cuems-nodeconf` moved again (three commits past `8ce7552`) and now files its findings formally at
`specs/001-network-map-object-adoption/upstream-report.md`. Re-verified here: yardstick still
byte-identical, **110 passed** at `b3f5bb0`, FR-064–FR-068 unchanged.

### T025(b) — no half-renamed combination is shippable: now **OBSERVED**, not computed

The earlier gap is closed. `cuems-nodeconf` generated its own demonstration
(`specs/001-network-map-object-adoption/evidence/out-of-order-refusal.txt`, 2026-09-17T17:19:48Z,
`mmdebstrap` 1.3.5) with **real packages on both sides** — not the equivs stubs whose missing
`Breaks:` produced `cuems-common`'s ACCEPTED case C1:

| Case | Combination | Expected | Observed |
|---|---|---|---|
| N1 | nodeconf 0.1.0-8 + common 1.3.0-22 (un-renamed) | REFUSED | **REFUSED** |
| N2 | common 1.3.0-23 + nodeconf 0.1.0-7 (un-renamed) | REFUSED | **REFUSED** |
| N5 | on a baseline host, upgrade **only** nodeconf | REFUSED | **REFUSED** |
| N6 | on a baseline host, upgrade **only** common | REFUSED | **REFUSED** |
| N7 | upgrade **both** in one `apt-get` call | ACCEPTED | **ACCEPTED** |
| N8 | `dpkg -i` the old nodeconf over the upgraded host | BREAKS-UNCONFIGURED | **as expected** |

N1 and N2 are the two half-renamed directions; N5/N6 are how an operator would actually reach
them. `cuems-common`'s C1 is **superseded**, not contradicted — it measured a stub that lacked the
guard, and said so.

**T025 still does not clear**, on clause (a) alone: the over-the-wire publisher→listener check needs
two hosts. `cuems-nodeconf`'s T050 and T051 are both marked **NOT PERFORMED** for that reason, in
its own file, which is the honest form.

### Three findings reported upstream — into *this* repository

`cuems-nodeconf`'s T049 is discharged as a **report** (its own constitution forbids patching the
library from a consumer branch, since the yardstick's guarantee depends on that file being stable
from that side). All three verified here against `d0340fc`:

| # | Finding | Verified |
|---|---|---|
| 1 | `save_document` leaves the target `0600` | **confirmed by measurement** — see below |
| 2 | `set_controller_always_adopted`'s docstring (`tools/NodeList.py:177`) claims first-run behaviour the method does not have | confirmed, still present |
| 3 | `refresh`'s docstring (`config/network_map.py:156-162`) calls a closed item open | confirmed, still present |

#### Finding 1 is a real permissions defect, and it is this repository's

`src/cuemsutils/xml/documents.py:189-195` writes through `tempfile.mkstemp`, which creates `0600`
by construction, then `os.replace`s it onto the target — carrying the **temporary's** mode, not the
target's. Measured directly:

```
fresh save      : 0o600
after chmod 644 : 0o644
after re-save   : 0o600     <-- the target's mode is discarded
```

**Why it matters, and it is not cosmetic.** `cuems-nodeconf` runs as **root**;
`cuems-controller-engine` and `cuems-node-engine` run as **`User=cuems`**; and `cuems-common` ships
`/etc/cuems/network_map.xml` mode `0644` (`debian/install:204`) precisely so the non-root engine can
read it. The first map write on any node therefore makes the cluster's topology root-only, silently.
That is the same failure shape as the `/tmp/nodeconf.ipc` crash-loop in `cuems-nodeconf`'s CLAUDE.md
— a root process creating something a non-root service must read.

It is **long-standing library behaviour**, not a feature-001 regression: the reporter measured it
through the pre-feature call path verbatim. It affects **every** `save_document` consumer
(`network_map`, `settings`, `project_settings`, `project_mappings`, and `CuemsScript.save`), not
only the node daemon.

Scheduled as **T080–T082**.

## T080–T084 — the upstream findings, closed (2026-09-17)

### T080/T081 — `write_tree` preserves the target's mode

The reporter's own measurement, re-run against the fix:

```
                     before T080      after T080
fresh save             0o600            0o664     (0o666 & ~umask, umask 0o002 here)
existing file 0o644    0o600            0o644
```

**Fixed at the choke point, not per domain.** `src/cuemsutils/xml/documents.py`'s `write_tree` is
the single writer for every document this package produces — all four configuration domains through
`config.base.save_document`, `CuemsScript.save`, and `xml/convert_documents.py` — so one change
covers them all. `_mode_for(target)` stats the target and copies its mode; with no target it falls
back to `0o666 & ~umask`.

**Reading the umask is itself a write**, since `os.umask` only returns the old value by setting a
new one. The probe is `0o077`, not the conventional `0`: if another thread creates a file inside the
window it comes out *more* restrictive than it asked for, never world-writable. This package runs
inside threaded daemons — `cuems-nodeconf`'s resident worker loop among them — so "the window is
short" is not on its own a reason to fail open in it.

**T081 was written failing first**, as the constitution requires: 6 of its 10 assertions failed
against the pre-fix library, 10/10 pass now. The four that passed before are the ones that *should*
have — `0o600` preserved trivially, the umask case (`0o600` is never other-readable), and the two
contracts the fix must not break.

The test file is `tests/contract/test_save_permissions.py`. Three things in it are deliberate:

- the existing-target case is parametrised over `0o644`/`0o664`/`0o600`/`0o640`, so a fix that
  hard-codes the mode `cuems-common` happens to ship **fails** rather than passes;
- `test_every_public_save_path_preserves_the_mode` runs `network_map` *and* `script`, so a fix
  applied inside one domain's `save` would pass the rest of the file and fail there;
- atomicity and non-mutation are re-asserted, including that a **failed** write leaves the target's
  mode alone — a save that fails but still relaxes a mode is a quieter version of the same bug.

| | |
|---|---|
| Suite | **2651 passed**, 100 skipped, 2 xfailed, 0 failed (2641 + the 10 new) |
| `cuems-nodeconf` against the fixed library | **110 passed** — yardstick still byte-identical |

### T082 — the two stale docstrings, corrected

`tools/NodeList.py`'s `set_controller_always_adopted` no longer claims first-run behaviour it does
not have, and now records *why* there is none. `config/network_map.py`'s `refresh` no longer calls
feature 008's "not ported" item open — it is closed, and closed in this library's favour.
Documentation only; the yardstick is unaffected and was re-diffed to confirm.

### T083 — the spelling that caused the misreading

`ConfigManager.load_network_map`'s `netmap.get_dict()` now states what it actually returns, and the
`network_map` setter's annotation no longer contradicts its own getter three lines above. No
behaviour change. Both exist so the next reader reaches the right conclusion without measuring —
which is what neither of the first two readers could do.

### T084 — no public alias, by decision

Recorded in [migration-guide.md §4a](migration-guide.md). FR-025 says *name the existing equivalent
rather than adding a synonym*; `ConfigManager.network_map` **is** the equivalent, so a re-export
would be the synonym FR-025 forbids. The consumer-side migration is prompted at
`specs/planning/xml-rebuild/010-consumer-prompts/04a-cuems-nodeconf-public-path.md`.

## T085–T090 — the second upstream report, closed (2026-09-21)

`cuems-nodeconf`'s feature `002-public-network-map-path`, measured against `cuems-utils` `6fd85fc`
(`0.1.0rc16`), `../cuems-common` `f2fc0f5`, `../cuems-nodeconf` `3e526e1`. Report:
[empty-node-list-report.md](empty-node-list-report.md); checklist
[empty-node-list-tasks.md](empty-node-list-tasks.md); recorded in
[migration-guide.md §4a-ii](migration-guide.md).

### T085/T086 — `get_node` answers `ValueError` for a map with no nodes

The reporter's reproduction, re-run here before and after:

```
                                  before T086                         after T086
empty <node_list/>                TypeError: 'NoneType' ...           ValueError: Node with uuid ... not found
no <node_list> element            TypeError: 'NoneType' ...           ValueError: Node with uuid ... not found
ConfigManager.load_network_map()  TypeError: 'NoneType' ...           ValueError: Node with uuid ... not found
```

**One line, and the trap is why it is that line.** `nodes_list = network_dict.get('node_list') or []`
— *not* `.get('node_list', [])`, which does not fix it: `node_list` is `minOccurs="0"` and an empty
`<node_list/>` decodes to a key that is **present with value `None`**, so the default never fires.
The neighbouring guards at `settings.py:187`/`:236` are safe by their `if not node_list:` check
rather than by their defaults; `config/network_map.py:181` already used `or []`. The message is
unchanged, because `cuems-nodeconf` logs it and pins it (FR-2).

**T085 was written failing first**, as the constitution requires: **5 of its 9 tests failed** against
the pre-fix library, 9/9 pass now. The four that passed before are the ones that should have — the
round-trip, `refresh`, and the two found-case tests — and their passing is the evidence that
`get_node` was the *only* unguarded path, not merely the first one found.

Three things in `tests/contract/test_empty_node_list.py` are deliberate:

- both `minOccurs="0"` shapes are parametrised (empty `<node_list/>` *and* no element at all), so a
  guard that handles one would fail rather than pass half the file;
- the fresh-node boot sequence is a test, not a claim — load the shipped empty map, refill, `save`,
  re-read and find the node — which is what makes the fix *sufficient* rather than merely quieter;
- the found case is asserted both ways (a present uuid still resolves, an absent one still raises),
  so the guard is shown not to have widened anything.

| | |
|---|---|
| Suite | **2660 passed**, 100 skipped, 2 xfailed, 0 failed (2651 + the 9 new) |

### T087 — no sibling path is unguarded, re-measured rather than assumed

All four paths the report names, driven against both shapes after T086:

| Site | Empty `<node_list/>` | Verdict |
|---|---|---|
| `xml/settings.py:159` `get_node` | `ValueError: Node with uuid ... not found` | ✅ **fixed here** |
| `xml/settings.py:187` `get_nodes_by_adoption` | `ValueError: No node list found ...` | ✅ already guarded |
| `xml/settings.py:236` `partition_by_adoption` | `ValueError: No node list found ...` | ✅ already guarded |
| `config/network_map.py:181` `refresh` | `False` (no discovery) / `True` (one node, written) | ✅ already guarded |
| `config/base.py` `save` on an empty document | wrote, no error | ✅ |

The fresh-node sequence completes end to end: empty map → `refresh` with one discovered node →
re-read → the node is found. **No `TypeError` anywhere.**

**One adjacent finding, measured and deliberately not fixed.** A document whose root is *entirely*
empty (`<CuemsNetworkMap/>`, no `node_list` element) decodes to `None`, so `get_dict()` returns a
plain `{}` and `refresh`/`save` raise `AttributeError` on it. That is a decode-layer behaviour
predating this fix — the diff touches only `get_node` — it concerns the whole document rather than
`node_list`, and **nothing ships that shape**: `cuems-common` ships `<node_list/>`. `get_node`
answers it correctly either way. Recorded rather than fixed, because widening it would touch the
decode path for all six schemas, which this report does not license.

### T090 — the release decision: inside `0.1.0rc16`, no bump

`src/cuemsutils/__init__.py` stays at `__version__ = "0.1.0rc16"`, verified unchanged. Sound rather
than convenient: **rc16 has never been released** — this repository's tags stop at `v0.1.0rc14`, it
carries no `debian/` directory, and consumers build the wheel from a checkout. Precedent: the
previous report's `save_document` fix landed inside rc16 the same way (`6fe2d3f`).

Consequences are all absence of work — consumers' pins stay exactly as they are
(`cuems-utils (>= 0.1.0rc16), (<< 0.1.1~)` plus the matching `pyproject.toml` floor, FR-091
satisfied untouched), and **the merge candidate is not re-cut**: `xml-refactor-merge-candidate`
moves only for packaged content, and none changed.

**The caveat, stated because packaging cannot state it**: inside rc16 the version string cannot
distinguish a build made before this fix from one made after — `>= 0.1.0rc16` matches both. So the
discipline is operational: rebuild or reinstall `cuemsutils` from the fixed commit in every
development venv and packaging run, with `tests/contract/test_empty_node_list.py` as the
discriminator. If it fails, the installed build predates the fix.

## Sibling pull and re-review (2026-09-21)

`cuems-common` and `cuems-nodeconf` pulled; `cuems-power-bridge` fetched. Three pending items move,
one of them to closed.

| Repository | Was | Now |
|---|---|---|
| `cuems-common` | `1a00159` | **`11fab0e`**, tag `xml-refactor-merge-candidate` at `f2fc0f5` |
| `cuems-nodeconf` | `a62ff40` | **`be45dda`**, tag `xml-refactor-merge-candidate` at `6c0cca7` |
| `cuems-power-bridge` | `main` @ `c201405` | **`feat/xml-refactor` @ `d7fed47`** |

### T070a — CLOSED

`cuems-power-bridge` now tracks both documents (`d7fed47`), on a feature branch, working tree
clean:

```
specs/planning/cuems-power-bridge-node-role-findings.md
specs/planning/cuems-utils-xml-refactor-consumer-migration.md
```

The findings document was **kept, not consumed** — it is the dated 2026-09-15 primary record and the
vendored bundle cites it, which is what T070a asked for.

### The `CuemsNetworkMapType` internal import — CLOSED by the consumer

`cuems-nodeconf` feature `002-public-network-map-path`, 18/18 tasks, merge candidate `6c0cca7`.
Verified here, not taken on report:

| | |
|---|---|
| `grep -rn "from cuemsutils\.\(xml\|config\)" cuemsnodeconf/` | **no matches** |
| Its suite + yardstick against this working tree | **129 passed**, 0 failed (was 110) |
| Yardstick vs `tests/contract/test_nodeindex_characterization.py` | **byte-identical** |

It took flow 04a's shape exactly, and answered both of the prompt's open decisions explicitly: the
first-run branch took **option A** (`_seed_empty_map()` writes a minimal map with stdlib, then loads
it back through the public path, so nothing constructs a document anywhere), and the test imports
were **kept and labelled** `# test-only (FR-007)`. It then added an anti-regression test the prompt
did not ask for — `tests/test_public_surface.py`, failing any *shipped* module that imports
`cuemsutils.config`/`cuemsutils.xml`, with a guard so a package rename cannot turn it silently
green. Recorded in [migration-guide.md §4a](migration-guide.md).

### T025 clause (b) — now demonstrated independently from **both** sides

`cuems-common` closed its own C1 gap (`f2fc0f5`, 2026-09-18) by rebuilding its stubs from
`cuems-nodeconf`'s **real** `debian/control` at both versions, rather than from the old floors-only
approximation that produced the ACCEPTED reading this baseline recorded on 2026-09-17:

| Case | Direction | Observed |
|---|---|---|
| B1 | renamed `cuems-common` + pre-cutover `cuems-nodeconf` 0.1.0-7 | **REFUSED** |
| C1 | renamed `cuems-nodeconf` 0.1.0-8 + un-renamed `cuems-common` 1.3.0-22 | **REFUSED** |
| E1 / F1 | upgrade only one half of the pair | **REFUSED** both ways |
| D1 / G1 | the matched pre-cutover pair / both halves together | **ACCEPTED** |

Two independent demonstrations now agree — `cuems-nodeconf`'s with real packages on both sides, and
this one with stubs mirroring the real control files. **Clause (a) is still the only thing holding
T025**, and it now has a named home rather than two scattered ones: `cuems-nodeconf`'s
`specs/002-public-network-map-path/checklists/hardware-verification.md` consolidates the hardware
debt of both its features, including feature 001's T050 (the operator chain) and T051 (the
over-the-wire discovery check T025 needs).

### US11 — unchanged, and still the live one

`cuems-power-bridge`'s migration has **not** started: only the docs commit landed. All three sites
still carry the retired vocabulary at `d7fed47`:

```
src/cuemspowerbridge/network_map.py:94   node_type=_text(el, "node_type"),
src/cuemspowerbridge/network_map.py:110  if n.node_type != "NodeType.slave":
src/cuemspowerbridge/network_map.py:141  if n.node_type != "NodeType.slave":
```

T071–T079 remain open. This is now the **only** consumer defect in the ecosystem that is both live
and silent, and both of its broken features (orderly power-off, and the autoload readiness gate)
are still broken.

## Sibling pull and re-review (2026-09-25)

`cuems-common` and `cuems-power-bridge` were **behind their own origins** and are now
fast-forwarded; `cuems-common`'s local candidate tag **disagreed with the published one** and has
been force-updated. Two items above are superseded, one of them completely.

| Repository | Was (2026-09-21) | Now | Note |
|---|---|---|---|
| `cuems-common` | `11fab0e`, tag at `f2fc0f5` | **`3af31cc`**, tag at **`3af31cc`** | 3 commits landed; the tag was **relocated** and force-pushed |
| `cuems-nodeconf` | `be45dda`, tag at `6c0cca7` | unchanged, in sync | — |
| `cuems-power-bridge` | `feat/xml-refactor` @ `d7fed47` | **`13a9af4`**, tag at **`d5c4226`** | 22 commits landed: **features 001 and 002, both complete** |
| `cuems-utils` | — | `b7db53e`, no tag | tags last, by decision |

### ⚠️ "US11 — unchanged, and still the live one" is now FALSE

The section above this one states that `cuems-power-bridge`'s migration *"has **not** started: only the
docs commit landed"*, and quotes three live sites in the retired vocabulary at `d7fed47`. **All three
are gone.** Re-measured 2026-09-25 at `13a9af4`:

```
$ grep -rn 'node_type\|NodeType\.' src/            # cuems-power-bridge
network_map.py:9    "...converts documents written before the ``node_type`` -> ``node_role`` rename."
network_map.py:104  "Deliberately has **no** `node_type` attribute and no string role: ..."
network_map.py:171  _RETIRED_MARKERS = ("node_type", "retired")
network_map.py:244  f"{network_map_path} still uses the retired <node_type> vocabulary ..."
```

Four occurrences, **all four deliberate**: two docstrings, the retired-marker tuple, and the loud
refusal message. The role filter is now `if v.role is NodeRole.node` (`:329`), reached through
`ConfigManager.network_map`, with `NodeRole` imported lazily from `cuemsutils.tools.NodeList` (`:262`).

This is the **option C** outcome T072 scheduled — the private parser deleted, not migrated, replaced by
a thin adapter preserving both field-learned resolution policies. It landed as two spec-kit features
(`specs/001-node-role-parser`, 54/60 tasks; `specs/002-cluster-poweroff-cli`, 69/69) with an evidence
directory each, including `evidence/pre-migration-parser-failure.txt` — the discriminating-fixture run
T073 asked for.

**Consequences for this repository's gate tasks**: T018, T019, T071–T079 are all now *verifiable*
rather than blocked. They are not thereby *done* — each still owes its entry in
`migration-guide.md` or a recorded verification here — but the premise that the consumer side is
outstanding no longer holds, and re-stating it would be the third time this repository's record of
`cuems-power-bridge` lagged the repository itself.

### T076's pin check — partially satisfied, with one gap the task did not anticipate

| File | Required | Measured 2026-09-25 |
|---|---|---|
| `pyproject.toml:38` | non-optional, `>=0.1.0rc16,<0.1.1` | ✅ exactly that, out of `[tool.poetry.extras]`, with a comment recording why |
| `debian/control:18` | floor raised **and bounded** | ◐ `cuems-utils (>= 0.1.0rc16)` — raised, **not bounded**. No `<< 0.1.1~`, no `Breaks:` |

So the source pin expresses the gate and the **packaged** one does not. `cuems-nodeconf`
(`debian/control:18-19`) and `cuems-common` (`:12-13`) both carry the pair. Record this as the bridge's
remaining edge rather than closing T076.

### The two edges still entirely absent

| Repository | `pyproject.toml` | `debian/control` |
|---|---|---|
| `cuems-engine` | `:41` `>=0.1.0rc10` | `:18` `>= 0.1.0rc4` — **and the two disagree with each other** |
| `cuems-editor` | `:27` `>=0.1.0rc10` | **no `debian/` directory at all** |

These are the only two consumers that cannot express the gate. Both are unstarted, and **neither has a
`feat/xml-refactor` branch** — local or remote — as of 2026-09-25:

```
cuems-engine   feat/nodelist-modify-dispatch @ dbc9e6d   (6 commits ahead of rc_1)
cuems-editor   rc1 @ d9e0a39                             (in sync with origin/rc1)
cuems-frontend main @ c69dc1c                            (in sync with origin/main)
```

Planning bundles were vendored into all three on 2026-09-25 under
`specs/planning/xml-refactor/`, following `cuems-nodeconf`'s and `cuems-power-bridge`'s precedent, so
each can run its flow from its own checkout. See §"Consumer flow status" below.

### C2 re-verified live

`cuems-editor`'s import failure is not historical:

```
$ python -c "from cuemsutils.create_script import create_script, new_uuid"
ModuleNotFoundError: No module named 'cuemsutils.create_script'
```

`../cuems-editor/src/cuemseditor/CuemsWsServer.py:24`. Every line number the flow-02 prompt recorded on
2026-09-03 still resolves to the same line — that repository has not changed since 2026-08-03.

### Consumer flow status, 2026-09-25

| Flow | Repository | Feature dir | State |
|---|---|---|---|
| 00 | `cuems-utils` | `010-consumer-migration` | wave 0 landed; waves 4–5 open |
| 01 | `cuems-engine` | `008-cuems-utils-migration` | **not started** — bundle vendored, base branch decided (below) |
| 02 | `cuems-editor` | `001-cuems-utils-migration` | **not started** — bundle vendored; C2 still live |
| 03 | `cuems-common` | `001-node-role-and-conversion-ordering` | **landed**, tag `3af31cc` |
| 04 / 04a / 04b | `cuems-nodeconf` | `001-…`, `002-public-network-map-path` | **landed**, tag `6c0cca7`. Open: hardware verification (001/T050, T051) and the merge-window handshake (001/T042) |
| 05 | `cuems-frontend` | `001-schema-descriptor-migration` | **not started** — bundle vendored |
| 07 | `cuems-power-bridge` | `001-node-role-parser`, `002-cluster-poweroff-cli` | **landed**, tag `d5c4226` |

**Three of six consumer flows have landed.** The three outstanding are the Python show/UI path —
engine, editor, frontend — and they are chained: the editor is gated on this repository's wave 0
(closed), and the frontend on the editor.

### A decision recorded here because it changes flow 01's §1

**`cuems-engine` bases `feat/xml-refactor` on `feat/nodelist-modify-dispatch`, not `rc_1`** (maintainer,
2026-09-25). The flow-01 prompt says `rc_1`, correctly for 2026-09-03. Since then six commits landed
the adopt/un-adopt hop and runtime cluster liveness, and in doing so added a **second**
`get_nodes_by_adoption` call site (`ControllerEngine.py:287`) plus two docstrings constraining when it
may be called (`:272-277`, `:938-943`) — they built *around* the deprecated mutating API this feature
replaces. Branching from `rc_1` would produce work conflicting with exactly that code.

Consequence for T023: the four `BaseEngine.py` sites it names (`:33`, `:410`, `:440`, `:443`) are
**unchanged** and the file is still 636 lines, so that entry needs no correction. Every
`ControllerEngine.py` line number in the flow-01 prompt has moved, and the re-measured table lives in
`../cuems-engine/specs/planning/xml-refactor/03-migration-inventory.md`.

### Two findings against T023's site list, measured rather than inherited

**`find_hosts` has no caller anywhere in the ecosystem**, and it is broken for a second, independent
reason. Swept 2026-09-25 across all seven repositories (`*.py`, `*.ts`, `*.sh`): one hit, its own
definition at `../cuems-engine/src/cuemsengine/core/BaseEngine.py:417`. And it iterates
`get_nodes_by_adoption`'s **wrappers** while calling `node.get("ip")` / `.get("uuid")` /
`.get("node_type")` / `.get("online")` — all four read the `{"node": ...}` wrapper, which holds one key,
so all four are `None`, `hosts` is `[]`, and the method raises `AttributeError("No controller found in
network map")` unconditionally **today**, before any 007 or 008 consideration.

So two of T023's four sites (`:440`, `:443`) are inside an unreachable, already-broken method. Fixing
their vocabulary yields something that still does not work and still has nothing calling it. T023's
verification should require the **decision** (fix-and-wire, or delete) rather than only the comparison.

**`CTimecode(CTimecode(...))` is idempotent** — measured, `CTimecode(CTimecode('00:00:12.500'))` returns
an equal value and does not raise. So the engine's five re-wrapping sites (`run_cue.py:176`, `:430`;
`loop_cue.py:112`, `:276`; `CueHandler.py:166`) are redundant rather than broken, and none is a release
blocker. Recorded so the question is not re-opened as an assumption.

### A sixth consumer of the retired surface, absent from `import-census.md`'s denominator

```
../cuems-editor/tests/test_repair_durations.py:6   from cuemsutils.xml.XmlReaderWriter import XmlReaderWriter
```

The release-gate contract's "known live consumers" list is drawn from `src/` only, so this test import is
outside the required-zero count — and it still breaks when the shims go. `cuems-nodeconf` set the
precedent for exactly this case: keep the test import and **label** it `# test-only (FR-007)`, so a
census can distinguish a shipped consumer from a test deliberately exercising the old path. **T049's
census method should state whether it counts test files**, because right now it neither counts them nor
says it does not.

### A frontend site absent from flow 05's inventory

Flow 05 names one media-duration display site,
`../cuems-frontend/src/app/components/projects/project-show/sequence/sequence.component.ts:194`. There
is a second, in an **Angular template**, which a sweep over `*.ts` cannot find:

```
../cuems-frontend/src/app/components/projects/project-edit/sequence/sequence.component.html:134
    {{ getCueData(cue.originalData)?.Media?.duration || '-' }}
```

Both render `[object Object]` post-008, and **neither fails loudly** — the object is truthy, so the
`|| '-'` fallback never fires. This is an FR-030a-ii instance rendered to an operator. Two further
undercounts in the same file, both measured: `getTemplateOutputStructure` has **three** call sites
(`:1022`, `:1346`, `:1387`), not the one its definition line implies; and the `|| 20` `master_vol`
fallback appears at **`:502` and `:965`** as well as flow 05's `:688`. The value it diverges from is
`100`, a **model-layer** default (`src/cuemsutils/cues/AudioCue.py:9`) with no XSD `default` attribute —
which is the concrete evidence for D25's "defaults are not optional".

All of these are recorded in `../cuems-frontend/specs/planning/xml-refactor/03-migration-inventory.md`.

### An unmerged three-repository feature the consumer flows did not know about (found 2026-09-25)

Found by asking whether `cuems-editor` had a counterpart to `cuems-engine`'s
`feat/nodelist-modify-dispatch`. It does, under a different name, and so does `cuems-nodeconf`. On
**2026-09-04**, fourteen commits landed across **three** repositories as one coordinated feature — the
node adopt/un-adopt hop and cluster liveness. **None of the three branches is merged anywhere.**

| Tier | Repository | Branch | Commits | State |
|---|---|---|---|---|
| UI | `cuems-frontend` | — | **none** | **the tier was never written** |
| middleware | `cuems-editor` | `feat/nodelist-adoption-api` | 5 ahead of `rc1`, 0 behind | pushed; was **not** checked out locally until 2026-09-25 |
| engine | `cuems-engine` | `feat/nodelist-modify-dispatch` | 6 ahead of `rc_1` | pushed, local in sync |
| node daemon | `cuems-nodeconf` | `feat/nodelist-modify-hardening` | 3 ahead, **47 behind**, **not merged** | divergent — below |

The pairings are one-to-one: engine `52962d9 expose runtime cluster liveness to the UI` ↔ editor
`c2eeb80 relay the engine's liveness view as node_status`; engine `cf5c4ad refuse instantly when
nodeconf is not running` ↔ editor `829c56c nodeconf_available was cached and could tell the UI a
comfortable lie`. Engine `8e36d13`'s message names the direction: *"land the adopt/un-adopt hop **the
editor was already calling**"*.

**The chain is Frontend → (WS :9092) → Editor → (NNG, `/tmp/editor.ipc`) → Engine → (NNG) → nodeconf.**
Three tiers built, the UI tier empty:

```
$ grep -rn "nodelist_get\|node_status\|cluster_status\|cluster_warning\|nodeconf_available" \
      ../cuems-frontend/src/
# no matches
```

**Why this matters to this feature rather than being someone else's branch hygiene**, three ways:

1. **It changed a base-branch decision.** `cuems-editor`'s flow now branches from
   `feat/nodelist-adoption-api`, matching the engine decision recorded above. Basing the two halves of one
   feature on opposite sides of it would migrate one and not the other. Every `CuemsWsServer.py` line
   number in the flow-02 prompt moves (563 → 651 lines; `CuemsWsUser.py` 806 → 889), while
   `CuemsDBProject.py` and `repair_durations.py` are untouched — so the prompt is exact for `rc1` and
   wrong for the base, and the bundle now carries both with `rc1` in brackets.
2. **It makes the domain entanglement three-way.** `CuemsWsServer.py:491` and `:537` inject
   `nodeconf_available` into `mappings_dict`, so `initial_mappings` carries `project_mappings`, plus
   `network_map` node status, plus a liveness fact about a **daemon** that belongs to no schema at all.
   FR-047's untangling has three things to separate, not two, and the third has no domain to go to. A
   descriptor-driven `project_mappings` form must not acquire it as a field.
3. **It adds a liveness distinction a descriptor-driven form can silently destroy.** The editor's own
   docstring (`../cuems-editor/src/cuemseditor/CuemsWsUser.py:469-472`) separates each node's `online` —
   `cuems-nodeconf`'s discovery view, refreshed within **~30 s** — from `node_status`'s `alive`, the
   engine's sub-second ping/pong and *"the only signal the GO gate trusts"*. FR-033's retyping of
   `online` to `bool` touches only the first. One "is this node up?" control on the adoption screen
   picks one, probably the staler.

Also: `cluster_status` and `cluster_warning` are **cross-repository contracts**, not internal engine
names — the editor calls the first at `CuemsWsUser.py:496`, `:501` and relays it as `node_status`.
Reshaping either during flow 01 is a coordinated change.

Recorded in all three consumer bundles: `../cuems-editor/specs/planning/xml-refactor/00-runnable-flow.md`
§0a (the cluster map and the base-branch decision),
`../cuems-engine/specs/planning/xml-refactor/04-findings-new-to-this-pass.md` F2a, and
`../cuems-frontend/specs/planning/xml-refactor/03-migration-inventory.md` §4a (the missing tier, as a
**scope decision** for that spec rather than an omission to fill).

#### `cuems-nodeconf`'s third is not in its published candidate — analysed separately

`cuems-nodeconf`'s candidate tag `6c0cca7` does **not** contain the hardening branch, and
`git cherry -v feat/xml-refactor origin/feat/nodelist-modify-hardening` marks all three commits `+` —
no equivalent patch upstream.

**Analysed in full in [`nodeconf-map-write-divergence.md`](nodeconf-map-write-divergence.md)**
(2026-09-25), which measures each of the branch's **four** defects against the current tree rather than
reasoning from commit messages. Summary:

| | Defect | Verdict |
|---|---|---|
| A | `engine_callback` answers only `nodelist_modify` — the engine stalls 15 s | **superseded completely** — ported verbatim as `21c2875` |
| B | two writers share the temp path `f"{map_path}.tmp.{os.getpid()}"` → truncated map, cluster will not boot | **superseded by construction** — the daemon renders no temp file at all now; `write_tree` uses `tempfile.mkstemp`. Measured: 6 distinct temp names over 6 saves. Worst case degrades to last-writer-wins with a **complete, valid** document |
| C1 | an adoption lost between the worker loop and the comms thread | **superseded in effect** — 0 of 60 concurrent trials lose it, because feature 001/002 passes node dicts by reference throughout (`_index_from_document`: *"no copies"*) and `NodeIndex.adopt` mutates in place. Carry a **test**, not a lock: a future defensive copy would reopen it silently |
| C2 | spurious *"Node not found"* in the `set_comms()` → `read_network_map()` window | **OPEN, needs code.** `start()` still calls `set_comms()` before `run()`, and `get_ips()` can hold the window open 10 s. Feature 002 closed the *crash* variant by ordering `self._document` before `self.network_map`; the wrong-answer variant is live — and `cuems-engine`'s `cf5c4ad` makes it answer **confidently wrong** rather than stall, because its readiness probe is the existence of `/tmp/nodeconf.ipc`, which `set_comms()` creates before the window opens |
| D | `CLAUDE.md` says `<online>` is a boot-only snapshot | **OPEN, documentation.** `CLAUDE.md:26` is still false on the candidate: the daemon has been resident since `3e100bb` and `<online>` is a ≤ 30 s-stale discovery proxy. This is the fact both the editor and frontend bundles depend on for the `online`-versus-`alive` distinction |

**Disposition: do not merge the branch; retire it against C1's test, C2's readiness flag and D's
paragraph.** It is 47 commits behind, predates the NodeList refactor, and `21c2875` already recorded
that merging it auto-merges tests into a file whose imports no longer define `CuemsNodeDict`.

**Not acted on from here** — a merge decision in another repository involving another author's work.
Reported because C2's write path is driven by `cuems-engine`'s `nodelist_modify` handler and reached from
`cuems-editor`'s WS action, both of which flows 01 and 02 migrate.

**A correction to this section's own first version**, recorded rather than silently edited: it described
`21c2875` as *"a narrower fix [that] landed in its place"* and the candidate as having *"no guard against
two threads writing the map at once"*, on the strength of a *"22 against 11 lock-related lines"* count.
All three were wrong. `21c2875` is an explicit intent-level cherry-pick that **states** which half it
excludes and why; the hazard the excluded lock guarded no longer exists; and the 11 matches were all
`master.lock`, a file name unrelated to threading — the honest count is **zero** mutexes on
`feat/xml-refactor` against **one `threading.RLock`** on the hardening branch. §0 of the report carries
the correction.

**A note on method, since this is the fourth time a hand-maintained list in this feature was wrong.**
`cuems-wsclient` was absent, `cuems-power-bridge` was absent, the two were counted separately — and now
three branches of one feature were invisible because they carry three different names and two were never
checked out locally. The branch-name convention this work adopted (`feat/xml-refactor` everywhere) exists
precisely to prevent that, and it does not extend to features that predate it. An ecosystem sweep should
enumerate **branches by content**, not by expected name.

### T091 / T092 — the aliasing contract, and the mutation runs that make its test discriminating

**Landed 2026-09-28.** `tests/contract/test_node_aliasing.py` (4 tests, 0.51 s) pins the two links of
the by-reference chain that live in this package, and the four docstrings that previously implied the
property by accident now state it.

**Why an evidence block rather than a "tests pass" line.** Constitution II requires that *"tests fail
before the implementation and pass after it"*. T091 is a test of **existing** behaviour, so it passes
on first run and cannot fail-first in the ordinary sense. Its whole value is that it fails against a
**defensive-copy** implementation — so the fail-first evidence is a set of deliberate source mutations,
each reverted immediately. Asserting the property in a commit message would leave it unverifiable
later; this is the record.

Four mutations, one per link, run against `tests/contract/test_node_aliasing.py`:

```
── mutation: adopt ──          n["adopted"] = True  ->  rebind a dict(n) copy
   FAILED …::test_adopt_mutates_the_node_object_the_caller_holds
   1 failed, 3 passed in 0.56s

── mutation: unadopt ──        n["adopted"] = False ->  rebind a dict(n) copy
   FAILED …::test_unadopt_mutates_the_node_object_the_caller_holds
   1 failed, 3 passed in 0.55s

── mutation: merge ──          existing_by_uuid holds dict(n) instead of n
   FAILED …::test_merge_refreshes_discovery_fields_on_the_callers_objects
   FAILED …::test_refresh_reaches_the_documents_own_node_objects
   2 failed, 2 passed in 0.53s

── mutation: refresh ──        current built from dict(item["node"])
   FAILED …::test_refresh_reaches_the_documents_own_node_objects
   1 failed, 3 passed in 0.57s
```

Each maps to exactly the test written for it. **The `merge` mutation fails two**, which is correct and
worth noting rather than trimming: `CuemsNetworkMapType.refresh` calls `merge`, so a copy introduced
there breaks the document-level guarantee as well as the index-level one. A single-failure expectation
would have been the wrong assertion.

**The identity assertions are the mechanism.** A value-only check
(`index[mac]["adopted"] is True`) **passes** against every one of the four mutations — a
copy-and-replace implementation still ends up with the right value in the index. Only
`aliased is victim` distinguishes them, which is why the tests assert identity and say so in their
own docstrings.

**Coverage gap closed.** An earlier readiness pass mutation-tested three links and reasoned about
`unadopt` rather than measuring it. The run above measures it; the reasoning was right, but it was
reasoning.

**Not a duplicate of existing coverage**, checked before writing:
`tests/contract/test_nodeindex_characterization.py` (203 lines, the vendored yardstick feature 008
wrote and `cuems-nodeconf` runs byte-identical) contains **no** identity, aliasing or in-place
assertion. It characterises *what* `NodeIndex` computes; this file pins *which objects it computes
through*.

**Suite and budget.** 2723 passed / 100 skipped / 2 xfailed in 55.75 s = **20.47 ms/test** — under
Principle IV's 27.27 ms budget and marginally under this feature's own 20.73 ms baseline. Four tests
at 0.51 s total; no measurable effect.

**No `.xsd`, golden or public symbol is touched**, so `test_schema_scope.py`'s hash pin needs no
update and no golden is re-based. `pytest` collects no doctests here (verified: no `doctest`
configuration in `pyproject.toml` or `tests/conftest.py`), and the only test that reads a `__doc__` —
`test_public_descriptor.py:70` — asserts `ConfigManager.get_schema_descriptor`'s is non-empty, which
T092 does not touch.

**What remains on this thread**: T093 pins the consumer's two links (`_index_from_document`,
`_network_map_document`) in `cuems-nodeconf`, and is a gate rather than work here. Until it lands, half
the chain is guarded and half is not — the docstrings added by T092 name the consumer explicitly so
that asymmetry is visible from this side.

### T093 / T097 — the consumer's half, landed in `cuems-nodeconf` (`2e2ae40`, 2026-09-28)

Verified here rather than taken on report, which is this gate's whole job.

| Check | Result |
|---|---|
| `tests/test_node_aliasing.py` exists and pins links 1 and 2 | **yes** — 5 tests, 0.28 s |
| Assertions are on **identity**, not value | **yes** — `index[n['mac']] is n`, `document is nodeconf._document`, `node_list[0]['node'] is n` |
| Written to fail against a defensive copy | **yes**, two mutations below |
| That repository's suite | **119 passed** (was 114), no skips introduced |
| Vendored yardstick unedited | **15/15 passed, byte-identical** to `tests/contract/test_nodeindex_characterization.py` — `diff -q`, not by eye |
| `CLAUDE.md`'s `<online>` cadence corrected | **yes**, and **two** lines were false, not the one T097 named |
| Packaged content touched | **none.** That package ships `include = "cuemsnodeconf"` only |
| Candidate tag `6c0cca7` | **unmoved**, verified after the commit |

**The consumer's two mutation runs**, each reverted:

```
── _index_from_document -> index[node['mac']] = dict(node) ──
   FAILED …::TestTheIndexAliasesTheDocument::test_index_from_document_holds_the_documents_own_node_objects
   1 failed, 4 passed in 0.32s

── _network_map_document -> [{"node": dict(n)} for n in …] ──
   FAILED …::TestTheDocumentIsKeptNotRebuilt::test_node_list_holds_the_indexs_own_node_objects
   FAILED …::TestTheAdoptRaceTheseLinksClose::test_an_adopt_after_the_document_is_built_still_reaches_it
   2 failed, 3 passed in 0.31s
```

**One finding from writing it, which changes how the end-to-end test had to be built.** An earlier draft
adopted *before* the worker loop builds the document. That arrangement **survives a copy at link 2** — the
copy is taken after the flag is set, so it carries it — and therefore proves nothing. The harmful
interleaving is the reverse: the loop builds the document, *then* the comms thread adopts on the index,
*then* the pass serialises. The landed test does that, and the link-2 mutation failing **two** tests rather
than one is the evidence the reordering worked. **A weak ordering would have passed against the very
defect the test exists to catch** — worth recording, because the same trap applies to any test of an
aliasing property.

**C1 is now closed on both sides**: four links, six mutations, two repositories. The asymmetry T092's
docstrings were written to make visible no longer exists — though the docstrings stay, since they explain
why copying is breaking rather than merely that it is tested.

**What this leaves on the thread.** T094 (C2) is the only code item, and its shape is now known rather than
guessed: a readiness flag set at the end of `read_network_map`, guarded in `engine_callback`, ~8 lines, and
**not** a lock — a mutex serialises the two threads without making an empty index any less empty. It needs
a numbered feature in `cuems-nodeconf` because of what it bears on, not because of its size: Principle IV
(*"verified end to end against the real dispatch path"* — *"'it compiles' and 'the unit test passes' are
not evidence that the operator's button still works"*), Principle VI (boot ordering reasoned about
explicitly; *"a change that is correct only when it wins or only when it loses a race is not correct"*),
the testing gate's hardware-verification clause, and an unresolved four-tier decision about what the engine
and the UI should **do** with "not ready" — where retrying contradicts `cuems-engine`'s `cf5c4ad`, which
made refusals instant on purpose. It also changes packaged content, so it re-cuts `6c0cca7` and is
announced to the other flows. That repository's Governance section requires a constitution check in a
feature plan, which is where all four of those belong.

## T094 and T096 — C2 closed in `cuems-nodeconf`, verified 2026-09-28

C2 was the last code item on this thread, and it is no longer this repository's to wait on. It
landed as `cuems-nodeconf` feature **`003-startup-readiness`**, merged to that repository's
`feat/xml-refactor` at **`b305c1c`**, which is also its re-cut `xml-refactor-merge-candidate`
(from `6c0cca7`; tag object `5f0b64a`, signed, pushed). Its own tasks are 47/48 — the one open
item is its maintainer-only T048 (the tag/announce step), not any part of the fix.

**T094 — "not ready", not "not found", and not a lock.** Verified by reading
`../cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py` at `b305c1c`, against the three clauses this
gate was written with:

| Clause | Evidence |
|---|---|
| A readiness flag **set at the end of `read_network_map`** | `:101` `self._ready = False` in `__init__`; `:887` `self._ready = True` is the **last** statement of `read_network_map`, after both `self._document` (`:875`) and `self.network_map` (`:876`) are installed, with a comment naming FR-002 and "anything raised above leaves the daemon not ready, which is the conservative state" |
| `engine_callback` returns a **distinguishable refusal** until then | `:384` `if not self._ready:` → `:393` `{'OK': False, 'error': 'nodeconf is still starting up'}` — inside the existing `{'OK': bool, 'error'?: str}` shape, so the contract with `settings.component.ts` is unchanged; `:390` logs `nodeconf is still starting up; refusing {action} for {uuid}` |
| **A mutex is not the fix** and was not accepted as one | `grep -n '_map_lock' cuemsnodeconf/CuemsNodeConf.py` → no matches. The unmerged `feat/nodelist-modify-hardening` branch is not merged; the flag is the whole mechanism |

**A test exercising the window**, as this task required rather than merely a fix:
`../cuems-nodeconf/tests/test_startup_readiness.py` — 15 tests, including a request arriving
**between** the document and the index being installed, which is the precise interval `b53ee5f`'s
lock would have serialised without emptying it any less. That repository's suite:
**173 passed** (119 baseline + 54 added), no skips, plus **15 passed** on the equivalence gate,
recorded in its `specs/003-startup-readiness/evidence/verification-record.md`.

**T096 — neither consumer compensates.** Measured in that feature's research **R14**, which names
this gate explicitly ("spec Story 4, their T096 gate"), 2026-09-28:

- **`cuems-engine`** at `cf5c4ad` (on `origin/feat/nodelist-modify-dispatch`):
  `git grep -nE 'starting up|retry|retries|not found' cf5c4ad -- src/cuemsengine/ControllerEngine.py`
  → **no matches**. What it carries is `NODECONF_IPC_PATH` (`:23`), the existence probe (`:857`)
  and an explicit `timeout=NODECONF_TIMEOUT_S` (`:867`): one probe, one timeout, **no retry and no
  reading of the error string**. The F2a prohibition in its bundle holds — `cf5c4ad` is not
  deepened, and it is not reverted either.
- **`cuems-editor`**: `grep -nE 'starting up|nodeconf|retry' *.py` → **no matches**. It relays
  whatever the engine answers, which is what §0a of its flow required.

So the four-tier decision resolved to **relay verbatim** (that feature's decision D), and neither
consumer repository needs an edit. The gate is recorded here; the measurement lives there.

**What this leaves.** T095, T098, T099 and T100 are recording tasks in
`migration-guide.md` — no sibling repository is waiting on them. T094's own note above, that C2
"re-cuts `6c0cca7` and is announced to the other flows", is **half done**: the re-cut happened,
the announcement did not reach any other flow. See `specs/011-etc-cuems-first-install/baseline.md`
§"UX pass and announcements" for the counterpart table and the maintainer actions outstanding.
