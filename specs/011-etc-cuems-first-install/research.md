<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Research — `/etc/cuems` first install (feature 011)

**Phase 0 output** for `plan.md`. Every decision below was reached by measuring the tree, the
sibling checkouts and the build host on 2026-09-25, not by assumption. Where the spec deferred a
question to the plan (Q4, Q5, Q6) the decision is here, with what was measured to reach it.

Environment measured: `feat/xml-refactor` at `8b29556` (this branch), Debian 12.15 build host,
`debhelper 13.11.4`, `dh-virtualenv 1.2.2`, `dpkg 1.21.23`, `mmdebstrap 1.3.5`, Python 3.11.9
(pyenv) for the suite, `/usr/bin/python3` = 3.11.2 for the package. **`hatch` is not installed on
this host**; the execution document's `pyenv exec hatch` form was written for another machine.
`uvx hatch` works and is what `quickstart.md` uses.

---

## R1 — Where `cuems-init-node` lives, and how `postinst` invokes it (spec Q5 / OPEN-4)

**Decision**: the entry point is declared in `[project.scripts]` as
`cuems-init-node = "cuemsutils.tools.init_node:main"`. dh-virtualenv installs it at
`/usr/lib/cuems/bin/cuems-init-node` with its shebang rewritten to the venv interpreter
(`dh_virtualenv/deployment.py:fix_shebangs`, measured). `postinst` invokes it **by absolute
path**, wrapped in `timeout`, and never through `PATH`. A `/usr/bin/cuems-init-node` symlink is
added via `debian/cuems-utils.links` for operators.

**Rationale**: the shared venv is one-way — `/usr/bin/python3` cannot import `cuemsutils`
(CLAUDE.md), so a script under `/usr/bin` executed by the system interpreter would fail on
import. A symlink is safe because the target's shebang selects the venv interpreter; a wrapper
script that itself imported `cuemsutils` would not be. The module goes under `tools/` (the
public configuration façade: `ConfigManager`, `NodeList`), not `xml/` (internal, `__all__ = []`),
because the tool's job is node coherence, not document mechanics.

**Alternatives considered**: a stdlib-only `/usr/bin` script (rejected: it would have to
re-implement the descriptor, the adapters and the validators — the tool "imports it heavily" by
design); installing under `/usr/lib/cuems/bin` with no `/usr/bin` link (rejected: the migration
guide asks operators to run it, and `cuems-common`'s own Python helpers already follow the
symlink-or-absolute-path convention).

## R2 — How the generator runs at build (spec Q6)

**Decision**: `debian/rules`'s `override_dh_virtualenv` runs `dh_virtualenv` and then, in the
same recipe:

```make
	debian/cuems-utils/usr/lib/cuems/bin/python -m cuemsutils.xml.make_defaults \
	    --out debian/cuems-utils/usr/share/cuems/defaults
	install -d debian/cuems-utils/usr/share/cuems/schemas
	install -m 0644 src/cuemsutils/xml/schemas/*.xsd debian/cuems-utils/usr/share/cuems/schemas/
	install -m 0644 src/cuemsutils/defaults/system-defaults.toml debian/cuems-utils/usr/share/cuems/defaults/
```

**Rationale (measured)**: dh-virtualenv's sequence file inserts `dh_virtualenv` *before*
`dh_installinit` and removes `dh_auto_install`, so by the time the override runs the venv exists
under the staging tree, `cuemsutils` is pip-installed into it, and `bin/python` is a symlink to
`/usr/bin/python3` (the absolute pin in `debian/rules`) — runnable on the build host. The
interpreter-hardlinking autoscript runs only at *install* time (`configure`), so it is irrelevant
to the build. Every path in the recipe is version-free: the generator is reached through the
venv's `bin/python`, never through `lib/python3.11/…`, which is what keeps a trixie build
neutral (FR-044). The `.xsd` and `.toml` are copied by `install`, not `debian/install`, because
`debian/install` runs from `debian/tmp`/source and this keeps the whole `/usr/share/cuems` tree
in one recipe a reviewer reads top to bottom.

**Determinism (measured)**: two consecutive `generate_settings_example().save()` calls produce
byte-identical files (SHA-256 equal); the writer emits no timestamp, and the sentinel is a fixed
value. The build asserts it: `make_defaults` generates twice into temp dirs and refuses to
install if the two differ.

**Alternatives considered**: generating in `override_dh_install` (rejected: the venv does not
exist yet at that point); committing the generated XML (rejected by D2 — a second source of
truth).

## R3 — Custody transfer of `/etc/cuems/network_map.{xml,xsd}` from `cuems-common` (FR-005)

**The trap, measured**: `dpkg-maintscript-helper rm_conffile` *moves the live file aside* —
an unmodified conffile goes to `.dpkg-remove` and is **deleted** in `postinst`; a modified one
becomes `.dpkg-backup` then `.dpkg-bak`. Either way the path is empty when the upgrade ends.
`cuems-common`'s own `preinst` already documents exactly this for `/etc/network/interfaces` and
works around it with a pre-save snapshot restored in `postinst`. Simply dropping the paths from
`debian/install` without `rm_conffile` leaves them as *obsolete conffiles*, which dpkg deletes on
a later `purge` of `cuems-common` — the live cluster topology gone on an unrelated purge.

**Decision** — `cuems-common 1.3.0-23`:

1. `preinst`: if `/etc/cuems/network_map.xml` exists, snapshot it byte-exact to
   `/var/backups/cuems-common.network_map.xml.presave` (the established pattern), then
   `rm_conffile /etc/cuems/network_map.xml 1.3.0-23~` and `rm_conffile /etc/cuems/network_map.xsd 1.3.0-23~`.
2. `postinst`: the same two `rm_conffile` calls (the helper needs all three phases); then
   restore `network_map.xml` from the snapshot if the path is absent, and remove
   `network_map.xml.dpkg-bak` **only if** it is byte-identical to the snapshot (so a `.dpkg-bak`
   that predates this upgrade is never touched); then, if `/etc/cuems/network_map.xsd` is absent,
   copy `cuems-utils`'s pristine `/usr/share/cuems/schemas/network_map.xsd` into place and remove
   any `network_map.xsd.dpkg-bak` (package content, no operator data).
3. `postrm`: the two `rm_conffile` calls (restores on abort).
4. `debian/install`: the two `etc/cuems/network_map.*` lines removed; the repository's
   `etc/cuems/network_map.xsd` file deleted; `etc/cuems/network_map.xml` kept only as the
   documentation example already installed under `/usr/share/doc/cuems-common/`.

**Package relations**: `cuems-utils` declares `Breaks: cuems-common (<< 1.3.0-23~)`.
**`Replaces` is deliberately omitted**: `cuems-utils` ships nothing under `/etc` in its manifest
(D5 — the schemas are copied by `postinst` from `/usr/share/cuems/schemas/`), so there is no
manifest overlap for `Replaces` to license. `Breaks` is what forces apt to upgrade the pair
together, which closes the window in which new `cuems-utils` would rewrite an `.xsd` that old
`cuems-common` still records as its conffile. `cuems-common`'s existing
`Depends: cuems-utils (>= 0.1.0rc16)` already names the shipping version (spec M6, A3).

**Verification**: the lifecycle test installs old `cuems-common` (a stub carrying the two
conffiles, from `tests/packaging/stubs/`) then upgrades in **both** unpack orders and via
`apt install ./a.deb ./b.deb`, asserting the live map is byte-identical, no `.dpkg-*` sibling
exists, and a subsequent `purge cuems-common` leaves the map in place.

## R4 — Seed values as TOML: file, key space, and the single copy

**Decision**: one file, `src/cuemsutils/defaults/system-defaults.toml`, shipped as **package
data** inside the wheel (the same mechanism as the schemas: `[tool.hatch.build] include`), read
through `importlib.resources` by both the build-time generator and `cuems-init-node`. The same
bytes are also installed to `/usr/share/cuems/defaults/system-defaults.toml` as the
operator-visible reference D9 names, and a test pins the two byte-identical. Operator overlay
files under `/etc/cuems/defaults.d/*.toml` use the same table layout.

Key space — one table per (schema, type), values typed as TOML scalars:

```toml
[settings.SettingsType]
conf_path = "/etc/cuems"
editor_url = "formitgo.local"
# ...

[settings.NodeConfType]
oscquery_ws_port = 9190
# ... uuid and mac are NOT here: identity is never a default (FR-033)

[settings.VideoPlayerType]
output_latency_ms = "auto"        # string
[settings.DmxPlayerType]
output_latency_ms = 35            # integer — the distinction TOML preserves (FR-035)

[network_map.NodeType]
name = "unprovisioned"            # Q1b
ip = "0.0.0.0"
node_role = "firstrun"

[project_mappings.CuemsProjectMappingsType]
number_of_nodes = 1
default_audio_output = ""         # placeholder until R12 settles the spelling
# ...
```

The generator keeps FR-010's two-way completeness check: a required field with no entry fails
naming `(schema, type, field)` and the file; an entry naming no declared field fails naming the
stale key. `descriptor._SETTINGS_EXAMPLE_VALUES` is deleted; `descriptor.generate_settings_example`
becomes a thin call into the new module so its eleven tests in
`tests/contract/test_settings_example_generation.py` keep their meaning with the import moved.

**Rationale**: `tomllib` is stdlib in 3.11 (read-only is all that is needed); typed scalars are
the one property the format had to have; one copy read by one code path avoids a second source
of truth, and the `/usr/share` copy is a courtesy that `dpkg -V` can verify.

**Alternatives considered**: reading `/usr/share/cuems/defaults/system-defaults.toml` at runtime
(rejected: an editable or test install has no `/usr/share` copy, so the tool would need a
fallback — two code paths); keeping the values in Python (rejected by D7/D9).

## R5 — The write record (FR-027a)

**Decision**: `/var/lib/cuems-utils/init-node/last-written.json` — one JSON object per document
(`settings`, `network_map`, `default_mappings`) holding the SHA-256 of the bytes written and a
flat map of dotted field path → value as written (identity fields included, for `--check`'s
benefit). Created by `cuems-init-node` after a successful write; directory created by `postinst`
(`install -d -m 0755`); removed by `postrm purge` together with the nine `/etc/cuems` paths.
Absent record ⇒ every on-disk difference is an operator edit (kept and reported), per FR-027a.

**Why not under `/etc/cuems`**: it is state, not configuration, and every extra path under the
shared directory is one more thing purge must reason about. `/var/lib/cuems` is `cuems-common`'s
(the `cuems` user's home, created by its `preinst`); a sibling directory owned by this package is
cleaner than sharing.

**Field comparison**: for each dotted path in the record, compare the on-disk decoded value with
the recorded one. Equal ⇒ recompute from seed + overlay. Different ⇒ operator edit, keep. Fields
absent from the record (new upstream fields) ⇒ take the computed value. `network_map.xml`'s
other rows are never compared — they are `cuems-nodeconf`'s (FR-027b).

## R6 — Writing the triple "atomically"

**Decision**: build all three documents in memory, validate each (T1) before touching disk,
write each to a temporary file beside its target via the existing `write_tree` mechanism
(`mkstemp` in the destination directory), then `os.replace` the three in a fixed order; if any
replace fails, put the previous files back from in-memory copies taken before the first replace.
Nothing is written to `/etc/cuems` until all three have validated.

**Honest limitation, recorded**: three `os.replace` calls are not one filesystem transaction.
The window is microseconds and the recovery is deterministic, which satisfies FR-025's
"either all three are replaced or none is" at the granularity an operator can observe. A
`rename`-based directory swap was rejected because `/etc/cuems` is shared with four other
packages' files.

**Locking**: the tool takes an `flock` on `/run/lock/cuems-init-node.lock` so two concurrent
runs (an operator and a provisioning script) serialize; `cuems-nodeconf` is detected by
`systemctl is-active cuems-nodeconf.service` and produces the warning the spec's edge case
requires.

## R7 — How the Avahi record derives from `settings.xml` (D14, FR-040a) — the mechanism

**Decided 2026-09-28 (shape B of R7a, maintainer's call)**: **`cuems-nodeconf` is the sole
writer of `/etc/avahi/services/cuems.service`, and derives it from `settings.xml` at every
start.** The first version of this section chose a `cuems-config-node render` subcommand in
`cuems-common`; R7a's analysis and the maintainer's premise — nodeconf becomes integral and
unmasked across the fleet once the xml-refactor lands — replaced it.

**Measured** (details in R7a): the live record's writer is already nodeconf (root,
`shutil.copy2` of `/usr/share/cuems/cuems.service.<role>`); nodeconf learns its own uuid from
its own announcement, never from `settings.xml`; the templates are package content that every
`cuems-common` upgrade resets; `cuems-config-node` is a second minter (`uuid1()`) whose
template rewrite is how the production controller's uuid reached the shipped templates (M2, M3).

**Decision**:

1. **Templates** (`cuems-common`): the three shipped `cuems.service.{firstrun,controller,node}`
   carry the **sentinel** uuid and are never rewritten by any tool — pure package content.
2. **`cuems-nodeconf`** (its own tree, delivered by **its feature `003-startup-readiness`**, whose
   brief landed upstream 2026-09-28 — see R20): at start, **before `set_comms()`** and before
   discovery, so that an unprovisioned node never creates `/tmp/nodeconf.ipc` (the engine's
   readiness probe is that socket's existence; a refusal after creating it would read as
   "available" — the C2 shape from `nodeconf-map-write-divergence.md` §5),
   read `uuid`/`mac` from `settings.xml` through the `ConfigManager` it already constructs;
   render the role template into the live file by literal substitution of the 36-character
   sentinel token (design §10.2's rule, the same one `cuems-init-node` uses); write atomically,
   reload `avahi-daemon` only if the bytes changed; **refuse to start** (exit non-zero,
   `NOT PROVISIONED` in the log) when `settings.xml` is absent or carries the sentinel — a node
   with no identity must not announce one. The same render runs on every role change (the
   three copy sites). After discovery, assert the discovered self carries the `settings.xml`
   uuid and refuse loudly otherwise (plan 09 §4's guard, now a cheap assertion).
3. **`cuems-config-node`** (`cuems-common`): loses `uuid1()` minting and every Avahi/template
   duty in this feature; keeps hostname, `/etc/hosts` and `avahi-daemon.conf` handling until
   nodeconf's identity chain retires it. Its `write` prints where identity now comes from.
4. **`cuems-common`'s `postinst`** makes no Avahi call beyond its existing live-file
   migration. The three dead `cp` rules in `etc/sudoers.d/99-cuems-avahi` are retired (the
   `reload` rule stays), and `test_template_consumers.py` is re-based.
5. **Transition**: the mutual `Breaks` **already exist** for the unreleased pair —
   `cuems-nodeconf 0.1.0-8` carries `Breaks: cuems-common (<< 1.3.0-23~)` and
   `cuems-common 1.3.0-23` carries `Breaks: cuems-nodeconf (<< 0.1.0-8)` (both from the
   `node_role` cutover) — so an old nodeconf can never copy a sentinel template verbatim beside
   new templates, and **no package relation changes**. The render lands in nodeconf's
   unreleased `0.1.0-8` entry; **no package is bumped** (R19). Unmasking nodeconf fleet-wide is part of the same landing;
   a node where it stays masked has an unmaintained record, which `cuems-init-node --check`
   reports (exit 1) and the migration guide answers with "enable and start cuems-nodeconf".
6. **`cuems-init-node`** prints, after any identity change, `restart cuems-nodeconf.service`;
   `--check` reads the live record (R14) and nothing else.
7. **One library primitive, shared** (R20): `NodeIndex.ensure(node) -> bool` — insert the caller's
   node dict **by reference** if no node carries its uuid, return whether it did — is added in
   this feature (inside `0.1.0rc16`, no bump). `cuems-init-node` uses it for the self-entry
   (FR-029, practice 3), and nodeconf's plan `09-self-node-seeding.md` §5 option 1 asked for
   exactly it, so feature 003 can seed from `settings.xml` without re-implementing map logic in
   the daemon (D22). It MUST honour the aliasing contract T091 pinned upstream — no `dict(node)`.

**Dividends**: feature 012's last step (design §10.5, "rewrite the Avahi TXT from the new
`settings.xml`") becomes "restart nodeconf"; `--force-new-identity` needs no operator step
beyond that; the duplicate-self failure cannot occur on a node whose nodeconf started, because
the announcement is derived from the source before discovery runs.

**Alternatives** — A (config-node renders, called from `cuems-common`'s postinst) and D (a
rendering helper in `cuems-common` invoked by nodeconf): both analysed in R7a; A rejected for
keeping identity in package-owned files and two writers; D rejected because its one advantage
over B — working on hosts without nodeconf — no longer describes the fleet.

## R7a — Ownership of the Avahi record: `cuems-common` (`cuems-config-node`) versus `cuems-nodeconf`

**Asked by the maintainer 2026-09-25** after R7's first version (shape A below): analyse the
implications of making the Avahi record `cuems-common`'s responsibility (through
`cuems-config-node`) against relying on `cuems-nodeconf`, whose name already says "node
configuration". **Outcome (2026-09-28): shape B**, on the maintainer's premise that nodeconf
becomes integral and unmasked across the fleet once the xml-refactor lands — which removes B's
only structural weakness and makes D's one advantage moot. R7 above now records B; this
section is kept as the argument.

### What was measured (sibling checkouts, 2026-09-25)

1. **The live record's writer today is `cuems-nodeconf`, not `cuems-config-node`.** It runs as
   root and `shutil.copy2`s `/usr/share/cuems/cuems.service.<role>` over
   `/etc/avahi/services/cuems.service` on every role decision (`set_node_role`,
   `_install_master_service_template`, the resume-controller path). The `sudo cp` rules in
   `etc/sudoers.d/99-cuems-avahi` are the *old* path ("the old `sudo cp` shelled out
   needlessly", nodeconf's own comment); nothing in production calls them any more — the only
   other copiers are three dev scripts in `cuems-engine/dev/scripts/`. The rules are dead
   privilege that `cuems-common`'s `test_template_consumers.py` still pins.
2. **`cuems-nodeconf` learns its own uuid from its own Avahi announcement.** `CuemsAvahiListener`
   builds a `Node` from each service's TXT `uuid=`; `retreive_local_node` picks the discovered
   node whose IP is this host's; that object becomes `self.node`, whose uuid is what nodeconf
   writes into `network_map.xml`. It never reads `settings.xml`'s uuid itself — `ConfigManager`
   does, in `load_network_map`, and nodeconf catches the resulting `ValueError` ("this node is
   not in the map yet"). So today's identity flow is **template → Avahi → nodeconf → map**, and
   `settings.xml` only enters through lookups that fail when the two disagree. That is the
   duplicate-self failure design §5 names, and on a fresh host it is the *default* state: the
   shipped template carries a production controller's uuid (M3).
3. **The templates are package content.** Every `cuems-common` upgrade rewrites them, so any
   identity written into them (by `cuems-config-node` today, by R7's `render` tomorrow) is host
   state living in `/usr/share`, reset on upgrade, and flagged by `dpkg -V` forever.
4. **`cuems-nodeconf` has already claimed this remit in writing.** Its `CLAUDE.md`: "when
   reactivated it also owns **node identity**: assigns `<role_id>` on adoption and applies the
   OS-side identity chain (hostnamectl + `/etc/hosts` + avahi-daemon.conf)" — exactly the
   duties `cuems-config-node write` performs by hand today. Its planning document
   `09-self-node-seeding.md` (maintainer, 2026-09-17) settles that `settings.xml` is the identity
   source, that nodeconf seeds its own row from it (`uuid`/`mac` via `ConfigManager`), and that
   "a seeding implementation should still verify [the TXT uuid equals `settings.xml`] at run
   time … and refuse loudly on a mismatch". The `cuems-nodeconf apply-identity [--check]` CLI
   the contract document cites is **planned, not implemented**.
5. **`cuems-nodeconf` is optional and mostly off.** `cuems-common` only `Breaks` old versions
   (no `Depends`); the unit is enabled by `cuems-common`'s `postinst` but never started there;
   it is masked at Medina and "still disabled elsewhere in the fleet" (re-enabled on one
   controller since 2026-06). On a host without nodeconf, nobody writes the live record at
   all — it is hand-placed, "shipped by no package".

### The three shapes

**A — R7 as planned: `cuems-common` renders (`cuems-config-node render`, called from its
`postinst`).**
*For*: works on the nodeconf-less majority; fixes the upgrade-reset at the place it happens;
no third repository; the handover commit already touches `cuems-config-node`.
*Against*: it **institutionalises finding 3** — per-host identity keeps living in `/usr/share`
templates that a package owns and resets; it makes `cuems-config-node` a second writer of the
live record beside nodeconf (F1 fails at document granularity for `cuems.service`); it leaves
the flow of finding 2 in place, so nodeconf still trusts the announcement over `settings.xml`
and the "refuse loudly on mismatch" guard from its own plan never gets built; and it adds an
operator step (`cuems-config-node render`) after every identity change.

**B — `cuems-nodeconf` owns the record end to end.** At every start, before discovery: read
`uuid`/`mac` from `settings.xml` (it already constructs a `ConfigManager`), render the role
template with them into the live file, reload avahi, then discover — so "announced ==
`settings.xml`" holds by construction and the self-row can be seeded from `settings.xml`
(closing its planning item 09 at the same time). Templates go back to pure package content
with a placeholder; `cuems-config-node` loses its Avahi duties.
*For*: one writer (F1 at document granularity), the D14 direction enforced at every boot and
self-healing after any `cuems-common` upgrade or `--force-new-identity` (restart nodeconf, no
operator step), no host state in `/usr/share`, and it is the remit nodeconf's own plan and
CLAUDE.md already assign it.
*Against*: opens a third repository in feature 011 (~30 lines in `CuemsNodeConf.py` plus
tests, and a template placeholder in `cuems-common`); on the nodeconf-less majority the live
record stays hand-managed until nodeconf is re-enabled — which is **exactly today's state**,
and `cuems-init-node --check` still detects the drift; and the transition needs mutual
`Breaks` so an old nodeconf never copies a placeholder template verbatim (the two packages
already use that pattern for the `node_role` cutover).

**D — one rendering helper in `cuems-common`, invoked by whoever decides the role.**
`cuems-common` ships `cuems-avahi-service <role>` (root; a sudoers rule for `cuems` replaces
the three dead `cp` rules): it renders the template with the uuid from `settings.xml` into the
live file and reloads avahi only on change; refuses on sentinel/absent (`NOT PROVISIONED`,
exit 3). `cuems-nodeconf` replaces its `copy2` with a call to it (one line per site, or an
import — it is root). `cuems-config-node` drops its template rewrite and Avahi duties (keeps
hostname/`/etc/hosts`/`avahi-daemon.conf` until nodeconf's identity chain lands).
`cuems-common`'s `postinst` calls the helper with the *current* role when a live record exists
and `settings.xml` is provisioned, which repairs every already-deployed host on upgrade.
Templates carry the sentinel and are never rewritten by anyone.
*For*: everything B gives (one writer of the live file — the helper; D14 direction enforced
at every write; no host state in `/usr/share`; self-healing on upgrade through `postinst`),
**plus** it works on nodeconf-less hosts (operators and provisioning call the helper directly),
and the nodeconf change is a swap of one call rather than new logic, so it can land in
nodeconf's own tree as part of the same coordinated merge (D27 already includes nodeconf in
`xml-refactor-merge-candidate` from feature 010).
*Against*: still opens `cuems-nodeconf`, minimally; the "refuse on mismatch" guard from
nodeconf's plan 09 is not built here (it becomes unnecessary once nodeconf renders through the
helper, but a nodeconf that is *not yet swapped* keeps trusting the announcement — the mutual
`Breaks` covers the transition).

### Comparison against the identity invariant (design §5)

| Practice | A (config-node renders) | B (nodeconf owns) | D (helper, nodeconf calls it) |
|---|---|---|---|
| 1 one source, one minter | source enforced only at render time; nodeconf still trusts Avahi | enforced at every nodeconf start | enforced at every write |
| 2 self-entry vs topology | unchanged | self-entry seeded from `settings.xml` (plan 09) | unchanged unless nodeconf also seeds |
| 6 TXT derives from `settings.xml` | yes, via templates in `/usr/share` (reset on upgrade, re-rendered by postinst) | yes, live file only | yes, live file only |
| 7 sentinel never announced | render refuses; but an old nodeconf copies the sentinel template verbatim until postinst re-renders | helper/nodeconf refuse | helper refuses; postinst repairs deployed hosts |
| 8 verifier | `--check` | `--check` | `--check` |
| F1 one writer of `cuems.service` | **two** (nodeconf copies, config-node renders) | one | one (the helper) |
| works with nodeconf masked | yes | no (hand-managed, as today) | yes |
| repositories opened by 011 | 2 | 3 | 3 (one-line swap) |
| operator step after `--force-new-identity` | run `render` | restart nodeconf | run the helper, or restart nodeconf |

### Recommendation (superseded — B was taken, see R7)

**D** was the recommendation under the fleet as measured on 2026-09-25 (nodeconf masked on most hosts). It is the only shape that satisfies F1 for the live record, keeps identity out of
package-owned files, and still works on the fleet as it is (nodeconf masked). The name
argument the maintainer raises is right in substance — the *decision* of which role to
announce is nodeconf's, and under D it stays so — but the *mechanism* of rendering a record from
`settings.xml` is a `cuems-common` concern because `cuems-common` owns the templates, the
avahi-daemon configuration, and the hosts where nodeconf does not run. B is the end state
nodeconf's own planning points at (self-row seeding plus the run-time guard), and D does not
foreclose it: once nodeconf renders through the helper at every start, B's guarantees follow
without a second mechanism.

**If D is taken**, the changes to the plan are: contract `cuems-common-handover.md` §4 is
rewritten around the helper (the `render` subcommand goes; `cuems-config-node` only *loses*
duties); `cuems-common`'s `postinst` calls the helper instead of `cuems-config-node render`;
the three `cp` sudoers rules are replaced by one rule for the helper and
`test_template_consumers.py` re-based; and a **`cuems-nodeconf`** change joins the coordinated
merge — the `copy2` sites call the helper, `Breaks: cuems-common (<< 1.3.0-23~)` already
exists in its `control`, and `cuems-common`'s reverse `Breaks: cuems-nodeconf (<< 0.1.0-8)` already covers it.
`cuems-init-node`'s post-change message names the helper. Spec FR-040a's wording ("`cuems-config-node`
reads the node uuid from `settings.xml` and never mints") stays true; its "refuse to write an
Avahi record carrying the sentinel" moves to the helper.

## R8 — `postinst`'s invocation mode and its fallback (FR-015 – FR-018, A6)

**Decision**: `cuems-init-node --no-overlay --install-missing`:

- `settings.xml` absent ⇒ mint (through `Uuid()`), write all three (any present sibling is
  left untouched — a present `network_map.xml` stub gets its self-entry seeded by plain insert,
  which is a *modification*, so in this mode a present sibling is **not** touched and `--check`
  reports it; the migration guide sends the operator to a plain run).
- `settings.xml` present and readable ⇒ identity taken from it; only absent siblings written.
- `settings.xml` present but unreadable ⇒ exit 2 with the path and reason; nothing written.

`postinst`:

```sh
INIT=/usr/lib/cuems/bin/cuems-init-node
if ! timeout 60s "$INIT" --no-overlay --install-missing; then
    echo "WARNING: cuems-init-node failed or timed out; installing pristine placeholders." >&2
    for f in settings.xml network_map.xml default_mappings.xml; do
        [ -e "/etc/cuems/$f" ] || cp /usr/share/cuems/defaults/"$f" "/etc/cuems/$f"
    done
    echo "WARNING: this node is NOT PROVISIONED (sentinel identity). Run: cuems-init-node" >&2
fi
```

`timeout` (coreutils, present on every target) is the one addition the design did not name: a
hang in `postinst` would block the stack exactly as a non-zero exit does. 60 s is 15× the
measured tool budget (R10). The whole block runs after `#DEBHELPER#` (FR-019) and the script
ends with `exit 0` unconditionally.

## R9 — Lifecycle tests without root or a container runtime

**Measured**: no `podman`, `docker` or `systemd-nspawn` on the build host; `mmdebstrap 1.3.5`
is present, the user has sub-uid/sub-gid ranges, and `unshare --map-auto --map-root-user`
works. `mmdebstrap --mode=unshare --variant=apt --include=python3 bookworm` built a 200 MB
tarball in 38 s; entering it with `unshare --map-auto --map-root-user chroot` gives uid 0,
`dpkg 1.21.23`, `python3 3.11.2` — bookworm's exact versions.

**Decision**: two tiers.

- **Script-level tests, always run** (`tests/packaging/`): the maintainer scripts are executed
  with `CUEMS_ETC`/`CUEMS_SHARE`/`CUEMS_STATE` overrides pointing into `tmp_path` and a stub
  `cuems-init-node` on `PATH`, covering every branch of FR-015–FR-018, FR-037, FR-038 and the
  fallback. The scripts read those variables with `/etc/cuems` etc. as defaults, the pattern
  `cuems-common`'s `tests/packaging/stubs/` established.
- **Chroot lifecycle tests, marked `slow`** (`tests/packaging/test_lifecycle_chroot.py`): build
  the `.deb`, install into a fresh copy of the tarball (`CUEMS_CHROOT_TAR` env var; skipped when
  unset), and run SC-001–SC-003, SC-006–SC-010 and the R3 upgrade orders with real `dpkg`. The
  tarball is built once by `quickstart.md`'s command and cached; CI builds it in a preparatory
  job. `ConfigManager(load_all=True)` runs *inside* the chroot through the installed venv
  (`/usr/lib/cuems/bin/python`), which is also what proves R1's interpreter path.

## R10 — Performance budgets, measured and re-based (FR-PERF-001, SC-PERF-001)

Measured on the build host (Python 3.11.9, warm disk cache, three runs each):

| Operation | Measured |
|---|---|
| bare interpreter start | 0.023 s |
| `import cuemsutils.tools.ConfigManager` | 0.40 – 0.50 s |
| import + `generate_settings_example()` + `save()` | 0.71 – 1.00 s |
| `ConfigManager(load_all=True)` on the engine corpus, cold process | 1.17 s |

A `cuems-init-node` write run is import + three loads + three generations + three writes ≈
the third and fourth rows combined, so **≈ 1.5 – 2.0 s cold on the build host**. The reference
node hardware (N97-class) is slower by a factor the audit has never measured; a 2× allowance is
the conservative choice. The spec proposed ≤ 2 s and allowed the plan to re-base with a reason.

**Budgets (re-based)**:

| Budget | Value | Validation |
|---|---|---|
| `cuems-init-node` write mode, cold | **≤ 4 s** | chroot test times the invocation; recorded in `baseline.md` for build host and, when reachable, one node |
| `cuems-init-node --check`, cold | **≤ 3 s** | same |
| `postinst`, fresh install, excluding dh-virtualenv's autoscript | **≤ 10 s** (hard cap: the 60 s `timeout`) | chroot test times `dpkg -i` minus a baseline `dpkg -i` of a package with an empty postinst |
| `postinst`, upgrade with all three present | **≤ 2 s** | same |
| library suite per-test figure | **≤ 110 %** of the figure measured at plan start (`baseline.md`) | `hatch run test.py3.11:run` |
| package size delta | **≤ 100 KB** (six schemas 42 KB + three documents + TOML) | `dpkg-deb -I` |

The generator's own cost at build time is unbudgeted (build, not runtime) but recorded.

## R11 — Recording the entry point in the public API golden (FR-023)

**Decision**: `tests/support/public_api.py` gains `PUBLIC_SCRIPTS = {"cuems-convert-documents",
"cuems-init-node"}` and `_snapshot()` gains a `"scripts"` key listing the installed
distribution's `console_scripts` entry points (`importlib.metadata.entry_points`). The golden
`tests/golden/api/public_api.json` moves **once**, adding that key — a recorded, argued change
(FR-021 stands: the golden is not regenerated to make a test pass; it is extended to cover a new
surface). `cuemsutils.tools.init_node` exposes `main` and nothing else public.

## R12 — `default_mappings.xml`: settling id-vs-name by consumption (spec Q1a, FR-012)

**Measured, by consumption** (who reads the six `default_*` fields):

- `cuems-frontend/src/app/components/projects/project-edit/sequence/sequence.component.ts:385,455,697-698`
  (measured 2026-09-25; the design document's `:379,449,682` had drifted) reads
  `default_audio_output` and `default_video_output` and uses them as the cue's `output_name`
  default, whose values are `<uuid>_<output_id>` (design §10.1; corpus scripts:
  `0367f391-…-000000000001_2`).
- `cuems-frontend/src/app/services/projects/projects.service.ts:560` (design said `:553`)
  parses the compound with `^(<uuid>)_(.+)$` — the tail is whatever follows the underscore,
  opaque to the parser.
- The engine reads `default_*` through `ConfigManager` only to expose them; it resolves outputs
  by **id** in `node_hw_outputs` (`ConfigManager.py:159,283,368-399`).

**Decision**: the compound's tail is the output **id** (`<uuid>_<id>`, host `.2`'s spelling);
host `.3`'s `…_DP-1 Left` is the wrong one — an output *name*, which the schema declares as a
free `NonEmptyString` and nothing resolves by. For a fresh, unconfigured node the seven root
scalars are: `number_of_nodes = 1`; every `default_*` **empty** (the corpus shows
`<default_video_input/>` empty and schema-valid; a fresh node has no discovered hardware to
point at, and inventing `…_0` would assert an output that may not exist — the disconnected
`DP-2` case from the audit); the node entry carries the sentinel uuid/mac and **empty**
`audio`/`video`/`dmx` sections. The plan's `data-model.md` records the table; the engine's
behaviour on an empty default is checked by `tests/integration/test_default_mappings_fresh.py`
(loads clean; `get_*_output_id('default')` returns the empty string rather than raising).

The tool substitutes the sentinel token in every string leaf (so a future non-empty compound
default specializes correctly, FR-026) and asserts the serialized bytes contain no sentinel.

## R13 — F1 annotation form (FR-047)

**Decision**: on each schema's root `xs:element`, one `xs:annotation` carrying
`<xs:appinfo><cms:writer scope="…">…</cms:writer>…</xs:appinfo>` — one `writer` element per
writer, `scope` naming the seam (`document`, `self-entry`, `topology`, `inventory`, `geometry`,
`default_mappings.xml`), plus a one-sentence `xs:documentation`. `xmlschema` exposes it as
`schema.elements[name].annotation.appinfo`, so `test_duplication_flags` can assert every schema
declares at least one writer and every writer is a known process name. Six hashes move in
`test_schema_scope.CURRENT_SCHEMA_HASHES` in the same commit, with the reason in the message.
No `doc_version` moves: annotations do not change any instance document's validity.

## R14 — `--check`'s four locations and precedence (FR-032)

Source: `settings.xml` `Settings/node/uuid`. Mirrors: `network_map.xml` (`node_list/node[uuid]`
present), `default_mappings.xml` (`nodes/node[uuid]` present **and** no sentinel token anywhere
in the file), `/etc/avahi/services/cuems.service` (every `<txt-record>uuid=…</txt-record>`;
the two service blocks must also agree with each other). Exit classes 0/1/2/3 with precedence
3 > 2 > 1 (spec A4). Output is one line per location, path first, in the
`cuems-convert-documents` style (`<path>: <verdict> (<detail>)`), and a final line naming the
fixing command.

## R15 — CLI logging (FR-UX-001)

**Measured**: the library's logger writes DEBUG/INFO lines to **stdout** by default
(`log.py:118`, seen during the timing runs), which would pollute a CLI's report. **Decision**:
`cuems-init-node` sets the library log level to `WARNING` unless `CUEMS_LOG_LEVEL` is set in
the environment or `--verbose` is given; its own report goes to stdout, warnings and errors to
stderr, exit codes as contracted. `cuems-convert-documents` already prints its report itself;
the same split applies.

## R16 — OPEN-3: `postinst` before the first engine start (spec Q4, FR-022)

**Measured**: `cuems-common` `Depends: cuems-utils (>= 0.1.0rc16)`, so dpkg configures
`cuems-utils` first; `cuems-common`'s `postinst` carries no `#DEBHELPER#` token (pinned by its
`tests/test_postinst_ordering.py`), so no engine is started at configure time; engines start
from `cuems-node.target`/`cuems-controller.target` on the next boot. **Decision**: pin the
premise from this side too — `tests/packaging/test_ordering_premise.py` asserts (a) this
package's `postinst` invokes the tool after `#DEBHELPER#` and before `exit 0`, and (b) when the
sibling checkout is present, `../cuems-common/debian/control` still depends on `cuems-utils`
and its `postinst` still lacks the token (skipped when the sibling is absent, the
`test_schema_mirror` convention).

## R17 — Packaging hygiene specifics (FR-042)

- `debian/compat` deleted; `Build-Depends: debhelper-compat (= 13)` (the siblings' value;
  `debhelper 13.11.4` on bookworm).
- `Standards-Version: 4.6.2` (bookworm's `debian-policy`; the siblings sit at 4.6.0).
- The `dh_python2` provenance string was produced by an older dh-virtualenv autoscript; the
  installed 1.2.2 autoscript says "dh-virtualenv postinst autoscript" (measured). A test greps
  the *built* `DEBIAN/postinst` for `dh_python2` and fails if present.
- `debian/README.Debian` is rewritten to point at `README.source` and the first-install notes
  rather than the 2025 stub.

## R18 — Suite baseline at plan start

Recorded in `baseline.md` once `hatch run test.py3.11:run` completes on this host (the
execution document's figure — 2719 passed, 100 skipped, 2 xfailed — was measured on another
machine and is not comparable for wall time). The per-test figure from this host is the
reference SC-PERF-001's suite budget uses.

## R19 — Versions and the merge candidate: nothing bumps

**Measured 2026-09-28**: every package this feature touches has an **unreleased** changelog
head that absorbs its change, and the relations between them already name those versions:

| Package | Head | This feature's share | Relation already in place |
|---|---|---|---|
| `cuems-utils` | `0.1.0rc16 UNRELEASED` (NOT YET BUILT) | ships schemas/defaults/tool; entry amended | gains `Breaks: cuems-common (<< 1.3.0-23~)` — the one relation this feature adds |
| `cuems-common` | `1.3.0-23 UNRELEASED` | custody transfer, config-node stripped, sentinel templates; entry amended | `Depends: cuems-utils (>= 0.1.0rc16)`, `Breaks: cuems-nodeconf (<< 0.1.0-8)` |
| `cuems-nodeconf` | `0.1.0-8 UNRELEASED` | render at start/role change, guard; entry amended | `Breaks: cuems-common (<< 1.3.0-23~)` |

**Decision**: no version moves — not `rc17`, not `1.3.0-24`, not `0.1.0-9` (an earlier draft
of R7/§4a said `0.1.0-9`; corrected). The library version stays `0.1.0rc16` for the reasons
design §12 records (`0.1.1` is reserved and refused by three consumers; `rc17` would say
nothing true). The coordinated state is what the `xml-refactor-merge-candidate` tag marks:
today it exists in `cuems-common`, `cuems-nodeconf` and `cuems-power-bridge` (not yet in this
repository); after 011–014 it is **re-pointed** at the final commit in each repository and
created here. Nothing ships between now and then (D27).

**Two candidate tags are re-cut by this feature, and both re-cuts must be announced** (the shared
convention nodeconf's brief §4 states: the tag moves only for packaged-content changes, and a re-cut
is announced to the other flows). `cuems-common`'s `3af31cc` and `cuems-nodeconf`'s `6c0cca7` both sit
at the head of their unreleased entries and both gain packaged content here (`debian/install`,
maintainer scripts, templates, `cuems-config-node`; `CuemsNodeConf.py`). Neither moves a version.
**Caveat, the T090 shape**: inside `0.1.0-8` the version cannot distinguish a nodeconf build made
before the render from one made after, so the mutual `Breaks` protect the transition only across the
version boundary, not within it — the rule is operational (rebuild both from the tagged commits), and
it costs nothing because D27 forbids shipping any intermediate build.

**Guard**: `tests/packaging/test_no_version_bump.py` asserts this repository's changelog head
is `0.1.0rc16` and, when the sibling checkouts are present, that `cuems-common`'s is
`1.3.0-23` and `cuems-nodeconf`'s is `0.1.0-8` — a bump is a deliberate act that updates the
test in the same commit, with the reason in the message.

## R20 — Revalidation against upstream `feat/xml-refactor` `5a1f7c9..0ba239b` (2026-09-28)

Four commits landed on the integration branch while this feature was being specified; the 011 branch
was rebased onto them cleanly (no file overlap) and the two upstream tests pass on the rebased tree.
What they change for this plan, item by item:

| Upstream change | Effect on 011 |
|---|---|
| `tests/contract/test_node_aliasing.py` + docstrings: `NodeIndex.adopt`/`merge` and `CuemsNetworkMapType.refresh` mutate **by reference**, as a contract (T091/T092) | Constrains R7 item 7 and FR-029: the new `NodeIndex.ensure` inserts the caller's dict, never a copy; `cuems-init-node`'s self-entry seeding goes through it and the aliasing test gains an `ensure` case |
| `specs/010-consumer-migration/nodeconf-map-write-divergence.md` §5: the start-up window (C2) and the engine's socket-existence probe | Fixes the **order** of B's render: before `set_comms()`, so an unprovisioned refusal never creates the socket the engine trusts (R7 item 2) |
| `tasks.md` T094 → `../cuems-nodeconf/specs/planning/10-readiness-window.md`, feature `003-startup-readiness` | B's nodeconf half is **delivered by feature 003**, not by a task of this feature; this plan carries it as a gate reference (the 010 convention), and both changes share **one** re-cut of `6c0cca7` |
| `tasks.md` "Consumer flow status": `cuems-common` landed at `3af31cc`, nodeconf at `6c0cca7`; 011–014 recorded as hard successor | Confirms A3/R19 and adds the two re-cuts above; the handover's `cuems-common` half re-cuts `3af31cc` |
| `etc-cuems-first-install-execution.md` §4.6 extended: the suite figure is a **range** (2717–2719 / 100–101) because `test_descriptor_laziness` breathes | `baseline.md` quotes ranges, and SC-PERF-001's suite budget compares per-test figures over the collected population, not a single passed count |
| `nodeconf` brief §7 criterion 7 and its `specs/002-…/checklists/hardware-verification.md` ledger (four entries, all "Not performed") | Step 6a's unmask/enable/start task belongs **in that ledger** rather than a second list — one place for every hardware-only check on a node; this plan's quickstart list stays as the operator's steps and points there |
| `release-gate.md` re-measured: `cuems-power-bridge`'s `debian/control` floor unbounded | Unrelated to 011's relations; noted so the no-bump guard is not mistaken for that gate |

**Decisions — taken by the maintainer 2026-09-28**, all three as recommended, recorded in
`../cuems-nodeconf/specs/planning/10-readiness-window.md` §9.4 (pushed to that repository's
`feat/xml-refactor` so they are stated before its feature 003 starts):

- D-R20-1 — B's nodeconf work **folds into `003-startup-readiness`**: one start-up sequence, one
  re-cut of `6c0cca7`, one hardware verification.
- D-R20-2 — **`NodeIndex.ensure` is added here**, inside `0.1.0rc16`, and consumed by both
  `cuems-init-node` and nodeconf; no daemon-side insert.
- D-R20-3 — the unmask/enable/start hardware task is **entry §5 of nodeconf's hardware-verification
  ledger**; this plan's step 6a points at it and keeps no second list.

## R21 — Analysis remediations (2026-09-28, `/speckit.analyze`)

Seventeen findings, none constitutional; the four HIGH ones and their resolutions:

- **`set -e` after `#DEBHELPER#`** (U1): dh-virtualenv's autoscript starts with `set -e`, so the
  custom block must begin with `set +e` and the script test must simulate the injected stanza.
  Contract packaging.md step 0; T020, T039.
- **Map-row `name`/`ip` at install time** (U2, maintainer): `name` = OS hostname; `ip` = the chosen
  interface's IPv4 else `0.0.0.0`; nodeconf's `merge` refreshes both. FR-025a.
- **No determinable MAC** (U3): refuse (exit 1) instead of a sentinel MAC — `NodeIndex` is keyed
  by MAC. Authoritative link `ethernet0` (the udev name `cuems-common` enforces), then the first
  physical interface. FR-025a; `postinst` falls through to placeholders.
- **FR-004** said `Breaks` and `Replaces`; R3 omits `Replaces` with a reason. Spec corrected.

The rest: FR-017/FR-025 reworded for `--install-missing` (I2); T028 no longer depends on US3's
tool block (I3); the sibling `.deb`s the chroot tests need are built from the sibling checkouts or
skipped (U4); the hardware steps live in nodeconf's ledger, this repository carries the pointer
(I4); FR-030/FR-039/FR-044/SC-005 gain explicit assertions (C1–C4); `NOT PROVISIONED` is one
spelling (A1); FR-046 says M1–M9 (I5); SC-PERF-001 names the binding re-based figures (I6);
FR-002/FR-020 and FR-013/FR-034 de-duplicated (D1, D2); `CUEMS_INIT_TIMEOUT` is in the contract (U5).
