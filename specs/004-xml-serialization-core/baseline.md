# Pre-refactor baseline

**Feature**: `004-xml-serialization-core` | **Captured**: 2026-08-11 | **Task**: T001
**Commit**: `6a118c8` (branch `004-xml-serialization-core`, `src/` unmodified)

This file is the arbiter for SC-PERF-001. It is captured **before any code moves**, because
after the D9 rename there is nothing left to compare against. Nothing here is re-measured
later except to compare against it.

---

## Measurement environment

Fixed, and recorded because SC-PERF-001 compares best-of-5 to best-of-5 on **one** machine
and interpreter. A number measured elsewhere is not comparable to these.

| | |
|---|---|
| Machine | AMD Ryzen 5 3600 6-Core |
| OS | Linux 6.12.74+deb13+1-amd64 x86_64 |
| Interpreter | **pyenv 3.11.9** (`/home/adria/.pyenv/versions/3.11.9/bin/python`) — conda is not used for this project |
| pytest | 9.0.1, pluggy 1.6.0 |
| `xmlschema` | 3.4.3 (pinned) |
| `lxml` | 6.1.0 (not in the write path) |
| Method | best-of-5 runs; best-of-5 is compared against best-of-5 |

Reproduce with:

```bash
export PYENV_VERSION=3.11.9
for i in 1 2 3 4 5; do pyenv exec python -m pytest tests/ -q | tail -1; done
```

---

## 1. Suite baseline

```
561 passed in 19.68s
561 passed in 19.74s
561 passed in 19.80s
561 passed in 19.89s
561 passed in 19.75s
```

| Metric | Value |
|---|---|
| Tests collected | **561** |
| Passed | **561** (0 failed, 0 skipped, 0 xfail) |
| Wall time, best-of-5 | **19.68 s** |

**561, not the 557 quoted in `plan.md` and `quickstart.md`.** Four tests were added between
the audit and this capture. `tasks.md`'s gate is "≥557 passing", which 561 satisfies; **561
is the number this feature is measured against** from here on.

### 1.1 The 12-second outlier, and where "~7.4 s" comes from

`tests/test_signalengine.py::test_daemon_run_stops_after_signal` takes **12.30 s** on its
own — it is a `sleep`-bound systemd-lifecycle test, not XML work, and it dominates the
total while being completely insensitive to anything this feature changes.

```
560 passed, 1 deselected in 7.33s
560 passed, 1 deselected in 7.40s
560 passed, 1 deselected in 7.39s
```

| Metric | Value |
|---|---|
| Wall time without that one test, best-of-5 | **7.33 s** |

This is the ~7.4 s figure the plan cites. Both numbers are recorded because the 10% rule is
easier to breach — and easier to read — against 7.33 s than against a total four fifths of
which is one `sleep`.

### 1.2 The pre-existing test ids

All 561 ids are recorded in [`baseline-test-ids.txt`](./baseline-test-ids.txt), **in
collection order**. This is the subset SC-PERF-001's 10% rule binds. After the suite grows
(SC-TEST-002 requires it to), re-run exactly this subset and time it on its own:

```bash
export PYENV_VERSION=3.11.9
tr '\n' '\0' < specs/004-xml-serialization-core/baseline-test-ids.txt \
  | xargs -0 pyenv exec python -m pytest -q
```

Measured this way: **561 passed in 19.72 s** (best of 5) — within noise of the 19.68 s
full-suite baseline, as expected, since the subset *is* the suite at this commit.

Two details in that command line are not incidental:

* **`xargs`, not `$(...)`.** zsh does not word-split unquoted command substitution, so
  `pytest $(cat ids)` passes all 561 ids as a **single** argument and pytest reports "no
  tests ran" — a green-looking zero that could easily be mistaken for a passing run.
* **Collection order, not sorted.** The ids were captured sorted at first, and the subset
  then failed: `tests/test_xml.py::test_XmlReader` reads a file an earlier test in the same
  module writes, and `tests/test_configmanager.py::test_fail_no_conf_parameter` depends on
  process state. Both are **pre-existing order dependencies**, unrelated to this feature —
  they pass in collection order and fail in alphabetical order. Recording collection order
  sidesteps them; fixing them is not this feature's business (FR-015 — that would be a
  behaviour change), but they are noted here so the next person does not rediscover them
  as a "regression".

The 10% rule is **not** applied to the grown total — SC-TEST-002 requires the count to grow,
which makes that comparison meaningless (this is the SC-PERF-001 split, plan §IV).

### 1.3 Slowest 15 (context for later regressions)

```
12.30s  tests/test_signalengine.py::test_daemon_run_stops_after_signal
 0.74s  tests/integration/test_mediacue_fade_performance.py::test_fade_profiles_parse_serialize_overhead_budget
 0.40s  tests/test_fade_cue.py::test_fade_cue_construction_performance
 0.26s  tests/contract/test_mediacue_fade_schema_contract.py::test_valid_fade_preset_passes_schema
 0.19s  tests/integration/test_mediacue_fade_roundtrip.py::test_create_script_template_validates_with_schema
 0.19s  tests/test_name_coercion.py::test_cue_name_survives_xml_roundtrip[0]
 0.18s  tests/test_name_coercion.py::test_cue_name_survives_xml_roundtrip[y]
 0.18s  tests/test_canvas_region_roundtrip.py::test_script_roundtrip_preserves_canvas_region
 0.17s  tests/test_xml.py::test_jsonload
 0.16s  tests/test_signalengine.py::test_signal_handling_graceful_exit
 0.16s  tests/integration/test_mediacue_fade_roundtrip.py::test_legacy_mediacue_without_fade_loads
 0.16s  tests/integration/test_mediacue_fade_roundtrip.py::test_mediacue_fade_profiles_roundtrip
 0.15s  tests/test_name_coercion.py::test_nullish_cue_name_no_longer_fails_validation[null]
 0.14s  tests/test_canvas_region_roundtrip.py::test_script_roundtrip_non_trivial_float
 0.14s  tests/unit/test_media_duration.py::test_xsd_rejects_malformed_duration
```

Everything below the outlier is sub-second. No single XML test is currently expensive; a
new one that is will be visible immediately in this table.

---

## 2. Write benchmark

`tests/integration/test_mediacue_fade_performance.py` asserts a *relative* budget
(fade overhead ≤ 15% of base), so it cannot detect a uniform slowdown of both arms. The
absolute numbers are therefore recorded here as well — they are what SC-PERF-001's "within
10%" binds.

```
1 passed in 1.21s / 1.19s / 1.20s / 1.29s / 1.18s
```

| Metric | Best-of-5 |
|---|---|
| Test wall time | **1.18 s** |
| `validate_object` median, dummy script | **0.00627 s** |
| `validate_object` median, script with fade profiles | **0.00653 s** |
| fade/base ratio | **1.041** (test's own budget: ≤ 1.15) |

The two medians are the load-bearing pair: each is the median of 40 `validate_object` calls,
and the reported figure is the best of 5 such medians. Re-measure with the same script in
T063.

---

## 3. New-suite absolute budget — **fixed at T020**

Measured with the corpus frozen and every Phase-1/Phase-2 test written, and deliberately
**before any engine code exists to be tuned against it**. Setting this number after the
engine landed would be measuring the implementation against itself.

```bash
export PYENV_VERSION=3.11.9
pyenv exec python -m pytest tests/contract/ tests/integration/test_d14_chain.py -q
# 252 passed, 27 skipped in 16.09s / 16.13s / 16.17s / 16.18s / 16.28s
```

| Metric | Value |
|---|---|
| Corpus documents | **28** (+ 1 generated), pinned in `tests/data/corpus/PROVENANCE.md` |
| New test files | **10** (9 contract + the D14 chain) |
| New tests | **273** (252 run, 27 skipped, 6 from `test_mediacue_fade_schema_contract.py` pre-existing) |
| New-suite wall time, best-of-5 | **16.09 s** |
| **Absolute budget** | **≤ 20.0 s** — the number T063 checks against |

The budget is set at **16.09 s + ~24% headroom**, rounded to 20 s. The headroom is not
generosity: Phases 4–7 add roughly ten more test files (derivation, adapters, registry
totality, ordering provenance, config parity, logging budget, coherence, legacy
compatibility), and a budget pinned at the current measurement would be breached by
writing the tests the feature requires — the exact mistake SC-PERF-001's split exists to
avoid. What it does **not** allow room for is the engine being slower than what it
replaces: that is caught by the two rules above, which have no headroom at all.

Total-suite figure for context: **807 passed, 27 skipped in 34.93 s** (best of 3). The
growth from 19.68 s is almost entirely the 27 corpus documents being read, written and
re-read across the contract tests.

This is an **absolute** budget, not a percentage. A 10% rule cannot bind a suite the
feature is required to grow (SC-TEST-002), which is why SC-PERF-001 was split.

### The three budgets, and what each one can actually catch

| Budget | Value | Catches |
|---|---|---|
| Write benchmark | ≤ 1.30 s; medians ≤ 0.00690 / 0.00718 s | the mapper being slower per object |
| Pre-existing 561 | ≤ 21.7 s (10% over 19.72 s) | a regression anywhere the old suite already touched |
| New corpus suite | ≤ 20.0 s | the corpus harness itself becoming the bottleneck |

None of the three can catch a slowdown that only appears on documents larger than any in
the corpus. The largest is `complex_test/script.xml` at 24 KB; real show files are bigger.
That limit is stated rather than papered over — SC-PERF-002's derivation-count assertion
(T064) is what covers scaling, because it is a count and not a clock.

---

## 4. Precondition: the baseline is green

Recorded as an explicit precondition, per the plan's Technical Context. At `6a118c8`, with
`git diff --stat src/` empty, the suite is **561 passed, 0 failed, 0 skipped**. Every
guarantee in this feature is relative to that state; if it were not green, "byte-identical"
would have nothing to be identical to.
