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
| `ConfigManager(load_all=True)`, engine corpus (build host) | 1.17 s | — |
| `ConfigManager(load_all=True)`, cold, inside the chroot on a freshly provisioned node (SC-001) | **1.22 – 1.35 s** | — |
| `cuems-init-node` write, cold (chroot, T074) | **1.14 s** fresh triple; **1.26 – 1.34 s** re-run with unchanged inputs | ≤ 4 s ✅ |
| `cuems-init-node --check`, cold (chroot) | **0.50 s** | ≤ 3 s ✅ |
| `dpkg -i`, fresh install (chroot; unpack of the 9 MB venv + autoscript + postinst incl. the tool) | **2.87 s** whole `dpkg -i`; the postinst share is the tool's 1.1 s plus the schema copies | ≤ 10 s (60 s hard cap) ✅ |
| `dpkg -i` again, triple present (upgrade path) | **2.70 s** whole `dpkg -i`, of which the postinst share is ≈ 1.4 s (the tool starts, finds nothing to do, exits) — the rest is dpkg re-unpacking the venv | ≤ 2 s for the postinst share ✅; the whole-`dpkg -i` figure is recorded, not budgeted |
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

**Status of those two re-cuts — first recorded 2026-09-28, CLOSED 2026-09-29.** The entry is kept
in two dated halves rather than rewritten, because the failure it describes is the reason the
counterpart check exists and is worth being able to read afterwards.

**As at 2026-09-28** — one re-cut had happened, one had not, and the pair as tagged did not work:

| Repository | head | tag | Drift | Verdict |
|---|---|---|---|---|
| `cuems-nodeconf` | `b305c1c` | **`b305c1c`** (re-cut from `6c0cca7`) | 0 | ✅ re-cut as announced |
| `cuems-common` | `e3c9430` | `3af31cc` | **3 commits**, all packaged: `b3dd7e1` (the `network_map.{xml,xsd}` handover, `preinst`/`postinst`/`postrm`, `debian/control`, `debian/install`), `f6750d7` (D14 — `cuems-config-node` stops minting, the three templates take the sentinel), `e3c9430` (the snapshot-wins fix) | ❌ announced, not performed |
| `cuems-power-bridge` | `13a9af4` | `d5c4226` | **6 commits**, two packaged: `ca67a99` (`debian/rules` resolves `cuemsutils` from the sibling checkout, not PyPI), `13a9af4` (strips foreign console scripts; `pyproject.toml` `0.3.0` → `0.3.1`) | ❌ not announced either |
| `cuems-utils` | `1a4e608` | — | — | ⏳ by decision (D27) |

**What the un-moved `cuems-common` tag cost, and it was not cosmetic.** `cuems-nodeconf`'s re-cut
candidate hard-requires the handover — its own tag message says so — and its
`_render_service_record` calls `sys.exit(-1)` on a template with no sentinel. At `3af31cc` the
**controller** template still carried `a3811d78-099f-11f0-a075-00e04c01b7e3`. So a technician
checking out the two candidate tags got a controller whose `cuems-nodeconf` refused to start,
with both working trees already correct and the reciprocal `Breaks:` unable to catch it, because
both packages sat at exactly their intended versions. **A tag set is only as good as its least
current member**, and nothing in the packaging expresses that.

**As at 2026-09-29 — all four re-cuts performed, verified against the remotes:**

| Repository | head | tag | Pushed | Signature |
|---|---|---|---|---|
| `cuems-nodeconf` | `9b8f565` | **`b305c1c`** | ✅ matches `origin` | ✅ good, `Adrià Masip <adria@stagelab.coop>` |
| `cuems-common` | `6a15200` | **`e3c9430`** (was `3af31cc`) | ✅ matches `origin` | ✅ good |
| `cuems-power-bridge` | `af7acb1` | **`13a9af4`** (was `d5c4226`) | ✅ matches `origin` | ✅ good |
| `cuems-utils` | `4ef7f91` | — | — | ⏳ by decision (D27): tags after 011–014 |

Checked, not assumed:

- **The composability failure is gone.** `git show xml-refactor-merge-candidate:usr/share/cuems/cuems.service.controller`
  in `cuems-common` now yields `uuid=00000000-0000-0000-0000-000000000000` — the sentinel — so
  `cuems-nodeconf`'s renderer accepts it and a controller starts.
- **`cuems-nodeconf`'s tag message now names the right counterpart**: `e3c9430`. It previously said
  `f2fc0f5`, two relocations stale, and contradicted its own closing paragraph.
- **Each head is exactly one commit past its tag, and that commit is documentation** — one `specs/`
  file each. The convention holds: the tag advances only for packaged content.
- **No version moved**: `0.1.0rc16` / `1.3.0-23` / `0.1.0-8` / `0.3.1-1`, matching `test_no_version_bump.py`.
- **Every tag signature verifies.** Both signing methods now do: this workstation signs with GPG
  `B25EB0EDCB9F13C2`, the development server signs over SSH with
  `SHA256:n2JoMP0xXSuw4NQS2cGBNEaYkcTHMobgcG1gDzRcrUU`, and `gpg.ssh.allowedSignersFile` was
  configured on 2026-09-29 so the latter verify here instead of erroring. A mixed-signature history
  across these repositories is two machines, not a defect.

**What remains is validation on real hardware**, which no amount of checking here substitutes for:
`cuems-nodeconf`'s ledger `specs/002-public-network-map-path/checklists/hardware-verification.md`,
entries §1–§6, and `cuems-power-bridge`'s
`specs/002-cluster-poweroff-cli/checklists/hardware-verification.md`. Every box is unchecked, and
that is the accurate state.

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

## T074 — budgets validated (2026-09-28, chroot on the build host, two runs)

All within budget (table above). Method: `date +%s%N` around each command inside the chroot,
`CUEMS_LOG_LEVEL=CRITICAL`, an empty `sh -c 'exit 0'` costing 2 ms as the floor. The reference
node hardware (N97-class) has still not been measured — both production hosts have been
unreachable since 2026-09-23 — so the 2× allowance research R10 built into the budgets stands
untested; the hardware ledger entry §5 in `cuems-nodeconf` is where that measurement is recorded
when a node is available.

## T001 / T081 — the suite, before and after (2026-09-28, this host, `uvx hatch run test.py3.11:run`)

| Run | Result | Wall | Collected | Per test | vs plan start (43.7–44.0 ms) |
|---|---|---|---|---|---|
| plan start, pre-M9 fix (two runs) | 9 failed, 2702 passed, 96 skipped, 2 xfailed, 16 errors | 123.45 / 124.39 s | 2825 | 43.7–44.0 ms | reference |
| feature complete, run 1 | 4 failed (3× laziness flake, 1× `test_realtime_25fps_jitter`), 2802 passed, 105 skipped, 2 xfailed | 143.78 s | 2913 | 49.4 ms | **112 % — exceeded** |
| feature complete, run 2 | 1 failed (`test_realtime_25fps_jitter`), 2805 passed, 105 skipped, 2 xfailed | 143.92 s | 2913 | 49.4 ms | **112 % — exceeded** |
| after caching the `.deb` reads in the packaging fixtures | 2 failed (laziness flake), 2804 passed, 105 skipped, 2 xfailed | 130.13 s | 2913 | **44.7 ms** | **102 % ✅** |

**Recorded as exceeded, then mitigated, not restated.** The first two complete runs were over the
budget by 12 %, and the cause was one file: `tests/packaging/test_built_package.py` re-extracted
the 9 MB venv from the `.deb` for every assertion (about 13 s for eight tests against a 44 ms
median). A per-archive cache in the packaging fixtures (`ba68bf0`) brings the file to under 5 s
and the suite to 102 % of the reference. No library code changed between those runs.

**The two non-passing tests are pre-existing, load-sensitive timing tests**, neither touched by
this branch: `test_descriptor_laziness` (the execution document's §4.6 flake; fails one to three
cases on roughly two runs in three on this 2-vCPU VM, passes on the others) and
`tests/unit/test_ctimecode_timer.py::TestIntegration::test_realtime_25fps_jitter` (a ±1 ms
real-time callback assertion; failed in two of three full runs under load, **passes 3 of 3 in
isolation**; `git diff feat/xml-refactor..HEAD -- src/cuemsutils/tools/CTimecode*` is empty).
The honest range for this tree is **2802–2805 passed, 105 skipped, 2 xfailed**, with 0–4 flake
failures per run. `ruff` is clean on every file this feature touches; `sh -n` passes on both
maintainer scripts.

## T049 — the `cuems-nodeconf` feature 003 gate, verified 2026-09-28

Verified against `../cuems-nodeconf` `feat/xml-refactor` @ `b305c1c`
("feat(003): start-up readiness — honest refusal, identity from settings.xml, own row via the
library"), which is also that repository's re-cut `xml-refactor-merge-candidate` (tag object
`5f0b64a`, annotated and signed, pushed). **A gate, not an edit** — nothing in this repository
changed for it. Its 003 tasks are 47/48; the one open task is its own T048, the maintainer's
tag/announce step.

| Contract §4a clause | Where it is, in `cuemsnodeconf/CuemsNodeConf.py` | Verified |
|---|---|---|
| The render runs **before** `set_comms()` | `:172` `_render_service_record(self._live_record_role())` immediately precedes `:173` `set_comms()`; `:170` `_preflight()` precedes both | ✅ pinned by `tests/test_service_record.py::TestRenderHappensBeforeTheSocket` (`['render', 'set_comms']`) and `tests/test_startup_config.py::TestPreflight::test_preflight_runs_before_identity_and_socket` (`['preflight', 'identity', 'render', 'set_comms']`) |
| Reloads only on change | `:336` `if current == rendered: … return False` — the `_reload_avahi()` at `:359` is unreachable for unchanged bytes | ✅ |
| Refuses unprovisioned with `NOT PROVISIONED`, creates **no** socket | `:232` `Logger.critical(f'NOT PROVISIONED: {reason}')`, reached from `_preflight` before `set_comms` | ✅ `TestUnprovisionedRefusesToStart` — absent, unreadable, invalid, sentinel uuid, sentinel MAC: each exits non-zero with `set_comms` **not called** and no record written |
| Renders at the three role-change sites | `:172` (start-up, live role), `:755` (`NodeRole.controller`), `:780` (`NodeRole.node`) — `grep -n _render_service_record` returns exactly these three call sites and the definition | ✅ |
| Asserts the discovered self uuid | `tests/test_startup_readiness.py::TestSelfGuard` (its FR-013) — a stale uuid at our IP is waited out and warned about naming both uuids; on timeout the error names both and says `restart cuems-nodeconf` | ✅ |
| Seeds through `NodeIndex.ensure`, **naming the `cuems-utils` commit that added it** | `:603` `inserted = self.network_map.ensure(self.node)`; the docstring at `:592-594` reads "inserted BY REFERENCE through NodeIndex.ensure (cuems-utils 73daab6)" | ✅ `73daab6` is an ancestor of this repository's `feat/xml-refactor` @ `1a4e608` (T014's commit) |
| Hardware ledger entry §5 exists | `../cuems-nodeconf/specs/002-public-network-map-path/checklists/hardware-verification.md` §5, added 2026-09-28, citing D3 and this feature's research R7/shape B; §6 was added in the same pass for the start-up refusal | ✅ unchecked, "Not performed" — which is the accurate state, not a gap |

**The run**, from `../cuems-nodeconf/specs/003-startup-readiness/evidence/verification-record.md`
(recorded 2026-09-28, baseline `2ca7474`, this repository installed editable at `73daab6`):
**173 passed** (119 baseline + 54 added), no skips, plus **15 passed** on the equivalence gate.
The yardstick `test_nodeindex_characterization.py` was `cmp`-compared against ours and is
**identical** — `73daab6` did not touch it either.

**One measured caveat, and it is a counterpart problem rather than a gate failure**: the render
refuses (`sys.exit(-1)`, `:325-327`) on a template carrying no sentinel. `cuems-common`'s
**tagged** candidate `3af31cc` still ships the production uuid in
`usr/share/cuems/cuems.service.controller`, so that tagged pair hard-fails on a controller. The
fix is already on `cuems-common`'s `feat/xml-refactor` (`f6750d7`, verified: all three templates
now carry `00000000-0000-0000-0000-000000000000`) — it is only the **tag** that has not moved.
See the counterpart table under "UX pass and announcements".

## Post-merge re-measurement on `feat/xml-refactor` @ `1a4e608` (2026-09-28)

**2800 passed, 111 skipped, 2 xfailed, 0 failed, 45.37 s** — `uvx hatch run test.py3.11:run -- -q`,
this host. Within the honest range T081 recorded (2802–2805 passed, 0–4 flake failures); both
load-sensitive timing tests passed this run. The six extra skips against T081's 105 are the
packaging tests whose `built_deb`/`sibling_deb` fixtures find no artefact in the parent directory
on a clean checkout — the documented skip-with-reason path, not a loss of coverage.

**One trap worth recording, because it cost a false regression here.** The first run of this
re-measurement reported **2 failed** —
`tests/contract/test_public_api_surface.py::test_public_api_matches_the_snapshot` (`scripts: []`
against the golden's `['cuems-convert-documents', 'cuems-init-node']`) and
`::test_the_published_scripts_are_the_declared_set`. Neither is a regression. Both read the
**installed distribution's** entry points via
`importlib.metadata.entry_points(group="console_scripts")` (`tests/support/public_api.py:20`), and
the reused `hatch-test.py3.11` environment held editable metadata from
**`cuemsutils-0.1.0rc10.dist-info`** — predating `[project.scripts]` entirely — while
`cuemsutils.__file__` already resolved to the live `src/` tree. Current code, stale metadata: the
dev-environment form of the "editable install is a no-op unless you remove the packaged copy"
gotcha in `CLAUDE.md`. `hatch env prune` rebuilt it and all 25 tests in that file pass.

The test is therefore **sensitive to install state rather than to the tree**, which is the price
of checking the *published* surface rather than re-reading `pyproject.toml`; that is the right
thing to check, so the note belongs here rather than a change to the test. Anyone seeing those two
failures alone should run `hatch env prune` before looking for a defect.
