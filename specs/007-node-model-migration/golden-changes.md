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
