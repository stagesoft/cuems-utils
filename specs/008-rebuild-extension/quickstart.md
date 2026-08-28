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

```bash
# Show document — the corpus's largest
pyenv exec python - <<'PY'
import statistics, time
from cuemsutils.cues.CuemsScript import CuemsScript
PATH = "tests/data/corpus/cuems-utils/fade_showcase.xml"
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

---

## Verifying ITEM A's golden re-cut

The re-cut is deliberate (D29, standing rule 3's one recorded exception) and must be a **reviewed
diff**, not a regenerate-to-pass.

```bash
git diff --stat tests/golden/ tests/data/corpus/
git diff tests/golden/ | grep -v "duration\|CTimecode\|action_type\|fade_profile" | head -40
```

The second command should print **nothing but diff headers**. Any other changed line is out of scope
for this feature and must be explained before the re-cut is committed.

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
