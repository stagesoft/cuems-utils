# Deliberate golden changes (T080, standing rule 1)

**Feature**: 006-public-object-api · **Date**: 2026-08-20

Standing rule 1: *no existing golden is ever regenerated to make a test pass.* Exactly two
tasks in this feature **modify** a recorded golden — T080 (here) and T065 (the API surface
snapshot, recorded in `api-surface-diff.md`). Every other change under `tests/golden/` is an
addition. `tests/contract/test_golden_immutability.py` enforces this against
`MANIFEST.sha256`, which is updated in the same commit as each change.

---

## Change 1 — the written `xsi:schemaLocation` (enumerated behaviour change 4)

**What changed**

```diff
-xsi:schemaLocation="https://stagelab.coop/cuems/ @@SCHEMAS_DIR@@/script.xsd"
+xsi:schemaLocation="https://stagelab.coop/cuems/ script.xsd"
```

**Why it is a change to existing evidence and not a regeneration**

`build_document` wrote `xsd_path` — the **writing machine's absolute path** to the bundled
`.xsd`. Every show file therefore recorded the local filesystem layout of whichever node last
saved it (F24), and the goldens could not be compared at all without normalising that one
component out: `tests/support/capture_goldens.py`'s `SCHEMA_PATH_PLACEHOLDER` existed for
exactly this and for nothing else.

T037 writes `os.path.basename(xsd_path)`. Nothing resolves the value — validation always uses
the explicitly loaded schema object, never the hint in the document — so the attribute is
informational, and a machine-local absolute path is the least useful thing it could hold.

**Which files**

Stated as a **glob, never a count** (contracts §W6), so that adding a corpus document cannot
leave a golden behind in the old format. Every file under `tests/golden/` that carried the
placeholder:

```
tests/golden/xml/cuems-editor__script_minimal.xml
tests/golden/xml/cuems-engine__projects__complex_test__script.xml
tests/golden/xml/cuems-engine__projects__empty_test__script.xml
tests/golden/xml/cuems-utils__fade_showcase.xml
tests/golden/xml/cuems-utils__unicode_showcase.xml
tests/golden/generated/create_script.xml
tests/golden/generated/create_script.reader.json
```

The last two are **outside `tests/golden/xml/`** and are included deliberately. T080 names
that directory because it is where the write goldens live, but `generated/create_script.xml`
is written by the same writer and `generated/create_script.reader.json` is *read back from
that file*, so both carry the attribute. Migrating the directory and not these two would have
left the feature's own generated document in the old format — the exact failure the
glob-not-a-count rule exists to prevent, one directory over.

**Nothing else in any of the seven files changed.** The edit was a literal substitution of
`@@SCHEMAS_DIR@@/` with the empty string; no golden was re-captured by running the code.
That distinction matters: a re-capture would have made the goldens agree with the writer by
construction, which is precisely what a golden must not do.

**Consequences, all of them asserted somewhere**

| Consequence | Where it is pinned |
|---|---|
| The normalization is now a **no-op** | `test_byte_identity_xml.test_the_schema_location_carries_no_machine_path_at_all` asserts the placeholder is *absent*, reversing what that test used to require |
| Live output needs no normalization at all | `test_byte_identity_xml.test_a_freshly_written_document_needs_no_normalization` compares raw bytes through `rt.write_bytes_raw` |
| Documents are portable across install layouts | T078 (US6) writes under two monkeypatched schema directories and compares bytes |
| Files already on disk still load | `test_legacy_compatibility` — absolute, relative and absent forms, unchanged since 004 |
| `save(load(x)) == x` now holds for the two canonically-authored documents | `test_roundtrip_stability.test_a_canonically_authored_document_survives_the_first_cycle_unchanged` |

The last one was not anticipated by the task list and is worth naming. `fade_showcase.xml`
and `unicode_showcase.xml` were authored in Phase 1 in the serializer's own output form, so
the *only* thing the first save/load cycle changed about them was the schema location.
Removing it makes the first cycle the identity for those two — a strengthening of SC-003 that
`test_roundtrip_stability`'s own docstring asks a reader to notice rather than absorb. The
"first cycle is not identity" check is now scoped to the hand-indented documents, and the
stronger property is asserted positively for the two canonical ones, so "excluded" and
"untested" stay distinguishable.

**Evidence that no consumer reads the attribute**: `schemalocation-evidence.md`.
