# Quickstart — 005 object model unification

**Feature**: one construction path for the object model. **Rule of thumb**: if a golden
changed, you broke something.

## Run

```bash
cd /disk/Projects/StageLab/cuems-utils
PYENV_VERSION=3.11.9 pyenv exec hatch test            # full suite
PYENV_VERSION=3.11.9 pyenv exec hatch test --show     # with output
```

Baseline on this branch (2026-08-12): **1251 passed, 43 skipped, 36.71 s**. Never start
implementation on a red suite.

## The three checks that matter most

```bash
# 1. Goldens must not move. This is the feature's primary gate.
git diff --stat tests/golden/          # must be empty, always

# 2. The preservation contracts
PYENV_VERSION=3.11.9 pyenv exec hatch test tests/contract/test_byte_identity_xml.py \
    tests/contract/test_byte_identity_dict.py tests/contract/test_accept_reject_parity.py \
    tests/integration/test_d14_chain.py

# 3. The measurement the feature exists to close
PYENV_VERSION=3.11.9 pyenv exec python -c "
from cuemsutils.xml.xml_reader_writer import XmlReaderWriter as R
s = R(schema_name='script',
      xmlfile='tests/data/corpus/cuems-engine/projects/complex_test/script.xml').read_to_objects()
cue = [c for c in s['CueList']['contents'] if 'Media' in c][0]
print('ui_properties:', type(cue['ui_properties']).__name__)     # dict  -> must become CuemsDict
print('regions[0]:   ', type(cue['Media']['regions'][0]).__name__)  # dict -> must become Region
"
```

## Where to start reading

1. `research.md` — R2 (two decode strategies), R3 (bare construction inventory), R10 (key
   order). Those three explain most of the design.
2. `data-model.md` §1 — the base protocol and the two construction modes.
3. `contracts/README.md` — C1–C4 are what you must not break; C5–C12 are what you must make
   pass.
4. `specs/planning/xml-rebuild-04-object-model.md` — the original measured evidence.

## The fail-then-pass recipe

Each of the seven behaviour changes needs a test that fails on the current code and passes
after. Write it first, run it, **see it fail**, then implement:

```bash
git stash                                     # park the implementation
PYENV_VERSION=3.11.9 pyenv exec hatch test tests/unit/test_region_coercion.py   # must FAIL
git stash pop
PYENV_VERSION=3.11.9 pyenv exec hatch test tests/unit/test_region_coercion.py   # must PASS
```

Record both outcomes in the pull request. A test that passes before the change is not
evidence of anything.

## Performance

Capture the pre-005 decode number **before** the first behaviour change lands — the 2×
allowance has no denominator otherwise:

```bash
PYENV_VERSION=3.11.9 pyenv exec python -c "
import time
from cuemsutils.xml.xml_reader_writer import XmlReaderWriter as R
f='tests/data/corpus/cuems-engine/projects/complex_test/script.xml'
r=R(schema_name='script', xmlfile=f)
t=time.perf_counter(); [r.read_to_objects() for _ in range(5)]
print(f'{(time.perf_counter()-t)/5*1000:.1f} ms')"     # 36.3 ms on 2026-08-12
```

Budget: ≤ 2× that number **and** ≤ 75 ms absolute; suite and write path within 10%.

## Eight tests you are allowed to touch — four changed, four extended

Everything else must pass unmodified. Touching any other test file means stopping and
re-reading the spec.

| File | Change |
|---|---|
| `tests/contract/test_dmx_failure_path.py` | swallow → raise |
| `tests/unit/test_coherence.py` | uncovered set becomes empty (18/18 coverage) |
| `tests/contract/test_registry_totality.py` | `UiPropertiesType` yields `CuemsDict` |
| `tests/contract/test_semantic_roundtrip.py` | built-vs-loaded exclusion lifted |
| `tests/integration/test_d14_chain.py` | **extended only** — built-vs-loaded leg |
| `tests/contract/test_logging_budget.py` | **extended only** — the drop-and-log record |
| `tests/integration/test_create_script_completeness.py` | **extended only** — cleared template |
| `tests/contract/test_accept_reject_parity.py` | **extended only** — explicit nil-UUID case |

"Extended only" means additive: no assertion those four carry today may change.

## Gotchas

- **Never** route decode through `cls(init_dict)` — `ensure_items` sorts, and the script root
  is an `xs:all` type whose emission order is arrival order. That single mistake rewrites the
  root element of every hand-authored script.
- **Do not** filter wildcard subtrees by declared fields. `ui_properties` content is not
  declared anywhere; filtering it deletes real editor state.
- **Do not** add or move a value-rejecting rule in any setter (FR-006b). Two legacy corpus
  documents are *pinned as rejected*; parity runs in both directions. Their rejection comes
  from `VideoCueOutput.__init__` → `_classify_output_name` (`CueOutput.py:154`), **not** from
  the `set_output_name` setter — preserve the constructor call, not setter invocation.
- **`_initialized` is a trap.** It looks like an ordinary runtime attribute and is not:
  `__init__` holds it false during population so that `set_output_name`'s region-consistency
  rules stay off the load path. If `_init_runtime()` sets it true before population, those
  rules switch on during decode and documents that load today start failing — order-dependently,
  so the corpus may not catch it. See `data-model.md` §5 and contracts C12.
- **`duration` is two different fields.** `FadeCue.duration` is a `CTimecode` and emits as
  `<duration><CTimecode>…</CTimecode></duration>`; `Media.duration` is a **string**
  (`TimecodeType`) and emits as bare text. Unifying them changes every media document. See
  `data-model.md` §4 before touching either setter.
- Commits are GPG-signed. Retry on "gpg failed to sign"; never `--no-gpg-sign`.
