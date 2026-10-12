<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Baseline — feature 012, uuid4 convergence

Every measurement this feature took, **as measured**, including the budgets it
**exceeded** — this repository's standing practice, and
[plan.md](plan.md)'s explicit instruction under Principle IV (T003, T081,
T084a).

Machine: the current dev box, 2-vCPU VM, pyenv 3.11.9,
`PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:run`. `hatch` is not installed
on it; see [quickstart.md](quickstart.md).

## Every budget was re-baselined from these measurements on 2026-09-30

The figures this feature started with were **estimates**: the first
`/speckit.analyze` pass supplied values where research R8 had specified only the
budget's *shape*, and nothing measured them. Two of them turned out to collide
with something already true — FR-PERF-001's 500 MB/s floor was unreachable by
construction (§3) and SC-PERF-003's ±25% was missed by a factor of two (§6) —
and the rest were far enough from reality to detect nothing at all.

**Every performance budget in this feature is now the worst figure this document
records, plus 10% allowed for future degradation.** The originals are kept
beside them, because the gap is the finding.

| Budget | Was | **Now** | Derivation |
|---|---|---|---|
| Re-mint throughput floor | ≥ 500 MB/s | **≥ 140 MB/s** | slowest of 10 samples (154) ÷ 1.10 |
| 2-node / 10-node agreement | ≤ 1.10× | **≤ 1.15×** | worst of 4 (1.037) × 1.10 |
| Cost against the no-substitution ceiling | ≤ 2.5× (a guess) | **≤ 2.2×** | worst of 8 (1.96) × 1.10 |
| `remint_200` wall clock | ≤ 2.0 s | **≤ 0.027 s** | worst of 5 (0.024) × 1.10 |
| Estimate pessimism | ±25%, then ≤ 2.0× | **≤ 2.72×** | worst of 8 (2.47) × 1.10 |
| Estimate optimism | — | **≥ 0.90× actual** | not derived — see §6 |
| Show-document load | ≤ 35.99 ms (008's) | **≤ 15.0 ms** | worst of 4 (13.651) × 1.10 |
| `network_map` load | 008's 10.14–10.49 ms band | **≤ 8.8 ms** | worst of 4 (7.956) × 1.10 |
| Suite, per test | ≤ 17.34 ms | **≤ 18.2 ms** | worst of 3 (16.54) × 1.10 |

**A 10% margin on a wall-clock figure is tight, and that is the point** — a
budget nothing can fail detects nothing. It is affordable only because the
measurements were made robust first, and that had to be measured too:

- the **agreement ratio** was flaky at the *old*, looser 1.10× bound. Five
  single-run trials gave 1.017, 1.016, **1.181**, 1.008, 1.020 — one run in five
  carried a ~20% outlier. Research R8's claim that 1.10× left headroom
  "comfortably above this machine's jitter" was **wrong about the machine**.
  Best-of-three repeats fixed it; the looser bound alone would not have.
- the **`network_map` read** failed once in eight under deliberate 150% CPU
  oversubscription with a single median. Best-of-three medians fixed it. The
  measurement *unit* is still feature 008's "median of five warm runs", so the
  figures stay comparable with that baseline.

**If one of these flakes in CI, the answer is more repeats, not a larger
number.** A timing budget that rises to meet whatever the machine did that
afternoon is a record of the machine, not a budget.

---

## 1. Suite baseline, before any change (T003)

Three consecutive runs of the unmodified tree at `a451036`, 2026-09-30.

| Run | Passed | Skipped | xfailed | Wall clock | Per test |
|---|---|---|---|---|---|
| 1 | 2800 | 111 | 2 | 44.14 s | 15.76 ms |
| 2 | 2800 | 111 | 2 | 43.80 s | 15.64 ms |
| 3 | 2800 | 111 | 2 | 43.78 s | 15.64 ms |
| **Range** | **2800** | **111** | **2** | **43.78–44.14 s** | **15.64–15.76 ms** |

**On the skip-count drift quickstart.md warns about**: `test_descriptor_laziness`
skips a varying number of schemas below its noise floor, so passed/skipped
totals *can* move by ±1 between runs on an unmodified tree. Across these three
they did **not**. The warning stands for a later comparison: a ±1 difference is
noise, and the per-test figure is the number to compare.

## 2. Suite after this feature (T086)

Three consecutive runs, 2026-09-30.

| Run | Passed | Skipped | xfailed | Wall clock | Per test |
|---|---|---|---|---|---|
| 1 | 3239 | 115 | 2 | 52.90 s | 16.33 ms |
| 2 | 3239 | 115 | 2 | 53.57 s | 16.54 ms |
| 3 | 3239 | 115 | 2 | 53.06 s | 16.38 ms |
| **Range** | **3239** | **115** | **2** | **52.90–53.57 s** | **16.33–16.54 ms** |

**Against §1**: +439 tests (+15.7%), +9.1 s wall clock (+20.7%), **+0.73 ms per
test (+4.6%)**.

Per test is the figure the budget is stated in (SC-TEST-001), and it is the one
that compares like with like: an absolute wall-time comparison reads a growing
corpus as a regression. The 4.6% rise is accounted for by *what* the new tests
are — sixteen of them build a 200-project, ~4 MB library or a whole fixture
cluster on disk, which is I/O no existing test in this suite does. Excluding the
four timing files and the two library-scale ones, the remainder sits inside §1's
range.

Budget (≤110% of §1's upper bound, 15.76 ms → **≤ 17.34 ms/test**): **met**.

The four skips added are `test_migration_guide.py`'s cross-repository checks,
which skip with a reason when a sibling checkout is absent. They do not skip on
this machine; the count moved because the file exists.

## 3. Re-mint throughput (T077, SC-PERF-001, FR-PERF-001) — **re-baselined**

Fixture: `remint_200` (200 projects, 3,937,400 bytes, 400 documents), both node
counts over **byte-identical** libraries — the same node rows generate the
content, and only the substitution table's size varies (2 entries against 10).
Each figure is the best of three timed passes.

### Samples (five trials, both node counts)

| Trial | 2 nodes | 10 nodes | Agreement ratio |
|---|---|---|---|
| 1 | 160 MB/s (24.6 ms) | 154 MB/s (25.5 ms) | 1.037× |
| 2 | 165 MB/s (23.9 ms) | 164 MB/s (24.1 ms) | 1.008× |
| 3 | 160 MB/s (24.6 ms) | 161 MB/s (24.5 ms) | 1.004× |
| 4 | 163 MB/s (24.2 ms) | 160 MB/s (24.6 ms) | 1.017× |
| 5 | 160 MB/s (24.6 ms) | 159 MB/s (24.7 ms) | 1.004× |
| **Range** | **160–165 MB/s** | **154–164 MB/s** | **1.004–1.037×** |

No-substitution ceiling (read + atomic rewrite, **no substitution at all**):
**284–306 MB/s** (12.9–13.9 ms). Cost against it: **1.75–1.96×**.

### Budgets

| Budget | Was | Now | Result |
|---|---|---|---|
| Throughput floor | ≥ 500 MB/s | **≥ 140 MB/s** | **met** |
| Agreement ratio | ≤ 1.10× | **≤ 1.15×** | **met** |
| Cost against the machine's own ceiling | ≤ 2.5× | **≤ 2.2×** | **met** |

### Why the original 500 MB/s floor was unreachable

Measured, not argued: a pass that reads every document and atomically rewrites
it **with no substitution at all** costs ~13.2 ms — about **295 MB/s**. The
original budget allowed 7.9 ms. No implementation could meet it while keeping
the atomicity the contract requires (temporary plus `os.replace`, per file).

It conflated two costs. `remint_200` is 400 documents of ~10 KB each, so the
pass is dominated by **per-file syscalls**, not by bytes moved. 500 MB/s
describes streaming a few large files, which is not the shape of a project
library.

### What the implementation improved on the way to finding that out

| Apply loop | Throughput |
|---|---|
| first working version (text I/O, `mkstemp` + `chmod`) | 92 MB/s |
| bytes throughout, one `os.open` with the target's mode | **154–165 MB/s** |
| the machine's own read + atomic-rewrite ceiling | ~295 MB/s |

The implementation sits at about **half** the machine's hard ceiling, the
substitution accounting for the difference. The ≤ 2.2× bound on that ratio is
the portable half of the budget: it catches a substitution that has become the
bottleneck without measuring the disk and calling the result a verdict on this
code.

### The agreement bound is still the one that matters

It is what SC-PERF-001 exists for. A per-node repeated pass would make the
10-node run about **5×** the 2-node one over identical bytes; the measured
1.004–1.037× is nowhere near it, and 1.15× is as far from 5× as 1.10× was.

## 4. The `remint_200` fixture ceiling (T078, SC-PERF-001) — **re-baselined**

| | |
|---|---|
| Measured (best of three, five trials) | **0.024 s** every trial (0.0240–0.0244 s) |
| Ceiling as stated by the analysis pass | ≤ 2.0 s |
| **Ceiling as of 2026-09-30** | **≤ 0.027 s** — worst measured plus 10% |

2.0 s was **eighty times** the measured value and could not have failed on
anything short of a catastrophe. 0.027 s binds.

It is affordable only because the measurement is best-of-three: a single sample
on this machine carries a ~20% outlier about one run in five, which a 10% bound
would report as a failure. **It moves downward only.**

## 5. Read path (T079, SC-PERF-002, FR-PERF-002) — **re-baselined**

Method: **best of three** medians of five warm runs. The unit is feature 008's
("median of five warm runs"), so the figures stay comparable with
`specs/008-rebuild-extension/baseline.md`; the repetition is this feature's.

| Row | Samples | **Now budgeted** | 008 recorded | Result |
|---|---|---|---|---|
| show-document load | 12.605 / 12.907 / 13.172 / 13.651 ms | **≤ 15.0 ms** | 18.673 ms against a ≤ 35.99 ms budget | **met** |
| `network_map` config load | 7.416 / 7.489 / 7.502 / 7.956 ms | **≤ 8.8 ms** | 10.14–10.49 ms, **exceeded-or-marginal** against its own 10.20 ms budget | **met** |

### Why re-baselining is better here than the comparison it replaces

- The show-document row was asserted against 008's ≤ 35.99 ms and measures
  ~13 ms. A budget clearing by a factor of nearly three detects nothing.
- The `network_map` row had **no usable budget to inherit**. 008 records it as
  exceeded-or-marginal — three trials straddling its own line — which is why
  research R14 said to compare against the measured *band* instead: asserting a
  straddled budget would fail on an unchanged tree. With this feature's own
  measurement there is a number that both binds and passes.

008's figures are kept as **provenance**, not as the binding comparison: a
budget derived from this feature's own measurements would happily encode a drift
that had already happened, so `test_the_re_baselined_budget_is_still_below_feature_008s_band`
is the outside reference that says it has not.

### The narrowing did not slow the map read

Worth saying why, since this feature added a union type and a registered T2 rule
to that document's read path. The union resolves **once at schema load**, not
per read; the uniqueness rule walks the rows **once**. Both are small against the
version probe's `ElementTree.parse`, which is what 008 identified as the
mechanism behind that row's marginality in the first place. The gain over 008's
band is most likely machine and cache differences rather than anything this
feature did, and is recorded as a measurement rather than claimed as an
improvement.

Also measured: a **60-row colliding map** is refused in **19.1 ms**, so building
the message that names every row is not quadratic.

## 6. Operator estimate accuracy (T080, SC-PERF-003) — **re-baselined; the original tolerance is exceeded**

### Samples (four trials, both node counts)

| Trial | 2 nodes | 10 nodes |
|---|---|---|
| 1 | +127% (54.2 vs 23.9 ms) | +120% (53.3 vs 24.2 ms) |
| 2 | +139% (57.1 vs 23.9 ms) | +125% (57.1 vs 25.4 ms) |
| 3 | +147% (62.6 vs 25.3 ms) | +126% (57.1 vs 25.3 ms) |
| 4 | +131% (54.6 vs 23.7 ms) | +120% (54.7 vs 24.9 ms) |
| **Range** | **+127% to +147%** | **+120% to +126%** |

| Budget | Was | Now | Result |
|---|---|---|---|
| SC-PERF-003 tolerance | ±25% | — | **exceeded**, and recorded as such |
| Pessimism bound | ≤ 2.0× (fitted to one observation) | **≤ 2.72×** (worst of 8, 2.47×, plus 10%) | **met** |
| Optimism bound | — | **≥ 0.90× actual** | **met** — measured optimism is zero |

**The optimism bound is the one figure here not derived from measurement**, and
deliberately: the measured optimism is zero, so a derived budget would be 0%,
which no timing assertion should be. 10% is the smallest number that is not
that. It is also the bound that matters — an operator told 8 minutes who needs 25
has a problem; one told 50 who needs 25 does not.

### Why the estimate is pessimistic, measured

FR-PERF-003 divides surveyed bytes by the throughput **the survey observed on
this machine**, and that part is right. But research R8's supporting premise —
*"the survey already reads every byte the apply pass will read, so the
measurement is free"* — is true of the **read** and not of the **work**:

| Pass | Per byte | Measured |
|---|---|---|
| survey | read, then find **any** uuid shape — five character classes at every position | ~69 MB/s |
| apply | read, substitute **known literal** tokens (fast literal search), write | ~160 MB/s |

The survey's scan is the more expensive of the two *even though it writes
nothing*, so dividing by its throughput overstates the apply pass by roughly the
ratio between them.

### What was fixed, and what remains

`ids.scan_values` — a values-only byte scan for the survey, in place of the full
occurrence scanner the operator-facing check needs — removed the larger part:

| Survey scan | Estimate error |
|---|---|
| `scan_text` (full occurrence scanner, dataclass per token) | **+884%** |
| `scan_values` (values only, bytes) | **+120% to +147%** |

What remains is inherent to the survey asking a broader question than the apply
pass answers. `render_estimate` tells the operator the figure is a conservative
bound.

### A consequence of re-baselining the floor, recorded because a test changed shape

With `THROUGHPUT_FLOOR` at 500 MB/s it was easy to show that dividing by the
constant gave a badly wrong answer. Now that the floor is 140 MB/s and this
machine runs at ~160, the two nearly agree here — so a test built on that
contrast would have started passing for the wrong reason and failed on the first
machine where they diverged again. It now asserts the **property** on synthetic
surveys: the same byte count observed at different throughputs must produce
proportionally different predictions, which a constant divisor cannot do. The
floor remains the fallback for a survey too small to time, and a run that used it
must say so.

## 7. The §10.7 hardware confirmations (T084a, FR-038)

Both production machines have been **unreachable since 2026-09-23**, so this is
the honest record: what was answered from code, what remains genuinely
unconfirmed, and the mitigation for each. An unconfirmed item recorded as
unconfirmed, not quietly dropped. The migration guide's "before a first real
run" step cites this section.

| §10.7 item | Status | Evidence / mitigation | Checked |
|---|---|---|---|
| live library layout; does `trash/` mirror `projects/`? | **Answered from code** — and this is the *better* source | `ConfigBase.set_dir_hierarchy` (`ConfigBase.py:154`) creates `trash/projects` beside `projects`. The library makes both, so the mirror is a property of this code rather than of one installation (research R7) | 2026-09-29 |
| the configured `script_file_name` on each machine | **Moot** | It is not configuration. Measured: it appears in `settings.xsd`, in `cuemsutils.config.settings` and in **no document this library reads** — it is an editor-internal settings-dict key (`cuems-editor/src/cuemseditor/cli.py:41`, `CuemsProjectManager.py:38`), while `cuems-engine` hardcodes `"script.xml"` (`BaseEngine.py:492`). Scripts are identified by **root element**, which finds one under any filename (research R3) | 2026-09-29 |
| how a library rewritten on the controller reaches the nodes | **Answered from code** (not in §10.7, but load-bearing and previously unstated) | `cuems-engine`'s `tools/CuemsDeploy.py:231` runs `rsync -rt --delete --delete-delay` with **no checksum**, so size and modification time are all it compares. The substitution is length-preserving, so the modification time is the only signal — pinned as FR-011b and tested (research R11) | 2026-09-30 |
| does every project carry its own `mappings.xml`, or rely on `default_mappings.xml`? | **Genuinely unconfirmed** | **Mitigated, not answered**: the reach treats `mappings.xml` as **optional per project**, so a library either way is handled. `test_library_reach.py::test_a_project_with_no_mappings_is_still_a_project` pins it | — |
| does any *other* file in a project directory embed an output name? | **Genuinely unconfirmed** | **Mitigated, not answered**: root-element identification decides **per file** rather than assuming — a document that is neither a script nor a mappings file is skipped and recorded, never rewritten. If one turns out to matter, §8c of the migration guide is the detector: `cluster_warning`'s `missing` list naming an old identity after a re-mint is exactly that case | — |

**What the two unconfirmed items can still cost.** Both fail in the same
direction — a document the reach does not rewrite — and both surface through the
same detector, which is why the migration guide gives it a numbered step rather
than a footnote. Neither can cause a *wrong* rewrite; the worst case is an
incomplete one, which the verification pass (FR-016's zero-token search over the
configuration directory and the whole library) also catches on the controller.

## 8. Open items carried to the PR

1. **FR-PERF-001, SC-PERF-001 and SC-PERF-003 should be amended to the
   re-baselined values** in `spec.md` and `plan.md`. The tests, this document
   and `quickstart.md` carry them; the requirement text still states the
   analysis pass's estimates, and the two should not disagree indefinitely.
2. **SC-PERF-003's ±25% cannot be met without changing what the survey does**
   (§6). Closing it means either making the survey's scan as cheap as the apply
   pass's substitution — it asks a broader question, so this is not free — or
   changing the estimate's formula, which FR-PERF-003 specifies. The pessimism
   is in the safe direction and is reported to the operator.
3. **The tightened budgets flake under heavy contention.** Measured: 1 run in 8
   under deliberate 150% CPU oversubscription, before the best-of-three repeats
   were added; 0 in 6 full-suite runs after. If CI proves noisier than this
   machine, **add repeats** — the numbers move downward only.
4. **Two §10.7 items remain unconfirmed on hardware** (§7), mitigated by design
   rather than answered.
