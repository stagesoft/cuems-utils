<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Migration guide — feature 012, uuid4 convergence

**Written for: the operator or maintainer performing the migration on a live
installation.** Not a design document — [spec.md](spec.md),
[plan.md](plan.md) and [research.md](research.md) are that. This is the
procedure, the losses, the hazards, and what to check afterwards.

**This is a stop-the-world operation.** Services stopped, no shows running, no
project loading. Budget a maintenance window.

`tests/contract/test_migration_guide.py` checks this document: every item
FR-033 through FR-036c requires is present, and every version and component
named below **resolves in the actual trees** rather than being asserted. A guide
whose named version has moved is worse than no guide, because an operator
follows it.

---

## 0. Before anything: is this needed at all?

The check is read-only and writes nothing, ever. Run it on each node:

```bash
cuems-init-node --check --json
```

| Exit | Meaning | Action |
|---|---|---|
| 0 | coherent, provisioned, **every identity converged** | nothing to do on this node |
| 1 | a mirror disagrees **or** an identity is not converged | read `verdict`: `mismatch` or `migration-needed` |
| 2 | a location is absent or unreadable | fix that first; the migration needs readable documents |
| 3 | the source carries the sentinel — NOT PROVISIONED | run `cuems-init-node`; this node was never provisioned |

`verdict: migration-needed` is what says the rest of this document applies.
The report's `occurrences` list names every identity it found, where, and its
class; the `embedded` flag marks the ones inside compound `<identity>_<output>`
strings, which is the part of the work no structural tool would see.

---

## 1. Preconditions

All of these, before step 2.

| Precondition | Why |
|---|---|
| **`cuems-engine 0.1.0rc7` or later on every node** | The re-mint ships in the same upgrade. An older engine's `cluster_status` cannot sort the resulting identities — it sorts node identities directly, and the identity type had no ordering before this release (FR-035, upstream report). Verify with `cuems-controller-engine --version` or `dpkg -s cuems-engine` |
| **`cuemsutils` at the coordinated `xml-refactor-merge-candidate` tag** | Nothing ships from feature 012's branch alone (D27). The tag comes after features 011–014 and is cut across seven repositories |
| **No pre-existing identity collision** | See [§7](#7-a-pre-existing-collision-must-be-resolved-first). This one is not optional and cannot be done later |
| **A backup of `/etc/cuems` and the project library on the controller** | See [§6](#6-the-backup-hazard) for what a backup does *not* protect you from |
| **Every node reachable over SSH** | The substitution table is copied by hand; this feature adds no transport |

---

## 2. Stop everything that writes

**`cuems-nodeconf` is the one that matters and the one most easily forgotten.**
It *writes* `network_map.xml` — it is the map's owner for every row but this
node's — and it is resident: it re-merges Avahi discovery and rewrites the map
on every debounced Avahi event, or every 30 seconds regardless. A discovery pass
landing mid-rewrite reintroduces an old identity into a map the re-mint has
already finished with, and nothing reports it (FR-034, §10.4).

On **every node**, in this order:

```bash
sudo systemctl stop cuems-nodeconf.service
sudo systemctl stop cuems-node-engine.service
sudo systemctl stop cuems-videocomposer.service
```

On the **controller**, additionally:

```bash
sudo systemctl stop cuems-controller-engine.service
sudo systemctl stop cuems-editor.service
sudo systemctl stop cuems-power-bridge.service
```

| Unit | Why it is on the list |
|---|---|
| `cuems-nodeconf.service` | **Writes `network_map.xml`.** The critical one |
| `cuems-controller-engine.service` | Holds `network_map` in memory and re-registers per-node OSC routes from it; also drives project deployment |
| `cuems-node-engine.service` | Holds this node's identity and its output set |
| `cuems-editor.service` | Reads the map on a timer and writes project documents in the library |
| `cuems-videocomposer.service` | Resolves outputs by the compound `<identity>_<output>` name |
| `cuems-power-bridge.service` | Reads the map to decide the power-off fan-out |

Confirm nothing is left:

```bash
systemctl list-units 'cuems-*' --state=running
```

`cuems-init-node` refuses to proceed while `cuems-nodeconf.service` is active
unless `--yes` is passed. Do not use `--yes` to get past that — stop the daemon.

---

## 3. Survey and estimate, on the controller

```bash
sudo cuems-init-node --remint --dry-run
```

This writes **nothing at all, not even a substitution table**. It reports:

- every identity it found and what each would become;
- every document it would rewrite, and every one it would leave alone;
- the surveyed byte volume and a **predicted duration**.

The estimate is the surveyed bytes divided by the throughput the survey just
measured **on this machine**. If the survey was too small to time meaningfully
the output says so and the figure is a pessimistic bound rather than a
measurement — it will say `the 500 MB/s floor … not a measurement`.

Use the predicted duration to size the window. It is accurate to within ±25%.

---

## 4. Re-mint the controller

```bash
sudo cuems-init-node --remint --yes
```

The controller rewrites **its own configuration documents and the whole project
library**. Order of operations:

1. survey;
2. **abort on a collision**, before the table is built — so an abort costs not
   even a minted identity;
3. build the table: one new uuid4 per distinct non-converged old identity;
4. **persist the table** before the first write;
5. estimate and confirm;
6. apply, per file: read, substitute, write to a temporary, `os.replace`;
7. verify: zero old tokens, every touched document valid, a full load succeeds
   here, adoption state unchanged;
8. write this node's **completion record**.

Exit codes: `0` done, `1` aborted or refused (nothing written), `2` **rewritten
but the verification failed**. A `2` is not a `1`: your cluster has changed and
the tool cannot prove it is right. Read the `VERIFICATION FAILED` lines before
doing anything else.

### 4a. Copy the table to every other node

**This is a numbered step, not a detail** (FR-007, FR-034). The controller
leaves the table at:

```
/var/lib/cuems-utils/remint/substitution-table.json
```

Copy it to each remaining node — anywhere readable; the path you give
`--table` is what matters:

```bash
for node in node1 node2 node3; do
  scp /var/lib/cuems-utils/remint/substitution-table.json \
      "$node":/tmp/substitution-table.json
done
```

**This feature adds no transport.** The table is one small file, the migration
is attended and stop-the-world, and a second distribution mechanism would put
two authorities on the operation's only durable record.

**A node invoked without the table refuses, and that refusal is the design
working.** A node that minted its own table would give itself an identity the
rest of the cluster has never heard of — the divergence §10.3 warns about. It is
not a fault to work around.

---

## 5. Re-mint every other node

On each node, with the table you copied:

```bash
sudo cuems-init-node --remint --table /tmp/substitution-table.json --yes
```

A node that is not the controller rewrites **only its own configuration
documents**. Its replica of the library is deliberately **not** re-minted in
place.

### The scope split, and the ordering it implies (FR-011a)

| Reach | Rewritten by | Reaches the other nodes by |
|---|---|---|
| `/etc/cuems/{settings,network_map,default_mappings}.xml` | **each node, itself**, from the copied table | not at all — each node's are its own |
| `<library_path>/projects/*/` and `trash/projects/*/` | **the controller, once** | the project deployer's existing replication, on the next project load |

The library reaches the nodes by the same `rsync` the deployer already runs for
every other library change (research R11). **A node re-minted but not re-synced
still holds stale output prefixes in its library replica** — it will resolve
outputs against identities that no longer exist.

**The one check that tells you replication has happened**: load a project on the
controller, then on any node compare an output prefix against that node's new
identity:

```bash
# on the controller, after restarting the stack (§8):
#   load any project from the editor, then on a node:
NEW=$(sudo cuems-init-node --check --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["source"]["uuid"])')
grep -rl "$NEW" /opt/cuems_library/projects/ | head
```

A hit means the replica carries the new identities. No hit, with the project
loaded, means replication has not run — load the project again and check the
controller's deploy log before proceeding.

---

## 6. The backup hazard

**Backups are not rewritten** (FR-015). The re-mint leaves alone:

- conversion backups, `<name>.<timestamp>.bak`, which
  `cuems-convert-documents` writes before every conversion;
- anything matching `*.bak-*`, `*.orig`, `*.save` or `*~`, including the copies
  §1 told you to take.

That is correct — rewriting a backup defeats the purpose of having taken it —
and it is a hazard you have to hold:

> **Restoring a pre-migration backup after the re-mint reintroduces a stale
> identity, and nothing at any layer will report it.** The restored document is
> schema-valid; the identity it names simply no longer exists anywhere. The
> symptom arrives later, as an output resolving to nothing.

If you restore one, re-run the re-mint afterwards. If the migration is complete
and you need the backup's *content*, edit the identities in it by hand against
the substitution table before restoring.

---

## 7. A pre-existing collision must be resolved first

**This is FR-036b, and without it the migration has a dead end.** Two rows of
the network map carrying one identity leaves you stopped by two requirements and
released by neither:

- the re-mint **aborts** on a shared identity (FR-019), because splitting it is
  safe in the configuration documents — the MAC discriminates — and unsafe in
  the library, where the compound `<identity>_<output>` prefix is the only
  record of which node an output belongs to. No discriminator exists there, so
  a split would silently reassign one node's entire output set;
- the library **refuses to guess** which row is real (FR-019a is registered
  `repairable=False`), for the same reason.

**Run this before the narrowing lands, while the map still loads.** After it, a
colliding map does not load at all — and the two components that would tell you
what is wrong are the two that say it least well (see
[consumer-census.md](consumer-census.md)): `cuems-nodeconf` propagates an
unhandled `ValidationError`, and `cuems-power-bridge` advises you that "every
node needs uuid, mac, name, node_role and ip" when every node has all five.

### The procedure

The library declines to automate this on purpose. It is a judgement about
hardware.

1. **Find it.** The check names it, and so does the re-mint's abort, with both
   MACs:

   ```bash
   cuems-init-node --check --json | python3 -m json.tool | grep -A2 uuid
   ```

2. **Decide which row is the real node.** Two pieces of evidence:
   - the two rows' **hardware addresses** — compare each against the MAC of the
     machine you believe it to be (`cat /sys/class/net/ethernet0/address`);
   - the **scripts naming the shared token**, which the abort message lists.
     Whichever node those outputs physically belong to is the node that owns the
     identity.

3. **Treat the other row as never provisioned.** On that machine:

   ```bash
   sudo cuems-init-node --force-new-identity --yes
   ```

   It receives a fresh uuid4 and **must be re-adopted** — see §9.

4. **Confirm the collision is gone** with `--check` on the controller, then
   return to §1.

---

## 8. Restart, and verify

```bash
# on every node
sudo systemctl start cuems-nodeconf.service
sudo systemctl start cuems-node-engine.service cuems-videocomposer.service
# on the controller
sudo systemctl start cuems-controller-engine.service cuems-editor.service
sudo systemctl start cuems-power-bridge.service
```

`cuems-nodeconf` derives the Avahi record from `settings.xml` at every start and
role change (feature 011, D14 shape B), so the live record picks up the new
identity without further action.

### 8a. Per node: the check

```bash
cuems-init-node --check
```

Exit `0` on every node.

### 8b. The roll-call — how you know the *cluster* is converged (FR-036c)

**The controller's run exiting cleanly says nothing about any other node.** It
never touched them. Converged is a **count**, not an impression.

Collect one completion record per node:

```bash
for node in controller node1 node2 node3; do
  scp "$node":/var/lib/cuems-utils/remint/completion-*.json "./records/$node/"
done
```

Then compare the set of records against the rows in the network map. One record
per row means converged. **A row with no record is a node the migration did not
reach** — not a node that is probably fine. Re-mint it (§5) and collect its
record.

Each record names: the node's **new** identity, the table's digest, the scope
(`configuration` or `both`), the paths it rewrote, and each verification result.
A record whose `table_digest` differs from the others is not part of this
migration — find out which table it applied.

### 8c. The incomplete-re-mint detector (FR-036, M-e)

The roll-call covers nodes. This covers **scripts the reach did not touch**.

After re-minting, load each project on the controller and watch
`cuems-engine`'s `cluster_warning` OSC status (`/engine/status/cluster_warning`,
a JSON string). A non-empty `"missing"` list **naming an old identity** is a
script the reach did not cover:

```
{"load_id": 3, "project": "showname", "missing": ["0367f391-ebf4-11b2-..."], "unreachable": []}
```

An old identity there means a document outside
`projects/*/` and `trash/projects/*/` still carries one — a project directory
with an unexpected layout, or a file the root-element identification correctly
declined to rewrite. Find it, and re-mint with `--library` pointed at the tree
that holds it.

`"missing"` naming a *new* identity is a different problem — a node that is not
reachable or not adopted — and is not this migration's business.

---

## 9. What this migration costs you

Both of these are permanent. Read them before step 4, not after.

### 9a. A re-imaged node no longer regenerates its identity (FR-033, §9.5)

Before this work, a node whose disk was re-imaged came back, was rediscovered,
and got an identity again. That is no longer true, and the change is
deliberate — it is what closes the cloned-disk collision route.

A re-imaged node arrives **unprovisioned** (sentinel identity), is minted a
fresh uuid4 by `cuems-init-node`, and **must be re-adopted** from the editor's
settings panel. Its old identity is gone; nothing recovers it. Every output
mapping keyed to the old identity has to be re-made.

**Keep the substitution table.** It is the only record of which old identity
became which new one, and it is what lets you reconstruct an output set after a
node is lost.

### 9b. A cloned disk is now refused (FR-019d, FR-036a)

`cuems-init-node` derives this hardware's MAC on every run and compares it with
the one stored in `settings.xml`. A mismatch is **refused**, not resolved:

```
ERROR: settings.xml carries identity … minted for mac=aabbccddee01, but this
hardware is mac=aabbccddee99 (ethernet0). This is either a disk image restored
onto other hardware — in which case keeping the identity gives two nodes one
name — or a replaced NIC on this same node, in which case keeping it is right.
Only you can tell which.
```

Two ways forward, and you choose:

- **it is a clone**: `sudo cuems-init-node --force-new-identity --yes`, then
  re-adopt;
- **it is a replaced NIC on the same machine**:
  `sudo cuems-init-node --mac <the new address>`, which keeps the identity and
  corrects the stored MAC.

This changes how a venue provisions. Cloning a provisioned disk used to work by
accident and produced two nodes with one identity. Clone an **unprovisioned**
image instead, and let each machine mint its own on first boot.

### 9c. The four collision routes, and which this feature closes (FR-036a, M-l)

| Route | Before | After |
|---|---|---|
| Cloning a provisioned disk | two nodes share one identity, silently | **refused** (§9b) |
| `--uuid` naming an identity already in the map | accepted and written | **refused**, naming the other row's MAC |
| A map that already collides | loads; `NodeIndex.merge` collapses the duplicate silently | **raises for every reader**; the re-mint aborts (§7) |
| Two nodes minting independently | possible whenever two tables exist | **closed by design**: the table is built once, on the controller, and a plain node without one refuses |

The third row is the one that changes what an existing cluster does, which is
why §7 comes before the narrowing and not after.

---

## 10. If something goes wrong

| Symptom | What it means | What to do |
|---|---|---|
| The run **aborted** naming two rows and their MACs | a pre-existing collision. **Nothing was written** | §7 |
| The run **refused**: "not the controller and no substitution table" | you are on a plain node. **Nothing was written** | §4a, then §5 |
| The run **refused**: "the table was built by …, which is not this cluster's controller" | the table was minted by something with no authority | discard it; copy the controller's |
| Exit **2**, `VERIFICATION FAILED` | rewritten, but the tool cannot prove the result is right | read the named failures. The table is on disk and `applied` names every file rewritten; fix the named document and re-run — the re-run loads the table and skips what is done |
| The run was **interrupted** | the table and its `applied` list are on disk | re-run with `--resume`. The table is **never** rebuilt, so no node receives a second identity |
| A node's library replica still holds old prefixes | replication has not run | §5's check |
| `cluster_warning` names an old identity | a document the reach did not cover | §8c |

**Never delete the substitution table** until the roll-call is complete and every
project has loaded cleanly. It is the operation's only durable record.

---

## 11. What this feature does *not* do

- It does not change the compound `<identity>_<output>` form. A stale prefix
  stays schema-valid, which is why the substitution is literal.
- It does not change the library version. Schema changes are signalled by the
  document version marker: `network_map` 1→2, `project_mappings` 1→2,
  `settings` 2→3.
- It does not register a conversion for any of those three steps, and that is
  the design. A per-document mint would give `settings.xml` and
  `network_map.xml` different answers for the same node — §9.4's measured
  failure. An identity cannot be repaired one document at a time.
- It does not narrow `project_mappings.xsd`'s `MappedToType/uuid` (out of scope
  by FR-020b, handed to feature 014) or `script.xsd`'s `UuidType`, which types
  cue and media identifiers and must **not** admit the sentinel — a nil cue id
  is a bug, not a placeholder.
