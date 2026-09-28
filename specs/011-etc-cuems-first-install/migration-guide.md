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

**Identity (US3, T050).** A host upgraded from any earlier state falls into one of three cases:

| `/etc/cuems/settings.xml` before | What the upgrade does | What you run |
|---|---|---|
| absent | `postinst` runs `cuems-init-node --no-overlay --install-missing`: mints one uuid4, writes the three documents | nothing; `cuems-init-node --check` → 0 once nodeconf runs |
| present, real uuid, `network_map.xml` is the old empty stub | **nothing is modified**; the stub is "present". The node is exactly as unbootable as before, no worse | `cuems-init-node` once — it seeds this node's row by plain insert and leaves every other row and its adoption flags alone; then `--check` |
| present, sentinel uuid (a hand-copied pristine file) | nothing is modified | `cuems-init-node` — it mints and specialises all three |

`postinst` never modifies an existing file. If the tool fails or times out during install (60 s
hard cap), the pristine placeholders are copied for the absent documents, the install still
succeeds, and the node is **NOT PROVISIONED** until you run `cuems-init-node`; two such nodes on
one network answer to one identity, so do not leave one that way.

## 2. The pristine copies and the install-if-absent rule (US2)

The three documents `ConfigManager` needs — `settings.xml`, `network_map.xml`,
`default_mappings.xml` — are generated at package build from the schemas and the seed values,
carry the reserved sentinel identity (`00000000-0000-0000-0000-000000000000`, MAC
`000000000000`), and ship under `/usr/share/cuems/defaults/` inside the package manifest
(`dpkg -V cuems-utils` verifies them). `system-defaults.toml` beside them is the upstream seed
values, for reading; the copy code uses is the library's package data, byte-identical.

**Install-if-absent, per file.** `postinst` copies a document to `/etc/cuems` only when nothing
is there. A present file — a real identity, a hand-placed file, a `cuems-common` stub map, or a
sentinel document — is never modified, renamed or removed by the package, on install, upgrade,
`--reinstall` or remove-then-install. To see how a live document differs from pristine:

```sh
diff /usr/share/cuems/defaults/settings.xml /etc/cuems/settings.xml
```

A node left with the pristine copies (the degraded fallback, or a hand copy) loads, but as
**NOT PROVISIONED**: `cuems-init-node --check` exits 3, and a plain `cuems-init-node` run mints a
real identity. Two such nodes on one network answer to one identity, so do not leave a node in
that state.

## 3. Purge destroys identity; remove does not (US5)

`apt remove cuems-utils` touches nothing under `/etc/cuems`: identity, documents and schemas
stay, and a later install finds them and leaves them alone. `apt purge cuems-utils` removes
**exactly** the nine paths this package placed (the three documents and the six schemas) and the
tool's write record under `/var/lib/cuems-utils`, then removes each directory only if it is empty.
It never removes recursively, so `cuems-common`'s conffiles, the cluster identity,
`power-bridge.key`, any `.dpkg-*` sibling and your `defaults.d/` overlays survive. Purge then
install mints a **new** uuid — purge destroys identity by design; a node re-installed that way
must be re-adopted.

## 4. Disk imaging after install (US3)

The sentinel protects against *package* imaging (every `.deb` carries the sentinel, never a
real uuid), not *disk* imaging: two machines cloned from one installed disk carry the same real
uuid4. Before imaging, `apt purge cuems-utils` (and reinstall on each clone), or run
`cuems-init-node --force-new-identity --yes` on every clone and restart `cuems-nodeconf` there.

## 5. `cuems-init-node --check` — the four locations and the four exit codes (US6)

`--check` reads `settings.xml` (the source), `network_map.xml`, `default_mappings.xml` and
`/etc/avahi/services/cuems.service`, prints one line per location, path first, then a verdict
and the command that fixes it. It writes nothing. `--json` gives the same as one object.

| Exit | Verdict | Meaning | Run |
|---|---|---|---|
| 0 | coherent | every location agrees with the source | — |
| 1 | mismatch | a mirror disagrees (self-entry missing; a sentinel token left in a compound string; the Avahi record differs) | `cuems-init-node`, or `systemctl restart cuems-nodeconf.service` when only the Avahi record disagrees |
| 2 | absent or unreadable | a location is missing or does not parse | `cuems-init-node`; for an absent Avahi record on a provisioned node, unmask and start `cuems-nodeconf` |
| 3 | NOT PROVISIONED | the source carries the sentinel; an absent Avahi record is expected here | `cuems-init-node` |

Precedence when several apply: 3 over 2 over 1. Examples:

```
/etc/cuems/settings.xml: source uuid=6f1d… mac=aabbccddeeff
/etc/cuems/network_map.xml: MISMATCH (self-entry missing (2 row(s), none with uuid=6f1d…))
/etc/cuems/default_mappings.xml: ok (node entry present, no sentinel token)
/etc/avahi/services/cuems.service: ok (2 records agree)
verdict: mismatch (exit 1) — run: cuems-init-node
```

## 6. Site overlays and operator edits (US4)

Drop `*.toml` files into `/etc/cuems/defaults.d/` using the same tables as
`/usr/share/cuems/defaults/system-defaults.toml` (grammar: `contracts/system-defaults-toml.md`),
then run `cuems-init-node`. Files apply in lexical order, later wins; `--verbose` names the file
behind each override. A syntax error, an unknown key, a wrong scalar type or an identity field
(`uuid`, `mac`) refuses the whole run before anything is written. `postinst` never reads the
overlay, so a broken one cannot affect an upgrade.

**Hand edits survive.** A field you changed by hand in `settings.xml` (or in this node's map row,
or in `default_mappings.xml`'s root) is kept on every plain re-run and reported as
`modified, kept`; upstream never silently wins over a venue decision. `cuems-init-node --reset`
returns every non-identity field to the system default (seed values plus your overlay), listing
what it reverts first; identity is untouched by `--reset` and changed only by
`--force-new-identity`. On a host provisioned before this feature there is no write record, so a
first re-run keeps every difference and says so.

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

**Re-cut status, 2026-09-28.** `cuems-nodeconf`'s is **done** — `6c0cca7` → **`b305c1c`**, signed
and pushed, carrying its feature `003-startup-readiness`. `cuems-common`'s is **not**: its tag is
still `3af31cc`, three packaged commits behind `e3c9430`, and those three commits *are* the
handover this section describes. Until it moves, the two candidate tags do not compose — at
`3af31cc` the `usr/share/cuems/cuems.service.controller` template still carries the production
uuid, and `cuems-nodeconf`'s renderer refuses a template with no sentinel, so a **controller**
built from the tagged pair has a `cuems-nodeconf` that exits at start-up. Both trees are correct;
only the tag is behind. `specs/011-etc-cuems-first-install/baseline.md` §"UX pass and
announcements" carries the counterpart table and the maintainer actions.

## 8. Hardware verification — the pointer

The one record of the manual per-node verification is entry §5 of `cuems-nodeconf`'s
hardware-verification ledger (`specs/002-public-network-map-path/checklists/hardware-verification.md`
in that repository; decision D3, 2026-09-28). Acceptance, per node class: unmask, enable and start
`cuems-nodeconf`; `cuems-init-node --check` exits **0** after the unmask and again after a reboot;
a second node lists this one exactly once with the `settings.xml` uuid.
