# Feature 010 — `cuems-wsclient`: the sixth consumer, silently broken

**Status:** ready to run — **independent; start immediately**
**Date:** 2026-09-03
**Repository:** `/disk/Projects/StageLab/cuems-wsclient`
**Run order:** 06 of 06 by dependency, but **first by severity**. See the
[index](README.md).

This repository appears in no earlier plan — not feature 007's migration guide,
not 008's, not Part 4 §8's repo list. It has been broken since 007 and the
failure is silent.

---

## 0. State of this repository, measured 2026-09-03

| | |
|---|---|
| Current branch | `main` @ `f78bea6` (2026-06-01), clean |
| Base for `feat/xml-refactor` | **`main`** |
| Spec-kit | **absent** — added on first run (§1) |
| Constitution | **absent** — written on first run (§2) |
| Existing features | none → this becomes **`001-node-role-reader`** |
| Tests | `poetry run pytest` configured (`testpaths = ["tests"]`, `asyncio_mode = "auto"`) — **but `tests/` DOES NOT EXIST** |
| `cuemsutils` | declared optional, `>=0.1.0rc5` — and **imported nowhere** |

---

## The defect, stated first because it changes the priority of this file

`src/cuemswsclient/network_map.py` parses `/etc/cuems/network_map.xml` with its
own `ElementTree` reader and filters nodes on a string literal:

```python
# :33
node_type: str | None  # "NodeType.master" | "NodeType.slave" | None
# :93
node_type=_text(el, "node_type"),
# :108, inside slave_avahi_names()
if n.node_type != "NodeType.slave":
    continue
```

Feature 007 renamed that element to `<node_role>` with a typed vocabulary
(`controller` / `node` / `firstrun`). So `_text(el, "node_type")` returns `None`
for every node, `None != "NodeType.slave"` is true for every node, and
`slave_avahi_names` returns an empty list.

**Follow what consumes it.** `bridge.py`'s `_run_shutdown` is the power bridge's
shutdown coordinator:

- **Step 5** builds the node target list from `slave_avahi_names` — now empty. It
  logs `"shutdown: 0 nodes to power off: (none)"` at INFO. Not an error.
- **Step 6** SSH-fans-out `poweroff` to that list — to nobody.
- **Step 7** polls reachability only `if resolved:` — so with an empty list the
  poll is **skipped entirely**, and the "are they actually down?" check never runs.
- **Step 8** arms the Shelly relay's hardware safety timer, which cuts mains power.

The result is that every coordinated shutdown cuts power to a cluster of nodes
that were never told to shut down, and nothing in the sequence reports a problem.
This is 007's `FR-030a-ii` class — "keeps resolving but becomes semantically
wrong" — in its most consequential form, in the one repository nobody was
searching. It is also the argument for why that class gets searched for rather
than waited on: no test failed, no service crashed, and the suite could not have
caught it because **this repository has no tests at all**.

---

## 1. Branch and bootstrap

```bash
cd /disk/Projects/StageLab/cuems-wsclient
git checkout main && git pull --ff-only     # if a remote is configured
git checkout -b feat/xml-refactor

specify init --here --integration claude --script sh --force
```

Commit the scaffold as its own commit before `/speckit.constitution`.

Spec-kit's sequential branch numbering will want its own branch. Stay on
`feat/xml-refactor`; let it name `specs/001-node-role-reader/` only.

---

## 2. Constitution — write one, this repository has none

```
/speckit.constitution

Establish the constitution for cuems-wsclient, grounded in what this repository actually is.
It has no CLAUDE.md; read README.md, pyproject.toml, src/cuemswsclient/bridge.py and
src/cuemswsclient/shelly.py before writing anything.

WHAT THIS REPOSITORY IS: the CUEMS power bridge — a Shelly-relay and Companion shutdown
coordinator that is also a WebSocket client of the engine. Python 3.11+, Poetry, PyPI name
cuemswsclient, installed into the shared /usr/lib/cuems virtualenv and shipped as a Debian
package. Its console scripts include cuems-wsclient and a Shelly installer. Its central
operation is an ordered shutdown sequence: read the cluster topology from
/etc/cuems/network_map.xml, resolve each node to an avahi hostname, SSH-fanout a poweroff,
poll reachability until the nodes are actually down, then arm the Shelly relay's hardware
safety timer to cut mains power.

PRINCIPLES THE CODE ALREADY IMPLIES — derive from these, do not invent unrelated ones:
- IT CUTS MAINS POWER TO OTHER MACHINES. That is the top of the hierarchy and everything
  else is subordinate to it. A step that silently finds nothing to do must not be
  indistinguishable from a step that succeeded — an empty target list before a poweroff is
  an anomaly to surface, not a fast path. Write this as a principle in those terms, because
  the defect this feature fixes is exactly that distinction being absent.
- IT ORCHESTRATES AN ORDERED, PARTIALLY-IRREVERSIBLE SEQUENCE. Steps have preconditions;
  skipping a verification step because its input was empty is a correctness bug, not an
  optimisation. State that verification steps run on the anomalous path too.
- IT READS A SCHEMA IT DOES NOT OWN. network_map.xml belongs to cuemsutils, which versions
  it deliberately and ships a reader for it. A private parser for someone else's schema
  is a liability with a known failure mode — this repository is the proof. Depend on the
  owning library rather than re-deriving its format.
- IT TALKS TO HARDWARE OVER THE NETWORK (Shelly RPC, SSH, reachability polling). Timeouts,
  partial failures and unreachable hosts are the normal case, not the exceptional one.
- ITS pyproject DECLARES A TEST SUITE THAT DOES NOT EXIST. tests/ is absent while
  [tool.pytest.ini_options] is fully configured. Do not paper over that: state the testing
  gate this repository will hold, and note that establishing it is part of the very next
  feature rather than aspirational.

Do NOT weaken any rule to accommodate the migration that follows.
```

---

## 3. Context block — paste verbatim into `/speckit.specify` and `/speckit.plan`

```
CONTEXT — read these before writing anything. They live in the SIBLING checkout
/disk/Projects/StageLab/cuems-utils, not in this repository:
  .../cuems-utils/specs/007-node-model-migration/migration-guide.md   the rename, the release gate,
                                                                     and §3's FR-030a-ii class
  .../cuems-utils/specs/planning/xml-rebuild/xml-rebuild-09-consumer-audit.md   C1 IS THIS REPOSITORY
  .../cuems-utils/specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md  §2 = the FULL decision list
  AND IN THE SIBLING CHECKOUT: src/cuemsutils/xml/schemas/network_map.xsd — the schema this
  repository parses by hand; and src/cuemsutils/tools/NodeList.py — NodeRole, NodeIndex.

SETTLED — the decisions that bind THIS repository. Do not reopen. Anything
outside this subset: read §2 of the prompts file above.
  D2  the schema is the single source of truth for structure/type/cardinality/order
  D11 the node model lives in cuemsutils ONLY. No consumer re-implements or re-tests it.
  D12 public surface returns objects, never raw dicts
  D15 public objects are CuemsScript (show) and ConfigManager/ConfigBase (config)
  D32 THIS REPOSITORY IS IN FEATURE 010'S SCOPE IN FULL. Its private ElementTree
      network-map reader is REPLACED by the library's public path, not merely re-spelled to
      node_role: a second reader for a schema cuemsutils owns is the duplication the whole
      rebuild exists to end. It also carries 5 of the ecosystem's node_type occurrences, so
      "zero, counted" cannot pass without it.
  D27 nothing in the ecosystem releases until every 010 flow lands
  Q14 -> (i) cuemsutils.xml is internal machinery; use ConfigManager, not xml/

MEASURED STARTING STATE — verified against live files 2026-09-03, not transcribed:
  src/cuemswsclient/network_map.py — a complete private parser for someone else's schema:
    :23  NS = "{https://stagelab.coop/cuems/}"   (accepts namespaced and bare elements)
    :26-33  @dataclass(frozen=True) Node — uuid, avahi, role_id, alias, hostname, node_type
    :33  node_type: str | None  # "NodeType.master" | "NodeType.slave" | None
    :35+ _text(parent, *names) — first matching child by local-name
    :57-58  docstring: "Includes both NodeType.master and NodeType.slave. Caller filters
            by node_type if it wants only slaves (e.g. the bridge's shutdown ...)"
    :93  node_type=_text(el, "node_type"),
    :102-118  slave_avahi_names(path) -> (resolved, unresolvable)
    :108  if n.node_type != "NodeType.slave": continue      <- NOW TRUE FOR EVERY NODE
  src/cuemswsclient/bridge.py:
    :21  from . import network_map
    :195 _run_shutdown — step 5 (:200) builds targets from slave_avahi_names; step 6 (:222)
         poweroff_all(targets); step 7 (:226) `if resolved:` reachability poll — SKIPPED
         ENTIRELY when the list is empty; step 8 (:239) arms the Shelly safety timer.
    :75, :104 _nodes_pending — reported over the HTTP status endpoint
  pyproject.toml:36  cuemsutils = {version = ">=0.1.0rc5", optional = true}
  pyproject.toml:40  production = ["cuemsutils"]
  debian/control:18  cuems-utils (>= 0.1.0rc5)
    ^ the dependency is DECLARED and NEVER IMPORTED. The library it depends on ships the
      reader this repository hand-rolled.
  tests/  DOES NOT EXIST, while [tool.pytest.ini_options] is fully configured.

  DELIBERATE, AND NOT TO BE "FIXED": the parser ignores <ip> on purpose — it is a stale
  link-local on many adopted nodes (network_map.py's module docstring). Resolution goes
  role_id.local -> alias.local -> hostname.local. Preserve that policy exactly; it is a
  field-learned behaviour, not an oversight.

CALLERS THAT KEEP RESOLVING BUT BECOME WRONG (007 FR-030a-ii): this repository is the
ecosystem's clearest instance. Nothing failed, nothing crashed, and no suite could have
caught it. Fixing the string is NOT the deliverable — proving the fix with a test that
fails against the old value is, and so is removing the class of defect by deleting the
private parser.
```

---

## 4. Specify

```
/speckit.specify <PASTE CONTEXT BLOCK>

Move cuems-wsclient onto cuemsutils' network-map reader, restore the shutdown coordinator's
node targeting, and give this repository the test suite its own pyproject already assumes.

WHAT MUST BE TRUE WHEN DONE:
- The private parser is GONE, not corrected. src/cuemswsclient/network_map.py reimplements a
  reader for a schema cuemsutils owns, ships and versions; that duplication is what allowed a
  rename in another repository to silently disable this one's core safety step. Consume the
  library's public config path (ConfigManager / the network_map object) and keep this module
  only as a thin adapter to whatever shape bridge.py wants — or delete it outright if the
  library's objects serve directly.
- The node filter uses the role enum. What was `n.node_type != "NodeType.slave"` becomes a
  comparison against NodeRole.node — the vocabulary is controller/node/firstrun now, and
  "slave" is not a value any current document carries.
- The avahi-resolution policy is PRESERVED EXACTLY: <ip> is deliberately ignored because it
  is a stale link-local on many adopted nodes, and resolution runs role_id.local ->
  alias.local -> hostname.local, with nodes that resolve to none of the three reported as
  unresolvable rather than dropped. This is field-learned behaviour; a migration that
  "simplifies" it is a regression.
- An empty node list before a poweroff is an ANOMALY, not a fast path. Today step 5 logs
  "0 nodes to power off: (none)" at INFO, step 6 SSHes nowhere, step 7's reachability poll is
  skipped by `if resolved:`, and step 8 cuts mains power regardless. Decide what SHOULD
  happen — abort, require an explicit force, or proceed with a loud error — and implement it.
  This is the deliverable that keeps the same class of defect from being invisible next time,
  and it is worth more than the string fix.
- The declared cuemsutils dependency becomes REAL AND BOUNDED. It is optional and
  >=0.1.0rc5 today and imported nowhere; after this feature it is a genuine dependency, and a
  lower bound alone cannot express the release gate (C7).
- tests/ EXISTS. pyproject already configures pytest with asyncio_mode = "auto" and
  testpaths = ["tests"] against a directory that is not there. At minimum: a test that the
  node filter selects adopted nodes from a CURRENT network_map.xml and FAILS against the old
  "NodeType.slave" string, and a test of the empty-list behaviour decided above. Those two
  are the ones that would have caught this defect.

DO NOT re-implement or re-test the node model here (007 FR-030a-i). Reading the map through
the library is the point; a local copy of NodeRole would recreate the problem being fixed.

Note for the migration guide: this repository was absent from 007's and 008's guides and from
Part 4 §8's repository list, and that absence is why the defect survived two features. Record
it as a consumer explicitly, so the next ecosystem-wide count includes it by construction
rather than by someone remembering.
```

---

## 5. Clarify

```
/speckit.clarify
```

Force one question: **what should a shutdown do when it resolves zero nodes?**
Abort, force-flag, or proceed loudly. Everything else here is mechanical; this is
a product decision about a machine that cuts power.

---

## 6. Plan

```
/speckit.plan <PASTE CONTEXT BLOCK>

Per-file scope:
- src/cuemswsclient/network_map.py — the private parser replaced by the library's reader,
  or reduced to a thin adapter; the avahi-resolution policy preserved verbatim.
- src/cuemswsclient/bridge.py — :200 the target build, :226 the skipped reachability poll,
  and the empty-list behaviour decided in clarify.
- pyproject.toml, debian/control — a real, bounded cuemsutils dependency.
- tests/ — created, with the two tests named in the spec at minimum.

Sequencing: fully independent of the other five flows. It needs nothing from them and
nothing needs it, so it can start immediately and land first. It still does not RELEASE
first (D27).

Constitution check, against the constitution written in §2:
- The cuts-mains-power principle is what makes the empty-list decision the centre of this
  feature rather than a footnote.
- The reads-a-schema-it-does-not-own principle is what makes deleting the parser the fix,
  rather than correcting the string.
- Testing: the two named tests are the gate. A repository whose pyproject configures a
  suite that does not exist should not finish this feature still in that state.
```

---

## 7. Tasks, checklist, analyze, implement

```
/speckit.tasks
```
```
/speckit.checklist Reader-migration readiness: the private parser deleted or reduced to a
thin adapter, not merely re-spelled; the node filter on the role enum with a test that FAILS
against "NodeType.slave"; the avahi-resolution policy (ignore <ip>; role_id -> alias ->
hostname; unresolvable reported not dropped) preserved exactly and covered by a test; the
empty-node-list behaviour decided and implemented, with the reachability poll no longer
skipped on the anomalous path; tests/ created and green; the cuemsutils dependency real,
non-optional where it is now used, and upper-bounded; zero node_type / NodeType. occurrences
remaining, counted; and this repository recorded as a consumer in the 010 migration guide so
the next ecosystem-wide count includes it by construction.
```
```
/speckit.analyze
```
```
/speckit.implement
```

Then [Part 4 §9](../xml-rebuild-07-speckit-prompts.md)'s quality loop.

---

## 8. Exit criteria

`poetry run pytest` green against a `tests/` directory that now exists; the
private network-map parser gone; the node filter on `NodeRole` with a test that
fails against the old string; the avahi-resolution policy preserved and covered;
the zero-node shutdown behaviour decided and implemented; the `cuemsutils`
dependency real and bounded; zero `node_type` occurrences; and this repository
present in the 010 migration guide as a consumer.

**Does not ship alone** (D27) — but it is the flow whose current state is most
worth fixing early.
