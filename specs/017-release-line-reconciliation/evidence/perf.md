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
