<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Feature 014 — one coordinated gate: `xs:boolean`, media pixel dimensions, and the curve names

**For:** the team working on `feat/xml-refactor` across `cuems-utils`, `cuems-editor`,
`cuems-engine` and `cuems-frontend`, and the author of
[`media-pixel-dimensions-for-xml-refactor.md`](media-pixel-dimensions-for-xml-refactor.md).

**Date:** 2026-10-02. **Status:** **accepted — this is feature `014`**, running the reduced SDD
path (`specs/planning/etc-cuems-first-install-execution.md` §5–§6). Content refinement is in
progress; this document becomes the feature's `plan.md`. Every figure below was measured on
2026-10-02 against `cuems-utils` `fdfb688`, `cuems-editor` `bf57d95`, `cuems-engine` `1662a99`,
`cuems-frontend` `8a61780`.

**Settled by the maintainer, 2026-10-02** — these are decisions, not proposals, and the document
below is written to them:

| | |
|---|---|
| **1** | **A schema version bump on the required files is not an issue** for the coordinated work. This is what makes the combination cheap |
| **2** | **The branch stays on rc16.** Every `feat/xml-refactor` change is planned to land **after** the rc15 work, so rc15 ships first and this branch migrates what it leaves behind |
| **3** | **All schema changes land in the *existing, unreleased* 1 → 2 bump.** Nothing has shipped, so there is **no 2 → 3 step** — version 2's *meaning* absorbs X1 before anyone has seen it (§2, and the one consequence measured in §2.1) |
| **4** | **`cuems-engine` absorbs the last fixes.** Expected to merge cleanly for lack of overlap, as that plan's §6 says — but a **thorough review is required**, not a clean-merge assumption (§6.1) |
| **5** | **`script` and `network_map` move together**, in one release — not staged (§2) |
| **6** | **This is feature `014`.** `hardware_outputs becomes real` moves to **015**; the coordinated tag comes after **011–015** |
| **7** | **`cuems-frontend` owns the `localStorage` eviction** — it is the repository that uses the browser machinery (§7) |
| **8** | **Feature 010's requirement changes are being implemented now**, and this gate's requirement changes **fold into that pass** rather than being carried separately (§8) |

**Answers to that document's §8 questions:** **(1)** declare the three fields natively on the
refactor branch and cherry-pick only `9c17418`; do not merge the rc15 line. **(2)** Yes — and it is
the 1 → 2 step already in flight, not a new one.

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

- **`_Bool` does not disappear, and `to_lexical` is the reason.** It is not a stylistic
  preference — deleting the class makes the library unable to write a document at all. Measured in
  full in **§1.3**, because this is the one place where "the machinery shrinks" would do real
  damage if acted on literally.
- **The asymmetry moves rather than vanishing.** Today `decode` is the odd method out and
  `to_lexical` is free; after X1 it is the other way round. Net size of the class: about the same.
- **`decode` must stay strict, so `be3e86e` is not made redundant.** `from_json` has no document to
  validate, so the adapter is still T1 on that path and `"banana"` still has to be refused. What
  changes is the accepted set, and it **widens**: `xs:boolean`'s lexical space is
  `true|false|1|0`, so the reader must take four spellings where it now takes two — and `"True"`
  becomes **invalid**, which is the one place this change is not purely additive for a client.
- **A new invariant appears.** `<enabled>1</enabled>` becomes schema-valid. Our writer normalises
  to `true`/`false`, but a hand-edited or third-party document can carry `1`, so
  `to_lexical ∘ decode` stops being the identity on text. That is a test to add, not one to remove.

### 1.3 `to_lexical` is strictly required, and this is why

The tempting form of "the machinery shrinks" is to delete `_Bool` outright once `BoolType` is a
built-in — `xmlschema` knows `xs:boolean`, so why keep an adapter? Because **`xmlschema` is not in
the write path.** Three measured facts make the class mandatory.

**Where `to_lexical` is actually called.** Exactly one place in the library:

```
src/cuemsutils/xml/mapper.py:946
    def _lexical(self, value, xsd_type):
        text = adapter_for(xsd_type).to_lexical(value)
        return "" if text is None else text
```

and `_lexical` is the **only** producer of element text and attribute values on the write path —
five call sites, all in `Mapper`: `:654` (a scalar bound to an element), `:765` (a list item),
`:861` (element text), `:868` (`element.set`, i.e. every attribute, including 013's `class`), and
`:900` (a child element). `Mapper.build_document` then returns `ElementTree(root)` (`:1186`) and
`documents.write_tree` serialises it with `tree.write(..., encoding="utf-8",
xml_declaration=True)` — **stdlib `ElementTree`** (`documents.py:289`, `:334`).

So the whole chain from Python object to bytes on disk is:

```
object → Mapper._lexical → adapter.to_lexical → Element.text (a str) → ElementTree.write
```

Nothing else in that chain can convert a value. `lxml` is a dependency but **not in the write
path**, and `xmlschema` is used to *validate* the result, never to encode it. If `to_lexical` does
not produce the right text, nothing downstream will fix it.

**Fact 1 — `Element.text` must be a `str`; a `bool` is a hard error.**

```python
e = Element('enabled'); e.text = True
ElementTree(e).write(io.BytesIO())
# TypeError: cannot serialize True (type bool)
```

So the bool→text conversion is not optional at any level. Something must do it, and `to_lexical` is
the only candidate.

**Fact 2 — the inherited default produces the wrong text.** `_Passthrough.to_lexical` is
`str(obj)`, and `str(True)` is `'True'`. That is correct *today*, which is exactly why `_Bool`
currently overrides `decode` and not `to_lexical`.

**Fact 3 — `'True'` is invalid against `xs:boolean`.** Verified against `XMLSchema11`:

| text | valid as `xs:boolean`? |
|---|---|
| `true`, `false`, `1`, `0` | ✅ |
| **`True`, `False`, `TRUE`** | ❌ |

**Put together**: delete `_Bool` and every boolean would be written as `True`, which the schema
rejects. And because `CuemsScript.save` *"runs T1 and T2 and raises at the first failure. On
failure no file is written"* (`CuemsScript.py:509-512`), the result is not a corrupt file — it is
**a library that refuses to save any document containing a cue**. Every save, every node, instantly.
A silent corruption would be worse in principle; this would be worse in practice, because it is
total.

So X1's edit to `_Bool` is a **swap, not a deletion**:

| Method | Today | After X1 |
|---|---|---|
| `decode` | overridden — the strict literal table from `be3e86e` | **still overridden**, table widened to `true`/`false`/`1`/`0` plus `bool` (and `'True'` now *rejected*) |
| `to_lexical` | **inherited** — `str(obj)` happens to be right | **overridden** — `{True: "true", False: "false"}`, and `None` → `None` so an absent optional stays absent |
| `to_wire` | overridden — returns `to_lexical`, the string | **deleted** — inherits `_Passthrough.to_wire`, returns the `bool` |

One override gained, one lost, one rewritten. That is the honest accounting, and it is why §1.2
says the class does not shrink even though the surrounding machinery does.

**Two tests this specifically needs**, because neither exists today:

1. `to_lexical(True) == "true"` *and* the round trip `decode(to_lexical(True)) is True` — the
   second is what catches a half-applied change, where the writer is updated and the reader is not.
2. A full save/load cycle asserting the **bytes on disk** contain `<enabled>true</enabled>`. A unit
   test on the adapter cannot catch a `Mapper` path that bypasses `_lexical`; `:868`'s attribute
   call is the one most easily missed, since 013 made attributes load-bearing.

---

### 1.4 The conversion is the real cost, and it is mechanical

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

**Decision 3 settles where they land: inside the 1 → 2 step already in flight.** Not a new 2 → 3.

`script` is at version **2** on this branch and `network_map` at **2**, both set by features 008 and
012 and **never released**. A version marker nobody outside this branch has seen is still
malleable, so the cheapest correct move is to let version 2 *mean* the new boolean form from the
start:

→ **`_script_1_to_2` gains the boolean rewrite**, beside the duration reshape, the `action_type`
rename and the `fade_profiles` drop it already carries. `CURRENT_VERSION["script"]` stays **2**.
→ **`network_map`'s 1 → 2 step gains the same rewrite.** Its version stays **2**, and by
**decision 5 the two schemas move together, in one release.** Staging them was the alternative —
`cuems-nodeconf` rewrites the map every 30 s, so the map would convert itself ahead of the project
libraries — but that buys a deployment convenience at the cost of two migration states to reason
about instead of one, and the conversion is the same four lines in both. One release, both
schemas.
→ `settings`, `project_mappings`, `project_settings`, `hardware_outputs`: **untouched** — no
boolean is referenced in any of them, and `settings.xsd`'s declaration is dead and gets deleted
with X1.
→ The three Media elements and the two curve values are **additive**, so they need no conversion at
all. They simply become part of what version 2 admits.

**This answers the media plan's §8 question 2, and more cleanly than a new step would.** It asks whether
the Media elements justify a step and notes a bump *"would give an older refactored library a clear
`DocumentTooNewError` instead of 'unexpected element'"*. They get that, because X1 is in the same
unreleased version 2 — without the ecosystem ever having to reason about a third script version.

### 2.1 The one consequence of reusing version 2, measured

A document **already marked `doc_version="2"` by this branch** carries the *old* boolean form, and
`cuems-convert-documents` will not touch it: it is already current, so there is no step to run.
Version 2 is briefly ambiguous — before and after this change — and the registry cannot resolve it.

This is feature 012's situation exactly, and its lesson applies verbatim: *"the machinery represents
an identity step as the absence of a registry entry, and the repair is cross-document and
out-of-band by design."*

Measured today across the six checkouts, split by marker:

| | Files with old-form booleans | Handled by |
|---|---|---|
| **unmarked (version 1)** | **51** — utils 28, bridge 10, engine 6, editor 4, common 2, nodeconf 1 | the registry's 1 → 2 step, once it carries the rewrite. **Nothing extra to do** |
| **already `doc_version` ≥ 2** | **9 real files** | a one-off rewrite, out of band |

The nine, named rather than counted: `tests/golden/xml/` (5) and `tests/golden/generated/` (1),
which **must be re-cut anyway** because the boolean text changes — so they are not extra work;
`tests/data/corpus/cuems-utils/{fade_showcase,unicode_showcase}.xml` (2), the same two
hand-authored documents feature 008 had to touch; and `cuems-engine`
`dev/test_xml_files/projects/complex_test_v2/script.xml` (1).

A raw count says 26 files; 17 of those are in `tests/tmp`, which `.gitignore:3` excludes and
`git ls-files` shows as zero tracked — throwaway test output, regenerated on every run. **So the
real out-of-band set is nine files, six of which are already on the must-re-cut list.** That is
what makes decision 3 the right call rather than merely the cheap one.

`ease_in`/`ease_out` matters more than it looks: a project saved by a `main`-line editor with an
`ease_in` fade **fails T1 on this branch today**, verified by comparing `FadeCurveType` across
`origin/main` and `HEAD`. It is a live divergence, not housekeeping.

---

## 3. The release-line collision, which is the gate's real problem

The media-dimensions plan targets **a different line**: rc15 cut from `main`, the editor on `rc1`,
the engine on PR #22 against `rc_1`, plus XSD-only back-patches for rc14 and `pre_release_1`. The
refactor is rc16 on `feat/xml-refactor`, and nothing ships from it until the coordinated
`xml-refactor-merge-candidate` tag after features 011–015 (D27) — this gate being 014, and so
inside that set rather than after it.

**So the work would otherwise land twice, and the second landing is the expensive one** — rc15's
`MediaXmlBuilder` fix (dict order, empty element for `None`) does not apply to this branch at all,
because the spec-driven writer already orders by schema position and omits absent fields.

**Decision 2 resolves it: rc15 ships first, and the branch stays on rc16.** So the two lines do not
race — they are sequential, and this branch's job is to migrate what rc15 leaves in the field.

| | |
|---|---|
| **Do** | let **rc15 ship on its own schedule**, with the back-patches in that plan's §5 exactly as written. The GO-latency fix does not wait on this gate, and nothing here blocks it |
| **Do** | implement the three Media elements **natively on the refactor branch** — three XSD elements, three `DECLARED_DEFAULTS` entries, three setter pairs. Roughly 30 lines, and `§6`'s utils points 1 and 6 are already satisfied by the branch's own machinery |
| **Do** | **cherry-pick `9c17418` alone** for the curve names |
| **Do not** | merge the rc15 line into `feat/xml-refactor`. rc15 is cut from `main`, which does not contain the refactor; the merge drags main's whole divergence and then collides head-on with X1's retype of the same file |

**What rc15 shipping first adds to this branch's obligations** — and it is a gain, not a cost: by
the time the refactor lands, real project libraries will contain documents that are
**unmarked (version 1), in the pre-013 device shape, with the three Media elements present**. That
is precisely the combination §4 orders, and it will exist in the field rather than only in a
fixture. It should therefore be a *test fixture*, not a hypothetical: a document written by rc15,
carried into this branch's corpus, reshaped and converted.

---

## 4. Ordering, and the one interaction that bites

A document arriving from the rc15 line at this branch carries **no `doc_version`** (so it reads as
`script` version 1) **and** the pre-013 device shape. Both migrations must run, in this order:

```
cuems-reshape-devices        # device shape — no version step, 013
cuems-convert-documents      # 1 → 2        — the registry, now carrying the boolean rewrite
```

That is the order 013 already established, and the reason is unchanged: reshape-first sees a
version-1 `<duration>`, convert-first sees old-shape cues, and neither order completes if reversed.

**Verified, so it need not be assumed:** `_script_1_to_2` (`xml/versioning.py:173`) touches only
`duration`, `action_type` and `fade_profiles`. It leaves every other `Media` child untouched, so
the three new elements survive the conversion — which is the document's own §6 point 3, confirmed.

Under decision 3 the boolean rewrite joins that same function, which makes the requirement sharper:
**the rewrite must be order-independent with respect to the Media elements.** It rewrites the text
of five named elements and must not care whether `pixel_width` is present, absent, or arriving in
the same pass. Since it matches on element name and the Media elements are `xs:positiveInteger`,
there is no overlap — but it is a test, not an assumption.

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
| **`cuems-utils`** | `script.xsd` + `network_map.xsd`: retype five elements, delete three `BoolType` declarations, add three `MediaType` elements, cherry-pick the two curve values. `_Bool`: delete `to_wire`, add the lowercase `to_lexical` map, widen `decode`'s literal table to the four lexical forms. `Media`: three `Unset` entries + three setter pairs. Registry: the boolean rewrite joins the **existing `script` 1 → 2 and `network_map` 1 → 2 steps** — one shared conversion, **no new version** (decision 3, §2). Re-cut the **six** goldens (`tests/golden/xml/` ×5 + `tests/golden/generated/` ×1) and hand-rewrite the **two** already-version-2 corpus documents, which the registry cannot reach (§2.1). Update the contract tests in §1.1 |
| **`cuems-editor`** | **No source change for X1** — it returns `to_wire()` and its FR-012 forbids touching the dict. The media work is its own (probe at upload, DB columns + `ALTER TABLE` migration, fill at save, repair-tool passes), and its branch has not touched those files. **One payload-version bump covers both** wire changes under its FR-047a; version 1 has not shipped, so it is free now |
| **`cuems-engine`** | **Nothing for X1** — zero `to_wire` in shipped source; it holds objects, already `bool`. The media read is `cue.media.get("pixel_width")`, which keeps working whatever the wire does. Its `cue.media` must stay dict-like with `.get()` — noted, and nothing in this gate changes that. **It must absorb the rc_1 fixes, and that merge gets a thorough review — see §6.1** |
| **`cuems-nodeconf`, `cuems-power-bridge`, `cuems-common`** | **No source change** — objects, not payloads. Fixtures only: 46 + 4 + 8 boolean elements, one conversion run each |
| **`cuems-frontend`** | the only repository doing real wire work, and it is small: drop the `=== 'True'` half at `sequence.component.ts:498`, make `:997` write a native boolean, and `settings.component.ts:176` (`online === true`) **starts working** — today it is permanently false, which disables `canAdopt()` and leaves the Adopt button dead for every node. Fix `:181`'s stale `node_type !== 'NodeType.master'` while in the file (007 renamed it to `node_role`). `autoload`/`timecode` need **nothing**: already written native, never read from the wire. **No change for media dimensions.** It also **owns the `localStorage` eviction** (decision 7, §7) |

---

### 6.1 `cuems-engine`'s merge is expected to be clean and reviewed anyway (decision 4)

The engine's candidate (`1662a99`) is **based on `main`, 14 commits behind `rc_1`**, and PR #22 —
which carries both the pre-arm fix and the media-dimensions read — is not in it. It absorbs them
when it merges `rc_1`.

That plan's §6 expects a clean merge *"due to the lack of overlaps"*, and the call-site evidence
supports it: `arm_cue.py:147` and `run_cue.py:462` are the same lines on both sides. **Expecting a
clean merge is not the same as assuming one**, and this repository has twice now been caught by the
second:

- Feature **012**'s lesson: the breakage was in **data** a call-site census cannot see. Four
  `cuems-nodeconf` failures, one cause, test fixtures whose identities were not uuid4 — predicted
  by nothing in the census.
- Feature **013**'s repeat of it: **96 engine failures, all old-shape fixtures**, zero source files
  implicated. Every compatibility surface did its job; the fixtures did not.

So the review has a specific shape rather than a general instruction. Three things a diff review
will not show:

1. **Run the engine's suite in three arms**, as 013 did — at the branch point, after the merge, and
   after one migration pass over `dev/test_xml_files/`. A single red run proves nothing about which
   of the three changes caused it.
2. **Check the engine's own fixtures, not its source.** It holds **6 unmarked and 1 already-version-2**
   boolean-carrying documents (§2.1) plus the old-shape device fixtures 013 measured. That is where
   both previous surprises lived.
3. **Confirm the hard coupling is still satisfied.** The engine's candidate is coupled to feature
   012 from `c31734c` onward (`coerce_identity` does not exist before it), so it cannot be tested
   against an older library to isolate a failure — the control arm that worked for 013 is
   unavailable here, and that is worth knowing *before* a red run has to be explained.

---

## 7. The hazard that is not in any repository

`projects.service.ts:209` and `:217` cache `initial_template` and `initial_mappings` in
`localStorage`; `project-show/video-mixer:94` and `audio-mixer:115` read the cached mappings. A
deploy that changes the boolean form leaves **old-form payloads in browsers that no server can
reach**.

The editor's `payload_version` first frame is the fix: evict when the stored version differs from
the received one. This is the strongest reason to land the gate **inside payload version 1** rather
than after it.

**Owner, settled (decision 7): `cuems-frontend`.** It is the repository that uses the browser
machinery — all four cache sites are its own files, `localStorage` is reachable from nowhere else,
and the editor can only *advertise* a version, never clear another origin's storage. The editor's
half already exists (it sends `payload_version` as the first frame); the frontend's half is to
compare and evict. The editor's T061 flagged this and left it unassigned; it is assigned now.

**Where it is recorded: feature 010** (decision 8). The eviction is a `cuems-frontend` obligation,
and 010 is the feature that owns the frontend flow and its US8 requirements — so it lands as a 010
requirement change in the pass now under way, not as a line item carried here. The same applies to
the two adoption bugs in §6: frontend-owned, recorded in 010, and shippable ahead of this gate.

---

## 8. Decisions — all settled

Every question this document opened has an answer, each folded into the text above rather than
left as a list. Recorded here so the reasoning is findable without re-reading the whole document.

| | Question | Settled | Where it landed |
|---|---|---|---|
| 1 | Is a version bump acceptable? | **Yes** — it is what makes the combination cheap | the premise of §2 |
| 2 | Does the rc15 line ship first? | **Yes.** The back-patches in that plan's §5 stand as written; the branch stays on rc16 and migrates what rc15 leaves in the field | §3, and the fixture it earns us |
| 3 | A new version step, or the one in flight? | **The one in flight.** No 2 → 3 — nine files need an out-of-band rewrite, six already on the re-cut list | §2, §2.1 |
| 4 | Is `cuems-engine`'s merge assumed clean? | **No.** Expected clean, reviewed anyway, with the review given a shape | §6.1 |
| 5 | Do `script` and `network_map` move together? | **Together, one release.** Staging them would buy a deployment convenience at the cost of two migration states instead of one, for the same four lines of conversion | §2 |
| 6 | What feature number? | **014.** `hardware_outputs becomes real` moves to **015**; the coordinated tag covers **011–015** | the status line; sequence and briefs in `etc-cuems-first-install-execution.md` §5–§6 |
| 7 | Who owns the `localStorage` eviction? | **`cuems-frontend`** — it is the repository that uses the browser machinery, and the editor cannot clear another origin's storage | §7 |
| 8 | How are the requirement changes carried? | **Folded into feature 010's requirement pass**, now under way — not carried as separate line items here | below |

### 8.1 Decision 8 — what folds into 010, and why there rather than here

Feature 010's requirement changes are being implemented now, so this gate's requirement changes go
into that pass instead of accumulating against a feature that has not started. Four items, all of
which 010 already owns the surface for:

| Item | 010's requirement today | What the fold changes |
|---|---|---|
| **The payload delta count** | FR-010, FR-011 and SC-004 say **two** deltas | **four** — (c) 013's cue key, (d) the projected model default. Already measured and recorded in 010's guide §4d and `baseline.md`; the FR text is what the fold corrects |
| **`localStorage` eviction** | unowned; the editor's T061 flagged it | assigned to **`cuems-frontend`** (decision 7), recorded against 010's frontend flow |
| **The frontend's two adoption bugs** | not recorded | `settings.component.ts:176` (`online === true`, so `canAdopt()` is permanently false and the Adopt button is dead) and `:181`'s stale `node_type !== 'NodeType.master'`. Both are live on `main`-line behaviour, both frontend-owned, and **both shippable ahead of this gate** |
| **T031a's widget premise** | *"verify the descriptor-driven forms against every restricted enumeration"* | after X1 a boolean is no longer a restricted enumeration, so the task verifies a checkbox rather than confirming a two-value dropdown as correct (§1.1) |

**The ordering that makes this safe:** the delta count and the widget premise are corrections to
010's *text* and need no code; the two adoption bugs and the eviction are `cuems-frontend` work that
010's flow 05 has not started. So nothing in this list blocks the gate, and nothing in the gate
blocks 010 — which is why folding is cheaper than carrying.
