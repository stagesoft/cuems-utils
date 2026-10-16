# Repository record — cuems-power-bridge

Fields per [data-model.md](../data-model.md). Filled as the phase runs.

| Field | Value |
|---|---|
| start_commit | `dd1256f` |
| measured_versions | `debian/changelog:1` `0.3.1-1 unstable` (never tagged or shipped); `pyproject.toml:7` `0.3.1`; `src/cuemspowerbridge/__init__.py:5` **`0.2.0`** ⚠ drift |
| release_line / released_high_water | `origin/main` → **`0.3.2-2`** (tags `v0.3.1-2`, `v0.3.2-1` 2026-10-15, `v0.3.2-2` 2026-10-16), none containing the refactor; `0.4.0-1 gt 0.3.2-2` ✅ (target moved twice: research R2, R2a) |
| release_gap_start | **59 behind** / 47 ahead of `origin/main` (26 on 2026-10-12, 41 on 2026-10-15); absent: `0.3.0-7`, `-8`, `-9`, `-10`, `-11`, `0.3.1-2`, `0.3.2-1`, `0.3.2-2` |
| target | **`0.4.0-1`** (maintainer, 2026-10-16) |
| bump_commit (replaced) | `f0da390` on `feat/xml-refactor` (signed, unpushed) |
| release_gap_bump | 59 behind / 48 ahead of `origin/main` at `f0da390` — **NOT YET RECONCILED** (incl. `CACHEDIR.TAG`, 0.3.0-8) |
| relations | rows 20–24: utils `(>= 0.1.0rc16)`→`(>= 0.1.1)`, `(<< 0.1.1~)`→`(<< 0.1.2~)`, common `(>= 1.3.0-23)`→`(>= 1.3.1~)`, `Breaks: cuems-common (<< 1.3.0-23)`→`(<< 1.3.1~)`, pyproject `>=0.1.1,<0.1.2`; with row 5 (the common side, `<< 0.4.0~`) 29/29 verdicts OK (`relation-verdicts-progress-5.txt`) |
| literals_reviewed | `tests/`: none. `debian/rules:10-12` comment and `:28` build message → moved (text only; also corrected the stale "newest on PyPI is 0.1.0rc14"). Folded `0.3.1-1` bullet naming `(>=0.1.0rc16,<0.1.1)`/`(<< 1.3.0-23)` → corrected in place |
| suite_start | 276 passed (`suite-start.txt`) |
| suite_A / suite_B | pyenv 3.11.9 `.venv`, both arms on `cuemsutils 0.1.1` (`.016-utils-bump` @ `67df8bc`); 3×interleaved: A (`dd1256f`) 276p, 43.23–43.51 s; B (`f0da390`) 276p, 43.39–43.63 s. Identical (warning counts 102/112 vary run to run) |
| library_effect | none — start run (old library) 276 = arm A (new library) 276 |
| reruns | |
| new_failures | none |
| build | `cuems-power-bridge_0.4.0-1_all.deb` (bookworm), Version = changelog, Depends `cuems-utils (>= 0.1.1), (<< 0.1.2~), cuems-common (>= 1.3.1~)`, Breaks `cuems-common (<< 1.3.1~)`; `home = /usr/bin`; its `debian/rules` built the wheel from `CUEMS_UTILS_SRC` inside the chroot (research R15) ✅; no `CACHEDIR.TAG` in the .deb |
| demo | none exists; relations checked by `dpkg --compare-versions` only (FR-011) |
| tag_message | `../.xml-refactor-tag-messages/cuems-power-bridge.txt`. Verified: `Tag:` = `f0da390…` = head; subject `0.4.0-1` = changelog head; pairs common `fb450b5`, nodeconf `334db12` match their messages; others pending (T121) |
| go_ahead | ✅ 2026-10-16 — maintainer: "go" |

## Re-run 3 (2026-10-16, after the cuems-utils bump `67df8bc` → `8f6eede` for frontend `0.2.0`)

All re-ran against `8f6eede` (FR-021): 121/121 verdicts; six bookworm builds OK; suites ×3
interleaved unchanged (utils B clean, A only the expected `test_ordering_premise`; common 101→103/3;
nodeconf 206+15; power-bridge 276; editor 271/3; engine 885+32, B +1 lock xfail); frontend build OK,
`test:ci` 288 ×6; demos common 13/13 (`fb450b5`), nodeconf 9/9. Evidence: the newest-suffixed files
in each `evidence/<repo>/`.
