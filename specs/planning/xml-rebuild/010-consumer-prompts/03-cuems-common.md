# Feature 010 — `cuems-common`: conversion ordering, the packaging gate, half the Avahi cutover

**Status:** ready to run — **pairs with [04-cuems-nodeconf](04-cuems-nodeconf.md)**
**Date:** 2026-09-03
**Repository:** `/disk/Projects/StageLab/cuems-common`
**Run order:** 03 of 06. See the [index](README.md).

This repository ships no compiled code and is therefore easy to underestimate.
It carries the release gate, the on-upgrade conversion, and half of a two-daemon
wire rename.

---

## 0. State of this repository, measured 2026-09-03

| | |
|---|---|
| Current branch | `007-node-model-migration` @ `78b89ad`, clean, **unmerged and unreleased** |
| Base for `feat/xml-refactor` | **`007-node-model-migration`** — *not* `main` |
| Spec-kit | **absent** — added on first run (§1) |
| Constitution | **absent** — written on first run (§2) |
| Existing features | none → this becomes **`001-node-role-and-conversion-ordering`** |
| Tests | `pytest tests/` — no `pyproject.toml`, no `pytest.ini`, no `conftest.py`; **3 test files** |
| `cuems-utils` floor | `debian/control` `>= 0.1.0rc15` + `Breaks: cuems-nodeconf (<< 0.1.0-8)` |

**Base on `007-node-model-migration`, not `main`.** Four commits live only there
and are this feature's foundation: the schema mirror and shipped-map conversion
(`9fc738e`), the conversion script wired into `postinst` with three tools updated
(`f4a8b3c`), versioned package dependencies (`6a9ec7f`), and the documentation
pass (`78b89ad`). Branching from `main` silently discards feature 007's entire
`cuems-common` phase.

`cuems-utils`'s `CLAUDE.md` claimed until 2026-09-03 that this work was "not yet
updated for the rename". It is done — on a branch, unmerged. C9 corrected that
line; do not re-derive it from the stale claim.

**This repository already holds the only mechanically enforced edge of the
release gate** (`Breaks: cuems-nodeconf (<< 0.1.0-8)`). Four more edges are
missing across the ecosystem, and the demonstration that any of them actually
works has been deferred twice.

---

## 1. Branch and bootstrap

```bash
cd /disk/Projects/StageLab/cuems-common
git checkout 007-node-model-migration
git checkout -b feat/xml-refactor

specify init --here --integration claude --script sh --force
```

Commit the scaffold as its own GPG-signed commit before `/speckit.constitution`.
**Commits here are GPG-signed** — retry on "gpg failed to sign", never
`--no-gpg-sign`.

Spec-kit's sequential branch numbering will want its own branch. Stay on
`feat/xml-refactor`; let it name
`specs/001-node-role-and-conversion-ordering/` only.

---

## 2. Constitution — write one, this repository has none

```
/speckit.constitution

Establish the constitution for cuems-common, grounded in what this repository actually is.
Read CLAUDE.md first; it is accurate and current.

WHAT THIS REPOSITORY IS: the system-level Debian package delivering all shared
configuration, systemd units, and operator tools for a CUEMS install. It carries NO
compiled code — every executable it ships is a shell or Python script; the compiled daemons
come from their own packages and are only wired into the systemd graph here. It ships:
systemd service/target/path/socket units for both host roles plus drop-ins for third-party
units (Apache2, hostapd, Avahi, rtpmidid); operator tools in usr/bin/; internal service
helpers in usr/lib/cuems/bin/; per-install config and XSD schemas in etc/cuems/;
Avahi/interface templates in usr/share/cuems/; and sysctl, JACK, DHCP/hostapd, ALSA,
rsyslog, logrotate, sudoers, tmpfiles and modules-load drop-ins in etc/. A CUEMS host is
either a controller (one per cluster) or a node (many), and roles are DYNAMIC — any host
can be promoted or demoted without a reinstall, decided only by <node_role> in
/etc/cuems/network_map.xml.

PRINCIPLES THE WORK ALREADY IMPLIES — derive from these, do not invent unrelated ones:
- Its unit of delivery is a PACKAGE UPGRADE ON A LIVE MACHINE, not a merge. Correctness
  means postinst leaves a working host — including a host that was mid-show, whose conffiles
  the operator has locally modified, and whose services are about to be restarted by
  dh_installsystemd. An upgrade that fails halfway is the failure mode to design against.
- It OWNS FILE-FORMAT MIGRATION for the ecosystem's config. It already ships
  cuems-migrate-network-map and runs it from postinst. Any conversion it runs MUST back up
  before it writes, MUST be idempotent (postinst runs again on every reinstall), and MUST
  NOT fail the upgrade.
- It is the ORDERING AUTHORITY. Nothing else in the ecosystem can sequence a conversion
  against a service restart. Ordering decisions belong here and get written down, not
  inherited.
- It enforces the RELEASE GATE mechanically. Versioned dependencies and Breaks are how this
  ecosystem refuses an out-of-order upgrade; prose in a migration guide is not enforcement.
  A gate that has never been demonstrated against a real install is a claim, not a gate.
- DOWNGRADE IS UNSUPPORTED and that is a deliberate position, not an oversight — the only
  path back from a converted node is the timestamped backup the conversion writes. Say so.
- Commits are GPG-signed.

Testing: this repository has three test files and no Python packaging. State a gate it can
actually meet — shell/Python tools and conversion scripts are testable; systemd unit
ordering largely is not, and pretending otherwise produces a rule that gets waived. Be
explicit about which half is covered by tests and which by a documented manual upgrade
check.

Do NOT weaken any rule to accommodate the migration that follows.
```

---

## 3. Context block — paste verbatim into `/speckit.specify` and `/speckit.plan`

```
CONTEXT — read these before writing anything. They live in the SIBLING checkout
/disk/Projects/StageLab/cuems-utils, not in this repository:
  .../cuems-utils/specs/007-node-model-migration/migration-guide.md   §7 = THE RELEASE GATE, §9 = the
                                                                     Avahi files 007 deliberately excluded
  .../cuems-utils/specs/008-rebuild-extension/migration-guide.md      the conversion tool and its FR-042 entry
  .../cuems-utils/specs/planning/xml-rebuild/xml-rebuild-09-consumer-audit.md   C6, C7, C9, C11 are this repo's
  .../cuems-utils/specs/planning/xml-rebuild/xml-rebuild-07-speckit-prompts.md  §2 = the FULL decision list
  AND IN THIS REPOSITORY: docs/node-identity-contract.md, debian/postinst, debian/control

SETTLED — the decisions that bind THIS repository. Do not reopen. Anything
outside this subset: read §2 of the prompts file above.
  D20 document compatibility is governed by an EXPLICIT version marker (doc_version), and
      008 built the conversion registry behind it
  D21 an OLD document converts on read; the same logic is also a standalone tool
  D33 the Avahi TXT-record vocabulary (node_type=master|slave|firstrun) is renamed in BOTH
      this repository AND cuems-nodeconf, inside feature 010, as ONE coordinated cutover --
      including the two template FILENAMES and the debian/install entries that place them.
      It cannot be half-renamed: a listener reading node_role against a publisher writing
      node_type discovers nothing, and discovery failure is how a cluster loses its topology.
  D27 nothing in the ecosystem releases until every 010 flow lands. This repository is where
      that gate is mechanically enforced.
  D30/D18b 008's duration promotion invalidates EVERY project document on disk, carried by
      the script 1->2 conversion. 007 converted ONE config file per node; this converts a
      whole library.

MEASURED STARTING STATE — verified against live files 2026-09-03, not transcribed:
  debian/postinst:35-58  the network_map node_type -> node_role conversion, run over BOTH
      /etc/cuems/network_map.xml and its .dpkg-new sibling, `|| true`, never fails the
      upgrade. Its own comment defers the ordering against dh_installsystemd's service
      restart to "feature 008" — a closed, cuems-utils-only feature. That deferral is THIS
      feature's to resolve (007 FR-011d-ii).
  debian/control:12  cuems-utils (>= 0.1.0rc15)     :38  Breaks: cuems-nodeconf (<< 0.1.0-8)
      ^ the ONLY mechanically enforced edge of the release gate in the whole ecosystem
  etc/cuems/network_map.xml:9   <node_role>controller</node_role>   (already converted)
  etc/cuems/network_map.xsd     the mirrored schema
  etc/avahi/services/cuems.service:6,13          <txt-record>node_type=master</txt-record>
  usr/share/cuems/cuems.service.firstrun:6,13    node_type=firstrun
  usr/share/cuems/cuems.service.master:6,13      node_type=master
  usr/share/cuems/cuems.service.slave:6,13       node_type=slave
      ^ THE RETIRED WORD IS IN THE FILENAME of the last two, so the change reaches
        debian/install and anything resolving a template by name
  CLAUDE.md:88  says CONTROLLER_NETWORK_FLAG etc. are "migrated in feature 008" — the
      2026-08-25 renumbering makes that 010 (C9). Correct it.
  tests/test_network_map_conversion.py, tests/test_controller_resolution.py,
  tests/test_schema_mirror.py   the three existing tests

ECOSYSTEM PIN STATE (C7), measured the same day — this is what "the gate" currently is:
  cuems-engine    pyproject >=0.1.0rc10   debian/control >= 0.1.0rc4   (they disagree)
  cuems-editor    pyproject >=0.1.0rc10   no debian entry
  cuems-nodeconf  pyproject >=0.1.0rc15   debian/control >= 0.1.0rc5
  cuems-wsclient  pyproject >=0.1.0rc5 (optional)   debian/control >= 0.1.0rc5
  cuems-common    debian/control >= 0.1.0rc15 + Breaks: cuems-nodeconf (<< 0.1.0-8)
  Every one of those is a LOWER BOUND. A lower bound cannot express "refuse a library that
  moved past me", which is precisely what the gate says.
```

---

## 4. Specify

```
/speckit.specify <PASTE CONTEXT BLOCK>

Settle the conversion ordering, make the release gate real, and rename this repository's
half of the Avahi discovery vocabulary.

WHAT MUST BE TRUE WHEN DONE:
- The postinst ordering is DECIDED AND WRITTEN DOWN, not inherited. The network-map
  conversion and dh_installsystemd's autogenerated service restarts both run in postinst,
  and their relative order decides whether a service reads the converted map or the old one.
  007 deferred this here because the services doing the reading are the ones feature 010
  migrates — they are migrated now, so the deferral has expired.
- 008's SECOND conversion is placed, and placed differently. cuems-convert-documents
  rewrites every project document in the library, not one config file per node. It has
  different timing characteristics entirely: it runs over user data at scale, it takes real
  time, and it writes a timestamped backup per document. DECIDE whether postinst is the
  right place for it AT ALL — and if it is not, say what is (a first-boot unit, an operator
  command, a one-shot service ordered before the readers) and why. State what an operator
  sees while it works, what happens to a library that is interrupted mid-conversion, and how
  the backups are retained and eventually reclaimed. This is a first-class deliverable, not
  a note.
- The alternative to converting on disk is named and priced. 008 made convert-on-read work
  (an old document loads and converts in memory, the file untouched), so "never run the
  batch tool" is a real option with a real cost: every load re-runs the conversion forever.
  Choose, and record the reasoning — both paths exist and are tested, which is exactly why
  the choice must be explicit.
- The release gate acquires the edges it is missing (C7). Today exactly ONE is mechanical:
  this repository's Breaks against cuems-nodeconf. Every other consumer declares only a
  lower bound. Supply the missing bounds — and RUN 007's twice-deferred mechanical
  demonstration (its T054b, guide §13): install an out-of-order combination and watch dpkg
  actually refuse it. It was deferred because no releasable .deb of any of the three
  repositories existed; feature 010 is the release, so the excuse has expired. A gate that
  has never been demonstrated is a claim.
- This repository's half of the Avahi cutover lands (D33): the node_type TXT record in
  etc/avahi/services/cuems.service (:6, :13) and in
  usr/share/cuems/cuems.service.{firstrun,master,slave} (:6, :13 each), INCLUDING the
  master/slave FILENAMES and the debian/install entries that place them. Coordinate with
  flow 04 (cuems-nodeconf), which owns the publisher, the listener and its own copies of
  these three templates. The two halves MERGE TOGETHER: a half-renamed intermediate state
  is a cluster that cannot discover itself.
- CLAUDE.md:88's "migrated in feature 008" is corrected to 010 (C9).
- The cluster-upgrade story covers the ENGINE'S DEPLOY PATH, not only dpkg. cuems-engine
  rsyncs each project's script.xml from controller to node (CuemsDeploy.py:329/:649). A
  controller whose library is converted pushes version-2 documents to every node it deploys
  to, and a node on older cuemsutils fails at SHOW-LOAD time — not at upgrade time, and not
  through any channel a package manager mediates (C11). Whatever ordering this spec picks
  must survive that path, or say explicitly that the cluster upgrades as a unit and this
  path is therefore never mixed-version.

DOWNGRADE remains unsupported (007 T087b): no reverse conversion exists or is planned, and
the only path back for a converted node is the timestamped backup. Do not quietly introduce
one; if this spec changes that position, it does so explicitly.
```

---

## 5. Clarify

```
/speckit.clarify
```

Force the one question everything else hangs on: **does the document conversion
run in `postinst` at all?** Every other ordering decision in this spec is
downstream of it.

---

## 6. Plan

```
/speckit.plan <PASTE CONTEXT BLOCK>

Per-file scope:
- debian/postinst — the ordering decision, and wherever cuems-convert-documents ends up
  if it ends up here.
- debian/control — the missing gate edges; keep the existing Breaks.
- debian/install — the renamed template filenames.
- etc/avahi/services/cuems.service, usr/share/cuems/cuems.service.{firstrun,master,slave}
  — the TXT records and the two filenames.
- CLAUDE.md — the stale feature number.
- tests/ — the conversion-ordering and gate tests, alongside the three that exist.
- possibly a new unit or operator tool, if the conversion does not belong in postinst.

Sequencing: pairs with flow 04. Their specs are separate because the repositories are;
their MERGES are simultaneous (D33). Nothing here releases before every other 010 flow
lands (D27) — and this repository is where that is enforced rather than described.

Constitution check, against the constitution written in §2:
- The live-upgrade principle governs the whole conversion-ordering question.
- The ordering-authority principle is why the deferral stops here rather than moving again.
- The mechanical-gate principle is what makes the dpkg demonstration a deliverable rather
  than a nice-to-have.
- Testing: state which half is covered by tests and which by a documented manual upgrade
  check, per the constitution — and make the manual half a written procedure, not a memory.
```

---

## 7. Tasks, checklist, analyze, implement

```
/speckit.tasks
```
```
/speckit.checklist Upgrade readiness: the postinst-vs-service-restart ordering DECIDED and
written, not inherited; the document conversion's placement decided with the mid-conversion,
backup-retention and operator-visibility questions answered; the convert-on-read alternative
priced rather than ignored; the release gate's missing edges present AND demonstrated
against a real out-of-order dpkg install, not asserted; the Avahi TXT records, both template
FILENAMES and the debian/install entries renamed, verified against flow 04's half so no
half-renamed state ships; the CuemsDeploy version exposure covered by the chosen ordering or
explicitly excluded by a cluster-upgrades-as-a-unit statement; CLAUDE.md:88 corrected; and a
controller-plus-node cluster upgrade performed, not just a single-node one.
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

`pytest tests/` green; the postinst ordering decided and written down; the
document conversion's placement decided with mid-conversion, backup and operator
visibility answered; the release gate's missing edges present **and** demonstrated
against a real out-of-order install; this repository's half of the Avahi rename
complete including both filenames and `debian/install`, merged simultaneously with
flow 04; `CLAUDE.md:88` corrected; and a controller-plus-node cluster upgrade that
comes back with its topology intact.

**This repository is where D27 is enforced.** Nothing in the ecosystem releases
until every 010 flow lands, and after this feature that sentence is a package
relationship rather than a paragraph.
