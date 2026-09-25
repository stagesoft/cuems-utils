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
| package size delta | *pending* | ≤ 100 KB |

Generator determinism: two `generate_settings_example().save()` runs → equal SHA-256. ✅

## Suite

| Run | Result | Wall | Per test |
|---|---|---|---|
| `hatch run test.py3.11:run`, no `CUEMS_CONF_PATH` | 9 failed, 2698 passed, 96 skipped, 2 xfailed, **16 errors** | 119.17 s | — (not a baseline: see M9) |
| same, `CUEMS_CONF_PATH=tests/data/corpus/cuems-engine/` | identical: 9 failed, 2698 passed, 96 skipped, 2 xfailed, 16 errors (2821 collected) | 116.03 s | **41.1 ms/test** (2-vCPU VM; host-specific) |

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

For comparison, the execution document's figure (another host): 2719 passed, 100 skipped,
2 xfailed. The population differs slightly (2805 collected here); only the per-test figure from
this host is used for SC-PERF-001.

## Lifecycle-test substrate

| Item | Measured |
|---|---|
| `mmdebstrap --mode=unshare --variant=apt --include=python3 bookworm` | 38 s, 200 MB tarball, no root |
| `unshare --map-auto --map-root-user … chroot` | uid 0, `dpkg 1.21.23`, `python3 3.11.2`, `apt 2.6.1` |
| container runtimes | none (`podman`, `docker`, `systemd-nspawn` absent) — not needed |
