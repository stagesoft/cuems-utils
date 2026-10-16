# Repository record — cuems-engine

Fields per [data-model.md](../data-model.md). Filled as the phase runs.

| Field | Value |
|---|---|
| start_commit | `7d0bda3` |
| measured_versions | `debian/changelog:1` `0.1.0rc2-3 bookworm` (**released**, on `origin/debian/bookworm`); `pyproject.toml:11` and `src/cuemsengine/__init__.py:5` `0.1.0rc7` ⚠ drift; **`CHANGELOG.md`'s top `## v…` header is a third site** (`test_version_single_source.py` requires it = `__version__`), missed by research R5 |
| release_line / released_high_water | `origin/debian/bookworm` → `0.1.0rc6-5` (also `release/0.1.0rc6-5`, tag `v0.1.0rc6-5`); `0.1.1-1 gt 0.1.0rc6-5` ✅. `poetry check --lock` passes at start |
| release_gap_start | **119 behind** / 26 ahead of `origin/debian/bookworm` (FR-010a re-measured); absent: `0.1.0rc3-1`, `rc3-2`, `rc4-1`, `rc5-1`, `rc6-1`…`rc6-5` |
| target | `0.1.1-1` (new top entry above the released `0.1.0rc2-3`, FR-003 second rule) |
| bump_commit (replaced) | `e994a5e` on `feat/xml-refactor` (signed, unpushed) |
| release_gap_bump | 119 behind / 27 ahead at `e994a5e` — **NOT YET RECONCILED** (incl. `stop_project`, rc6-5); lock relock pending (FR-022) |
| relations | rows 6–10 + 25: utils `(>= 0.1.1)`, `(<< 0.1.2~)`; common `(>= 1.3.1~)`; `-mock` → `cuems-engine (>= 0.1.1)`; pyproject `>=0.1.1,<0.1.2`; **new** `libmtcmaster (>= 0.0.2-0)`; the comment above `Depends:` rewritten. 27/27 verdicts OK (`relation-verdicts-progress-6.txt`). `python3-pyossia` and the dev wheel unchanged |
| literals_reviewed | `test_mtclistener.py:167` "cuemsutils 0.1.0rc7's" → **kept, history**. `CHANGELOG.md` `## v0.1.0rc7 — UNRELEASED` (never released) → folded into `## v0.1.1 — UNRELEASED`, with its "0.1.0rc16's public API" corrected. New `tests/test_lock_is_current.py` (FR-022): strict xfail with `raises=AssertionError`; it finds `poetry` beside the interpreter; **XPASS(strict) before the bound moved** (`lock-test-before.txt`), xfail after |
| suite_start | pass 1 885 passed, pass 2 32 passed, real `pyossia` 2.0.0rc6+124.cuems.3 (`suite-start-2.txt`; run 1: `libmtcmaster.so.0` not on host — now from `.016-native` via `LD_LIBRARY_PATH`) |
| suite_A / suite_B | pyenv 3.11.9 `.venv-016`, real `pyossia 2.0.0rc6+124.cuems.3`, `cuemsutils 0.1.1` (`67df8bc`), native libs from `.016-native` via `LD_LIBRARY_PATH`; CI's two passes ×3 interleaved: A (`7d0bda3`) 885 + 32 (13.4–14.7 s + 7.6 s); B (`e994a5e`) 885 + 1 xfail (lock test) + 32 (13.4–15.2 s + 7.6 s). Within 115% |
| library_effect | none — start run (old library) 885 + 32 = arm A |
| reruns | — |
| new_failures | none (the B-only `test_lock_is_current` is the intended strict xfail) |
| build | `cuems-engine_0.1.1-1_all.deb` + `cuems-engine-mock_0.1.1-1_all.deb` (bookworm), Versions = changelog; engine Depends include `libmtcmaster (>= 0.0.2-0)`; mock Depends `cuems-engine (>= 0.1.1)`; `home = /usr/bin` |
| demo | none exists; relations by `dpkg --compare-versions` only (FR-011) |
| tag_message | `../.xml-refactor-tag-messages/cuems-engine.txt` (first tag). Verified: `Tag:` = `e994a5e…` = head; subject `0.1.1-1` = changelog head; pairs common/nodeconf/power-bridge match their messages; utils/editor/frontend pending (T121) |
| go_ahead | ✅ 2026-10-16 — maintainer: "go" |

## Re-run 3 (2026-10-16, after the cuems-utils bump `67df8bc` → `8f6eede` for frontend `0.2.0`)

All re-ran against `8f6eede` (FR-021): 121/121 verdicts; six bookworm builds OK; suites ×3
interleaved unchanged (utils B clean, A only the expected `test_ordering_premise`; common 101→103/3;
nodeconf 206+15; power-bridge 276; editor 271/3; engine 885+32, B +1 lock xfail); frontend build OK,
`test:ci` 288 ×6; demos common 13/13 (`fb450b5`), nodeconf 9/9. Evidence: the newest-suffixed files
in each `evidence/<repo>/`.
