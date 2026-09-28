<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# `cuems-nodeconf` — is `feat/nodelist-modify-hardening` superseded by `feat/xml-refactor`?

**Written** 2026-09-25, against `cuems-nodeconf` `feat/xml-refactor` @ `3af31cc`-era tree (candidate
tag **`6c0cca7`**) and `origin/feat/nodelist-modify-hardening` @ `61b759f`, with `cuems-utils` at
`b7db53e` (`0.1.0rc16`).

**Answer: three of the four defects are superseded — two completely, one in effect. Two things remain
open: one live in-memory race, and one false statement in the candidate's own documentation.** The
branch should not be merged; it should be **retired against a short list of carried-forward items**.

---

## 0. Correction to this repository's earlier record

`baseline.md`'s 2026-09-25 section first described `21c2875` as *"a narrower fix [that] landed in its
place"* and said the candidate *"has no guard against two threads writing the map at once"*, with a
supporting count of *"22 lock-related lines against 11"*. **All three statements were wrong**, and the
error was mine, not the tree's:

| Claim | Why it was wrong |
|---|---|
| "a narrower fix landed in its place", implying independent re-derivation | `21c2875`'s own commit message says *"Cherry-picked in intent from `b53ee5f` on `feat/nodelist-modify-hardening` rather than merged"*, and then spends a paragraph justifying **exactly** which half it excludes and why. This was a documented decision, not an oversight |
| "has no guard against two threads writing the map at once" | True as stated and misleading as framed. There is no lock **because the hazard the lock existed for no longer exists** — see §2 |
| "22 lock-related lines against 11" | A careless `grep -ic 'lock'`. All **11** matches on `feat/xml-refactor` are `master.lock`, a *file name* with no relation to threading, plus one docstring word. The honest count is **zero mutexes** on `feat/xml-refactor` and **one `threading.RLock`** on the hardening branch |

The framing error mattered more than the count: it presented a reasoned, recorded trade-off as a gap.

---

## 1. What the hardening branch actually fixes — four defects, not one

| | Defect | Commit | Stated consequence |
|---|---|---|---|
| **A** | `engine_callback` replies only for `action == 'nodelist_modify'`; every other well-formed message returns without answering | `b53ee5f` | On an NNG Req/Rep socket the engine blocks for its full 15 s timeout — *"an unexplained stall with nothing in either log to explain it"* |
| **B** | Two writers render through the **same** temp path `f"{map_path}.tmp.{os.getpid()}"` before `os.replace` | `b53ee5f` | *"promote a truncated map that neither the engine nor the editor can load at next start … a cluster that will not come up"* |
| **C** | In-memory races on `self.network_map`: a lost adopt, and `run()` replacing the index while the comms thread iterates it | `b53ee5f`, `61b759f` | lost adoption; spurious *"Node not found"*; adopting into a dict about to be discarded |
| **D** | `CLAUDE.md` says `<online>` is a boot-only snapshot; the daemon has been resident since `3e100bb` | `28f26d3` | *"sending readers to the wrong conclusion about how fresh it is"* |

`61b759f` adds the sharpest observation of the four: **there are three writers, not two.** `start()`
calls `set_comms()` **before** `run()`, so the NNG responder is accepting adopt/unadopt requests while
`run()` is still installing the map.

---

## 2. Defect B is superseded completely, by construction — verified, not inferred

`21c2875` claims the temp path is gone because `write_network_map` now delegates to
`CuemsNetworkMapType.save()`, and `cuemsutils`' `write_tree()` allocates a unique temp name per call.
**Both halves verified 2026-09-25.**

**The daemon no longer renders a temp file at all.** On `feat/xml-refactor`,
`grep -n 'tmp\.\|\.tmp\|getpid\|os.replace' cuemsnodeconf/CuemsNodeConf.py` returns **nothing**;
`write_network_map` does not exist. Both write paths end at
`self._network_map_document().save(self.map_path)` → `config/base.save_document` →
`xml/documents.write_tree`.

**`write_tree` allocates a unique name** (`src/cuemsutils/xml/documents.py:237-239`):

```python
handle, temporary = tempfile.mkstemp(
    dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
)
```

**Measured** — six sequential saves through the public path, `tempfile.mkstemp` instrumented:

```
Q1 temp names over 6 saves: 6 distinct of 6
  -> ['.network_map.xml.3yyvoyvc.tmp', '.network_map.xml.5bo3gqqz.tmp', '.network_map.xml.cgpkfw6e.tmp', …]
```

So two concurrent writers cannot collide on the temporary. Each writes a **complete** tree to its own
file and `os.replace`s it, and `os.replace` is atomic on one filesystem — a reader sees the whole old
document or the whole new one. **The worst case degrades from "truncated map, cluster will not boot"
to "last-writer-wins with a complete, valid document."**

This is a genuine supersession rather than a workaround: the hazard was a *property of the daemon's
own temp-path scheme*, and that scheme was deleted when the write moved into the library.

---

## 3. Defect A is superseded completely — ported verbatim

`21c2875` carries `b53ee5f`'s control-flow hunk with no dependency on the node model, and says why it
was ported rather than merged: the hardening branch *"predates the NodeList refactor, so merging it
here conflicts and — worse — auto-merges its tests into a file whose imports no longer define
`CuemsNodeDict`."*

`engine_callback`'s docstring on `feat/xml-refactor` now states the invariant directly
(`CuemsNodeConf.py:142-146`): *"EVERY path must answer."* Verified against the pre-fix behaviour by
`test_unknown_action_is_answered` and `test_missing_action_is_answered`, both of which fail before the
change.

Nothing is carried forward. **Retire A.**

---

## 4. Defect C's lost-adopt half is superseded *in effect* — 0 of 60 trials — but not by design

This is the interesting one, and the mechanism is not the one either branch describes.

**Why a lock looked necessary.** Two paths reach the map from two threads, with no mutex:

| Thread | Path | What it does |
|---|---|---|
| main | `_run_worker_loop` → `refresh_network_map` (every 30 s or on a debounced avahi event) | rebuilds the document from the index, calls `document.refresh(discovered, path)`, then **rebinds** `self.network_map` from the document |
| comms | `engine_callback` → `adopt_node`/`unadopt_node` | `self.network_map.adopt(uuid)`, then `_save_network_map()` |

**Why it turns out not to be.** Feature 001/002's design passes **references, never copies**, all the
way down:

- `_index_from_document` — *"The MAC-keyed index over a network-map document's nodes (**no copies**)"*
- `_network_map_document()` returns **`self._document` itself**, the same object every call, with
  `node_list` refilled from the index
- `CuemsNetworkMapType.refresh` builds `current = NodeIndex({item["node"]["mac"]: item["node"] …})` —
  again the **same node dicts**
- `NodeIndex.adopt` does `n["adopted"] = True` — an **in-place** mutation of a node dict

So an adoption performed on the index is immediately visible through every other alias, including the
`node_list` that `refresh` is mid-way through merging and the document that either thread is about to
serialise. There is no private copy for the write to be lost into.

**Measured** — 60 trials, each starting the two daemon code paths as concurrent threads against one
`CuemsNetworkMapType` and one set of node dicts, with a randomised 0–4 ms offset on the adopt, then
re-reading the file through `ConfigManager`:

```
trials=60  adoption LOST on disk=0  exceptions=0
```

**Verdict: superseded in effect, and worth a regression test rather than a lock.** The property holds
because of aliasing, which is a consequence of the no-copies design rather than a stated guarantee
about concurrency — `refresh_network_map`'s docstring only claims safety for an adoption *"made
between passes"*, and this is stronger than that. An optimisation that introduced a defensive copy
anywhere on this chain would reopen the window silently, with a green suite. **That is the carried
item: a test pinning it, not a mutex.**

---

## 5. Defect C's startup half is **OPEN**, and one engine fix makes it answer confidently wrong

`61b759f`'s third writer is still there, and it is the one thing in this analysis that is a live bug.

**The ordering, unchanged on `feat/xml-refactor`:**

```
__init__      self.network_map = NodeIndex()      # empty
              self._document   = None
start()  :130 self.set_comms()                    # the NNG responder goes live
         :131 self.run()
run()    :192   self.get_ips()                    # TimeoutLoop(timeout=10, interval=1) — up to 10 s
         :209   self._seed_empty_map()            # only when the file is absent
         :212   self.read_network_map()           # <-- index and document finally populated
```

An adopt arriving between `:130` and `:212` reaches `adopt_node` with an **empty** `NodeIndex`:
`network_map.adopt(uuid)` iterates nothing and returns `False`, `_find_node(uuid)` returns `None`, and
the operator gets

```python
{'OK': False, 'error': f'Node {node_uuid} not found'}
```

— a confident, specific, **wrong** answer. The window is dominated by `get_ips()`'s 10 s loop, and
`61b759f` notes the rollout restarts nodeconf first, *"which is exactly when the window opens."*

**What feature 002 did fix, deliberately.** `read_network_map` carries this, and it is `61b759f`'s
premise rediscovered independently:

```python
# Keep the document BEFORE installing the index, not after. set_comms()
# starts the IPC listener before run(), so an adopt arriving between
# these two lines would mutate a populated index and then try to save
# through a document that is not there yet (constitution VI).
self._document = manager.network_map
self.network_map = self._index_from_document(manager.network_map)
```

That closes the **crash** variant (`RuntimeError: network map document not loaded`). It does not close
the **spurious not-found** variant, which is the operator-visible one.

**And `cuems-engine`'s `cf5c4ad` makes it worse, while being correct in itself.** That commit replaced
a 15 s stall with an instant refusal by **checking whether `/tmp/nodeconf.ipc` exists** before calling.
But that socket is created by `set_comms()` — at `:130`, before the window opens. So during the window
the engine's probe says *"nodeconf is available"*, forwards the adopt, and relays nodeconf's wrong
answer to the UI. Before `cf5c4ad` the operator got a stall; now they get a definite *"Node not
found"* for a node that is present.

**This is the one item that needs code**, and it does not need `_map_lock` to fix: a readiness flag set
at the end of `read_network_map`, with `engine_callback` answering
`{'OK': False, 'error': 'nodeconf is still starting up'}` until then, is sufficient and is honest about
the state. A lock would serialise the two threads without making the empty index any less empty.

---

## 6. Defect D is **OPEN**, and its subject is false in the candidate's own `CLAUDE.md`

`feat/xml-refactor`'s `CLAUDE.md:26` still reads:

> **Cadence:** nodeconf runs at boot and on explicit reconfigure — not continuously. So `<online>` is
> stale between those moments *by design*.

That stopped being true at `3e100bb`. On the same branch, `_run_worker_loop` does
`self._dirty.wait(timeout=30)` and calls `refresh_network_map()` on every debounced avahi event **or
every 30 s**. So `<online>` is a **≤30 s-stale discovery proxy**, not a boot snapshot. `28f26d3` is the
commit that corrects exactly this sentence.

**Why this is not cosmetic, and why it matters to feature 010 specifically.** Both consumer bundles
written on 2026-09-25 lean on the `online`-versus-`alive` distinction:
`cuems-editor`'s `node_status` docstring separates each node's `online` (nodeconf's discovery view) from
the engine's sub-second ping/pong, and `cuems-frontend`'s inventory §4a calls conflating them a trap on
the screen operators use to adopt hardware. A reader who checks nodeconf's `CLAUDE.md` for how fresh
`online` is currently gets **"stale between boots"** — which understates it by a factor that changes the
design answer.

The load-bearing half of that section — *`<online>` is not runtime liveness, and only the engine's probe
gates GO* — is correct on both branches and is not in question.

---

## 7. Disposition — retire the branch against four carried items

**Do not merge `feat/nodelist-modify-hardening`.** It is 47 commits behind, it predates the NodeList
refactor, and `21c2875` already recorded that merging it auto-merges tests into a file whose imports no
longer define `CuemsNodeDict`. Two of its four defects are gone and a third is gone in effect; merging
it to obtain the fourth would reintroduce a mutex for a hazard that no longer exists and conflict
across the file.

| | Defect | Disposition |
|---|---|---|
| A | `engine_callback` answers everything | **Retire** — ported verbatim as `21c2875` |
| B | shared temp path → truncated map | **Retire** — superseded by construction, measured 6/6 distinct temp names |
| C-lost-adopt | adoption lost between threads | **Retire the lock; carry a test.** 0/60 trials lose it, because of the no-copies aliasing. Pin the property so a future defensive copy cannot reopen it silently |
| C-startup | spurious *"Node not found"* in the `set_comms`→`read_network_map` window | **CARRY — needs code.** A readiness flag, not a lock. Worsened by `cuems-engine`'s socket-existence probe, which now reports the daemon available during it |
| D | `CLAUDE.md`'s `<online>` cadence is false | **CARRY — documentation.** One paragraph; `28f26d3`'s text applies almost verbatim |

**Whose call, and whose work.** The branch is Ion Reguera's; `21c2875` is the maintainer's. Retiring a
colleague's branch on the strength of this analysis is the maintainer's decision, not this document's —
and `cuems-nodeconf`'s own constitution is why its two features reported upstream rather than patching
across a boundary. This report is the input to that decision.

**Sequencing.** Neither carried item blocks feature 010's consumer flows, and neither is a reason to
re-cut `6c0cca7`: D is documentation, and C-startup is a pre-existing bug in a window that predates
this work. But **both touch code flows 01 and 02 are about to migrate** — the engine's
`nodelist_modify` handler drives the write path, and the editor's WS action is the caller — so they
belong on the same release's list rather than a later one.

**Where the work is tracked.** The carried items are **T091–T100** under US7 in
[`tasks.md`](tasks.md)'s Phase 4, split by owner rather than by defect:

| Tasks | Owner | What |
|---|---|---|
| T091, T092 | **this repository** | C1's guarantee: a contract test pinning links 3 and 4 of the by-reference chain (`NodeIndex.adopt`/`merge`, `CuemsNetworkMapType.refresh`), written to fail against a defensive copy; and the three docstrings that currently imply the aliasing by accident made to state it |
| T093 | gate | `cuems-nodeconf`'s half of the same test — links 1 and 2 |
| T094, T096 | gate | C2's readiness flag, and a check that neither flow 01 nor flow 02 compensated for the wrong string |
| T095 | this repository | the `cf5c4ad` readiness-contract gap recorded in the migration guide |
| T097, T098 | gate + guide | D's `CLAUDE.md` correction, and why a documentation line is a release item |
| T099, T100 | this repository | the branch's disposition once the maintainer takes it, and the discovery-method lesson |

T091 and T092 are blocked by nothing. T093–T098 are gates on edits **no numbered feature in
`cuems-nodeconf` currently owns** — if that repository opens a feature `003`, they become its gate
references and the implementation detail moves out of `tasks.md`.

---

## 8. How to reproduce

```bash
cd /disk/Projects/StageLab/cuems-nodeconf
git fetch origin
git cherry -v feat/xml-refactor origin/feat/nodelist-modify-hardening   # all three '+': none upstream
git show feat/xml-refactor:cuemsnodeconf/CuemsNodeConf.py | grep -n 'getpid\|os.replace\|\.tmp'   # empty
git show feat/xml-refactor:CLAUDE.md | sed -n '26p'                     # the false cadence line
```

The two probes behind §2 and §4 instrument `tempfile.mkstemp` and run the two daemon paths as threads
against one `CuemsNetworkMapType` obtained from `ConfigManager(config_dir=…, load_all=False)`;
`cuems-nodeconf`'s `tests/fixtures/etc_cuems/{settings.xml,network_map.xml}` is a ready pair. They are
throwaway scripts, deliberately not committed — §7's carried test is the durable form, and it belongs
in `cuems-nodeconf`.
