# Quickstart: working on the serialization core safely

**Feature**: `004-xml-serialization-core`

## Environment

Tests run under **pyenv 3.11.9**. Conda environments are not used for this project.

```bash
cd /disk/Projects/StageLab/cuems-utils
hatch test --show          # full suite; baseline 557 passed in ~7.4s
hatch build                # build
```

Pinned: `xmlschema==3.4.3`, `lxml==6.1.0`. The pin on `xmlschema` is load-bearing — the
whole design rests on `content.iter_elements()` ordering semantics (see `research.md` R1,
tripwire test C10).

## The one rule that matters

**The D14 chain test and the golden files are written against pre-refactor code, before
any machinery changes, and are never edited afterwards.**

If a golden test fails after the swap, the engine is wrong — not the golden. Regenerating
goldens to make a test pass defeats the entire feature. `git log` must show the goldens
landing before the first engine commit.

## Order of work

```
T1  record baseline           -> no code changes
T2  corpus + goldens + chain  -> test-only commit, suite green, zero production changes
T3  D9 rename                 -> pure git mv + imports, no logic
T4  deprecation shims         -> consumer imports keep working
T5  schema.py, spec.py        -> + coherence test
T6  adapters.py, registry.py
T7  converter.py              -> D5 thin subclass
T8  mapper.py + route through -> THE SWAP; all byte-identity contracts must be green
T9  config schemas
T10 logging pass (F11)
T11 verify no live path reaches a shim
```

## Verifying the premise yourself

```python
from xmlschema import XMLSchema11
s = XMLSchema11('src/cuemsutils/xml/schemas/script.xsd')
names = [e.local_name for e in s.types['AudioCueType'].content.iter_elements()]
assert names.index('master_vol') < names.index('fade_profiles')   # non-alphabetical
assert s.types['DmxSceneType'].content.model == 'all'             # order-free
```

## Traps found during research — read before writing the mapper

1. **`xs:all` is not ordered.** `CuemsScript` (the script root, an *anonymous* type) and
   `DmxSceneType` use `xs:all`. Their declaration order differs from what the current code
   emits. Using `iter_elements` order for them rewrites the root element of every script
   file on disk. Use the sorted-key tie-break — see `data-model.md` §2.1.
2. **There is no `CuemsScriptType`.** Root types are anonymous; bind by element path.
3. **`outputs.xsd` cannot be merged with `script.xsd`.** Both declare `OutputsType` in the
   same namespace with different content. Registries are per schema.
4. **`CTimecodeType` is a complex type**, not a scalar — it wraps a `<CTimecode>` child.
5. **`DmxUniverseType` has an attribute and an element both named `universe_num`.**
   Preserve whatever the current converter does; do not "fix" it.
6. **The serializer is stdlib `ElementTree`**, not `lxml`. Output has single-quoted
   declarations, no indentation, no trailing newline. Do not change the writer.
7. **`save(load(x)) == x` is false** for hand-authored corpus files — the serializer
   normalizes formatting. Idempotence is asserted from the first save onward.

## Checking your work

```bash
# the gates
hatch test --show                                   # >= 557 passing
python -m pytest tests/integration/test_d14_chain.py -v
python -m pytest tests/contract/ -v

# no live path reaches a deprecated shim (C8)
python -W error::DeprecationWarning -m pytest tests/ -q

# performance budget
python -m pytest tests/integration/test_mediacue_fade_performance.py -v
```

## What is out of scope here

Object-model changes, public API changes, `.xsd` edits, the node model migration, consumer
repo edits — and every behaviour-changing bug fix (F4, F12, F16–F20, F13/F21, F23), which
belong to features 005–007. See the deferred table in `spec.md`.
