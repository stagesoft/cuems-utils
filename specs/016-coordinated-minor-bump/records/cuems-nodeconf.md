# Repository record — cuems-nodeconf

Fields per [data-model.md](../data-model.md). Filled as the phase runs.

| Field | Value |
|---|---|
| start_commit | `82b0a69` |
| measured_versions | `debian/changelog:1` `0.1.1-1 UNRELEASED` (already the target); `pyproject.toml:7` `0.1.0` ⚠ drift; no `__version__` under `cuemsnodeconf/` |
| release_line / released_high_water | `origin/rc_1` → `0.1.0-9`; `0.1.1-1 gt 0.1.0-9` ✅ |
| release_gap_start | 0 behind / 84 ahead of `origin/rc_1` — **reconciled** (merged 2026-10-13) |
| target | `0.1.1-1` (header kept, FR-003 third rule) |
| bump_commit (replaced) | `334db12` on `feat/xml-refactor` (signed, unpushed) |
| release_gap_bump | 0 behind / 85 ahead — reconciled |
| relations | rows 15–19: utils `(>= 0.1.0rc16)`→`(>= 0.1.1)`, `(<< 0.1.1~)`→`(<< 0.1.2~)`, common `(>= 1.0.0)`→`(>= 1.3.1~)`, `Breaks: cuems-common (<< 1.3.0-23~)`→`(<< 1.3.1~)`, pyproject `>=0.1.1,<0.1.2`; 23/23 verdicts OK (`relation-verdicts-progress-3.txt`) |
| literals_reviewed | changelog top-entry bullets naming `1.3.0-23`, `<< 1.3.0-23~`, `>= 0.1.0rc16, << 0.1.1~`, "inside 0.1.0rc16" → **corrected in place** (unreleased entry); `test_library_prerequisite.py` docstring → note added (floor now expresses both gates), test kept; `test_service_record.py:149` "predates cuems-common 1.3.0-23" → **kept, history**; demo + stub → moved (T056) |
| suite_start | 206 passed + yardstick 15 passed (`suite-start-2.txt`; run 1: `zeroconf` missing from venv, 20 collection errors) |
| suite_A / suite_B | pyenv 3.11.9 `.venv`, both arms on `cuemsutils 0.1.1` (`.016-utils-bump`); 3×interleaved: A (`82b0a69`) 206p + yardstick 15p, 33.34–33.35 s; B (`334db12`) 206p + 15p, 33.35–33.37 s. Identical |
| library_effect | none — start run (old library) 206 + 15 = arm A (new library) 206 + 15 |
| reruns | 2026-10-16, after the R2a amends (utils `67df8bc`, common `fb450b5`); `334db12` itself unchanged: build (`bookworm-build-2.txt`), suites (`suite-*-2.txt`), demo (`release-gate-demo-2.txt`, `COMMON_NEW=fb450b5`) — results below |
| new_failures | none |
| build | `cuems-nodeconf_0.1.1-1_all.deb` (bookworm), Version = changelog, Depends `cuems-utils (>= 0.1.1), (<< 0.1.2~), cuems-common (>= 1.3.1~)`, Breaks `cuems-common (<< 1.3.1~)`; `home = /usr/bin` (pass 1) |
| demo | `release-gate-demo.txt`: **9/9 match**, all packages REAL (old nodeconf `0.1.0-9` built from `origin/rc_1` `23c5b31`; common `901a5ba` and `v1.3.0-25`), clean evidence; library wheel built from `.016-utils-bump-clone` @ `055ec52`. ⚠ Run 1 exited 2 before doing anything: the script requires `[ -d "$UTILS/.git" ]`, which a `git worktree` (where `.git` is a file) fails, so a clean **clone** at the same commit was used (pre-existing limitation; recorded, not changed). ⚠ The evidence header labels `COMMON_OLD` with `git rev-parse v1.3.0-25` = the annotated **tag object** `ca8ff3d`; the commit is `6a295ba` (`^{commit}`). Label only: `git archive` built the right tree. A pre-existing script defect, recorded |
| tag_message | `../.xml-refactor-tag-messages/cuems-nodeconf.txt`. Verified: `Tag:` = `334db12…` = `feat/xml-refactor`; subject `0.1.1-1` = changelog head; pairs with `cuems-common 901a5ba` match its message; others pending (T121) |
| go_ahead | ✅ 2026-10-16 — maintainer: "go" (script defects recorded, not fixed) |

## Re-run after the R2a amends (2026-10-16; this repository unchanged at `334db12`)

- **Build** (`bookworm-build-2.txt`): OK with the wheel from `67df8bc`, `home = /usr/bin`.
- **Suites** (`suite-*-2.txt`): A and B 206 + 15, ×3 interleaved, identical.
- **Demo** (`release-gate-demo-2.txt`): **9/9 match**, `COMMON_NEW=fb450b5`, all packages real.

## Re-run 3 (2026-10-16, after the cuems-utils bump `67df8bc` → `8f6eede` for frontend `0.2.0`)

All re-ran against `8f6eede` (FR-021): 121/121 verdicts; six bookworm builds OK; suites ×3
interleaved unchanged (utils B clean, A only the expected `test_ordering_premise`; common 101→103/3;
nodeconf 206+15; power-bridge 276; editor 271/3; engine 885+32, B +1 lock xfail); frontend build OK,
`test:ci` 288 ×6; demos common 13/13 (`fb450b5`), nodeconf 9/9. Evidence: the newest-suffixed files
in each `evidence/<repo>/`.
