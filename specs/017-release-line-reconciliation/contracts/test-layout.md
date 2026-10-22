<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract: test layout and directory markers — FR-063, SC-012

**Audience:** every contributor, including the release-line maintainer (`CONTRIBUTORS.md`,
`upstream-reports/release-line-hygiene.md`).

## Rules

1. **A test module lives in exactly one of** `tests/unit/`, `tests/integration/`,
   `tests/contract/`, `tests/packaging/`. `tests/support/`, `tests/data/` and `tests/golden/` hold
   no test modules.
2. **No `tests/test_*.py` at the root.**
3. **The marker comes from the directory.** A `pytest_collection_modifyitems` hook in
   `tests/conftest.py` adds `unit`, `integration`, `contract` or `packaging` from
   `item.path.relative_to(<tests root>).parts[0]`. No module declares its own directory marker.
4. The four markers are registered in `pyproject.toml` beside `slow` and `expects_deprecation`.
   `addopts = "--strict-markers"`.
5. The `filterwarnings` entry for the name-coercion regression follows its module:
   `tests.test_name_coercion` → `tests.unit.test_name_coercion`.

## Kind, by signal (checked per file at move time)

| Kind | Signal |
|---|---|
| `integration` | real sockets / `pynng`, `asyncio` servers, threads, syslog, `CUEMS_CONF_PATH` or `/etc/cuems`, subprocesses of the console tools |
| `contract` | asserts a published surface: schema hashes, the API snapshot, enumerations, version sites, the workflow file |
| `packaging` | reads `debian/`, builds or inspects a `.deb`, the chroot lifecycle |
| `unit` | everything else (pure in-process) |

## Enforcement

`tests/contract/test_test_layout.py`:
- (a) `glob("tests/test_*.py") == []`;
- (b) collected in a subprocess (`pytest --collect-only -q -p no:cacheprovider` plus a tiny
  plugin that prints each item's markers), every item carries **exactly one** of the four markers.

Red first: (a) is red before the C3 moves, and (b) is red before the hook exists.

## Moves (research R10)

| Destination | Root modules |
|---|---|
| `integration/` | `test_hubservices`, `test_communicatorservices`, `test_logger`, `test_configmanager` |
| `contract/` | `test_version` |
| `unit/` | `test_canvas_region_roundtrip`, `test_cue`, `test_cue_output`, `test_cuelist`, `test_fade_cue`, `test_funcdict`, `test_helpers`, `test_name_coercion`, `test_project_mappings`, `test_signalengine`, `test_superproperty`, `test_xml` |
| retired | `testdev_nng_talk.py` → `evidence/test-retirements.md` |

These are pure `git mv`s. Any name collision with an existing module in the destination is
resolved by renaming the moved file, recorded in the commit message. The pass set is compared
before and after (SC-012).
