<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Feature 010 — `cuems-power-bridge`: the live repository behind flow 06

**Status:** ready to run — **independent; start immediately**
**Date:** 2026-09-18
**Repository:** `/disk/Projects/StageLab/cuems-power-bridge`
**Supersedes:** [06-cuems-wsclient.md](06-cuems-wsclient.md) — **same repository,
renamed.** See §0.0, which is the first thing to read in this file.
**Run order:** independent of every other flow. First by severity: its failure is
silent *and* physical. See the [index](README.md).

---

## 0.0 The correction that reorders this whole feature — `cuems-wsclient` **is** `cuems-power-bridge`

Measured 2026-09-18, and it invalidates a repository count that two features have
carried:

| Measurement | Result |
|---|---|
| `git merge-base --is-ancestor f78bea6 main` in `cuems-power-bridge` | **true** — `f78bea6` is the exact commit flow 06 measured `cuems-wsclient` at, 30 commits back |
| `/disk/Projects/StageLab/cuems-wsclient` remote | `git@github.com:stagesoft/cuems-wsclient.git` — the **pre-rename** remote |
| `/disk/Projects/StageLab/cuems-power-bridge` remote | `git@github.com:stagesoft/cuems-power-bridge.git` |
| The rename in history | `83d4f5d refactor: rename package cuems-wsclient -> cuems-power-bridge (v0.2.6)`, 2026-06 |
| `pyproject.toml:36` in **both** checkouts | `cuemsutils = {version = ">=0.1.0rc5", optional = true}` |
| `debian/control:18` in **both** checkouts | `cuems-utils (>= 0.1.0rc5)` |

`/disk/Projects/StageLab/cuems-wsclient` is a **stale checkout of this same
repository**, abandoned 2026-06-01 at the commit flow 06 audited. It is not a
sixth consumer and `cuems-power-bridge` is not an eighth one. There are **seven**
repositories in feature 010, not eight, and **US1 and US11 are one story about one
file**.

Three consequences, all of them things this flow must not re-inherit:

1. **US1's defect and US11's defect are the same defect.** `slave_avahi_names`'s
   `n.node_type != "NodeType.slave"` is one comparison in one file that was counted
   twice — once against a checkout frozen in June, once against the live tree.
2. **T076's premise is wrong in both directions.** It says this repository's
   `debian/control` declares "no `cuems-utils` relation at all". It declares one at
   `:18` (`cuems-utils (>= 0.1.0rc5)`) and a second at `:19`
   (`cuems-common (>= 1.0.0)`). Flow 06 read the same file correctly in 2026-09-03.
   The defect is real but it is a **stale, unbounded floor**, not an absent edge.
3. **Flow 06 and US11's findings gave contradictory instructions for the same
   file** — 06 mandated deleting the private parser (D32), the findings document
   recommended migrating it in place (its option A). Settled 2026-09-18 in favour
   of **06's instruction**: the parser goes. §4 states it.

The durable lesson, and the reason this section is at the top rather than in a
footnote: **the repository list was wrong three times** — `cuems-wsclient` missing
entirely (FR-UX-002), `cuems-power-bridge` missing (US11), and now the same
repository counted twice. What each of those has in common is that the list was
maintained by hand. T062's denominator must be **discovered by the command**
("every repository under `/disk/Projects/StageLab/` that reads `network_map.xml`",
de-duplicated **by git remote, not by directory name**), which is the only
enumeration that would have caught all three.

---

## 0. State of this repository, measured 2026-09-18

| | |
|---|---|
| Current branch | **`feat/xml-refactor`** already exists, at `c201405` (= `main`), clean but for the untracked `specs/` below |
| Base for `feat/xml-refactor` | `main` @ `c201405` — `release: cuems-power-bridge 0.3.0-6 (single-controller auto-load settle)` |
| Spec-kit | **absent** — added on first run (§1) |
| Constitution | **absent** — written on first run (§2) |
| Existing features | none → this becomes **`001-node-role-parser`** |
| Tests | `pytest` configured and **`tests/` EXISTS** — 15 files. **The suite is RED**: `6 failed, 133 passed` (§0.2) |
| `cuemsutils` | `pyproject.toml:36` `>=0.1.0rc5`, **optional**, and **imported nowhere** — verified by grep across `src/` and `tests/` |
| Debian | `debian/control:18` `cuems-utils (>= 0.1.0rc5)`, `:19` `cuems-common (>= 1.0.0)` — both unbounded floors |
| Shipped | `rc1_packages/cuems-power-bridge_0.3.0-5_all.deb`; the systemd unit is shipped by `cuems-common` |
| Planning | `specs/planning/cuems-power-bridge-node-role-findings.md` (2026-09-15) + the vendored bundle, **untracked** as of this writing |

**On the "no tests" claim in flow 06**: it was true at `f78bea6` and is false now —
`tests/` arrived with the projector-control work (`b150a1c`). Do not carry 06's
"create tests/" deliverable forward; carry §0.2's instead.

### 0.1 The two independently-broken features

Both measured 2026-09-18 by running this repository's own parser against a map
that `cuems-migrate-network-map` has converted. **Neither is inferred.**

```
$ slave_avahi_names(converted_map)  ->  ([], [])
$ slave_ips(converted_map)          ->  []
```

Note the second element of the first result. The **unresolvable list is empty
too** — so not even the `ERROR … has no role_id/alias/hostname` path fires. There
is no log line anywhere that says anything is wrong.

**(i) Orderly cluster power-off** — `src/cuemspowerbridge/network_map.py:110`, via
`bridge.py:391`:

- Step 5 builds the target list from `slave_avahi_names` → empty. Logs
  `"shutdown: 0 nodes to power off: (none)"` at **INFO**.
- Step 6 SSH-fans-out `poweroff` to nobody.
- Step 7's reachability poll is guarded by `if resolved:` (`bridge.py:431`) — with
  an empty list **the "are they actually down?" check never runs at all**.
- Step 8 arms the Shelly hardware safety timer, which cuts mains power.

The venue loses mains to a cluster of machines nothing ever told to shut down, and
the sequence reports success. It happens during a poweroff transition, when nobody
is watching a terminal, and the only evidence is the journal of a machine that
then powered off.

**(ii) The autoload / NNG-hub readiness gate** — `network_map.py:141`, via
`bridge.py:589` → `_expected_node_ips` → `_try_auto_load`. **The findings
document's §3 misses this entirely**, and it is not on the poweroff path:

- `slave_ips()` returns `[]`, so `expected_ips` is empty.
- `_try_auto_load` therefore takes the **`else` branch at `bridge.py:652`** — the
  one commented `SINGLE-CONTROLLER CLUSTER (network_map lists no slave with an
  <ip>)` — logs `"no remote node-engine in network_map (single-controller
  cluster)"`, settles, and loads.
- On a real multi-node cluster the show is therefore loaded **before the
  node-engines join the hub**.

That is precisely the regression `0.3.0-5` was released to fix
(`debian/changelog:150-165`: node players excluded, GO blocked until a manual
engine restart). A converted map silently re-opens it. **Show-playback readiness
and orderly power-off fail and recover independently** — verify them separately
(US11/T075); "the bridge works now" is not an answer to either.

### 0.2 The suite is red before this feature touches anything

```
$ uv run --python 3.11 --with pytest --with pytest-asyncio --with pytest-mock \
      --with aiohttp --with websockets --with python-osc python -m pytest -q
6 failed, 133 passed in 12.28s
```

All six are `tests/test_install_mjs.py`, all the same cause, and **unrelated to
this migration**:

```
TypeError: _patched_code() missing 1 required positional argument: 'force'
  tests/test_install_mjs.py:39
```

`_patched_code()` gained a `force` parameter (the `FORCE` constant documented in
`CLAUDE.md`'s Shelly mJS section) and its six callers in the test file were not
updated. **Standing rule: never `/speckit.implement` on a red suite.** Fix these
six first, in their own commit, before anything in §4 — or the first green run of
this feature will be proving nothing.

Note the runner: the default interpreter has no `pytest`, and `aiohttp`,
`websockets` and `python-osc` are not installed either. The `uv` line above is
what works; it is at `/home/adria/.pyenv/versions/3.11.9/bin/uv`.

### 0.3 The fixtures certify the defect

`tests/test_network_map_ips.py:13-20` — the only network-map fixture in the
repository — is written in the **retired** vocabulary:

```xml
<node><uuid>u-ctrl</uuid><node_type>NodeType.master</node_type>
  <ip>169.254.9.204</ip><role_id>controller</role_id></node>
<node><uuid>u-n1</uuid><node_type>NodeType.slave</node_type>
  <ip>169.254.13.233</ip><role_id>node01</role_id></node>
```

So the suite is green **because** it certifies the defect. This is the
FR-030a-ii discipline this class of caller demands: a passing suite is not
evidence. Two fixtures must exist — pre-007 and post-007 — and **the post-007 one
must fail against the pre-migration parser**. Record the failing run; a test that
was green the first time it was written has not demonstrated anything here.

That fixture has a second problem under §4's chosen fix, and it is not cosmetic:
it is **not schema-valid**. `network_map.xsd`'s `NodeType` requires `uuid`
(canonical 8-4-4-4-12 hex), `mac`, `name`, `node_role` and `ip`, all
`minOccurs="1"`. `u-n1` is not a uuid and there is no `mac` or `name` anywhere in
the file. Today that does not matter, because the parser validates against
nothing. After §4 it matters for every fixture in the repository.

### 0.4 Every site carrying the retired vocabulary, counted

Measured 2026-09-18 across the working tree. **Shipped code first.**

| Path | What |
|---|---|
| `src/cuemspowerbridge/network_map.py:110` | `if n.node_type != "NodeType.slave"` — **defect site 1**, `slave_avahi_names` |
| `src/cuemspowerbridge/network_map.py:141` | `if n.node_type != "NodeType.slave"` — **defect site 2**, `slave_ips` |
| `src/cuemspowerbridge/network_map.py:94` | `node_type=_text(el, "node_type")` — the read that yields `None` |
| `src/cuemspowerbridge/network_map.py:33` | the dataclass field and its `"NodeType.master" \| "NodeType.slave"` comment |
| `src/cuemspowerbridge/network_map.py:58-59,102,120` | four docstrings in the retired vocabulary |
| `tests/test_network_map_ips.py:13-20,40` | the fixtures of §0.3 |
| `debian/control:34` | **shipped prose**: "SSHes every NodeType.slave from /etc/cuems/network_map.xml" |
| `README.md:320,323,476,767,1265` | five documentation sites |

And **the third defect site, in the other repository**:

| `cuems-common` `usr/bin/cuems-cluster-poweroff:275` | `if n.node_type != "NodeType.slave"` — re-measured 2026-09-18, still at `:275` |
| `cuems-common` `usr/bin/cuems-cluster-poweroff:240` | docstring: "matches the network_map `NodeType.master` entry" |

The findings document names **only** the `cuems-common` site. Fixing the tool
alone — its option D — would leave both of this repository's live. Conversely,
fixing only this repository leaves the tool broken, because the tool pipes a
Python heredoc into this repository's venv and calls `network_map.parse()`
itself (`cuems-cluster-poweroff:209`). **The two repositories must land
together**, the same way `cuems-common` and `cuems-nodeconf` must for the Avahi
cutover (D33).

**Deliberately excluded from the count**, so it is not "fixed" by accident:
`src/cuemspowerbridge/wsclient.py:69-70` defaults `--host` to `master.local`.
That is an **mDNS hostname**, not the node-role field — renaming it changes what
a deployed host answers to. Out of scope, recorded here so the next counter does
not silently include it.

---

## 1. Branch and bootstrap

```bash
cd /disk/Projects/StageLab/cuems-power-bridge
git checkout feat/xml-refactor        # ALREADY EXISTS at c201405 — do not re-create
git status                            # specs/ is untracked; commit it first (§1a)

specify init --here --integration claude --script sh --force
```

Commit the scaffold as its own commit before `/speckit.constitution`.

Spec-kit's sequential branch numbering will want its own branch. Stay on
`feat/xml-refactor`; let it name `specs/001-node-role-parser/` only.

### 1a. Commit the planning documents first (US11/T070a)

`specs/planning/cuems-power-bridge-node-role-findings.md` and the vendored bundle
beside it are **untracked**. They are currently the only written record of a live,
silent, physical failure. Commit them before anything else — an untracked file is
not a deliverable, and this one has already survived one move
(`cuems-common`'s tree → `dev/planning/` → `specs/planning/`) by luck.

---

## 2. Constitution — write one, this repository has none

```
/speckit.constitution

Establish the constitution for cuems-power-bridge, grounded in what this repository actually
is. Read CLAUDE.md, README.md, pyproject.toml, src/cuemspowerbridge/bridge.py,
src/cuemspowerbridge/shelly.py and src/cuemspowerbridge/cluster_bus.py before writing
anything.

WHAT THIS REPOSITORY IS: the CUEMS power bridge — a controller-only asyncio HTTP coordinator
on :8478 fronting orderly cluster shutdown and GO/STOP, triggered by a wired Shelly Pro 1
flip-switch or a Bitfocus Companion Stream Deck. Python 3.11+, Poetry, PyPI name
cuemspowerbridge, dh-virtualenv into the shared /usr/lib/cuems venv, Debian package
cuems-power-bridge (its systemd unit is shipped by cuems-common). It holds persistent
WebSockets to the engine (:9190, binary OSC) and the editor (:9092, JSON). Two of its
operations read the cluster topology from /etc/cuems/network_map.xml: the ordered shutdown
sequence (resolve nodes to avahi hostnames, SSH-fanout poweroff, poll reachability until they
are down, arm the Shelly hardware timer, then poweroff locally) and the boot auto-load gate
(wait for the expected node-engines on the controller's NNG hub before firing project_ready).
It was renamed from cuems-wsclient in 2026-06; the console entry cuems-wsclient survives
deliberately.

PRINCIPLES THE CODE ALREADY IMPLIES — derive from these, do not invent unrelated ones:
- IT CUTS MAINS POWER TO OTHER MACHINES. That is the top of the hierarchy and everything
  else is subordinate to it. A step that silently finds nothing to do must not be
  indistinguishable from a step that succeeded — an empty target list before a poweroff is
  an anomaly to surface, not a fast path. Write this as a principle in those terms, because
  the defect this feature fixes is exactly that distinction being absent, twice.
- IT ORCHESTRATES AN ORDERED, PARTIALLY-IRREVERSIBLE SEQUENCE. Steps have preconditions;
  skipping a verification step because its input was empty is a correctness bug, not an
  optimisation. State that verification steps run on the anomalous path too — bridge.py:431's
  `if resolved:` is the live counter-example.
- IT READS A SCHEMA IT DOES NOT OWN. network_map.xml belongs to cuemsutils, which versions it
  deliberately, ships a validating reader for it, and ships a conversion tool for documents
  written before a rename. A private parser for someone else's schema is a liability with a
  known failure mode — this repository is the proof, and it is the FOURTH copy of the same
  node-identity model. Depend on the owning library rather than re-deriving its format.
- ITS DEGRADED PATHS ARE DESIGNED, AND THEIR TRIGGERS MUST BE REAL. cluster_bus's
  single-controller branch, slave_ips's missing-<ip> skip and the node-timeout
  degraded-proceed are all deliberate, field-measured behaviours. Each is correct only when
  its trigger is genuine. A parse that silently yields nothing counterfeits every one of
  them at once. State that a degraded path entered because of a READ FAILURE is a defect,
  not a degradation.
- IT TALKS TO HARDWARE OVER THE NETWORK (Shelly RPC, SSH, ICMP/TCP reachability, PJLink and
  Epson ESC/VP21 projectors). Timeouts, partial failures and unreachable hosts are the
  normal case, not the exceptional one.
- IT SHARES A VIRTUALENV WITH EVERY OTHER CUEMS PYTHON COMPONENT. /usr/lib/cuems is shared;
  a .deb that bundles what another package ships breaks dpkg -i, and stripping a bundle can
  break a SIBLING component at its next restart (CLAUDE.md records exactly this happening
  with pythonosc and the engine). Packaging changes are a correctness concern here, not a
  release chore.

Do NOT weaken any rule to accommodate the migration that follows.
```

---

## 3. Context block — paste verbatim into `/speckit.specify` and `/speckit.plan`

```
CONTEXT — read these before writing anything. Those marked SIBLING live in
/disk/Projects/StageLab/cuems-utils, not in this repository:
  IN THIS REPOSITORY:
    specs/planning/cuems-power-bridge-node-role-findings.md  the 2026-09-15 findings, and
        THREE CORRECTIONS TO IT are in the bundle beside it — read the bundle's §0 first
    specs/planning/cuems-utils-xml-refactor-consumer-migration.md  the vendored bundle
  SIBLING:
    .../cuems-utils/specs/007-node-model-migration/migration-guide.md   the rename, the
        release gate, and §3's FR-030a-ii class
    .../cuems-utils/specs/008-rebuild-extension/migration-guide.md      the strict load path,
        the conversion registry, the report types
    .../cuems-utils/specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md  §2 = the
        FULL decision list
    .../cuems-utils/src/cuemsutils/xml/schemas/network_map.xsd   the schema this repository
        parses by hand
    .../cuems-utils/src/cuemsutils/tools/NodeList.py             NodeRole, NodeIndex, node
    .../cuems-utils/src/cuemsutils/tools/ConfigManager.py        network_map, node_network_map
  OTHER CONSUMER (this feature lands in BOTH repositories, together):
    /disk/Projects/StageLab/cuems-common/usr/bin/cuems-cluster-poweroff  :275 and :240

SETTLED — the decisions that bind THIS repository. Do not reopen. Anything
outside this subset: read §2 of the prompts file above.
  D2  the schema is the single source of truth for structure/type/cardinality/order
  D11 the node model lives in cuemsutils ONLY. No consumer re-implements or re-tests it.
      THIS REPOSITORY IS THE FOURTH COPY. Deleting it is the point of the feature.
  D12 public surface returns objects, never raw dicts
  D15 the public objects are CuemsScript (show) and ConfigManager/ConfigBase (config)
  D19/D21 reading is strict: a document either loads, converts in memory, loads repaired,
      or raises — it never silently yields a partial answer
  D27 nothing in the ecosystem releases until every 010 flow lands
  D32 THIS REPOSITORY IS IN FEATURE 010'S SCOPE IN FULL, and it is the repository flow 06
      called "cuems-wsclient" — one repository, renamed, not two. Its private ElementTree
      network-map reader is REPLACED by the library's public path, not re-spelled to
      node_role.
  D33 a half-renamed vocabulary state is not shippable — here that means this repository
      and cuems-common's cuems-cluster-poweroff land TOGETHER
  Q14 -> (i) cuemsutils.xml is internal machinery; use ConfigManager, not xml/

MEASURED STARTING STATE — verified against live files 2026-09-18, not transcribed:
  src/cuemspowerbridge/network_map.py — a private, schema-less, namespace-agnostic parser:
    :23  NS = "{https://stagelab.coop/cuems/}"  (accepts namespaced and bare elements)
    :27-34  @dataclass(frozen=True) Node — uuid, avahi, role_id, alias, hostname, node_type, ip
    :33  node_type: str | None  # "NodeType.master" | "NodeType.slave" | None
    :37-44  _text(parent, *names) — first matching child by LOCAL NAME; returns None, never raises
    :47-52  _resolve_avahi — role_id -> alias -> hostname -> None. NEVER <ip>.
    :55-99  parse() — scans the whole tree for any element whose local-name is "node",
            requires only <uuid>, VALIDATES AGAINST NO SCHEMA
    :101-117 slave_avahi_names()  :110  if n.node_type != "NodeType.slave": continue  <- DEFECT 1
    :119-151 slave_ips()          :141  if n.node_type != "NodeType.slave": continue  <- DEFECT 2
  src/cuemspowerbridge/bridge.py:
    :386+ _run_shutdown — step 5 (:391) targets from slave_avahi_names; step 6 (:403)
             poweroff_all; step 7 (:430-431) `if resolved:` reachability poll — SKIPPED ENTIRELY
             when empty; step 8 (:458) arms the Shelly safety timer
    :575-593 _slave_ips_cached — mtime-keyed cache over slave_ips
    :594-616 _expected_node_ips -> :618 _try_auto_load; :652 the SINGLE-CONTROLLER branch
             that an empty result silently counterfeits
    :115-116 _slave_ips_cache / _slave_ips_cache_key
  MEASURED, not inferred, against a cuems-migrate-network-map-converted document:
    slave_avahi_names(converted) -> ([], [])   <- note: the UNRESOLVABLE list is empty too,
                                                  so not even the ERROR log path fires
    slave_ips(converted)         -> []
  tests/test_network_map_ips.py:13-20,40 — the only fixtures, in the RETIRED vocabulary, and
    NOT schema-valid (no <mac>, no <name>, and "u-n1" is not a uuid)
  SUITE IS RED BEFORE THIS FEATURE: 6 failed, 133 passed —
    tests/test_install_mjs.py, TypeError: _patched_code() missing 1 required positional
    argument: 'force'. Unrelated to this migration. FIX FIRST, in its own commit.
  pyproject.toml:36  cuemsutils = {version = ">=0.1.0rc5", optional = true}  AND IMPORTED NOWHERE
  pyproject.toml:40  production = ["cuemsutils"]
  debian/control:18  cuems-utils (>= 0.1.0rc5)      <- EXISTS. T076 says it does not. T076 is wrong.
  debian/control:19  cuems-common (>= 1.0.0)
  debian/control:34  shipped description prose: "SSHes every NodeType.slave from ..."

WHAT THE LIBRARY ACTUALLY GIVES YOU — measured 2026-09-18 by running it, so the plan does
not discover these during implement:
  ConfigManager(config_dir=..., load_all=False).load_network_map() then .network_map
    -> CuemsNetworkMapType. Its ["node_list"] is a list of {"node": <node>} WRAPPERS
       (the wrapper is kept deliberately — cuems-engine reads that shape).
    -> per node, TYPED: uuid=Uuid, mac=str, name=str, node_role=NodeRole (an ENUM, so
       `n["node_role"] is NodeRole.node` is the filter), ip=str, adopted=bool, online=bool,
       role_id/alias/hostname=str where present.
       network_map is the ONE config schema that runs the adapter table (007, research R1).
  AN UNCONVERTED MAP RAISES, NAMED AND ACTIONABLE — this is the loud failure the findings
  document asks for, and it is already built:
       SchemaError: <path>: node <uuid> still carries the retired <node_type> element
       (value 'NodeType.master') — network_map.xsd now requires <node_role>, one of
       ['controller', 'node', 'firstrun']. Run the network_map conversion
       (cuems-migrate-network-map) and re...
  THREE PRECONDITIONS THE PUBLIC PATH ADDS, ALL MEASURED — the plan MUST cover each:
    1. /etc/cuems/settings.xml MUST EXIST and be schema-valid. ConfigManager.__init__ calls
       ConfigBase.load_base_settings UNCONDITIONALLY — even with load_all=False — and raises
       FileNotFoundError without it. NO PACKAGE SHIPS THAT FILE (findings §5). Today this
       repository needs no such file. This turns findings §5 from "a secondary fragility to
       decide deliberately" into a HARD PRECONDITION of the fix.
    2. THIS host's uuid (settings.xml's node_uuid) MUST have an entry in the map, or
       load_network_map() raises ValueError: Node with uuid <uuid> not found — it resolves
       node_network_map eagerly.
    3. EVERY node entry must be schema-valid: uuid (canonical 8-4-4-4-12), mac, name,
       node_role, ip are all minOccurs="1". Today parse() requires only <uuid>. Every
       fixture in this repository must be rewritten, and an operator-hand-maintained
       /etc/cuems/network_map.xml missing a <mac> or <name> will now RAISE where it used to
       yield a partial node.

DELIBERATE, AND NOT TO BE "FIXED": the avahi resolution ignores <ip> ON PURPOSE — it is a
stale link-local on many adopted nodes (network_map.py's module docstring, and
feedback_avahi_hostnames). Resolution runs role_id.local -> alias.local -> hostname.local,
and nodes resolving to none of the three are REPORTED as unresolvable, never dropped.
slave_ips() is the deliberate exception: it TRUSTS <ip> because the NNG-hub readiness gate
matches bus peers by IP, not hostname. Both policies are field-learned. Preserve them
EXACTLY; a migration that "simplifies" either is a regression.

CALLERS THAT KEEP RESOLVING BUT BECOME WRONG (007 FR-030a-ii): this repository is the
ecosystem's clearest instance, and it is the instance that proves the class needs SEARCHING
for. Nothing failed, nothing crashed, and the suite stayed green BECAUSE its fixtures were
written in the retired vocabulary. Fixing the comparison is NOT the deliverable. Proving the
fix with a test that fails against the old value is, and so is removing the private parser
that made a rename in another repository able to do this silently.
```

---

## 4. Specify

```
/speckit.specify <PASTE CONTEXT BLOCK>

Move cuems-power-bridge off its private network-map parser and onto cuemsutils' public
configuration path, restore BOTH broken features, and make an empty node selection
impossible to mistake for success.

WHAT MUST BE TRUE WHEN DONE:

- THE PRIVATE PARSER IS GONE, NOT CORRECTED. src/cuemspowerbridge/network_map.py
  reimplements a reader for a schema cuemsutils owns, ships, versions and validates. That
  duplication is what let a rename in another repository silently disable two features of
  this one. Read the map through ConfigManager's network_map object; keep this module only
  as a THIN ADAPTER that turns the library's node objects into whatever shape bridge.py
  wants, preserving the two resolution policies verbatim. This is D32 and D11, and it is
  what flow 06 required of this same file in 2026-09-03.

- THE ROLE FILTER IS AN ENUM COMPARISON, NOT A STRING ONE. What was
  `n.node_type != "NodeType.slave"` becomes a comparison against NodeRole.node. Both sites
  (slave_avahi_names and slave_ips) change; there is no third site in this repository.
  Do NOT define a local NodeRole (007 FR-030a-i) — import it from cuemsutils.tools.NodeList.

- THE THREE PRECONDITIONS FROM THE CONTEXT BLOCK ARE HANDLED EXPLICITLY, NOT DISCOVERED.
  (1) settings.xml is now REQUIRED for the bridge to read the map at all. Decide and
  implement what happens on a host without it — and note that the honest answer probably
  involves cuems-common or cuems-nodeconf shipping or generating it, which makes it a
  cross-repository decision, not a try/except. Do NOT reproduce findings §5's
  swallow-everything-and-return-None: that is the pattern under repair.
  (2) A map with no entry for this host's own uuid raises. Decide whether that is fatal for
  the bridge or a condition it reports and continues past.
  (3) Fixtures and any hand-maintained /etc/cuems/network_map.xml must be schema-valid.

- AN EMPTY SELECTION IS AN ERROR, NOT A SUCCESS — in BOTH features, separately.
  This is the invariant the findings document asks for in §2, and the only deliverable here
  that survives the vocabulary question entirely: a future field rename breaks the selection
  the same silent way, and this check is what makes it loud.
  * Shutdown: a stage that resolves zero targets must not proceed silently to arming the
    Shelly. Decide the behaviour — abort, require an explicit force, or proceed with a loud
    ERROR and a distinguishable /status state — and implement it. Note this is NOT the same
    as a genuine single-node cluster, which must still work; distinguish "the map contains no
    other node" from "the read produced nothing".
  * Autoload: bridge.py:652's single-controller branch must be entered because the map
    genuinely lists no other node with an <ip>, never because a read failed. Those two are
    indistinguishable today.

- THE RESOLUTION POLICIES SURVIVE UNCHANGED, COVERED BY TESTS. avahi: ignore <ip>, resolve
  role_id -> alias -> hostname, report the unresolvable rather than dropping them. Bus
  readiness: trust <ip>, skip-with-WARNING when absent, degrade gracefully when stale.

- THE cuemsutils DEPENDENCY BECOMES REAL AND BOUNDED. It is optional, >=0.1.0rc5 and
  imported nowhere today; after this feature it is a genuine runtime dependency. Move it out
  of [tool.poetry.extras], bound it in pyproject.toml the way cuems-nodeconf bounds its
  (>=0.1.0rc16,<0.1.1), and raise debian/control:18's floor to match. A floor alone cannot
  express the release gate (FR-091/C7).

- THE FIXTURES DISCRIMINATE. tests/test_network_map_ips.py's fixtures are written in the
  retired vocabulary, so today's green suite CERTIFIES the defect. Two fixtures must exist —
  pre-007 (<node_type>NodeType.slave</node_type>) and post-007 (<node_role>node</node_role>)
  — both schema-valid, and the post-007 one MUST FAIL against the pre-migration parser.
  Record that failing run. A passing suite is not evidence in this class of defect.

- BOTH FEATURES ARE VERIFIED SEPARATELY. (i) orderly power-off selects the expected nodes
  from a converted map; (ii) the autoload / NNG-hub readiness gate does too. They fail and
  recover independently, so "the bridge works now" is not an answer to either.

- cuems-common's usr/bin/cuems-cluster-poweroff:275 LANDS IN THE SAME CUTOVER. It pipes a
  Python heredoc into this repository's venv and calls network_map.parse() itself
  (:209-210), so the two repositories are one change (D33's pattern). Its :240 docstring
  ("matches the network_map NodeType.master entry") is corrected in the same pass. Coordinate
  the merges; do not land one half.

- ZERO OCCURRENCES OF THE RETIRED VOCABULARY REMAIN IN SHIPPED CODE OR SHIPPED PROSE,
  COUNTED — including debian/control:34's package description and the five README sites.
  EXEMPT, and recorded as exempt with its reason: any fixture that exists to prove the
  pre-007 document still fails. Do NOT include wsclient.py:69-70's `master.local` default in
  the count — that is an mDNS hostname, not the role field, and renaming it changes what a
  deployed host answers to.

DO NOT re-implement or re-test the node model here (007 FR-030a-i). Reading the map through
the library is the point; a local copy of NodeRole would recreate the problem being fixed.

RECORD, DO NOT SCHEDULE: this repository's parser is the FOURTH copy of the node-identity
model (role_id -> alias -> hostname -> uuid), after cuemsutils, cuems-common's cuems-logs and
cuems-nodeconf's. Deleting this copy is this feature's work; a ROOT-CAUSE statement about why
a fourth copy existed belongs in the 010 migration guide, not in this repository's backlog.

Note for the migration guide: this repository is the one flow 06 called "cuems-wsclient" —
one repository, renamed in 2026-06, counted twice in feature 010's repository list. That list
has now been wrong three times. Record the DISCOVERY METHOD, not the corrected number.
```

---

## 5. Clarify

```
/speckit.clarify
```

Force three questions, in this order. Everything else here is mechanical.

1. **What should a shutdown do when it resolves zero nodes?** Abort, force-flag, or
   proceed loudly. This is a product decision about a machine that cuts mains
   power, and it is the item that outlives the vocabulary question.
2. **What happens on a host with no `/etc/cuems/settings.xml`?** The public path
   requires it and no package ships it. The answer may be "another repository
   ships it", which makes this a cross-repo dependency to raise now rather than at
   implement time.
3. **Does the bridge start honouring `adopted`?** The module docstring says
   "Resolve every **adopted** node", and `parse()` has never filtered on it —
   because the private parser had no typed `adopted` to filter on. The library
   gives one. Adding the filter is a **behaviour change** to a poweroff target
   list, so it is a decision, not a tidy-up.

---

## 6. Plan

```
/speckit.plan <PASTE CONTEXT BLOCK>

Per-file scope:
- src/cuemspowerbridge/network_map.py — the private parser deleted; what remains is a thin
  adapter over ConfigManager's network_map object, preserving _resolve_avahi's policy and
  slave_ips's deliberate <ip> trust. The two "NodeType.slave" comparisons (:110, :141) become
  NodeRole.node comparisons.
- src/cuemspowerbridge/bridge.py — :391 the shutdown target build, :431 the reachability poll
  no longer skipped on the anomalous path, :575-615 the cache and _expected_node_ips over the
  new adapter, :652 the single-controller branch distinguished from a failed read.
- tests/test_network_map_ips.py — both fixtures, schema-valid, with the discriminating run.
- tests/test_autoload.py — the readiness-gate half of the recovery, verified separately.
- tests/test_install_mjs.py — the six pre-existing failures, FIRST and in their own commit.
- pyproject.toml:36,40 and debian/control:18 — a real, non-optional, bounded dependency.
- debian/control:34 and README.md:320,323,476,767,1265 — the shipped prose.
- SIBLING /disk/Projects/StageLab/cuems-common/usr/bin/cuems-cluster-poweroff:275,240 — the
  third defect site and its stale docstring, merged simultaneously with this repository.

Packaging edge (findings §8, US11/T077) — DECIDE AND RECORD:
  cuems-common `Suggests: cuems-power-bridge` (debian/control:49) carries no version, and
  this repository `Depends: cuems-common (>= 1.0.0)` (debian/control:19) — an unbounded
  floor. So nothing today refuses a new tool beside an old bridge or the reverse. Whichever
  side changes first acquires a `Breaks:` against the versions of the other that cannot work
  with it. `Suggests:` MUST BE PRESERVED AS-IS — it is deliberately not Depends:/Recommends:
  so cuems-common stays functional on a host with no bridge, and both scripts already log one
  ERROR and exit 0 when the venv interpreter is absent. A fix must not turn the bridge into a
  hard dependency of cuems-common, and must not make the absent-bridge path fail a poweroff.

Shared-venv check, because this repository has broken a sibling this way before:
  making cuemsutils a real dependency must not change what the .deb BUNDLES into
  /usr/lib/cuems. cuems-utils already ships cuemsutils into that venv; bundling a second copy
  is a dpkg -i file-overwrite conflict, and stripping one another package needs has broken the
  engine's OSC at its next restart (CLAUDE.md, Field notes). Verify the built .deb's contents
  before shipping.

Sequencing: independent of every other 010 flow. It needs nothing from them and nothing needs
it, so it starts immediately and can land first — EXCEPT that its cuems-common half must land
simultaneously. It still does not RELEASE first (D27).

Constitution check, against the constitution written in §2:
- The cuts-mains-power principle is what makes the empty-selection invariant the centre of
  this feature rather than a footnote.
- The reads-a-schema-it-does-not-own principle is what makes deleting the parser the fix
  rather than correcting two string comparisons.
- The designed-degraded-paths principle is what makes bridge.py:652 in scope at all.
- Testing: the discriminating fixtures are the gate, and the six pre-existing failures are
  cleared before any of this starts.
```

---

## 7. Tasks, checklist, analyze, implement

```
/speckit.tasks
```
```
/speckit.checklist Parser-removal readiness: the six pre-existing test_install_mjs failures
cleared first, in their own commit; the private parser DELETED or reduced to a thin adapter,
not re-spelled to node_role; both role filters (network_map.py:110 and :141) on NodeRole with
a post-007 fixture that FAILS against the pre-migration parser, recorded; both fixtures
schema-valid; the three public-path preconditions (settings.xml, the self-uuid entry, node
validity) each decided and implemented rather than discovered; the empty-selection invariant
implemented in BOTH features, with the reachability poll no longer skipped on the anomalous
path and bridge.py:652's single-controller branch distinguished from a failed read; both
resolution policies (avahi ignores <ip>; slave_ips trusts it) preserved verbatim and covered;
both broken features verified SEPARATELY; cuems-common's cuems-cluster-poweroff:275 and :240
landing in the same cutover with the Suggests: relationship preserved and a Breaks: added;
the cuemsutils dependency non-optional and upper-bounded in pyproject.toml AND debian/control;
the built .deb bundling nothing another CUEMS package ships; zero retired-vocabulary
occurrences in shipped code and shipped prose, counted, with the exempt set enumerated and
wsclient.py:69-70 excluded by reason; and this repository recorded in the 010 migration guide
as ONE repository with two names, with the discovery method recorded rather than the
corrected count.
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

The suite green — including the six failures that were red before this feature
started, and a post-007 fixture whose failing run against the pre-migration
parser was recorded. The private network-map parser gone. Both role filters on
`NodeRole`. The three public-path preconditions decided and implemented. The
empty-selection invariant live in both features, each verified separately against
a converted map. Both resolution policies preserved and covered.
`cuems-common`'s `cuems-cluster-poweroff` merged simultaneously, with its
`Suggests:` preserved and a `Breaks:` added. The `cuemsutils` dependency real,
non-optional and upper-bounded in both `pyproject.toml` and `debian/control`. The
built `.deb` verified not to bundle anything another CUEMS package ships. Zero
retired-vocabulary occurrences in shipped code and shipped prose, counted, with
the exempt set enumerated.

Then, on real hardware (010/T046, the only task in the feature with a cluster):
orderly power-off selects the expected nodes from a converted map, and the
autoload gate waits for them.

**Does not ship alone** (D27) — but nothing in feature 010 is worth fixing
earlier. Every other consumer's failure is loud; this one's cuts mains power and
files a success.
