# Contract: the public API surface

**Feature**: 006-public-object-api · **Date**: 2026-08-18

After this feature the library has **two** public entry points. Everything else is internal.
Each method below states its signature, its guarantee, its error behaviour and its
deprecation counterpart. The error behaviour is not uniform, and the differences are
deliberate.

## C0 — Signatures at a glance (CHK001)

| Method | Signature | Returns | Raises |
|---|---|---|---|
| `load` | `CuemsScript.load(path: str \| PathLike) -> CuemsScript` | fully coerced script | `SchemaError`; `OSError` unwrapped |
| `from_json` | `CuemsScript.from_json(payload: str \| bytes \| Mapping) -> CuemsScript` | fully coerced script | `IngestError`, `SchemaError` |
| `save` | `script.save(path: str \| PathLike) -> None` | `None` | `ValidationError`/`SchemaError`; `OSError` unwrapped |
| `validate` | `script.validate() -> ValidationReport` | report, falsy when empty | — (reports, never raises on a violation) |
| `to_wire` | `script.to_wire() -> dict` | the UI payload | — (does not validate) |
| `to_json` | `script.to_json() -> str` | UTF-8 JSON text | — (does not validate) |

`path` accepts `str` or any `os.PathLike`; relative paths resolve against the process working
directory, not against the package. No signature accepts a schema name (FR-021).

**`from_json` inputs, exhaustively** (CHK004): a JSON **string**; UTF-8 **bytes**; or an
already-decoded **`Mapping`**. All three are required — `bytes` is not optional and not a
convenience: FR-036c makes accepting UTF-8 bytes (and *rejecting* other codecs rather than
guessing) part of the encoding contract. Rejected with `IngestError`: a JSON array or scalar, a
mapping whose root is not a recognised script, and bytes that are not valid UTF-8. Undeclared
keys are dropped and logged at `DEBUG`, one record naming the class and the key — 005's
behaviour, unchanged.

**What "structural validation" means on this path** (FR-023a). FR-023 requires T1 at four call
sites, but this is the one with no XML document to hand the schema. Here T1 is the mapper's
**decode-time structural check** — every key resolved against a declared field of its schema
type, every value accepted by its adapter, every required element present — surfaced as
`SchemaError`. It is deliberately **not** a second pass that builds a document in order to
validate it: that would pay the projection cost FR-005a exists to avoid, on the editor's
hottest ingestion path. Consequence, stated rather than inferred: a payload can be accepted
here and still fail `save()`'s document-level check for a constraint only expressible on the
assembled document (`xs:assert`). `load()` carries the same asymmetry today; it is not new.

---

## C1 — `CuemsScript`, the show object

### `CuemsScript.load(path) -> CuemsScript`

**Guarantee**: the returned object is **fully coerced** — every field holds its declared
type, at every depth, regardless of how the document was written. This is a guarantee, not a
convention: there is no public path that produces a partially coerced script.

- Runs T1 (schema-derived) validation. Raises on a structurally invalid document.
- Does **not** run T2 (semantic) validation. A document that violates a semantic rule
  **loads** — reading never becomes stricter (standing rule 8).
- Returns an object whose runtime state is initialized and which the engine can run without
  a promotion step.
- Replaces `XmlReaderWriter(schema_name="script", xmlfile=path).read_to_objects()`.

### `CuemsScript.from_json(payload) -> CuemsScript`

**Accepts both** a JSON string (the inverse of `to_json()`) and an already-decoded mapping
(the editor's WebSocket payload). Same coercion guarantee and same validation posture as
`load()`.

- A payload that is not a script fails with a message naming what was expected, not with a
  structural error from inside the machinery.
- Keys the schema does not declare are **dropped and logged**, one record per key naming the
  class and the key — the behaviour feature 005 settled, unchanged.
- Replaces `CuemsParser(payload).parse()`.

### `CuemsScript.save(path) -> None`

Validates, **then** writes.

- Runs T1 **and** T2. Raises at the **first** failure.
- On failure, **no file is created, truncated or partially written** at the target path.
- Persists declared fields only. Saving while a show is running is **supported and
  document-only**: playback state is ignored, and the call does not refuse. The library never
  observes that a show is running and does not acquire a mechanism to.
- Replaces `XmlReaderWriter(...).write_from_object(obj)`.

### `CuemsScript.validate() -> ValidationReport`

Validates an in-memory object with **no file involved**.

- Runs T1 **and** T2, and **collects** every violation rather than stopping at the first.
- Returns a report; an empty report means valid.
- This is the deliberate asymmetry with `save()`: `validate()` exists to *inspect*, so it
  answers exhaustively; `save()` exists to *persist*, so it answers atomically and early.
- Replaces `XmlReaderWriter(schema_name="script", xmlfile=None).validate_object(obj)` —
  the `xmlfile=None` idiom `create_script` reaches for today.

**`ValidationReport` is internal, and is not part of the public surface.** It is what
`validate()` *returns*, not a name a consumer imports: callers inspect the report they are
given and never construct one, so it adds no entry to `__all__` and no entry to the API
golden. It lives beside the `run_rules` that produces its contents, in the internal
`xml/validators.py`.

Because the type is internal it gets no documentation page of its own, which makes
`validate()`'s **docstring the only place its shape is documented** — so that docstring states
the shape in full: the report is falsy when empty (`if script.validate():` reads as "there are
violations"), it iterates its violations, and each violation names its tier (T1 structural or
T2 semantic), the rule that produced it, and where in the document it applies. A caller needs
nothing beyond that, and a reader of the generated documentation must not have to open
`validators.py` to learn it.

### `CuemsScript.to_wire() -> dict`

The schema-faithful projection. **This is the UI payload.** See
[wire-format.md](wire-format.md) for the byte-identity guarantees.

**It does not validate** (CHK002, FR-005a). A projection is not a validation gate — `save()`
is the gate. The consequences, stated rather than left to be inferred:

- Projecting a half-built or semantically invalid object yields a **partial payload**, not an
  exception. `to_wire()` reports what the object holds.
- A caller wanting a guarantee calls `validate()` first. The two are separable on purpose
  (FR-006).
- `to_json()` behaves identically, so the two projections cannot diverge on this either.
- The reason is measured, not stylistic: running T1 here would cost roughly the 15.49 ms the
  direct projection exists to avoid, against a 5 ms budget on the system's hottest path.

### `CuemsScript.to_json() -> str`

`json.dumps(self.to_wire())`, with the serialization form **specified** rather than left to
`json.dumps` defaults (FR-005b) — separators, `ensure_ascii` and key ordering each change the
bytes, and this output is compared for equality:

| Parameter | Value | Why |
|---|---|---|
| `separators` | `(", ", ": ")` — the `json.dumps` default | Matches what consumers produce today; changing it would alter every recorded payload |
| `ensure_ascii` | **`False`** — *not* the default | Emits real UTF-8 rather than `\uXXXX` escapes, so `Cançó` stays `Cançó`. See the note below — this reverses an earlier draft |
| `sort_keys` | `False` | Key order comes from `to_wire()` and is part of the wire contract (W3). Sorting here would reorder the payload the UI receives |

**On `ensure_ascii`.** An earlier draft of this contract said `True`, on the reasoning that
pure-ASCII output is transport-agnostic. That reasoning is sound but answers a question nobody
asked: **both settings round-trip losslessly**, because `ç` and `ç` decode to the same
codepoint. The choice is therefore about directness, not correctness, and `False` is the better
default here for three reasons — the transport is a WebSocket text frame, which is UTF-8 by
definition; payloads carrying accented show and cue names are smaller; and a maintainer reading
a captured payload sees the text rather than its escapes. See C6.

Defined in terms of `to_wire()` so the two cannot diverge, and does not validate.

### Equality and copy

- Equality compares **declared fields only**. Two scripts that differ only in accumulated
  playback state are equal, which is what makes `load(save(x)) == load(x)` hold.
- This **widens** `Cue.__eq__`, which compares by `id` alone today — enumerated as behaviour
  change 5.
- `__hash__` stays `hash(self.id)` and stays consistent, because `id` is a declared field
  (FR-028d). It must be **preserved**, not removed: defining `__eq__` alone sets `__hash__` to
  `None` and makes every cue unhashable.
- **Copy covers both** `copy.copy` and `copy.deepcopy` (CHK008). Each produces fresh runtime
  state; the difference between them concerns declared fields only, where they behave as the
  stdlib defines.

### The `ValidationReport` shape, stated (CHK005, CHK006)

`ValidationReport` is falsy when empty (`if script.validate():` reads as "there are
violations"), iterates its violations, and reports `len()`. Each violation carries:

| Field | Meaning |
|---|---|
| `tier` | `T1` structural or `T2` semantic — so the two are distinguishable and neither absorbs the other |
| `rule` | the registered rule name for T2; the schema constraint for T1 |
| `location` | **`(cue_id, field)`** for a cue-scoped rule, **`(None, field)`** for a document-scoped one. Defined as a pair so a caller can address either without parsing a string |
| `message` | the existing rule message, preserved where already actionable |

---

## C2 — `ConfigManager` / `ConfigBase`, the config object

- The constructor is **unchanged**: `ConfigManager(config_dir)`.
- **Every existing accessor keeps its name and its meaning.** Only return types change, and
  only where the value is a structure rather than a scalar. `library_path` still returns a
  path string; `network_map` now returns node objects instead of nested dicts.
- Accessors returning objects: `network_map`, `node_network_map`, `mappings`,
  `node_mappings`, `node_conf`, and the project settings/mappings accessors.
- Accessors returning scalars are untouched.
- No accessor returns a raw nested dict.

**The authoritative per-accessor split is recorded, not listed here** (CHK036). The bullet
above is a summary and will drift; `tests/golden/api/config_accessors.json` — generated by
introspection **before** any US3 change lands (T040a) — is the arbiter. It records every public
name on `ConfigBase` and `ConfigManager` with its current return type, and T040 asserts FR-018
against *it* rather than against a list retyped into a test. That is what makes "every name that
exists today" verifiable rather than merely assertable, and it is why T040a is sequenced ahead
of every other US3 task. Counts quoted in prose ("~15 scalar", "~18 accessors") are
approximations from different vantage points; the recorded inventory is the number.

### C2 errors (CHK037, FR-014b)

Config accessors take the **same** error posture as the show surface, for the same reason —
two failure kinds a consumer must tell apart must not arrive as one exception:

| Condition | Raises | Note |
|---|---|---|
| Config file missing or unreadable | `OSError` / `FileNotFoundError`, **unwrapped** | Identical to `load()` (FR-035). A node with no config and a node with a corrupt one are different operational problems |
| Config file fails schema validation | `SchemaError`, naming the offending element | Includes the measured **X13** case — `gradient_osc_port` added as required, invalidating older files. Reported here; **fixed** under the schema evolution convention, not in this feature |
| Accessor asked for a section the document omits | The model-layer default, per the schema evolution convention | An absent optional element loads to the same object as one carrying its default |

### Config objects project like show objects

Config models expose **`to_wire()` and `to_json()`**, from the same engine that produces the
show payload — one projection implementation, not two (FR-014a).

Configuration is **not** transmitted to the UI today. The requirement exists because opening
configuration files to the UI is planned follow-on work, and the cost of building the
projection once, here, is near zero: `encode_wire` takes a schema spec and the config types
become registry-bound in this feature anyway. The cost of *not* doing it is the failure mode
this feature exists to close — a second projection written later, diverging from the first,
which is exactly how F15's three incompatible mappings shapes came about.

The guarantee is testable immediately, with no new evidence needed: the config projection is
asserted against the already-recorded `tests/golden/dict/*.config.json` goldens, exactly as
the show projection is asserted against `*.reader.json`.

**Where the method lives, and what that adds to the public surface.** "One projection
implementation" is a claim about *code*, so it is met by putting `to_wire()`/`to_json()` on the
shared `CuemsDict` base (`src/cuemsutils/helpers.py`) rather than on `CuemsScript` and again on
a config base. `CuemsScript.to_wire()` is defined there first (T026) and **relocated**, not
duplicated, when the config layer needs it (T056a) — there is never a second body, which is
what T043b asserts.

The consequence must be counted rather than discovered: putting the method on the base means
**every** `CuemsDict` subclass — every cue class, not only `CuemsScript` and the config models —
exposes `to_wire()`/`to_json()` publicly. That is intended (a cue projecting itself is
meaningful and free), but it is an addition to the recorded API surface and belongs in T057a's
enumerated expected diff, or T065's "exactly the enumerated set" fails on names nobody listed.

---

## C5 — Errors

Exceptions are **public and importable**, in `cuemsutils/errors.py`. This is the one new public
module the feature adds, and the justification is specific: a returned type can stay internal
because the caller only inspects what it is handed, but an exception the caller cannot name is
an exception the caller cannot catch. The alternative is consumers matching on message strings.

| Type | Raised by | Meaning |
|---|---|---|
| `CuemsError(Exception)` | — | Base. Lets a consumer catch everything this library raises without catching its own bugs |
| `ValidationError(CuemsError)` | `save()` | A document failed validation. Carries the **first** violation, in the same form `validate()` reports it (FR-034b) |
| `SchemaError(ValidationError)` | `load()`, `from_json()`, `save()` | Structural (T1) failure specifically, so a caller can distinguish "does not match the schema" from "violates a semantic rule" |
| `IngestError(CuemsError)` | `from_json()` | The payload is not a script at all — the actionable-message case, distinct from a script that fails validation |

**I/O failures are not wrapped** (FR-035). A missing or unreadable file raises the standard
library's `OSError`/`FileNotFoundError`, which every consumer already handles. Wrapping it
would force callers to unwrap it to find out what actually happened.

**Every public method carries a `Raises:` docstring entry** naming each type and the condition
that produces it (FR-035a). For most consumers the generated documentation is the only place
they will look, and error behaviour that is only discoverable by reading source is not
specified.

---

## C3 — What is no longer public

`cuemsutils.xml.__all__ == []`.

**Two different counts, and they are both right** (CHK017). Conflating them is what made C3's
"six" look like it contradicted SC-005's "five":

| Count | Today | After | What it measures |
|---|---:|---:|---|
| Names exported by `cuemsutils.xml` (`__all__`) | **5** | 0 | `XmlReaderWriter`, `Settings`, `NetworkMap`, `ProjectMappings`, `ProjectSettings` — this is SC-005's number |
| Supported public entry points removed | **6** | 0 | the five above **plus `CuemsParser`**, which was never in `__all__` but is reached by dotted path and is a supported entry point |

`CuemsParser` is the sixth because feature 004 made it one deliberately: it is *not* deprecated
today, it emits no warning, and `Parsers.py` records why — it is `cuems-editor`'s primary
JSON → object path and **the library calls it internally** from
`XmlReaderWriter.write_from_dict` and `read_to_objects`.

> **Sequencing constraint this creates.** Contract C8 from feature 004
> (`tests/contract/test_no_internal_deprecation.py`) asserts that no internal caller invokes a
> deprecated symbol, and it exercises `CuemsParser` **expecting silence**. Deprecating
> `CuemsParser` while the library still calls it fails that test. The two internal call sites
> (`xml_reader_writer.py:78` and `:119`) must therefore move to `Mapper.decode_document`
> **before** the shim is attached — which they do anyway once `XmlReaderWriter` becomes a shim
> over `CuemsScript.load`/`from_json`. C8 is not amended; it is satisfied.

Each of the six gets a one-release deprecation shim ([deprecations.md](deprecations.md)).

**`schema_name` disappears from every public signature.** It is a property of the type, not
of the caller — passed at six call sites across three repositories today.

---

## C6 — Text encoding: UTF-8 end to end

Show and cue names carry Latin-locale text — `Cançó d'obertura`, `Iluminación`, `Prêt-à-jouer`.
Every method that reads, writes or transmits **MUST** preserve those characters exactly.

| Boundary | Requirement | Status today |
|---|---|---|
| `save()` → XML | UTF-8 with an explicit `<?xml … encoding="utf-8"?>` declaration | **Already correct** at `xml_reader_writer.py:71-75`; the risk is T028's *new* atomic write dropping the argument |
| `load()` ← XML | Honour the document's declaration; UTF-8 when absent | Correct — `xmlschema` handles it |
| Any file access | Explicit `encoding="utf-8"`, **never** the platform default | No `open()` in `src/` omits it today; this pins it so the temp-file write does not introduce the first one |
| `to_json()` | `ensure_ascii=False`, encoded UTF-8 | New |
| `from_json()` | Accept `str`; accept `bytes` **only** as UTF-8 | New |
| `to_wire()` | `str` values are Python `str` — no encode/decode round trip | Structural |

**The failure mode this prevents is silent and environmental.** `open()` without `encoding=`
uses the platform default, which on a node booted with `LANG=C` is ASCII — so a show file with
an accented cue name saves fine on a developer's UTF-8 laptop and raises
`UnicodeEncodeError` on the node, or worse, writes mojibake. It cannot be caught by review
because the source line looks identical either way.

**The corpus cannot currently catch this: it contains zero non-ASCII bytes**, in documents and
in goldens. Measured 2026-08-18. That is a coverage gap of the same class as the eight
unexercised `FadeCue` rules, and it is closed here rather than recorded, because unlike those
rules this one is cheap to exercise and the failure is environmental rather than programmatic.

---

## C4 — Verification

| Contract | Test |
|---|---|
| C1 coercion guarantee | recursive type comparison, built vs loaded vs from-JSON, zero differences |
| C1 `save()` atomicity | invalid script + pre-existing file → raises, file unchanged byte for byte |
| C1 `validate()` collects | script with ≥3 distinct violations → report names all three |
| C1 `save()` raises first | same script → one exception, nothing written |
| C1 load runs no T2 | semantically invalid but structurally valid document loads, then fails on save |
| C1 equality | `load(save(x)) == load(x)` after mutating playback state on one side |
| C1 hashability | a cue survives `set` insertion and `dict`-key use; equal cues hash equal — the silent breakage FR-028d exists to prevent |
| C1 `from_json` inputs | all three forms accepted (`str`, UTF-8 `bytes`, `Mapping`); non-UTF-8 bytes and a non-script mapping raise `IngestError` |
| C1 T1 on ingestion | a payload with an undeclared-type value raises `SchemaError` from `from_json()` — FR-023a's decode-time check |
| C2 names frozen | every accessor name present before is present after, asserted against the recorded inventory |
| C2 no raw dicts | every accessor's return is a declared-field object or a scalar |
| C2 errors | missing file → unwrapped `OSError`; schema-invalid file → `SchemaError` naming the element; never the same type for both |
| C3 empty exports | `from cuemsutils.xml import *` binds nothing |
| C3 no `schema_name` | no public signature accepts it |
| C3 API golden | `tests/golden/api/public_api.json` diff is exactly the enumerated set |
| C5 error types | each failure path raises its declared type; no bare `ValueError`/`RuntimeError`; I/O propagates unwrapped |
| C5 carried violation | the `ValidationError` `save()` raises carries a `Violation` whose `tier`/`rule`/`location`/`message` match what `validate()` reports for the same document (FR-034b) |
| C5 `Raises:` coverage | every public method's docstring names each type and its condition |
| C6 UTF-8 round trip | a fixture with Latin-locale text survives `load → to_wire → to_json → from_json → save → load` unchanged, **byte for byte** in the written XML |
| C6 hostile locale | the same fixture passes with `LANG=C`/`LC_ALL=C` — the environment that turns a missing `encoding=` into a crash |
| C6 declaration | written documents carry `<?xml version="1.0" encoding="utf-8"?>` |
