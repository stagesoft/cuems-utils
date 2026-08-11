# XML infrastructure rebuild — Part 2d: The editor↔UI wire contract

**Status:** analysis for review
**Date:** 2026-08-10
**Question:** will `cuems-editor`'s WebSocket transmission to the UI be affected by the
rebuild? Are the requirements still met if the API changes?

**Answer:** yes it is affected, but far less than feared — and the investigation found that
the wire format is **already inconsistent today**, with the frontend carrying explicit
code to absorb it. The recommended target is *more* consistent than the status quo and
leaves the main payload byte-identical. Evidence below is measured, not inferred.

---

## 1. The UI receives two different JSON shapes for the same document type

| Message | Source | Serialization |
|---|---|---|
| `initial_template` | `create_script()` — a **`CuemsScript` object** ([CuemsWsServer.py:84,503](../../../cuems-editor/src/cuemseditor/CuemsWsServer.py)) | `json.dumps` → `json_fix` → **`__json__`** (the object-model projection) |
| `project` (on `project_load`) | `db.project.load(uuid)` → `load_xml` → `XmlReaderWriter.read()` — a **raw dict** ([CuemsWsUser.py:477-479](../../../cuems-editor/src/cuemseditor/CuemsWsUser.py)) | `json.dumps` of **`xmlschema.to_dict()` via `CMLCuemsConverter`** |

So the outbound project payload never touches the object model, and the outbound template
payload never touches the converter. Two independent projections, one document type.

### 1.1 Measured difference

Same script, both paths (probe in Appendix A):

| field | A — `initial_template` (`__json__`) | B — `project_load` (converter) |
|---|---|---|
| structure, key names, cue wrapping (`{"AudioCue": {…}}`) | identical | identical |
| `autoload`, `enabled`, `timecode` | **`bool`** (`true`) | **`str`** (`"True"`) |
| `ui_properties.warning` | **`int`** | **`str`** |
| `offset` / `prewait` / `postwait` | `{"CTimecode": "…"}` | `{"CTimecode": "…"}` — same |
| `loop` | `int` | `int` — same |
| extra top-level key | — | **`{http://www.w3.org/2001/XMLSchema-instance}schemaLocation`** |

Structure and naming agree. **Scalar encoding does not.**

### 1.2 The frontend already compensates — explicitly

`cuems-frontend/src/app/components/projects/project-edit/sequence/sequence.component.ts`:

```typescript
// :492  — inbound, absorbs BOTH encodings
enabled: cueData.enabled === true || cueData.enabled === 'True',

// :959  — outbound, always sends the STRING form
newCue.enabled = cue.enabled ? 'True' : 'False';
```

That dual-check is the frontend paying for §1.1. And note the asymmetry it reveals: the UI
**sends back** the string form, so the inbound editor contract (`CuemsParser(data).parse()`)
is already string-typed.

---

## 2. Which shape is "right"? The schema says B

`cms:BoolType` is `xs:string` restricted to `"True"` / `"False"` — in both `script.xsd`
and `network_map.xsd` (Part 1, X1). So on the wire, per the schema, these fields **are
strings**.

- **Shape B (converter) is schema-faithful.**
- **Shape A (`__json__`) is the deviation** — it leaks Python types, because the object
  model coerced `"True"` → `bool` via `strtobool` on the way in and `__json__` emits
  whatever Python holds.

This inverts the intuitive reading. The object model's JSON projection is the odd one out,
not the converter's.

---

## 3. What this means for decisions already taken

### 3.1 D5 was right, for a reason we had not identified

Q2 option (c) was *"drop the fork for a stock converter and absorb the shape change in the
parser layer, deleting the six compensations."* Because `project_load` transmits
`CMLCuemsConverter`'s output **directly to the UI**, that option would have changed the
wire format and **broken the frontend**. The chosen D5 (thin subclass preserving the
repeated-element shape) keeps the UI contract intact.

Restated as a constraint: **`CMLCuemsConverter`'s decode shape is a frontend contract, not
merely an internal convention.** Part 1 F5's "six hand-written compensations" undercounted —
the seventh consumer is the UI.

### 3.2 Q14 (internal-only `xml/`) — this is where the real impact lands

Under Q14, `load_xml` returns a `CuemsScript` rather than a raw dict. If the editor then
`json.dumps`es that object, `project_load` switches from shape B to shape A, and every
boolean on the wire changes `"True"` → `true`. The frontend's `=== true || === 'True'`
would survive that, but nothing guarantees every other field is equally defended.

**So Q14 is safe only if the public object can still produce the schema-faithful wire
shape.** That is a concrete requirement on the new API, and it is satisfiable.

---

## 4. Are the requirements still met?

The requirements, stated independently of today's spelling:

| # | Requirement | Met under the proposed design? |
|---|---|---|
| R1 | UI receives a JSON representation of a `CuemsScript` it can render | ✅ |
| R2 | UI can send that representation back and have it persist to XML | ✅ — `CuemsScript.from_json()` replaces `CuemsParser(data).parse()` |
| R3 | The representation is **stable and single** | ✅ — improves on today, which has two |
| R4 | `initial_template` and `project_load` are mutually consistent | ✅ — **fixed**, currently broken |
| R5 | No frontend change required for the main path | ✅ if the unified shape is B (§5) |

Yes — and on R3/R4 the design is strictly better than the status quo.

---

## 5. Recommendation: unify on the schema-faithful shape (B)

One JSON projection, derived from the schema like everything else under D2, emitting what
the XSD declares — which is exactly today's `project_load` payload.

Consequences:

- **`project_load`: byte-identical.** No frontend change. The heaviest, most-used path is
  untouched.
- **`initial_template`: changes** — booleans become `"True"`/`"False"`, `ui_properties`
  integers become strings. The frontend's existing `=== true || === 'True'` already covers
  the boolean case; other fields need a check.
- **The frontend can eventually simplify**, dropping its dual-check once both paths agree.
  That is a follow-up for `cuems-frontend`, not a blocker.
- **Drop the `schemaLocation` key** from the payload — an XML artifact with no meaning to
  the UI. Low risk, but it is a wire change; confirm no frontend code reads it.

This also resolves **Q12** concretely: the JSON projection is owned by the rebuild and
derived from the schema, and the eight hand-written `__json__` methods (F13) are retired
into it. `to_json` gains its missing inverse.

### Deferred, and worth stating

If real JSON booleans on the wire are wanted, that is **X1** — changing `BoolType` from
`xs:string` to `xs:boolean` — which is a file-format migration touching every XML on disk
and is deferred under D3. Under this design it becomes a single change that propagates to
XML, JSON and the UI at once, instead of three independent edits.

---

## 6. New findings for Part 1

| # | Severity | Finding |
|---|---|---|
| F21 | **HIGH** | The editor sends the UI two mutually inconsistent JSON encodings of the same document type: `initial_template` via `__json__` (Python types) and `project_load` via the converter (schema types). The frontend absorbs it with `cueData.enabled === true \|\| cueData.enabled === 'True'`. Measured. |
| F22 | MEDIUM | `CMLCuemsConverter`'s decode shape is transmitted **verbatim to the UI**, making it a frontend contract rather than an internal convention. Raises the stakes on any converter change (D5). |
| F23 | LOW | The `project_load` payload carries a stray `{http://www.w3.org/2001/XMLSchema-instance}schemaLocation` top-level key — an XML artifact leaked to the UI. |

---

## Appendix A — probe

`scratchpad/probe_ui_shapes.py`. Builds one script, renders it both ways — `json.dumps({"CuemsScript": script})`
(the `initial_template` path) and `write_from_object` → `read()` → `json.dumps` (the
`project_load` path) — then diffs structure and per-field container/scalar kinds. Should be
promoted into the D14 chain test, which is the natural place to assert that the two UI
payload shapes agree.
