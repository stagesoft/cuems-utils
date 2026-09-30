<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — the cluster re-mint

**Surface**: a new mode on the existing identity tool, backed by a new module. It is a
**stop-the-world operation on a live installation** — services stopped, no shows running.

## Invocation

```
cuems-init-node --remint [--dry-run] [--yes] [--library PATH] [--table FILE] [--resume]
```

**Where it runs, and what it touches there.** The two reaches have different scopes (FR-011a):

| Run on | Rewrites | Does not rewrite |
|---|---|---|
| the controller | its own configuration documents **and** the project library | — |
| any other node | **only** its own configuration documents, from the table the controller handed it (`--table`) | its replica of the library — that arrives by the project deployer's replication on project load |

A node that is not the controller and has no table **refuses** rather than minting one: a locally
minted table is precisely the divergence §10.3 warns about.

`--yes` is required to proceed, as for every destructive step in this tool (Principle III).
`--dry-run` surveys, estimates and reports, and writes nothing — including no table.

## Order of operations

1. **Survey** — classify every identity across the configuration documents and the library.
2. **Refuse** on a collision: two rows sharing an identity. Names both rows with their MACs and
   every script referencing the shared token. **Nothing has been written at this point.**
3. **Build the table** — one new uuid4 per distinct non-converged old identity, minted through
   the library's minter. Built **once, on the controller**, and distributed (FR-019c). On a node
   that is not the controller this step is skipped: the table arrives, it is not built.
4. **Persist the table** before the first write. This is the operation's only durable record.
5. **Estimate and confirm** — report the predicted duration from measured throughput and the
   surveyed byte count, then require confirmation (FR-PERF-003).
6. **Apply**, per file: read, substitute every table entry, write to a temporary, `os.replace`,
   append the path to `applied`.
7. **Verify** — zero old tokens anywhere, every touched document valid, a full load succeeds per
   node, adoption state unchanged.

## Reach

| Location | Source | Scope |
|---|---|---|
| the three configuration documents | the configuration directory | **per node** — every node rewrites its own |
| `<library_path>/projects/*/mappings.xml` | `library_path` in the configuration; optional per project | **controller only** |
| `<library_path>/projects/*/<script>` | **found by root element, not filename** (R3) | **controller only** |
| `<library_path>/trash/projects/*/…` | same; included by default (assumption 2, confirmed in code at R7) | **controller only** |

Both library forms are measured, not assumed (M-o): the mappings carry a bare identity, the
scripts carry one embedded in compound output names.

**Not rewritten**: backups of any kind. Restoring one after the re-mint reintroduces a stale
identity, and the migration guide must say so (FR-015).

## Guarantees

| | |
|---|---|
| Idempotent | a second run substitutes nothing and changes no file's bytes (FR-013) |
| Resumable | a re-run loads the persisted table rather than rebuilding it; no node receives a second new identity (FR-008) |
| Atomic per file | temporary plus `os.replace`, the pattern the identity tool already uses |
| Byte-exact elsewhere | only the 36-character tokens change; no reserialisation, no reformatting of hand-edited documents (FR-009) |
| Visible to replication | a rewritten library file's modification time advances. The substitution preserves file size exactly and the replication compares size and time with no checksum, so the time is the only signal it has. Times are never restored (FR-011b, R11) |
| Bounded | the table is keyed from node identities only, so a replacement cannot land on an unrelated uuid (FR-010) |

## Refusals

| Condition | Behaviour |
|---|---|
| Two nodes share an identity | abort before any write, naming both rows and every affected script |
| A minted value collides with an existing one | refuse; checked rather than trusted |
| `--remint` run on a node that is **not** the controller **without** a table | refuse — minting locally is the divergence this design exists to prevent. `--table` is how a plain node proceeds |
| A table arrives whose `controller` is a node that is not the map's controller | refuse — it was minted by something that had no authority to mint it |
| A plain node is asked to rewrite the library | refuse — the library is controller-authoritative and reaches this node by replication (FR-011a) |

**Not a refusal, stated because an earlier draft had it backwards**: a table whose `controller`
is not *this* node is the **normal** case on every node but one. That is what distribution means.
The refusal is on *minting* without authority, never on *using* a table another node built.
