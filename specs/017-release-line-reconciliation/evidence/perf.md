# Performance (FR-PERF-001) — 017

Interpreter: hatch `test.py3.11`, uv-managed CPython **3.11.9** (Clang 18.1.8),
`~/.local/share/hatch/env/virtual/cuemsutils/KPtCKENL/test.py3.11/bin/python`. Governor
`powersave`. Host: Debian 13, kernel 6.12.

## T005: arm A (`5e4c637`) baselines, 2026-10-21, ~17:30 UTC

⚠ **The box was contended.** The 1-minute load average was 7.8–9.0, from desktop processes
(Chrome ~28% CPU, Cursor). Treat these absolute figures as indicative. The budget verdicts are
taken from **interleaved A/B** runs in T066, never from a comparison between windows.

| Path | Method | Arm A | Reference |
|---|---|---|---|
| show-document load | `tools/perf_show_load.py`, 6 samples, one window (015's recipe: min of 3 medians of 5) | **16.139–16.373 ms**, median 16.28 | band 16.465–17.750 ms (015) |
| `script` descriptor, warm | `python -m tests.support.perf_descriptor --rounds 5 --schemas script` | **0.166 ms** [0.163–0.168]; cold 254.5 ms; `_instance_for`/warm call 0 | 0.165 ms (descriptor-instance-cache record) |
| suite ms/test | `evidence/suite-A-1.txt` | **9.56 ms/test** (3770 passed in 36.05 s) | — |

Raw show-load samples (`arm ms scaling_cur_freq_kHz loadavg1`):

```
A 16.221 2013694 9.02
A 16.322 4028175 9.02
A 16.227 1396956 9.02
A 16.373 1913336 9.02
A 16.339 3640931 8.78
A 16.139 1113000 8.78
```

## T035: the migration tools' post-write loader check (FR-029c): measured, not budgeted

013's precedent (SC-PERF-003): a tool's cost is per-document validation, which a throughput
budget does not measure. So this is recorded, with no pass/fail line.

**Method.** `<scratchpad>/toolcost/run_once.py`, in a fresh process per sample, runs
`reshape_devices.main` then `convert_documents.main` over **fresh copies** of five documents
that both tools actually rewrite. The documents: `tests/data/corpus/pre-013/{script,settings,
project_mappings}.xml` and `tests/data/rc17/{stop_project,stop_control}.xml`. Arms alternate
×8: **before** = `ffc34cc` (S-4, just before S-3), **after** = `6768e96` (S-3). Same interpreter
as above. Load 1.31, `scaling_cur_freq` 1.76 GHz at the start.

| Arm | 8 samples (ms) | Median |
|---|---|---|
| before S-3 | 310.4 308.9 311.9 304.9 305.3 310.2 306.3 313.0 | **309.6 ms** |
| after S-3 | 528.2 522.9 521.5 532.7 513.3 523.7 519.5 531.8 | **522.9 ms** |

- **+213 ms** for the run, about **21 ms per written document**.
- That matches 013's "~30 ms per script" for schema validation, which is what the check is: one
  T1+T2 load of each written document.
- For a 200-project library migrated once, it adds about **4 s**.
- No document in the sample was refused, so the report path's own cost is not in these figures.

## T066: the three budgets, as bands, interleaved A/B (FR-PERF-001, SC-009)

Arm A = `5e4c637`, arm B = the 017 head (`8f210fd`, a fixed worktree, so the later cleanup commits
are not in it). Same interpreter as above. Three windows: 22:24 and 22:25 (load 2–3), then 21:42
the next session (load 0.94, a quiet box). Arms alternate per sample.

### Show-document load (`tools/perf_show_load.py`, 015's recipe)

| Arm | n | Band | Median | Spread |
|---|---|---|---|---|
| A | 17 | 16.002–17.041 ms | **16.387** | 6.3% |
| B | 17 | 16.072–16.804 ms | **16.323** | 4.5% |

**B is 99.6% of A. ✅ No worse than A.** B's median is below 015's band (16.465–17.750 ms),
meaning faster, not over. This box measures lower than 015's did. The verdict rests on the
interleaved comparison, which is the instrument the budget names.

### Suite ms/test (from `suite-verdict.md`'s three interleaved runs)

A median 33.25 s / 3906 tests = **8.51 ms**; B median 36.38 s / 4038 tests = **9.01 ms**.
**105.9% of A ✅** (budget ≤ 115%). One B sample ran at load 8.06, so the median is used.

### `script` descriptor, warm call (`python -m tests.support.perf_descriptor --rounds 5 --schemas script`)

| Window | A | B |
|---|---|---|
| 1 | 0.165 ms | 0.165 ms |
| 2 | 0.165 ms | 0.164 ms |
| 3 | 0.164 ms | 0.165 ms |

**About 100% of A ✅** (budget ≤ 115%). Every warm call was a cache hit (`_instance_for`/warm
call = 0) on both arms.

**SC-009: all three budgets hold.** One enum value and one membership test moved none of them, as
the work order expected.

Raw samples: `<scratchpad>/perf/show-w{1,2,3}.txt` and `desc-w{1,2,3}.txt`, transcribed below.

```
# window 1 22:24:16 load 3.13 5.06 3.17
A 16.624 3497609 3.13
B 16.392 1546517 2.96
A 16.002 1113000 2.96
B 16.672 1540814 2.96
A 16.234 1882302 2.96
B 16.089 2472093 2.96
A 16.387 4024303 2.96
B 16.284 1113000 2.80
A 16.003 4038044 2.80
B 16.155 1397147 2.80
A 16.048 4041579 2.80
B 16.437 1719614 2.80
# window 2 22:24:59 load 2.07 4.49 3.07
A 16.729 3124962 2.07
B 16.338 1113000 2.07
A 17.041 3368560 2.07
B 16.072 1982744 1.98
A 16.570 1397511 1.98
B 16.094 4036256 1.98
A 16.349 1796536 1.98
B 16.323 2918714 1.98
A 16.119 1550779 1.98
B 16.179 2908103 1.91
# window 3 21:42:24 load 0.94 1.52 2.14
A 16.276 4028455 0.94
B 16.297 1927991 0.94
A 16.419 1796741 0.94
B 16.343 1113000 0.94
A 16.955 4038918 0.94
B 16.804 1113000 0.94
A 16.167 1796495 0.94
B 16.112 4038970 0.94
A 16.773 1113000 0.94
B 16.333 1113000 0.94
A 16.674 1396917 0.94
B 16.453 1797168 0.94
```
