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
| `cuems-engine` | `:41` `>=0.1.0rc10` | `:18` `>= 0.1.0rc4` | ✗ **and the two disagree with each other** — **closed 2026-09-30**, see the row below |
| `cuems-editor` | `:27` `>=0.1.0rc10` | no `debian/` directory | ✗ — **closed 2026-10-02**, see the row below |
| `cuems-frontend` | not packaged | not packaged | n/a — handshake only |

**What this changes for the argument, not just the numbers.** When this contract was written,
`cuems-common` was the *only* edge and the gate had to be argued for. It is now a convention **three
sibling repositories follow** — `cuems-common`, `cuems-nodeconf` and, since 2026-09-29,
`cuems-power-bridge` — and what remains is the two holdouts that cannot express it at all. Cite
`cuems-nodeconf`'s `debian/control:18-19` as the pattern rather than re-deriving the reasoning.

**T076 was not closed by the bridge's `pyproject.toml` alone**, and the distinction is the *exact*
one this contract's opening claim rests on: a `>=` floor in `debian/control` is what `dpkg` actually
enforces; a bound in `pyproject.toml` is not. **Closed 2026-09-29** (`../cuems-power-bridge`
`399baf7`) by adding `cuems-utils (<< 0.1.1~)` at `:19`. Verified with `dpkg --compare-versions`:
`0.1.0rc16` and `0.1.0rc17` satisfy both bounds; `0.1.1~rc1`, `0.1.1` and `0.2.0` are refused — and
`0.1.1` is the release **T060** removes the deprecated surface in, so the bound now refuses exactly
the library version that would break this consumer at runtime.

## T077 — the `cuems-common` ↔ `cuems-power-bridge` edge, decided

An edge FR-091 did not enumerate, because when FR-091 was written this repository was not on the
list. `Suggests:` carries no version, so nothing refused a new tool beside an old bridge or the
reverse. **Decision: `Suggests:` stays unversioned; the side that changed first acquires the
`Breaks:`.** Both halves are in the tree, verified 2026-09-29:

| Side | Relation | Why |
|---|---|---|
| `cuems-common` | `Suggests: cuems-power-bridge` — **unversioned, deliberately** — plus `Breaks: cuems-power-bridge (<< 0.3.1-1)` | It changed first: `cuems-cluster-poweroff` now selects through the bridge's topology adapter, which older bridges do not have |
| `cuems-power-bridge` | `Breaks: cuems-common (<< 1.3.0-23)` | The reciprocal half |

**`Suggests:` must stay as it is.** It is deliberately not `Depends:`/`Recommends:` so `cuems-common`
remains functional on a host with no bridge — promoting it would make a controller-only, opt-in
feature a mandatory dependency of the package every node installs. Both scripts already log one
ERROR and exit 0 when the venv interpreter is absent. The reasoning is recorded in a comment beside
the relation in `cuems-common`'s `debian/control`, not only here.

The pair now upgrades together or `dpkg` refuses, instead of the mismatch surfacing as an
`AttributeError` part-way through a poweroff transaction.

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


### Re-measured 2026-10-02 — **all five edges closed** (T037b, T038)

The two holdouts have both moved, and FR-091's enumeration is complete.

| Repository | `pyproject.toml` | `debian/control` | Expresses the gate? |
|---|---|---|---|
| `cuems-common` | — | `:12` `>= 0.1.0rc16`, `:13` `<< 0.1.1~` | ✅ |
| `cuems-nodeconf` | `:28` `>=0.1.0rc16,<0.1.1` | `:18`/`:19` | ✅ |
| `cuems-power-bridge` | `:38` `>=0.1.0rc16,<0.1.1` | `:18`/`:19` (`399baf7`) | ✅ |
| `cuems-engine` | `:50` `>=0.1.0rc16,<0.1.1` | `:26` `>= 0.1.0rc16`, `:27` `<< 0.1.1~` | ✅ **the two floors now agree** — the one reconciliation T038 asked for |
| `cuems-editor` | `:27` `>=0.1.0rc16,<0.1.1` | `:18`/`:19`, in a `debian/` acquired at `9067b1a` from `debian/bookworm` @ `72f952a` | ✅ **T037b's precondition and T038's edge, in one landing** |
| `cuems-frontend` | not packaged | not packaged | n/a — payload handshake (FR-108); the editor now sends `payload_version` 1 as its first frame |

**The convention is no longer argued for; it is what every packaged repository does.** Cite
`cuems-nodeconf`'s `debian/control:18-19` as the pattern.

## ⚠️ What closing the gate obliges, which this contract did not say

Five `debian/control` files now carry `cuems-utils (<< 0.1.1~)`. **T060 moves this library to
`v0.1.1`.** `dpkg --compare-versions` refuses `0.1.1` against every one of them — correctly, since
`0.1.1` is the release that removes the surface a pre-migration consumer would still import. The
consequence:

**The version move and the re-bound of five sibling packages are one atomic step.** Not a
version bump followed by five follow-ups. A library at `0.1.1` beside five packages bounded
`<< 0.1.1~` is an ecosystem that will not install at all, and the failure is at `dpkg` time on a
node, which is exactly where this feature has twice already found that a cross-repository
requirement carried by one side's task list gets built on one side.

The re-bound each sibling needs is the same two lines, raised in lockstep with whatever release
actually ships (`>= 0.1.1`, `<< 0.2.0~` if the next break is minor), **plus the matching
`pyproject.toml` bound**, which is not what `dpkg` enforces but is what `pip`/`poetry` resolves. This
is carried in `specs/planning/upcoming-feature-requirements-2026-10-02.md` and belongs to whichever
feature cuts the release; **T060 must not be executed on its own.**
