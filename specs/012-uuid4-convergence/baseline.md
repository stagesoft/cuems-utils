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

**Two budgets are recorded as exceeded**, both stated by the first
`/speckit.analyze` pass as values rather than measurements, and both found on
measurement to collide with something already true. §3 and §6 have the
arithmetic. Neither is a defect in the implementation, and saying so here rather
than restating them as passing is the whole point of this document.

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

## 3. Re-mint throughput (T077, SC-PERF-001, FR-PERF-001) — **budget exceeded**

Fixture: `remint_200` (200 projects, 3,937,400 bytes, 400 documents), both node
counts over **byte-identical** libraries — the same node rows generate the
content, and only the substitution table's size varies (2 entries against 10).

| Measurement | Value |
|---|---|
| 2 nodes | **147 MB/s** (26.8 ms) |
| 10 nodes | **158 MB/s** (24.9 ms) |
| Agreement ratio (slower ÷ faster) | **1.08×** |
| FR-PERF-001 floor | ≥ 500 MB/s |
| FR-PERF-001 agreement bound | ≤ 1.10× |

**Agreement: met, and comfortably.** This is the budget SC-PERF-001 exists for —
a per-node repeated pass would make the 10-node run about **5×** the 2-node one
over identical bytes, and 1.08× is nowhere near it.

### The 500 MB/s floor is **not met, and cannot be**

Measured directly (`test_the_no_substitution_pass_is_the_machines_own_ceiling`):
a pass that reads every document and atomically rewrites it **with no
substitution at all** costs **13.2 ms — about 298 MB/s**. The budget allows
7.9 ms. So no implementation can reach it while the operation keeps the
atomicity its contract requires (temporary plus `os.replace`, per file).

The floor conflates two different costs. `remint_200` is 400 documents of about
10 KB each, so the pass is dominated by **per-file syscalls**, not by bytes
moved: 400 atomic replaces cost what they cost. 500 MB/s describes streaming a
few large files, which is not the shape of a project library.

**What the implementation did improve**, measured during this work:

| Apply loop | Throughput |
|---|---|
| first working version (text I/O, `mkstemp` + `chmod`) | 92 MB/s |
| bytes throughout, single `os.open` with the target's mode | **147–158 MB/s** |
| the machine's own read + atomic-rewrite ceiling | 298 MB/s |

So the implementation sits at about **half** the machine's hard ceiling, with
the substitution itself accounting for the difference. That is the figure the
test now asserts against (within 2.5× of the no-substitution pass), because it
is portable across machines and catches the regression the absolute number was
reaching for — a substitution that has become the bottleneck — without
measuring the disk and calling the result a verdict on this code.

**Recommendation for whoever revisits FR-PERF-001**: state the budget per
document, or state it for a fixture of realistic file sizes. A throughput figure
over many small files is a syscall benchmark wearing a throughput figure's
clothes.

## 4. The `remint_200` fixture ceiling (T078, SC-PERF-001) — **met, and lowered**

| | |
|---|---|
| Measured | **0.024–0.026 s** (400 documents, 3,937,400 bytes) |
| Ceiling as stated by the analysis pass | ≤ 2.0 s |
| **Ceiling as of 2026-09-30** | **≤ 0.5 s** |

T078 instructs that a measurement landing well under the provisional ceiling
lowers it to the measured figure plus headroom. 2.0 s was **eighty times** the
measured value and could not have failed on anything short of a catastrophe.

0.5 s is ~20× the measurement. Deliberately generous for a wall-clock assertion
on a 2-vCPU VM — the alternative failure mode is a test that goes red on an
unrelated load spike, and a timing test that cries wolf gets its budget raised
rather than its cause investigated. It is four times tighter than what it
replaces and would still catch a per-file cost that grew by an order of
magnitude. **It moves downward only.**

## 5. Read path against feature 008's baseline (T079, SC-PERF-002, FR-PERF-002)

Method: median of five warm runs, fresh measurement per run, matching
`specs/008-rebuild-extension/baseline.md`. Two rows, two different comparisons
(research R14).

| Row | 008 recorded | Compared against | Measured | Verdict |
|---|---|---|---|---|
| show document load | 18.673 ms, within budget | its **budget**, 35.99 ms | **13.062 ms** | **met**, with room |
| `network_map` config load | 10.14–10.49 ms, **exceeded-or-marginal** against its own 10.20 ms budget | its **measured band** | **7.817 ms** | **met** — and *faster* than the band |

**The `network_map` row is compared to the band and not to the budget**, and
that is the point of R14: 008 records it as exceeded-or-marginal, so asserting
the budget would fail on a tree where this feature changed nothing — which tells
a reader nothing about this feature and teaches them to ignore the test.

**The narrowing did not slow the map read; it came in below the band.** Worth
saying why, since this feature added a union type and a registered T2 rule to
that document's read path. The union resolves once at schema load, not per read.
The uniqueness rule walks the rows once. Both are small against the version
probe's `ElementTree.parse`, which is what 008 identified as the mechanism
behind that row's marginality in the first place. The gain over 008's band is
most likely machine and cache differences rather than anything this feature did,
and is recorded as a measurement rather than claimed as an improvement.

Also measured: a **60-row colliding map** is refused in **19.1 ms**, so building
the message that names every row is not quadratic — an operator diagnosing a
collision is already having a bad day.

## 6. Operator estimate accuracy (T080, SC-PERF-003) — **budget exceeded, in the safe direction**

| | 2 nodes | 10 nodes |
|---|---|---|
| Predicted | 54.3 ms | 55.5 ms |
| Actual | 24.6 ms | 25.0 ms |
| Error | **+121%** | **+122%** |
| SC-PERF-003 tolerance | ±25% | ±25% |

**Exceeded, and pessimistic.** The estimate is about twice the actual duration.

### Why, measured

FR-PERF-003 divides surveyed bytes by the throughput **the survey observed on
this machine**, and that part is right — it is what keeps the estimate off
FR-PERF-001's floor. But research R8's supporting premise, *"the survey already
reads every byte the apply pass will read, so the measurement is free"*, is true
of the **read** and not of the **work**:

| Pass | Per byte | Measured |
|---|---|---|
| survey | read, then find **any** uuid shape — five character classes at every position | ~69 MB/s |
| apply | read, substitute **known literal** tokens (fast literal search), write | ~150 MB/s |

The survey's scan is the more expensive of the two *even though it writes
nothing*, so dividing by its throughput overstates the apply pass by roughly the
ratio between them.

### What was fixed, and what remains

Introducing `ids.scan_values` — a values-only byte scan for the survey, in place
of the full occurrence scanner the operator-facing check needs — removed the
larger part of the gap:

| Survey scan | Estimate error |
|---|---|
| `scan_text` (full occurrence scanner, dataclass per token) | **+884%** |
| `scan_values` (values only, bytes) | **+121%** |

What remains is inherent to the survey asking a broader question than the apply
pass answers.

### What is asserted instead

The direction matters more than the magnitude, and it is what an operator is
exposed to. `test_estimate_tolerance.py` asserts that the estimate is **never
optimistic** (an operator told 8 minutes who needs 25 has a problem; one told 50
who needs 25 does not), that it stays within a **recorded pessimism bound** so it
cannot drift back to ten times the truth, and that dividing by FR-PERF-001's
floor remains **worse and in the dangerous direction** — 7.9 ms predicted against
24.6 ms actual, which is the specific wrong implementation the requirement
excludes. `render_estimate` tells the operator the figure is a conservative
bound.

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

1. **FR-PERF-001's 500 MB/s floor is unreachable** for this operation at
   `remint_200`'s file count (§3). Not an implementation defect — measured
   against a no-substitution pass. The budget needs restating per document or
   over realistic file sizes.
2. **SC-PERF-003's ±25% is not met** (§6), by about a factor of two and in the
   pessimistic direction. Closing it means either making the survey's scan as
   cheap as the apply pass's substitution — it asks a broader question, so this
   is not free — or changing the estimate's formula, which FR-PERF-003 specifies.
3. **Two §10.7 items remain unconfirmed on hardware** (§7), mitigated by design
   rather than answered.
