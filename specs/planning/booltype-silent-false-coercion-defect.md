<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Defect — `cms:BoolType` ingestion turns any unrecognised string into `False`, silently

**Found** 2026-10-02, while checking a `cuems-editor` claim about `to_wire` and booleans.
**Measured on** `cuems-utils` `6213b16` (`0.1.0rc16`), `src/cuemsutils/xml/adapters.py`, `_Bool`.
**Severity**: high — a wrong value is written to a schema-valid document and nothing anywhere
refuses it or reports it.

This record exists to prompt a numbered feature, following
`dmx-universe-channel-conversion-defect.md` → `specs/009-fix-dmx-channel-conversion/`. Delete it
once that feature lands.

---

## 1. First, the thing that is *not* a defect

`cuems-editor`'s specs say the wire carries the **strings** `"True"` / `"False"`, never JSON
`true` / `false` (its `contracts/project-payload.md`, `data-model.md:76`,
`tests/ws-command-responses.txt:95`, `research.md` R6). **That is correct and deliberate**, and it
is not a parsing failure:

- `cms:BoolType` is an `xs:string` enum of exactly `True` / `False` — declared independently and
  identically in `script.xsd:489`, `network_map.xsd:55` and `settings.xsd:155`. It is **not**
  `xs:boolean`.
- Decode *does* parse to real Python booleans. Measured on
  `tests/golden/xml/cuems-editor__script_minimal.xml`: a cue's `enabled` is `True` (`bool`),
  `autoload` and `timecode` are `False` (`bool`). The object model holds no strings here.
- `_Bool.to_wire` deliberately un-parses at the boundary (`to_lexical` → `str(obj)`), and
  `adapters.py`'s own module docstring says why: *"Decoding them to JSON booleans would be the most
  natural 'improvement' available here and would break every consumer of the payload at once (C5)."*
  `tests/unit/test_adapters.py::test_bool_round_trips_to_strings_in_both_output_directions` and
  `tests/contract/test_wire_booleans.py` pin it.

So "`to_wire` is not parsing to bools" is true of the **direction it describes** and is a contract,
not a bug. **Nothing below asks for that to change.** The wire stays strings.

## 2. The defect, in the other direction

`_Bool.decode` (`src/cuemsutils/xml/adapters.py:83-88`):

```python
def decode(self, raw):
    if raw is None or isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw == "True"      # ← every other string becomes False
    return bool(raw)
```

Measured, adapter level:

| input | decode | to_lexical | to_wire |
|---|---|---|---|
| `True` / `False` | `True` / `False` | `'True'` / `'False'` | same |
| `'True'` / `'False'` | `True` / `False` | `'True'` / `'False'` | same |
| **`'true'`** | **`False`** | `'False'` | `'False'` |
| **`'false'`** | `False` | `'False'` | `'False'` |
| **`'TRUE'`** | **`False`** | `'False'` | `'False'` |
| **`'1'`** | **`False`** | `'False'` | `'False'` |
| **`'yes'`** | **`False`** | `'False'` | `'False'` |
| **`'banana'`** | **`False`** | `'False'` | `'False'` |
| `1` / `0` | `True` / `False` | `'True'` / `'False'` | same |
| `None` | `None` | `None` | `None` |

### Reachable, end to end, through the editor's save path

`CuemsScript.from_json` is the ingestion path (`CuemsParser(payload).parse()`'s replacement) and
`cuems-editor` now calls it on every client save. Measured end to end — payload in, file on disk
out, `<enabled>` values in document order, the second being the edited cue's:

| payload `"enabled"` | object | document on disk |
|---|---|---|
| `"True"` | `True` | `['True', 'True', 'True', 'True', 'True']` |
| `true` (JSON) | `True` | `['True', 'True', 'True', 'True', 'True']` |
| **`"true"`** | **`False`** | **`['True', 'False', 'True', 'True', 'True']`** |
| **`"banana"`** | **`False`** | **`['True', 'False', 'True', 'True', 'True']`** |

`save` succeeds. The document is **schema-valid** — `False` is a legal `BoolType` — so T1 cannot
refuse it, T2 has no rule about it, the `LoadReport` says `CLEAN`, and the next load returns a cue
that is disabled. **A disabled cue does not fire.** For `autoload` and `timecode` the failure is the
same shape.

### Why this one is worse than it looks: it is the only adapter that manufactures a value

| Adapter | `decode("banana")` | Where the operator finds out |
|---|---|---|
| `_Int` (`PercentType`, `LoopType`, `ChannelNumberType`, `ChannelValueType`) | **raises** `ValueError` | immediately — `from_json` → `SchemaError` |
| `_Float` (`UnitFloat`, `PositiveUnitFloat`) | **raises** `ValueError` | immediately |
| `_CTimecodeAdapter` | **raises** `ValueError` | immediately |
| `_EnumAdapter` (`PostGoType`, `ActionType`, `FadeCurveType`, `NodeRoleType`, …) | `'banana'` passes through | at `save` — T1 refuses on the enumeration facet (verified: `SchemaError: [T1] XsdEnumerationFacets at post_go`) |
| `_UuidAdapter` | `'banana'` passes through | at `save` — T1 refuses on the pattern |
| **`_Bool`** | **`False`** | **never** |

Every other adapter either refuses the value or lets a *detectably wrong* value through. `_Bool`
converts a bad value into a **good, different** value. That is the one failure mode no downstream
tier can catch.

### It also makes a documented promise empty

`CuemsScript.from_json`'s docstring defines its structural check as *"T1 is the mapper's
decode-time check — every key resolved against a declared field, **every value accepted by its
adapter**"* (FR-023a). For booleans that check accepts everything, so the promise is vacuous
exactly where it is load-bearing: `from_json` has no document to validate, so the adapter **is**
T1.

### And it is the defect class `adapters.py` was written to close

From the same module docstring: `str_to_value` was retired because it *"ran every scalar through
`int` → `float` → `strtobool` → `Uuid` — which is why a cue named `n` was saved as `False` and one
named `none` as `None` (ClickUp 869cqbpxa)"*, and the fix was to make the class *"unrepresentable
rather than denylisted"*.

`tests/unit/test_adapters.py::test_free_text_is_never_coerced_to_a_boolean` pins exactly
`["n", "y", "t", "f", "N", "Y", "on", "off", "no", "yes"]` — **against `NameStringType`**. Feed those
same ten strings to a *boolean* field and `"yes"`, `"on"` and `"y"` all become `False`. The defect
class is closed on the side the test checks and open on the other side of the same seam.

## 3. The fix

**One adapter, four lines. Refuse what the schema does not declare, exactly as `_Int` does.**

```python
def decode(self, raw):
    if raw is None or isinstance(raw, bool):
        return raw
    if raw == "True":
        return True
    if raw == "False":
        return False
    raise ValueError(
        f"cms:BoolType accepts 'True', 'False' or a bool; got {raw!r}"
    )
```

**Why this shape:**

1. **It matches the house pattern.** `_Int`, `_Float` and `_CTimecodeAdapter` all raise. `_Bool`
   becomes consistent with its three neighbours instead of being the one that guesses.
2. **The public exception comes for free.** `from_json` already converts an adapter `ValueError`
   into `SchemaError` (verified with `loop: "banana"` → `SchemaError: the payload does not match
   script.xsd: invalid literal for int()…`). No new error type, no new catch site. The message
   should name the field as well as the value; check whether the int case already does, and if not,
   that is one improvement for both.
3. **No document on disk changes meaning.** T1 guarantees only `True` / `False` ever appear as
   `BoolType` text in a valid XML file, so every currently-loadable document decodes exactly as it
   does today. The blast radius is confined to `from_json` payloads that were **already producing
   wrong values**.
4. **The wire contract is untouched.** `to_lexical` and `to_wire` are not edited. `"True"` /
   `"False"` still go out. §1 stays true.
5. **JSON-native clients keep working.** `true` / `false` are `bool` and hit the `isinstance`
   branch.

**Dropping the `bool(raw)` fallback is part of the fix, not an extra.** It is what makes `1` → `True`
and `"1"` → `False`, which is an inconsistency with no caller: it is unreachable from XML (T1) and
from a well-formed payload (a JSON boolean is a `bool`).

### The one judgment call: should `"true"` be accepted?

**Recommendation: no.** Raise on it.

- Accepting it creates a second ingestion vocabulary wider than the schema's — `"true"` would be
  legal on the wire and never legal in a file. This codebase's stated preference is one declared
  vocabulary; widening here re-opens, in miniature, the "guess from the text" behaviour the module
  exists to end.
- A refusal is a one-line fix in the client and is **visible**. A silent `False` is not.
- If a migrating `cuems-frontend` turns out to send lowercase, that is the right moment to find
  out — flow 05 has not started, so no shipped UI depends on either answer today. (If it is
  accepted later, accept `"true"`/`"false"` **only**, case-sensitively, and never `"1"`/`"yes"`.)

### Tests the fix needs

- `tests/unit/test_adapters.py`: parametrised refusal over `["true", "false", "TRUE", "False ",
  "1", "0", "yes", "on", "y", "n", "", "banana"]` — reusing the ten strings
  `test_free_text_is_never_coerced_to_a_boolean` already names, so the two tests state the same rule
  on both sides of the seam.
- A `from_json` integration case asserting `SchemaError` with the field named, for a cue `enabled`
  of `"true"` — the end-to-end path measured in §2, red before the fix.
- `1` / `0` refused (records the dropped fallback deliberately rather than by omission).
- No existing test pins the lenient behaviour — checked: `tests/unit/test_adapters.py` asserts only
  `"True"`/`"False"`/`None` and the two output directions. The change is additive to the suite.

### Do this *before* `cuems-editor` UR-5 lands

Today the hazard is confined to the show path, because the only JSON ingestion this library offers
is `CuemsScript.from_json`. `network_map` is the one configuration schema that runs the adapter
table (`runs_adapter_table=True`, feature 007), and its `adopted` / `online` are `BoolType` — so
**the day a public config-document ingestion exists** (`cuems-editor` UR-5, see
`upcoming-feature-requirements-2026-10-02.md` §1), a client's `"adopted": "true"` silently unadopts
a node, through the same four lines. Fixing `_Bool` first means that ingestion path is born strict
instead of acquiring the same defect by inheritance.

## 4. Secondary, lower severity — recorded so it is not merged into the above

`_EnumAdapter` and `_UuidAdapter` pass an unrecognised value through unchanged, so
`from_json` accepts it and `save` refuses it at T1. **This is not the same defect**: the value is
detectably wrong and the operator does get an error. What they cost is a *worse message at a later
point* — a facet violation at save rather than a named field at ingestion. Worth deciding as part
of the same feature (the symmetry argument is the same one), but it is a diagnostics improvement,
not a silent-wrong-value fix, and it must not be used to justify delaying §3.

## 5. Schema housekeeping noticed in passing

`settings.xsd:155` **declares `BoolType` and no element references it.** It is a dead simple type,
the same class of item as `PutType` (schema item X9), which feature 007 deleted from the schema,
the model and the registry. `project_mappings.xsd`, `project_settings.xsd` and
`hardware_outputs.xsd` have no boolean of any kind. So the live boolean surface is exactly five
elements: `autoload`, `enabled`, `timecode` (`script.xsd`) and `adopted`, `online`
(`network_map.xsd`).

Deleting `settings.xsd`'s copy would, however, break `tests/unit/test_descriptor_enums.py` and
`tests/contract/test_schema_name_overlap.py:82`, which assert `BoolType` is declared identically in
**three** schemas and is a sanctioned identical duplicate. That makes it a deliberate choice with a
test cost, not a tidy-up: record a decision either way rather than leaving the dead type
undocumented.

---

## 6. The separate question: should the **wire** carry native booleans?

Raised 2026-10-02 alongside this defect, and **deliberately kept separate** — §3 is a defect fix
that changes no wire byte; this is a contract change. Both can happen; only §3 must.

### The case against, as `cuems-editor`'s vendored bundle states it

`../cuems-editor/specs/planning/xml-refactor/04-wire-contract.md` §2: the dual read
`cueData.enabled === true || cueData.enabled === 'True'` *"is not legacy debt to clean up in this
feature — it is the compatibility mechanism, and changing the wire to a real boolean here would be a
third delta this contract does not sanction."*

That reasoning was sound **for flow 02's scope**. Two things about it are now out of date, both
measured:

- **It says "a third delta".** There are four (013's cue key, and `opacity`). The editor's own
  landed `contracts/project-payload.md` and `cuems-frontend`'s re-measured copy of the same bundle
  (`8a61780`, which also carries an `05-amendment-2026-10-02.md`) both say four. **The editor's copy
  of `04-wire-contract.md` has not had the re-measure that its `00` and `03` just got** — it still
  says two deltas and still cites `sequence.component.ts:492`.
- **It cites `:492`.** At `cuems-frontend` `8a61780` the dual read is at **`:498`**.

### The case for, measured in `cuems-frontend` at `8a61780`

| Site | Code | Consequence |
|---|---|---|
| `project-edit/sequence/sequence.component.ts:498` | `enabled: cueData.enabled === true \|\| cueData.enabled === 'True'` | the dual read. **Already accepts a native boolean**, so the read half of a switch costs nothing |
| `project-edit/sequence/sequence.component.ts:997` | `newCue.enabled = cue.enabled ? 'True' : 'False'` | the write half — **one line** |
| `project-edit/sequence/sequence.component.ts:884`, `:895`; `project-edit/project-edit.component.ts:158`, `:169` | `autoload: false`, `timecode: false` | ⚠️ **the frontend already writes these two as native JSON booleans.** So the wire is *already* mixed: `enabled` goes out and comes back as a string, while `autoload`/`timecode` come back native. `_Bool.decode` absorbs it because `isinstance(raw, bool)` passes through |
| `settings/settings.component.ts:176` | `nodeWrapper?.node?.online === true` | ⚠️ **a live bug, and not a cosmetic one.** `online` arrives as `"True"`; a string is never `=== true`, so `isSeenByDiscovery()` is **permanently false** — and `canAdopt()` at `:185` is `nodeconfAvailable() && isSeenByDiscovery(...)`, so **the Adopt button is dead for every node** |

**Answering the question the editor's bundle left open.** `03-migration-inventory.md` §7 asks to
*"grep the same file for the matching `adopted === true` read before closing the item"*, noting it is
*"not verifiable from this repository"*. Verified here: **there is no `adopted` read.** The only
`.online`/`.adopted` reads in the whole frontend are `settings.component.ts:176` and an unrelated
`onlineUsers` setter in `app-footer.component.ts:56`. The item closes on one site, not two.

**And one more fault on the adjacent line, which is not a boolean matter but travels with it**:
`canUnadopt()` at `settings.component.ts:181` compares
`nodeWrapper?.node?.node_type !== 'NodeType.master'`. Feature 007 renamed that element to
`node_role` with values `controller`/`node`/`firstrun`, so the key is absent and `undefined !==
'NodeType.master'` is **always true** — Unadopt is permanently *enabled*, controller included, and
`cuems-nodeconf` then refuses the operation. Textbook 007 FR-030a-ii ("keeps resolving but becomes
wrong"). Owned by the frontend flow; recorded here because anyone fixing `:176` is already in the
file.

### What this changes about the recommendation

The string form was adopted as a compatibility mechanism, and the measurement shows it is **not
being honoured consistently by the consumer it protects**: of the frontend's boolean reads, exactly
one got the dual treatment (`enabled`) and the one that did not (`online`) is a dead control in the
adoption UI. A compatibility mechanism that one of two consumers' sites implements is not buying
compatibility.

So the coordinated change is defensible, and its three steps are the right three:

1. `_Bool.to_wire` returns the Python `bool` (and `to_lexical` keeps emitting `"True"`/`"False"`,
   because the **XSD is unchanged** — `cms:BoolType` stays an `xs:string` enum; only the JSON
   projection moves). This is also the moment to decide whether `network_map`'s `adopted`/`online`
   move with `script`'s three, or separately.
2. `cuems-frontend`: delete the `=== 'True'` half of `:498`, change `:997` to a native boolean, fix
   `:176`, and fix `:181`'s `node_type` while in the file. `autoload`/`timecode` need nothing.
3. Amend `04-wire-contract.md` **in both vendored copies** (the editor's is the stale one) plus the
   editor's `contracts/project-payload.md`, `data-model.md:76`, `tests/ws-command-responses.txt`
   and `cuems-utils`' `tests/contract/test_wire_booleans.py` / `test_ui_payload_contract.py`, which
   currently pin the string form as the contract.

**Sequencing, and the reason it is not negotiable: §3 lands first.** A wire switch is exactly the
window in which a half-updated client sends `String(true)` → `"true"`, which today becomes `False`,
is schema-valid, is written to disk, and is reported by nothing. Strict decode turns that migration
hazard into an error message. Doing the contract change first and the defect fix second means the
one transition where the bug matters most is the one it is not fixed for.

It is also a **payload-version bump** by the editor's own FR-047a (an existing message changes a
value's form), and payload version 1 has not shipped — so if it is going to happen, before that
ships is cheaper than after.

---

## 7. Widening it: "move all values to true booleans" — reviewed 2026-10-02

Asked because the coordinated refactor makes it cheap. It is cheaper than the deferral implies,
**and it is bounded far more tightly than "all values" suggests** — but only at one of three levels.

### 7.1 There is exactly one type to widen

Every adapter's `to_wire` output, measured:

| XSD type | Python | `to_wire` | Natural JSON form? |
|---|---|---|---|
| `PercentType`, `LoopType`, `ChannelNumberType`, `ChannelValueType` | `int` | `50` | ✅ native |
| `UnitFloat`, `PositiveUnitFloat` | `float` | `0.5` | ✅ native |
| `CTimecodeType` | `CTimecode` | `{"CTimecode": "…"}` | ✅ wrapper, by design (D17/D18b) |
| `UuidType`, `TargetType`, `NodeUuidType` | `Uuid` | `"8726353c-…"` | ✅ JSON has no uuid |
| `PostGoType`, `ActionType`, `FadeCurveType`, `NodeRoleType` | `str`/enum | `"pause"` | ✅ JSON has no enum |
| **`BoolType`** | **`bool`** | **`"True"`** | ❌ **the only one** |

So "all values" is **one type, five elements, two schemas**: `autoload`, `enabled`, `timecode` on
`script.xsd`'s `CommonPropertiesType` (so on *every* cue — 15 occurrences in the smallest golden,
27 in the largest) and `adopted`, `online` on `network_map.xsd`. `settings.xsd` declares `BoolType`
and references it nowhere (§5).

### 7.2 Three levels, and **there is no cheap partial**

| | What changes | Version step? | Documents on disk |
|---|---|---|---|
| **L1 — wire only** | `_Bool.to_wire` returns the `bool`. `to_lexical` still writes `True`/`False`, because the **XSD is untouched** | **no** | **unchanged, byte for byte** |
| **L2 — all five, together** | nothing extra: the adapter is bound per **XSD type**, so L1 *is* L2 | no | unchanged |
| **L3 — X1 proper** | `cms:BoolType` → `xs:boolean`; XML text becomes `true`/`false` | **yes**, `script` 2→3 and `network_map` 2→3, each with a registered conversion | **every one invalidated** |

**L2 is the finding.** You cannot widen `enabled` alone and leave the other four: the adapter is
keyed by XSD type name, so one edit moves all five. Doing only `enabled` would need a per-**field**
opt-in like feature 012's `adapter_fields` — *more* machinery for *less* result. Accept all five or
none.

**L3 buys nothing L1 does not** *— superseded 2026-10-02, see below.* The UI gets real JSON
booleans at L1. L3 only changes what the file says, at the cost of a version step on two schemas, a
registered conversion each, re-cut goldens, and fixture migration in five repositories — on top of
013's reshape debt, with the reshape-then-convert ordering to respect.

> **⚠️ Revised the same day.** This sentence was written on the assumption that a version step was
> expensive. The maintainer ruled that a bump on the required files is **not** an issue for the
> coordinated work, which removes L3's whole cost argument — and one thing L3 buys that L1 does not
> then becomes decisive: **the descriptor cannot tell a boolean from a two-value string enum.**
> Measured: `enabled` reports `enum_values: ('True', 'False')`, structurally identical to
> `post_go`'s three values, so every descriptor-driven form renders a two-option dropdown where a
> checkbox belongs — and the editor's `schema_descriptor` action serves that to clients today.
> L1 cannot fix it; only retyping can. **L3 is now the recommendation**, combined with two other
> `script.xsd` changes in one version step:
> [`coordinated-gate-booleans-media-dimensions.md`](coordinated-gate-booleans-media-dimensions.md).
> §3's strict `decode` is **not** made redundant by it — `from_json` has no document, so the
> adapter is still T1 there; its literal table widens to `xs:boolean`'s four lexical forms.

### 7.3 The decisive fact: the dual read's cause was removed two features ago

`04-wire-contract.md` calls `cueData.enabled === true || cueData.enabled === 'True'` *"the
compatibility mechanism"*. The audit records what it is actually compatible **with** — finding
**F21, severity HIGH, measured**:

> *"The editor sends the UI two mutually inconsistent JSON encodings of the same document type:
> `initial_template` via `__json__` (Python types) and `project_load` via the converter (schema
> types). The frontend absorbs it with `cueData.enabled === true || cueData.enabled === 'True'`."*

Both halves of F21 are now closed:

- **Feature 006** retired the eight `__json__` methods into one derived projection. Verified today:
  `generate_example(SchemaName.SCRIPT)` emits `"enabled": "True"` — the *string*, same as
  `to_wire`. The two encodings are one encoding.
- **The editor's T060** retired `initial_template` altogether at payload version 1; a client builds
  from `schema_descriptor`'s `instance`.

So the `=== true` half of that dual read is **dead code today**, and the string form's stated
justification was a symptom of a defect that no longer exists. Meanwhile the one site that never
got the dual treatment — `settings.component.ts:176`, `online === true` — is a dead Adopt button
(§6). A compatibility mechanism honoured at one of two sites is not buying compatibility.

### 7.4 Cost of L1/L2, per repository

| Repository | Work |
|---|---|
| `cuems-utils` | `_Bool.to_wire` returns `obj`. Then the tests that pin the string form **as the contract**: `tests/contract/test_wire_booleans.py` (its whole premise, docstring included), `test_ui_payload_contract.py`, and check `test_payload_parity`, `test_config_parity`, `test_node_field_coercion`, `test_adoption_selection`, `test_partition_public`. **The XML goldens are unaffected** — at L1 no document text changes |
| `cuems-engine`, `cuems-nodeconf`, `cuems-power-bridge` | **nothing.** Zero `to_wire` in shipped source; they hold objects, already `bool`. Every boolean write found in those trees is a real Python `bool`, which passes through unchanged |
| `cuems-editor` | **no source change** — it returns `to_wire()` and FR-012 forbids it touching the dict. Record the delta in `tests/ws-command-responses.txt`, `contracts/project-payload.md`, `data-model.md:76`; it is a **payload-version bump** under its own FR-047a |
| `cuems-frontend` | drop the `=== 'True'` half at `sequence.component.ts:498`; `:997` writes native; `settings.component.ts:176` starts working; and fix `:181`'s stale `node_type` while in the file. **`autoload`/`timecode` need nothing** — measured: written native already (`:884`, `:895`, `project-edit.component.ts:158`, `:169`) and **never read from the wire** |

### 7.5 The one real hazard is the browser, not the server

`projects.service.ts:209` and `:217` cache `initial_template` and `initial_mappings` in
`localStorage`; `project-show/video-mixer:94` and `audio-mixer:115` read the cached mappings. A
deploy that changes the boolean form leaves **old-form payloads in browsers that nothing on the
server can reach** — the eviction story the editor's T061 already flagged and left unowned.

**The editor's new first frame is the fix**: evict the cache when the stored `payload_version`
differs from the received one. That makes this a reason to do L1/L2 **with** payload version 1
rather than after it — version 1 has not shipped, so the bump is free now and a second bump later.

**Do not touch the OSC channel.** `osc.service.ts:191` and `:361` carry cue-enabled as `1`/`0` over
OSC (`Number(msg.args[0]) === 1`). Different transport, correct as it is, and not part of this.

### 7.6 Recommendation

**Do L1/L2 inside payload version 1. Leave L3 (X1) deferred.** The ordering constraint from §3
stands: strict `decode` lands first, because the switch is exactly when a half-updated client sends
`String(true)` → `"true"`.

### 7.7 ⚠️ A finding for 010 — X1 is about to be deleted

010's **T069c** plans to delete `specs/planning/xml-rebuild/` once its residue is relocated, and
names the residue as *"`xml-rebuild-01-audit.md` §6's **X13–X17** schema debt"*.

**§6 holds X1–X17, and the list is short by more than X1.** Still-open, unrelocated items in that
section: **X1** (this one), **X2** (`TimecodeType` — recorded dead, and measured today as *still
referenced once*, so the audit entry is itself now wrong), **X3** (`EmptyStringType`, declared and
referenced nowhere — confirmed dead today), **X4** (`TargetType` vs `UuidType`, two spellings of
"uuid or nothing"), **X5** (deferred, marked superseded), **X7**/**X8** (XSD 1.1 facts), and
**X10** (`UiPropertiesType` is `xs:anyType` — a standing *constraint* on D2, not debt, and the one
most costly to lose). X9 is closed by 007; X11/X12 closed structurally by D13; X13 is already in
`specs/agreements/schema-evolution-convention.md`.

So T069c's relocation must carry **§6 whole**, not the five items it names — otherwise deleting the
folder destroys the only record of X1 at the moment a feature is being written to act on it. Add
this to T069c rather than to this file, since this file is itself scheduled for deletion.
