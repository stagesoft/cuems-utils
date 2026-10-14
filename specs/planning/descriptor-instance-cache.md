<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Descriptor instance cache — implementation plan

**Opened**: 2026-10-14, following up `015-consumer-gate-closure`'s recorded exception
(`specs/015-consumer-gate-closure/baseline.md`, "Exceeded, recorded as exceeded" item 1).
**Status**: phases 0–4 done (2026-10-14), uncommitted; phase 5 (record and delete) remains. Re-verified 2026-10-14 against `9d2f337`, after the
foreign-controller scoping pull. That pull touched none of `xml/descriptor.py`, `xml/mapper.py`
or `ConfigManager.get_schema_descriptor`, and the gates still hold there: ruff 0, mypy 72, suite
3724 passed / 115 skipped / 2 xfailed.
**Scope**: `cuems-utils` only. No schema change, no version step, no public-surface change, no
new dependency.

> ⚠ **This document deletes itself.** Per this repository's deletion policy (`CLAUDE.md`,
> "specs/planning and specs/agreements"), once every phase below is implemented and its
> resolution is recorded in `CLAUDE.md`'s "Recent Changes" (phase 5), **this file MUST be
> deleted in the same change that records it**. Do not leave it behind as history; git keeps it.
> The last task in this plan is that deletion.

---

## 1. The problem

Feature 015's G3 made every `TypeDescriptor.instance` wire-shaped, seeded and fully expanded,
and built it eagerly in `SchemaDescriptor.describe()`. 015 measured descriptor derivation for
`script` going from **1.04 to 2.83 ms (+170%) against a ≤ 1.22 ms budget**. About 80% of that is
`descriptor._instance_for`. 015 accepted the cost and carried it, naming two possible mitigations
(build lazily, or cache and hand out copies) and one open question: callers mutate instances, so
is a copy safe?

This plan answers that question with measurements and adopts **cache and copy**.

## 2. What was measured (2026-10-14, hatch `test.py3.11` interpreter, load 1.0–1.3)

Measured with throwaway scratch scripts, not committed. Phase 0 replaces them with a committed
probe.

⚠ **The absolute figures in §2.1 and §2.2 were taken while the box was in its slow state and read
about 2× high.** The same scratch script re-run later the same day gave `script` **2.922 →
0.136 ms** instead of 5.645 → 0.265 ms. The **ratios did not move** (21.5× against 21.3×), and
the conclusions rest on the ratios. §2.5 has the resolution. Use the phase 0 figures (§2.6) for
any absolute number.

### 2.1 Where the time goes

| Measurement, `script` schema, warm | ms per call |
|---|---|
| `SchemaDescriptor().types('script')` (34 types) | 5.645–5.884 |
| `_instance_for` alone, all 34 types | 4.314–4.399 |
| raw build (`_build_value_for`), the 29 normal-path types | 1.711 |
| `Mapper.encode_wire` alone over those raw values | 1.226 |
| `Mapper('script')` construction ×34 | 0.012 (negligible) |

The 34 script instances hold **633 nodes** in total, which is about **7 µs per output node**.
There is no single hotspot. The cost has four sources:

1. **Nothing is cached across calls.** `ConfigManager.get_schema_descriptor` calls
   `SchemaDescriptor().types()` fresh every time. Only `spec.derive()` is `lru_cache`d.
   015's baseline describes this as "an `lru_cache`d path", which is not true of the
   descriptor itself. The result depends only on the bundled XSDs and the model classes, so it
   is a per-process constant that is recomputed on every request.
2. **Every type rebuilds its whole subtree.** One `types('script')` call makes about 105
   `_build_value_for` calls for 29 distinct types (~3.6×). `CueListContentsType` alone takes
   698 µs because it re-expands every cue type, and each cue type is then described again
   separately (Audio/Video/MediaCueType about 310 µs each).
3. **Each node is walked twice.** The raw build calls `_defaults_for`, resolves `_seed_for`
   through xmlschema facet objects (`_facet`, `get_facet`), constructs the model class
   (`model(body)`, which runs the `CuemsDict` setters and coercion) and parses a `CTimecode`.
   Then `encode_wire` walks the same tree again (`spec.field`, `order_keys`, `adapter_for`,
   `_omit`, `isinstance`).
4. **Lots of small overhead.** About 750 `TypeKey.__hash__` calls per `types()` (`TypeKey` is a
   dataclass, so its hash runs in Python) and about 2,150 `dict.get` calls.

### 2.2 Per schema, and what a cache would cost instead

| schema | types | nodes | `types()` now | cached + structural copy | speedup |
|---|---|---|---|---|---|
| script | 34 | 633 | 5.645 ms | 0.265 ms | 21× |
| settings | 10 | 144 | 1.310 | 0.058 | 23× |
| network_map | 3 | 40 | 0.385 | 0.017 | 22× |
| project_mappings | 16 | 362 | 2.723 | 0.154 | 18× |
| project_settings | 2 | 9 | 0.136 | 0.008 | 17× |
| hardware_outputs | 3 | 18 | 0.161 | 0.014 | 12× |

The prototype checked two things for all six schemas: the cached instances are JSON-identical
to freshly built ones, and clearing a returned instance leaves the next call's instance intact.

### 2.3 The copy-safety question 015 left open

Across all six schemas, **every leaf of every instance is `str`, `int`, `float`, `bool` or
`None`**. Containers are only `dict` and `list`. This is consistent with
`test_nothing_non_serialisable_enters_the_instance` (FR-030), which already guarantees the
instance is JSON-safe.

So a structural copy of the dicts and lists is a **complete** copy: there is no mutable leaf
for two callers to share. It is also about 3.5× cheaper than `copy.deepcopy` (0.186 vs 0.650 ms
for all script instances), because `deepcopy` keeps a memo dict and dispatches through Python
for every object.

### 2.4 Cold path, for context only

In a fresh process, the first `types('script')` costs about **490 ms**: compiling `script.xsd`
takes 352 ms, the global repairability join builds the other five registries in 132 ms, and
building the descriptors themselves takes about 10 ms. That first-call cost belongs to
xmlschema/elementpath and is **out of scope** here (see §7).

The ~490 ms above was measured in the slow state (§2.5) and by a different method. The phase 0
probe, which times the first `types()` call after import in a fresh process (so it includes the
global join but not import), reads **about 252 ms** for `script` on both arms (§2.6). Either way,
it is unchanged by 015 and unchanged by this plan.

### 2.5 The discrepancy, resolved in phase 0 (T0.3)

015's paired runs read `derive=2.79–2.87 ms` for the branch in its "fast" box state and
`derive=5.733 ms` in its "slow" state (`snapshots/perf-paired-2026-10-14.txt`). This plan's first
session read 5.6–5.9 ms, which matched the slow state.

**Resolution: same operation, different box state.** The committed probe reproduces 015's
fast-state figures within 3% (A 1.052 against 015's 1.023/1.062 ms, B 2.895 against 2.791/2.873
ms). The original scratch script, re-run later the same day, read 2.922 ms instead of 5.645 ms
with its ratio unchanged. Two other suspects were measured and **ruled out**:
- **Garbage collection.** No generation-2 collection fired in 300 warm calls, and mean, median and
  `gc.disable()` all agree at about 3.0 ms.
- **Logging.** The median is unchanged across `CUEMS_LOG_LEVEL` unset / ERROR / INFO / DEBUG, and
  nothing is written to stdout during the call.

**Hypothesis, not proven**: the slow state is CPU frequency scaling. The governor is
`powersave`, and core clocks read 2.0–4.0 GHz. If a later session sees the 2× state again, check
`scaling_cur_freq` before trusting any absolute figure. Ratios from interleaved A/B runs are
immune to it either way.

### 2.6 Phase 0 baseline (T0.2), the figures acceptance is measured against

Run 2026-10-14 11:00–11:11 with `tests/support/perf_descriptor.py`. Interpreter: hatch
`test.py3.11`, CPython 3.11.9 python-build-standalone (Clang 18.1.8). A = worktree at 015's branch
point `75a958e`; B = `9d2f337`. **16 samples per arm in three windows, five minutes apart**
(5 + 5 + 6 rounds, interleaved), 100 timed warm calls per sample. Load was 2.24–2.63, then
0.66–0.71, then 0.43–0.52.

| schema | A: branch point, warm ms | B: `9d2f337`, warm ms | B/A | nodes A→B | `_instance_for` per warm call (B) |
|---|---|---|---|---|---|
| script | **1.052** [1.032–1.287] | **2.895** [2.844–3.153] | **2.75×** | 732 → 633 | 34 |
| settings | 0.200 [0.198–0.207] | 0.689 [0.678–0.928] | 3.45× | 93 → 144 | 10 |
| network_map | 0.057 [0.055–0.058] | 0.206 [0.201–0.225] | 3.63× | 38 → 40 | 3 |
| project_mappings | 0.314 [0.308–0.425] | 1.412 [1.382–1.568] | 4.50× | 336 → 362 | 16 |
| project_settings | 0.023 [0.021–0.024] | 0.070 [0.067–0.093] | 3.07× | 8 → 9 | 2 |
| hardware_outputs | 0.029 [0.027–0.029] | 0.085 [0.082–0.126] | 2.96× | 14 → 18 | 3 |

Each figure is the median of 16 sample medians, with the band of sample medians in brackets.

- **The ratio is stable across windows.** For `script` it is 2.77×, 2.72× and 2.76×, although
  load fell by a factor of five between the first and last windows.
- **Only `script` and `project_mappings` are above 1 ms.** The four small schemas show bands of
  up to 54% from single outliers, so, as in `test_descriptor_laziness.py`'s `_MEANINGFUL_MS`, they
  are reported but not used for a verdict.
- **The node count is not the cost.** B builds fewer `script` nodes than A (633 against 732) yet
  takes 2.75× as long. The cost is per node: seeding, model construction and the `encode_wire`
  pass (§2.1), not tree size.
- **015's recorded exception is confirmed**: 2.895 ms against the ≤ 1.22 ms budget.

## 3. Decision

**Cache each `TypeDescriptor` per process. On every call, return a `TypeDescriptor` whose
`instance` is a fresh structural copy.**

- **Why caching, not laziness.** The main consumer, `cuems-editor`'s `schema_descriptor` handler
  (`CuemsWsUser.py`, `schema_descriptor_value`), serialises **every** type's instance on every
  request. Building lazily would save nothing on that path. Caching helps every path.
- **Why caching keeps the G3 guarantee.** The cached value is still produced by the same
  `Mapper.encode_wire` that `to_wire()` uses. The guarantee that the instance is "wire-shaped by
  construction" (research R2) does not change: it is computed once instead of on every call.
- **Why the cache is safe.** Inputs are fixed for the life of a process (bundled XSDs, model
  classes, registries). Every existing cache below it (`derive`, `get_schema`, the registries,
  `_repairability_cache`, `_wrap_index_cache`) already makes the same assumption, and
  `descriptor.clear_cache()` already exists as the reset point.
- **Why not memoise subtrees (§2.1 point 2) or `_seed_for`.** Either would cut only the single
  uncached build per process, which is about 6 ms. Once the cache lands, that build stops
  mattering. Recorded in §7 as not done.

## 4. Design

All changes are in `src/cuemsutils/xml/descriptor.py`.

### 4.1 The cache

```python
_described_cache: dict[TypeKey, TypeDescriptor] = {}

def _copy_instance(value):
    """A structural copy. Correct only because every leaf is an immutable
    JSON scalar, which _assert_scalar_leaves checks when the cache is filled."""
    kind = type(value)
    if kind is dict:
        return {k: _copy_instance(v) for k, v in value.items()}
    if kind is list:
        return [_copy_instance(v) for v in value]
    return value
```

- **Cache by `TypeKey`, inside `describe()`**, not by schema inside `types()`. `types()` already
  goes through `describe()`, so one cache covers both entry points, and a caller asking for a
  single type also benefits.
- **On a cache miss**, build the descriptor exactly as today, then run
  `_assert_scalar_leaves(instance, key)`, then store it.
- **On every call**, return `dataclasses.replace(cached, instance=_copy_instance(cached.instance))`.
  `fields` is a tuple of frozen `FieldDescriptor`s and is shared on purpose.
- **Never hand out the cached object itself**, not even on the call that filled the cache.
  Otherwise the first caller would hold the one mutable original.

### 4.2 Fail loudly if the leaf invariant ever breaks

`_assert_scalar_leaves` walks the instance once, when the cache is filled. It raises `TypeError`
naming the `TypeKey` and the path to any leaf whose `type()` is not one of
`str, int, float, bool, NoneType`, and any container that is not exactly `dict` or `list`.

**Exact types, not `isinstance`.** A `CuemsDict` subclass, a `Uuid` or a `CTimecode` is a
mutable or identity-carrying object that a structural copy would share between callers. Those
must be rejected, not passed through. If a future seed ever produces one, this check is what
stops the cache from silently aliasing it across callers.

Running the check only on a miss keeps its cost off the warm path.

### 4.3 Resetting the cache

`descriptor.clear_cache()` gains `_described_cache.clear()`. Tests that reset the lower caches
(`spec.clear_cache`, `schema.clear_cache`, `registry.clear_cache`) without also calling
`descriptor.clear_cache()` would keep stale descriptors. Phase 1 checks for any such test.

### 4.4 Threads

`cuems-editor` calls `get_schema_descriptor` from an executor thread pool, so two threads can
miss on the same key at once. Under the GIL, `dict.get` and dict assignment are each atomic.
The worst case is that both threads build the descriptor, both store an equal value, and the
second store wins. Every caller still receives its own copy. No lock is needed, but the
docstring must say why, so nobody adds one later.

### 4.5 Docstrings that change

- `TypeDescriptor.instance`: add that **each call returns an independent copy**, so a caller may
  mutate it freely.
- `ConfigManager.get_schema_descriptor`: add the same sentence to the G3 bullet list. That
  docstring is the rendered public contract (`cuemsutils.xml` is private).
- `SchemaDescriptor.describe`: state the cache, the copy, and §4.4's reasoning.

## 5. Phases

Each phase ends with the suite green (`uvx hatch run test.py3.11:run -- -q`), ruff at 0 and mypy
at no more than 72.

### Phase 0: a committed measurement

- **T0.1** ✅ Added `tests/support/perf_descriptor.py`. It is run as
  `$PY -m tests.support.perf_descriptor --arm A=<src> --arm B=<src> --rounds N [--jsonl FILE]`
  and, like `capture_goldens.py`, is not collected by pytest. One sample is one fresh process
  that reports, per schema: the warm `types()` median (and min) over `--calls`, the cold first
  call, the node count of all instances, and **how many `_instance_for` calls a warm call
  makes**, which phase 2's T2.5 needs to be zero. The child process imports only stdlib and the
  arm's own `cuemsutils`, so an arm can be any older checkout. It alternates arms round by round
  and refuses a sample whose `cuemsutils.__file__` is not the arm's.
  - On pre-015 trees `_instance_for(key, branch)` was recursive, so its call count includes the
    recursion and is not comparable across that line.
- **T0.2** ✅ Interleaved A/B, A = a throwaway `git worktree` at 015's branch point `75a958e` and
  B = `9d2f337`, with 16 samples per arm across three windows. Results in §2.6. Keep the A
  worktree, or recreate it at the same commit, for phase 3.
- **T0.3** ✅ The probe reproduces 015's fast-state 1.06 → 2.83 ms (here 1.052 → 2.895 ms). The
  5.7 ms read earlier was the same operation in the box's slow state. See §2.5. Acceptance (§6)
  is measured against §2.6's B column.

### Phase 1: pin the invariants before changing anything

These tests are added and **pass on the current tree**. They guard behaviour the cache must not
change.

✅ **Done 2026-10-14.** T1.1–T1.3 are in `tests/contract/test_descriptor_cache.py`, 24 cases,
all green on the uncached tree.

- **T1.1** ✅ `test_instance_leaves_are_immutable_scalars`, parametrised over all six schemas.
  Every leaf has an exact type in `{str, int, float, bool, NoneType}` and every container is
  exactly `dict` or `list`. This is §2.3's measurement, made permanent.
- **T1.2** ✅ `test_a_returned_instance_is_independent` (through `types()`) and
  `test_a_described_instance_is_independent` (through `describe()`). Every container is mutated
  innermost first, so a shared nested dict is caught as well as a shared top-level one.
  - **Proven able to fail.** A naive cache that returns the cached object uncopied was
    monkeypatched in. In its first draft the `describe()` guard **passed** against it: an earlier
    test had already vandalised the shared objects, so its "before" snapshot was vandalised too,
    and before == after. The guards now also assert that a marker string (`_MARK`) never appears
    in a fresh result, which catches a leak from any earlier test. Both guards fail against the
    naive cache in either order. Re-run this check if either guard is ever edited.
- **T1.3** ✅ `test_repeated_calls_are_equal`. Two calls return equal tuples (`TypeDescriptor`
  equality) for every schema.
- **T1.4** ✅ Snapshot of all six schemas' instances as canonical JSON (`sort_keys=True`,
  `indent=1`, `[[str(key), instance], …]` per schema): 32,978 bytes, **sha256
  `08cf6074cbc5d3c2208e5a9f12bf54a37ebd4557af311898a81a8f175788def3`**. It is deterministic,
  with the same hash across processes and `PYTHONHASHSEED` values, so the hash alone is the
  phase 2 check.
- **T1.5** ✅ **No test needs `descriptor.clear_cache()`.** Tests call only `spec.clear_cache`
  (`test_spec_cache.py`, `test_spec_derivation.py`, to count derivations) and
  `coercion.clear_cache`, and none of them then reads the descriptor. The tests that combine
  `monkeypatch` with the descriptor patch only `CUEMS_CONF_PATH` or validators. The cache also
  has **no environment input**: `schema.get_schema` reads the package's own `schemas/`
  directory through `SCHEMAS_DIR`, never `CUEMS_CONF_PATH` or `/etc/cuems`, so a key of
  `TypeKey` alone is complete.

### Phase 2: the cache

✅ **Done 2026-10-14**, uncommitted on top of `9d2f337`.

- **T2.1** ✅ `_described_cache`, `_SCALAR_LEAVES`, `_copy_instance` and `_assert_scalar_leaves`
  in `xml/descriptor.py`, beside `clear_cache()`.
- **T2.2** ✅ `describe()` is the cache. The old body is `_describe_uncached()`, and `types()` is
  untouched. The docstring carries §4.4's no-lock reasoning, written beside the code so nobody
  adds a lock later.
- **T2.3** ✅ `clear_cache()` empties `_described_cache`. Per T1.5, no existing test needed it.
- **T2.4** ✅ `test_the_cache_rejects_a_mutable_leaf` monkeypatches a `CTimecode` into
  `MediaType`'s instance and requires a `TypeError` that names `script:MediaType`, the type and
  the path `$.duration`.
- **T2.5** ✅ `test_the_cache_is_hit`: after one `types('script')`, a second call makes **zero**
  `_instance_for` calls. Both new tests use a fixture that clears the cache before and after,
  so a monkeypatched build never outlives its test.
- **T2.6** ✅ The snapshot hash **matches** T1.4's `08cf6074…88def3` byte for byte. Full suite:
  **3750 passed** (3724 + 26 new), 115 skipped, 2 xfailed. That includes
  `test_golden_immutability`, so `MANIFEST.sha256` is unchanged, and
  `test_descriptor_laziness.py` (T3.2). ruff 0, mypy 72.
- **Default sharing, measured rather than asserted (§4.1):** of the 327 `FieldDescriptor`
  defaults, the only mutable one is `CueListType.contents` (a `list`). It **was already the same
  object on every call before the cache**: `a.default is b.default` across two uncached
  `types()` calls. `FadeCueType.curve_type`'s `FadeCurveType` is an enum member. So the cache
  shares nothing in `fields` that was not shared before.

### Phase 3: measure, then fix the budget record

- **T3.1** ✅ Run 2026-10-14 11:19–11:31 with the same interpreter and probe as §2.6. A = a
  worktree at `9d2f337` (no cache); B = the working tree with phase 2. 16 samples per arm in
  three windows, five minutes apart, interleaved; load 1.03–2.21.

  | schema | A: `9d2f337`, warm ms | B: cached, warm ms | B/A | speedup | `_instance_for` per warm call A → B |
  |---|---|---|---|---|---|
  | script | **2.850** [2.813–2.965] | **0.165** [0.162–0.186] | **0.058** | **17.2×** | 34 → **0** |
  | project_mappings | 1.384 [1.369–1.481] | 0.093 [0.092–0.097] | 0.067 | 14.9× | 16 → 0 |
  | settings | 0.677 [0.665–0.692] | 0.040 [0.039–0.059] | 0.059 | 17.0× | 10 → 0 |
  | network_map | 0.201 [0.198–0.204] | 0.014 [0.013–0.016] | 0.069 | 14.5× | 3 → 0 |
  | project_settings | 0.068 [0.064–0.073] | 0.008 [0.008–0.010] | 0.121 | 8.3× | 2 → 0 |
  | hardware_outputs | 0.082 [0.078–0.092] | 0.012 [0.012–0.015] | 0.145 | 6.9× | 3 → 0 |

  - **A6 met.** `script` reads 0.165 ms against the ≤ 1.22 ms budget (7.4× under) and is
    **6.4× faster than before 015** (1.052 ms, §2.6). The B/A ratio was 0.058 in every window,
    under the ≤ 0.1× expected for `script` and `project_mappings`. A's column matches §2.6's B
    column to within 2% (2.850 against 2.895), so the control arm is the same tree measured
    twice.
  - **The cold first call did not move** (`script` 258.7 ms A, 264.8 ms B, within this probe's
    run-to-run spread). The ratio is smaller for the two tiny schemas because the copy and the
    `dataclasses.replace` per type are a fixed per-call floor of a few µs.
  - **The prototype predicted 21× (§2.2) and the result is 17×, and the gap is measured.** The
    prototype cached the whole tuple per schema. The real cache works per `TypeKey` inside
    `describe()`, so `types()` still lists, sorts and hashes 34 keys on every call. Breakdown of
    one warm `types('script')` at 0.163 ms (median of 2000):

    | part | ms |
    |---|---|
    | copying the instances | 0.095 |
    | 34 `dataclasses.replace` | 0.033 |
    | listing the keys | 0.017 |
    | 34 cache lookups | 0.010 |

    The last two rows (0.027 ms) are exactly what the prototype skipped: its fast-state 0.136 ms
    plus 0.027 is 0.163. A per-schema tuple cache on top would recover them, but the gain is
    0.03 ms against a 7× budget margin. **Not done.**
- **T3.2** ✅ `test_descriptor_laziness.py` passes in the full suite run of T2.6. Its first call
  in a fresh process is a cache miss on both paths, as predicted.
  - ⚠ **Pre-existing flake found on the way, not caused by this plan.**
    `test_no_individual_schema_regresses_where_it_is_measurable[project_mappings]` fails
    intermittently. It compares the first call on the public and internal paths, each in one
    fresh process, within 110%, and `project_mappings` costs only about 2 ms there, just above
    the test's own 1 ms `_MEANINGFUL_MS` floor. Measured as 12 runs per tree, interleaved, each
    tree running its own tests against its own `src`: **2 of 12 runs failed on `9d2f337`
    without the cache** (one of them failing two cases), **1 of 12 with it**. Not fixed here;
    the likely remedy is the test file's own precedent of raising the floor or comparing a band.
    Carried in `CLAUDE.md` (phase 5) so it has an owner.
- **T3.3** ✅ **No suite regression.** The same test set, this checkout's `tests/`, was run
  against each tree's `src` via `PYTHONPATH` (verified to take precedence over the editable
  install), with `test_descriptor_cache.py` deselected in both arms because its cache tests
  cannot pass without the cache. Same interpreter, interleaved A, B, A, B:

  | run | A: `9d2f337` | B: cached |
  |---|---|---|
  | 1 | 32.94 s, 8.85 ms/test | 32.09 s, 8.62 ms/test |
  | 2 | 31.93 s, 8.57 ms/test | 32.06 s, 8.61 ms/test |

  All four runs passed 3724 tests. The ±2% difference is noise: the suite builds each schema's
  descriptor only a handful of times, so the cache saves a few tens of ms in total. B's second
  run reads 3725 passed / 114 skipped because one laziness case crossed its 1 ms floor and ran
  instead of skipping, which is timing-dependent by design.
  - One harness caveat: `test_descriptor_laziness.py`'s subprocesses put `src` on their own
    path, so in arm A those two probe processes measured B's code. They take about the same time
    in both arms.

### Phase 4: docstrings and the consumer note

✅ **Done 2026-10-14.**

- **T4.1** ✅ The three docstring edits in §4.5: `describe()` (cache, copy, no-lock reasoning),
  `TypeDescriptor.instance` (each call returns an independent copy), and a new fifth bullet in
  `ConfigManager.get_schema_descriptor`'s rendered G3 contract.
- **T4.2** ~~Re-cut `tests/golden/api/public_api.json` if it captures the docstring.~~
  **Not needed, verified 2026-10-14**: that golden pins signatures only, and
  `test_public_api_surface.py` states "Not captured: docstrings and source". The docstring
  change is visible only in the mkdocstrings-rendered `docs/` page for `ConfigManager`, which
  `test_public_docs_coverage.py` checks for presence, not content. No golden moves in this plan.
- **T4.3** Consumer note for `cuems-editor`. This is not a change to that repository. Its
  `_root_instance` builds every type in a schema to read one root, and both it and
  `schema_descriptor_value` round-trip each instance through
  `json.loads(json.dumps(..., default=_json_safe))`. After this plan, a warm `script`
  descriptor costs about 0.165 ms (T3.1). The round trip is still useful for `_json_safe` on
  keys and fields, but it is **no longer needed for isolation**. It is optional, and nothing
  blocks on it.
  - ✅ **Handed over through the release notes**: `CHANGELOG.md`, `0.1.1 — Unreleased`,
    "Changed — `get_schema_descriptor` is cached…". Nothing was written into `cuems-editor`
    itself; a note in that repository's own planning folder is the maintainer's call.

### Phase 5: record the result and delete this plan

- **T5.1** Add a "Recent Changes" entry to `CLAUDE.md`: the mechanism (§2.1), the decision
  (cache plus structural copy, with the leaf invariant enforced when the cache is filled), the
  measured before/after with interpreter and box state, and a line saying that 015's recorded
  exception for descriptor derivation is now cleared or still open, whichever §6 shows.
- **T5.2** **Do not edit `specs/015-consumer-gate-closure/baseline.md`.** Landed feature specs
  are frozen record (`CLAUDE.md`). The correction belongs in `CLAUDE.md`, the same way 014 and
  015 recorded corrections to earlier features.
- **T5.3** **Delete `specs/planning/descriptor-instance-cache.md` (this file) in the same commit
  as T5.1.** A planning document whose content is implemented and recorded elsewhere must be
  deleted, not kept.

## 6. Acceptance criteria

| # | Criterion | How it is checked |
|---|---|---|
| A1 | Every instance in all six schemas is byte-identical (canonical JSON) before and after | T1.4 / T2.6 |
| A2 | Every XML and API golden is unchanged, with no exceptions (T4.2) | `MANIFEST.sha256` |
| A3 | A mutated instance never affects a later call | T1.2 |
| A4 | A non-scalar leaf makes the cache fail with a `TypeError` that names the key | T2.4 |
| A5 | A second call does no instance building | T2.5 |
| A6 | Warm `types('script')` ≤ **1.22 ms**, 015's budget, on the phase 0 probe. Against §2.6's B of 2.895 ms, the prototype's 21× predicts about **0.14 ms**: roughly 9× under budget, and below even the pre-015 1.052 ms. **Verdict on the A/B ratio**, A = `9d2f337`'s state before phase 2: expect ≤ 0.1× for `script` and `project_mappings` | T3.1, 16 samples in three windows, A/B interleaved |
| A7 | `test_descriptor_laziness.py` stays green | T3.2 |
| A8 | Suite ms per test ≤ the control arm's in the same session | T3.3 |
| A9 | ruff 0, mypy ≤ 72 | release gates |

If A6 fails on the probe, record it as exceeded in `CLAUDE.md`, as features 012–015 did. Do not
restate it as passing.

## 7. Not doing, and why

### 7.1 A C++ or Rust implementation

Considered and **rejected**.

- **On the warm path, it cannot beat the cache.** `_instance_for` calls back into the Python
  model classes (`model(body)`), coercion, and `Mapper.encode_wire`. A native version would
  either cross the FFI boundary for each of those, which gains nothing, or reimplement the
  model, coercion and encoder layers natively. The second option is a second implementation of
  the wire shape, and G3 exists to prevent exactly that drift (research R2). The result must
  also come back as Python dicts. Building about 633 Python objects through PyO3 or the C API
  costs about the same as the 0.27 ms Python copy. Estimated native warm cost is 0.2–0.4 ms
  against 0.27 ms cached Python: no real gain, and a second implementation to keep in sync.
- **On the cold path, there is no native replacement for what dominates.** The ~490 ms first
  call is xmlschema/elementpath compiling the XSDs. A native replacement would need XSD 1.1
  (`xs:assert`, `xs:alternative`, the reason `xmlschema==3.4.3` is pinned). libxml2/lxml and
  Xerces-C++ support only XSD 1.0. The only native XSD 1.1 implementation known to this plan is
  Saxon's commercial edition (SaxonC-EE), a licensing change for the whole stack. The
  descriptor also reads xmlschema's object model directly (facets, enumerations, member types),
  so replacing the validator would not remove xmlschema.

### 7.2 Memoising subtrees and `_seed_for`

About 3.6× fewer builds, but only on the single cache miss per type per process. Not worth the
extra bookkeeping for the cycle-bounding `seen` branch set, whose results depend on the branch.

### 7.3 Generating the descriptor at build time

The descriptor could be generated during the package build, the way `xml/make_defaults.py`
already generates the default documents, and loaded as JSON (about 0.2 ms for all script
instances). That would also remove most of the cold first-call cost for this path. It trades
the "computed at runtime from the schema" guarantee for a golden-equality test, and it adds a
build artefact that must be regenerated whenever a schema changes. **Only reconsider this if
cold start of the editor's first descriptor request becomes a measured complaint.** If it does,
open a new planning document; do not extend this one.

### 7.4 Lazy `instance`

Rejected in §3: the main consumer reads every instance.

---

> ⚠ **Reminder: delete this file when done.** Task T5.3 is part of this plan, not optional
> cleanup. When phase 5 lands, this document is removed in the same commit that records its
> result in `CLAUDE.md`.
