# Arm A (`5e4c637`), re-run **beside the siblings** (supersedes suite-A-1.txt as the baseline)

`tests/support/sibling_tags.py` finds the sibling checkouts at `Path(__file__).parents[3]`.

- For a worktree under the session scratchpad, that is the scratchpad directory. With no siblings
  there, the **22 sibling-reading tests skip**. That happened in `suite-A-1.txt` (134 skipped)
  and in the M1 run (`suite-M1.txt`, also in a scratchpad worktree).
- In the real checkout `/disk/Projects/StageLab/cuems-utils`, the siblings are found and those
  tests run.

To compare like with like, the scratchpad got symlinks to the real siblings
(`<scratchpad>/cuems-{common,nodeconf,power-bridge,engine,editor,frontend}` and
`libmtcmaster` → `/disk/Projects/StageLab/…`). No sibling repository was touched. Arm A was then
re-run (2026-10-21, hatch `test.py3.11`, CPython 3.11.9):

**3785 passed, 7 failed, 112 skipped, 2 xfailed** (33.86 s → 8.95 ms/test)

The 7 failures are **pre-existing and environmental**: they come from the siblings' and tags'
current state, not from this library's code.

| Test | Why it fails on arm A too |
|---|---|
| `contract/test_migration_guide.py::test_the_coupled_engine_version_resolves` | compares the version a migration guide names with `../cuems-engine`'s **current checkout**, which is on its own `009-release-line-reconciliation` branch at `0.1.1` |
| `packaging/test_release_matrix.py::test_siblings_at_their_candidate_tags[*]` (×6) | `XPASS(strict)`: the marker says "until the maintainer re-cuts `xml-refactor-merge-candidate` (016)", and the re-cut happened on 2026-10-16 |

**From here on, arm A means this run.** Every later arm-A suite (T065) runs with the sibling
symlinks in place, and the 017-head runs happen in the real checkout. A failure on the 017 head
counts as 017's only if it is not in this set (SC-003).
