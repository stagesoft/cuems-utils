<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Baseline — feature 012, uuid4 convergence

Every measurement this feature took, **as measured**, including any budget exceeded — this
repository's standing practice (T003, T081, T084a).

Machine: the current dev box, 2-vCPU VM, pyenv 3.11.9, `uvx hatch run test.py3.11:run`.
`hatch` is not installed on it; see [quickstart.md](quickstart.md).

---

## 1. Suite baseline, before any change (T003)

Recorded **as a range** over three consecutive runs of the unmodified tree at `a451036`,
2026-09-30.

| Run | Passed | Skipped | xfailed | Wall clock | Per test |
|---|---|---|---|---|---|
| 1 | 2800 | 111 | 2 | 44.14 s | 15.76 ms |
| 2 | 2800 | 111 | 2 | 43.80 s | 15.64 ms |
| 3 | 2800 | 111 | 2 | 43.78 s | 15.64 ms |
| **Range** | **2800** | **111** | **2** | **43.78–44.14 s** | **15.64–15.76 ms** |

**On the skip-count drift quickstart.md warns about**: `test_descriptor_laziness` skips a
varying number of schemas below its noise floor, so passed/skipped totals *can* move by ±1
between runs on an unmodified tree. Across these three runs they did **not** — the counts were
identical. The warning stands for a later comparison: a ±1 difference against this table is
noise, not a regression, and the per-test figure is the number to compare.

The per-test figure is what the budget is stated in. Feature 011's re-measure recorded
20.73 ms/test over 2573 tests (2026-09-03); the suite has since grown to 2800 and is faster per
test, which is why an absolute wall-time comparison across features reads a growing corpus as a
regression and the per-test one does not.

## 2. Suite after this feature (T086)

_Pending — recorded at T086, as a range, against §1._

## 3. Re-mint throughput (T077, SC-PERF-001, FR-PERF-001)

_Pending._

## 4. The `remint_200` fixture ceiling (T078, SC-PERF-001)

_Pending. The ceiling is **provisional** — ≤ 2.0 s, lowered to the measured figure plus headroom
if the measurement lands well under it, and never raised._

## 5. Read path against feature 008's baseline (T079, SC-PERF-002, FR-PERF-002)

_Pending. Two comparisons (research R14): the show-document load against its recorded **budget**,
the `network_map` configuration load against its recorded **measured band**, 10.14–10.49 ms._

## 6. Operator estimate accuracy (T080, SC-PERF-003)

_Pending._

## 7. The §10.7 hardware confirmations (T084a, FR-038)

_Pending._
