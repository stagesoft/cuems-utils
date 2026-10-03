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
