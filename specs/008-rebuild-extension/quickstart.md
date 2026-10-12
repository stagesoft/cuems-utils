# Quickstart — feature 008 verification and measurement

How to run the suite, take the measurements FR-PERF-002 budgets, and check the phase gate.

---

## Suite

```bash
cd /disk/Projects/StageLab/cuems-utils
hatch test --show
```

Tests run under **pyenv 3.11.9**; conda environments are not used for this project.

**Baseline to beat (feature 007, measured 2026-08-24):** 2393 passed, 94 skipped, 2 xfailed in
59.33 s = **24.79 ms/test**. Budget: ≤ 110%, i.e. **≤ 27.27 ms/test**.

Take the **per-test** figure, never wall time. The suite grows every feature — 1485 → 2222 → 2393 —
so an absolute wall-time budget compares different suites and reads growth as regression.

---

## Load-time measurement

Method, unchanged from 006 and 007 so the figures stay comparable: **median of five warm runs, fresh
process per measurement.**

**The fixture is `projects/complex_test/script.xml`, and the choice is load-bearing** (research R10).
It is the corpus's largest show document at **24,183 bytes** — 9.1× `fade_showcase.xml`, which this
file named until 2026-08-28 and which is *not* the largest. The absolute half of FR-PERF-002's
show-document budget exists to "stop the ratio from excusing a path that scales badly on large
scripts", so measuring a 9×-undersized document makes that cap unreachable and therefore
non-protective. Indicative pre-feature medians (measured 2026-08-28 on Python 3.13, **not** the 3.11.9
the real baseline must use):

| Document | Size | Median load |
|---|---|---|
| `cuems-engine/projects/complex_test/script.xml` | 24,183 B | **11.76 ms** |
| `cuems-editor/script_minimal.xml` | 3,738 B | 5.00 ms |
| `cuems-utils/fade_showcase.xml` | 2,649 B | 3.48 ms |

At 11.76 ms the 50 ms cap binds at ~4.3× and the ≤200% ratio (23.5 ms) is the tighter of the two — both
budgets do real work. At 3.48 ms the cap sits 14× away and can never bind, which is the failure mode
this fixture change fixes. The two 24,067-byte `legacy/` documents are **not** candidates: feature 005
recorded them as deliberately rejected at `VideoCueOutput.__init__`. `complex_test/script.xml` was
confirmed to load before being named here.

```bash
# Show document — the corpus's largest, confirmed loadable
pyenv exec python - <<'PY'
import statistics, time
from cuemsutils.cues.CuemsScript import CuemsScript
PATH = "tests/data/corpus/cuems-engine/projects/complex_test/script.xml"
CuemsScript.load(PATH)                       # warm
runs = []
for _ in range(5):
    t = time.perf_counter(); CuemsScript.load(PATH); runs.append((time.perf_counter()-t)*1000)
print("runs (ms):", [round(r,3) for r in runs], "median:", round(statistics.median(runs),3))
PY
```

```bash
# Configuration domains — one per domain, same shape
pyenv exec python - <<'PY'
import statistics, time
from cuemsutils.tools.ConfigManager import ConfigManager
cm = ConfigManager(load_all=False)
cm.load_network_map()                        # warm
runs = []
for _ in range(5):
    t = time.perf_counter(); cm.load_network_map(); runs.append((time.perf_counter()-t)*1000)
print("network_map median (ms):", round(statistics.median(runs),3))
PY
```

### The three budgets (FR-PERF-002)

| Measurement | Budget |
|---|---|
| Show-document load | ≤ 200% of its re-measured pre-feature figure **and** ≤ 50 ms absolute |
| Each configuration domain's load | ≤ 110% of its re-measured pre-feature figure |
| Suite per-test | ≤ 110% of 24.79 ms |

**Re-measure the pre-feature figures on this branch before the strictness lands** (SC-024a). 006's
numbers predate 007 and are superseded; 007's `baseline.md` supplies only the suite figure.

The asymmetry between the first two rows is deliberate and follows FR-039: show documents carry nearly
every semantic rule that exists, so doubling is a real allowance for real work. The configuration
domains have **zero** T2 rules (three of four) or **one** (`project_mappings`), so they gain almost
nothing to run — a regression there is plumbing overhead, not enforcement, and is held to the tighter
number for that reason.

**Record results in `baseline.md`** beside 007's, including any budget exceeded. A budget exceeded is
recorded as exceeded and either mitigated or explicitly approved — never restated as passing.

---

## Phase gate check (D30)

Before **any** Phase 2 (ITEM E) task starts:

```bash
git log --oneline main..HEAD          # Phase 1 merged
hatch test --show                     # green
```

Then confirm the two hand-off interfaces are landed and stable (SC-013):

```bash
# 1. Config save() — all four domains, same shape
grep -rn "def save" src/cuemsutils/config/ | sort
grep -n "def save_" src/cuemsutils/tools/ConfigManager.py

# 2. Descriptor — defaults AND repairability present
pyenv exec python -c "
from cuemsutils.<descriptor-module> import SchemaDescriptor
d = SchemaDescriptor()
f = d.describe(...).fields[0]
print(f.name, f.enum_values, f.default, f.repairability)
"
```

If either signature is still under discussion when Phase 1 merges, **stop** — the gate exists so
Phase 2 is written against landed code, and a negotiable interface means it bought nothing.

Finally, **record** the fifth gate condition (T084(e), FR-057/SC-014): every Phase 1 acceptance
criterion is green on a tree containing no part of ITEM E. Conditions (a) and (b) establish it
incidentally, but SC-014 asks for a check, and an unrecorded check is indistinguishable from an
assumption:

```bash
git log --oneline --all -- src/cuemsutils/xml/versioning.py   # must be empty at the gate
```

---

## Verifying the golden events

FR-010 sanctions **three** golden events across this feature and no fourth. Each is deliberate (D29,
standing rule 3's recorded exception), each is its own **reviewed diff**, and none is a
regenerate-to-pass:

| Event | Task | Every changed line must be… |
|---|---|---|
| 1. ITEM A's cut | T023 | FR-003's duration reshape or FR-007a's fade-profile deletion |
| 2. ITEM D's replacement | T076 | the `create_script` → descriptor generator change (`generated/` only) |
| 3. ITEM E's renormalisation | T102a | the added `doc_version` root attribute, nothing else |

FR-029a's `ActionType` narrowing appears in **no** event: no corpus document carries `fade_in` or
`fade_out` (SC-012a), so it produces no golden churn.

```bash
# Event 1 (T023)
git diff --stat tests/golden/ tests/data/corpus/
git diff tests/golden/ | grep -v "duration\|CTimecode\|fade_profile" | head -40

# Event 3 (T102a) — the attribute and nothing else
git diff tests/golden/ | grep '^[+-]' | grep -v '^[+-][+-]' | grep -v 'doc_version' | head -40
```

Each command should print **nothing but diff headers**. Any other changed line is out of scope for
that event and must be explained before it is committed.

**Event 3 also touches nothing else.** Confirm the config round-trip fixtures still pass unmodified —
their normaliser absorbs `doc_version` by design (FR-015) — and that `tests/data/corpus/pre-008/` is
byte-unchanged, since it is conversion *input* and never writer output:

```bash
hatch test --show tests/integration/test_config_save.py
git status --porcelain tests/data/corpus/pre-008/    # must be empty
```

Confirm the pre-change corpus survives (FR-011) — it is the only first-party collection of real
old-shape documents, and Phase 2 converts it:

```bash
ls tests/data/corpus/pre-008/    # retained originals, ITEM E's fixtures
```

---

## Checking the three load outcomes (Phase 2)

Each must fail before its implementation and pass after (SC-016):

| Fixture | Expected |
|---|---|
| A retained pre-008 document | Converts in memory, loads, `outcome == CONVERTED`, **file on disk byte-unchanged** |
| Same, on read-only media | Still loads — no backup is needed, so none is attempted (SC-016a) |
| Current document, repairable violation | Loads, `outcome == REPAIRED`, report names field and both values |
| Current document, unrepairable violation | Raises `ValidationError` |
| Document marked newer than the library | Raises, distinguishably (FR-052) |
| A version step with no transformation | Loads, bytes unchanged, no backup, no repair (SC-016f) |
