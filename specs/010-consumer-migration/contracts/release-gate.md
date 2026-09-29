# Contract — the release gate

**Waves 4 and 5** | Governs FR-091–FR-097, FR-100–FR-108, FR-029–FR-029d

## The claim the gate makes

> An unmigrated consumer must refuse a library that has moved past it.

That is an **upper bound or a `Breaks:`**. A `>=` floor says only "I need at least this" and cannot
express it. When this contract was written **exactly one** edge in the ecosystem expressed the gate;
re-measured 2026-09-25 it is **three, plus one half-closed** — see the table below.

## Edges

| Repository | As audited 2026-09-03 | After |
|---|---|---|
| `cuems-common` | `>= 0.1.0rc15` **+ `Breaks:`** | unchanged — the model for the others |
| `cuems-engine` | `>=0.1.0rc10` (pyproject) / `>= 0.1.0rc4` (control) | **reconciled** (FR-092) + bound |
| `cuems-editor` | `>=0.1.0rc10` (pyproject), no `debian/` | bound; packaging decided in wave 4 |
| `cuems-nodeconf` | `>=0.1.0rc15` / `>= 0.1.0rc5` | bound |
| `cuems-wsclient` | `>=0.1.0rc5`, **optional** | non-optional + bound (FR-053) |
| `cuems-frontend` | not packaged | **no edge possible** → the payload handshake instead (FR-108) |

### Re-measured 2026-09-25 — three edges closed, two open, one half-closed

The table above is the 2026-09-03 audit and is kept as that record. Two of its rows are now misleading
if read as current: the `cuems-wsclient` row is **`cuems-power-bridge`**'s, under the name the list
still used before the 2026-09-18 identity correction (one repository, renamed in 2026-06 — so this
table has **six** rows for six repositories, and T076's entry is that row, not a seventh). And three
repositories have since moved.

| Repository | `pyproject.toml` | `debian/control` | Expresses the gate? |
|---|---|---|---|
| `cuems-common` | — | `:12` `>= 0.1.0rc16`, `:13` `<< 0.1.1~` | ✅ |
| `cuems-nodeconf` | `:28` `>=0.1.0rc16,<0.1.1` | `:18` `>= 0.1.0rc16`, `:19` `<< 0.1.1~` | ✅ **the model to copy** |
| `cuems-power-bridge` | `:38` `>=0.1.0rc16,<0.1.1`, non-optional | `:18` `>= 0.1.0rc16`, `:19` `<< 0.1.1~` — **bounded 2026-09-29** (`399baf7`) | ✅ |
| `cuems-engine` | `:41` `>=0.1.0rc10` | `:18` `>= 0.1.0rc4` | ✗ **and the two disagree with each other** |
| `cuems-editor` | `:27` `>=0.1.0rc10` | no `debian/` directory | ✗ |
| `cuems-frontend` | not packaged | not packaged | n/a — handshake only |

**What this changes for the argument, not just the numbers.** When this contract was written,
`cuems-common` was the *only* edge and the gate had to be argued for. It is now a convention **three
sibling repositories follow**, and what remains is two holdouts plus one half-closed edge. Cite
`cuems-nodeconf`'s `debian/control:18-19` as the pattern rather than re-deriving the reasoning.

**T076 is not closed by the bridge's `pyproject.toml` alone.** Its source pin expresses the gate and
its packaged pin does not — which is the *exact* distinction this contract's opening claim rests on. A
`>=` floor in `debian/control` is what `dpkg` actually enforces; a bound in `pyproject.toml` is not.

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
verification has passed *and* at least one show has been loaded from the converted library and run to completion on the cluster (research R5).

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

**Re-measured 2026-09-25 — one moved, one closed, and one the denominator does not reach:**

- `ControllerEngine.py:12` is now **`:15`**; six commits landed on `cuems-engine`'s working branch and
  moved every line number in that file. `BaseEngine.py:17` and every editor site are **unchanged**.
- `Timeoutloop` in `cuems-nodeconf` is **closed** — that repository's features 001 and 002 landed, and
  `grep -rn "from cuemsutils\.\(xml\|config\)" cuemsnodeconf/` returns no matches.
- **A sixth consumer the list does not reach**: `../cuems-editor/tests/test_repair_durations.py:6`
  imports `XmlReaderWriter`. The enumeration above is drawn from `src/` only, so a test import falls
  outside the required-zero count — and still breaks when the shim goes. `cuems-nodeconf` set the
  precedent: keep it and **label** it `# test-only (FR-007)`, so a census can tell a shipped consumer
  from a test deliberately exercising the old path. **T049's census method must state whether it counts
  test files.** Right now it neither counts them nor says it does not, which is the same class of
  hand-maintained-denominator failure the repository-identity correction was about.

Then: five shim modules, the seven aliases, the four deprecated-symbol sites, and `__version__` to
the release every warning since 006 has promised — or the divergence recorded (FR-029c).

**Two cautions**: the retiring of the 22 contract tests is deliberate and must be stated, not
silent (FR-029b); and the two similarly-named parser symbols are different — one is a retired
alias, the other a façade contractually required to stay silent (FR-029d).
