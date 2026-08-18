# Contract: the wire format

**Feature**: 006-public-object-api · **Date**: 2026-08-18
**Evidence**: `specs/planning/xml-rebuild-05-ui-wire-contract.md`

`cuems-editor` transmits this dict **verbatim** to the Angular UI on `project_load`. It is the
heaviest, most-used path in the system, and it crosses a repository this feature does not
edit. If it moves, the UI breaks in production and nothing in this repository's tests would
have caught it — which is why the byte-equality assertion is the feature's gating test rather
than one test among many.

---

## W1 — Byte-identity (the hard constraint)

For **every** corpus script document:

```
CuemsScript.load(path).to_wire()  ==  <pre-feature XmlReaderWriter.read() golden>
                                       minus the schemaLocation key
```

- Goldens live in `tests/golden/dict/*.reader.json`, captured before this feature.
- **They are never regenerated to make a test pass** (standing rule 3). A diff is a bug in
  the projection, not a stale golden.
- Comparison is on the decoded structure *and* on scalar types: `"True"` is not `true`, and
  `"0"` is not `0`.

## W2 — Scalars

| XSD type | Wire form | Note |
|---|---|---|
| `BoolType` | `"True"` / `"False"` — **strings** | `cms:BoolType` is `xs:string` restricted to those two literals. The UI reads `cueData.enabled === true \|\| cueData.enabled === 'True'` and **writes back the string form**. Converting to JSON booleans is deferred item X1 and a file-format migration — explicitly forbidden here |
| `PercentType`, `LoopType`, channel types | `int` | |
| `UnitFloat`, `PositiveUnitFloat` | `float` | |
| `UuidType`, `TargetType` | uuid string; unparseable values pass through as their raw string | what keeps the editor's nil `Media.id` loading |
| `CTimecodeType` | `{"CTimecode": "…"}` | |
| Enum types | member name | |
| Wildcard (`ui_properties`, `xs:anyType`) | scalars as **strings** | X10's documented fallback |
| everything else | `str` | |

## W3 — Structure

- **Repeated elements keep `CMLCuemsConverter`'s current decode shape, exactly.** F22: that
  shape is a frontend contract, not an internal convention. D5's thin subclass exists to
  preserve it.
- Cue wrapping (`{"AudioCue": {…}}`) is unchanged.
- Key order is unchanged.

## W4 — What is removed, and what is added

| Change | Direction | Note |
|---|---|---|
| `{http://www.w3.org/2001/XMLSchema-instance}schemaLocation` key | **removed** from the wire dict | F23. An XML artifact with no meaning to the UI. Evidence that no consumer reads it is a deliverable |
| Runtime attributes | **cannot appear**, by construction | the projection walks declared fields; `RUNTIME_FIELDS` are not among them |
| `initial_template` payload | **changes** to match | booleans become `"True"`/`"False"`, `ui_properties` integers become strings |

**W4 changes ship together** (FR-031), so the wire format moves once rather than twice.

## W5 — The two payloads become one projection

Today the UI receives two mutually inconsistent encodings of the same document type (F21):

| | `initial_template` (via `__json__`) | `project_load` (via the converter) |
|---|---|---|
| `enabled`, `autoload`, `timecode` | `bool` — `true` | `str` — `"True"` |
| `ui_properties.warning` | `int` | `str` |
| `schemaLocation` | absent | **present** |

After this feature both come from `to_wire()`. `project_load` is **byte-identical** except for
the dropped key; `initial_template` moves to match it.

**No frontend change is required** — the dual-check already absorbs the boolean case. The
frontend team is told anyway, because they own the follow-up that removes the dual-check once
both payloads agree.

## W6 — The written document

`xsi:schemaLocation` changes from the writing machine's absolute path to the **bare schema
filename**.

- Today every show file carries the writing machine's local layout, so documents are neither
  portable nor reproducible (F24), and goldens are machine-dependent.
- Nothing resolves the value: validation uses the explicitly loaded schema object.
- `tests/contract/test_legacy_compatibility.py` already proves the read side across all three
  forms — absolute, relative, absent — as 004's FR-035c/SC-019. **Files already on disk are
  unaffected.**

## W7 — Verification

| Guarantee | Test |
|---|---|
| W1 byte-identity | golden comparison, every corpus script document — **the gating test** |
| W1 safety of the fast path | `encode_wire(obj) == schema.to_dict(build_document(obj))`; the round-trip is the oracle, the direct projection is what ships |
| W2 booleans | assert `"True"`, and assert **not** `True`, on every boolean field |
| W3 repeated shape | golden comparison covers it; one explicit test names it so a future change fails loudly |
| W4 key absent | enumerate wire keys, assert no `schemaLocation` |
| W4 no runtime state | assert no `RUNTIME_FIELDS` name appears at any depth |
| W5 payload parity | render one script both ways, diff field by field, **zero** differences — fails before this feature |
| W6 portability | write the same object under two installation layouts, compare bytes |
| W6 read tolerance | the existing three-form matrix keeps passing |
