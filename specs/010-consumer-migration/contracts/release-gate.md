# Contract — the release gate

**Waves 4 and 5** | Governs FR-091–FR-097, FR-100–FR-108, FR-029–FR-029d

## The claim the gate makes

> An unmigrated consumer must refuse a library that has moved past it.

That is an **upper bound or a `Breaks:`**. A `>=` floor says only "I need at least this" and cannot
express it. Today exactly one edge in the ecosystem expresses the gate.

## Edges

| Repository | Today | After |
|---|---|---|
| `cuems-common` | `>= 0.1.0rc15` **+ `Breaks:`** | unchanged — the model for the others |
| `cuems-engine` | `>=0.1.0rc10` (pyproject) / `>= 0.1.0rc4` (control) | **reconciled** (FR-092) + bound |
| `cuems-editor` | `>=0.1.0rc10` (pyproject), no `debian/` | bound; packaging decided in wave 4 |
| `cuems-nodeconf` | `>=0.1.0rc15` / `>= 0.1.0rc5` | bound |
| `cuems-wsclient` | `>=0.1.0rc5`, **optional** | non-optional + bound (FR-053) |
| `cuems-frontend` | not packaged | **no edge possible** → the payload handshake instead (FR-108) |

**The demonstration is run, not described** (FR-093): install an out-of-order combination and watch
the package manager refuse it. 007 deferred this here precisely because no releasable package
existed before this feature; 008 then added a second breaking change to the same gate without
adding an edge.

## Three cutover classes

| Class | Dual state? | Consequence |
|---|---|---|
| 007's role rename | **No** | hard cutover; "the library releases first" does not apply |
| 008's duration change + load strictness | **No** | hard cutover **plus** a data migration |
| 006's show-API deprecations | **Yes** — all six still resolve and warn | the only class the library can lead; wave 5 closes it |

Keeping these apart is load-bearing (FR-097): collapse them one way and wave 5 looks impossible;
collapse them the other and two hard cutovers get a release-first story they cannot have.

## Rollback: two procedures, one boundary

| Boundary | Procedure |
|---|---|
| **Before** the operator runs the show-document conversion | package downgrade, nothing else — documents are still version 1 and the previous library reads them (FR-101) |
| **After** it | package downgrade **plus** restore from the conversion backups (FR-102) |

**The boundary must be checkable** without inspecting documents by hand (FR-103) — the no-write
check mode on the conversion command (research R4). A procedure beginning "if you converted" with
no way to answer that is not a procedure.

**Retention** (FR-102): backups are retained **indefinitely**; the conversion never reclaims them.
Reclamation is an explicit operator action, recommended no earlier than after the post-upgrade
verification has passed *and* one full show cycle has run (research R5).

**No reverse conversion** (FR-104): the conversion registry is forward-only by construction, one
transformation drops a block and is not reversible, and building one would be new library
capability in a feature that sanctions exactly one. Recorded so it is not re-proposed as an obvious
convenience.

## Ordering constraints — all three, named together

1. Configuration conversion vs. service restart, both in `postinst` (FR-094).
2. Controller vs. node upgrade. **Nodes first is safe** — older documents convert in memory on
   read. Controller-first with un-upgraded nodes still receiving deployments is the dangerous one.
3. A converted controller deploying to an un-upgraded node (FR-036/FR-096): fails at **show-load
   time, not upgrade time**, mediated by no package manager.

## The wave-5 precondition

Deletion is gated on a **measured** count, not on "the flows are merged" (FR-029). The census —
per repository, per path, with the command that produced it — is written to `import-census.md` and
**re-run immediately before the deletions**; a repository can regress between merge and removal.

Required value: **zero**. Known live consumers today: `XmlReaderWriter` (engine `BaseEngine.py:17`,
editor `CuemsDBProject.py:10`, `repair_durations.py:40`), `NetworkMap` (engine
`ControllerEngine.py:12`, editor `CuemsWsServer.py:23`), `CuemsParser` (editor
`CuemsDBProject.py:9`, `repair_durations.py:39`), `Timeoutloop` (nodeconf `CuemsNodeConf.py:26`).

Then: five shim modules, the seven aliases, the four deprecated-symbol sites, and `__version__` to
the release every warning since 006 has promised — or the divergence recorded (FR-029c).

**Two cautions**: the retiring of the 22 contract tests is deliberate and must be stated, not
silent (FR-029b); and the two similarly-named parser symbols are different — one is a retired
alias, the other a façade contractually required to stay silent (FR-029d).
