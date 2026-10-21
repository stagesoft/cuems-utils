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
