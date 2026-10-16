# Repository record — cuems-common

Fields per [data-model.md](../data-model.md). Filled as the phase runs.

| Field | Value |
|---|---|
| start_commit | `e595e67` |
| measured_versions | `debian/changelog:1` `1.3.0-23 UNRELEASED` (no Python version in this repo) |
| release_line / released_high_water | `origin/debian/bookworm` → `1.3.0-25` (also `rc_1`, tag `v1.3.0-25` = `6a295ba`); `1.3.1-1 gt 1.3.0-25` ✅ |
| release_gap_start | **22 behind** / 41 ahead of `origin/debian/bookworm`; absent: `1.3.0-24`, `1.3.0-25` (a *different* `1.3.0-23` exists on both) |
| target | `1.3.1-1` |
| bump_commit (replaced) | **`fb450b5`** on `feat/xml-refactor` (signed, unpushed). Replaced: `901a5ba` (2026-10-16, FR-021 amend: `Breaks: cuems-power-bridge (<< 0.3.2~)` → `(<< 0.4.0~)`, research R2a; `2dd0f8d` was an intermediate amend with the stale message, never used) |
| release_gap_bump | 22 behind / 42 ahead at `901a5ba`; absent `1.3.0-24`, `1.3.0-25` — **NOT YET RECONCILED** |
| relations | rows 2–5: utils `(>= 0.1.0rc16)`→`(>= 0.1.1)`, `(<< 0.1.1~)`→`(<< 0.1.2~)`; `Breaks: cuems-nodeconf (<< 0.1.0-8)`→`(<< 0.1.1~)`, `cuems-power-bridge (<< 0.3.1-1)`→`(<< 0.3.2~)`; 19/19 verdicts OK (`relation-verdicts-progress-2.txt`). `:49 Suggests: cuems-power-bridge` unchanged on purpose |
| literals_reviewed | `test_version_bounds.py` lists + docstring → moved; `test_network_map_handover.py` `1.3.0-23~` → `1.3.1~` (moved with the scripts); `test_template_consumers.py:55` "retired in 1.3.0-23" → **kept, history**; demo script + both nodeconf stubs → moved (T040). **Found**: `rm_conffile` prior-version `1.3.0-23~` in preinst/postinst/postrm for `network_map.{xml,xsd}` and `99-cuems` → `1.3.1~` (released 1.3.0-23..25 still ship them as conffiles: the handover would be skipped and retired sudo rules left active) |
| suite_start | 101 passed, 3 skipped (`suite-start-2.txt`; run 1 failed collecting: `lxml` missing from venv) |
| suite_A / suite_B | pyenv 3.11.9 `.venv`; 3×interleaved: A (`e595e67`) 101p/3s, 0.81–1.02 s; B (`901a5ba`) 103p/3s, 0.83–0.97 s. +2 = longer bounds lists. Within 115% |
| library_effect | n/a — the suite does not import `cuemsutils` |
| reruns | 2026-10-16, after the R2a amends: verdicts (`relation-verdicts-progress-4.txt`), build (`bookworm-build-2.txt`), suites (`suite-A-2.txt`, `suite-B-2.txt`), demo (`release-gate-demo-2.txt`) — results below |
| new_failures | none |
| build | `cuems-common_1.3.1-1_all.deb` (bookworm), Version = changelog, Depends `cuems-utils (>= 0.1.1), (<< 0.1.2~)`, Breaks `cuems-nodeconf (<< 0.1.1~), cuems-power-bridge (<< 0.3.2~)`; no venv; clean evidence (`bookworm-build.txt`) |
| demo | `release-gate-demo.txt`, 13/13 match at clean `901a5ba`, `OLD_REF=v1.3.0-25`. G2–G4 (new): baseline owned `network_map.{xml,xsd}` as conffiles; after G1 they are not owned, the live map keeps its operator mark, and `99-cuems` (active before) is now an inert `99-cuems.dpkg-bak` with `99-cuems-avahi` in place; `visudo -c` OK. ⚠ Cosmetic: the baseline state line greps `99-cuems$`, which misses the checksum suffix, so it lists only the map files. The before/after `ls` shows `99-cuems` itself |
| tag_message | `../.xml-refactor-tag-messages/cuems-common.txt`. Verified: `Tag:` = `901a5ba` = `feat/xml-refactor`; subject `1.3.1-1` = changelog head. Pairs pending (T121) |
| go_ahead | ✅ 2026-10-16 — maintainer: "go" |

## Re-run after the R2a amend (2026-10-16, `fb450b5`)

- **Verdicts** (`relation-verdicts-progress-4.txt`): row 5 is now `<< 0.4.0~`, and refuses `0.3.0-11`,
  `0.3.1-1`, `0.3.1-2`, `0.3.2-1`, `0.3.2-2` and admits `0.4.0-1`.
- **Build** (`bookworm-build-2.txt`): OK, `Breaks: cuems-nodeconf (<< 0.1.1~), cuems-power-bridge (<< 0.4.0~)`.
- **Suites** (`suite-*-2.txt`): A 101p/3s, B 103p/3s, ×3 interleaved, no new failures.
- **Demo** (`release-gate-demo-2.txt`): **13/13 match** at clean `fb450b5`.
- The library's chroot custody test (see the cuems-utils record) passes against this package
  built from `fb450b5`, upgrading from a `1.3.0-25` stub in both orders.

## Re-run 3 (2026-10-16, after the cuems-utils bump `67df8bc` → `8f6eede` for frontend `0.2.0`)

All re-ran against `8f6eede` (FR-021): 121/121 verdicts; six bookworm builds OK; suites ×3
interleaved unchanged (utils B clean, A only the expected `test_ordering_premise`; common 101→103/3;
nodeconf 206+15; power-bridge 276; editor 271/3; engine 885+32, B +1 lock xfail); frontend build OK,
`test:ci` 288 ×6; demos common 13/13 (`fb450b5`), nodeconf 9/9. Evidence: the newest-suffixed files
in each `evidence/<repo>/`.
