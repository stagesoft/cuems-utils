# Public API surface diff — feature 010

**Golden**: `tests/golden/api/public_api.json`
**Re-cut**: 2026-09-04, by wave 0 (T012)
**Precedent**: feature 006's `api-surface-diff.md`. Standing rule 1 permits a golden update when
its diff is **enumerated and justified** rather than regenerated to go green.

## The diff, in full

```
ADDED    ConfigManager.get_schema_descriptor(self, schema: SchemaName)
ADDED    ConfigManager.generate_example(self, schema: SchemaName)
REMOVED  (none)
CHANGED  (none)
```

The file diff is **2 insertions, 0 deletions** — no reformatting, no trailing-newline churn. An
earlier re-cut added a trailing newline the original did not have; it was redone to match the
original byte format, so the diff shows the change and nothing else.

`tests/golden/MANIFEST.sha256` is updated for **one** entry (`api/public_api.json`):

```
old  1b5a724f5f53609c10bbe0217dff439b2ed1edd0e0eef425cb5b199455f44550
new  ae0acaee81945765f64377baf0e5b80cd717a92223a4b5f6c025448c57899ec8
```

That manifest is what makes a golden re-cut visible rather than silent — `test_golden_immutability`
failed on this change until the entry was updated deliberately, which is the guard working.

**Purely additive.** No existing name, kind or signature moved — which is the property that makes
this re-cut safe and separates it from the kind standing rule 3 forbids. Every consumer call site
that worked against the previous golden still works.

## Justification

`get_schema_descriptor` is D34's public path for the schema descriptor, and FR-023 requires the
example generators to be reachable from the same place. Both are new public surface by design
(FR-020–FR-028a); a golden that did not record them would be recording a surface the library no
longer has.

## SC-004, and why these two are exempted

Feature 006's SC-004 says **no public signature takes a schema name**, and both new methods do. The
exception is recorded in `tests/contract/test_public_api_surface.py`
(`SCHEMA_PARAMETER_EXCEPTIONS`) and as FR-028b, rather than worked around:

- SC-004 exists to stop a consumer naming a schema to do **domain** work. 006 replaced
  `manager.load("network_map")` with `manager.network_map` for that reason, and that stands
  untouched.
- Describing a schema is **meta**, and inherently parameterised by schema — there is no version of
  "describe this schema" that does not name one.
- The parameter is a `SchemaName` **enum member**, never a string, so SC-004's deeper intent — no
  stringly-typed schema naming on the public surface — is preserved rather than bypassed. A test
  asserts the exempted methods actually take the enum, so the exemption cannot be inherited by a
  method that takes a bare `str`.

Two alternative designs were considered on 2026-09-04 and rejected on measured grounds:

| Alternative | Rejected because |
|---|---|
| Six per-schema properties (`script_descriptor`, …), no parameter | Loses iteration, which is what `cuems-frontend`'s generic form renderer does. It would rebuild `SchemaName` plus a lookup table in the consumer |
| Classmethods on the owning model classes (`NetworkMap.get_schema_descriptor()`) | `outputs` has **no class at all** (both bindings `GENERIC`), and three of five `ConfigManager` accessors raise or return a bare `dict` before a document is loaded — precisely when the editor needs the descriptor |

## Known gap, recorded not fixed

`SchemaName` is new **public** surface — five repositories will import it — and the snapshot's
`PUBLIC_CLASSES` does not cover it, so no golden pins its members. The anti-drift guarantee comes
instead from `tests/contract/test_schema_name_enum.py`, which asserts the members against the
registry in both directions. Whether the API golden should also pin public *enums* is a question
this feature raises and does not settle.
