# Contract — the editor↔UI message family

**Waves 2 and 3** | Governs FR-010–FR-013, FR-047–FR-049c, FR-088b, FR-105–FR-108

## Principle: generalise, do not invent

A config domain with **both halves already exists** — `initial_mappings` serves state and
`nodelist_modify` accepts a mutation. Every message below generalises that pair. Modelling on
`initial_template` instead would inherit a serve-only shape for domains that must accept saves
(E25/FR-088b).

Two naming cautions carried from the audit: the screen named for one configuration domain actually
edits another, and the new per-domain views must not inherit that; and a network-map edit currently
reaches the UI *inside* a mappings payload, which this feature untangles (FR-088a).

## The project-load payload

**Never byte-identical: it differs from its predecessor in an enumerated set of deltas, and that
set is defined in one place**, `cuems-editor`'s `tests/ws-command-responses.txt` ("project (reply
to project_load)"), pinned by its `tests/test_project_payload.py`. Cite it, never a count.

> ⚠ **Corrected 2026-10-17 (T068; analysis D1 missed this section).** It said "exactly two
> changes", called the **string** boolean form "verified", and said the UI writes the string form
> back. All three became false: 013 and 014 and one ruling added deltas, and 014 put native
> booleans on the wire. The table below is the enumeration as of that date, for reading only.

| # | Delta | Source |
|---|---|---|
| (a) | `schemaLocation` absent | 006, `to_wire()` |
| (b) | `Media.duration` is `{"CTimecode": "HH:MM:SS.mmm"}`, not a bare string | 008, D17/D18b |
| (c) | a hardware cue's key is `Cue` with `class`, its output's is `CueOutput` | 013 |
| (d) | a model default projected for an absent optional element (`"opacity": 100`) | ruled 2026-10-02 |
| (e) | booleans are JSON `true`/`false`, not `"True"`/`"False"` | 014 |

Unchanged: every other key and the key ordering. The UI **writes** native booleans and still
*reads* either form ("write native, read either").

`doc_version` is **not** a delta: excluded from every wire projection; the UI never sees it
(FR-012).

## Messages

*As implemented (T068, 2026-10-17)*: the family below is the editor's `schema_descriptor`,
`config_load` / `config_save` / `config_changed`, `document_load_report`, `document_load_failed`
and `payload_version` frames, all on the one websocket, all `{"type": …, "value": …}`, failures
through the editor's one error frame. The names and shapes are `cuems-editor`'s
`tests/ws-command-responses.txt`, which binds; this contract records why each exists.

### Serve a schema descriptor

Generalises `initial_mappings` from one domain to all six (contract:
[`descriptor-access.md`](descriptor-access.md)). Retires `initial_template`-as-an-instance: the UI
receives *structure and defaults*, not a cloned example document.

### Accept a configuration-domain save

Generalises `nodelist_modify` from adopt/unadopt to per-domain saves. **Adopt and unadopt must keep
working through the port** (FR-088, SC-013) — this is a migration of a screen in daily use, not a
new build.

### Repair report

Forwards the library's report unchanged in substance (FR-048). Must carry the **stale-on-disk**
indication, which under FR-048a is not informational: it is the only thing distinguishing "repaired
in memory, disk untouched" from "already fixed" (FR-048b).

**The UI must not de-duplicate a repeated report.** An unsaved repaired document is repaired and
reported on *every* open; the repetition is the signal that it is still unsaved (FR-048c).

### Unrepairable-load failure

Same channel, same family (FR-049): names the document and the failing field. Must not take down
the session or the project list — one document refuses, everything else still opens (FR-049a).
**No permissive fallback** for a document the strict path rejects (FR-049b).

This is **new user-visible behaviour** introduced by 008's strictness reversal: a project that
opened before this release can refuse to open after it. The migration guide says so (FR-049c).

### Payload-version handshake

The editor advertises a payload version on connect; a UI that does not understand it **refuses and
says so** rather than rendering a payload it cannot interpret (FR-105).

| Property | Rule |
|---|---|
| Scope | this contract only — the editor↔UI link |
| **Not** | the document-version marker, which describes a file on disk (FR-106) |
| Changes when | an existing message loses, renames or reorders a key, or changes a value's form — the editor's bump rule in `tests/ws-command-responses.txt`. Version **1** already contains all five project deltas (a)–(e); it was restated, not bumped, because it had not shipped (FR-107, corrected 2026-10-16) |
| Exists because | `cuems-frontend` has no packaging and cannot hold a release-gate edge (FR-108) |

The concrete failure it catches, which "they deploy together" does not: a **cached browser bundle**.

## Verification

- Payload compared against the **enumerated-delta** statement (five since 014), not unconditional identity (FR-013).
- All three load outcomes reachable and distinguishable from the UI (SC-011a).
- A deliberately stale bundle is refused at connect, and says why (SC-015a).
- Adopt/unadopt end to end after the port, proven by characterization tests written **before** it
  (SC-013).
