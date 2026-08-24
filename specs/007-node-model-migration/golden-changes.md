# Golden changes — feature 007

Two transformations to the `network_map` corpus and its goldens, kept in separate sections so a
reviewer never has to disentangle them from one diff (R8a, C4a).

---

## 1. Corpus normalisation (T006b–T006e) — whitespace and `schemaLocation` only

**Commit scope**: `tests/data/network_map.xml`, `tests/data/corpus/{cuems-utils,cuems-engine,cuems-common}/network_map.xml`,
and the four goldens their normalisation invalidates.

**What changed**: each document was reformatted to the writer's output form —
`build_document`'s style (research R8a, `mapper.py:942-950`): the XML declaration on its own line,
everything else on one line with no indentation, and `xsi:schemaLocation` carrying the bare schema
filename rather than an absolute path.

| File | Before | After |
|---|---|---|
| `tests/data/network_map.xml` | 4-space indented; `schemaLocation=".../etc/cuems/network_map.xsd"` | unindented; `schemaLocation="https://stagelab.coop/cuems/ network_map.xsd"` |
| `tests/data/corpus/cuems-utils/network_map.xml` | same as above (identical content) | same |
| `tests/data/corpus/cuems-engine/network_map.xml` | 4-space indented; `schemaLocation="https://stagelab.coop/cuems/ https://stagelab.coop/cuems/network_map.xsd"` | unindented; bare filename |
| `tests/data/corpus/cuems-common/network_map.xml` | 4-space indented; **no** `schemaLocation` attribute; root child is `<CuemsNodeDict>`, not `<node_list>` (already schema-invalid before this feature — confirmed via `documents.iter_schema_errors`, "Unexpected child with tag 'CuemsNodeDict'") | unindented; `schemaLocation` still absent (not added — normalisation narrows inconsistent *existing* values, it does not introduce a new attribute where none was present) — `<CuemsNodeDict>` left exactly as-is, since C4a permits no element-name change |

**Confirmed unchanged** (T006c): every element name and every element text value, across all four
files. The only byte-level change in each is the whitespace between tags and the `schemaLocation`
attribute's *value* (an XML artifact, not model content) on the three files that carried one.
Verified by running the full suite before and after and inspecting every failure's diff — each
failure was exactly a `schemaLocation` string mismatch (see below), nothing else.

**Goldens regenerated** (T006d), **exactly four**, via the reliable capture path
(`tests.support.roundtrip.read_dict` / `.read_config_dict`, which reads through
`cuemsutils.xml.settings` directly — see `baseline.md`'s note on why the deprecated package-root
alias used by `tests.support.capture_goldens` could not be trusted here):

| Golden | Diff |
|---|---|
| `dict/cuems-utils__network_map.reader.json` | `schemaLocation` value: `.../etc/cuems/network_map.xsd` → `network_map.xsd` |
| `dict/cuems-utils__network_map.config.json` | same |
| `dict/cuems-engine__network_map.reader.json` | `schemaLocation` value: `https://stagelab.coop/cuems/network_map.xsd` → `network_map.xsd` |
| `dict/cuems-engine__network_map.config.json` | same |

No `xml/*` golden exists yet for `network_map` (the write path doesn't exist until US2, T042), so
none is regenerated here. `tests/golden/MANIFEST.sha256` updated for exactly these four entries in
the same change.

**Deliberately not touched**: `tests.support.capture_goldens --force` also wanted to rewrite six
unrelated goldens (`settings`, `project_mappings`, `project_settings` — `.config.json` and
`outcomes.json`'s `write` outcomes) and reported them as conflicts even before this normalisation
ran. Investigated and reverted — see `baseline.md`'s "a pre-existing, unrelated anomaly" section.
None of those six is part of this feature's `network_map` scope, and two of the outcomes.json
changes were shown to be caused by an unrelated write-path behaviour change, not by anything this
step did.

**Suite**: 2222 passed / 94 skipped / 2 xfailed after regeneration — identical to the T002 baseline.

---

## 2. The rename diff (`node_type` → `node_role`)

Recorded once the schema edit and corpus conversion (T009–T017) land — see this file's next
section, added by T017.

---

## 3. The rename diff (T015–T017)

**Conversion**: the four (post-normalisation) corpus network maps converted with
`specs/007-node-model-migration/cuems_migrate_network_map.py` (the reference implementation of the
`cuems-common` conversion script — see that module's docstring for why it is developed here rather
than in `../cuems-common/usr/bin/`, which is out of scope for this pass). Every node's `NodeType.master`
became `<node_role>controller</node_role>` and every `NodeType.slave` became `<node_role>node</node_role>`,
with a deprecation notice recorded for each (the enum-repr spelling, not the bare one). Verified
against the updated schema (`documents.iter_schema_errors`, zero errors on all three validatable
documents — `cuems-common`'s carries its pre-existing, unrelated `<CuemsNodeDict>` invalidity,
recorded in section 1, and stays invalid the same way after conversion).

**Every changed line is the rename or the value mapping** (T017 / SC-010a), confirmed against the
regenerated goldens:

```diff
-  "node_type": "NodeType.master",
+  "node_role": "controller",
```
```diff
-  "node_type": "NodeType.slave",
+  "node_role": "node",
```

No other key, value, or structural change appears in the `dict/{cuems-utils,cuems-engine}__network_map.{reader,config}.json`
diff from section 1's post-normalisation state — checked by inspecting each `git diff` hunk
individually, not merely by re-running the suite.

**A second, distinct change rides in the same golden regeneration, and is recorded separately so it
is not mistaken for part of the rename**: `network_map`'s `adopted`/`online` fields now decode to
Python `bool` in the `.config.json` golden (JSON `true`/`false`, where they were the string
`"True"`/`"False"`), because `Mapper.decode_config` now runs the adapter table for this schema
(T018–T024, research R1) and `cms:BoolType` was always bound to a `bool`-producing adapter — it
simply never ran for config schemas before. This is FR-011a, not FR-010b; the `.reader.json` golden
(Configuration A, which never runs adapters) is unaffected and still carries the strings, which is
how `test_reader_configs.py`'s "the two configurations differ" contract keeps meaning something.

**Goldens touched**: the same four as section 1
(`dict/{cuems-utils,cuems-engine}__network_map.{reader,config}.json`), regenerated again from this
converted, typed state — `MANIFEST.sha256` updated in the same commit.

**Test-support change riding along**: `tests/support/roundtrip.py`'s `json_dumps` gained an
`Enum`-aware `default=` — the first golden to carry a real enum value (`node_role`, `NodeRole`) is
this one, since neither existing decode path (Configuration A's raw `schema.to_dict()`, or the show
path's `.reader.json`, which no config schema used) ever produced one before.

**Suite**: 2248 passed / 94 skipped / 2 xfailed. Six existing tests needed adjustment for the
now-typed `network_map` values — none of them assert anything this feature didn't deliberately
change; each comment names FR-011a / research R1 at the point of the fix:
`tests/contract/test_config_wire.py` (`to_wire()`'s `bool` → `"True"`/`"False"` string is no longer
an identity on the decoded value, for this schema only), `tests/contract/test_reader_configs.py`
(Configuration A vs B "differ only by namespace handling" gains a typed-value exception, scoped to
`network_map`), `tests/contract/test_config_parity.py` (two golden-vs-live comparisons decode the
golden's `node_role` string through `NodeRole` before comparing), `tests/unit/test_coherence.py`
(the bound-model count drops 40 → 39 with `PutType` deleted), `tests/test_configmanager.py` and
`tests/test_xml.py` (literal `'node_type'`/string-`'True'` assertions updated to `'node_role'`/
`NodeRole.controller`/`True`).
