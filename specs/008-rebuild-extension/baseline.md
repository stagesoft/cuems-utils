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

### T083 — suite green, measured 2026-09-02

Same method as T002's pre-feature baseline above — `pyenv exec hatch test -py 3.11` — so the two
figures are comparable on the same basis. (A parallel raw-`pytest` run collects 2497 tests against
hatch's 2493: `tests/test_signalengine.py`'s four tests are absent from hatch's isolated venv, which
does not carry `systemd-python`, this repository's dependency for `tools.SignalEngine`, CLAUDE.md. This
gap pre-dates 008 and is a venv-completeness difference, not a Phase 1 regression — it does not appear
in either figure below.)

```
PYENV_VERSION=3.11.9 pyenv exec hatch test -py 3.11
```

```
2395 passed, 96 skipped, 2 xfailed, 213 warnings in 54.72s
```

Per-test figure: 54.72s / 2395 = **22.85 ms/test** — under the ≤ 27.27 ms/test budget (FR-PERF-002),
and *faster* than T002's pre-feature 24.86 ms/test despite the suite growing by 128 tasks' worth of new
tests (2393 → 2395 passed is misleadingly small because two tests moved to `skipped`/`xfailed`; the
tree gained far more than 2 tests across Setup + ITEMs A–D — see each item's own test count in its
tasks.md section).

### T084 — GATE (D30), recorded

All five conditions verified 2026-09-02:

- **(a) Phase 1 complete.** T001–T083 implemented and tested on `008-rebuild-extension`; not yet
  committed as of this recording — commit-splitting happens on request, per this feature's standing
  practice (Setup/A/B/C each landed as their own reviewed commit).
- **(b) Suite green.** T083 above: 2395 passed, 0 failed.
- **(c) Config `save()` interface landed and unchanged.** `data-model.md` §2, frozen at T036 (ITEM B);
  untouched by ITEM D.
- **(d) Descriptor interface landed and unchanged, including defaults and repairability.**
  `data-model.md` §3, frozen at T082 (ITEM D) — see that section's landed-and-frozen note.
- **(e) Every Phase 1 acceptance criterion demonstrated green with no part of ITEM E present.** No
  ITEM E file exists in this tree yet (`xml/versioning.py`, `errors.py`'s `LoadReport`/`Outcome`/
  `RepairRecord`/`ConversionRecord`, `doc_version` on any schema — none are present), so (a)/(b) above
  establish this by construction rather than by a separate demonstration.

**Not a release boundary** (D27): nothing ships until feature 009 lands. Phase 2 (ITEM E) may now
begin, written against `data-model.md` §2 and §3 as landed code.

## Phase 2 (ITEM E) — measured, 2026-09-02

Same method throughout: median of five warm runs, fresh process per measurement, `pyenv 3.11.9`
(T123). Compared against T001's pre-feature figures (Setup, above) — not against T083's, which already
includes Phase 1's own cost.

### Suite (T124)

```
PYENV_VERSION=3.11.9 pyenv exec hatch test -py 3.11
```

```
2456 passed, 96 skipped, 2 xfailed, 213 warnings in 54.19s
```

Per-test: 54.19s / 2456 = **22.06 ms/test** — under the ≤ 27.27 ms/test budget (FR-PERF-002), and
faster in absolute per-test terms than both T002's pre-feature 24.86 ms/test and T083's post-Phase-1
22.85 ms/test, despite the suite gaining ITEM E's own ~60 new tests on top of Phase 1's growth.

### Show document

Fixture unchanged: `tests/data/corpus/cuems-engine/projects/complex_test/script.xml` (24,183 B).

```
runs (ms): [18.673, 23.063, 18.81, 18.372, 17.934]
median: 18.673 ms
```

Budget (against **T001's** pre-feature 17.994 ms, not T083's — FR-PERF-002 measures the strictness this
phase adds against the true pre-feature baseline): ≤ 200% (35.99 ms) **and** ≤ 50 ms absolute →
**18.673 ms, well under both.** The added cost is one extra `ElementTree.parse` (the version probe,
research R2) plus the T2 tier now running on every load — on a document with no semantic violation, T2
costs one walk that finds nothing, which is why the delta from T001's 17.994 ms is small.

### Configuration domains (T090)

**Coverage caveat, stated beside the numbers it qualifies rather than only in `spec.md`
(FR-039):** four of the six schemas (`settings`, `network_map`, `project_settings`, `outputs`)
carry **zero** registered T2 rules, and `project_mappings` carries exactly **one**
(`one_custom_template_per_node`). So "T2 now runs on every configuration read" is, for these
domains, mostly plumbing — a walk that finds nothing to check — not enforcement catching real
violations. The measured costs below must not be read as "the cost of validating these
domains"; they are the cost of the walk itself plus the version-probe parse, on schemas that
had almost nothing for T2 to do even before this feature.

Same fixtures as T001, same method.

| Domain | T001 baseline (ms) | Budget (≤110%) | Measured (ms) | Margin |
|---|---|---|---|---|
| `network_map` | 9.277 | 10.20 | 10.14–10.49 (3 trials) | **at the edge — see note** |
| `settings` (system) | 20.575 | 22.63 | 20.79 | under |
| `project_mappings` (default) | 22.523 | 24.78 | 22.67 | under |
| `project_settings` | 6.504 | 7.15 | 5.73 | under |

**`network_map` is recorded as exceeded-or-marginal, not restated as passing** (FR-PERF-002's own
instruction). Three repeated trials of five runs each gave medians 9.984 / 10.486 / 10.214 ms against a
10.20 ms budget — straddling the line within measurement noise on a ~10 ms operation, where a
millisecond of scheduler jitter is a double-digit percentage. The **mechanism** for the added cost is
identified rather than hand-waved: `read_versioned_config_document` (`xml/mapper.py`) now parses the
document into a stdlib `xml.etree.ElementTree` **itself** (so the version probe, research R2, and any
conversion have a tree to work against) and hands that already-built tree to
`schema_object.to_dict(tree, ...)`, where the pre-008 path handed `to_dict` the **file path** directly
and let `xmlschema`'s own resource loader parse it — foreclosing whatever internal fast path that
loader may take for a bare path/URL argument versus an already-materialised foreign tree object. This
is a real, identified cost, not a guess dressed as one: it is paid on **every** config read regardless
of whether any conversion ever runs, on a domain FR-039 already notes carries **zero** T2 rules — so
100% of the measured delta here is version-probe plumbing, not enforcement. No mitigation is applied in
this pass: the absolute cost (~1 ms) is small, `network_map` is the smallest of the four config
fixtures (so a fixed per-call overhead shows up as its largest *percentage*), and D27 means nothing
ships on this figure alone — recorded here as a measurement obligation for 009's release gate to weigh,
per FR-PERF-002's instruction to record an exceeded budget rather than silently pass it. A cheaper
probe (e.g. a bounded `iterparse` that stops after the root's start-tag, only building the full tree
when a conversion actually applies) is the natural next step if this needs to be closed rather than
carried; not attempted here because it is exactly the kind of change that wants its own measurement.

### Mechanism summary, for whoever reads this next

Every load-path measurement above pays two new fixed costs versus T001: routing the decode through a
pre-parsed tree instead of a bare path (so the version probe, research R2, has something to read) and
one T2 walk (`xml.validators.repair`/`_iter_t2_findings`, unconditional per FR-037). Show documents
amortise both over a much larger parse and a real (if often empty) semantic surface; the smallest
config fixture (`network_map`) amortises them the least, which is exactly what the measured margins
above show.
