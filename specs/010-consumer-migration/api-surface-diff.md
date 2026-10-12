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

---

# Golden events — feature 010

Standing rule 1 permits a golden update when its diff is **enumerated and justified**. Four files
moved, in two unrelated groups. Both are recorded here so neither reads as a regeneration.

## Group 1 — a non-conformant fixture, corrected at the input

`tests/data/corpus/cuems-engine/projects/empty_test/script.xml` carried
`<target>00000000-0000-4000-8000-000000000000</target>`, a placeholder naming no cue. `script.xsd`
says `<!-- target uuid or none -->`, so the document was simply **wrong**, and `target_resolves`
found it — a real instance of the defect the rule exists for, in this repository's own corpus.

Corrected at the **input** (`<target />`, the schema's "none") rather than by re-cutting the output
to show the repaired value. A document with an empty `<contents />` has no cue to target, so "none"
is the truthful state; pointing it at the CueList's own id would have been a self-reference,
resolvable and meaningless.

| File | Change |
|---|---|
| `tests/data/corpus/…/empty_test/script.xml` | `<target>0000…0000</target>` → `<target />` |
| `tests/golden/xml/cuems-engine__projects__empty_test__script.xml` | same, following the input |
| `tests/golden/dict/cuems-engine__projects__empty_test__script.reader.json` | `"target": "0000…0000"` → `"target": null` |

**The `pre-008` twin is deliberately left alone.** It carries the same value, but it is read only by
the conversion tests, which do not load strictly, and it exists to represent a *real old-shape
document*. Editing it would rewrite the historical record the conversion path is tested against.

## Group 2 — the generated example was not loadable

`generate_script_example` gave `ActionCue` and `FadeCue` an `action_target` of `target_uuid`, a
freshly minted placeholder **also used as a DMX output name** — so it never resolved. Undetectable
until `action_target_resolves` existed, because nothing checked that a non-`None` action target
named a real cue.

| File | Changed leaves |
|---|---|
| `tests/golden/generated/example_script.xml` | `action_target` on `ActionCue` and `FadeCue`: `…000004` → `…000002` (the AudioCue's id). Nothing else |
| `tests/golden/generated/example_script.reader.json` | **exactly 2** changed leaves, both `action_target` |

## A capture-script defect found while doing this — NOT fixed here

`python -m tests.support.capture_goldens --force` replaced **8** goldens, not the 2 intended, and
its output for the config-dict goldens is **wrong**:

```
-"adopted": true,  "online": true,  … "schemaLocation": "…"
+"adopted": "True","online": "True"   (schemaLocation dropped)
```

That contradicts feature 007's single-schema typing exception (`network_map` decodes
`adopted`/`online` to `bool`). The capture path has drifted from the library, so **`--force` cannot
currently be trusted to regenerate config goldens**. All eight were reverted and the four files
above were applied surgically, with `MANIFEST.sha256` updated for exactly those four entries.

This is a pre-existing defect in test tooling, unrelated to feature 010's scope. Recorded rather
than fixed, because fixing it means deciding which side is right — the capture script or the
committed goldens — and that is 008's decision to revisit, not this feature's.
