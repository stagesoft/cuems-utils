<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Show-document load drift — owned follow-up

**Opened**: 2026-10-14 by `015-consumer-gate-closure` (FR-079c, SC-PERF-005, R12)
**Status**: open, **not investigated**. Feature 015 records it; it MUST NOT investigate it.
**Not deleted by FR-091**: this is a live follow-up, not a landed one-shot prompt.

## The finding

`CuemsScript.load` of `tests/data/corpus/cuems-engine/projects/complex_test/script.xml`
straddles the 16.5 ms budget feature 013 set. Measured at the 015 branch point on the interpreter
`hatch` resolves, **16 samples across three windows**:

| Window | Samples (ms) | Spread |
|---|---|---|
| A | 16.829 · 16.898 · 17.069 · 17.110 · 17.312 | 2.9% |
| B | 16.474 · 16.532 · 16.816 · 17.322 · 17.750 | 7.7% |
| C | 16.465 · 16.625 · 16.816 · 16.819 · 17.030 · 17.262 | 4.8% |
| **pooled** | **band 16.465 – 17.750, median 16.864** | **7.8%** |

14 of 16 exceed 16.5 ms, 2 do not — the old assertion was flaky on an unchanged tree.

## Budget history

| Feature | Budget | Why |
|---|---|---|
| 008 | ≤ 35.99 ms | original; measured 18.673 |
| 012 | ≤ 15.0 ms | worst of 12.605–13.651 plus 10% |
| 013 | ≤ 16.5 ms | worst of 14.07–14.96 plus ~10%; mechanism named (`elementpath` node tree per `xs:alternative`) |
| 015 | band 16.465–17.750, bound = top × 115% | change of instrument (012's R14 precedent), not a fourth raise |

## Why it is real, not an instrument artefact

It **survived a full interpreter migration across two 3.11.9 builds** (conda-built CPython 3.11.2
→ pyenv/uv 3.11.9; R11 additionally found that a pyenv build without `--enable-optimizations
--with-lto` is 32–72% slower, so the figure depends on *which build*). Against 013's own
14.07–14.96 ms the band is **+13% to +19%**.

## Owner and next step

Owner: the maintainer of `cuems-utils`. Start from 013's profiled mechanism (the fresh
`build_node_tree` per `xs:alternative`/`xs:assert` evaluation, cost ∝ document size × class-carrying
elements) and the identified candidate — fewer alternatives or a cheaper discriminator than an XPath
test, a schema-design change. Record which interpreter build every new figure comes from.
