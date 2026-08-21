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
# expect: 2222 passed, 94 skipped, 2 xfailed  (~59 s)  -- after feature 006
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
# expect two records: the class ('… use …CuemsScript instead; removed in v0.1.1')
# and the method ('… use …CuemsScript.to_wire instead; removed in v0.1.1;
#                  note: the returned dict no longer contains the schemaLocation key')
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
PYENV_VERSION=3.11.9 pyenv exec hatch run hatch-test.py3.11:python \
  specs/006-public-object-api/bench_public_api.py
```

That measures **what shipped**. `bench_to_wire.py` beside it is the *research*
script: it compares the two candidate strategies, and the one it calls "Strategy A"
— the round trip through XML — is the one that was **rejected**. Running it after
the fact measures code that is not on the shipped path.

| Path | Budget | Measured |
|---|---|---:|
| `load()` + `to_wire()` | ≤ 25 ms | **18.3 ms** ✅ |
| `to_wire()` alone | ≤ 5 ms | **0.73 ms** ✅ |
| write path (`save()` vs `write_from_object()`) | ≤ +10 % | **+8.8 %** ✅ |
| suite wall time | ≤ 10 % over 44.57 s | **59 s (+33 %)** ❌ |

The suite figure is **exceeded as written and is not a regression**: the suite grew
from 1485 tests to 2222 across features 005 and 006. Per test it is ~27 ms against
the baseline's 30 ms — 11 % faster. See [baseline.md](baseline.md), which records it
as exceeded rather than reframing the budget.

If `to_wire()` ever lands near 16 ms — or even near the 1.1 ms tree build — the direct
projection has silently become the round-trip strategy, which measures at 33.99 ms end
to end. Check that `encode_wire` is not calling `to_dict`.

The write path's +8.8 % is the semantic tier, essentially exactly: `run_rules()` alone
measures 0.90 ms, which is 5.9 % of `save()`. Nothing else moved.

## 8. Full suite

```bash
PYENV_VERSION=3.11.9 pyenv exec hatch test --show
```

Green, ≥ 1485 passing, `ruff` clean.

## 9. UTF-8 under a hostile locale (FR-036e)

The failure this guards is silent and environmental: `open()` without
`encoding=` uses the platform default, which on a node booted with `LANG=C` is
ASCII. A show file with an accented cue name then saves fine on a developer's
UTF-8 laptop and raises `UnicodeEncodeError` on the node — or, worse, writes
mojibake. Review cannot catch it, because the source line looks identical
either way.

```bash
cd <repo>
LC_ALL=C LANG=C PYENV_VERSION=3.11.9 pyenv exec hatch test \
  tests/contract/test_utf8_roundtrip.py
```

**Expect:** all tests pass, including
`test_the_whole_chain_survives_lc_all_c`, which re-runs the whole chain in a
**subprocess** started under `LC_ALL=C`. The subprocess is not ceremony: Python
reads the locale at interpreter start, so `monkeypatch.setenv` alone changes
nothing that matters.

The fixture is `tests/data/corpus/cuems-utils/unicode_showcase.xml` — added in
Phase 1, with its goldens captured by the pre-feature harness, carrying accented
vowels, `ç`, `ñ`, an apostrophe and an em dash in show name, cue names and
`ui_properties` text. Before it, **the corpus contained zero non-ASCII bytes**,
so no test could have caught an encoding regression at all.

To see it end to end by hand:

```bash
LC_ALL=C LANG=C PYENV_VERSION=3.11.9 pyenv exec hatch run \
  hatch-test.py3.11:python -c "
from cuemsutils.cues.CuemsScript import CuemsScript
s = CuemsScript.load('tests/data/corpus/cuems-utils/unicode_showcase.xml')
print(s.name)
print('escapes:', '\\\\u' in s.to_json())
"
```

**Expect:** `Espectáculo de Otoño`, then `escapes: False` — `to_json()` uses
`ensure_ascii=False`, so the payload carries the characters rather than their
escapes.
