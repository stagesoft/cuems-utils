<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Note → the `debian/bookworm` release-line maintainer (`cuems-utils`)

**From:** `cuems-utils` feature 017, 2026-10-22. It is about the release line itself, not a sibling.
Nothing here was changed on `debian/bookworm`; these are requests and records.

## 1. Your line is merged into the refactor, and may keep releasing

`origin/debian/bookworm` (`398a9cf`, `0.1.0rc17`) and `origin/main` (`v0.1.0rc17`) are merged into
`feat/xml-refactor` by feature 017, with their history. Once the maintainer merges 017, your line is
an ancestor of `0.1.1`, and nothing you shipped in rc15, rc16, rc16+1 or rc17 is lost.

**You may keep cutting `0.1.0rcN` until `0.1.1` is published** (017 Q10: the new structure and
package versions are agreed with the development team). Each release you cut is merged into
`feat/xml-refactor` the same way: a real merge, never a cherry-pick, so your next commit merges
without re-conflicting. `tests/packaging/test_changelog_completeness.py` fails if a released
`debian/changelog` entry goes missing from the refactor or drifts from yours byte for byte.

## 2. Please stop tracking build outputs and experiment files

`debian/bookworm` tracks **42 paths** that were never shipped and must not land anywhere. The merge
deleted them on the refactor side; please remove them on yours too.
- **21 debhelper build outputs**, including `debian/.debhelper/`, `debian/cuems-utils/DEBIAN/`,
  `debian/cuems-utils/usr/…`, `debian/files`, `*.substvars`, `*.debhelper`,
  `debian/debhelper-build-stamp`, `.pybuild/` and **`debian/compat`**. `debian/compat` beside
  `debhelper-compat (= 13)` is a debhelper error that fails the build.
- **21 root files** from a 2025 bus/OSC experiment and `.python-version`: `bus_test.py`,
  `bus_test_slave.py`, `test_bus_controller.py`, `test_bus_node.py`, `test_osc_hub_*.py`,
  `test_player_queue.py`, and the `OSC_*`/`PING_PONG_*`/`QUICK_START_*`/`REFACTORING_*`/… notes.

The exact list is in `cuems-utils`' `specs/017-release-line-reconciliation/research.md` R17.

## 3. `0.1.0rc17` is not on PyPI

`v0.1.0rc17` is tagged and its `.deb` shipped, but PyPI's newest is `0.1.0rc16` (PyPI JSON API,
2026-10-22). So `cuems-engine`'s `cuemsutils >= 0.1.0rc17` floor cannot be resolved from PyPI.
Whether to upload rc17 is your call. `CHANGELOG.md` marks it "(Debian only; not published to
PyPI)", and will drop the mark if it is uploaded before `0.1.1` ships.

## 4. New tests go in a kind directory, never at the root

All three test files your line added (`tests/test_action_cue_stop_project.py`,
`tests/test_media_guards.py`, `tests/unit/test_media_pixel_dimensions.py`) had to be ported or
re-filed. After 017's cleanup, `cuems-utils` requires every test module to live in exactly one of
`tests/unit/`, `tests/integration/`, `tests/contract/` or `tests/packaging/`. The marker comes from
the directory, and a contract test fails on any `tests/test_*.py` at the root. Please add new tests
there, through the public API (`CuemsScript.save` / `load` / `from_json`): the deprecated
`XmlReaderWriter` / `CuemsParser` are removed in `v0.1.2`, and a test that imports them is now
required to say so (`pytest.mark.expects_deprecation`).

## 5. The pre-publication gate

`tests.yml` gains a dispatchable gate (`gh workflow run tests.yml --ref <ref> -f siblings_ref=<tag>`).
It runs the cross-repository tests with the siblings checked out, and builds the `.deb` in
`debian:bookworm`. Publication of `0.1.1` waits for a green run on the post-merge
`feat/xml-refactor` head with every sibling at its reconciled tag.
