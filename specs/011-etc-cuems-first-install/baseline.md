<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Baseline — feature 011

Measurements taken at plan start (2026-09-25) on the build host: Debian 12.15, 2 × Intel Xeon
(Skylake, virtualized), Python 3.11.9 via `uvx hatch` `test.py3.11` env, tree at `8b29556`.
Rows marked *pending* are filled as the corresponding task lands.

## Tool and library timings (cold process, warm disk cache, three runs)

| Operation | Measured | Budget (research R10) |
|---|---|---|
| bare interpreter start | 0.023 s | — |
| `import cuemsutils.tools.ConfigManager` | 0.40 – 0.50 s | — |
| import + `generate_settings_example()` + `save()` | 0.71 – 1.00 s | — |
| `ConfigManager(load_all=True)`, engine corpus | 1.17 s | — |
| `cuems-init-node` write, cold | *pending* | ≤ 4 s |
| `cuems-init-node --check`, cold | *pending* | ≤ 3 s |
| `postinst`, fresh install (chroot, minus empty-postinst baseline) | *pending* | ≤ 10 s (60 s hard cap) |
| `postinst`, upgrade, triple present | *pending* | ≤ 2 s |
| package size delta | **+~50 KB** against the previous build (9,013,536 B vs 8,96x,xxx B measured from the same tree without the schemas/defaults: six schemas 42,516 B, three documents 2,814 B, TOML 4,512 B, tool script 234 B) | ≤ 100 KB |

Generator determinism: two `generate_settings_example().save()` runs → equal SHA-256. ✅

**Pre-move reference for T012** (recorded 2026-09-28 before T011 moved the values to TOML):
`generate_settings_example().save()` → SHA-256 `5635a078302cc6513b3a85e795ba0c4f75afa3adbcf9de8385755c604974da3d`,
1814 bytes. The post-move document must equal it byte for byte.

## Suite

| Run | Result | Wall | Per test |
|---|---|---|---|
| `hatch run test.py3.11:run`, no `CUEMS_CONF_PATH` | 9 failed, 2698 passed, 96 skipped, 2 xfailed, **16 errors** | 119.17 s | — (not a baseline: see M9) |
| same, `CUEMS_CONF_PATH=tests/data/corpus/cuems-engine/` | identical: 9 failed, 2698 passed, 96 skipped, 2 xfailed, 16 errors (2821 collected) | 116.03 s | **41.1 ms/test** (2-vCPU VM; host-specific) |

**Pre-fix range at implementation start (T001, 2026-09-28, two runs)**: 9 failed, 2702 passed,
96 skipped, 2 xfailed, 16 errors in 123.45 s / 124.39 s (2825 collected, **43.7–44.0 ms/test**).
**After Phase 2, before US1's scripts existed (two runs)**: 3–4 failed, 2722–2724 passed,
106–107 skipped, 2 xfailed, 14 errors in 127.65 s / 115.55 s (~2849 collected, **40.6–44.8 ms/test**).
The non-passing cases at that moment were the packaging tests written ahead of their scripts
(fail-first) and the laziness flake; the final hermetic figure is T081's.

**R12 corrected (T027)**: `get_video_output_id('default')`/`get_audio_output_id('default')` raise
`KeyError` on every node — fresh or not — because they read `node_conf['default_*_output']`,
keys `settings.xsd` has never declared. Zero callers; feature 014's fossil. Pinned as measured.

**`test_descriptor_laziness` on this host**: after T007 pointed its probe at a real corpus it
fails the 1.10× cap on roughly two runs in three (public 285 ms vs internal 233 ms = 1.22×, script
alone 1.23×) and passes on the others — the same sub-noise-floor timing assertion the execution
document's §4.6 records. Not a schema or a code regression: the probe's timed region starts after
the manager is built, and the public path builds *fewer* schemas in it than before. Re-run before
recording a delta; the budget needs a noise floor (§4.6's own recommendation), which is not this
feature's to add.

**M9 (finding)**: all 25 come from four modules that construct `ConfigManager(load_all=False)`
with no `config_dir` (`test_public_surface.py`, `test_descriptor_instances.py`,
`test_public_descriptor.py`, `test_descriptor_laziness.py`), and
`tests/support/config_inventory.py:55` pops `CUEMS_CONF_PATH` from the environment **at
import time, for the whole session** — so even an exported path is discarded and the
constructor's `/etc/cuems/` default must exist on the developer's host. That is the condition
this feature exists to remove. Step 0 of the plan passes an explicit `config_dir` (the engine
corpus) in those four modules; the suite budget uses the **41.1 ms/test** figure above, computed
over the collected population, since the 25 non-passing cases cost the same wall time either
way and the population is what SC-PERF-001 compares.

For comparison, the execution document's figure (another host) is a **range**: 2717–2719 passed,
100–101 skipped, 2 xfailed — `test_descriptor_laziness` skips a varying set of sub-noise-floor schemas
and occasionally fails one or two on a clean tree (its §4.6, extended 2026-09-25). Quote ranges, never a
single run, when recording a delta. The population differs slightly (2805 collected here); only the per-test figure from
this host is used for SC-PERF-001.

## Lifecycle-test substrate

| Item | Measured |
|---|---|
| `mmdebstrap --mode=unshare --variant=apt --include=python3 bookworm` | 38 s, 200 MB tarball, no root |
| `unshare --map-auto --map-root-user … chroot` | uid 0, `dpkg 1.21.23`, `python3 3.11.2`, `apt 2.6.1` |
| container runtimes | none (`podman`, `docker`, `systemd-nspawn` absent) — not needed |

## UX pass and announcements (T075, T080, 2026-09-28)

- The three pinned wordings are one constant each, printed identically by the tool, `--check`
  and `postinst`: `NOT PROVISIONED` (4 print sites), `modified, kept`, and the fixing commands
  `cuems-init-node`, `cuems-init-node --reset`, `systemctl restart cuems-nodeconf.service`,
  `systemctl unmask cuems-nodeconf.service && systemctl enable --now cuems-nodeconf.service`.
  The reporting idiom is `<path>: <verdict> (<detail>)`, the one `cuems-convert-documents` uses.
- Re-cuts announced: `cuems-common`'s `3af31cc` (its local commits `b3dd7e1`, `f6750d7` amend the
  `1.3.0-23` entry, which names the handover and the retired minter) and `cuems-nodeconf`'s
  `6c0cca7` (its brief §9.3 records one re-cut for feature 003 and B together). This repository
  creates no tag in this feature (D27); the migration guide §7 carries the table.
- Repository-wide `ruff` on the integration branch: 365 fixable findings (pre-existing); on this
  branch: 362. Every file this feature touches lints clean.

## Build (T071, 2026-09-28)

| Build | Wall | `pyvenv.cfg` | Notes |
|---|---|---|---|
| 1 (pre-F1) | 1m37s | `home = /usr/bin`, `bin/python -> ../../../bin/python3` | `usr/share/cuems/{schemas,defaults}` present; zero `/etc/cuems` conffiles |
| 2 and 3 (double build, SC-005) | 1m32s / 1m32s | same | `usr/share/cuems/defaults/*` byte-identical across the two builds: SHA-256 `f42a4f93…06c91` for the concatenation |
| 4 (relabel fix) | 1m35s | same | built `postinst` contains no `dh_python2`; autoscript → `set +e` → tool block in that order |

`.deb` size: 9,013,536 bytes. `git status` after each build: clean (artifacts ignored).

## Chroot lifecycle (T017/T018/T030/T040/T058, 2026-09-28) — measured in the bookworm chroot

Substrate: `mmdebstrap --mode=unshare --variant=apt --include=python3,python3-systemd,python3-daemon`
(the tarball with the package's runtime dependencies; a first attempt named `xmlschema`, which is
not a Debian package, and produced an empty tarball). Extraction skips `./dev/*` (no `CAP_MKNOD`
in the namespace; a bind mount of the host `/dev` is refused too) and provides a plain-file
`/dev/null` and a fake `sys/class/net/ethernet0/address` per root — there is no sysfs in the
chroot, and the tool refuses without a MAC (FR-025a), which is itself the first measured
fallback path.

| Case | Result |
|---|---|
| fresh install, `ConfigManager(load_all=True)` inside the venv | **loads**; uuid4 minted (SC-001); no sentinel token anywhere under `/etc/cuems` (SC-007) |
| second root from the same `.deb` | a different uuid4 (SC-007) |
| tool cannot determine a MAC (no `ethernet0`) | refuses; `postinst` installs the placeholders, prints `NOT PROVISIONED`, exits 0; `--check` exits **3** and reports the absent Avahi record as expected (SC-008) |
| tool not executable (the broken-venv trap) | the `[ -x ]` branch warns, placeholders installed, exit 0 (SC-008, second variant) |
| upgrade / `--reinstall` / remove-then-install | the three documents byte-identical through all four steps (SC-002) |
| purge alone | the nine paths and the write record gone; other owners' files byte-identical; `/etc/cuems` kept (SC-003) |
| purge of every package | `/etc/cuems` gone; a reinstall mints a **new** uuid (SC-003) |
| six installed `.xsd` | byte-identical to the bundled schemas; the corpus validates against `/etc/cuems/project_mappings.xsd` and `settings.xsd` (SC-006, SC-011) |
| **the Breaks** | a bare `dpkg -i` of new `cuems-utils` beside `cuems-common 1.3.0-22` is **refused** ("installing cuems-utils would break cuems-common, and deconfiguration is not permitted"); with `--auto-deconfigure` (what apt does) `cuems-utils` configures, the old `cuems-common` is deconfigured, and the new one upgrades it |
| **custody transfer, utils first** | live map byte-identical; zero `network_map.*.dpkg-*` siblings; `.xsd` equals the installed library's; a later `purge cuems-common` leaves the map |
| **custody transfer, common unpacked first** | dpkg's own obsolete-conffile step at unpack parks the modified map as `.dpkg-bak` and removes the `.xsd`; the `postinst` block restores the map from the snapshot, removes the identical `.dpkg-bak`, reinstalls the schema — before the conversion loop, which then reports "already converted". Configuration is dependency-ordered by dpkg (the `cuems-common` postinst refuses to run without the venv), so the realistic form of this order is unpack both, then `dpkg --configure -a` |
