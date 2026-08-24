# Quickstart — verifying feature 007

**Feature**: `007-node-model-migration` | **Date**: 2026-08-24

How to run, measure and check this feature by hand. Every command is the one the tasks use, so a
reviewer reproduces the evidence rather than trusting a summary.

---

## 0. Environment

```bash
export PYENV_VERSION=3.11.9        # tests run under pyenv 3.11.9; conda is not used here
cd /disk/Projects/StageLab/cuems-utils
```

Sibling repositories, at the commits this feature works from:

```bash
git -C ../cuems-nodeconf log --oneline -1   # must be 0a3ce37 on feat/nodeconf-reenable
git -C ../cuems-common   status --short
```

---

## 1. Before touching anything — capture the pre-state

The FR-010 diff and the FR-PERF-001 budget are both measured *against this*, so it runs first and
exactly once.

```bash
pyenv exec python -m tests.support.capture_goldens          # never with --force at this point
hatch test --show 2>&1 | tail -5                            # the pre-feature suite figure
```

Record in `baseline.md`: pass/skip/xfail counts, wall time, per-test milliseconds, and the
network-map load timing.

**Then normalise the corpus** — its own commit, before any schema change:

```bash
# after T006b: no indentation, bare-filename schemaLocation
grep -c "    <node>" tests/data/corpus/*/network_map.xml   # must be 0
grep -o 'schemaLocation="[^"]*"' tests/data/corpus/*/network_map.xml | sort -u
# must show only:  https://stagelab.coop/cuems/ network_map.xsd
```

The FR-010 diff is measured against these normalised documents, not against what was in git before
this step.

**Verify the FR-026d break exists before repairing it** (research R11) — this is a named
deliverable, not a formality:

```bash
cd ../cuems-nodeconf && pyenv exec python -c "
from cuemsnodeconf import NodeXmlBuilders
import cuemsutils.xml.XmlBuilder as B
print('injected:', hasattr(B, 'nodeXmlBuilder'))
print('consulted: ', 'no — the registry resolves the type')
"
```

---

## 2. The schema change

```bash
git diff src/cuemsutils/xml/schemas/            # must touch network_map.xsd and nothing else
```

Check the two added simple types and the in-place rename:

```bash
grep -n "node_role\|NodeRoleType\|UuidType" src/cuemsutils/xml/schemas/network_map.xsd
grep -c "node_type" src/cuemsutils/xml/schemas/network_map.xsd     # must be 0
```

---

## 3. Read a map, and look at the types

```python
from cuemsutils.tools.ConfigManager import ConfigManager
from cuemsutils.tools.NodeList import NodeRole   # cuemsutils.config is INTERNAL

cm = ConfigManager("tests/data")
node = cm.network_map["node_list"][0]["node"]

type(node["node_role"])   # <enum 'NodeRole'>
node["node_role"]         # NodeRole.controller
type(node["adopted"])     # <class 'bool'>
type(node["uuid"])        # <class 'cuemsutils.tools.Uuid.Uuid'>
type(node["alias"])       # <class 'str'>  — free text, never coerced
```

Confirm the exception is scoped — these must be **unchanged**, still text:

```python
cm.settings          # adopted/online-style BoolType fields here stay strings
cm.project_mappings
```

---

## 4. Write a map, and diff it

```python
netmap = cm.network_map
netmap.save("/tmp/out.xml")
```

```bash
diff tests/data/network_map.xml /tmp/out.xml
```

**Expected**: only `<node_type>NodeType.master</node_type>` → `<node_role>controller</node_role>`
lines. Any other differing line is a defect (C4).

---

## 5. The conversion, from a legacy file

```bash
cp tests/data/corpus/cuems-engine/network_map.xml /tmp/legacy.xml
../cuems-common/usr/bin/cuems-migrate-network-map /tmp/legacy.xml
../cuems-common/usr/bin/cuems-migrate-network-map /tmp/legacy.xml   # idempotent
xmllint --schema src/cuemsutils/xml/schemas/network_map.xsd /tmp/legacy.xml --noout
```

Second run must change nothing:

```bash
cp /tmp/legacy.xml /tmp/once.xml && ../cuems-common/usr/bin/cuems-migrate-network-map /tmp/legacy.xml
diff /tmp/once.xml /tmp/legacy.xml && echo "idempotent"
```

---

## 6. The suite

```bash
hatch test --show
```

Specifically:

```bash
hatch test --show -- tests/unit/test_coherence.py                       # C9
hatch test --show -- tests/contract/test_declared_break_nodeconf.py     # C7
hatch test --show -- tests/contract/test_golden_immutability.py         # M6
hatch test --show -- tests/contract/test_registry_totality.py
```

---

## 7. `cuems-nodeconf`, after migration

```bash
cd ../cuems-nodeconf
ls cuemsnodeconf/CuemsNode.py cuemsnodeconf/NodeXmlBuilders.py   # both must be absent
grep -rn "XmlBuilderModule\.\|ParsersModule\." --include="*.py" . # must be empty (C7)
grep -rn "class NodeType\|NodeType\." --include="*.py" . | grep -v __pycache__   # must be empty
pyenv exec python -m pytest -q                                    # SC-008
```

---

## 8. Budgets

```bash
hatch test --show 2>&1 | tail -3
```

Compare against `baseline.md`:

- network-map load: ≤ 110% of the pre-feature figure.
- suite per-test: ≤ 110% of the feature 006 baseline (~27 ms/test).

Record **both** figures whether they pass or not. Feature 006's wall-time budget was recorded as
exceeded rather than restated as passing, and that convention holds here.

---

## 9. The evidence a reviewer should be able to find

| Claim | Where it is proven |
|---|---|
| Only two bytes-classes changed in a round trip | C4 test + the golden diff |
| The other four config schemas are untouched | C2 test + SC-010a |
| Free text is safe structurally, not by denylist | C3 test asserting `adapter_for` |
| The 004 break is closed | rewritten `test_declared_break_nodeconf.py` |
| A deployed node survives | M3 idempotence + validity tests |
| Nothing ships early | the release gate stated in `migration-guide.md` |
