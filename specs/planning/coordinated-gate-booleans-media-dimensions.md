<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Proposal — one coordinated gate: `xs:boolean`, media pixel dimensions, and the curve names

**For:** the team working on `feat/xml-refactor` across `cuems-utils`, `cuems-editor`,
`cuems-engine` and `cuems-frontend`, and the author of
[`media-pixel-dimensions-for-xml-refactor.md`](media-pixel-dimensions-for-xml-refactor.md).

**Date:** 2026-10-02. **Status:** proposal. Every figure below was measured today against
`cuems-utils` `fdfb688`, `cuems-editor` `bf57d95`, `cuems-engine` `1662a99`, `cuems-frontend`
`8a61780`.

**Premise accepted:** a schema version bump on the required files is not an issue for the
coordinated work. Everything here assumes that, and it is what makes the combination cheap.

**It answers the two questions in that document's §8 directly.** Short versions: **(1)** declare the
three fields natively on the refactor branch and cherry-pick only `9c17418`; do not merge the rc15
line. **(2)** Yes, a `script` version step — and X1 is what turns it from optional into mandatory.

---

## 1. `BoolType` → `xs:boolean` (X1): agreed, with one correction to the reasoning

**The conclusion is right and the strongest argument for it is not the adapter.** Machinery does
shrink, but not where "the global machine would shrink" implies, so the ledger is worth stating
honestly before it is used to justify effort.

### 1.1 What genuinely shrinks

| | |
|---|---|
| **`_Bool.to_wire` is deleted** | it inherits `_Passthrough.to_wire` and returns the `bool`. Correct as predicted |
| **Three bespoke `simpleType` declarations are deleted** | `script.xsd:489`, `network_map.xsd:55`, `settings.xsd:155`, replaced by an XSD built-in. That drops `BoolType` from `KNOWN_IDENTICAL_DUPLICATES` (`tests/contract/test_schema_name_overlap.py:82`) and three rows from `test_enum_audit.py` — and it **resolves the dead-type housekeeping item for free**: `settings.xsd`'s copy, declared and referenced nowhere, stops being a decision with a test cost and simply goes |
| **⭐ The descriptor stops lying about booleans** | the real win, and neither of us had counted it. Measured: `enabled` comes back as `enum_values: ('True', 'False')` — *structurally identical* to `post_go`'s `('pause', 'go', 'go_at_end')`. **The descriptor cannot tell a boolean from a two-value string enum**, so any descriptor-driven form renders a **two-option dropdown where a checkbox belongs**, for all five boolean fields. The editor's new `schema_descriptor` action serves exactly this to clients today, and 010's **T031a** commits to verifying the generated forms *"against every restricted enumeration"* — i.e. it would verify the wrong widget as correct. With `xs:boolean`, `enum_values` is `None` and the field is natively boolean |
| **A whole contract surface collapses** | `test_wire_booleans.py`'s entire premise (docstring included), `test_ui_payload_contract.py`'s boolean section, the frontend dual read, the X1 deferral note in three rebuild documents, and the warning paragraph in `adapters.py`'s module docstring |

### 1.2 What does **not** shrink — the correction

- **`_Bool` does not disappear.** Today `to_lexical` needs *no* special case, because
  `str(True) == "True"` is exactly what the XSD wants. `xs:boolean`'s canonical form is
  **lowercase**, so `to_lexical` **gains** a mapping. The asymmetry moves rather than vanishing:
  today `decode` is the odd method out, after X1 `to_lexical` is. Net size of the class: about the
  same.
- **`decode` must stay strict, so `be3e86e` is not made redundant.** `from_json` has no document to
  validate, so the adapter is still T1 on that path and `"banana"` still has to be refused. What
  changes is the accepted set, and it **widens**: `xs:boolean`'s lexical space is
  `true|false|1|0`, so the reader must take four spellings where it now takes two — and `"True"`
  becomes **invalid**, which is the one place this change is not purely additive for a client.
- **A new invariant appears.** `<enabled>1</enabled>` becomes schema-valid. Our writer normalises
  to `true`/`false`, but a hand-edited or third-party document can carry `1`, so
  `to_lexical ∘ decode` stops being the identity on text. That is a test to add, not one to remove.

### 1.3 The conversion is the real cost, and it is mechanical

Boolean elements in XML on disk, measured across the six checkouts:

| Repository | Files | Elements |
|---|---|---|
| `cuems-utils` | 66 | 545 |
| `cuems-engine` | 13 | 85 |
| `cuems-power-bridge` | 10 | 46 |
| `cuems-editor` | 4 | 38 |
| `cuems-common` | 2 | 8 |
| `cuems-nodeconf` | 1 | 4 |
| **total** | **96** | **726** |

Plus every node's live `/etc/cuems` (4 elements on this box) and every project library in the field.
All of it is `True`→`true`, `False`→`false` in two schemas — a registered conversion, which is
exactly what `cuems-convert-documents` exists for.

**One operational note in X1's favour**: `cuems-nodeconf` rewrites `network_map.xml` every 30 s, so
the live map converts itself almost immediately in practice. The same fact shortens the rollback
window to near zero — already recorded as 012's migration guide §9b, and it applies here unchanged.

---

## 2. The combination: **one `script` step carries all three changes**

This is the whole argument for a single gate. Three changes want `script.xsd`; only one of them
needs a conversion; a version step is indivisible.

| Change | Nature | Needs a conversion? |
|---|---|---|
| **X1** booleans → `xs:boolean` | **breaking** — retypes five elements in two schemas | **yes**: `True`→`true`, `False`→`false` |
| **Media pixel dimensions** — `pixel_width`, `pixel_height`, `file_size` | **additive**, three optional elements on `MediaType` | no |
| **`ease_in` / `ease_out`** (`9c17418`, on `main`, **not** on this branch — verified) | **additive**, two enumeration values on `FadeCurveType` | no |

→ **`script` 2 → 3, one step, one registered conversion** (the boolean rewrite), with the two
additive changes riding it at zero extra cost.
→ **`network_map` 2 → 3**, one step, the same boolean conversion.
→ `settings`, `project_mappings`, `project_settings`, `hardware_outputs`: **untouched** (no boolean
is referenced in any of them — `settings.xsd`'s declaration is dead and gets deleted with X1).

**This answers §8 question 2 decisively.** That document asks whether the Media elements justify a
step and notes a bump *"would give an older refactored library a clear `DocumentTooNewError`
instead of 'unexpected element'"*. With X1 in the same release the bump is no longer a judgement
call — X1 requires it — so the Media elements get the clean `DocumentTooNewError` as a side effect
of a decision made for another reason.

`ease_in`/`ease_out` matters more than it looks: a project saved by a `main`-line editor with an
`ease_in` fade **fails T1 on this branch today**, verified by comparing `FadeCurveType` across
`origin/main` and `HEAD`. It is a live divergence, not housekeeping.

---

## 3. The release-line collision, which is the gate's real problem

The media-dimensions plan targets **a different line**: rc15 cut from `main`, the editor on `rc1`,
the engine on PR #22 against `rc_1`, plus XSD-only back-patches for rc14 and `pre_release_1`. The
refactor is rc16 on `feat/xml-refactor`, and nothing ships from it until the coordinated
`xml-refactor-merge-candidate` tag after features 011–014 (D27).

**So the work would otherwise land twice, and the second landing is the expensive one** — rc15's
`MediaXmlBuilder` fix (dict order, empty element for `None`) does not apply to this branch at all,
because the spec-driven writer already orders by schema position and omits absent fields.

**Recommended split**, answering §8 question 1:

| | |
|---|---|
| **Do** | implement the three Media elements **natively on the refactor branch** — three XSD elements, three `DECLARED_DEFAULTS` entries, three setter pairs. Roughly 30 lines, and `§6`'s utils points 1 and 6 are already satisfied by the branch's own machinery |
| **Do** | **cherry-pick `9c17418` alone** for the curve names |
| **Do not** | merge the rc15 line into `feat/xml-refactor`. rc15 is cut from `main`, which does not contain the refactor; the merge drags main's whole divergence and then collides head-on with X1's retype of the same file |
| **Keep separate** | the rc15 release and its back-patches, if the field needs the GO latency fix before the refactor ships. They are a *different product decision* and should not wait on this gate |

---

## 4. Ordering, and the one interaction that bites

A document arriving from the rc15 line at this branch carries **no `doc_version`** (so it reads as
`script` version 1) **and** the pre-013 device shape. Both migrations must run, in this order:

```
cuems-reshape-devices        # device shape — no version step, 013
cuems-convert-documents      # 1 → 2 → 3    — the registry
```

That is the order 013 already established, and the reason is unchanged: reshape-first sees a
version-1 `<duration>`, convert-first sees old-shape cues, and neither order completes if reversed.

**Verified, so it need not be assumed:** `_script_1_to_2` (`xml/versioning.py:173`) touches only
`duration`, `action_type` and `fade_profiles`. It leaves every other `Media` child untouched, so
the three new elements survive 1→2 and then face the version-3 schema — which is the document's own
§6 point 3, confirmed.

The new 2→3 step must therefore be written to be **order-independent with respect to the Media
elements**: it rewrites boolean text and must not care whether `pixel_width` is present.

---

## 5. What I verified in the media-dimensions plan — two confirmations and one correction

The three points it directs at `cuems-utils` §6, checked against this branch:

### ✅ Point 2 is exactly right, and it is the one that would have silently lost data

`CuemsDict.setter` resolves `getattr(self, f"set_{k}")` and `continue`s on `AttributeError`.
Measured:

```python
Media({'file_name': 'a.mov', 'id': '…', 'pixel_width': 1920}).keys()
# -> ['file_name', 'id']        pixel_width is gone, no error
```

So on this branch the three fields need **both** `DECLARED_DEFAULTS` entries **and** `set_<name>`
accessors. A field with one and not the other is dropped in silence. (Note the local irony: that
`continue` carries a long comment explaining that F17 split the lookup from the call so a *broken*
setter could not silently drop a field — a *missing* setter still can, by design, because that is
how undeclared keys are rejected.)

### ❌ Point 1's reading of `Unset` is inverted — and the correction makes the work smaller

The document says the three optional fields *"need a default that emits nothing when absent, unlike
`Unset`, which marks required fields."*

`Unset` **is** that mechanism. From `helpers.py:32`: *"A declared field with **no** default: the key
stays absent rather than present-and-empty"*, and the docstring goes on to name optional schema
fields as the reason it exists — *"`canvas_region` is the clearest case"*. Confirmed at
`CueOutput.py:173`: *"`canvas_region` is `minOccurs="0"` and so defaults to `Unset`"*, and a bare
`VideoCueOutput()` emits no `canvas_region`.

The inference came from `Media`'s own comment — *"All four are required by the schema, so each takes
`Unset`"* — which explains why those four happen to use it, not what it means. **So: declare all
three as `Unset`. Nothing new is needed.**

### ✅ Point 3 confirmed above (§4). Points 5 and 6 confirmed

`9c17418` is on `origin/main` and is **not** an ancestor of `HEAD` — the cherry-pick is real work,
not a no-op. And the spec-driven writer already solves ordering: no `MediaXmlBuilder` fix is needed
on this branch, which is one of the plan's three utils deliverables dropping out entirely.

---

## 6. Per-repository work for the combined gate

| Repository | Work |
|---|---|
| **`cuems-utils`** | `script.xsd` + `network_map.xsd`: retype five elements, delete three `BoolType` declarations, add three `MediaType` elements, cherry-pick the two curve values. `_Bool`: delete `to_wire`, add the lowercase `to_lexical` map, widen `decode`'s literal table to the four lexical forms. `Media`: three `Unset` entries + three setter pairs. Registry: `script` 2→3 and `network_map` 2→3 with one shared boolean conversion. Re-cut the five goldens. Update the contract tests in §1.1 |
| **`cuems-editor`** | **No source change for X1** — it returns `to_wire()` and its FR-012 forbids touching the dict. The media work is its own (probe at upload, DB columns + `ALTER TABLE` migration, fill at save, repair-tool passes), and its branch has not touched those files. **One payload-version bump covers both** wire changes under its FR-047a; version 1 has not shipped, so it is free now |
| **`cuems-engine`** | **Nothing for X1** — zero `to_wire` in shipped source; it holds objects, already `bool`. The media read is `cue.media.get("pixel_width")`, which keeps working whatever the wire does. Its `cue.media` must stay dict-like with `.get()` — noted, and nothing in this gate changes that |
| **`cuems-nodeconf`, `cuems-power-bridge`, `cuems-common`** | **No source change** — objects, not payloads. Fixtures only: 46 + 4 + 8 boolean elements, one conversion run each |
| **`cuems-frontend`** | the only repository doing real wire work, and it is small: drop the `=== 'True'` half at `sequence.component.ts:498`, make `:997` write a native boolean, and `settings.component.ts:176` (`online === true`) **starts working** — today it is permanently false, which disables `canAdopt()` and leaves the Adopt button dead for every node. Fix `:181`'s stale `node_type !== 'NodeType.master'` while in the file (007 renamed it to `node_role`). `autoload`/`timecode` need **nothing**: already written native, never read from the wire. **No change for media dimensions** |

---

## 7. The hazard that is not in any repository

`projects.service.ts:209` and `:217` cache `initial_template` and `initial_mappings` in
`localStorage`; `project-show/video-mixer:94` and `audio-mixer:115` read the cached mappings. A
deploy that changes the boolean form leaves **old-form payloads in browsers that no server can
reach**.

The editor's `payload_version` first frame is the fix: evict when the stored version differs from
the received one. This is the strongest reason to land the gate **inside payload version 1** rather
than after it — and it is an obligation currently owned by nobody (the editor's T061 flagged the
eviction story and left it unassigned).

---

## 8. Open decisions this proposal does not make

1. **Does the rc15 line ship first?** A product call about GO latency in the field, independent of
   this gate. If yes, the back-patches in that plan's §5 stand as written and this branch still does
   its own work.
2. **Does X1 move `script` and `network_map` in the same release, or separately?** Same release is
   simpler to reason about; separately would let the map convert itself (30 s) while the project
   libraries convert on an operator's schedule.
3. **Is this feature 015, or part of 014?** It shares 014's shape (schema change + conversion +
   consumer migration) but none of its content. A separate number keeps 014's `hardware_outputs`
   scope honest.
4. **The frontend's two adoption bugs** (§6) are live on `main`-line behaviour and do not need this
   gate. They could ship now, and arguably should.
