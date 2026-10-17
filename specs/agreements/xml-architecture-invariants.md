<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# XML architecture invariants

**Adopted**: 2026-10-17, by feature `010-consumer-migration` (T069), compiled from the
`specs/planning/xml-rebuild/` series that planned features 004–010
**Applies to**: `cuemsutils` and every CUEMS repository that reads or writes its documents —
`cuems-common`, `cuems-editor`, `cuems-engine`, `cuems-frontend`, `cuems-nodeconf`,
`cuems-power-bridge`
**Status**: binding

## Why this exists

Between August and October 2026 the XML layer was rebuilt: four duplicated mapping
implementations became one schema-derived engine, two public objects replaced a dozen entry points,
and seven repositories moved onto them. The decisions behind that lived in nine planning documents,
most of which were about *how to land the work*, and that part is now spent. What follows is the
part that still binds: the rules a change to this layer is expected to be read against.

Decision ids (`D2`, `Q14`, …) are kept beside each rule so the history can be found in git. The
rules stand on their own; you should not need the history to follow them.

Schema changes have their own binding reference,
[schema-evolution-convention.md](schema-evolution-convention.md), which this document does not
restate. Read it before editing any `.xsd`.

---

## 1. The schema is the single source of truth (D2, Q11 → (c))

Structure, type, cardinality and element order are derived from the six XSDs under
`src/cuemsutils/xml/schemas/`, never re-encoded by hand in Python. What is hand-written is the
façade and the behaviour, nothing that describes shape. Defaults are the one split: most are
model-layer defaults, and an XSD `default=` attribute seeds a new instance where one is declared
(015's seeding rule 0). Moving the literal ones into the schemas is planned, not done
(`specs/planning/xsd-literal-defaults.md`).

- A second description of a type, such as a hand-maintained example or template or a per-field
  fallback table, is a defect, because it drifts. `create_script()` and `templates/settings.xml`
  were removed for exactly this (D25).
- The one deliberate exception is `UiPropertiesType`, which is `xs:anyType` so the UI can store
  arbitrary keys (X10). Nothing can be derived for it, and machinery that walks types must treat it
  as opaque.

## 2. Two public objects, and they return objects (D12, D15, Q14 → (i))

- **`CuemsScript`** is the show document (`load`, `load_with_report`, `save`, `validate`,
  `from_json`, `to_json`, `to_wire`). **`ConfigManager` / `ConfigBase`** are the configuration
  documents (accessors, `save_*`, `from_json`, `get_schema_descriptor`).
- The public surface returns **objects, never raw dicts**. A dict appears only at the wire edge,
  through `to_wire()`, which is a direct projection, not a round trip.
- **`cuemsutils.xml` is internal machinery**: `__all__ == []`. A consumer importing from it is
  using a path that can change without notice.
- **An exception a consumer cannot name is one it cannot catch.** Every failure a consumer must
  distinguish is a public type in `cuemsutils.errors`, or a structured field on one
  (`violation.rule`), never a sentence to parse.

## 3. One type and one form for every time value (D17, D18)

Every element that carries a time value is `cms:CTimecodeType` and stores a `CTimecode` object,
with no exception. The canonical lexical form is `HH:MM:SS.mmm`. On the wire a time value is
`{"CTimecode": "HH:MM:SS.mmm"}`, never a bare string.

## 4. Reading is strict, and recoverable (D19, D21)

Every load runs structural (T1) **and** semantic (T2) validation. A document has one of these
outcomes, and each is distinguishable by data, not by message text:

| Document | Outcome |
|---|---|
| valid and current | loads clean |
| **older** than the library (`doc_version` precedes current) | converted **in memory**; the file on disk is untouched |
| current, with a **repairable** T2 violation | loads with the field repaired to the descriptor's default, reported in the `LoadReport` |
| current, with an **unrepairable** violation | refused: `ValidationError` naming the document, the field and the value |
| **newer** than the library | refused: `ValidationError` with `violation.rule == "document_version_too_new"`. The fix is to upgrade the reader |

- **A load never writes.** Persisting a conversion or a repair is a save the user initiates, or a
  standalone tool's job, and only a tool that persists owes a backup.
- **A backup never overwrites another backup**, and a document's oldest backup is its pre-upgrade
  state.
- **Every repair traces to the descriptor**: no hand-written per-field fallback and no hand-kept
  list of unrepairable fields. The library has no UI channel and must not gain one. It returns the
  report, and the editor forwards it.
- **The version marker is a document property, never a domain field.** It never appears in a wire
  projection.

## 5. The network map's logic lives in the library (D22, 007 FR-030a-i)

Merge, adopt, unadopt, refresh, the signature and the write orchestration live on `NodeIndex` and
`CuemsNetworkMapType` in `cuemsutils`, not on a consumer's daemon. **The node model and its tests
live in `cuemsutils` exclusively**: a node-model test added to a consumer is a regression against
this rule, and a fourth private copy of the model (as `cuems-power-bridge` once held) is exactly how
a vocabulary change fails silently.

## 6. One descriptor, one public path (D25, D34)

The schema descriptor (field name, XSD type, cardinality, restricted enumeration values, defaults,
repairability, and a constructible instance per type) covers all six schemas. It is reached through
**`ConfigManager.get_schema_descriptor(SchemaName.…)`**, `script` included. One path for one
mechanism beats a config accessor plus a show accessor, because the component that serves
configuration forms is the same one that serves the show template. Building it must not construct
schemas the caller did not ask for. Eager construction there is a design error, not a budget overrun.

## 7. The editor→UI payload changes only in enumerated ways

The `project` payload is **never** promised byte-identical. It differs from its predecessor in an
**enumerated** set of deltas, and the enumeration lives in **one** place:
`cuems-editor`'s `tests/ws-command-responses.txt`, pinned by its `tests/test_project_payload.py`.
Cite that file, never a count. It was two deltas, then four, then five, and every document that
restated the number went stale. Any change to an existing key, its order or a value's form bumps
`payload_version` by that file's rule. The UI refuses a version it does not implement and says why.

## 8. Discovery has two owners and one cutover (D33)

The Avahi TXT record's vocabulary (`node_role=controller|node|firstrun`) is written by
`cuems-common`'s templates and read by `cuems-nodeconf`'s listener. A listener and a publisher
that disagree discover nothing, and discovery failure is how a cluster loses its topology. So the
vocabulary changes **only** as one coordinated cutover of both halves, never per repository.

## 9. Callers that keep resolving but become wrong (007 FR-030a-ii)

A caller that **stops resolving** fails loudly at import. A caller that **keeps resolving but
becomes semantically wrong** keeps running and returns the wrong answer: it compares against a
retired vocabulary, normalises a spelling that no longer exists, or filters on a string the data
no longer carries. These are a **named class**, counted separately, and each one carries a test that
**fails against the pre-change value**. A green suite is not evidence for this class: the
power-bridge's fixtures were themselves in the retired vocabulary, so its tests certified the defect.

## 10. Counting consumers: discover them, never list them (D32)

The consumer set is **seven** repositories today. That number is not the rule. A hand-maintained
list of consumers was wrong **four** times during the rebuild: `cuems-wsclient` was absent;
`cuems-power-bridge` was absent; the two were counted separately although they are one repository,
renamed; and three branches of one feature were invisible because they carried three names. Each
error was found by reading the filesystem, and a silent failure shipped in the meantime. So:

- **Enumerate** consumers with a command: every checkout that reads the document in question.
- **De-duplicate by root commit**, not by directory name and not by remote URL. A stale checkout of
  a renamed repository keeps its old URL, but its first commit cannot change.
- **Find a feature's branches by content** (`git cherry`, subjects, symbols), including
  remote-only refs, never by expected name.

`specs/010-consumer-migration/tools/count-retired-vocabulary.sh` is the worked example.

## 11. A retired-vocabulary count has an enumerated exempt set, with two reasons (D36)

A count of a retired spelling must reach zero **outside an exempt set listed site by site**
(`<path>:<lines>`, re-measured each time, never copied), and every entry says **which** of two
reasons applies:

- **permanent**: the code exists to detect, convert or refuse the retired spelling (a migration
  tool, a diagnostic, a `Breaks:` and its comment). Deleting it deletes a working diagnostic.
- **removable**: the file is not shipped (a dev fixture). It can be cleaned up at any time.

Merging the two is how the next person to run the count deletes a working migration diagnostic to
make a number reach zero.

## 12. Standing rules for any change to this layer

1. **Never implement on a red suite.**
2. A chain test (`xml → object → json → object → xml`, D14) is written **before** the machinery it
   guards, against current behaviour.
3. **Goldens never move to make a red test go green.** A deliberate wire change re-cuts them
   **once**, as a reviewed diff that is part of the decision, and the pre-change files are
   **kept** as the conversion path's fixtures, since they are the only first-party corpus of
   real old-shape documents.
4. **Compatibility is defined against the current XSDs**, not against file history. Structural
   (T1) reading never becomes stricter than the schema. Semantic strictness (§4) makes reading
   *more* recoverable: a corrupt document can no longer enter the runtime silently, but it can
   still be read, because every first-party repair tool is a `load()` consumer.
5. All six schemas share one `targetNamespace` and none includes or imports another, so a QName
   can be defined twice incompatibly. **Keep names distinct across schemas.** The anti-drift
   guarantee is a test (`tests/contract/test_schema_name_overlap.py`), not a schema mechanism.
6. Commits are GPG-signed; retry on "gpg failed to sign", never bypass it.
7. Planning material lives in `specs/planning/`, feature material in `specs/NNN-*/`, and a
   planning document is deleted once its decision is made and acted on (`CLAUDE.md`).
