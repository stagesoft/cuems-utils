<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Consumer census — feature 012, uuid4 convergence

**T060. A blocking precondition of the library-surface change, not a follow-up**
(FR-032, FR-032a, SC-011). No task in Phase 6 may start until this document exists.

Two results per repository, because this feature changes two things a consumer
receives, and they fail in opposite ways:

| Column | What changes | How it fails |
|---|---|---|
| **1. The own-identity accessor's type** | `ConfigManager.node_uuid` answers with the identity type on a provisioned node instead of a `str` (FR-021b) | **Silently.** A site that formats, compares or hashes it keeps working; one that slices or `split`s it raises far from the change |
| **2. A network-map read that raises** | FR-019a makes node-identity uniqueness a registered, **not repairable** rule, so a map with two rows sharing one identity — which loads today, `NodeIndex.merge` collapsing the duplicate silently (M-l) — raises `ValidationError` for every reader afterwards | **Loudly, and in the wrong place.** A successful read becomes an exception, at whatever call site happens to reach the map first |

Column 1's measurement is research R4's; this document records it per repository.
**Column 2's measurement was not in R4 and was taken for this task**, on
2026-09-30, against each sibling's `feat/xml-refactor` branch. It found one
repository R4 does not list at all.

---

## The table

| Repository | Branch | 1. Reads the accessor? | Risk under the changed type | 2. Reads the map? | Behaviour when the read raises |
|---|---|---|---|---|---|
| `cuems-engine` | `feat/xml-refactor` | **Yes**, many sites | **None measured.** Equality, f-string, set membership, hashing — all supported by the identity type's `__eq__`, `__str__`, `__hash__`. rc7 routes egress through `id_str` | **Yes**, two paths | **Startup: fatal, and correctly so.** `BaseEngine.set_config_manager` (`:323`) wraps `ConfigManager(load_all=True)` in `except Exception` and `exit(-1)` with the message logged. A colliding map stops the engine rather than running it over an ambiguous topology. **Reload: guarded and degrades well.** `ControllerEngine._reload_network_map` (`:903`) is wrapped and answers the operator with a named partial success — "adopted, but the engine could not reload the topology" |
| `cuems-power-bridge` | `feat/xml-refactor` | **Yes**, one site — `network_map.py:295`, `own_uuid = str(cm.node_uuid)` | **None.** Already converts explicitly | **Yes**, one path | **Guarded, and lands in the right bucket.** `load_nodes` (`:299`) catches broadly and routes through `_classify`, which has no branch for this message and falls through to its final `NETWORK_MAP_INVALID` case: *"… is not a valid document (…). Every node needs uuid, mac, name, node_role and ip; fix the document …"*. **That closing advice is wrong for this fault** — every node *does* have all five, and the fault is that two of them share one. Not blocking (the bridge refuses safely and names the document), but it is the one message this feature makes misleading, and it belongs in the bridge's own follow-up rather than here |
| `cuems-nodeconf` | `feat/xml-refactor` | **No** | — | **Yes**, one path | **Unguarded, and this is the finding.** `CuemsNodeConf.read_network_map` (`:859`) catches `ValueError` **only**, for the documented "this node is not in the map yet" case. `ValidationError` subclasses `CuemsError(Exception)`, **not** `ValueError`, so it propagates out of `read_network_map` and takes the daemon's startup with it. Correct in outcome — a daemon that writes the map must not write over a collision — but it arrives as an unhandled traceback rather than as a diagnosis, on the one component whose job is to repair the map |
| `cuems-editor` | `feat/xml-refactor` | **No.** Its `node_uuid` occurrences are websocket handler parameters from the frontend, not library reads | — | **Yes**, two paths — **and R4 does not list this repository at all** | **Guarded, and degrades to silence.** `CuemsWsServer.reload_network_map_nodes` (`:447`) retries **three times with exponential back-off** and then logs and returns `False`. The retries are for a map being written concurrently; a collision is permanent, so all three are spent and the settings panel shows a stale node list with only a log line to say why. `watch_network_map` (`:555`) disables the watcher on a path failure. Not blocking, but the operator-visible symptom is "the node list stopped updating" |
| `cuems-common` | `feat/xml-refactor` | **No** | — | **No** Python reader. It *ships* `network_map.xml` and mirrors the XSD | — |
| `cuems-frontend` | `feat/xml-refactor` | **No** — TypeScript, consumes JSON over the wire | — | **No** — receives the node list from the editor, already decoded | — |

---

## What column 2 adds that column 1 did not

R4's conclusion — "the type change is safe against every measured site" — holds,
and Phase 6 is unblocked on that basis. Column 2 changes the shape of the risk
rather than the verdict:

1. **It reaches four repositories, not two.** The accessor is read by
   `cuems-engine` and `cuems-power-bridge`. The **map** is read by those two plus
   `cuems-nodeconf` and `cuems-editor`. The editor is not in R4's table at all,
   because R4 asked about the accessor and the editor does not read it.
2. **Every reader refuses safely.** No repository proceeds over a colliding map.
   That is the outcome this feature wants, and it is what makes the rule's
   `repairable=False` affordable.
3. **Two of the four report it badly**, and neither is this repository's to fix:
   - `cuems-nodeconf` lets it propagate as an unhandled `ValidationError`,
     because its `except ValueError` predates an exception type that is not one.
   - `cuems-power-bridge`'s classifier falls through to advice that is wrong for
     this fault ("every node needs uuid, mac, name, node_role and ip").

   Both are recorded here and carried to the migration guide (FR-036b): the
   collision must be resolved **before** the narrowing lands, while the map still
   loads, precisely because after it the two components that would tell an
   operator what is wrong are the two that say it least well.

4. **The editor's retry loop is wasted work on a permanent fault.** Three
   attempts with back-off against a document that will never parse differently.
   Harmless, and worth naming because the symptom an operator sees — a node list
   that quietly stops refreshing — does not point at the map.

---

## Method

Measured 2026-09-30 by reading each checkout at
`/disk/Projects/StageLab/<repo>` on its `feat/xml-refactor` branch:

```bash
# column 1
grep -rn "node_uuid\|node_conf\[.uuid.\]" <repo> --include='*.py' --include='*.ts'
# column 2
grep -rn "network_map" <repo> --include='*.py' --include='*.ts'
# then: read every call site's enclosing try/except by hand
```

The hand-reading is the part that matters and the part a grep cannot do: the
question is not *does this repository touch the map* but *what does its
`except` clause catch*, and `ValidationError`'s base class is what decides the
answer in three of the four cases.

**Not measured, and deliberately**: whether any of the four has a *test* that
would catch the new exception. That is each repository's business, and asserting
it from here would be this library making claims about suites it does not run.

## One site named although it is not a library read

`cuems-editor/src/cuemseditor/CuemsWsUser.py:407` does
`if not node_uuid or not isinstance(node_uuid, str)`. The identity type is
**not** a `str` subclass, so this would reject one. It is fed from the websocket,
so it is out of reach today — and it is the exact shape of the silent failure
column 1 exists to find, and a reason not to let the identity type leak into
wire payloads.
