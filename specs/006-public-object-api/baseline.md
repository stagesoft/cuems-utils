# Baseline (T001) — pre-implementation

Recorded 2026-08-19, before any 006 code lands. See T083/T091 for the
post-implementation figures appended to this file.

## Measurement context

- Machine: AMD Ryzen 5 5500U with Radeon Graphics, 12 logical CPUs, 14 GiB RAM.
- **Environment deviation from CLAUDE.md**: this sandbox has no `pyenv` install (`pyenv`
  is not on `PATH`, `~/.pyenv` does not exist). CLAUDE.md's documented workflow
  (`PYENV_VERSION=3.11.9 pyenv exec hatch test`) is not runnable here. The only Python
  toolchain available is an Anaconda env (`cuems_debian12`, Python 3.11.2) providing
  `hatch`. All commands below were run as plain `hatch ...` from that environment.
- **Test command deviation**: `hatch test` (the built-in hatch-test matrix) has no
  `hypothesis` dependency and fails to collect `tests/unit/test_ctimecode.py`. The
  project's actual test environment is the custom `[tool.hatch.envs.test]` matrix
  (`python = ["3.11", "3.12", "3.13"]`, includes `hypothesis`), invoked via
  `hatch run test:run` — confirmed as the canonical command by
  `.github/workflows/tests.yml`, which runs `hatch run test:run-cov` in CI. This
  feature's baseline and every subsequent suite run use `hatch run test:run`.

## Suite result

```
hatch run test:run
========== 1485 passed, 47 skipped, 2 xfailed, 140 warnings in 35.49s ==========
```

Matches the previously recorded baseline (1485 passed / 47 skipped / 2 xfailed) exactly.
Wall time for the command including environment sync: 3m50s; pure pytest run time: 35.49s.

## `bench_to_wire.py` (all three matrix Pythons; corpus doc
`tests/data/corpus/cuems-engine/projects/complex_test/script.xml`, 24183 bytes)

| Python | `read()` (XML→wire dict) | Strategy A `to_wire` alone | tree build | `to_dict` |
|--------|---------------------------|------------------------------|------------|-----------|
| 3.11   | 13.44 ms                  | 12.83 ms                     | 0.80 ms    | 11.70 ms  |
| 3.12   | 15.34 ms                  | 14.79 ms                     | 0.90 ms    | 13.58 ms  |
| 3.13   | 12.95 ms                  | 12.68 ms                     | 0.78 ms    | 11.59 ms  |

Strategy A end-to-end (`load()` + `to_wire()` via the round-trip route) is ~2× `read()`
on every interpreter (0.95x–0.98x of `read()` for `to_wire()` alone, doubled by the
`load()` cost that precedes it) — consistent with the plan.md finding that a round trip
through XML costs 33.99 ms vs. today's 16.95 ms `read()`, and the reason `encode_wire`
(T008/T009) is a *direct* object walk rather than object→tree→`to_dict`.

Full raw output: see `bench_output.txt` captured during this run (not committed;
reproducible via `hatch run test:python specs/006-public-object-api/bench_to_wire.py`).

## `ruff check src tests`

```
hatch run test:lint    # ruff check src/ tests/
Found 610 errors.
357 fixable with `--fix` (222 more with `--unsafe-fixes`)
```

This is the pre-feature count SC-QUALITY-001's "net line-negative" is measured against
(T089).

## `script_documents()` population (T003)

`tests.support.corpus.script_documents()` — the corpus entries bound to the `script`
schema — returns **14** documents as of this commit (after T003b/T003c land):

```
cuems-engine/projects/complex_test/script.xml
cuems-engine/projects/empty_test/script.xml
cuems-engine/script_one_simple_cue.xml
cuems-engine/script_one_cue_in_a_cuelist.xml
cuems-engine/sample_cue.xml
cuems-engine/sample_cuelist.xml
cuems-engine/sample_audiocue.xml
cuems-engine/sample_videocue.xml
cuems-engine/sample_dmxcue.xml
cuems-editor/script_minimal.xml
legacy/script_complex_test-engine-e6fc6c9.xml
legacy/script_complex_test-engine-e7215ae.xml
cuems-utils/fade_showcase.xml          (T003c — new)
cuems-utils/unicode_showcase.xml       (T003b — new)
```

This is the population every "100% of corpus script documents" claim (SC-001 and others)
is measured against from here on. Every later "100%" claim in this feature is checkable
against this number, not aspirational.

## Discovered during Setup: a pre-existing `FadeProfile`/`CuemsParser` JSON-leg defect

Adding `fade_showcase.xml` (the first corpus document to carry a populated
`fade_profiles` pair through the JSON leg) exposed a pre-existing defect unrelated to
this feature: `FadeProfile.__json__`/`FadeFunctionParameter.__json__` self-wrap as
`{"FadeProfile": {...}}`, and `CuemsParser` rebuilds that shape without unwrapping it,
so the re-written XML gets a literal `<FadeProfile>` tag instead of `<fade_profile>`.
No corpus document exercised this path before (corpus-sweep.md found zero fade coverage
anywhere). `FadeProfile.py:63`/`:157` are exactly the hand-written `__json__` bodies
T035 deletes and T026/T036 replace with the derived projection, which does not
self-wrap — so this is expected to clear once US2 lands. Marked as a scoped, documented
`xfail` in `tests/integration/test_d14_chain.py` (two parametrized cases) rather than
worked around, so it stays visible until US2 removes it. If it is still failing after
T036, that is a real regression, not an artifact of this note.

## Discovered during Foundational: `read()`'s golden and the decoded object legitimately diverge

`encode_wire` (T008/T009) faithfully projects what a decoded object *holds*. For two corpus
documents (`complex_test/script.xml`, `script_minimal.xml`), that is not byte-identical to
`dict/*.reader.json` as literally captured: `VideoCue.opacity` is optional in the schema and
defaults to `100` in the object model (`VideoCue.py` `REQ_ITEMS`), and `from_decoded`
(feature 005, unrelated to and predating this feature) materializes every declared default a
decoded object's document omits — including optional fields whose default is a real,
non-empty value. `read()` never touches the object model, so its raw dict has no key at all
for an omitted optional field; the decoded object does, once defaulted.

**Confirmed pre-existing, not introduced here**: the *frozen* `tests/golden/xml/*.xml` write
goldens (captured before this feature, untouched by it) already contain
`<opacity>100</opacity>` written into documents whose source never had the element — proof
this materialization already happened, and was already accepted, before `encode_wire` existed.

**Resolution**: `tests/contract/test_wire_byte_identity.py` adjusts the oracle mechanically —
from the schema and each bound model's `declared_defaults()`, not by naming `opacity`
specially — rather than either weakening `encode_wire` or touching feature 005's tested
`from_decoded` behaviour. Both were considered and rejected: weakening `encode_wire` would
make it lie about what the object holds, and touching `from_decoded` risks regressing
already-shipped, already-tested behaviour for a concern outside this feature's scope. Grep
of `script.xsd` for other optional fields with a non-empty Python default found one further
candidate (`ActionCue.action_type` defaults to `'play'`) that has not yet manifested a
mismatch in the current corpus but would take the same, already-generic fix if it ever does.

## Performance budgets (for T083)

- `load()` + `to_wire()` ≤ 25 ms — baseline `read()` = 16.95 ms (plan.md figure; this
  run measured 12.95–15.34 ms across interpreters, within the same order).
- `to_wire()` alone ≤ 5 ms — baseline tree build = 1.09 ms (plan.md figure; this run
  measured 0.78–0.90 ms).
- Suite ≤ 10% over 44.57 s — baseline wall time for pytest itself: 35.49 s.
- Write path ≤ 10% regression — baseline not yet isolated; see T083.

---

# T083 — the budgets, measured

**Date**: 2026-08-20 · **Script**: the method `bench_to_wire.py` uses, applied to
the shipped surface.

## Measurement context, stated so the numbers are reproducible (CHK041)

| | |
|---|---|
| Machine | `despatx` — AMD Ryzen 5 3600, 6 cores |
| Python | 3.11.9 under pyenv, in the `hatch-test.py3.11` environment |
| Process | **warm** — 3 untimed warmup iterations, then 30 samples |
| Statistic | **median** of 30 (the `max` column shows the first-call outlier) |
| Document | `tests/data/corpus/cuems-engine/projects/complex_test/script.xml`, 24 183 bytes |

## Results

```
  read()          [pre-feature project_load]     16.65 ms  (min 15.88, max 32.01)
  CuemsScript.load()                             17.51 ms  (min 17.05, max 34.81)
  to_wire()                                       0.74 ms  (min  0.71, max  0.92)
  to_json()                                       1.29 ms  (min  1.27, max  1.39)
  build_tree()    [objects -> ElementTree]        1.10 ms  (min  1.07, max  1.35)
  validate()      [T1 + T2]                      14.88 ms  (min 14.05, max 35.38)
  save()          [build + T1 + T2 + atomic write] 15.51 ms  (min 14.81, max 39.32)
  write_from_object()  [pre-feature write]       14.52 ms  (min 13.92, max 32.36)
  run_rules()     [the T2 tier alone]             0.93 ms  (min  0.90, max  1.06)
```

## Against the budgets

| Budget | Limit | Measured | |
|---|---:|---:|---|
| `load()` + `to_wire()` | ≤ 25 ms | **18.25 ms** | ✅ |
| `to_wire()` alone | ≤ 5 ms | **0.74 ms** | ✅ |
| Write path regression | ≤ 10 % | **+6.8 %** | ✅ |
| Suite wall time | ≤ 10 % over 44.57 s | **59.17 s (+32.8 %)** | ❌ as stated — see below |

### `to_wire()` is a direct projection, and the number proves it

T083 names the check explicitly: *"if `to_wire()` lands near 16 ms the direct
projection has silently become the round trip."* It landed at **0.74 ms** — a
twentieth of that, and *below* the 1.10 ms tree build alone, which is the half
of the round trip that cannot be avoided. The measured design decision holds:
the round trip would have cost 33.99 ms against today's 16.95 ms `read()`, and
it is kept as the **test oracle** (`test_wire_oracle.py`) rather than as the
implementation.

### The write path's +6.8 % is the T2 tier, and it is accounted for

`save()` does everything `write_from_object` did — build, schema-validate,
write — **plus** the semantic tier and an atomic rename. `run_rules()` measures
**0.93 ms**, which is 6.0 % of `save()`: the regression is the tier, essentially
exactly, and nothing else moved.

### The suite budget is exceeded as literally written, and should not be read as a regression

44.57 s → 59.17 s is +32.8 %, well past the 10 % the budget allows. The budget
compares **wall time** and the suite is not the same suite:

| | baseline | now |
|---|---:|---:|
| tests | 1 485 | 2 222 |
| wall time | 44.57 s | 59.17 s |
| **per test** | **30.0 ms** | **26.6 ms** |

737 tests were added by this feature — the contract tests for the public
surface, the payload parity and wire-format guards, the config object surface,
the rule registry, the fade coverage. Per test the suite got **11 % faster**,
which is what the schema cache in `xml/documents.py` bought.

Recorded as **exceeded**, not restated as passing. A budget whose terms are
rewritten after the measurement is not a budget. What the number says is that
the *stated* form of this one (absolute wall time, against a suite the feature
was always going to grow) could not survive contact with the feature; the
per-test figure is offered as the comparison that does mean something, and a
future feature should set the budget in those terms.

## What did not need measuring, and why

`load()` at 17.51 ms against `read()`'s 16.65 ms is +5 %, and all of it is the
decode step `read()` does not perform — `read()` returns a raw dict, `load()`
returns coerced objects. They are not the same operation and the comparison is
here only because the two sit at the same place in the editor's flow.

---

# T089 — lint and line count, reported as measured

## `ruff check src tests`

**Not clean, and it was not clean before this feature either.** The project's
own configuration (`select = ["E", "F", "W", "I"]`, `ignore = ["E501"]`)
reported **605** findings on the tree this feature started from and reports
**591** now.

| | findings |
|---|---:|
| `38038f1` (before US1) | 605 |
| now | **591** |
| delta | **−14** |

**Every file this feature adds is clean** — all 31 of them, checked
individually: `src/cuemsutils/config/*`, `errors.py`, `xml/documents.py`, and
every new test module and support helper. The 591 are pre-existing: trailing
whitespace, unsorted imports and unused imports in modules this feature does not
touch, plus `f`-strings without placeholders in the tools package.

T089 asks for "clean, no new warnings". The second half is met and asserted; the
first half was already false when the feature began, and making it true means a
repo-wide `ruff --fix` — which would reformat modules the byte-identity goldens
are measured against, for no benefit to this feature. Recorded rather than
silently reinterpreted.

## SC-QUALITY-001: net line-negative — **not met**

| | lines |
|---|---:|
| `git diff --shortstat` over `src/` | +2 844 / −774 = **+2 070** |
| executable code only (blank, comment and docstring lines excluded) | 5 104 → 5 577 = **+473** |

The raw diff overstates it — most of the +2 070 is prose, and this feature's
whole method is writing down *why* rather than only *what*. The +473 figure is
the honest one, and it is still positive.

**Why, and whether it should have been.** The feature deletes a great deal:
~355 lines of frozen parser tree, six hand-written `__json__` bodies, three
compensations, two unreachable `check_mappings` fossils, a dead XML builder and
a dead reshaping helper. It also *adds* four things that did not exist:

- `src/cuemsutils/config/` — 22 model classes across four modules, which is the
  structure that let the compensations be deleted at all;
- `src/cuemsutils/errors.py` — the public exception hierarchy;
- `src/cuemsutils/xml/documents.py` — read/build/validate/atomic-write, split
  out of `XmlReaderWriter` so it can become a shim over the public surface;
- the T2 rule registry in `xml/validators.py` — fifteen named rules where there
  had been fourteen anonymous setter bodies and three loose functions.

Three of those four are *net new capability*, not refactoring, so a line-negative
outcome was never available without dropping one of them. The success criterion
was written on the assumption that the feature was mostly deletion; it is
mostly deletion **plus** the object layer FR-014 requires.

Stated as **not met** rather than reframed. What can be claimed instead, and is
checkable: every deletion the plan enumerated happened, and
`tests/unit/test_mappings_shape.py` and
`tests/contract/test_no_internal_deprecation.py` assert the deleted things are
gone by name rather than by count.

---

# T091 — final suite

```
PYENV_VERSION=3.11.9 pyenv exec hatch test --show
```

**2222 passed, 94 skipped, 2 xfailed** in ~59 s (2026-08-20).

| | start (`38038f1`) | end |
|---|---:|---:|
| passed | 1 587 | **2 222** |
| skipped | 49 | 94 |
| xfailed | 4 | 2 |

Two `xfail`s cleared during the feature and were **removed** rather than
relaxed, because a strict `xfail` that starts passing is information:

- the `fade_showcase` json-leg mark, whose own comment predicted T035/T036
  would clear it — and did;
- `test_built_and_json_decoded_have_identical_internal_types` was *not* an
  xfail but is worth naming here: its unqualified "zero differences" held only
  while the JSON payload was a separate, richer encoding, and making the two
  payloads one costs exactly that. The assertion now pins the residual by group
  and a sibling test asserts the JSON leg diverges in no group the XML leg does
  not.

The skip count rose from 49 to 94, and all of the increase is parametrised
guards skipping documents outside their scope — `test_config_object_surface`
skipping accessors that raise before `load_project_config`, and the config
surface sweeps skipping non-config corpus entries. No test was skipped to make
it pass.
