# Migration map: shim → replacement → consumer call site

**Feature**: `004-xml-serialization-core` | **Tasks**: T031, T031a | **Date**: 2026-08-11
**Requirement**: FR-028 | **Input to**: feature 009 (consumer migration), feature 007
(the `cuems-nodeconf` fix)

Every symbol this feature deprecates, what replaces it, and which consumer code reaches it.
Call sites were enumerated by grep across the three sibling checkouts on the date above;
that was a **one-time read**, not an ongoing dependency (FR-022b) — no test in this
repository resolves a path outside it.

**No file outside this repository is edited by feature 004.**

---

## 1. Import-path renames (D9)

Both old modules survive as shims. Importing them is silent; calling anything they export
warns on **every** call, at the caller's line, naming the replacement and `v0.1.1`
(FR-027a, FR-027b).

| Deprecated symbol | Replacement | Consumer call sites |
|---|---|---|
| `cuemsutils.xml.XmlReaderWriter.XmlReaderWriter` | `cuemsutils.xml.xml_reader_writer.XmlReaderWriter`, or `from cuemsutils.xml import XmlReaderWriter` | `cuems-editor/src/cuemseditor/CuemsDBProject.py:9`, `repair_durations.py:40`, `tests/test_repair_durations.py:6` |
| `cuemsutils.xml.XmlReaderWriter.CuemsXml` | `cuemsutils.xml.xml_reader_writer.CuemsXml` | none found |
| `cuemsutils.xml.XmlReaderWriter.get_pkg_schema` | `cuemsutils.xml.xml_reader_writer.get_pkg_schema` | none found (in-repo test only) |
| `cuemsutils.xml.XmlReaderWriter.XmlReader` / `.XmlWriter` | `cuemsutils.xml.xml_reader_writer.XmlReaderWriter` | `cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py:17`, `test_xml_roundtrip.py:23`, `cuems-engine/dev/CuemsEngine_old.py:13` |
| `cuemsutils.xml.Settings.Settings` | `cuemsutils.xml.settings.Settings`, or `from cuemsutils.xml import Settings` | none found directly |
| `cuemsutils.xml.Settings.NetworkMap` | `cuemsutils.xml.settings.NetworkMap` | `cuems-engine/src/cuemsengine/ControllerEngine.py:12` |
| `cuemsutils.xml.Settings.ProjectMappings` | `cuemsutils.xml.settings.ProjectMappings` | none found directly |
| `cuemsutils.xml.Settings.ProjectSettings` | `cuemsutils.xml.settings.ProjectSettings` | none found directly |

`XmlReader` and `XmlWriter` were **already** deprecated in 0.0.7 in favour of
`XmlReaderWriter`. The rename deprecates them a second time; they now emit two records per
instantiation, one per decorated ancestor. Three call sites still use them.

Imports through the **package root** — `from cuemsutils.xml import XmlReaderWriter`,
`NetworkMap`, … — are **not** deprecated and need no change. That covers
`cuems-editor/src/cuemseditor/CuemsWsServer.py:23`,
`cuems-engine/src/cuemsengine/core/BaseEngine.py:17` and
`cuems-engine/tests/test_default_mappings_valid.py:9`. This is worth stating plainly,
because it means most consumer code needs no edit at all.

---

## 2. Frozen legacy implementations

Not replaced symbol-for-symbol: they are the four duplicated mapping implementations this
feature collapses into one engine. Their replacement is the engine, which is **internal in
004** (Q14) and becomes public API in feature 006. Consumers reaching them directly have no
supported target until then, which is why removal is `v0.1.1` and the migration is feature
009's job rather than a same-release expectation.

| Deprecated symbol | Replacement | Consumer call sites |
|---|---|---|
| `Parsers.GenericDict` | engine registry generic binding | `cuems-nodeconf/cuemsnodeconf/NodeXmlBuilders.py:10`, `test_xml_roundtrip.py:22` |
| `Parsers.GenericParser` | engine `mapper.decode` | `cuems-nodeconf/.../NodeXmlBuilders.py:10`, `test_xml_roundtrip.py:22` |
| `Parsers.CuemsScriptParser`, `CueListParser`, `CTimecodeParser`, `mediaParser`, `outputsParser`, `CuemsNodeDictParser`, `AudioCueOutputParser`, `VideoCueOutputParser`, `DmxCueOutputParser`, `DmxCueParser`, `fade_profilesParser`, `fade_profileParser`, `GenericSubObjectParser`, `NoneTypeParser` | engine `mapper.decode`, driven by `TypeSpec` | none found |
| `Parsers.CuemsParser.str_to_value` | schema-declared types — the engine does not guess (FR-003) | `cuems-nodeconf/cuemsnodeconf/NodeXmlBuilders.py:101` (via `self.str_to_value`), `cuems-nodeconf/tests/test_node_field_coercion.py` |
| `XmlBuilder.XmlBuilder` and the whole `*XmlBuilder` family | engine `mapper.encode_xml` | `cuems-nodeconf/.../NodeXmlBuilders.py:8`, `test_xml_roundtrip.py:20` |

### 2.1 Deprecated but unable to warn

Two symbols are values, not callables. They are read in `isinstance` / membership checks
and never invoked, so there is no call for a warning to attach to. Listed here because this
table is the only place their retirement is recorded — and because claiming they warn, when
they cannot, would be worse than saying so.

| Symbol | Kind | Replacement | Consumer call sites |
|---|---|---|---|
| `Parsers.STRING_TYPED_KEYS` | `frozenset` | nothing — the denylist exists only to protect `str_to_value`, and both retire together | `cuems-nodeconf/tests/test_node_field_coercion.py` |
| `XmlBuilder.VALUE_TYPES` | `tuple[type, ...]` | adapter table, bound by XSD type qname | `cuems-nodeconf/.../NodeXmlBuilders.py:8`, `test_xml_roundtrip.py:20` |

### 2.2 `CuemsParser` is **not** deprecated

The one symbol in `Parsers.py` that emits nothing, deliberately (Assumption 3a, FR-026d).
It becomes the engine's delegating facade at T048 and stays a supported entry point:

- it was already library-internal before this feature — `XmlReaderWriter.write_from_dict`
  and `read_to_objects` both call it;
- it is `cuems-editor`'s primary JSON → object path, at
  `CuemsDBProject.py:8` and `repair_durations.py:39`;
- contract C8 runs the whole corpus through the library's own entry points and requires
  **zero** deprecation warnings. A warning on `CuemsParser` would fail the very test that
  proves the library no longer calls its own retired code.

Its method `str_to_value` **is** deprecated, which is not a contradiction: the class
survives, the type-guessing heuristic does not.

---

## 3. Declared breaking change — FR-026d (T031a)

Exactly one call site cannot be kept working. Under FR-030a that is an acceptable outcome
but never a silent one, so it is named here, flagged in `CHANGELOG.md`, and asserted by
contract **C11** / test `tests/contract/test_declared_break_nodeconf.py` (T049a).

### What breaks

| | |
|---|---|
| **Symbol** | the `globals()` handler lookup in `CuemsParser.get_parser_class` and `XmlBuilder.get_builder_class` |
| **Affected consumer** | `cuems-nodeconf` — the only one |
| **Call sites** | `cuems-nodeconf/cuemsnodeconf/NodeXmlBuilders.py:105-111`, `cuems-nodeconf/test_xml_roundtrip.py:96-99` |
| **Carrier of the fix** | **feature 007** (FR-030b scheduling clause) |
| **Asserted by** | C11 / SC-017 |

`cuems-nodeconf` registers its node handlers by writing into the private module namespaces
of this library:

```python
XmlBuilderModule.node_listXmlBuilder = node_listXmlBuilder
XmlBuilderModule.nodeXmlBuilder      = nodeXmlBuilder
ParsersModule.node_listParser        = node_listParser
ParsersModule.nodeParser             = nodeParser
```

`get_parser_class` then resolves `class_string + 'Parser'` through `globals()` of
`Parsers.py`, and finds the injected name.

### Why no shim can preserve it

Honouring an injected name means keeping the implicit `globals()` lookup — which is
precisely what FR-007's explicit registry exists to delete. Preserving the injection and
deleting the lookup are the same decision made two ways, so the alternative to this break
is abandoning the feature's premise. It is declared rather than discovered.

### What does *not* break

The imports still resolve. The four assignments still execute without error. Only their
**effect** is gone: the engine resolves the type through its registry and never consults
the module globals. That silence is exactly why the break has to be pinned by a test rather
than left to be noticed — nothing raises, nothing logs, and the node simply serializes
through a generic instead of through `nodeXmlBuilder`.

### Why the fix is not in this feature

The fix must target the engine's registry, which is **internal in 004**, becomes **public
API in 006**, and **absorbs the node model in 007**. Written against 004's intermediate
shape it would be rewritten twice. `cuems-nodeconf` is already an out-of-date repository
whose serialization work lives on the unlanded `feat/nodeconf-reenable` branch, so it is not
shipping against this release and the deferral costs nothing.

`feat/nodeconf-reenable` now **feeds** feature 007 rather than gating it.

### No further unsupportable call site was found

T031a requires any *additional* unsupportable call site discovered during T031 to be
recorded the same way. The inventory above found none: every other consumer call site is
either a package-root import (unaffected) or a deprecated-but-working shim path.

---

## 4. Release-time review — FR-030c layer (ii)

In-repo tests (`tests/contract/test_deprecation_shims.py`) cover every shimmed path and
need no sibling checkout, which is what keeps FR-022b and SC-015 true. They cannot,
however, prove that a *particular consumer's* code still works — only that the symbols it
imports still resolve and behave.

So compatibility is gated in two layers. Layer (ii) is a checklist step outside the suite:
before release, walk §1 and §2 of this table against each sibling repository and confirm
each call site still resolves. That review is also what hands feature 007 its input.

| Repository | Call sites | Status at this release |
|---|---|---|
| `cuems-editor` | 6 | ✅ all work unmodified (SC-013) |
| `cuems-engine` | 5 | ✅ all work unmodified (SC-013) |
| `cuems-nodeconf` | 11 | ⚠️ 10 work; the handler injection is **broken by design** (FR-026d) |
