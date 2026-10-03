<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Feature 014 — one coordinated gate: `xs:boolean`, the media pixel elements, the curve names, and the public configuration ingestion

**For:** the team working on `feat/xml-refactor` across `cuems-utils`, `cuems-editor` and
`cuems-engine`, and the author of
[`media-pixel-dimensions-for-xml-refactor.md`](../planning/media-pixel-dimensions-for-xml-refactor.md).
**`cuems-frontend`'s share is not here** — it is unloaded into that repository's own bundle
(§6.2), and a frontend reader should start there.

**Date:** 2026-10-02, **refinement closed 2026-10-03.** **Status:** this **is** feature `014`'s
plan, on the reduced SDD path (`../planning/etc-cuems-first-install-execution.md` §5–§6). Branch
`014-xs-boolean-and-media-elements`, cut from `feat/xml-refactor` at `84705b9`. Measurements below
are from 2026-10-02 against `cuems-utils` `fdfb688`, `cuems-editor` `bf57d95`, `cuems-engine`
`1662a99`, `cuems-frontend` `8a61780`; [`baseline.md`](baseline.md) re-measures the performance
figures on the branch point and states this feature's budgets.

**Relocated 2026-10-03** from `specs/planning/coordinated-gate-booleans-media-dimensions.md`, which
is deleted rather than left as a second copy — §6.2 makes that argument about the frontend and it
applies to this document too. `specs/planning/booltype-silent-false-coercion-defect.md` stays until
this feature lands, on the `dmx-universe-channel-conversion-defect.md` precedent.

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
| **9** | **`cuems-frontend`'s share is unloaded into that repository** — landed 2026-10-02 as `specs/planning/xml-refactor/06-amendment-feature-014.md` (`ad305f9`). This document keeps its measurements and stops being the owner (§6.2) |
| **10** | **`cuems-editor` UR-5's correction belongs to this repository, and lands *in this feature*** — the public configuration-document ingestion that unblocks that repository's T059. Reviewed against 014's work and folded in, because the one configuration domain that needs it is the one 014 retypes (§9) |
| **11** | **The media block is FOUR elements, not three** — `pixel_width`, `pixel_height`, `file_size` (not `size`) and `file_hash`, all `minOccurs="0"` (§10) |
| **12** | **The `get_schema` mitigation 013 identified and left is applied here** — one line, measured at −80% on the configuration load and −58% on the suite ([`baseline.md`](baseline.md) §5) |

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
| **The media block** — `pixel_width`, `pixel_height`, `file_size`, `file_hash` | **additive**, **four** optional elements on `MediaType` (decision 11, §10) | no |
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
| **`cuems-utils`** | `script.xsd` + `network_map.xsd`: retype five elements, delete three `BoolType` declarations, add three `MediaType` elements, cherry-pick the two curve values. `_Bool`: delete `to_wire`, add the lowercase `to_lexical` map, widen `decode`'s literal table to the four lexical forms. `Media`: three `Unset` entries + three setter pairs. Registry: the boolean rewrite joins the **existing `script` 1 → 2 and `network_map` 1 → 2 steps** — one shared conversion, **no new version** (decision 3, §2). Re-cut the **six** goldens (`tests/golden/xml/` ×5 + `tests/golden/generated/` ×1) and hand-rewrite the **two** already-version-2 corpus documents, which the registry cannot reach (§2.1). Update the contract tests in §1.1. **Plus the public configuration ingestion** (decision 10, §9) — one new public call, no schema change, which unblocks `cuems-editor`'s T059 |
| **`cuems-editor`** | **No source change for X1** — it returns `to_wire()` and its FR-012 forbids touching the dict. The media work is its own (probe at upload, DB columns + `ALTER TABLE` migration, fill at save, repair-tool passes), and its branch has not touched those files. **One payload-version bump covers both** wire changes under its FR-047a; version 1 has not shipped, so it is free now. **Its T059 unblocks** — §9's ingestion is the call its `config_save` is waiting for, and its test is `xfail(strict=True)`, so it needs no edit to pick it up, only a re-run |
| **`cuems-engine`** | **Nothing for X1** — zero `to_wire` in shipped source; it holds objects, already `bool`. The media read is `cue.media.get("pixel_width")`, which keeps working whatever the wire does. Its `cue.media` must stay dict-like with `.get()` — noted, and nothing in this gate changes that. **It must absorb the rc_1 fixes, and that merge gets a thorough review — see §6.1** |
| **`cuems-nodeconf`, `cuems-power-bridge`, `cuems-common`** | **No source change** — objects, not payloads. Fixtures only: 46 + 4 + 8 boolean elements, one conversion run each |
| **`cuems-frontend`** | the only repository doing real wire work, and **it is no longer tracked here** — unloaded 2026-10-02 into that repository's own planning bundle (decision 9, §6.2). The measurements stay below because they were taken here; the ownership does not |

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

### 6.2 `cuems-frontend`'s share is unloaded, not deleted (decision 9)

Every frontend item this gate measured now lives in that repository, where its spec will be written:
**`../cuems-frontend/specs/planning/xml-refactor/06-amendment-feature-014.md`**, committed
2026-10-02 as `ad305f9` on its `feat/xml-refactor`.

**Why there rather than here.** This document is `cuems-utils` feature 014's plan. A frontend task
list inside it would be a second copy of work whose spec is written in another repository, against
another repository's base branch and line numbers — the drift this folder's deletion policy exists
to prevent, and the same mistake 010 made three times with its repository list. The gate's job is to
state the *wire change*; the consuming repository's job is to state what that costs it.

**What was unloaded**, five items — and the amendment is the authority on all of them now:

| # | Item | Coupling |
|---|---|---|
| 1 | characterization tests for the save path and the adoption guards | before everything (its D35, finding C8) |
| 2 | `sequence.component.ts:997` → write the native boolean | **hard and simultaneous with 014** |
| 3 | `settings.component.ts:176` → nothing if shipping with 014; a dual read only if shipping before | scheduling |
| 4 | `settings.component.ts:182` → `node_role !== 'controller'` | none — a 007 defect, shippable now |
| 5 | the `localStorage` eviction keyed on `payload_version` | same release as payload version 1 |

**Two things that amendment establishes which this document had not**, both measured there:

- **Item 2 is not cleanup, it is a hard coupling in both directions.** `'True'` becomes a *refused*
  spelling (§1.2), and because `from_json` has no document to validate against, the adapter is the
  whole of its structural check — so a refusal is a `SchemaError` and the **save fails**. 014 cannot
  ship without that one line, and that line cannot ship without 014. It is the only such line in
  that repository.
- **The frontend already writes the same field native, three lines away.** The CueList fallback at
  `sequence.component.ts:882-897` sends `enabled: true` while `:997` sends `'True'` — two spellings
  of one field in one file today. Only the string one breaks. That is the strongest available
  argument that the native form is safe there, and it is the repository's own code making it.

**Corrected on the way out**, so the numbers in §6 and §7 above are not quoted against the wrong
lines: `canAdopt()` is at **`:187`**, not `:185`, and the stale `node_type` is at **`:182`**, not
`:181`. Both re-measured against `cuems-frontend` `8a61780`.

**The supersession this created**, recorded because it reverses a standing instruction rather than
merely adding to it: that bundle's `04-wire-contract.md` §4 is titled *"The string boolean form
survives, and simplifying it is out of scope"* and says **"Keep it"**, and its
`03-migration-inventory.md` §4a item 2 tells the frontend to *add* a dual read for `online`. Both
sections keep their text and carry a pointer to the amendment, because each is still correct about
the mechanism and only wrong about the direction.

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

**Where it is recorded, in two places and deliberately.** As a **010 requirement change**
(decision 8) because 010 owns the frontend flow and its US8 requirements, and as **§4 of that
repository's own amendment** (decision 9) because that is where its spec will be written and where
the mechanism belongs. The same applies to the two adoption bugs in §6: frontend-owned, recorded in
both, and shippable ahead of this gate.

The amendment adds three properties this section did not state, each a way to get the eviction
wrong: **evict on any difference, not only on "older"** (a rolled-back editor leaves a *newer*
cache against an older server); **a missing stored version counts as a difference** (which is every
browser in the field today); and **`initial_template` is deleted rather than migrated**, since it is
retired at payload version 1 and a cache entry for a frame the server no longer sends can never be
refreshed.

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
| 9 | Where does `cuems-frontend`'s work live? | **In `cuems-frontend`**, as `specs/planning/xml-refactor/06-amendment-feature-014.md` (`ad305f9`, 2026-10-02). This document keeps the measurements and stops being the owner | §6.2 |
| 10 | Where does `cuems-editor` UR-5's correction land? | **Here, in 014.** The one configuration domain that needs typed ingestion is `network_map`, which is also the only one carrying a boolean and the only one 014 retypes — so the two are one piece of work, and building the ingestion first would specify a new public API against a type 014 then changes | §9 |

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

---

## 9. The public configuration ingestion — `cuems-editor` UR-5, folded in (decision 10)

**The report**: `../cuems-editor/specs/001-cuems-utils-migration/upstream-reports/UR-5-no-public-config-json-ingestion.md`.
**What it blocks**: that repository's **T059**, the one task of 63 that did not land. Its
`config_save` answers the four configuration domains with an error naming the report, and its test
is `xfail(strict=True)` — so it turns **XPASS** the day this call exists, with no edit on its side.

**Why it is in this feature rather than after it.** Reviewed against 014's work, and the answer is
not "it is convenient": it is that the two changes touch **the same one domain, for the same
reason**.

### 9.1 The correlation that decides it, measured

| Configuration schema | Carries a `cms:BoolType`? | Runs the adapter table? |
|---|---|---|
| **`network_map`** | **yes** — `adopted`, `online` | **yes** (007 R1 — the only one) |
| `settings` | no | no (one per-**field** opt-in, `NodeConfType/uuid`, from 012) |
| `project_mappings` | no | no |
| `project_settings` | no | no |
| `hardware_outputs` | no | no |

**The only configuration domain whose ingestion needs real type coercion is the only one that
carries a boolean, and it is the only one 014 retypes.** `ConfigDict.from_decoded`'s own docstring
states the split that follows:

> *"`node`'s `mapping` already carries a `NodeRole` for `node_role` and a `bool` for
> `adopted`/`online` by the time it reaches this method; `Settings`'/`ProjectMappings`'/
> `ProjectSettings`' mappings still carry the raw strings `read_config_document` produced,
> unchanged, because their schemas did not opt in."*

So an ingestion for the other three is a shape check and a verbatim store. An ingestion for
`network_map` is the only one that has to *decide what a value means* — and 014 changes two of the
three answers it has to give.

### 9.2 The closed loop 014 makes consistent, and would otherwise make inconsistent

`config_save` does not receive an arbitrary document. It receives one **a client built from
`get_schema_descriptor`'s `instance`** (editor FR-045). So the descriptor and the ingestion are the
two halves of one round trip, and they must agree on the type of every field. Measured today:

```
get_schema_descriptor(SchemaName.NETWORK_MAP)  ->  NodeType
    adopted    xsd_type='BoolType'  enum_values=('True', 'False')
    online     xsd_type='BoolType'  enum_values=('True', 'False')
    node_role  xsd_type='NodeRoleType'  enum_values=('controller', 'node', 'firstrun')
```

`adopted` is **structurally indistinguishable from `node_role`** — a restricted string enumeration
— so a descriptor-driven form renders a two-option *dropdown of the strings* `"True"` / `"False"`,
and an ingestion built today would have to accept those strings to close the loop.

**Build the ingestion before 014 and both halves are specified against a mistyped field**: a form
that offers strings, and a brand-new public API that accepts them. 014 then changes the type, and
*both* halves migrate — a second migration of an API whose first release has not shipped. Build
them together and the loop is born with a checkbox on one side and a `bool` on the other.

This is the same finding as §1.1's ⭐ row, arriving from the other direction. There it was an
argument for X1; here it is the argument for doing UR-5 **with** X1.

### 9.3 The work

**One new public call. No schema change, no version step, no conversion** — so it adds nothing to
§2's story and cannot complicate it.

| | |
|---|---|
| **Shape** | `ConfigManager.from_json(SchemaName, payload)` returning the root object the matching `save_*` writes, per UR-5's own request. Symmetric with `CuemsScript.from_json`, including its three accepted forms (a JSON `str`, UTF-8 `bytes`, or an already-decoded `Mapping`) |
| **Path** | decode through **the same mapper call `load_*` uses**, so the per-schema asymmetry in §9.1 is preserved rather than normalised. Normalising it would silently retire the guarantee feature 007 measured and pinned for the other four schemas |
| **Returns an object, not a dict** | UR-5's second near-miss: the `network_map` property setter accepts a `dict`, and `save_network_map` then calls `.save` on it. The ingestion must produce `CuemsNetworkMapType`, or the save path fails on the thing it was handed |
| **`doc_version` is not expected** | it is excluded from every wire projection, so no client payload carries it. The ingestion must not require it, and the writer emits the current version as it does on every other write |
| **Refusals stay refusals** | `script` is `CuemsScript.from_json`'s, not this call's; `hardware_outputs` has no model bindings until **015**. The editor already refuses both with those reasons, and this call does not widen them |

**What it is not.** Not `ConfigDict.from_decoded` made public — that takes the *decoded* shape
rather than the wire shape and stores values verbatim, so for `network_map` a wire
`"node_role": "node"` would stay a `str` where `save_network_map` expects a `NodeRole`. Publishing
it would publish the wrong half. And not `validate_config_document`, which validates a **path**;
013 added it for checking a file and it is the right surface for that and the wrong one for
ingesting a payload. (Both near-misses are recorded in
`upcoming-feature-requirements-2026-10-02.md` §1 so they are not re-proposed.)

### 9.4 Tests, and the one that only exists because both changes land together

- **Per domain, a round trip**: `get_schema_descriptor(X).instance` → `from_json(X, …)` →
  `save_X()` → `load_X()` equals what went in. That is the loop §9.2 describes, asserted rather
  than argued.
- **`network_map`'s types, specifically**: after ingestion, `adopted` is a `bool`, `node_role` is a
  `NodeRole`, `uuid` is a `Uuid` — and the other three schemas' scalars are still **`str`**. The
  second half is the one that catches an ingestion that "helpfully" coerces everywhere, which is
  the 007 regression this feature must not cause.
- **The boolean form is 014's, not the old one**: `from_json(NETWORK_MAP, {... "adopted": true ...})`
  is accepted and `"adopted": "True"` is **refused**, by the same `_Bool.decode` table §1.3
  specifies. This is the assertion that makes the two changes one feature; written against either
  change alone it would be wrong.

### 9.5 One adjacent descriptor oddity, found while measuring and **not** in scope

```
NodeType  uuid  xsd_type='NodeUuidType'  enum_values=('00000000-0000-0000-0000-000000000000',)
```

The node identity's union type (012's `NodeUuidType` = `ConvergedUuidType` ∪
`NotProvisionedUuidType`) surfaces in the descriptor as **an enumeration of one value** — the NOT
PROVISIONED sentinel — so a descriptor-driven form would offer a dropdown containing only the
sentinel where a uuid field belongs. Same family as §1.1's boolean finding: a type the descriptor
flattens into the wrong widget.

**It is not 014's.** The boolean case is in scope because 014 retypes the field anyway; this one
would need the descriptor to learn about unions, which is a change to `xml/descriptor.py` with no
other driver in this feature. Recorded here so it is found by whoever does the descriptor-driven
forms, and carried to `upcoming-feature-requirements-2026-10-02.md` rather than to this feature's
tasks.

---

## 10. The media block — four elements (decision 11)

The input document ([`../planning/media-pixel-dimensions-for-xml-refactor.md`](../planning/media-pixel-dimensions-for-xml-refactor.md)
§1) specifies three. **This feature ships four.** All four are `minOccurs="0"`, appended after
`regions` in `MediaType`, and every existing project stays valid.

| Element | Type | Why |
|---|---|---|
| `pixel_width` | `xs:positiveInteger` | the media's original width, as `ffprobe` reports it. **Not** the layer's size on screen — `width`/`height` already exist in `CanvasRegionType` as unit floats |
| `pixel_height` | `xs:positiveInteger` | the same, for height |
| `file_size` | `xs:positiveInteger` | **named `file_size`, not `size`** (decision 11). Bytes |
| **`file_hash`** | `cms:Md5HashType` *(new)* | **the fourth, added here.** The md5 sum of the file when the dimensions were measured |

### 10.1 `file_size` must hold a file larger than 100 GB — verified

A 100 GiB file is 107,374,182,400 bytes, which **overflows a 32-bit int** (2³¹ = 2,147,483,648).
So the type matters. Measured against `XMLSchema11`:

| value | | valid as `xs:positiveInteger`? | decodes to |
|---|---|---|---|
| `107374182400` | 100 GiB | ✅ | `int` |
| `2147483648` | 2³¹ | ✅ | `int` |
| `9223372036854775808` | 2⁶³ | ✅ | `int` |
| `0` | zero-byte file | ❌ | — |
| `-1` | | ❌ | — |

`xs:positiveInteger` has **no upper bound** in XSD and `xmlschema` decodes it to a Python `int`,
which is arbitrary-precision. No facet, no `xs:long`, nothing to add — the requirement is met by the
type choice alone. The adapter side is `_Int.decode` → `int(raw)`, equally unbounded.

**`0` being invalid is deliberate, not an oversight.** A zero-byte file is not playable media, and
the three integers share one rule: **absent means unknown; 0 is not a value**. The input document
says the same for the pixel pair — *"An absent element means 'unknown'. Never write an empty one"* —
and its editor-side fill strips `None`, `0` and non-numeric values before save so a client value can
never reach the XSD. If a zero-length file ever needs representing, that is `xs:nonNegativeInteger`
and a decision to take then, not a hedge to build in now.

### 10.2 `file_hash` needs a type, and the house style settles its shape

An md5 sum is 32 hex characters. The pattern follows `UuidType`'s exactly — which is **lowercase
only** (`[a-f0-9]`) with both length facets pinned:

```xml
<xs:simpleType name="Md5HashType">
  <xs:restriction base="xs:string">
    <xs:pattern value="[a-f0-9]{32}" />
    <xs:maxLength value="32" />
    <xs:minLength value="32" />
  </xs:restriction>
</xs:simpleType>
```

**Lowercase-only is a decision, and it is the consistent one.** `md5sum`, `hashlib.md5().hexdigest()`
and `ffmpeg` all emit lowercase, and `UuidType` already refuses uppercase for the same reason. It is
also the same argument this feature makes about `_Bool`: a wider ingestion vocabulary than the
schema's means a value legal on the wire that can never appear in a file. Accepting
`[a-fA-F0-9]{32}` would be the forgiving choice and the inconsistent one.

### 10.3 What the fourth element changes about the engine's check

The input document's §3 has the engine compare the stored `file_size` against `os.stat` to detect
*"a file that was replaced under the same name"*, falling back to a probe when they differ. A hash
is a **strictly stronger** version of that test: a replacement that happens to be the same length
passes the size check and fails the hash.

**That is the engine's decision to make, not this feature's.** `cuemsutils` ships the element; what
the engine compares, and whether hashing a multi-gigabyte file at arm time is acceptable where
`os.stat` was free, is `cuems-engine`'s call. Stated here so the element does not arrive looking
like an instruction. The one thing this feature owes it: the element is optional, so an engine that
ignores it is correct.

### 10.4 Model and writer

Per §5's two confirmations and one correction, unchanged by the fourth element:

- **Four `DECLARED_DEFAULTS` entries, all `Unset`** — `Unset` *is* the emits-nothing-when-absent
  mechanism (`helpers.py:32`), with `canvas_region` as the precedent. The input document's reading
  of it is inverted, and the correction makes the work smaller.
- **Four `set_<name>` accessors.** Without both halves the key is dropped **in silence**:
  `CuemsDict.setter` resolves `getattr(self, f"set_{k}")` and `continue`s on `AttributeError`.
  Measured — that is §5's point 2, and it is the one that would have lost data.
- **No writer change.** The spec-driven writer already orders by schema position and omits absent
  fields, so the input document's `MediaXmlBuilder` fix does not apply to this branch.
- The setters accept a positive `int` or a string of digits and store an `int`; `None` removes the
  key; anything else raises. `file_hash`'s setter normalises nothing — a non-matching string is a
  `ValueError`, because the schema will refuse it at save and failing at assignment names the field.

---

## 11. Constitution check

Against `.specify/memory/constitution.md` v1.0.0. Required by the Delivery Workflow section for
every plan, and by Governance for every pull request.

| Principle | How this feature satisfies it |
|---|---|
| **I. Code quality by default** | The changes are small and local: one adapter class (a method swap), one setter line, four model fields with accessors, two schema files. Every public surface gets a docstring stating *why* — `_Bool`'s explains why the class cannot be deleted, the `schema` setter's explains why the cache is keyed as it is |
| **II. Tests as a release gate** | Tests-first throughout. `be3e86e` already demonstrated the shape on this feature's first slice: 29 red tests, then four lines. Specific red-first tests are named per task in [`tasks.md`](tasks.md); the two that cannot be written after the fact are `to_lexical`'s round trip and the bytes-on-disk assertion (§1.3) |
| **III. Consistent user experience** | This feature *creates* consistency rather than risking it: `BoolType` stops being the one type whose wire form is not its natural JSON form, `CTimecode.milliseconds` joins the one deprecation message format (already landed, `84705b9`), and the descriptor stops reporting a boolean as a two-value string enum |
| **IV. Performance budgets are requirements** | Stated **before** implementation in [`baseline.md`](baseline.md) §5: three budgets against post-mitigation figures. Any exceedance is recorded as exceeded, not restated as passing |

### 11.1 Complexity tracking — three exceptions

Governance requires exceptions documented here rather than argued in review.

| # | Exception | Why it is granted |
|---|---|---|
| **1** | **The reduced SDD path**: `plan.md`, `tasks.md`, `baseline.md` and a rule-4 release note, with **no `spec.md` story pass and no `research.md`** | The design space is closed — twelve settled decisions — and the research is already measured and committed in this document. A `spec.md` with user stories would be transcription, not thinking; there are no user stories here, there are four changes and a per-repository table. Recorded as an exception in `../planning/etc-cuems-first-install-execution.md` §5, which also states that a reduced path is **not** a lighter standard: Principles II and IV bind unchanged, which is *why* this plan exists at all |
| **2** | **D3 relaxed again** — "wire-compatible with every XML on disk; no `.xsd` edits". This is the seventh recorded relaxation (007 once, 008 five times, 013 orthogonally) | X1 is a rule-4 file-format migration by `specs/agreements/schema-evolution-convention.md`'s own definition, and it is granted **only because the conversion exists to carry it**, which is the same condition 008's three invalidating relaxations were granted under. The media block and the curve values are rule-1 additive and need no relaxation |
| **3** | **`doc_version="2"` becomes briefly ambiguous** — a marker that no longer determines its own content (§2.1) | Measured and bounded: 51 documents convert for free, **nine** need an out-of-band rewrite, and six of those nine are goldens already on the must-re-cut list. This is feature 012's situation verbatim, whose lesson applies — the machinery represents such a step by the *absence* of a registry entry and the repair is cross-document and out-of-band by design. The alternative, a 2 → 3 step, was rejected by decision 3 because nothing has shipped |

### 11.2 What this feature does **not** do, so the scope is reviewable

- **No `v0.1.1`, no deprecated-surface removal.** That is
  `../planning/deprecated-surface-removal-v0-1-1.md`, and `0.1.0rc16` does not move.
- **No `hardware_outputs` work.** That is **015**, which this feature precedes by advice only — both
  edit `settings.xsd` and so both move `test_schema_scope`'s hashes.
- **No frontend code.** Unloaded to that repository (§6.2). Its 001 is **now starting its SDD path**
  (2026-10-03), so the one hard-coupled line arrives shortly after this work rather than
  indefinitely later — which is what makes §6.2 item 2's mutual coupling schedulable.
- **No descriptor union support.** §9.5's `NodeUuidType`-as-one-value-enum stays open.
