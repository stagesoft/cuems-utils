# Types that reach a generic today

**Feature**: `004-xml-serialization-core` | **Task**: T041 | **Date**: 2026-08-11
**Requirement**: FR-007 | **Method**: instrumentation, not inspection

Every name that misses its `globals()` lookup in `Parsers.py` / `XmlBuilder.py` and falls
back to a generic, measured by wrapping `get_parser_class`, `get_class` and
`get_builder_class` and driving the **whole corpus** — all 28 vendored documents plus the
generated one — through read, object build and write.

This list is the input to the explicit registry. FR-007's rule is that each of these binds
**to the same generic it reaches today**: registry completeness means *accounted for*, not
*given a bespoke class*. Promoting any one of them to a bespoke handler would change the
output, which is exactly what this feature forbids.

Research R9 estimated "roughly 13 of script.xsd's 33 types". Measured across all six
schemas the figure is **17 parser misses, 7 class misses and 12 builder misses** — the
estimate was for one schema and one of the three lookups.

---

## 1. Parser misses — `class_string + 'Parser'` not found → `GenericParser`

| Name | Hits | Note |
|---|---|---|
| `offset` | 23 | `CTimecodeType` |
| `postwait` | 23 | `CTimecodeType` |
| `prewait` | 23 | `CTimecodeType` |
| `ui_properties` | 20 | wildcard type (R6) |
| `timeline_position` | 18 | inside `ui_properties`, so also wildcard |
| `Media` | 13 | **has** a `mediaParser`, lowercase — the name mangling misses on case |
| `file_name` | 13 | plain string |
| `regions` | 13 | `RegionsType` |
| `VideoCue` | 8 | cue type |
| `AudioCue` | 5 | cue type |
| `number_of_nodes` | 4 | settings |
| `Settings` | 2 | settings root |
| `node_list` | 2 | network map |
| `ActionCue` | 1 | cue type |
| `icon` | 1 | inside `ui_properties` |
| `video_outputs` | 1 | outputs |
| `{…XMLSchema-instance}schemaLocation` | 1 | the leaked attribute (F23) |

### `Media` is the one worth pausing on

`mediaParser` **exists** (`Parsers.py:258`) and is never found: the lookup builds
`'Media' + 'Parser'` = `MediaParser`, while the class is spelled `mediaParser`. Thirteen
hits across the corpus, every one silently falling through to `GenericParser`.

The class is not dead — it is simply unreachable by the name the lookup constructs. This is
the clearest single illustration of why FR-007 replaces `globals()`: an implicit lookup
cannot report a miss, so a handler can be written, imported, and never called, for as long
as anyone cares to maintain it.

**It stays unreachable in this feature.** Binding `MediaType` to `mediaParser` would start
using a code path that has never run, which is a behaviour change. It is bound to the
generic it actually reaches, and the discrepancy is recorded for feature 005.

### `AudioCue` / `VideoCue` / `ActionCue` are not what they look like

These names appear as misses even though `AudioCueParser` does not exist — the cue types
are handled by `CuemsScriptParser` reached through a different path. They are listed for
completeness; their output is unchanged.

---

## 2. Class misses — tag not found in `globals()` → `GenericDict`

| Name | Hits |
|---|---|
| `ui_properties` | 20 |
| `regions` | 13 |
| `number_of_nodes` | 4 |
| `Settings` | 2 |
| `node_list` | 2 |
| `video_outputs` | 1 |
| `{…XMLSchema-instance}schemaLocation` | 1 |

`ui_properties` misses because the Python class is spelled `UI_properties` — the same
case-mangling failure as `Media`, from the other direction. It is bound to `GenericDict`,
which is what it reaches today.

---

## 3. Builder misses — `type(obj).__name__ + 'XmlBuilder'` → `GenericCueXmlBuilder`

| Python type | Hits | Note |
|---|---|---|
| `dict` | 25 | plain dicts inside wildcard content |
| `CuemsDict` | 10 | the library's own dict subclass |
| `Region` | 4 | `RegionType` |
| `int` | 4 | scalars reaching the builder dispatch |
| `ActionCue` | 3 | |
| `list` | 3 | |
| `DmxChannel` | 2 | |
| `DmxCue` | 2 | |
| `DmxCueOutput` | 2 | |
| `DmxUniverse` | 2 | |
| `FadeCue` | 2 | |
| `str` | 1 | |

That `int`, `str`, `list` and `dict` reach a *builder class* lookup at all shows the
dispatch is running on values as well as on model objects. The engine's registry binds
types, and scalars are handled by adapters before dispatch is reached — so these entries
have no registry counterpart. They are recorded because their **output** must not change.

---

## How this list is used

`registry.py` binds every complex type in every schema. Types on this list bind to the
generic they reach today (`GenericDict` on decode, `GenericCueXmlBuilder` on encode). The
registry raises at build time for any complex type left unbound, naming it — which is the
half `globals()` could never do.

**Regenerate** with the instrumentation in the T041 probe if the corpus grows; do not edit
by hand. A hand-edited list is an assertion about code rather than a measurement of it,
which is the failure mode this whole document exists to avoid.
