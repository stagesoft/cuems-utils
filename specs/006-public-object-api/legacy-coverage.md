# The legacy parser tree was unreachable — measured (T060, D4)

**Feature**: 006-public-object-api · **Date**: 2026-08-20

T063 deletes ~355 lines from `src/cuemsutils/xml/Parsers.py`: the sixteen frozen
`*Parser` classes that `CuemsParser.parse()` used to drive. D4 requires the
unreachability to be **measured before** the deletion, not argued.

## Method

The whole suite, under coverage restricted to the one file:

```bash
python -m coverage run --rcfile=/dev/null \
  --include='*/cuemsutils/xml/Parsers.py' \
  -m pytest -q --no-header \
  --deselect tests/test_fade_cue.py::test_fade_cue_construction_performance \
  tests
python -m coverage report --rcfile=/dev/null \
  --include='*/cuemsutils/xml/Parsers.py' --show-missing
```

`--rcfile=/dev/null` is not incidental: the project's coverage configuration
sets its own `source`, which overrides `--include` and reports the whole
package instead of the one file being interrogated.

One deselection, and it is not a carve-out from the measurement: coverage
instrumentation slows execution enough that
`test_fade_cue_construction_performance` — a wall-clock budget assertion —
fails under it. It exercises no parser.

## Result, before the deletion

```
Name                            Stmts   Miss  Cover   Missing
-------------------------------------------------------------
src/cuemsutils/xml/Parsers.py     258    170    34%   46-48, 57-65, 68-73, 76,
                                                     79, 98, 108, 137-140,
                                                     143-152, 156-157, 160-185,
                                                     189-192, 195-234, 238-239,
                                                     245-247, 275-296, 300,
                                                     303-312, 330-336, 349-351,
                                                     358-365, 376-393, 400-416,
                                                     421, 424
-------------------------------------------------------------
TOTAL                             258    170    34%
```

`CuemsParser.parse()` ends at line **133**. Every executable line from **135**
to the end of the tree is in the Missing set — `CuemsScriptParser`,
`CueListParser`, `GenericParser`, `GenericSubObjectParser`, `CTimecodeParser`,
`mediaParser`, `outputsParser`, `CuemsNodeDictParser`, the three
`*CueOutputParser`s, `DmxCueParser`, `fade_profilesParser`,
`_normalize_fade_parameters`, `fade_profileParser` and `NoneTypeParser`.

**Zero hits below `parse()`.** That is the claim D4 asks for.

### What the 34% that *is* covered consists of

The module still executes, so the number is not "34% of the tree ran". It is
the part that stays:

- the module's import block and its constants (`STRING_TYPED_KEYS`,
  `PARSER_SUFFIX`, `XML_ROOT_TAG`);
- `GenericDict`, imported by `XmlBuilder.py`;
- `CuemsParser.__init__` and `parse()`, which delegate to
  `Mapper.decode_document`;
- `CuemsParser.get_parser_class` / `get_class` / `str_to_value`, reached only
  by `test_name_coercion` and `test_type_coercion_live_paths`, which read them
  deliberately as retired history rather than as live paths. Their partial
  misses (46-48, 57-65, 68-73, 76, 79, 98, 108) are branches those tests do not
  take.

## Result, after the deletion

The same command, same method:

```
Name                            Stmts   Miss  Cover   Missing
-------------------------------------------------------------
src/cuemsutils/xml/Parsers.py      69     20    71%   46-48, 57-65, 68-73, 76,
                                                     79, 98, 108
-------------------------------------------------------------
TOTAL                              69     20    71%
```

258 statements → **69**. Every remaining miss is inside `get_parser_class`,
`get_class` and `str_to_value` — the branches the two coercion-history tests do
not take — and *nothing* below `parse()` remains to miss. The before/after pair
is what makes the deletion checkable: the lines that disappeared are exactly the
lines that were never executed.

## Why this is evidence rather than a formality

The tree was frozen by feature 004 and its unreachability *asserted* in
`parse()`'s own docstring: *"Everything below this method in the module is the
frozen legacy tree it used to drive. It is unreachable from here now."* An
assertion in a docstring is exactly the kind of claim that stops being true
without anyone noticing — `_normalize_fade_parameters` was added to that tree
*after* it was frozen, which is what makes measuring rather than trusting the
right call.

Two guards outlive this document:

- `tests/contract/test_no_internal_deprecation.py::test_the_deleted_parser_tree_is_actually_gone`
  names all fifteen deleted classes individually, so reintroducing one fails
  loudly. A count would pass if one came back while another went.
- The same module's C8 sweep runs the whole corpus through the library's public
  entry points and asserts **zero** deprecation warnings, with a control that
  calls a frozen symbol directly to prove the warnings still work.

## What was kept, and why

| Symbol | Why it survives |
|---|---|
| `CuemsParser` | the entry point. `parse()` delegates; the class carries a deprecation warning at `cuemsutils.xml.CuemsParser` (T061) — which it could not do while the library still called it, hence T061a moving `write_from_dict` and `read_to_objects` off it first |
| `CuemsParser.str_to_value` | the retired type-guessing heuristic. `test_name_coercion` reads it to assert the defect class (a cue named `n` saved as `False`) is now unrepresentable rather than merely unreached |
| `STRING_TYPED_KEYS` | the denylist that held that heuristic's damage back. Read as a value, so it cannot warn; kept as named history beside what it protected |
| `GenericDict` | imported by `XmlBuilder.py`, itself a frozen shim. Deleting it breaks that module's **import**, not just its behaviour |
