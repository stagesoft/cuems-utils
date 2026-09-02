# Baseline — feature 008

Measured on branch `008-rebuild-extension`, before any Phase 1 edit, under **pyenv 3.11.9**
(method: research R10 / `quickstart.md` — median of five warm runs, fresh process per measurement,
except the suite figure which is one `hatch test` invocation).

## Suite (T002)

```
PYENV_VERSION=3.11.9 pyenv exec hatch test -py 3.11
```

```
2393 passed, 94 skipped, 2 xfailed, 334 warnings in 59.49s
```

Per-test figure (over the 2393 passed tests, matching 007's method): 59.49s / 2393 = **24.86 ms/test**.
This matches CLAUDE.md's recorded 007 baseline (24.79 ms/test, 2026-08-24) to within measurement noise —
confirms this branch has not drifted from 007's landing.

**Budget (FR-PERF-002)**: ≤ 110% of 24.79 ms/test = **≤ 27.27 ms/test**.

## Load-time measurements (T001)

### Show document — the corpus's largest

Fixture: `tests/data/corpus/cuems-engine/projects/complex_test/script.xml` (24,183 B), per research R10
(NOT `fade_showcase.xml`, which cannot make the 50 ms absolute cap bind).

```
runs (ms): [18.123, 19.619, 17.994, 17.683, 17.768]
median: 17.994 ms
```

(Indicative pre-feature figure in quickstart.md, measured on Python 3.13, was 11.76 ms — this is the
3.11.9 figure and is the one the budget below is measured against.)

**Budget**: ≤ 200% of 17.994 ms (35.99 ms) **and** ≤ 50 ms absolute → effective cap **35.99 ms**.

### Configuration domains

Measured via `tests/data` fixtures (`CUEMS_CONF_PATH=tests/data`), same method.

| Domain | Fixture | Median load (ms) | Budget (≤110%) |
|---|---|---|---|
| `network_map` | `tests/data/network_map.xml` | 9.277 | 10.20 |
| `settings` (system) | `tests/data/settings.xml` | 20.575 | 22.63 |
| `project_mappings` (default) | `tests/data/default_mappings.xml` | 22.523 | 24.78 |
| `project_settings` | constructed minimal fixture — the corpus's only `project_settings.xml` (`tests/data/corpus/cuems-engine/project_settings.xml`) is empty (zero `<setting>` elements) and under-represents load cost, so a one-setting fixture matching `project_settings.xsd` was built for measurement only and discarded after use | 6.504 | 7.15 |

**Note on `project_settings`**: `ConfigManager.load_project_settings`'s `project_conf = conf.get_dict()`
is a pre-existing, deliberately-preserved defect (`main_key` mismatch, see `ConfigManager.py:350-368`) —
it always yields `{}`. The load-time figure above measures the reader (`ProjectSettings.__init__` →
`.read()`), which is what ITEM B's `save()` work and ITEM E's strict-load work both touch, independent
of that dict-flattening defect.

## Phase gate (T083/T084)

Recorded once Phase 1 (ITEMs A–D) is complete and green — see plan.md D30 / quickstart.md "Phase gate
check".
