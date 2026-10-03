<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Migration guide — feature 014

**This document is also the rule-4 release note.**
`specs/agreements/schema-evolution-convention.md` rule 4 requires three things of a versioned
file-format migration: *a version marker that lets a reader tell old from new; a conversion that
runs on read, or a documented tool that runs once; and a release note naming what has to be
converted and when the old form stops being accepted.* The first two exist by design
([`plan.md`](plan.md) §2); **§4 below is the third**, and it is the one deliverable that cannot be
inferred from anything else in this feature.

**It accumulates as the work lands** rather than being written at the end — 010's T002 precedent.
Sections marked *(pending)* have a task against them in [`tasks.md`](tasks.md).

---

## 1. What changes, in four sentences

1. **Booleans become real booleans.** `cms:BoolType` — an `xs:string` enum of `True`/`False` — is
   retyped to the standard `xs:boolean`, so XML text becomes `true`/`false` and the JSON wire
   carries `true`/`false` instead of `"True"`/`"False"`.
2. **`MediaType` gains four optional elements**: `pixel_width`, `pixel_height`, `file_size` and
   `file_hash`.
3. **`FadeCurveType` gains `ease_in` and `ease_out`**, cherry-picked from `main`.
4. **`ConfigManager.from_json(SchemaName, payload)`** is new: the first public way to build a
   configuration document from JSON, which is what `cuems-editor`'s `config_save` has been waiting
   for.

**No new schema version.** All of it lands in the **existing, unreleased** `script` 1 → 2 and
`network_map` 1 → 2 steps. `0.1.0rc16` does not move.

## 2. The media block is **four** elements, not three *(T008)*

The input document
([`../planning/media-pixel-dimensions-for-xml-refactor.md`](../planning/media-pixel-dimensions-for-xml-refactor.md)
§1) specifies three. **Read this instead**, and note two naming points it is easy to get wrong:

| Element | Type | Note |
|---|---|---|
| `pixel_width` | `xs:positiveInteger` | the media's **original** size, as `ffprobe` reports it — not the layer's size on screen. `width`/`height` already mean something else in `CanvasRegionType` |
| `pixel_height` | `xs:positiveInteger` | |
| `file_size` | `xs:positiveInteger` | **`file_size`, not `size`.** Bytes. Holds a file well past 100 GB — see below |
| **`file_hash`** | `cms:Md5HashType` | **the fourth, new in this feature.** 32 **lowercase** hex characters |

All four are `minOccurs="0"`, appended after `regions`. **Every existing project stays valid.**

**Three rules that are one rule:** absent means *unknown*; `0` is **not** a value and is refused by
the type; never write an empty element. `<pixel_width/>` fails `xs:positiveInteger` — which is
deliberate, since a zero-byte or zero-pixel file is not playable media.

**`file_size` holds a file larger than 100 GB, verified.** 100 GiB is 107,374,182,400 bytes, which
overflows a 32-bit int. `xs:positiveInteger` has **no upper bound** and decodes to an
arbitrary-precision Python `int`; 2⁶³ validates too. Nothing to configure.

**`file_hash` is lowercase-only**, matching `UuidType`'s existing `[a-f0-9]` pattern. `md5sum`,
`hashlib` and `ffmpeg` all emit lowercase. Uppercase is refused on purpose: a wider ingestion
vocabulary than the schema's means a value legal on the wire that can never appear in a file.

**For `cuems-engine`**: a hash is a strictly stronger "was this file replaced under the same name?"
test than comparing `file_size` against `os.stat` — a replacement of identical length passes the
size check and fails the hash. **What you compare is your decision**, including whether hashing a
multi-gigabyte file at arm time is acceptable where `os.stat` was free. The element is optional, so
an engine that ignores it is correct.

## 3. The boolean change, per consumer *(pending — T024)*

Summary now; the per-site detail lands with the work.

| Repository | What it must do |
|---|---|
| `cuems-engine`, `cuems-nodeconf`, `cuems-power-bridge`, `cuems-common` | **no source change** — they hold objects, which were always real `bool`s. **Fixtures only** |
| `cuems-editor` | **no source change** for the boolean — it returns `to_wire()` and its own FR-012 forbids touching the dict. One payload-version bump. **Its T059 closes by re-run** once §1's item 4 exists |
| `cuems-frontend` | **one line is hard-coupled and mutual**: `sequence.component.ts:997` writes `'True'`, which this feature makes a **refused** spelling, so saving fails without it — and this feature cannot ship without it. Its own `06-amendment-feature-014.md` is the authority; its 001 began its SDD path 2026-10-03 |

## 4. The release note — what must be converted, and when the old form stops being accepted

> **Rule 4's third deliverable.** *(pending — T024, T025. The shape is fixed; the per-path detail
> lands with the conversion.)*

**What must be converted**: every document carrying `<autoload>`, `<enabled>`, `<timecode>`,
`<adopted>` or `<online>` with the text `True`/`False`. Measured across the six checkouts: **96
files, 726 elements**, plus every node's live `/etc/cuems` and every project library in the field.

**How, and it is two different answers:**

| | Count | Route |
|---|---|---|
| Documents with **no `doc_version`** or version 1 | **51 files** | **Automatic.** The registry's 1 → 2 step carries the rewrite and runs on read. Nothing to do |
| Documents **already marked `doc_version="2"`** | **9 files** | **Manual, out of band.** The registry will not touch them — they are already current, so there is no step to run |

**Why the second row exists, stated plainly rather than discovered**: this feature puts the rewrite
into the *existing unreleased* version 2 rather than adding a version 3, so `doc_version="2"` is
briefly ambiguous — before and after — and the version marker cannot resolve it. That is feature
012's situation verbatim, and its lesson applies: the machinery represents such a step by the
*absence* of a registry entry, and the repair is cross-document and out-of-band **by design**. The
trade was measured, not assumed: 51 convert free, nine need hands, and six of the nine are goldens
already due for re-cutting.

**When the old form stops being accepted**: **immediately on this feature**, for reading *and*
writing. `"True"` becomes a refused spelling at `from_json` and `True` becomes invalid XML text.
There is no grace period and no dual-accept window — deliberately, because a wider ingestion
vocabulary than the schema's is a value legal on the wire that can never appear in a file.

**The order, if a document needs both migrations** (013's device shape and this one):

```
cuems-reshape-devices        # device shape — no version step
cuems-convert-documents      # 1 → 2 — now carrying the boolean rewrite
```

Reversed, neither completes: reshape-first sees a version-1 `<duration>`, convert-first sees
old-shape cues.

## 5. Rollback *(pending)*

## 6. What this feature does not do

- **No `v0.1.1` and no deprecated-surface removal** — `../planning/deprecated-surface-removal-v0-1-1.md`.
- **No `hardware_outputs`** — that is **015**.
- **No descriptor union support** — `NodeUuidType` still reports as an enumeration of one value
  ([`plan.md`](plan.md) §9.5).
- **No frontend code** — unloaded to that repository ([`plan.md`](plan.md) §6.2).
