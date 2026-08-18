# Contract: deprecations and the migration map

**Feature**: 006-public-object-api · **Date**: 2026-08-18

Old entry points are **deprecated in this release, removed in the next** — after consumers
migrate (feature 008). Shipping the replacement before removing the old path is what keeps
the UI contract intact while `cuems-editor` is still on the old call.

---

## D1 — Mechanism: reuse, do not reinvent

`src/cuemsutils/xml/_deprecation.py` already exists and already solves this: `deprecated==1.2.18`,
one message template, `REMOVAL_RELEASE = "v0.1.1"`, warning on **every call** rather than once
per import, correct `stacklevel` so the caller's line is reported. Its docstring is explicit
that it *"must not grow into a second warning system"*.

Message format, unchanged: `use <replacement> instead; removed in v0.1.1`

### The import-ordering hazard — do not remove those two lines

`xml/__init__.py` opens with:

```python
from . import Settings as _settings_shim          # noqa: F401
from . import XmlReaderWriter as _xml_reader_writer_shim  # noqa: F401
```

`Settings.py` and `XmlReaderWriter.py` are **real submodules**, so the first import of either
makes Python bind it as an attribute of the package — clobbering the same-named *class*.
Importing them first forces that assignment to happen before the class bindings, so the
classes win permanently.

Setting `__all__ = []` must **not** remove these imports. Doing so resurrects a
`TypeError: 'module' object is not callable` that has already been diagnosed and fixed once.

## D2 — The migration map

| Removed from public API | Replacement | Consumer sites |
|---|---|---|
| `XmlReaderWriter(schema_name="script", xmlfile=p).read_to_objects()` | `CuemsScript.load(p)` | `cuems-engine` `BaseEngine.py:509` |
| `XmlReaderWriter(...).read()` → raw dict | `CuemsScript.load(p).to_wire()` | `cuems-editor` `CuemsDBProject.load_xml` |
| `XmlReaderWriter(...).write_from_object(obj)` | `script.save(p)` | `cuems-editor` `CuemsDBProject.save_xml` |
| `XmlReaderWriter(schema_name="script", xmlfile=None).validate_object(obj)` | `script.validate()` | `create_script.validate_template` (first-party, migrated **in** this feature) |
| `CuemsParser(payload).parse()` | `CuemsScript.from_json(payload)` | `cuems-editor`, 3 sites |
| `Settings`, `NetworkMap`, `ProjectMappings`, `ProjectSettings` | `ConfigManager` accessors | `cuems-engine` `ControllerEngine.py:249`, `cuems-editor` `CuemsWsServer.py:470` |
| `schema_name="script"` argument | *(nothing — it is a property of the type)* | 6 sites, 3 repos |
| `XmlReader` / `XmlWriter` | already deprecated since 0.0.7 | `cuems-nodeconf` |

**Consumer repositories are not edited by this feature.** The map is the deliverable; the
edits are feature 008. The one exception is `create_script.py`, which is first-party code in
this repository and migrates here.

## D3 — What is deleted outright (never public)

Not deprecated, because nothing outside this package could reach them:

- `Parsers.py`'s frozen legacy tree below `CuemsParser.parse()` — ~430 unreachable lines. The
  module's own docstring schedules the deletion for this feature.
- `settings.py`'s dead `data2xml` / `buildxml` / `process_network_mappings`.
- The eight hand-written `__json__` methods, replaced by the derived projection.
- `ConfigManager`'s three shape compensations.
- The two unreachable `check_mappings` bodies in `VideoCue` and `AudioCue` (F15's fossils).

## D4 — Verification

| Guarantee | Test |
|---|---|
| Every deprecated entry point still resolves and works | import and exercise each; result equals the new API's |
| Each warns exactly once per call, not per import | call twice, assert two warnings |
| Message names replacement and removal release | assert both substrings |
| The two shim imports survive | `from cuemsutils.xml import Settings` yields a **class**, not a module, and is callable |
| Nothing public remains in `xml/` | `__all__ == []` and the API golden diff is the enumerated set |
| Deleted code is unreachable first | coverage shows zero hits on the legacy tree before deletion |
