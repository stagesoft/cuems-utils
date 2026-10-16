# Repository record — cuems-editor

Fields per [data-model.md](../data-model.md). Filled as the phase runs.

| Field | Value |
|---|---|
| start_commit | `e5e6ac1` |
| measured_versions | `debian/changelog:1` `0.1.0rc1-4 UNRELEASED`; `pyproject.toml:7` and `src/cuemseditor/__init__.py:4` `0.1.0rc1` (`__init__` is the hatch version source); `CHANGELOG.md` top `## 0.1.0rc1 — 2026-05-26` (released, dated) |
| release_line / released_high_water | `origin/debian/bookworm` → `0.1.0rc1-7` (also `release/0.1.0rc1-7`); `0.1.1-1 gt 0.1.0rc1-7` ✅ |
| release_gap_start | **43 behind** / 62 ahead of `origin/debian/bookworm`; absent: `0.1.0rc1-5`, `-6`, `-7` |
| target | `0.1.1-1` (fold `0.1.0rc1-4`) |
| bump_commit (replaced) | `a2431f0` on `feat/xml-refactor` (signed, unpushed) |
| release_gap_bump | 43 behind / 63 ahead at `a2431f0` — **NOT YET RECONCILED** |
| relations | rows 11–14: utils `(>= 0.1.1)`, `(<< 0.1.2~)`; common `(>= 1.0.0)`→`(>= 1.3.1~)`; pyproject `cuemsutils>=0.1.1,<0.1.2`. 21/21 verdicts OK. **With this commit all 121 verdicts across rows 1–25 pass** (`relation-verdicts-progress-7.txt`, exit 0) |
| literals_reviewed | folded rc1-4 bullet naming `(>= 0.1.0rc16), (<< 0.1.1~)` → corrected in place; `tests/packaging/bookworm-build.sh:16` PyPI note → moved; `tests/fixtures/README.md:11` provenance "cuemsutils 0.1.0rc16 @ 6213b16" → **kept, history**; `CHANGELOG.md` → new `0.1.1 — Unreleased` section above the released `0.1.0rc1` (not folded: it is dated and released) |
| suite_start | 271 passed, 3 skipped (`suite-start.txt`) |
| suite_A / suite_B | pyenv 3.11.9 `.venv`, `cuemsutils 0.1.1`; 3×interleaved: A (`e5e6ac1`) 271p/3s, 6.40–6.44 s; B (`a2431f0`) 271p/3s, 6.34–6.38 s. Identical |
| library_effect | none — start (old library) 271/3 = arm A |
| reruns | — |
| new_failures | none |
| build | `cuems-editor_0.1.1-1_all.deb` (bookworm), Depends `cuems-utils (>= 0.1.1), (<< 0.1.2~), cuems-common (>= 1.3.1~)`, `home = /usr/bin` (`bookworm-build.txt`); corroborated by its own `tests/packaging/bookworm-build.sh` (`bookworm-build-own-script.txt`), same result |
| demo | none exists; relations by `dpkg --compare-versions` only (FR-011) |
| tag_message | `../.xml-refactor-tag-messages/cuems-editor.txt` (first tag). Verified: `Tag:` = `a2431f0…` = head; pairs common/nodeconf/power-bridge/engine match; utils/frontend pending (T121) |
| go_ahead | ✅ 2026-10-16 — maintainer: "go" |

## Re-run 3 (2026-10-16, after the cuems-utils bump `67df8bc` → `8f6eede` for frontend `0.2.0`)

All re-ran against `8f6eede` (FR-021): 121/121 verdicts; six bookworm builds OK; suites ×3
interleaved unchanged (utils B clean, A only the expected `test_ordering_premise`; common 101→103/3;
nodeconf 206+15; power-bridge 276; editor 271/3; engine 885+32, B +1 lock xfail); frontend build OK,
`test:ci` 288 ×6; demos common 13/13 (`fb450b5`), nodeconf 9/9. Evidence: the newest-suffixed files
in each `evidence/<repo>/`.
