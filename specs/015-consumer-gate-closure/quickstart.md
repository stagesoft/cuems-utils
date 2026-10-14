<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Quickstart — working on the consumer-gate closure

**Phase 1** · 2026-10-13. Everything here was run on this branch in this session.

---

## 1. The interpreter — read this before measuring anything

The box was migrated on 2026-10-13: anaconda removed, pyenv installed, the toolchain (`uv`, `hatch`,
`specify`) reinstalled under `~/.local`. The suite runs on CPython **3.11.9**, matching the
convention's version for the first time.

Two 3.11.9 builds exist, and **they agree only because pyenv's carries PGO+LTO**:

```bash
uvx hatch run test.py3.11:python -VV
# 3.11.9 [Clang 18.1.8]   -> ~/.local/share/uv/python/...  (python-build-standalone)
python -VV
# 3.11.9 [GCC 12.4.0]     -> ~/.pyenv/versions/3.11.9      (local build)
python -c "import sysconfig; print(sysconfig.get_config_var('CONFIG_ARGS'))" | grep -o 'optimizations\|lto'
# must print both: optimizations, lto
```

Measured interleaved, same method, same session:

| Path | pyenv **without** PGO/LTO | pyenv **with** PGO+LTO | uv | gap |
|---|---|---|---|---|
| show-document load | **23.421 ms** | 16.650 / 16.305 ms | 16.649 / 16.505 ms | **~0%** |
| show-document save | 19.809 ms | 14.177 / 13.742 ms | 13.800 / 13.612 ms | ~2% |
| descriptor derivation | 1.793 ms | 1.060 / 1.042 ms | 1.054 / 1.015 ms | ~2% |

⚠ **A pyenv build without those flags reads 42% over budget on unchanged code** (23.4 ms against
16.5). If you ever rebuild the interpreter, rebuild it as:

```bash
PYTHON_CONFIGURE_OPTS="--enable-optimizations --with-lto" CC=gcc-12 pyenv install -f 3.11.9
```

`CC=gcc-12` is required: the default GCC 14 makes `-Wincompatible-pointer-types` an error and
CPython 3.11 will not build.

Record **which build** a figure came from, not just "3.11.9". For quick probes use the hatch
interpreter by absolute path:

```bash
PY=~/.local/share/hatch/env/virtual/cuemsutils/KPtCKENL/test.py3.11/bin/python
PYTHONPATH=src $PY -c "import cuemsutils; print(cuemsutils.__file__)"
```

## 1a. The two static gates

Both are **baseline-compared, never clean-asserted** — neither tool is clean on this tree, and mypy
had never been run on it before 2026-10-13.

```bash
# lint (T005a captures the before; T121 compares)
PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:lint

# types (T005b's baseline is registered; T121a compares)
PYENV_VERSION=3.11.9 uvx hatch run types:check src/cuemsutils
#  -> Found 80 errors in 26 files (checked 68 source files)      <- the branch point
```

**Pass `src/cuemsutils` explicitly.** The `types:check` script's default is `src/cuemsutils tests`,
which reports **278** errors — but 158 of them are the single module `pytest` being unimportable,
because `[tool.hatch.envs.types]` installs only `mypy` and none of the test dependencies from
`[tool.hatch.envs.test]`. An env defect, not a finding; not this feature's to fix.

**Dependencies outside pyenv**: `uv`/`uvx`, and **network on the first run only** — hatch builds the
`types` env and installs `mypy>=1.0.0`, and `--install-types --non-interactive` pulls one stub
package, `types-Deprecated`. Both are cached in
`~/.local/share/hatch/env/virtual/cuemsutils/<hash>/types/` afterwards, so later runs are offline.
Nothing is needed on a deployed node: this is a dev-box gate only.

**The baselines DESCEND** (FR-109): at the end of this feature both figures must be *lower* than the
branch point's — type **80** in `src/`, lint **606** — and the lower figures become the gate. The
sweep is `T126`–`T136`, last of all, because 438 of the 606 lint findings are whitespace on blank
lines touching nearly every file.

⚠ **Do not bulk `ruff --fix`.** `I001` (17 findings in `src/`) can break this package's documented
lazy-import contract — `adapters._register_enums()` imports `NodeRole` back out of `NodeList` during
that module's own initialisation — producing an `ImportError` neither gate catches. Sort imports one
file at a time with the suite after each. And `E721`'s correct fix is `type(x) is Y`, **never**
`isinstance(x, Y)`: the 24 findings in `tests/` assert the *exact* type.

```bash
# what is actually suppressing nothing
PYENV_VERSION=3.11.9 uvx hatch run types:check --warn-unused-ignores src/cuemsutils
PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:lint src/ --extend-select RUF100
```

To compare after a change:

```bash
PYENV_VERSION=3.11.9 uvx hatch run types:check src/cuemsutils 2>&1 | tail -1
diff <(grep -E '^src/.*error:' specs/015-consumer-gate-closure/snapshots/types-before.txt) \
     <(PYENV_VERSION=3.11.9 uvx hatch run types:check src/cuemsutils 2>&1 | grep -E '^src/.*error:')
```

---

## 2. Run the suite

```bash
cd /disk/Projects/StageLab/cuems-utils
uvx hatch run test.py3.11:run -- -q
```

**Expect five failures at the branch point.** They are not yours:

```
5 failed, 3565 passed, 113 skipped, 2 xfailed in 31.13-31.83 s   # = 8.73-8.93 ms/test
```

The counts are identical before and after the toolchain migration, and the identical **113 skips**
is the check that confirms dependency parity — a different skip count means something did not come
across.

| Failing test | Cause | Owner |
|---|---|---|
| `test_read_path_regression.py::test_the_show_document_load_is_within_its_recorded_budget` | budget exceeded by 1.7–8.4% | **this feature**, FR-079 |
| `test_migration_guide.py::test_the_coupled_engine_version_resolves` | 012's guide names an engine version that tree no longer declares | **this feature**, FR-080 |
| `test_migration_guide.py::test_the_engine_really_broadcasts_the_status_the_guide_tells_you_to_watch` | the named signal is gone from the engine source | **this feature**, FR-080 |
| `test_migration_guide_names_sites.py::…[cuems-editor]` | 013's guide pins a dead commit | **this feature**, FR-080 |
| `test_migration_guide_names_sites.py::…[cuems-frontend]` | same | **this feature**, FR-080 |

The suite must end with **no more than these five**, each attributed (SC-TEST-002).

Lint:

```bash
uvx hatch run test.py3.11:lint
```

---

## 3. Measure a budget the way the budget was set

Best of three medians of five warm runs, one warm call first, fresh process. **Check the box's load
first** — this is not optional, and skipping it is how this feature's own first pass recorded a
phantom 2× regression:

```bash
cat /proc/loadavg    # quiet here is 0.6-1.1; wait if the 1-minute figure is above ~1.5
```

And **take samples in more than one window**. This feature got the headline figure wrong twice from
single-window sampling that looked perfectly consistent both times — see §3's reference figures.

```bash
PY=~/.local/share/hatch/env/virtual/cuemsutils/KPtCKENL/test.py3.11/bin/python
PYTHONPATH=src $PY - <<'PY'
import statistics, time
from cuemsutils.cues.CuemsScript import CuemsScript
D = "tests/data/corpus/cuems-engine/projects/complex_test/script.xml"
CuemsScript.load(D)                      # warm: schema parse and registry build are once per process
medians = []
for _ in range(3):
    timings = []
    for _ in range(5):
        started = time.perf_counter()
        CuemsScript.load(D)
        timings.append((time.perf_counter() - started) * 1000)
    medians.append(statistics.median(timings))
print("%.3f ms" % min(medians))        # hatch interpreter: 16.3-17.3 ms, window-dependent
PY
```

### Branch-point reference figures, and the budgets

Re-measured 2026-10-13 after the migration, through the hatch interpreter:

| Path | Branch point (worst observed) | Budget (115%) |
|---|---|---|
| show-document **save** | 14.297 ms | ≤ 16.4 ms |
| descriptor derivation, `script` | 1.060 ms | ≤ 1.22 ms |
| suite | 8.93 ms/test | ≤ 10.3 ms/test |
| show-document **load** | band **16.465–17.750 ms**, median 16.864, n=16 | **straddles** its 16.5 ms line (14 of 16 over) — compared against the band, not the line (FR-079a) |

**115%, and the sampling rule that goes with it.** Pooled spread over 16 samples in three windows is
**7.8%**; the individual windows read 2.9%, 7.7% and 4.8%. A tolerance claim needs at least two
separated windows — this feature briefly set 110% from the 2.9% window alone and had to undo it.

⚠ The pre-migration save (28.6 ms) and derive (2.08 ms) figures are **withdrawn**, not a "before":
they were taken with a weaker method during a contended window, on an interpreter that no longer
exists to re-measure on.

---

## 4. Reproduce G5's dead end

The defect, on a document that is both pre-013 (flat players) and pre-F3 (carrying the retired
counts):

```bash
git -C ../cuems-nodeconf show 4d7c91d:tests/fixtures/etc_cuems/settings.xml > /tmp/pref3.xml
PYTHONPATH=src $PY -c "
import sys; sys.argv=['cuems-reshape-devices','/tmp/pref3.xml']
from cuemsutils.xml.reshape_devices import main; print('exit', main())"
```

At `75a958e` this printed:

```
/tmp/pref3.xml: skipped (would not validate: ... Unexpected child with tag 'audio_cards' at position 3 ...)
nothing to do (1 skipped)
exit 1
```

**On the finished branch (verified 2026-10-14) it prints `reshaped`, exits 0, and the document then
loads** (`load_config_document(Settings, …)` returns a `Settings`; the file is now indented).
That composition — not a unit test on the converter — is the red test. The red test is this
composition, not a unit test on the converter — a unit test with an already-reshaped tree would pass
the moment the paths are added and would not catch the next instance of this class.

**Operator triage question**, for the record: *not* "is it flat-shaped?" but

```bash
grep -cE '<(audio_cards|universes)>' /etc/cuems/settings.xml    # non-zero -> affected
```

⚠ This dev box's own `/etc/cuems/settings.xml` is in the **pre-013 device shape**, so
`ConfigManager()` against the host configuration refuses it. Point tools at a fixture
`CUEMS_CONF_PATH`, or migrate the host file first.

---

## 5. Inspect what the gates change

**The descriptor instance (G3):**

```bash
PYTHONPATH=src $PY -c "
import json
from cuemsutils.xml.descriptor import SchemaDescriptor
sd = SchemaDescriptor()
for td in sd.types('script'):
    if td.key.name in ('AudioCueOutputsType','VideoCueOutputsType'):
        print(td.key.name, json.dumps(td.instance, default=str))"
```

At the branch point: no wrapper, `channels` nested the wrong way, every scalar `null`. Now (G3): the wrapper is present, `channels` is a list of single-key wrappers, `class` is set and every required scalar carries a value. Compare against the wire
shape in `tests/golden/dict/cuems-engine__projects__complex_test__script.reader.json`.

**The union narrowing (S2)** — five sites must stop reporting a one-value choice set:

```bash
PYTHONPATH=src $PY -c "
from cuemsutils.xml.descriptor import SchemaDescriptor
sd = SchemaDescriptor()
for s in ('network_map','settings','project_mappings'):
    for td in sd.types(s):
        for f in td.fields:
            if f.xsd_type in ('NodeUuidType','AutoOrIntLatencyMsType'):
                print(s, td.key.name, f.name, f.enum_values)" \
  | tee specs/015-consumer-gate-closure/snapshots/union-enums-before.txt
```

⚠ **Snapshots go in `specs/015-consumer-gate-closure/snapshots/`, not `/tmp`** — `mkdir -p` it
first. T058 and T123 read these files many phases after T003/T004 write them, and a before-state
that does not survive a reboot is a baseline that quietly becomes "trust me". The scratch documents
in §4 are a different thing: they are read within the same command.

**The repairability invariance (SC-005a)** — capture before, compare after. Zero entries may change:

```bash
PYTHONPATH=src $PY -c "
from cuemsutils.xml.descriptor import SchemaDescriptor
sd = SchemaDescriptor()
rows = [(s, td.key.name, f.name, f.repairability.value, repr(f.default))
        for s in ('script','settings','network_map','project_mappings','project_settings','hardware_outputs')
        for td in sd.types(s) for f in td.fields]
print(len(rows))
open('specs/015-consumer-gate-closure/snapshots/repairability-before.txt','w').write('\n'.join(map(str, sorted(rows))))"
```

**The candidate tags (FR-080f)** — resolve the **commit** (`^{commit}`); a bare `rev-parse` of an annotated tag prints the tag object, which is what made three recorded values look wrong when only one (`cuems-nodeconf`) had moved:

```bash
for r in cuems-common cuems-nodeconf cuems-power-bridge cuems-engine cuems-editor cuems-frontend cuems-utils; do
  printf "%-22s %s\n" "$r" "$(git -C ../$r rev-parse --short 'xml-refactor-merge-candidate^{commit}' 2>/dev/null || echo 'no tag')"
done
```

---

## 6. Re-cut the goldens (the polish phase's single event)

The capture tool **refuses to overwrite without `--force`**, which is what makes this one reviewable
act rather than a drift:

```bash
PYTHONPATH=src $PY -m tests.support.capture_goldens --force
```

Expect exactly these to move, and nothing else:

| Re-cut | Why |
|---|---|
| `xml/` × 5, `generated/example_script.xml` | the writer now indents |
| `api/public_api.json`, `api/config_accessors.json` | **four** additions: G1's two path signatures, G2's `project_settings` property, G4's `NodeIndex.set_alias` and S1's `NodeIdentityCollisionError` |
| `MANIFEST.sha256` | follows |
| `dict/` × 24, `outcomes.json` | **must not move** — a wire dict carries no whitespace |

⚠ **Two of those four appear only if their surface record moved first** (T049a, T080a). The goldens'
scope is the hand-maintained `PUBLIC_CLASSES` / `PUBLIC_FUNCTIONS` / `PUBLIC_ERRORS` in
`tests/contract/test_public_api_surface.py` — `NodeIndex` is in neither golden at the branch point,
and the `errors` section is generated **from** the tuple rather than read from `__all__`. Check the
diff contains all four rather than trusting the capture.

⚠ **This is the polish phase's event, not US2's and not US8's.** It runs after every public addition
and after the writer change, so the goldens are deliberately stale in between.

Also re-author by hand, in the writer's new output form — **five documents, not two**:

- `tests/data/corpus/cuems-utils/fade_showcase.xml` and `unicode_showcase.xml`, which
  `tests/contract/test_roundtrip_stability.py` asserts are byte-identical after one save (T090);
- `specs/007-node-model-migration/pre-state/network_map.xml`,
  `pre-state/corpus/cuems-utils/network_map.xml` and `pre-state/corpus/cuems-engine/network_map.xml`,
  which `tests/contract/test_network_map_roundtrip.py` diffs `save()`'s output against while
  asserting the diff is **exactly two lines** — true only while the document is one line (T090a).

If any of the five is not re-authored, those assertions break rather than the goldens being wrong.

---

## 7. Sequencing that matters

1. **S2 before G3.** The union seeding rule reads member types directly; before the narrowing, a
   union reports its members' merged enumerations *as* its own, so the rule-1 path fires and the
   test meant to pin rule 2 passes vacuously.
2. **G1 with G2.** One user journey — an empty document after a tolerant load makes a project's first
   save work as soon as the write target exists — one integration test, and the same two API
   goldens.
3. **S3 last of the code changes**, so later work is not reviewed against freshly moved goldens.
4. **G4, G5, S1 are independent** of everything above and of each other.
5. **The sweep is the polish phase**, and the nine deletions come last of all: the source document is
   the checklist against which "every row implemented or declined" is verified, so deleting it
   earlier removes the evidence.
