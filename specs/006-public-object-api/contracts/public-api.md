# Contract: the public API surface

**Feature**: 006-public-object-api · **Date**: 2026-08-18

After this feature the library has **two** public entry points. Everything else is internal.
Each method below states its signature, its guarantee, its error behaviour and its
deprecation counterpart. The error behaviour is not uniform, and the differences are
deliberate.

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

### `CuemsScript.to_wire() -> dict`

The schema-faithful projection. **This is the UI payload.** See
[wire-format.md](wire-format.md) for the byte-identity guarantees.

### `CuemsScript.to_json() -> str`

`json.dumps(self.to_wire())`. Defined in terms of `to_wire()` so the two cannot diverge.

### Equality and copy

- Equality compares **declared fields only**. Two scripts that differ only in accumulated
  playback state are equal, which is what makes `load(save(x)) == load(x)` hold.
- Copying a cue produces **fresh** runtime state rather than sharing thread handles.

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

---

## C3 — What is no longer public

`cuemsutils.xml.__all__ == []`.

Removed from the public surface, each with a one-release deprecation shim
([deprecations.md](deprecations.md)): `XmlReaderWriter`, `CuemsParser`, `Settings`,
`NetworkMap`, `ProjectMappings`, `ProjectSettings`.

**`schema_name` disappears from every public signature.** It is a property of the type, not
of the caller — passed at six call sites across three repositories today.

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
| C2 names frozen | every accessor name present before is present after |
| C2 no raw dicts | every accessor's return is a declared-field object or a scalar |
| C3 empty exports | `from cuemsutils.xml import *` binds nothing |
| C3 no `schema_name` | no public signature accepts it |
| C3 API golden | `tests/golden/api/public_api.json` diff is exactly the enumerated set |
