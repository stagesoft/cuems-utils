<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — the public surface this feature adds

**Phase 1** · 2026-10-13 · every addition, with its exact shape and its refusals.

**The governing rule** (FR-100): everything here is **additive**. No existing public call changes
its signature's meaning, its default behaviour, or its exception type. The one behaviour change is
G5's, and it is a defect fix in the direction of succeeding where the tool previously refused.

Two goldens pin signatures as strings and are re-cut as part of this feature:
`tests/golden/api/public_api.json` and `tests/golden/api/config_accessors.json`.

---

## C1 — Tolerant configuration write targets (G1)

```
ConfigBase.conf_path(file_name: str, *, must_exist: bool = True) -> str
ConfigManager.project_path(project_uname: str, file_name: str, *, must_exist: bool = True) -> str
```

| Contract | Statement |
|---|---|
| default | `must_exist=True` — identical to today for all 10 in-package call sites and every consumer |
| `must_exist=True`, file absent | `FileNotFoundError`, same message as today |
| `must_exist=False`, file absent | the canonical path, no error |
| `must_exist=False`, file present | the canonical path |
| keyword-only | enforced by `*`, so no positional call site can acquire tolerance by accident |
| side effects | **none**. No file and no directory is created by resolving a path |
| parent directory absent | still fails **at write time**, unchanged and deliberately not addressed |

**Not in this contract**: a call that ingests, resolves a target and persists. Declined twice — the
spec's SET-8, and 014's own plan decision that `from_json` returns the object and `save_*` writes what
the manager holds.

**Consumer note, recorded because it decides whether the gate reads as closed**: `cuems-editor`'s
strict xfail for G1 does **not** flip on this change alone. That repository must also pass the flag
on at its own write site; its `tag-readiness.md` says so.

---

## C2 — A public read for a project's settings (G2)

```
ConfigManager.project_settings  ->  CuemsProjectSettingsType      # property
ConfigManager.to_wire('project_settings') -> dict
```

| Contract | Statement |
|---|---|
| after a load that found the file | the decoded document; `to_wire` projects its actual values |
| after a load that found **no** file | an **empty** document; `to_wire` projects `{}` |
| before any project load | the existing "not loaded" failure — **unchanged and distinct** |
| projection body | the **same** one every other section uses. A second projection is forbidden |
| section name | `'project_settings'` joins the public section set, so the error that enumerates valid sections names it |
| round trip | `to_wire('project_settings')` → `from_json(SchemaName.PROJECT_SETTINGS, …)` → `save(path)` → reload compares **equal** |

**Why `{}` is the right empty answer, not `{"setting": []}`**: the schema declares the settings
element `minOccurs="0"`, so zero settings is a valid document, and the projection's existing rule
omits an optional empty field. Measured: an empty document saves, and projects `{}`.

**Existence is the consumer's question**, answered by C1's existence-checking form. The projection
does not acquire an existence flag — that would be a second answer to a question one call already
answers.

---

## C3 — The descriptor's instance, in wire shape and saveable (G3)

No new call. `get_schema_descriptor(schema)` keeps its shape; the per-type `instance` changes.

| Contract | Statement |
|---|---|
| nesting | a repeated complex field is a **list of singly-keyed objects**, as the wire nests it — in every schema |
| wrapper | a document-body type carries the wrapper the wire carries |
| anonymous single child | expanded, not `null` |
| scalars | seeded — see [seeding-rules.md](seeding-rules.md) |
| completeness | every declared non-wildcard field is present |
| saveability | **every** root instance, and every nested type instance a consumer names, passes this library's write path unmodified |
| callable defaults | **not invoked**; still visible on the field |
| `FieldDescriptor.default` | **unchanged** |
| repairability classification | **unchanged for every field** — the invariant this gate must not break |
| serialisability | nothing non-serialisable enters the instance |

**The mechanism is a contract too**, because it is what keeps the first three rows true next year:
the instance is produced by populating a value and projecting it through the **same encoder**
`to_wire()` uses. A future change to the wire shape moves the instance with it, automatically.

---

## C4 — The operator's node label (G4)

```
NodeIndex.set_alias(node_uuid, alias: str | None) -> bool
```

| Case | Result | Mutates? | Signature moves? |
|---|---|---|---|
| known node, valid non-blank label | `True` | yes, **in place** | yes |
| known node, label equal to the current one | `True` | no change | **no** |
| known node, `None` | `True`, key **removed** | yes, in place | yes |
| unknown identity | `False` | **no** | no |
| label present but empty or blank | **raises** | **no — validated first** | no |
| offline node, or the controller | as above; liveness is **not** a precondition | | |

**Validation precedes mutation**, and this is the clause with an incident behind it: an in-place
empty label makes the subsequent save fail *after* the index has changed, and the daemon's
pending-write retry then fails on that row until restart.

**In-place is contractual**, not incidental: callers hold these node objects through more than one
reference, which is what makes a concurrent adopt unlosable in a daemon that takes no lock across
its worker loop and its comms thread. Rebinding a copy would break a consumer while leaving every
suite green.

**Scope is `alias` only** (FR-042). A general "set operator fields" call is deliberately not
offered, because it would invite writes to fields discovery overwrites.

**Documentation obligations in the same change** (FR-045): the docstrings of the map's save and
ingest paths must state that the file has exactly **one runtime writer** and that any other writer's
changes are reverted at that writer's next write. Two consumers have already read those calls as the
way to persist a UI edit.

**This contract is stated identically** in `../cuems-nodeconf/specs/planning/12-node-set-alias.md` §4.
Any divergence here is a change to a two-repository contract.

**`NodeIndex` joins the recorded public surface in the same change** (FR-041a). Measured 2026-10-13:
the API golden tracks `CuemsScript`, `ConfigManager` and `ConfigBase` as classes and
`partition_by_adoption` / `validate_config_document` as functions, so `NodeIndex` is in **neither**
golden — this signature would otherwise be the one public addition of the feature with no recorded
shape, in a module that has been *"the only public path to the node model"* since feature 007.

---

## C5 — The identity collision, as data (S1)

```
cuemsutils.errors.NodeIdentityCollisionError(ValidationError)
    .collisions   # each colliding identity with the hardware addresses carrying it
    .file         # the document's path
    .violation    # located as (identity, "uuid")
```

| Contract | Statement |
|---|---|
| base | `ValidationError`, so a consumer catching the general case keeps catching this one |
| raised by | the public **accessor**, which is where the file path exists |
| raised by the rule | an **internal** `ValueError` subclass carrying the same data — `isinstance(exc, ValueError)` still holds everywhere it holds today |
| message | **unchanged**, including the remedy sentence and the command it names |
| message-shape recognition | keeps answering for any caller still on it |
| two distinct collisions | distinguishable without re-parsing text |
| published | in the errors module's `__all__`, its documented hierarchy, **and the recorded surface** |

**"Published" means three places, and two of them do not follow the code** (FR-065c). `__all__` is
asserted **equal** to a hand-maintained `PUBLIC_ERRORS` tuple in
`tests/contract/test_public_api_surface.py`, and `api/public_api.json`'s `errors` section is
**generated from that tuple**. So adding to `__all__` alone turns an existing contract test red, and
re-cutting the golden without extending the tuple yields a golden that omits the new class. All
three move together.

**The two layers are the contract, not an implementation detail.** The accessor's handler orders
`except ValidationError: raise` **before** the clause that attaches the file path, so a
`ValidationError` subclass raised inside the validator would lose the one field the accessor exists
to add. Keeping the internal exception a `ValueError` also preserves `tests/golden/outcomes.json`,
which pins the internal reader's raw verdicts document by document.

---

## C6 — A union is not an enumeration (S2)

| Contract | Statement |
|---|---|
| all members enumerated | the merged values are reported, as today |
| any member not enumerated | **no** closed choice set is reported |
| every other fact | unchanged |

Five sites stop reporting a one-value choice set: three node-identity fields across three schemas,
and **two numeric latency fields** — the case the planning document did not record, and the worse of
the two, because `0–500` are valid and a form was offering only `auto`.

---

## C7 — The written document indents (S3)

| Contract | Statement |
|---|---|
| output | indented and line-broken |
| idempotence | a document this library wrote, reloaded and rewritten, is **byte-identical** |
| text that is data | never altered — guaranteed by the stdlib indenter's own behaviour on mixed content, verified |
| atomicity, mode preservation, prefix registration, encoding, declaration | all unchanged |

**Golden event** (one reviewable change, **executed in the polish phase**): six XML goldens, two API
goldens and the manifest. The **24** wire-dict goldens,
`generated/example_script.reader.json` and the outcomes record are unaffected — a wire dict carries
no whitespace. The two canonically-authored corpus documents are re-authored with S3 itself, since
they are input data rather than recorded output.
⚠ **Scheduled after every public addition, not with the change that moves each golden.**
`public_api.json` enumerates every public error class, so S1's new exception moves it exactly as G1's
signatures and G2's property do — and S1 lands five phases after the re-cut this plan originally
scheduled inside G2. Counted on disk 2026-10-13; this said 20 wire-dict goldens and two API goldens
for two additions.

---

### C7's byte-level reach, enumerated (FR-074, FR-075, FR-075a)

Eight goldens plus the manifest, and **five hand-authored documents**: the two canonical corpus
documents (`fade_showcase.xml`, `unicode_showcase.xml`) and the **three 007 pre-state**
`network_map.xml` documents, which `tests/contract/test_network_map_roundtrip.py` diffs `save()`'s
output against while asserting the diff is **exactly two lines** — a claim that holds only while the
document is one line. Measured 2026-10-13: all three are one line. Re-authored rather than compared
structurally, because that test's value is a rename a human can read in a diff.

---

## C8 — What is deliberately **not** added

Each of these was asked for at least once and is declined with its reason, so a later pass does not
re-propose it.

| Not added | Reason |
|---|---|
| one call that ingests, resolves the target and persists | SET-8; 014 settled the split deliberately |
| a content-hash helper for revision tokens | SET-7; the md5 type is a media field and is not generalised |
| an existence flag on the configuration projection | C2 — one call already answers that question |
| a general "set operator fields" call on the node index | C4, FR-042 — it would invite writes to fields discovery overwrites |
| per-field defaults as the route to a saveable instance | it would move 64 fields across 19 types from unrepairable to repairable, changing the load path's strictness ecosystem-wide |
| an engine-side configuration reload | SET-9; not this repository's |
| a schema version step | FR-101; these are public-surface and defect changes |
