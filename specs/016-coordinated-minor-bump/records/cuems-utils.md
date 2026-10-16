# Repository record — cuems-utils

Fields per [data-model.md](../data-model.md). Filled as the phase runs.

| Field | Value |
|---|---|
| start_commit | `b83d5c2 (branch 016 at b65a213, docs only)` |
| measured_versions | `src/cuemsutils/__init__.py:4` `0.1.0rc16`; `debian/changelog:1` `0.1.0rc16 UNRELEASED` (native) |
| release_line / released_high_water | `origin/debian/bookworm` → **`0.1.0rc17`** (also `origin/release/0.1.0rc17`); `0.1.1 gt 0.1.0rc17` ✅; release line not an ancestor |
| release_gap_start | **77 behind** / 263 ahead of `origin/debian/bookworm` (73 on 2026-10-12); absent: `0.1.0rc16+1`, `0.1.0rc17` |
| target | `0.1.1` (native) |
| bump_commit (replaced) | **`8f6eede`** on `016-coordinated-minor-bump` (signed, unpushed). Replaced: `055ec52` → `67df8bc` (2026-10-16, power-bridge `0.3.2-1` → `0.4.0-1`, research R2a); `67df8bc` → `8f6eede` (2026-10-16, frontend `0.1.0` → `0.2.0`, research R2b). Each amend touched only `CHANGELOG.md` and `test_release_matrix.py`'s `PINNED`, and each re-ran every dependent build, suite and demo (FR-021) |
| release_gap_bump | 77 behind / 264 ahead of `origin/debian/bookworm` at `055ec52`; absent: `0.1.0rc16+1`, `0.1.0rc17` — **NOT YET RECONCILED** |
| relations | row 1: `debian/control` `Breaks: cuems-common (<< 1.3.0-23~)` → `(<< 1.3.1~)`; verdicts 6/6 OK (`evidence/relation-verdicts-progress-1.txt`) |
| literals_reviewed | `v0.1.1` → `v0.1.2` at 13 sites (src 9, README, docs, CHANGELOG, debian/changelog:94-95); 3 test pins (one now derived from `REMOVAL_RELEASE`); old-filename citations re-pointed in 13 files, 014/015 left frozen; supersession notices on 12 docs (T020) |
| suite_start | 3756 passed, 114 skipped, 2 xfailed, test.py3.11 hatch (`suite-start.txt`) |
| suite_A / suite_B | hatch, uv-managed CPython (matrix). 3.11 ×3 interleaved: A (`b83d5c2`, `.016-utils-start`) 3756p/114s/2xf, 31.3–34.0 s; B (`055ec52`) 3754p/116s/6xf, 31.7–31.8 s. 3.12 and 3.13 once each. Count deltas (−2 passed, +2 skipped, +4 xfailed) = the renamed release-matrix file exactly |
| library_effect | n/a (this is the library) |
| reruns | 2026-10-16, after the R2a amend: build (`bookworm-build-2.txt`), suites 3.11 ×3 interleaved (`suite-*-2.txt`) — results below |
| new_failures | **none attributable**. B-only id `test_descriptor_laziness[settings]` (3.11 run 1) is the open ~2 ms first-call flake recorded in CLAUDE.md; A hit `[project_mappings]` of the same test; alone on B it fails 1/5. Both arms: remint ceiling/throughput timing flakes; on 3.13 `test_public_api_matches_the_snapshot` fails in **both** arms (pre-existing on 3.13) |
| build | `cuems-utils_0.1.1_amd64.deb` (bookworm, Python 3.11.2, dh-virtualenv 1.2.2-1.3), Version 0.1.1 = changelog, `Breaks: cuems-common (<< 1.3.1~)`; **in the .deb**: `home = /usr/bin`, `bin/python -> ../../../bin/python3`; no `CACHEDIR.TAG` (`evidence/cuems-utils/bookworm-build.txt`) |
| demo | none exists for cuems-utils; row 1 checked by `dpkg --compare-versions` only (FR-011) |
| tag_message | `../.xml-refactor-tag-messages/cuems-utils.txt` — **draft** (Tag/pairs pending T121) |
| go_ahead | ✅ 2026-10-15 — maintainer: "cuems-power-bridge takes 0.3.2-1. go with Phase 4" (R2 confirmed) |

## Notes (bump half)

- **mypy**: `uvx hatch run types:check` reports **283 errors on both `b83d5c2` and `055ec52`**.
  The error sets are identical once line numbers are ignored; the only difference is the two errors
  that moved with the renamed test file. Feature 015's recorded "≤ 72" is not reproducible with
  this command on this box: most errors are `import-not-found` for `pytest` inside the `types`
  environment. **SC-QUALITY-001 holds** ("does not rise"). ruff: 0.
- **Working-tree suite (T022)**: 3753 passed, 116 skipped, 6 xfailed, 1 failed:
  `test_estimate_tolerance[2]`, the timing flake CLAUDE.md records under contention. Alone: 10/10
  passed three times.
- **Release-matrix fail-before**: `evidence/cuems-utils/release-matrix-fail-before.txt` —
  `test_this_repository_is_at_0_1_1` FAILS at `b83d5c2`, passes at the bump.
- **Build source**: built from the clean bump worktree `.016-utils-bump`, not the main checkout,
  which holds untracked 016 records.

## Re-run after the R2a amend (2026-10-16)

- **Build** (`bookworm-build-2.txt`): `cuems-utils_0.1.1_amd64.deb` from `67df8bc`, OK, `home = /usr/bin`.
- **Suites** (`suite-A-2.txt`, `suite-B-2.txt`, 3.11 ×3 interleaved): A 3755p/114s/2xf, B 3753p/116s/6xf,
  31.1–31.8 s. **One failure in both arms**: `test_ordering_premise.py::test_cuems_common_still_configures_after_this_package`.
  It reads the **sibling** `../cuems-common/debian/control` and pinned the literal
  `cuems-utils (>= 0.1.0rc16)`, so it broke when `cuems-common` was bumped (`901a5ba`), in both
  arms because both read the same sibling tree. My R11 grep missed it. It is a sibling-head
  assertion, so under analyze A1 / FR-013 its fix (`>= 0.1.1`) lands in the **record commit**, made
  in the working tree now. With the fix: 2 passed.
- **Same class, found while fixing**: `test_lifecycle_chroot.py` expected the sibling `cuems-common`
  to install as `1.3.0-23`, and upgraded from a `1.3.0-22` stub. Now `1.3.1-1`, and the stub is
  **`1.3.0-25`**, so the custody-transfer test exercises `rm_conffile`'s new prior-version `1.3.1~`
  (with `1.3.0-22` the old `1.3.0-23~` would have passed as well). Also for the record commit.
- **Chroot lifecycle tests, run for real** (`CUEMS_CHROOT_TAR` = bookworm with `python3,
  python3-systemd, python3-daemon`, per 011's quickstart): **23 passed, 1 failed**. Custody transfer
  in both orders from `1.3.0-25` ✅. The failure, `test_fresh_install_loads_and_is_unique` ("sentinel
  token still present" in `/etc/cuems/{project_mappings,network_map,settings}.xsd`), **fails
  identically with the start tree's `0.1.0rc16` `.deb`**. Feature 011's test greps every
  `/etc/cuems` file for the sentinel, and feature 012 later made the three XSDs declare it as an
  allowed enumeration value. It predates this feature; recorded, not fixed here.

## Re-run 3 (2026-10-16, after the cuems-utils bump `67df8bc` → `8f6eede` for frontend `0.2.0`)

All re-ran against `8f6eede` (FR-021): 121/121 verdicts; six bookworm builds OK; suites ×3
interleaved unchanged (utils B clean, A only the expected `test_ordering_premise`; common 101→103/3;
nodeconf 206+15; power-bridge 276; editor 271/3; engine 885+32, B +1 lock xfail); frontend build OK,
`test:ci` 288 ×6; demos common 13/13 (`fb450b5`), nodeconf 9/9. Evidence: the newest-suffixed files
in each `evidence/<repo>/`.

## Record half (Phase 10, 2026-10-16)

- **T117**: `test_siblings_at_feat_xml_refactor` added; with the two sibling-literal fixes
  (`test_ordering_premise.py` `>= 0.1.1`; `test_lifecycle_chroot.py` `1.3.1-1`, stub `1.3.0-25`).
  Working-tree suite: **3760 passed, 116 skipped, 6 xfailed, 0 failed**; ruff 0.
- **T115**: final verdicts **121/121** (`evidence/relation-verdicts.txt`). **T116**: re-run 3's B arms
  (`evidence/suite-final.txt`). **T122**: nothing pushed, no tag moved (`evidence/no-push-no-tag.txt`).
  **T123**: all version sites (`evidence/version-sites.txt`).
- **T118**: the planning document is updated with its status, corrections and the owed list. It is not
  deleted (FR-017). **T119**: `CLAUDE.md`'s `debian/bookworm` / `packaging-rc14` claim is corrected,
  and a Recent Changes entry is added.
- Evidence housekeeping: `evidence/cuems-engine/suite-start.txt`, the environmental first start run,
  4.7 MB of 863 identical tracebacks, is **trimmed** to its header, distinct errors and summary,
  with a note giving the original size and hash.

## Final stop and handover (T125–T127, 2026-10-16)

- **go_ahead (T125)**: ✅ 2026-10-16, maintainer: "go and merge the spec branch into
  feat/xml-refactor when all tasks are done".
- **T126**: `.016-utils-start` and `.016-utils-bump` worktrees removed and pruned; the
  `.016-utils-bump-clone` and `.016-native` scratch directories deleted. Sibling venvs (excluded via
  `.git/info/exclude`) kept, and re-pointed with `pip install --no-deps -e` at
  `/disk/Projects/StageLab/cuems-utils`. All seven trees clean.
- **Merge**: on the maintainer's instruction, `016-coordinated-minor-bump` is merged into this
  repository's `feat/xml-refactor` with a signed `--no-ff` merge commit, following the 011/012/014/015
  precedent. **Not pushed.** The `cuems-utils` candidate tag message keeps the decided tag point, the
  record commit (analyze I2). The merge commit is named in the message as the merge into
  `feat/xml-refactor`, so the maintainer can choose either; tagging the merge commit would match
  the siblings, whose tags sit on their `feat/xml-refactor` heads.
- **Handover (T127)**, owed by the maintainer:
  1. tell the power-bridge and frontend maintainers the refactor's numbers (`0.4.0-1`, `0.2.0`);
  2. rule 4, release-line reconciliation, re-running `tools/verdicts.sh` after each merge;
  3. re-cut the seven tags from `../.xml-refactor-tag-messages/` (`README.md`; `cuems-utils` last),
     then §11.1 validation on the re-cut tags;
  4. the `cuems-engine` `poetry.lock` relock (its strict-xfail test flags it), and engine CI under rule 5;
  5. pushing the eight local commits (seven repositories, plus this merge) and the tags;
  6. publication.
