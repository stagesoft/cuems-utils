<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Implementation Plan: `/etc/cuems` first install

**Branch**: `011-etc-cuems-first-install` (local; merges into `feat/xml-refactor`) | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/011-etc-cuems-first-install/spec.md`, clarified 2026-09-25 (eight questions answered, three deferred here and settled in `research.md` R1, R2, R16).

## Summary

A plain `apt install cuems-utils` must leave a node that loads its configuration and is uniquely
identified. The package will ship the six schemas to `/etc/cuems` (replacing `cuems-common`'s
drifting mirror), generate the three default documents at build from the schema descriptor and a
TOML seed-values file, install them only when absent, and run a new public tool,
`cuems-init-node`, from `postinst` to mint one uuid4 and write a coherent triple atomically.
`postinst` never exits non-zero: every failure degrades to pristine placeholders and a warning.
The tool also re-provisions (preserving identity and operator edits, `--reset` to return to
defaults), applies a `defaults.d` overlay, and verifies all four identity locations with
`--check`. `cuems-common` hands over two paths, retires its second uuid minter, and gains D14's
derivation contract. Purge removes only the package's own paths.

The technical approach is settled in `research.md`: entry point in the venv `bin/` invoked by
absolute path under `timeout` (R1, R8); generation inside `override_dh_virtualenv` through the
built venv's interpreter (R2); a snapshot-and-`rm_conffile` custody transfer for the two
`cuems-common` paths (R3); TOML as package data read by one code path (R4); a JSON write record
under `/var/lib/cuems-utils` for three-way edit preservation (R5); validate-then-replace with
in-memory restore for the triple (R6); `cuems-config-node render` as the Avahi derivation
mechanism, leaving `cuems-nodeconf` untouched (R7); unprivileged `mmdebstrap` chroots for
lifecycle tests (R9); budgets re-based on measurements (R10).

## Technical Context

**Language/Version**: Python 3.11 (package pinned; suite on 3.11.9). POSIX `sh` for the maintainer scripts. GNU make for `debian/rules`.
**Primary Dependencies**: stdlib `tomllib`, `importlib.resources`, `fcntl` (flock); existing `xmlschema==3.4.3` through the descriptor; `debhelper-compat (= 13)`, `dh-virtualenv (>= 1.2)`; `coreutils timeout`. **No new runtime dependency.**
**Storage**: files — `/etc/cuems/*.xml|*.xsd`, `/usr/share/cuems/{schemas,defaults}/`, `/var/lib/cuems-utils/init-node/last-written.json`, `/etc/cuems/defaults.d/*.toml`.
**Testing**: pytest via `uvx hatch run test.py3.11:run`; script-level packaging tests with path overrides; `slow`-marked chroot lifecycle tests via `mmdebstrap --mode=unshare` + `unshare --map-auto --map-root-user chroot` (no root, no container runtime).
**Target Platform**: Debian 12 bookworm amd64 nodes (N97-class), `/usr/bin/python3` = 3.11.2; trixie neutrality preserved (no new version-bearing path).
**Project Type**: library + CLI entry point + Debian packaging; one cross-repository handover (`cuems-common`).
**Performance Goals**: `cuems-init-node` write ≤ 4 s cold, `--check` ≤ 3 s cold; `postinst` ≤ 10 s fresh / ≤ 2 s upgrade (60 s hard `timeout`); suite ≤ 110 % of the per-test figure in `baseline.md`; package size delta ≤ 100 KB (research R10).
**Constraints**: `postinst` exits 0 on every path; nothing under `/etc/cuems` is a conffile; no existing file under `/etc/cuems` is modified by the package; `/etc/cuems` is never removed recursively; the venv is one-way (`/usr/bin/python3` cannot import `cuemsutils`); no manifest overlap with any sibling package; build reproducible (sentinel, never a minted uuid); one minter (`cuemsutils.tools.Uuid`); library version stays `0.1.0rc16`; no schema shape change (annotations only, R13).
**Scale/Scope**: three documents, six schemas, one tool, two maintainer scripts, one handover in one sibling repository; ~20 new test modules; two production hosts to migrate by the guide.

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1 (below).*

### I. Code Quality By Default

- `ruff check src/ tests/` (E, F, W, I) clean; no new warning in the default tooling.
  Maintainer scripts pass `sh -n` and, where `shellcheck` is available, `shellcheck -s sh`.
- Every public symbol (`cuemsutils.tools.init_node.main`, the seed-values loader, the generator
  module) carries a docstring stating its contract; every maintainer-script block carries the
  comment that names the decision it implements (D5, D6, D13, R8), the convention
  `cuems-common`'s scripts already follow.
- The generator and the tool share one code path for reading seed values and building
  documents (R4) — no second implementation of the descriptor walk.

### II. Tests As A Release Gate

Fail-before-pass per story (the task list makes each explicit):

| Story | Tests that fail before and pass after |
|---|---|
| US1 schemas | `tests/packaging/test_built_package.py` (six schemas in `/usr/share/cuems/schemas`, byte-identical; zero `/etc/cuems` conffiles); chroot: installed `.xsd` equal bundled; custody transfer in both orders (R3) |
| US2 defaults | `tests/contract/test_seed_values.py` (V1–V4, both-direction completeness); `test_make_defaults.py` (determinism, sentinel, empty `LoadReport`); script-level `test_postinst.py` install-if-absent per file |
| US3 init-node | `tests/integration/test_init_node_triple.py` (mint, coherence, compound-string substitution, atomic restore on injected failure, `--install-missing` never rewrites); `test_postinst.py` fallback path and `timeout`; chroot SC-001, SC-007, SC-008 |
| US4 TOML/overlay | `test_seed_values.py` byte-identity before/after the move; `test_init_node_overlay.py` (precedence, refusals, typed scalars, `postinst` ignores overlay) |
| US5 purge | script-level `test_postrm.py` (nine paths + record; nothing else; `remove` no-op); chroot SC-003 |
| US6 --check | `test_identity_check.py` (four locations, exit classes 0/1/2/3, precedence, never writes) |
| US7 hygiene | `test_built_package.py` (compat 13, `Standards-Version`, no `dh_python2`, `pyvenv.cfg` home, no artifacts in `git status` after build) |
| F1 (FR-047) | `test_duplication_flags.py::test_every_schema_declares_its_writer`; `test_schema_scope` hashes updated in the same commit |
| public API | `test_public_api_surface.py` with the `scripts` key (golden extended once, R11) |
| cross-repo | `test_ordering_premise.py` (R16); in `cuems-common`: `test_config_node_render.py`, `test_avahi_vocabulary.py` sentinel extension |

Existing goldens are not regenerated (FR-021); `tests/golden/outcomes.json` is not touched.

### III. Consistent User Experience

- CLI: argparse, `<path>: <verdict> (<detail>)` lines, exit-code table in the contract, the
  same style as `cuems-convert-documents`; the library's log noise silenced by default (R15).
- Wording pinned by tests: `NOT PROVISIONED`, `modified, kept`, and the three fixing commands
  appear identically in `--check` output and in `postinst`'s fallback warning.
- Docs: `debian/README.source` gains the first-install section; `migration-guide.md` covers
  upgraded hosts, purge, imaging, exit codes, handover order (FR-045); `cuems-common`'s contract
  document gains the D14 section (contract 5 of the handover).

### IV. Performance Budgets Are Requirements

Declared and re-based on measurement in `research.md` R10; validated by the chroot tests
(timing the tool and `dpkg -i`) and by the suite run recorded in `baseline.md`. A regression is
recorded as such, never restated as passing.

### Gate result

**Pass.** One item to justify is recorded in Complexity Tracking: the public API golden is
*extended* (a new `scripts` key), which is a sanctioned, argued golden event, not a regeneration.

## Project Structure

### Documentation (this feature)

```text
specs/011-etc-cuems-first-install/
├── plan.md                 # this file
├── spec.md
├── research.md             # Phase 0 — R1…R18
├── data-model.md           # Phase 1
├── quickstart.md           # Phase 1
├── contracts/
│   ├── cuems-init-node.md
│   ├── packaging.md
│   ├── system-defaults-toml.md
│   └── cuems-common-handover.md
├── baseline.md             # measurements: timings, suite, chroot; filled as tasks land
├── migration-guide.md      # FR-045 — written during implementation
├── checklists/requirements.md
└── tasks.md                # /speckit.tasks output (not created here)
```

### Source code (repository root)

```text
src/cuemsutils/
├── defaults/
│   ├── __init__.py                     # package-data marker
│   └── system-defaults.toml            # R4 — the one copy code reads
├── xml/
│   ├── seed_values.py                  # TOML load + V1–V4 checks + merge with overlay
│   ├── make_defaults.py                # `python -m cuemsutils.xml.make_defaults --out DIR` (R2)
│   ├── descriptor.py                   # _SETTINGS_EXAMPLE_VALUES removed; generate_settings_example delegates
│   └── schemas/*.xsd                   # R13 annotation only (one isolated commit)
└── tools/
    ├── init_node.py                    # the entry point: modes, triple write, write record
    ├── identity_check.py               # --check: four locations, exit classes
    └── write_record.py                 # /var/lib/cuems-utils/init-node/last-written.json

debian/
├── control                             # debhelper-compat (= 13), Standards-Version 4.6.2, Breaks
├── rules                               # override_dh_virtualenv: generator + install (R2)
├── cuems-utils.postinst                # contract packaging.md; after #DEBHELPER#
├── cuems-utils.postrm                  # purge inventory (data-model §8)
├── cuems-utils.links                   # usr/bin/cuems-init-node
├── changelog                           # rc16 entry amended: first install shipped
├── README.Debian, README.source        # rewritten / extended
└── compat                              # deleted

pyproject.toml                          # [project.scripts] cuems-init-node; include defaults/

tests/
├── packaging/
│   ├── stubs/                          # fake cuems-init-node; old cuems-common stub .deb recipe
│   ├── test_postinst.py                # script-level, path overrides
│   ├── test_postrm.py
│   ├── test_built_package.py           # needs a built .deb (skips otherwise)
│   ├── test_ordering_premise.py        # R16
│   └── test_lifecycle_chroot.py        # slow; CUEMS_CHROOT_TAR
├── contract/
│   ├── test_seed_values.py
│   ├── test_make_defaults.py
│   ├── test_identity_check.py
│   ├── test_duplication_flags.py       # + F1 writer check
│   ├── test_schema_scope.py            # hashes move once (R13)
│   └── test_settings_example_generation.py   # imports re-pointed
├── integration/
│   ├── test_init_node_triple.py
│   ├── test_init_node_overlay.py
│   └── test_default_mappings_fresh.py  # R12
├── support/public_api.py               # PUBLIC_SCRIPTS (R11)
└── golden/api/public_api.json          # + "scripts" key

../cuems-common/ (handover, contract cuems-common-handover.md)
├── debian/{install,preinst,postinst,postrm,control,changelog}
├── usr/bin/cuems-config-node           # render; no uuid1()
├── usr/share/cuems/cuems.service.*     # sentinel uuid
├── docs/node-identity-contract.md      # D14 section
└── tests/…                             # five re-based/retired, two added
```

**Structure Decision**: single library project, extended in place. New runtime code sits under
`tools/` (public façade) and `xml/` (internal mechanics), matching the existing split; packaging
tests get their own `tests/packaging/` directory because they are shell- and `.deb`-level, not
Python-API-level, and several skip unless a build or chroot exists.

## The work, in dependency order

The stories are independent to *ship*, but they build on one another to *implement*. The order
below is the one that lets each step's tests run against real artifacts rather than stubs.

### Step 0 — make the suite independent of a host `/etc/cuems` *(finding M9, prerequisite)*

Measured on this host: 16 errors and 9 failures, all from four modules that construct
`ConfigManager(load_all=False)` with no `config_dir`, while `tests/support/config_inventory.py`
pops `CUEMS_CONF_PATH` from the environment at import time for the whole session. The
constructor's default `/etc/cuems/` must therefore exist on the developer's host — the very
condition this feature exists to make unnecessary. The fix is local: those four modules pass
`config_dir=<engine corpus>` explicitly (the constructor already accepts it), and a
`conftest.py` assertion pins that no test depends on a host `/etc/cuems`. Recorded in
`baseline.md` (41.1 ms/test on this host, the SC-PERF-001 reference).

### Step 1 — seed values to TOML (US4's data half; D7, D9)

`defaults/system-defaults.toml`, `xml/seed_values.py` (load, V1–V4, overlay merge),
`descriptor.py` slimmed, `test_settings_example_generation.py` re-pointed. Gate: generated
`settings.xml` byte-identical before and after (SC-005's precondition).

### Step 2 — the generator for all three documents (US2; D2, D3, R12)

`xml/make_defaults.py` builds `settings`, `network_map` (one `firstrun` row: sentinel,
`unprovisioned`, `0.0.0.0`) and `default_mappings` (sentinel node entry, empty sections, empty
defaults, `number_of_nodes = 1`), each validated and loaded back with an empty `LoadReport`,
generated twice and compared. Retirement notes on the `default_mappings` pieces (FR-012).

### Step 3 — `cuems-init-node` (US3, US4's apply half, US6; D11–D13, R5–R8, R14, R15)

`tools/write_record.py`, `tools/identity_check.py`, `tools/init_node.py`; `[project.scripts]`;
`PUBLIC_SCRIPTS` and the golden's `scripts` key. Tests: triple coherence, compound-string
substitution, atomic restore, `--install-missing` never rewrites, overlay precedence and
refusals, three-way edit preservation and `--reset`, `--check` classes and precedence,
nodeconf-active warning, idempotence.

### Step 4 — packaging (US1, US2's install half, US3's `postinst` half, US5, US7; D4–D6, R1–R3, R8, R17)

`debian/rules`, `control`, `postinst`, `postrm`, `links`, `changelog`, `README.*`, `compat`
removed; script-level tests with path overrides; `test_built_package.py`; the chroot lifecycle
suite (`test_lifecycle_chroot.py`) covering SC-001–SC-003, SC-006–SC-010 and the R3 orders.
`baseline.md` gets the `dpkg -i` and tool timings.

### Step 5 — F1 writer annotations *(one isolated commit; FR-047, R13)*

Six schemas annotated, six hashes updated, the F1 check added to `test_duplication_flags.py`.

### Step 6 — the `cuems-common` handover *(sibling repository; contract cuems-common-handover.md)*

Custody transfer, `cuems-config-node render`, sentinel templates, `postinst` render call, five
tests re-based/retired, two added, the D14 section in `docs/node-identity-contract.md`,
`1.3.0-23` changelog text. Verified by the chroot test installing both packages.

### Step 7 — records (FR-045, FR-046)

`migration-guide.md`; planning documents corrected for M1–M9 with the corrections recorded;
`debian/README.source` first-install section replaced by the landed description; CLAUDE.md
"Recent Changes" entry; `baseline.md` completed.

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
|---|---|---|
| The public API golden gains a `scripts` key (golden moves once) | FR-023 requires the new entry point to be a recorded, sanctioned surface change; the snapshot only knew classes | leaving entry points unrecorded means a renamed or dropped script is invisible to the surface test, which is the gap the golden exists to close |
| A JSON write record outside the three documents (R5) | FR-027's three-way preservation needs to know what the tool last wrote; the documents cannot carry that without a schema change | "overwrite silently" and "refuse on any difference" were both rejected by the maintainer in clarification (Q8, option D) |
| A 60 s `timeout` around the tool in `postinst` (R8) | a hang blocks the stack as surely as a non-zero exit, and the design named only the exit case | no simpler mechanism exists in POSIX `sh`; `timeout` is coreutils and present on every target |
| Performance budgets re-based above the spec's proposal (R10) | measured cost on the build host is 1.5–2.0 s for the write path; node hardware is slower | keeping ≤ 2 s would fail on the reference hardware for reasons unrelated to this feature's code |

## Constitution re-check (post-design)

Unchanged: pass. The design adds no dependency, no schema shape change, no second code path
for reading values or building documents; every user-facing surface has a contract and a test
that pins its wording; every budget has a measurement and a validation method.
