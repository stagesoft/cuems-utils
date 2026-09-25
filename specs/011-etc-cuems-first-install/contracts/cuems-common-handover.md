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

## 2. Package relations

`Depends: cuems-utils (>= 0.1.0rc16), cuems-utils (<< 0.1.1~)` — unchanged, already correct.
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
| new `tests/test_config_node_render.py` | `render` reads the uuid from a settings fixture, rewrites templates and a live file, refuses on sentinel/absent with exit 3, reloads only on change |

## 4. `cuems-config-node` (research R7, FR-040a)

- Gains `render`: uuid from `/etc/cuems/settings.xml` (`.//node/uuid`) into the three templates
  and, if present, the live `/etc/avahi/services/cuems.service`; `avahi-daemon` reloaded only
  when the live file changed. Exit 0 rendered / 0 nothing changed / 3 not provisioned (sentinel
  or absent `settings.xml`) / 2 unreadable. Never writes the sentinel to a live record.
- `write` no longer calls `uuid1()`; it uses `render` for the uuid and keeps its hostname, MAC
  and `avahi-daemon.conf` duties unchanged.
- The three shipped templates carry the sentinel uuid.
- `debian/postinst` calls `/usr/bin/cuems-config-node render || true` after the Avahi migration
  block (never fails the upgrade; on an unprovisioned node it prints "not provisioned" and
  continues).

## 5. `docs/node-identity-contract.md` — the D14 section to add

Under "Discovery TXT record", a new subsection **"Where the `uuid=` value comes from"** stating:

- the source is `/etc/cuems/settings.xml`, whose sole writer is `cuems-init-node`; the only
  minter in the ecosystem is `cuemsutils.tools.Uuid`;
- `cuems-config-node render` derives the record from it; nothing else may set the value and
  nothing may hand-enter it;
- the retired second minter (`cuems-config-node`'s former `uuid1()`) and the retired hardcoded
  production uuid in the shipped templates, with the version that retired each;
- `cuems-init-node --check` is the verifier and the only detector of a drifted record;
- the sentinel is never announced: an unprovisioned node has no `uuid=` record until provisioned.

Also: the "Role-flip" procedure gains the step "run `cuems-config-node render` after any
identity change", and the OPEN-4 ownership note (who writes which `/etc/cuems` file) lands here
as a table matching `data-model.md` §5.
