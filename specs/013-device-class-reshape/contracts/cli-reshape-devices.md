<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — `cuems-reshape-devices`

**Feature**: `013-device-class-reshape` | **Requirements**: FR-022 – FR-027, FR-029
**Decision record**: research [R6](../research.md) — a new entry point rather than a second mode of
`cuems-convert-documents`, because that tool's only discriminator is the version marker
(`convert_documents.py:76-79`) and this migration moves no marker.

---

## Synopsis

```
cuems-reshape-devices [--check] [--dry-run] [--conf PATH] [--library PATH] [PATH...]
```

Migrates every old-shape document in an installation to the class-carrying shape, once. With no
`PATH`, it discovers the installation: the configuration documents under `CUEMS_CONF_PATH` (default
`/etc/cuems`) and every project in the library — scripts and mappings — through
`tools/library_reach.py`, which already resolves `library_path` from `settings.xml` and walks
`projects/` and `trash/projects/`.

**Scripts are found by root element, not filename** (FR-023). `script_file_name` is an
editor-internal dict key and appears in no document this library reads; feature 012 measured this and
`library_reach.root_local_name` is the implementation.

---

## Modes

| Mode | Writes | Purpose |
|---|---|---|
| default | yes | migrate every old-shape document found |
| `--check` | no | report what would be migrated, and exit non-zero if anything is old-shape |
| `--dry-run` | no | the full plan, per document, including the backup path each would get |

---

## Per-document behaviour

1. Parse with stdlib `xml.etree.ElementTree`. A document the reshape must read may be invalid against
   the current schema — that is the normal case — so no schema decode happens before the rewrite.
2. Identify the schema by **root element** (`SCHEMA_ROOTS`), as `convert_documents._schema_name_for_root`
   does. An unrecognised root is skipped and named.
3. Classify the shape: old (carries a reshaped element name at its reshaped position), new (carries
   the container), or not applicable. The two cannot coexist (FR-021), so the classification is exact.
4. **Back up before rewriting**: `<name>.<YYYYMMDDTHHMMSS>.bak` beside the original, via
   `shutil.copy2`, exactly as `convert_documents.py:81-85`. A backup failure is **fatal for that
   document only** (FR-025) — the document is left unrewritten and the run continues.
5. Reshape in place (the transformations are tabulated in [data-model.md](../data-model.md) §6), then
   **validate against the current schema** before writing. A document that would not validate is not
   written, and the failure names the document and the element that failed.
6. Write atomically through `documents.write_tree` (`mkstemp` + `os.replace`, mode preserved).
7. **Leave `doc_version` alone** (FR-020). A reshaped document carries the same marker it arrived
   with.

**Idempotence** (FR-026): a second run finds every document new-shape, reports "nothing to do", and
changes no file's bytes — asserted on bytes, not on the report.

---

## Output

One line per document, in the `<path>: <verdict>` form feature 011 established:

```
/etc/cuems/settings.xml: reshaped
/etc/cuems/default_mappings.xml: reshaped
/etc/cuems/network_map.xml: not applicable
<library>/projects/<p>/script.xml: reshaped
<library>/projects/<q>/script.xml: already current
<library>/projects/<r>/mappings.xml: skipped (backup failed; document left unrewritten)
```

A closing summary names the counts and, when anything was written, the backup location pattern.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | every document is new-shape — migrated now or already |
| 1 | at least one document was skipped, or (`--check`) at least one is still old-shape |
| 2 | usage error, or the installation could not be resolved (no `settings.xml`, unreadable library) |

---

## The diagnosis this tool is named by (FR-027)

Reading an un-migrated document through the library must not produce a bare `xs:sequence`
"unexpected child" complaint — the X13 failure mode this project vendors two broken settings files as
evidence of. The load path therefore classifies the failure by shape and raises with the document, the
old shape and this tool named:

```
project_mappings document /etc/cuems/default_mappings.xml is in the pre-013 device shape
(<audio>/<video>/<dmx> on <node>). Run `cuems-reshape-devices` to migrate it.
```

Asserted **on the message**, not on the exception type (SC-005): `xmlschema`'s own validation errors
are `ValueError` subclasses too, which is the distinction feature 008 had to make.

This diagnosis lands in the **same commit as the first schema edit**. A commit that narrows a schema
without it leaves exactly the error message this requirement exists to prevent.

---

## What this tool deliberately does not do

- **No rollback.** The backup is the rollback, and the migration guide states the point after which it
  stops being usable (FR-028).
- **No cluster scope.** It migrates the installation it runs on. Unlike feature 012's re-mint there is
  no table to distribute: the transformation needs no information from any other node.
- **No version conversion.** `cuems-convert-documents` still owns that, unchanged.
- **No identity work.** Feature 012's identities, sentinel and `--remint` are untouched (A8).
