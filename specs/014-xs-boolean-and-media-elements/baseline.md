<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Feature 014 — baseline and budgets

**Measured before any schema edit**, which is the point: Principle IV wants targets stated before
implementation, and once the schemas move the "before" number is gone. Branch
`014-xs-boolean-and-media-elements`, cut from `feat/xml-refactor` at `84705b9`.

**Method**, identical to 013's so the shapes are comparable: best of 3 medians of 5 warm runs, one
warm call first, fresh process, the method in `tests/integration/test_read_path_regression.py`.

⚠ **Compare within this document, not against 013's absolute figures.** 013 measured
`project_mappings` at 15.153 ms pre-013 and 20.442 ms post-013 on its own run; this box reads
18.292 ms for the same path on the same tree. Machine state differs. Every before/after pair below
is from the same session and is self-comparable; cross-feature deltas are not.

---

## 1. The document load path

| Document | Path | Before | The three medians |
|---|---|---|---|
| `project_mappings` | `tests/data/corpus/cuems-utils/project_mappings.xml` via `load_config_document(ProjectMappings, …)` | **18.292 ms** | 18.292, 18.514, 18.392 |
| `settings` | `tests/data/corpus/cuems-utils/settings.xml` via `load_config_document(Settings, …)` | **14.702 ms** | 14.702, 15.401, 14.781 |
| `script` | `tests/data/corpus/cuems-engine/projects/complex_test/script.xml` via `CuemsScript.load` | **13.338 ms** | 15.195, 14.758, 13.338 |

## 2. The suite

| | Before |
|---|---|
| Result | 3432 passed, 112 skipped, 2 xfailed |
| Wall | **57.66 s** |

Per test: 57.66 s / 3432 ≈ **16.80 ms**. 013 recorded 16.66–16.81 ms/test against a ≤ 18.04 budget,
so this tree starts at the top of that range.

## 3. The descriptor, as it reports booleans today

The "before" of §1.1 of [plan.md](plan.md) — the finding that decided X1:

```
script      ActionCueType  enabled   xsd_type='BoolType'  enum_values=('True', 'False')
network_map NodeType       adopted   xsd_type='BoolType'  enum_values=('True', 'False')
network_map NodeType       online    xsd_type='BoolType'  enum_values=('True', 'False')
```

Structurally identical to `post_go`'s `('pause', 'go', 'go_at_end')`. **After X1 every one of these
must report `enum_values = None`** and a native boolean type — that is the acceptance criterion, not
a hoped-for side effect.

Also recorded as a "before", because 014 does **not** fix it (plan.md §9.5):

```
network_map NodeType  uuid  xsd_type='NodeUuidType'
                            enum_values=('00000000-0000-0000-0000-000000000000',)
```

## 4. Documents carrying old-form booleans

Re-verified on the branch point. The split that makes plan.md's decision 3 cheap:

| | Files | Handled by |
|---|---|---|
| unmarked (version 1) | **51** — utils 28, bridge 10, engine 6, editor 4, common 2, nodeconf 1 | the registry's 1 → 2 step once it carries the rewrite |
| already `doc_version` ≥ 2 | **9 real files** (+17 in gitignored `tests/tmp`) | a one-off rewrite, out of band |

---

## 5. The `get_schema` mitigation — applied, and it is the largest single result in this feature

013 profiled SC-PERF-001's 23% miss, identified this as a contributing cause and **deliberately did
not apply it**, recording it as "the identified one-line mitigation". 014 applies it, because 014
edits the schemas and therefore has to measure them anyway.

**What it was** (`xml/xml_reader_writer.py`, the `schema` setter):

```python
self.schema_object = XMLSchema11(self.schema, converter=self.converter)
```

Every `CuemsXml` instance recompiled the XSD. The configuration path constructs one per call, so
that cost was paid **per load** rather than per process — while `xml/schema.py` already had
`get_schema`, cached on `(name, converter)`, whose own docstring says it is "what makes SC-PERF-002's
*schema load once per process* an implementation fact rather than an aspiration". One call site was
outside that guarantee.

**What it is now:**

```python
self.schema_object = get_schema(name.removesuffix('.xsd'), self.converter)
```

Keyed on *this call's* argument rather than on `self.schema_name` — nothing reassigns the property
today, but reading the attribute would hand a reassignment the previous schema's compiled object,
silently. `self._schema` stays the absolute path: `read()` passes it as `xsd_path`.

### Measured, same session, same method

| Document | Before | After | Change |
|---|---|---|---|
| `project_mappings` | 18.292 ms | **3.690 ms** | **−80%** |
| `settings` | 14.702 ms | **1.646 ms** | **−89%** |
| `script` | 13.338 ms | 13.311 ms | unchanged — `CuemsScript.load` does not go through this setter |

| Suite | Before | After | Change |
|---|---|---|---|
| Wall | 57.66 s | **24.29 / 24.35 / 24.65 s** | **−58%**, three runs |
| Per test | 16.80 ms | **7.08 ms** | −58% |

3432 passed, 112 skipped, 2 xfailed in every run.

**Three things worth stating plainly:**

1. **013's SC-PERF-001 miss is not merely recovered.** That budget was 16.668 ms (110% of a
   15.153 ms pre-013 baseline) and 013 measured 20.442 ms against it. The configuration path now
   loads in **3.690 ms** — roughly a quarter of the *original* pre-013 figure, on a tree that
   carries all of 013's `xs:alternative` machinery.
2. **It does not touch the mechanism 013 identified as dominant.** `elementpath` still builds a
   fresh node tree per `xs:alternative`/`xs:assert` evaluation; that cost scales with document size
   × class-carrying elements and is unaffected. What went away is schema *compilation*, which 013
   described as "a smaller, one-off part". On this evidence the two were the other way round for the
   configuration path — the one-off part was being paid per call, which is what made it the larger
   one.
3. **The suite halving is the same cause, not a separate win.** The suite constructs these readers
   thousands of times.

### Budgets for the rest of the feature

Stated against the **post-mitigation** figures, because that is the tree 014's schema edits land on:

⚠ **Prefixed `SC-014-PERF-` deliberately.** 013's `SC-PERF-001` is the mappings load against a
16.668 ms budget and 010's is a suite budget; three features are live at once and a bare
`SC-PERF-001` now means three different things. These are **feature-local and supersede nothing**.

| Criterion | Budget | Rationale |
|---|---|---|
| **SC-014-PERF-001** | `project_mappings` load ≤ **4.06 ms** (110% of 3.690) | the shape 013 used, re-based |
| **SC-014-PERF-002** | ≤ **7.79 ms/test** (110% of 7.08) | the suite |
| **SC-014-PERF-003** | `script` load ≤ **14.68 ms** (110% of 13.338) | unmoved by the mitigation, so it is the honest reference for the show path |

X1 removes three `simpleType` declarations and retypes five elements to a built-in, which should if
anything help: a built-in needs no facet checks. **If any of these three is exceeded, it is recorded
as exceeded rather than restated as passing**, per Principle IV and this repository's practice
across 006, 008, 012 and 013.

---

## 6. The three budgets, validated after Phase 3 (T026)

**Measured 2026-10-05**, after Phases 1–3, same method as §1 (best of 3 medians of 5 warm runs,
one warm call first, fresh process). Three independent runs of each, because two of the three land
*at the line* and a single run would have picked an answer rather than measured one.

| Criterion | Budget | Measured (3 runs, best-of-medians) | Verdict |
|---|---|---|---|
| **SC-014-PERF-001** | `project_mappings` ≤ 4.06 ms | **4.066 / 4.150 / 4.409** | ⚠ **EXCEEDED** by 0.1–8.6% |
| **SC-014-PERF-002** | ≤ 7.79 ms/test | **7.30 / 7.12 / 7.16** (3565–3566 tests in 26.02 / 25.39 / 25.53 s) | ✅ **MET**, 6–9% under |
| **SC-014-PERF-003** | `script` ≤ 14.68 ms | **14.682 / 14.982 / 15.316** | ⚠ **EXCEEDED** by 0.01–4.3% |

`settings` carries no budget and is recorded anyway: **1.983 / 2.013 / 2.032 ms** against §5's
1.646 ms "After".

### 6.1 The two overruns are the instrument, and that is measured rather than argued

Recorded as exceeded above, per Principle IV. But "exceeded" is not the same as "this feature made
it slower", and the control arm separates the two. **The same three measurements were taken, in the
same session, on `2cc5506`** — the commit that applied the `get_schema` mitigation and *nothing
else*, i.e. the exact tree §5 measured at 3.690 / 1.646 / 13.311:

| Path | §5's recorded "After" | `2cc5506`, **re-measured today** | `e295289` (Phase 2) | HEAD (Phase 3) |
|---|---|---|---|---|
| `project_mappings` | 3.690 ms | **4.049 / 4.118 / 4.172** | 4.036 / 4.089 / 4.144 | 4.066 / 4.150 / 4.409 |
| `settings` | 1.646 ms | **1.947 / 1.978 / 2.019** | 1.943 / 1.951 / 2.062 | 1.983 / 2.013 / 2.032 |
| `script` | 13.311 ms | **14.456 / 14.852 / 14.994** | 14.639 / 14.927 / 14.967 | 14.682 / 14.982 / 15.316 |

**The pre-edit tree does not reproduce the numbers the budgets were derived from.** `2cc5506` reads
4.05–4.17 where §5 recorded 3.690, and 14.46–14.99 where it recorded 13.311 — so
SC-014-PERF-001 is already exceeded *by the tree it was calibrated on*, before a single schema byte
moved. The three arms are mutually indistinguishable: every path's three-run band overlaps every
other arm's.

So the mechanism is **session and machine state**, which is exactly what §1's own ⚠ warns about one
level up (*"Compare within this document, not against 013's absolute figures… Machine state
differs"*). What this feature adds to that warning is the measured consequence: **a 110%-of-baseline
budget is below this instrument's resolution.** The run-to-run spread on a single unchanged tree is
±4–8%, so a 10% headroom cannot distinguish a regression from a quiet afternoon. 013 hit the same
wall from the other side when it had to say *"compare within this document"*; 014 is the feature
where the budget shape itself is the finding.

**No mitigation applied, and none is indicated** — there is nothing measured to mitigate. The
honest statement of the overrun is: *both budgets are exceeded, by a margin smaller than the
measurement noise, on a tree where the pre-change control is also exceeded by the same margin.*

**Phase 3 contributes nothing measurable**, which is the one thing these runs do resolve cleanly:
`e295289` and HEAD are indistinguishable on all three paths, and the only hot-path line Phase 3
adds is one `is not None` test per repeated configuration member in `_decode_config_item`.

## 7. The descriptor after X1 — helped, hurt, or neither? (T027)

**Neither.** The predicted flat result, and now measured rather than predicted.

Cold build in a **fresh process** per measurement (the descriptor's `derive` is `lru_cache`d, so an
in-process repeat measures the cache), three processes per schema, same session, HEAD against
`2cc5506`:

| Schema | Complex types | `2cc5506` cold | HEAD cold | HEAD warm |
|---|---|---|---|---|
| `script` | **34** (unchanged) | 228.5 / 233.9 / 236.2 ms | **230.7 / 233.6 / 235.3 ms** | 1.08–1.54 ms |
| `network_map` | **3** (unchanged) | 106.0 / 108.6 / 109.1 ms | **106.1 / 106.9 / 107.2 ms** | 0.066–0.067 ms |
| `settings` | **10** (unchanged) | 122.6 / 133.9 / 134.8 ms | **122.9 / 124.4 / 135.2 ms** | 0.249–0.338 ms |

Every band overlaps. Removing three `simpleType` declarations and retyping five elements to a
built-in changed neither the build time nor the **number of described types** — correctly, since
the descriptor describes *complex* types and a `simpleType` was never one of them.

**Why flat is the right answer and not a disappointment.** The hypothesis in §5's budget table was
that a built-in *should if anything help*, because it needs no facet checks. The facet checks it
removes are three enumeration pairs on five elements — and 013 profiled the dominant cost as
`elementpath` building a **fresh node tree over the document per `xs:alternative` or `xs:assert`
evaluation**, which scales with document size × class-carrying elements. **This feature does not
touch that mechanism at all.** A flat result is therefore the prediction confirmed, not a missing
win: there was no facet cost large enough to see next to a per-evaluation tree rebuild.

**What did move, and it is the one X1 result worth stating in performance terms**: three of the four
residual type divergences in `test_construction_parity.py`'s `opaque_dmx` group closed with no code
aimed at them, because `xmlschema` decodes `xs:boolean` to a Python `bool` itself and the missing
`OPAQUE_TYPES` recursion never had to reach the value (T017 ⚠(a)). That is correctness, not speed,
and it is free.

### 7.1 The descriptor's reported types — the acceptance criterion from §3

§3 recorded the "before": `adopted`, `online` and `enabled` each reporting
`xsd_type='BoolType'` with `enum_values=('True', 'False')`, structurally indistinguishable from
`post_go`'s genuine three-value enumeration. **All five fields now report `enum_values = None` and
a boolean type**, asserted in `tests/integration/test_xs_boolean.py` (T018) rather than inspected
here.

§3's second "before" — `NodeUuidType` reporting as an enumeration of one value — is **unchanged and
deliberately so** ([`plan.md`](plan.md) §9.5): fixing it needs the descriptor to learn about union
types, which has no other driver in this feature. It is carried in
`../planning/upcoming-feature-requirements-2026-10-02.md`.

---

## 8. The sibling gates, per repository (T033 — **partial**, two of five)

**Two gates have landed and reported.** Three have not run. T033 is recorded as partial rather than
held back, because *"a sibling left red with the reason named is a result; a sibling not run is
not"* — and the two that ran deserve their record now.

The prompt the gate sessions work from is
[`../planning/feature-014-sibling-gate-prompt.md`](../planning/feature-014-sibling-gate-prompt.md).

| Repository | Gate | Arm A (pre-014) | Arm B (library moved) | Arm C (converted) | State |
|---|---|---|---|---|---|
| `cuems-editor` | T032 | 154 passed / 2 skipped / 1 xfailed | **5 failed / 149 passed** | 154 / 2 / 1 → **161 passed / 2 skipped** after its T059 | ✅ **green** |
| `cuems-nodeconf` | T030 | 32 failed / 142 passed | **33 failed / 141 passed** | 32 failed / 142 passed → **174 / 174** after an independent 013 fix | ✅ **green** |
| `cuems-engine` | T028 | — | — | — | not run |
| `cuems-power-bridge` | T029 | — | — | — | not run |
| `cuems-common` | T031 | — | — | — | not run |

Arm counts for the two landed gates are **as those repositories measured them**, in their own
environments, and are attributed rather than re-derived — `cuems-nodeconf`'s suite needs `zeroconf`,
which this repository's test environment does not carry, so re-running it here is not possible.
What *was* independently verified here is every claim either report makes **about this repository's
code**; see below.

### 8.1 `cuems-editor` — T032, and UR-5 closed in the same session

`8f8b46e` (the gate), `365d57f` (T059), `d6fa83b` (`project_uuid` on the wire), `22093fd` (reports).

**Arm B was 5 failed / 149 passed — exactly the figure the gate prompt forecast**, which is worth
recording because the forecast was the point of including it: a session can tell a surprise from the
expected. One retired premise (`test_node_merge.py::test_merged_nodes_carry_the_string_wire_form`)
plus four in `test_project_payload.py`.

- **Two `network_map.xml` fixtures converted** with `cuems-convert-documents`.
- **`script_minimal.xml` left old-form, for the right reason** — refused for its **pre-013 device
  shape**, not for a boolean. That is precisely the distinction T032 asked be checked rather than
  assumed, and the report makes it explicitly.
- **`script_minimal_013.xml` left untouched** — no `doc_version`, so the library converts it 1 → 2
  in memory on load. Correct, and a document the tool would also have converted; leaving it
  exercises the on-read path instead.
- **The retired premise was inverted, not deleted**, and `test_project_payload` gained a **fifth
  sanctioned delta (e)**: `autoload`/`enabled`/`timecode` are JSON booleans rather than
  `"True"`/`"False"`. Note what that means for 010's count — this feature adds a fifth to the four
  payload deltas CLAUDE.md records.
- **UR-5 is closed**, pinned to `429f8d2` in that repository's own report, and the
  `xfail(strict=True)` is **removed**. §3.1 of
  [`migration-guide.md`](migration-guide.md) predicted the ~6 lines in `config_save` and that they
  were that repository's to write; they were written there, not here.

⚠ **One new upstream report, and it is a real gap**: **UR-6** — `conf_path`/`project_path` refuse the
file a first save would create, so a project's *first* `config_save` of
`project_settings`/`project_mappings` cannot resolve a write target. **All three of its claims were
verified here** by test on 2026-10-05, including the pivotal one: `.save()` does *not* require the
path to pre-exist, so the limitation is entirely in the two helpers. Recorded with both candidate
fixes in [`../planning/upcoming-feature-requirements-2026-10-02.md`](../planning/upcoming-feature-requirements-2026-10-02.md) §8.
**Not 014's** — it arrived after this feature's public-surface pass landed.

### 8.2 `cuems-nodeconf` — T030, green, and one finding that outranks the gate

`4d7c91d` (the gate), `61c5705` (an independent 013 fixture fix). Its report is
`../cuems-nodeconf/specs/sibling-gates/014-xs-boolean-and-media-elements.md`.

- **One document converted**: `tests/fixtures/etc_cuems/network_map.xml`. `settings.xml` and
  `settings_sentinel.xml` needed nothing *for 014* — and the report **says so explicitly** rather
  than leaving them unmentioned, which is what T030 asked for.
- **The write-path check was done on bytes, not the object**, as instructed — nodeconf is the one
  sibling whose *output* this feature changes. It extended an existing on-disk assertion
  (`test_an_adoption_between_passes_is_on_disk_after_the_next_pass`) whose regex was pinned to
  `<adopted>\s*True\s*</adopted>`; narrowed to the lowercase form, same guarantee.
- **The one-way door was checked and found to need nothing**: it looked for an upgrade/rollback
  procedure in its own docs that would need the "upgrade the package before nodeconf restarts, no
  rollback after" rule and reports that none exists. A negative result, stated.
- **Two doc corrections**: `CLAUDE.md:25` and
  `specs/001-network-map-object-adoption/quickstart.md:76,80` — both named by §4.1 of the migration
  guide as teaching the retired spelling.

**Arms A and B and C share an identical 32-failure set**, which is the whole value of measuring in
arms: 014 **neither caused nor fixed** it. The cause is **feature 013's device reshape, never
applied to that repository's `settings.xml` fixtures** — which
`specs/013-device-class-reshape/sibling-repository-updates.md` had already named as *"a prediction
for them"* and nobody closed. It closed it locally by hand-rewrite (174/174).

🔴 **The finding that outranks this gate**, and it is this repository's:
**013's `reshape_players` defeats F3's `settings` 1 → 2 conversion.** `reshape_file` reshapes the
tree *before* handing it to `_as_the_load_path_sees_it` — the mechanism 013 built so the two tools
would compose — and `_settings_1_to_2` addresses `audio_cards`/`universes` by their **pre-013 flat
paths**, which the reshape has just renamed. Both `find`s miss, both `continue`, nothing is dropped,
and validation then refuses the document. **Reproduced here in both tool orders** and recorded with
the mechanism, the bounds and the fix to avoid in
[`../planning/settings-reshape-defeats-f3-conversion-defect.md`](../planning/settings-reshape-defeats-f3-conversion-defect.md).

**It is not 014's and it blocks the coordinated tag.** Also worth noting against the sibling's own
framing: its report calls the case *"likely rare in the field"* and the schema history says it is
the ordinary state of any node whose `settings.xml` predates 2026-09-23 — while **this box's live
`/etc/cuems/settings.xml` is a counterexample** (flat-shaped, zero retired fields, reshapes
cleanly), so it is not *every* document either. Both bounds are measured in that record.

### 8.3 A process defect in the gate prompt itself, found by being used

`cuems-nodeconf`'s report §4: `../cuems-utils` was found mid-measurement in a detached `HEAD` at a
commit predating `0.1.0rc14`, because a second sibling session was running its gate against the
same shared checkout and had switched it. Neither repository was at fault — **the prompt was**. Its
arm-A instruction told each session to point the shared tree at `84705b9`, which is a race by
construction as soon as two gates run at once, and the gates are marked `[P]`.

**Corrected 2026-10-05**: the prompt now has each session create its **own detached `git worktree`**
at the branch point, named after the repository so two cannot collide, and says never to move
`../cuems-utils` at all. Verified working. It also now says to report arm A as
`UNAVAILABLE — shared checkout in use` rather than switching the branch anyway, because *"an arm
that silently measured the wrong library is worse than no arm"*.

That nodeconf's session caught it before trusting any result is the reason there is a correction
rather than a wrong record.
