<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Migration guide — feature 011, `/etc/cuems` first install

**Audience**: operators of existing hosts, and the maintainers of `cuems-common` and
`cuems-nodeconf`. Written as the stories land (FR-045); each section is filled by the task that
delivers it and says so.

## 1. Upgraded hosts — what changes and what to run (US1, US3)

**Schemas (US1, T025).** After the upgrade, `/etc/cuems` holds all six `.xsd` files
(`settings`, `network_map`, `project_mappings`, `project_settings`, `script`, `hardware_outputs`),
each byte-identical to the installed library's bundled copy, mode 0644, owned by `cuems-utils`'s
`postinst` and **replaced on every install and upgrade** of that package. They are not conffiles,
so there is no prompt and no `.dpkg-dist`. A stale `network_map.xsd` — every audited production
host carried one, and one host carried a `network_map.xsd.dpkg-dist` beside it — is replaced
outright; a `.dpkg-dist`/`.dpkg-old` sibling that predates this feature is left alone (it is the
operator's) and can be deleted by hand. The pristine copies live in `/usr/share/cuems/schemas/` and
`dpkg -V cuems-utils` verifies them; `diff /usr/share/cuems/schemas/X.xsd /etc/cuems/X.xsd` should
print nothing.

**What closes.** `cuems-display-setup`'s validation against `/etc/cuems/project_mappings.xsd`,
`docs/latency-tuning.md`'s `/etc/cuems/settings.xsd`, and the editor's hardcoded
`/etc/cuems/script.xsd` all resolve to real files now.

**The `cuems-common` custody transfer.** `cuems-common 1.3.0-23` stops shipping
`/etc/cuems/network_map.{xml,xsd}` as conffiles. On its upgrade, a live `network_map.xml` is
snapshotted by `preinst`, the conffile record is dropped, and `postinst` puts the snapshot back
before its conversion loop runs — the file is byte-identical afterwards, no `.dpkg-bak` is left
behind unless one predates the upgrade, and a later `purge cuems-common` no longer touches the map.
`cuems-utils` declares `Breaks: cuems-common (<< 1.3.0-23~)` so apt upgrades the pair together;
`Replaces` is deliberately absent (nothing under `/etc` is in the manifest).

*The identity half (US3) is filled by T050.*

## 2. The pristine copies and the install-if-absent rule (US2)

*Filled by T034.*

## 3. Purge destroys identity; remove does not (US5)

*Filled by T060.*

## 4. Disk imaging after install (US3)

*Filled by T050.*

## 5. `cuems-init-node --check` — the four locations and the four exit codes (US6)

*Filled by T064.*

## 6. Site overlays and operator edits (US4)

*Filled by T056.*

## 7. The `cuems-common` handover — order, versions, announced re-cuts

| Package | Version | Change |
|---|---|---|
| `cuems-utils` | `0.1.0rc16` (first build) | ships the schemas and defaults; `Breaks: cuems-common (<< 1.3.0-23~)` |
| `cuems-common` | `1.3.0-23` (unreleased entry amended) | drops the two paths; custody transfer in `preinst`/`postinst`/`postrm`; `Depends: cuems-utils (>= 0.1.0rc16)` unchanged |
| `cuems-nodeconf` | `0.1.0-8` (unreleased entry amended, by its feature 003) | renders the Avahi record from `settings.xml` |

No version moves anywhere (research R19). Either install order works: `Breaks` and `Depends`
make apt take the pair together, and the transfer recipe is verified in both unpack orders. The
coordinated state is the re-pointed `xml-refactor-merge-candidate` tag; `cuems-common`'s
(`3af31cc`) and `cuems-nodeconf`'s (`6c0cca7`) candidates are re-cut by this feature and the
re-cuts announced (T080). Nothing ships from any of the three alone.

## 8. Hardware verification — the pointer

The one record of the manual per-node verification is entry §5 of `cuems-nodeconf`'s
hardware-verification ledger (`specs/002-public-network-map-path/checklists/hardware-verification.md`
in that repository; decision D3, 2026-09-28). Acceptance, per node class: unmask, enable and start
`cuems-nodeconf`; `cuems-init-node --check` exits **0** after the unmask and again after a reboot;
a second node lists this one exactly once with the `settings.xml` uuid.
