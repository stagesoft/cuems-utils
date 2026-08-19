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
