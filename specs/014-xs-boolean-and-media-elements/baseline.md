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

## 8. The sibling gates, per repository (T033 — **complete, five of five**)

**All five gates have landed and reported.** All five are green. T033 is recorded as partial rather than
held back, because *"a sibling left red with the reason named is a result; a sibling not run is
not"* — and the three that ran deserve their record now.

The prompt the gate sessions work from is
[`../planning/feature-014-sibling-gate-prompt.md`](../planning/feature-014-sibling-gate-prompt.md).

| Repository | Gate | Arm A (pre-014) | Arm B (library moved) | Arm C (converted) | State |
|---|---|---|---|---|---|
| `cuems-editor` | T032 | 154 passed / 2 skipped / 1 xfailed | **5 failed / 149 passed** | 154 / 2 / 1 → **161 passed / 2 skipped** after its T059 | ✅ **green** |
| `cuems-nodeconf` | T030 | 32 failed / 142 passed | **33 failed / 141 passed** | 32 failed / 142 passed → **174 / 174** after an independent 013 fix | ✅ **green** |
| `cuems-power-bridge` | T029 | 55 failed / 221 passed | **55 failed / 221 passed** — identical set, confirmed by diff | **276 / 0** | ✅ **green** |
| `cuems-common` | T031 | 104 / 104 | **102 / 104** — both on `network_map.xml.example`, exactly as forecast | **104 / 104** | ✅ **green** |
| `cuems-engine` | T028 | **UNAVAILABLE** — coupled to 012 from `c31734c`, as `tasks.md` foresaw | **70 failed / 827 passed / 26 errors** | **1 failed / 922 passed** — its own pre-existing baseline | ✅ **green** |

Arm counts for the three landed gates are **as those repositories measured them**, in their own
environments, and are attributed rather than re-derived — `cuems-nodeconf`'s suite needs `zeroconf`,
which this repository's test environment does not carry, so re-running it here is not possible.
What *was* independently verified here is every claim each report makes **about this repository's
code**; see below.

### 8.0 All five in: **014 broke eight tests; 183 were already broken**

| Repository | Failures attributable to 014 | Attributable to 013, pre-existing |
|---|---|---|
| `cuems-engine` | **0** — all 96 were the pre-013 device shape | **96** |
| `cuems-power-bridge` | **0** — arms A and B identical, diffed | 55 |
| `cuems-nodeconf` | **1** | 32 |
| `cuems-common` | **2** — both on the one document a `*.xml` glob missed | 0 |
| `cuems-editor` | 5 | 0 |
| **Total** | **8** | **183** |

**Eight failures attributable to this feature across five repositories, against 183 that were
already there.** Arm A is what separates them, and without it `cuems-engine` and
`cuems-power-bridge` would between them have reported **151 failures against this feature, every one
of them someone else's.** That is the clearest vindication of the three-arm method the gates could
have produced, and it is the single most useful number this feature measured.

🔴 **The counterpart, and it is the cross-cutting finding of the whole gate round: 013's device
migration was never completed in *three* of the five siblings** — `cuems-nodeconf`,
`cuems-power-bridge` and `cuems-engine`. `specs/013-device-class-reshape/sibling-repository-updates.md`
left them as *"a prediction for them"*; the prediction was right in all three and nobody closed it,
so **014's gates paid the debt**: 11 `settings.xml` hand-rewritten plus five documents reshaped in
`cuems-engine`. Each gate reported that work separately from 014's, which is the only reason the
attribution table above is possible.

**The lesson for 015**: a feature that reshapes documents must close its sibling fixtures *in that
feature*, or the next feature's gates discover it — and the next feature's signal is buried under it
until they do. 013 measured `cuems-engine` in three arms and did exactly this correctly for *that*
repository; what it did not do is run the other two, and it said so.

The counterpart finding: **013's sibling migration was never completed**, and two gates have now
had to do it. `specs/013-device-class-reshape/sibling-repository-updates.md` left
`cuems-power-bridge` and `cuems-nodeconf` as *"a prediction for them"*; the prediction was right and
nobody closed it, so 014's gates closed it — 11 settings documents hand-rewritten between them. That
is a cross-feature debt pattern worth naming before 015 inherits it.

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

### 8.3 `cuems-power-bridge` — T029, green, and the cleanest arm pair of the three

`dd1256f`, GPG-signed. **Arms A and B are identical, confirmed by diffing the failing-test sets** —
so 014 caused **zero** failures here. Arm C is **276 / 0**, which restores the green state its
CLAUDE.md records as predating 013.

- **8 of 10 `network_map.xml` converted by the tool**: `map-{controller-only,mixed,no-self,no-settings,none-adopted,partial-resolve,two-adopted,unresolvable}`.
- ⚠ **2 of 10 left old-form by design, and this repository's §4.1 did not say so.**
  `map-incomplete` exists to test `NETWORK_MAP_INVALID` (a missing required `<mac>`) and
  `map-pre007` to test `NETWORK_MAP_RETIRED_VOCABULARY` (an old `<node_type>`) — verified in
  `tests/test_network_map_adapter.py:171,173`. **The tool correctly refused both**, and converting
  them would have defeated the fixtures' own purpose.
- **No source change**, and the report says how it established that: it grepped `src/` for the wire
  literals and found none. A negative result with its method stated.
- **No retired premises** — it holds objects throughout and never asserted on the lexical form.

**The general rule those two fixtures establish**, which is better than the enumeration §4.1
attempted: **a fixture whose purpose is to be refused must keep the form it is refused for.** Three
instances across two repositories now — `cuems-editor`'s `script_minimal.xml` (refused for its
device shape) and these two. §4.1 named the editor's because that repository's own README did; it
could not have named power-bridge's without reading its tests, which is exactly why the gate belongs
in the repository and not here. **The check is "is this document refused for the reason it was
written to test?", not "is it converted?"**

### 8.4 `cuems-common` — T031, green, and it found a property of *this* repository's tool

`e595e67`. Arms **104 / 104 → 102 / 104 → 104 / 104**, and **both arm-B failures were on
`etc/cuems/network_map.xml.example`** — the document §4.1 was corrected on 2026-10-04 to name, and
the one a `*.xml` glob misses. The forecast said *"at least one certain failure, the `.xml.example`
validated raw"*; it was exactly that and nothing else.

- **2 documents, 2 test modules, 3 doc files.** `tests/fixtures/maps/converted.xml` by tool; the
  example **hand-rewritten**; inline literals in `test_network_map_conversion.py` and
  `test_controller_resolution.py`; and `CLAUDE.md`, `docs/node-identity-contract.md`, `README.md`
  where doc tables quoted `True`/`False` as the literal wire form.
- **No source change**, with the reason given: that package holds no objects, only text and scripts
  that pass the value through unexamined.
- **Confirmed both corrections this repository made to T031's task text**: no stale schema mirror
  (`debian/postinst:173` installs this repository's own copy), and `debian/postinst`'s
  `node_type`→`node_role` step is unaffected because it never touched booleans.
- ⚠ **It corrected one of my own warnings.** §4.1 said to convert `tests/fixtures/maps/{converted,
  unconverted}.xml` *"both sides or neither"*, on the assumption they were the input/expected pair
  of `test_network_map_conversion.py`. **They are not** — both are orphaned, no test references
  either — so it converted one and deliberately left `unconverted.xml`, which predates the
  `node_type`→`node_role` migration and was never schema-valid regardless of boolean spelling. The
  *inline* literals were the real work. Corrected in §4.1.

🔴 **The finding, and it is about a tool this repository ships**: **`cuems-convert-documents`
silently destroys every XML comment.** That gate hit it on its annotated example, hand-rewrote
instead, and reports it *"nearly ran over a doc file unattended"* — which is the right warning to
take from it. Measured here afterwards: the example goes **10 comments → 0 and 40 lines → 24**, with
no warning and exit 0. `cuems-reshape-devices` does the same; both write through `write_tree`, i.e.
stdlib `ElementTree`, which drops comment nodes on parse.

**Scoped here, because the report bundled a benign item with the serious one:**

| | |
|---|---|
| XML comments | 🔴 **destroyed**, silently |
| Indentation / whitespace | ✅ **preserved** — it is text. The 40 → 24 is exactly the 16 comment lines |
| `xsi:schemaLocation` | ✅ **preserved**, verified on a corpus document carrying one |
| `xmlns:xsi` with nothing using it | ⚠ dropped, and **harmless** — an unused namespace declaration carries no information |

T031 reported the `xmlns:xsi` drop beside the comment loss as one finding. Both observations are
correct; only the first is a problem, and separating them is what keeps the warning actionable
rather than alarming. **The one thing to protect is the comments.**

It is **not new** and **not 014's**, but 014 is the first release note instructing operators to run
the tool over **live** files, and `/etc/cuems/network_map.xml` is a `dpkg` conffile operators edit.
After a conversion pass the `.bak` is the only copy of their comments, and nobody reads a `.bak`.
**Undocumented and untested** — no test asserts preservation *or* loss, so nothing would catch it
moving either way. Recorded in [`migration-guide.md`](migration-guide.md) §4.1 and §4.3 with the
warning; a pinning test is for whoever decides the behaviour, not for 014.

### 8.4a One correction to that report — the arm-A commit it names

Its arm A was taken at `cuems-utils@c02f35c`, described as *"the true 014 branch point —
013-device-class-reshape's tip"*. **`c02f35c` is 013's landing commit; the 014 branch point is
`84705b9`** (`git merge-base 014-xs-boolean-and-media-elements feat/xml-refactor`), and **14 commits
separate them**.

**Its arm A is still sound**, and the reasoning that got it there was right — it rejected
`main` because that branch sits 224 commits behind and predates feature 007, which would have been a
useless baseline. For *that* repository the two commits are equivalent: it carries no
`import cuemsutils` at all, its tests validate against the XSD directly, and **none of the 14
commits touches a schema** (verified).

**But it would not be equivalent for `cuems-engine`**, the one gate still open, and that is why this
is worth writing down. `be3e86e` — the strict `_Bool.decode` — is among those 14. It is **S1 in
`tasks.md`'s "Already settled — do not redo"** precisely because it is a *precondition* rather than
part of 014's diff. An arm A taken at `c02f35c` folds S1 into the measured delta and would report a
behaviour change this feature did not make. The gate prompt names `84705b9`; §8.5's worktree
instruction is the mechanism for reaching it without moving the shared checkout.

### 8.5 `cuems-engine` — T028, green, and the ordering case §4.5 did not cover

`9fce7e6`. **Arm A unavailable**, exactly as `tasks.md` foresaw — this repository is coupled to
feature 012 from `c31734c` onward (`coerce_identity` does not exist before it), so there is no clean
pre-012 comparison point. The task said *"design the comparison **before** a run goes red"*, and the
gate did: it attributed arm B by **error type** instead, reporting all 96 as
`cuemsutils.errors.SchemaError` for the pre-013 device shape and **zero** for the boolean. That is
the right substitute for a missing arm and it is why this row can still claim **0 attributable to
014** without the usual diff.

- **Seven documents converted**: four by tool, **three by hand** — `dev/network_map.xml` and
  `dev/test_xml_files/script_one_cue_in_a_cuelist.xml` (blocked by finding 2 below) and
  `complex_test_v2/script.xml` (§4.2's already-version-2 case, which **T015 had claimed and missed**
  and this repository's §4.2 recorded as outstanding — **now closed**). All seven verified case-only
  before and after write, which is the discipline T015 used here.
- **No source change**, and it confirms §2.1's claim about the media block: `MediaType`'s four new
  optional elements are correctly ignored. *"An engine that ignores it is correct"*, asserted by a
  suite rather than by the guide.
- **Still red: one test**, `test_project_go.py::test_project_go_from_controller` — a `TimeoutError`
  with `[ERR] libmtcmaster thread scheduling error`, reproducing standalone. **Environment, not 013
  or 014**, and it matches this repository's own recorded `1 failed / 922 passed` baseline. Reported
  with the attribution rather than left ambiguous.

🔴 **The finding worth the most, and it is a gap in this feature's own release note**: §4.5
documented *one* migration order (reshape → convert), and there is a third case it does not cover.
`complex_test_v2/script.xml` is **already `doc_version="2"`, carries old-form booleans *and* is old
device shape** — and reshape-first fails:

```
skipped (would not validate: failed validating 'False' with XsdAtomicBuiltin(name='xs:boolean'))
```

**Reproduced here.** The mechanism is §4.2 in operational form: reshape validates *as the load path
will see it*, which applies any **registered** conversion — and a document already at the current
version has none, so its booleans are never rewritten and the current schema refuses them. **The
order that works is booleans by hand first, then reshape**, verified end to end. §4.5 now states all
three orders instead of one.

**Three further findings, each correctly scoped by the gate itself:**

| # | Finding | Verdict |
|---|---|---|
| 2 | `dev/network_map.xml` and `dev/test_xml_files/script_one_cue_in_a_cuelist.xml` carry `xmlns:cms="https://stagelab.coop/cuems"` — **missing the trailing slash** — so both tools refuse them outright. Verified; the correct form is `…/cuems/` | **Pre-existing dead weight**, neither file referenced by any test. Same family as audit item **X15**, which recorded a namespace typo in the only out-of-repository `hardware_outputs` instance — so this is the **second** instance of that class and worth folding into whatever cleans up X15 |
| 3 | `projects/complex_test{,_v2}/project_mappings.xml` fail reshape on a `PutType` mismatch (`<output>` with `<name>`/`<mappings>` but no `<id>`) | **Already recorded, and the gate's verdict matches 013's.** CLAUDE.md states it from 013's own pass: *"an `<output>` with no `<id>` and no `<new_nodes>` at all… the branch-point library rejects it too, verified."* Confirmed again here (`grep -c '<id>'` → 0). A correct re-identification, not a new finding |
| 4 | **Third independent confirmation** that `write_tree` drops XML comments: `empty_test/script.xml`'s `<!-- Empty CueList -->` is gone after conversion. Verified, 1 → 0 | Corroborates §8.4's open finding. **Three repositories have now hit it**; that is enough evidence to stop calling it incidental |

### 8.6 A process defect in the gate prompt itself, found by being used

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

**Confirmed working by the next gate, mid-flight.** `cuems-power-bridge`'s session picked up the
corrected instruction and took arm A from *"a disposable worktree at 84705b9"*, reporting it as the
proper practice for parallel sessions. So the fix was validated by use within hours of being
written, by a session that never saw the broken version — and `cuems-power-bridge` produced the one
arm pair in the whole set that is **identical between A and B**, which is only trustworthy *because*
the shared checkout never moved under it.

**The lesson, stated for whoever writes the next cross-repository prompt**: a prompt that tells N
parallel sessions to mutate one shared resource is a defect in the prompt, not in the sessions. It
cost one near-miss, caught only because the session verified its library resolution before trusting
a number — which the prompt also told it to do. Two instructions, one of which saved the other.
