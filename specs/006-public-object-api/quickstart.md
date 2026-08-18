# Quickstart — verifying feature 006 end to end

**Feature**: 006-public-object-api · **Date**: 2026-08-18

How to check that this feature does what it claims, in the order the claims matter. Every
command is runnable from the repository root.

Tests run under **pyenv 3.11.9**; conda is not used for this project. If `hatch` is not on
`PATH`, prefix with `PYENV_VERSION=3.11.9 pyenv exec`.

---

## 0. Baseline before touching anything

```bash
PYENV_VERSION=3.11.9 pyenv exec hatch test 2>&1 | tail -3
# expect: 1485 passed, 47 skipped, 2 xfailed  (~45 s)
```

If that is not green, stop — standing rule 1 forbids implementing on a red suite.

## 1. The gating check: the UI payload has not moved

This is the one that matters most, because it crosses into a repository this feature does not
edit and its failure mode is invisible here.

```bash
PYENV_VERSION=3.11.9 pyenv exec hatch run pytest tests/contract/ -k wire -v
```

Asserts, for every corpus script document, that `CuemsScript.load(p).to_wire()` equals the
pre-feature `read()` golden minus the `schemaLocation` key — structure **and** scalar types.

Manual spot check on the boolean encoding the UI depends on:

```bash
PYENV_VERSION=3.11.9 pyenv exec hatch run python -c "
from cuemsutils.cues.CuemsScript import CuemsScript
w = CuemsScript.load('tests/data/corpus/cuems-engine/projects/complex_test/script.xml').to_wire()
cue = w['CuemsScript']['CueList']['contents'][0]
body = next(iter(cue.values()))
print('enabled =', repr(body['enabled']))          # expect the STRING 'True'/'False'
print('schemaLocation present:', any('schemaLocation' in k for k in w))   # expect False
"
```

`enabled` must print `'True'`, **not** `True`. A JSON boolean here is deferred item X1 and a
file-format migration.

## 2. The two payloads now agree

The bug this feature fixes is that the UI receives two different encodings of one document
type. Confirm they are now one:

```bash
PYENV_VERSION=3.11.9 pyenv exec hatch run pytest tests/contract/ -k payload_parity -v
```

This test **fails before** the feature and passes after — it is the fail-then-pass evidence
for behaviour change 1.

## 3. The public surface is the only surface

```bash
PYENV_VERSION=3.11.9 pyenv exec hatch run python -c "
import cuemsutils.xml as x
print('xml exports:', x.__all__)                    # expect []
from cuemsutils.xml import Settings
print('Settings is a class:', isinstance(Settings, type))   # expect True, NOT a module
"
```

The second line guards a hazard that has bitten once already: `Settings.py` is a real
submodule, and if the shim imports are dropped while emptying `__all__`, this returns a module
and calling it raises `TypeError: 'module' object is not callable`.

Deprecation path still works, and says so:

```bash
PYENV_VERSION=3.11.9 pyenv exec hatch run python -W all::DeprecationWarning -c "
from cuemsutils.xml import XmlReaderWriter
XmlReaderWriter(schema_name='script', xmlfile='tests/data/corpus/cuems-editor/script_minimal.xml').read()
" 2>&1 | grep -i deprecat
# expect: '… use CuemsScript.load instead; removed in v0.1.1'
```

## 4. The round trip, through the public API only

D14's chain, with no machinery imported:

```bash
PYENV_VERSION=3.11.9 pyenv exec hatch run pytest tests/integration/ -k chain -v
```

`xml → object → json → object → xml`, byte-identical XML out, for every corpus document.

## 5. Validation behaves differently on purpose

`validate()` collects; `save()` raises at the first failure and writes nothing:

```bash
PYENV_VERSION=3.11.9 pyenv exec hatch run pytest tests/contract/ -k "validate or save_atomic" -v
```

And the deliberate asymmetry — a semantically invalid document still **loads**:

```bash
PYENV_VERSION=3.11.9 pyenv exec hatch run pytest tests/contract/ -k semantic_not_on_read -v
```

Reading never becomes stricter. That is policy (standing rule 8), and the corpus sweep in
[corpus-sweep.md](corpus-sweep.md) is why it is safe to keep.

## 6. Documents are portable

```bash
PYENV_VERSION=3.11.9 pyenv exec hatch run pytest tests/contract/ -k schema_location -v
```

Written documents carry the bare schema filename, so the same object written on two machines
produces identical bytes; and documents already on disk keep loading with the attribute
absolute, relative, or absent.

## 7. Performance

```bash
PYENV_VERSION=3.11.9 pyenv exec hatch run python specs/006-public-object-api/bench_to_wire.py
```

| Path | Baseline | Budget |
|---|---:|---|
| `load()` + `to_wire()` | `read()` = 16.95 ms | **≤ 25 ms** |
| `to_wire()` alone | tree build = 1.09 ms | **≤ 5 ms** |
| Suite | 44.57 s | ≤ 10% regression |

If `to_wire()` lands near 16 ms, the direct projection has silently become the round-trip
strategy — which measures at 33.99 ms end to end, a 2× regression on `project_load`. Check
that `encode_wire` is not calling `to_dict`.

## 8. Full suite

```bash
PYENV_VERSION=3.11.9 pyenv exec hatch test --show
```

Green, ≥ 1485 passing, `ruff` clean.
