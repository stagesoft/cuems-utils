# Suite verdict (T065, SC-003)

## 3.11: three runs, interleaved A/B/A/B/A/B (2026-10-22)

Arm A = `5e4c637`, arm B = the 017 head `8f210fd`. Both are worktrees under the scratchpad, with the
sibling symlinks in place, so both run the 22 sibling-reading tests (`suite-A-1b.md`). Interpreter:
hatch `test.py3.11` (uv CPython 3.11.9, Clang). `CUEMS_CONF_PATH` unset.

| Run | Arm A | Arm B |
|---|---|---|
| 1 | 3785 p / 7 f / 112 s / 2 xf, 33.73 s (load 2.95) | 3915 p / 7 f / 114 s / 2 xf, 39.04 s (load 2.39) |
| 2 | 3785 p / 7 f / 112 s / 2 xf, 33.25 s (load 1.71) | 3915 p / 7 f / 114 s / 2 xf, 36.37 s (load 1.56) |
| 3 | 3785 p / 7 f / 112 s / 2 xf, 33.08 s (load 3.02) | 3915 p / 7 f / 114 s / 2 xf, 36.38 s (load **8.06**) |

- **B's failure set ⊆ A's.** It is the **same 7** in every run, and nothing is in B that is not in A
  (`comm` of the sorted sets: empty both ways). The 7 are the pre-existing, environmental set:
  `test_migration_guide::test_the_coupled_engine_version_resolves` and six
  `test_release_matrix::test_siblings_at_their_candidate_tags[*]` (`XPASS(strict)` since the 016
  re-cut).
- The `project_mappings` laziness flake did not appear in any of the six runs.
- B runs **132 more tests** (+130 passed, +2 skipped: the two built-`.deb` checks, which skip without
  a `.deb` beside the checkout).

## 3.12 and 3.13, once each, on the head (hatch `test.py3.12` / `test.py3.13`)

| Interpreter | Result | Beyond the 7 |
|---|---|---|
| 3.12 | 3915 p / **7 f** / 114 s / 2 xf | none |
| 3.13 (3.13.5) | 3913 p / **9 f** / 114 s / 2 xf | `test_public_api_surface.py::test_public_api_matches_the_snapshot` and `test_remint_fixture_ceiling.py::test_the_named_fixture_is_rewritten_within_the_ceiling` |

**Both 3.13 extras are pre-existing.** They fail on **arm A under 3.13 too** (measured, same
interpreter). The snapshot failure is the one spec Q11 records, which is why CI gates on 3.11 and
keeps 3.13 informational. The remint ceiling test is one of the timing tests CLAUDE.md records as
flaky under contention, and it failed 3/3 re-runs at load 10.8. Neither is caused by 017.

**SC-003: met.** On the same host, the 017 head has no failure that `5e4c637` lacks, on 3.11 (×3),
3.12 and 3.13.
