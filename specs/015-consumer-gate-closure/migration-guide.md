<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Migration guide — feature 015, the consumer-gate closure

**Feature**: `015-consumer-gate-closure` | **Written**: 2026-10-13
**Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md) | **Data model**: [data-model.md](data-model.md)
**Consumer obligations**: [consumers_works.md](consumers_works.md) — the measured, per-repository counterpart to this file

This document is for the maintainer of **one** consumer repository, and for this repository's
own release record. Find your repository below; if your repository is not named, this feature
makes no change you need to react to.

---

## 1. Sibling obligations (FR-008, FR-046, FR-103)

Nine gates, ten obligations — the full breakdown, measured per site, lives in
[consumers_works.md](consumers_works.md). The short form:

| Gate | This library | The sibling half |
|---|---|---|
| G1 | `must_exist=False` on both path helpers | `cuems-editor` must pass the flag on at its own `_config_path` write site (FR-008) |
| G2 | `project_settings` becomes publicly readable | `cuems-editor` must remove its refusal entry and add a load step (FR-017) |
| G3 | the descriptor's instance is wire-shaped and saveable | `cuems-frontend` deletes its hand-written `toWireShape` transform in one edit (FR-031); `cuems-editor` corrects a docstring that becomes false |
| G4 | `NodeIndex.set_alias` | `cuems-nodeconf` ships the `node_set` IPC handler (FR-046/FR-047), verified word for word against `../cuems-nodeconf/specs/planning/12-node-set-alias.md` §4 |
| G5 | the version step addresses both player shapes | none — this is this library's own defect |
| S1 | `NodeIdentityCollisionError` carries structured data | `cuems-editor` deletes its regular expression over this library's prose (FR-065b) |

## 2. The sanctioned golden event (FR-074)

Executed once, in the polish phase, after every public addition and after the writer change —
see §6 below for the record once it runs.

## 3. The operator triage question (FR-058, G5)

Not *"is it flat-shaped?"* — two different populations, because 013's reshape and F3's retired
counts are independent axes. The correct question:

```bash
grep -cE '<(audio_cards|universes)>' /etc/cuems/settings.xml    # non-zero -> affected
```

## 4. Cross-repository assertion-class split (FR-080)

Recorded once T097–T104 land — see §7 below.

## 5. Planning-folder disposition table (FR-093)

Recorded once T109–T115 land — see §8 below.

## 6. G4 — `NodeIndex.set_alias`, verified against the two-repository contract (T050)

`NodeIndex.set_alias(node_uuid, alias: str | None) -> bool` was checked word for word against
`../cuems-nodeconf/specs/planning/12-node-set-alias.md` §4, which states this library's half of
the contract identically. Agreement, item by item:

| That document's §4 | This implementation |
|---|---|
| "Validates first: `alias` must be `None` or a string matching `NonEmptyString`, else `ValueError`, raised **before** any node is touched" | matches — the blank/empty check runs before the search loop |
| "Mutates in place, on the node object the document holds" | matches — the same aliasing contract `adopt`/`unadopt` already document |
| "Returns `False` for an unknown uuid and `True` otherwise, whether or not the value changed" | matches |
| "`signature()` already includes `alias`, so the write-if-changed path needs no change" | verified (T049) — `NodeIndex.signature` already reads `n.get("alias")` |

No divergence found. `cuems-nodeconf`'s own `alias_node` (its §5b) is written against exactly this
signature, catching `ValueError` and checking `found`/`signature()` in that order — unblocked by
this landing, not yet shipped (§1 above).

---

*Sections below are filled in as each phase of `tasks.md` lands.*
