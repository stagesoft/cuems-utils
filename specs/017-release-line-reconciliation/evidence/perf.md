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
