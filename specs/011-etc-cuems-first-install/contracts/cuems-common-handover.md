<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — the `cuems-common` handover (`1.3.0-23`)

What `cuems-common`'s working branch must carry for feature 011 to be true across the pair.
Both land under the coordinated `xml-refactor-merge-candidate` merge (spec A3); neither ships
alone.

## 1. Paths relinquished (research R3)

| Path | Before | After |
|---|---|---|
| `/etc/cuems/network_map.xsd` | `cuems-common` conffile (stale mirror) | `cuems-utils` `postinst` installs the current schema, always |
| `/etc/cuems/network_map.xml` | `cuems-common` conffile (empty stub) | created by `cuems-utils` `postinst` if absent; written by `cuems-nodeconf` (topology) and `cuems-init-node` (self-entry) |

Mechanics: `preinst` snapshots the live map to `/var/backups/cuems-common.network_map.xml.presave`;
`rm_conffile` for both paths in `preinst`/`postinst`/`postrm` with prior-version `1.3.0-23~`;
`postinst` restores the map from the snapshot if absent, removes only a `.dpkg-bak` identical
to the snapshot, and reinstalls the `.xsd` from `/usr/share/cuems/schemas/` if absent.
`debian/install` drops the two lines; `etc/cuems/network_map.xsd` is deleted from the
repository; `etc/cuems/network_map.xml` remains only as the `/usr/share/doc` example.

Measured outcome required (lifecycle test, both unpack orders and `apt install ./a ./b`):
live map byte-identical; zero `network_map.*.dpkg-*` siblings; a later `purge cuems-common`
leaves the map in place; `/etc/cuems/network_map.xsd` equals the installed library's schema.

## 2. Package relations and versions

`Depends: cuems-utils (>= 0.1.0rc16), cuems-utils (<< 0.1.1~)` — unchanged, already correct.
`Breaks: cuems-nodeconf (<< 0.1.0-8)` — unchanged, already covers the render transition.
**No version bumps anywhere** (research R19): `cuems-common` stays at its unreleased
`1.3.0-23`, `cuems-nodeconf` at `0.1.0-8`, `cuems-utils` at `0.1.0rc16`; the three land
together under the re-pointed `xml-refactor-merge-candidate` tag.
The `control` description's paragraph about the "mirrored network_map.xsd" is rewritten: the
floor's reason is now "the release that ships the schemas to `/etc/cuems`".

## 3. Tests re-based or retired

| Test | Action |
|---|---|
| `tests/test_schema_mirror.py` | **retired** |
| `tests/test_shipped_network_map.py` | retired (nothing shipped); its "no topology can be installed by the package" intent moves to a test that `debian/install` names no `etc/cuems/network_map.xml` |
| `tests/test_network_map_example.py` | re-based: validates the example against `../cuems-utils/src/cuemsutils/xml/schemas/network_map.xsd` when the sibling exists (skip otherwise) |
| `tests/test_documented_validation.py` | re-based the same way; the documented command keeps `/etc/cuems/network_map.xsd` as its argument, which now exists on every host |
| `tests/test_network_map_conversion.py` | unchanged in substance; fixture schema path re-based |
| `tests/test_avahi_vocabulary.py` | extended: every template's `uuid=` record is the sentinel |
| `tests/test_template_consumers.py` | re-based: no `cp` rule expected; `cuems-config-node` names no template |
| new `tests/test_config_node_no_minting.py` | `cuems-config-node` contains no `uuid1`/`uuid4` call and names no template; the sudoers file has no `cp` rule |

## 4. `cuems-config-node`, the templates, and the sudoers rules (research R7, FR-040a)

- `cuems-config-node` **loses** `uuid1()` minting and every Avahi/template duty: it no longer
  rewrites `usr/share/cuems/cuems.service.*` nor any live record. `write` keeps its hostname,
  `/etc/hosts` and `avahi-daemon.conf` handling and prints that identity comes from
  `/etc/cuems/settings.xml` (written by `cuems-init-node`) and is announced by `cuems-nodeconf`.
- The three shipped templates carry the **sentinel** uuid and are never rewritten by any tool.
- `etc/sudoers.d/99-cuems-avahi`: the three `cp` rules are retired (dead privilege — nodeconf
  runs as root and copies directly; nothing else in production copies a template); the
  `systemctl reload avahi-daemon.service` rule stays.
- `debian/postinst` makes **no** new Avahi call; the existing live-file key migration stays.
- `debian/control`: **unchanged** — the existing `Breaks: cuems-nodeconf (<< 0.1.0-8)` already
  covers the transition, matching nodeconf's `Breaks: cuems-common (<< 1.3.0-23~)`.

## 4a. `cuems-nodeconf` — delivered by its feature `003-startup-readiness` (inside the unreleased `0.1.0-8` entry, no bump; one re-cut of `6c0cca7`, announced)

- At start, **before `set_comms()`** (so an unprovisioned refusal never creates `/tmp/nodeconf.ipc`,
  the socket `cuems-engine`'s readiness probe trusts) and before discovery: uuid/MAC from
  `settings.xml` via its `ConfigManager`; render
  the role template into `/etc/avahi/services/cuems.service` by literal substitution of the
  sentinel token; atomic write; `avahi-daemon` reloaded only if the bytes changed. Absent or
  sentinel `settings.xml` ⇒ log `NOT PROVISIONED`, exit non-zero, announce nothing.
- The three template-copy sites (`_install_master_service_template`, the node branch of
  `set_node_role`, the resume path) render the same way.
- After discovery: the discovered self must carry the `settings.xml` uuid; otherwise refuse
  loudly (plan 09 §4).
- Self-entry seeded through the library's `NodeIndex.ensure` (by reference), never a daemon-side
  insert (D22; nodeconf plan 09 §5).
- Tests: render from a settings fixture (real uuid, sentinel, absent), reload-only-on-change,
  the guard, the ordering before `set_comms()`, and that the templates are read from
  `/usr/share/cuems` unchanged. Hardware verification recorded in that repository's ledger.

## 5. `docs/node-identity-contract.md` — the D14 section to add

Under "Discovery TXT record", a new subsection **"Where the `uuid=` value comes from"** stating:

- the source is `/etc/cuems/settings.xml`, whose sole writer is `cuems-init-node`; the only
  minter in the ecosystem is `cuemsutils.tools.Uuid`;
- **`cuems-nodeconf` is the record's sole writer** and derives it from that file at every start
  and every role change; nothing else may set the value and nothing may hand-enter it;
- the retired second minter (`cuems-config-node`'s former `uuid1()`) and the retired hardcoded
  production uuid in the shipped templates, with the version that retired each;
- `cuems-init-node --check` is the verifier and the only detector of a drifted record;
- the sentinel is never announced: an unprovisioned node's nodeconf refuses to start;
- the shipped templates carry the sentinel and are package content — a host's identity never
  lives under `/usr/share`.

Also: the "Role-flip" procedure gains the step "restart `cuems-nodeconf` after any identity
change" (which is also feature 012's last step), the transition note records the mutual
`Breaks` and that unmasking nodeconf fleet-wide is part of the same landing, and the OPEN-4 ownership note (who writes which `/etc/cuems` file) lands here
as a table matching `data-model.md` §5.
