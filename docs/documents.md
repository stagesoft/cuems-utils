# Documents: reading and writing

`cuemsutils.xml` is internal and exports nothing. A show and a node's configuration are read and
written through the public objects.

## A show: `CuemsScript`

```python
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import Outcome, SchemaError, ValidationError

script = CuemsScript.load("project/script.xml")
script, report = CuemsScript.load_with_report("project/script.xml")
if report.outcome is not Outcome.CLEAN:
    for repair in report.repairs:          # what was repaired, from what, by which rule
        print(repair.field_path, repair.previous_value, "->", repair.substituted_value, repair.rule_name)

script.validate()                          # a ValidationReport; falsy when clean
script.save("project/script.xml")          # T1 + T2 first; nothing is written if either fails

payload = script.to_json()                 # and back: CuemsScript.from_json(payload)
wire = script.to_wire()                    # the JSON-ready projection a UI consumes
```

**Every read is strict.** The schema (T1) and the semantic rules (T2) run on every load:

| The document | `load_with_report` |
|---|---|
| valid and current | `Outcome.CLEAN` |
| a schema version behind | converted **in memory** (the file is untouched), `Outcome.CONVERTED` |
| a repairable T2 violation | the field is set to its declared default, `Outcome.REPAIRED`, one `RepairRecord` each |
| an unrepairable T2 violation | raises `ValidationError` |
| structurally invalid | raises `SchemaError` |
| newer than the library | raises, distinguishably |

## A node's configuration: `ConfigManager`

`ConfigManager` reads `settings.xml`, `network_map.xml`, `project_mappings.xml` and
`project_settings.xml` from `CUEMS_CONF_PATH` (default `/etc/cuems`) and answers with objects.
It writes them back with `save_settings`, `save_network_map`, `save_project_mappings` and
`save_project_settings`. `ConfigManager.from_json(schema, payload)` builds one from JSON,
`to_wire(section)` projects one, and `get_schema_descriptor()` describes every schema (types,
enumerations, defaults, repairability) for a UI. See [Tools](tools.md).

To validate one document without an installation:

::: cuemsutils.tools.config_validate

## The bundled schemas

They live in `src/cuemsutils/xml/schemas/` and are installed to `/usr/share/cuems/schemas/`:
`script.xsd`, `settings.xsd`, `network_map.xsd`, `project_mappings.xsd`,
`project_settings.xsd` and `hardware_outputs.xsd`.

## Migrating documents

Run `cuems-reshape-devices`, then `cuems-convert-documents`, each with a path or with `--check`.
The first rewrites the pre-013 device shape, and the second upgrades the schema version. Both back
up a document before rewriting it, and both report every document the loader would refuse
afterwards.

!!! warning "Deprecated in 0.1.1, removed in v0.1.2"
    `XmlReaderWriter`, `XmlBuilder` and `Parsers` still import, with a warning. Do not use them in
    new code. Use `CuemsScript` and `ConfigManager` instead.
