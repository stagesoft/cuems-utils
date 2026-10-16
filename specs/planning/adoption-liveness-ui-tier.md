<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# The adoption / liveness UI tier — a product decision, not a migration

**Created**: 2026-10-14 by `015-consumer-gate-closure` (T110, FR-093a), re-homed from the residue of
`refactor-sequencing-2026-10-01.md` §4c, which is deleted in the same change.
**Status**: open, **unowned**. It has no feature number and no repository decided.

## The statement

`cuems-frontend` has **no UI tier for node adoption and node liveness**: an operator cannot see from
the UI which nodes the controller has adopted or which are online. `specs/010-consumer-migration/tasks.md`
recorded this as a *scope decision* on flow 05 (*"the adoption/liveness UI tier does not exist"*),
and `specs/013-device-class-reshape/spec.md` lists it under **Out of scope**: *"new product work, not
a migration, and it belongs to neither this feature nor flow 05's completion."*

## Why it was split out

Bundling it into the frontend's migration (flow 05) would have made a **migration's completion depend
on a product decision**. `refactor-sequencing-2026-10-01.md` §4c said to split it out *"before
starting, whenever that is"*. The frontend flow has since landed and carries an
`xml-refactor-merge-candidate` tag, without this tier — which was the intent.

## What already exists on the library side

Nothing the UI would need is missing from this library:

- `cuemsutils.tools.NodeList` — `NodeIndex`, `NodeRole`, `partition_by_adoption` (feature 013, FR-035).
- `NodeIndex.set_alias` — the operator's node label (feature 015, G4), so a UI could name nodes; its
  IPC half is `../cuems-nodeconf/specs/planning/12-node-set-alias.md`.
- `online` / `adopted` are real booleans on the wire since feature 014.

## What a decision needs

An owner and a repository (`cuems-frontend` for the tier; `cuems-editor` for any new WebSocket
action; `cuems-nodeconf` for liveness data). The coordinated `xml-refactor-merge-candidate` tags were
cut on 2026-10-16 (feature 016) **without** it, as intended, so it ships in a later release.
