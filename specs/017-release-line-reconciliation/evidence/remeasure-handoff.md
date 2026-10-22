# Re-measure before the cleanup (T069, FR-004)

2026-10-21T22:24:59Z, after `git fetch --all --tags --prune`, on `cb66cc3`.

| Check | Result |
|---|---|
| `origin/debian/bookworm` | `398a9cf`, **unmoved** since 2026-10-17 |
| `origin/main` | `23e4752`, **unmoved** |
| `HEAD..origin/debian/bookworm` / `HEAD..origin/main` | **0 / 0** |
| new `debian/*` or `v*` tags | none (newest: `debian/0.1.0rc17`, `v0.1.0rc17`) |
| stray sweep (`rev-list --no-merges <ref> ^HEAD`) | `origin/feat/faders`, `origin/options`, `origin/parser-fixxes` (excluded, research R2), `origin/gh-pages` (not source). **`v0.0.9rc7` no longer appears**: M3 made it an ancestor (Q9) |
| PyPI 0.1.0 line (JSON API) | rc1–rc4, rc7, rc8, rc10, rc11, rc14–rc16: **unchanged**. `RELEASED_PYPI` stands, and rc17 keeps its "Debian only" mark |

**No delta, so there is nothing to merge before the cleanup.** T081 re-checks once more after the
cleanup's test moves (checklist CHK020).

# Re-measure after the cleanup (T081, checklist CHK020)

2026-10-21T22:04:53Z (NTP-synchronised clock), after `git fetch origin --tags --prune`, on `812fe9b`.

| Check | Result |
|---|---|
| `origin/debian/bookworm` | `398a9cf` (committed 2026-10-15), **unmoved** |
| `origin/main` | `23e4752`, **unmoved** |
| `HEAD..origin/debian/bookworm` / `HEAD..origin/main` | **0 / 0** |
| newest tags | `debian/0.1.0rc17`, `v0.1.0rc17`: none new |
| stray sweep (`rev-list --no-merges <ref> ^HEAD`, every remote branch) | `origin/feat/faders`, `origin/options`, `origin/parser-fixxes` (1 each, excluded, research R2), `origin/gh-pages` (not source): **unchanged** |
| PyPI 0.1.0 line (JSON API) | rc1–rc4, rc7, rc8, rc10, rc11, rc14–rc16: **unchanged**, so rc17 keeps its "Debian only" mark |
| root `tests/test_*.py` | none, so there is nothing to `git mv` |

**No delta after the cleanup either.** Nothing is merged, and T073's layout test and T065 need no re-run.
The suite at `812fe9b` was run anyway for US7: 3936 passed, 114 skipped, 2 xfailed, **0 failed**.

**A note on this file's timestamps.** The box's clock ran fast for part of the session, and NTP stepped it
back between `cb66cc3` (committer date 2026-10-22T00:24:00+02:00) and its own child `9c02cdc`
(2026-10-21T23:36:26+02:00), by at least 48 minutes. So the T069 time above (22:24:59Z), and the
"2026-10-22" dates in `upstream-reports/` and `suite-verdict.md`, came from the fast clock. They are
left as recorded. Only the order of events is evidence here, and git's parent links fix that.
