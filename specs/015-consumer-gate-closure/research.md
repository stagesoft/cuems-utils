<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Phase 0 research — the consumer-gate closure

**Feature**: `015-consumer-gate-closure` · **Branch point**: `75a958e` · **Measured**: 2026-10-13

Every finding below was measured on this branch, in this session. Nothing is carried forward from a
planning document's reading, and where a planning document or this feature's own spec said something
the measurement contradicts, the contradiction is recorded rather than quietly corrected.

**Measurement environment — changed mid-plan, and the change is itself a finding.** Phase 0 was
first measured on CPython **3.11.2** `[GCC 11.2.0]` from a conda environment, because `~/.pyenv` did
not exist and the convention's `PYENV_VERSION=3.11.9` was inert. **On 2026-10-13 the maintainer
migrated the box**: pyenv was installed with a real 3.11.9, the toolchain (`uv`, `hatch`, `specify`)
was reinstalled outside conda, and anaconda was removed entirely.

Every figure below was then **re-measured on the migrated box**, and re-measured again after pyenv's
3.11.9 was **rebuilt with PGO+LTO**. The interpreter the suite runs on is **uv-managed CPython
3.11.9** (python-build-standalone, `Clang 18.1.8`); after the rebuild pyenv's `GCC 12.4.0` build
agrees with it to within **0–2%**. R10 carries the baselines and the budget verdict; R11 carries the
interpreter finding and its resolution.

---

## R1 — Why a single-child root instance is `null`, and the precedent that fixes it

**Question**: FR-022. `CuemsSettings` → `{"Settings": null}` and `CuemsProject` →
`{"CuemsScript": null}`. Why, and where is the fix?

**Measured**. `FieldSpec.child` is `None` for both, and so is `xsd_type`:

```
settings:/CuemsSettings     Settings     child=None  repeated=False  xsd=None
script:/CuemsProject        CuemsScript  child=None  repeated=False  xsd=None
network_map:/CuemsNetworkMap node_list   child=network_map:NodeDictType  xsd=NodeDictType
```

The cause is `spec._type_key` (`src/cuemsutils/xml/spec.py:194-200`): it returns `None` for a
complex type with no `local_name`. Both roots declare their single child's type **inline**, so there
is no qname to key it by. `_instance_for` then takes the scalar branch and seeds `None`.

**Decision**: fix it in `_instance_for` by **path resolution**, not by changing `_type_key`.

**Rationale**: this exact case already has a solution in this codebase, twice —
`Mapper._anonymous_child` (`mapper.py:389`) and `Mapper._child_spec_for` (`mapper.py:857`), both of
which resolve `derive_path(schema, f"{spec.key.name}/{key}")` when `field.child is None`,
`field.xsd_type is None` and the parent spec `is_path`. The descriptor already enumerates
`CuemsSettings/Settings` and `CuemsProject/CuemsScript` as type keys, so the targets exist. Reusing
the guard conditions verbatim means one documented mechanism gains a third call site rather than a
fourth variant appearing.

**Alternatives rejected**:
- *Widen `_type_key` to return a path key for anonymous complex types.* Globally correct and much
  more dangerous: `FieldSpec.child` has **27 consumers**, 21 of them in `mapper.py`, plus
  `seed_values.py:111` and `ConfigManager.py:98` which both test `child is None` as the *definition*
  of "this field is a scalar". Changing that predicate would silently reclassify fields on the
  decode and encode paths. A descriptor convenience must not move the mapper's notion of a leaf.
- *Special-case the two roots by name.* Two hard-coded names, and a third schema with a wrapping
  root would reintroduce the bug. `_child_spec_for`'s docstring already explains why the path-bound
  case is resolved generally and the non-path-bound case is deferred; that reasoning holds here.

---

## R2 — The repeated-complex nesting inversion is one rule, and the encoder already owns it

**Question**: FR-020/FR-021. The instance nests repeated complex content one way and the wire nests
it the other. Where is the single rule?

**Measured**, three independent sites, all the same shape:

| Field | Instance today | Wire (from `tests/golden/dict/`) |
|---|---|---|
| `network_map` `node_list` | `{"node": [ {...} ]}` | `[ {"node": {...}} ]` |
| `script` `channels` | `{"channel": [ {...} ]}` | `[ {"channel": {...}} ]` |
| `project_mappings` `defaults` | `{"default": [ {...} ]}` | `[ {"default": {...}} ]` |
| cue output wrapper | *(none)* | `{"CueOutput": {...}}` |

So it is **not** three findings and not specific to cue outputs: a complex type whose content is a
repeated element projects on the wire as a **list of singly-keyed objects**, and the descriptor
builds a dict whose value is a list. `cuems-frontend` UR-1 reports the `channels` case and notes
*"the two nest in opposite directions"*; the measurement says that is a general property.

**Decision**: build the instance as a **value the projection can consume**, then project it through
`Mapper.encode_wire` — the same call `to_wire()` uses. Do not re-derive the wrapping and nesting
rules inside the descriptor.

**Rationale**: three reasons, in order of weight.
1. It makes FR-020, FR-021 and FR-031 true **by construction** rather than by three separate
   transformations that can drift from the encoder. Re-deriving them in the descriptor is precisely
   what `cuems-frontend` is doing today in TypeScript, and UR-1 names the cost: *"this repository now
   encodes knowledge of a projection it does not own, in a language the schema is not written in.
   That is the drift the descriptor cutover exists to end."* Moving that transform from TypeScript
   into `descriptor.py` would relocate the drift, not remove it.
2. `encode_wire` already handles the document-body wrapper through `_body_tag_for`
   (`mapper.py:512`), which is exactly FR-021's `CueOutput` wrapper. Verified: an `AudioCueOutput()`
   projects through `encode_wire(obj, derive(TypeKey('script','AudioCueOutputsType')))` without
   error.
3. It matches FR-011's standing requirement for the configuration sections — *"the same projection
   body… a second projection is forbidden"* — and extends it to the descriptor, where the same
   argument applies and was never stated.

**Consequence that must be designed for, not discovered**: `_encode_wire_value` **omits a field that
is optional and empty** (`mapper.py:527-535`), deliberately, so that the wire and the XML writer
agree on which fields vanish. An instance built only of required fields would therefore lose
`canvas_region` — and UR-1's whole use case is the nested shape *including* `canvas_region`. See R3's
decision 3.

---

## R3 — The seeding rules: a closed, derivable set

**Question**: FR-025/FR-026b/FR-028. Clarification 1 settled *instance-local seeding from the XSD
type*, with the per-primitive rule left to planning. What are the rules, and is "derived, not
hand-tabulated" actually achievable?

**Measured**: the complete set of scalar types reachable from any instance across all six schemas is
**30 named simple types plus 7 built-ins** — a closed set, enumerated below with its facets.

### Built-ins in use (7)

| Type | Sites | Seed | Why |
|---|---|---|---|
| `boolean` | 32 | `False` | |
| `string` | 24 | `""` | |
| `positiveInteger` | 7 | **`1`** | `0` is invalid — the one built-in where `0` would not validate |
| `nonNegativeInteger` | 6 | `0` | |
| `integer` | 4 | `0` | |
| `float` | 4 | `0.0` | |
| `byte` | 1 | `0` | |

### Named types, by the rule that seeds them

**Rule 1 — enumeration → the first declared value.** `PostGoType`→`pause`, `ActionType`→`play`,
`FadeCurveType`→`linear`, `PortDirectionType`→`input`.

**Rule 2 — union → its enumerated member if it has one, else its first member.**
`NodeUuidType`→`00000000-0000-0000-0000-000000000000` and
`AutoOrIntLatencyMsType`→`auto`. ⚠ Note this rule **depends on S2 being fixed in the same pass**:
`_enum_values` currently merges a union's members' enumerations and so reports these two types *as*
enumerations, which would make rule 1 fire on them accidentally and give the right answer for the
wrong reason. After S2 narrows the reporting, rule 2 must read the member types directly. The
sentinel is also the semantically correct seed for an unprovisioned identity, so this rule happens
to be right twice.

**Rule 3 — numeric `minInclusive` → that bound.** `PercentType`→`0`, `ChannelNumberType`→`0`,
`ChannelValueType`→`0`, `UnitFloat`→`0.0`, `NonPrivilegedPort`→`1024`, `LoopType`→`-1`,
`DateType`→`2020-01-01T00:00:00`.

**Rule 4 — numeric `minExclusive` with a `maxInclusive` → the `maxInclusive`.**
`PositiveUnitFloat` (`minExclusive 0.0`, `maxInclusive 1.0`) → **`1.0`**. "The smallest valid value"
is not expressible for an exclusive float bound, and `1.0` is also the semantically right seed for a
scale or a region width.

**Rule 5 — numeric with only `maxInclusive` → `0`.** `IntLatencyMsType` (`maxInclusive 500`, base
`nonNegativeInteger`) → `0`.

**Rule 6 — length-bounded string, no pattern → `""` if `minLength` is 0, else one character.**
`DescriptionStringType` (`minLength 0`) → `""`; `NameStringType` (`minLength 1`, `maxLength 60`) →
one character.

**Rule 7 — pattern-restricted string → a type-keyed seed from a declared table.** Five patterns, all
of them:

| Type | Pattern | Seed |
|---|---|---|
| `UuidType` (script) | `[a-f0-9]{8}-…-4[a-f0-9]{3}-[89ab]…` | `00000000-0000-4000-8000-000000000000` |
| `TargetType` | `(uuid-shaped)\|()` | `""` — the pattern admits empty and `minLength` is 0 |
| `Md5Type` | `[a-f0-9]{32}` | thirty-two `0`s |
| `TimecodeType` | `[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}` | `00:00:00.000` |
| `NonEmptyString` (4 schemas, identical facets) | `.*[^\s].*`, `minLength 1` | one non-space character |

**Decision**: implement rules 1–6 as derivation over the resolved simple type's own facets, and
rule 7 as a **type-keyed** table of five entries with a contract test asserting (a) every
pattern-restricted simple type in the six schemas has an entry, and (b) every entry validates
against its own type.

**Rationale**: FR-028 forbids "a per-field hand-written table of fallbacks, and no per-type special
case". Rules 1–6 satisfy it outright — 25 of the 30 named types and all 7 built-ins are seeded by
reading facets. Rule 7 is the irreducible residue: **a regular expression cannot be inverted**, there
is no runtime dependency that generates a matching string (`hypothesis.from_regex` exists but is a
test-environment dependency only, and adding a runtime one for a seed would be out of proportion),
and five entries keyed by *type* is not a per-field table. The completeness test is this
repository's established answer to exactly this shape — `seed_values.py`'s four rules name
schema/type/field/file, and `descriptor._assert_every_choice_member_has_a_builder` fails if a choice
member has no builder. A sixth pattern added to any schema fails the test rather than silently
seeding `None`.

**Alternatives rejected**:
- *Model-layer defaults.* Settled against in clarification 1, and the reason is measured:
  `_repairability` (`descriptor.py:208`) opens `if default is Unset: return UNREPAIRABLE`, so giving
  these fields a default moves **64 fields across 19 types** from unrepairable to repairable, and
  feature 008's load path repairs a repairable violation where it raises on an unrepairable one.
- *Seed only the required fields.* Would satisfy the four `cuems-editor` xfails and break UR-1's
  actual use case, because `canvas_region` is optional and `_encode_wire_value` omits an optional
  empty field (R2).
- *Invoke the callable defaults to get a real value.* Refused by `TypeDescriptor.instance`'s own
  recorded reason: `derive` is cached, so calling `new_uuid()` once freezes one "fresh" identifier
  and hands the same one to every later caller. FR-027 keeps that.

**Decision 3 — populate every field, required and optional, scalar and complex.** Then nothing is
"optional and empty", so `_encode_wire_value` omits nothing, and the instance is simultaneously
wire-shaped (R2), saveable (FR-023/FR-024) and **complete** — which is the property the current
`null`-filled instance has and which a consumer building a form depends on. This is the one point
where the instance deliberately differs from the projection of a *real* sparse object, and the
difference is in the direction of being more useful rather than less.

---

## R4 — Where the structured collision is raised, and why not in the validator

**Question**: FR-060/FR-060a/FR-060b. Clarification 3 settled *a `ValidationError` subclass with its
violation populated*. Raised where?

**Measured, and it changes the answer.** `ConfigBase.load_config_document` orders its handlers:

```
except OSError:          raise
except SchemaError:      raise
except ValidationError:  raise          # <-- here
except DocumentTooNewError: ...
except Exception as exc:                # <-- node_identity_collision_message lives here
```

A `ValidationError` subclass raised inside the validator therefore **propagates before** the clause
that attaches the file path. The consumer's frame needs `{"kind", "identity", "file"}` — so raising
the public subclass from the rule would lose the one field the accessor exists to add.

**Decision**: two layers.
1. `check_node_identities_unique` raises an **internal** `ValueError` subclass carrying the
   collisions as data. It stays a `ValueError`, so every existing path is unchanged.
2. `load_config_document` promotes it to the **public** `NodeIdentityCollisionError`
   (`ValidationError` subclass) with the file path attached and the violation populated as
   `location=(identity, "uuid")`.

**Rationale**: the `ValueError` base is load-bearing and documented three times — the rule raises a
plain `ValueError` *because* `xmlschema`'s own `XMLSchemaValidationError` is also a `ValueError`, so
`isinstance` cannot distinguish a semantic from a structural failure (feature 008, FR-037), and the
recognition is therefore by message shape. Keeping the internal exception a `ValueError` preserves:
`validate_node_identities` on the read path, `_node_uuid_unique` through `run_rules`, the
`except Exception` promotion above, and `tests/golden/outcomes.json`, which pins the internal
reader's **raw verdicts** document by document (`ConfigBase`'s docstring: *"The internal reader
deliberately does not wrap: its raw verdicts are what `outcomes.json` pins"*). The public type then
appears exactly where contract C2 already places the posture — at the accessor.

Also: the message is unchanged, so FR-063 and FR-064 hold without further work, and
`node_identity_collision_message` keeps answering for any caller still on it.

**Alternatives rejected**:
- *Raise the public subclass from the validator and add an `except NodeIdentityCollisionError` clause
  above `except ValidationError`.* Works, but makes the rule's exception type a public contract and
  changes what `outcomes.json` pins for the internal reader. The raw verdict should not change
  because a public accessor gained a type.
- *A structured return value instead of an exception.* Rejected by the errors module's own stated
  position, quoted in clarification 3.

---

⚠ **Added by the second analyze pass (2026-10-13): "published" is three places, and two of them are
hand-maintained.** `tests/contract/test_public_api_surface.py` holds `PUBLIC_ERRORS` (9 names),
asserts it **equal** to `cuemsutils.errors.__all__`, and **generates** `api/public_api.json`'s
`errors` section from it. So the new class must land in `__all__`, in that tuple, and in the golden
in one change (T080a) — otherwise either an existing contract test goes red or the re-cut golden
omits the class it was scheduled late in order to capture.

---

## R5 — `must_exist` and the two API goldens

**Question**: FR-001/FR-003. Can the path helpers gain tolerance additively?

**Measured**. `ConfigBase.conf_path` (`ConfigBase.py:147`) and `ConfigManager.project_path`
(`ConfigManager.py:907`) each `path.exists` and raise. In-package call sites: **10**, all of them load
paths or `save_*` defaults — `ConfigBase.py:137`; `ConfigManager.py:379, 409, 427, 434, 436, 499,
551, 559, 600` — none positional beyond the documented arguments. (Five further mentions are
docstrings naming the default, not calls.)

Both signatures are pinned in **two** goldens as strings:
`tests/golden/api/public_api.json` (`"conf_path": "(self, file_name: str) -> str"`) and
`tests/golden/api/config_accessors.json`.

**Decision**: add a **keyword-only** `must_exist: bool = True` to both, and re-cut the two API
goldens as part of this feature's sanctioned golden event.

**Rationale**: keyword-only satisfies FR-003 directly — no positional call site can acquire the
tolerance by accident. The default `True` satisfies FR-002, so all 10 in-package call sites and every
consumer keep today's behaviour with no edit. `tests/support/capture_goldens.py` refuses to
overwrite a golden without `--force`, so the re-cut is necessarily an explicit, reviewable act.

⚠ **Added by the second analyze pass: the goldens' scope is a hand-maintained list, which matters
for G4 rather than for G1.** `PUBLIC_CLASSES` is `CuemsScript`/`ConfigManager`/`ConfigBase` and
`PUBLIC_FUNCTIONS` is `partition_by_adoption`/`validate_config_document`, so both of *this*
requirement's signatures are pinned (they are `ConfigBase`/`ConfigManager` methods) — but
`NodeIndex` is tracked **nowhere**, so G4's `set_alias` had no recorded shape and T026's claim to
cover it was false. `NodeIndex` joins the tracked classes by maintainer decision (FR-041a, T049a).

**Note for G1's completion**: `cuems-editor`'s strict xfail for this gate does **not** flip on the
library change alone — that repository's own `_config_path` must pass the flag on. Its
`tag-readiness.md` says so explicitly, and FR-008 records it.

---

## R6 — `project_settings`: the read projection and the absent file

**Question**: FR-010/FR-015. What does the public read return, and what happens with no file?

**Measured**:
- `_PROJECTABLE_SECTIONS` (`ConfigManager.py:166`) has 8 members and `project_settings` is not one;
  `to_wire` resolves a section with `getattr(self, section)`, so a **public property of that exact
  name** is what the existing body needs — no change to `to_wire` itself.
- With no file, `load_project_settings` logs *"Keeping default settings"* and returns, leaving
  `_project_settings_document = None` and `project_conf = {}`. There is nothing to project, which is
  the measurement that falsified the source document's premise.
- `CuemsProjectSettingsType()` constructs empty, projects `{}`, and **saves** a valid document
  (verified; `setting` is `minOccurs="0"`).

**Decision**: `load_project_settings`'s absent-file branch sets `_project_settings_document` to an
empty `CuemsProjectSettingsType()`, and a public `project_settings` property returns it. Add
`'project_settings'` to `_PROJECTABLE_SECTIONS`.

**Rationale**: it satisfies FR-010, FR-011 (the existing projection body is reached unchanged),
FR-012 and FR-015 with one change rather than a special case per requirement, and it makes FR-015a
fall out for free — a manager that never loaded a project still has no attribute, so "not loaded"
and "no file" stay distinguishable without a flag. It also produces a **synergy worth naming**:
with an empty document present after a tolerant load, `save_project_settings` works for a project's
*first* save as soon as G1 supplies the write target. G1 and G2 are therefore one user journey, not
two adjacent fixes.

**Refinement to the spec, recorded rather than silently applied**: clarification 2 illustrated the
empty projection as `{"setting": []}`. Measured, it is `{}` — the repeated field is omitted when
empty, which is the projection's existing rule. The spec's illustration is corrected; the decision
is unchanged.

---

⚠ **Added by the second analyze pass: the accessor returns the object, and that is load-bearing.**
`ConfigManager.to_wire` reads the named section off the manager and calls `to_wire()` on what it
finds (`ConfigManager.py:897-901`), so a dict-returning `project_settings` property would raise
instead of projecting; and `tests/contract/test_config_object_surface.py` asserts **no** inventoried
accessor returns a raw `dict`, reading its accessor set from the recorded inventory — so the failure
would have appeared only when T026 re-cuts that inventory, six phases after US2. `contracts/`'s C2
had the shape right; the requirement did not state it (now FR-010, pinned by T022a).

---

## R7 — The version step must address both player shapes

**Question**: FR-050/FR-051. Is the two-shape lookup expressible with the standard library?

**Measured**. `_settings_1_to_2` (`versioning.py:321`) does `node.find(section)` for `audioplayer`
and `dmxplayer`. After `reshape_players` the path is `players/player[@class='audio']`.
`ElementTree`'s limited XPath **supports the attribute predicate**, verified:
`root.find("players/player[@class='audio']/audio_cards")` resolves on a reshaped tree.

Reproduced at `75a958e` that the dead end is still live:
`cuems-reshape-devices` → `skipped (would not validate: … Unexpected child with tag 'audio_cards' at
position 3 …)`, exit 1.

**Decision**: look under the flat path **and** the reshaped predicate path, dropping the field
wherever found, in one loop over both spellings.

**Rationale**: four lines, no new dependency, and tolerance of both shapes is in character for a
conversion step — a conversion exists to read what is on disk, and after 013 "what is on disk" has
two spellings. The order of the tools is **not** inverted: 013's own docstring records why
convert-before-reshape dead-ends for `script` (a version-1 `<duration>` the 1 → 2 step wraps), so
reversing would trade this defect for its mirror image. FR-054 pins that.

**Open sub-question for the design, raised by the measurement**: `root.find("Settings/node")` is
singular and addresses only the **first** node section. Whether a `settings` document can carry more
than one `<node>` is a schema question the fix must answer rather than inherit; if it can, the
converter has a second latent defect of the same family.

---

## R8 — Indentation: the stdlib already guarantees FR-073

**Question**: FR-070/FR-073. Does indenting risk altering content?

**Measured**:
- `write_tree` (`documents.py:289`) never indents — `tree.write(temporary, encoding="utf-8",
  xml_declaration=True)` and nothing else.
- Exactly **one** mixed-content type exists across all six schemas: `script:UiPropertiesType`.
- `ET.indent` **preserves mixed content**: `<m>lead<b>x</b>tail</m>` is returned unchanged, while an
  element-only parent is indented. Verified directly.

**Decision**: use `xml.etree.ElementTree.indent(tree, space="  ")` immediately before `tree.write`,
inside `write_tree`, so every document this library writes is indented by one code path.

**Rationale**: FR-073 ("indentation MUST NOT alter any element's text where that text is data") is
satisfied by `ET.indent`'s own contract rather than by a guard this feature would have to write and
test. The single mixed type is the one place the risk lives, and the stdlib function already declines
to touch it. Placing the call in `write_tree` rather than in each `save()` keeps FR-072's five
guarantees — encoding, declaration, prefix registration, mode preservation, atomic replace —
untouched and in one place.

**Golden event scope, enumerated** (FR-074). Of the 34 entries in `tests/golden/MANIFEST.sha256`:
- **6 XML goldens re-cut**: `xml/cuems-editor__script_minimal.xml`,
  `xml/cuems-engine__projects__complex_test__script.xml`,
  `xml/cuems-engine__projects__empty_test__script.xml`, `xml/cuems-utils__fade_showcase.xml`,
  `xml/cuems-utils__unicode_showcase.xml`, `generated/example_script.xml`.
- **2 API goldens re-cut** for R5's and R6's signature additions: `api/public_api.json`,
  `api/config_accessors.json`.
- **The 24 `dict/` goldens, `generated/example_script.reader.json` and `outcomes.json` are
  unaffected** — a wire dict carries no whitespace,
  and re-authoring the two canonical corpus documents changes their bytes, not their decoded values.
- `MANIFEST.sha256` itself.

**The contract-test consequence, named because its own docstring asks for it** (FR-075/FR-076).
`tests/contract/test_roundtrip_stability.py` splits the corpus into `FIRST_CYCLE_IS_IDENTITY`
(`fade_showcase.xml`, `unicode_showcase.xml` — asserted byte-identical after one save) and
`REFORMATTED` (asserted *not* identical). Indenting the writer:
- breaks the first set unless both documents are re-authored in the new output form — FR-075;
- may make a hand-authored document in the second set become identity, which that test's docstring
  says *"must be a decision rather than a drift"* — FR-076 is that decision.

⚠ **A second contract test, added by the second analyze pass (2026-10-13) — this enumeration was one
test short.** `tests/contract/test_network_map_roundtrip.py` diffs what `save()` writes against
`specs/007-node-model-migration/pre-state/{network_map.xml,corpus/cuems-utils/network_map.xml,corpus/cuems-engine/network_map.xml}`
and asserts `len(body_lines) == 2`, stating its own reason: *"the whole document is one line after
normalisation, so the rename+mapping collapses the diff to a single before/after pair."* Measured:
all three are one line, so indenting makes that diff the entire document, three times over. The
three documents are re-authored in the new form (**FR-075a**, T090a) rather than the comparison
being made structural — the test's value is that the `node_type` → `node_role` rename is legible
**in a diff**. **So S3's hand-authored cost is five documents, not two**, and the reason this one was
missed is worth keeping: it asserts a *line count*, so it does not appear in any golden list or
manifest.

---

## R9 — Candidate tags, and the mechanism clarification 5 asked for

**Question**: FR-080c/FR-080e/FR-080f. Can cross-repository claims resolve at a tag today?

**Measured, 2026-10-13**, across all seven repositories:

| Repository | `xml-refactor-merge-candidate` | `CLAUDE.md` records | Verdict |
|---|---|---|---|
| `cuems-common` | `91b2d25` | `e3c9430` | ⚠ **moved** |
| `cuems-nodeconf` | `c29c25c` | `b305c1c` | ⚠ **moved** |
| `cuems-power-bridge` | `cabbb3e` | `399baf7` | ⚠ **moved** |
| `cuems-frontend` | `531004b` | *(recorded as carrying a tag, value not stated)* | newly pinned |
| `cuems-engine` | none (tip `a197cac`) | none | consistent |
| `cuems-editor` | none (tip `1144a1d`, 002 merged) | none | consistent |
| `cuems-utils` | none (tip `75a958e`) | none — tags last by D27 | consistent |

**Three of four recorded values are wrong.** This is the drift FR-080c exists to catch, and it was
found by resolving the tags rather than by reading the record — which is the whole argument for the
mechanism.

Also measured: both contract test files **already skip with a reason** when a sibling is not checked
out (`test_migration_guide.py:137`, `test_migration_guide_names_sites.py:146`), so **FR-081 is
already satisfied** and is a property to preserve rather than work to do.

And the two pinned commits are not merely moved: `106015c` and `3183845` are absent from
`git log --all` in their respective siblings. They are dead references.

**Decision**: one shared resolver used by both contract files — given a sibling name, resolve its
`xml-refactor-merge-candidate` tag; **skip with a reason** when the checkout or the tag is absent;
**fail** when the tag resolves and the claim does not hold. Provenance pins become dated statements
and are no longer resolution-asserted. The two false operator-facing claims in 012's guide are
corrected.

**Rationale**: a tag is a stable reference by construction and a tip never was one, which is why this
collision has now occurred for two separate guides. FR-080d's whole-set re-validation is the first
mechanism in the ecosystem that expresses feature 011's recorded lesson — *a candidate tag set is
only as current as its least current member, and no packaging relation expresses that* — which cost
a day when the set did not compose.

---

## R10 — The performance instrument, two corrections and a migration

**Question**: FR-079. What is the show-document load actually, and what binds?

### The first correction — contention, not code

Measured first at **32.8–33.5 ms** against a **16.5 ms** budget, and recorded in the specify pass as
*"consistent across three isolated runs, so not scheduler noise"*. That was wrong: all three readings
were taken immediately after a full-suite run, at load average 2.26 — three readings under one
contention, not three isolations. Ruled out individually before the cause was found: logging (DEBUG
handler attached → 17.3 ms), warning filters (`-W default`/`-W always` → 17.0/17.5 ms), pytest itself
(an isolated test outside this repo's conftest → 17.5 ms), this repo's conftest (→ 17.2 ms), output
capture and the logging plugin (→ 16.6/17.1 ms), and the interpreter (the hatch env and a direct
invocation were the **same** interpreter → 17.0 ms). The variable was the box.

### The migration, and what it settled

The box was then migrated (R11). **The overrun survived it**, which is the strongest available test
of FR-079's disposition: had the figure been an artefact of the old conda-built 3.11.2, it would have
vanished.

**Authoritative branch-point figures**, measured 2026-10-13 on the migrated box, quiet (load average
0.6–1.0), by each budget's own method — best of three medians of five warm runs, one warm call first,
fresh process — on the interpreter `hatch` uses:

| Path | Measured | Note |
|---|---|---|
| show-document **load**, through the test | window A of three — see the band below | budget 16.5 → **straddled**, not cleanly exceeded |
| show-document **load**, standalone | 16.305–17.241 ms across sessions | agrees with the test harness |
| show-document **save** | **13.612 – 14.297 ms** over eight samples | worst observed 14.297 |
| descriptor derivation, `script` | **1.015 – 1.060 ms** over eight samples | worst observed 1.060 |
| suite | **31.13 / 31.43 / 31.83 s** over 3565 passed = **8.73 / 8.82 / 8.93 ms/test** | counts identical to pre-migration |

**Two pre-migration figures are withdrawn, not restated as a "before".** The earlier save (28.6 ms)
and derive (2.08 ms) readings were taken with a weaker method (a single median of five) during the
contended window, and the old interpreter no longer exists to re-measure on. The method accounts for
only ~7% of the gap — measured on the new box, save is 14.755 by median-of-5 against 13.719 by
best-of-3, and derive is 1.037 either way — so contention and the interpreter build together account
for the rest, and the split between them is **unresolvable**. Citing 28.6 → 14.0 as a 51% improvement
would be a claim the evidence cannot support.

### The budget is straddled, not exceeded — and that is a different defect

**Sixteen samples across three separated windows**, all through the test, all on the interpreter
`hatch` resolves:

| Window | Samples | Spread |
|---|---|---|
| A | 16.829 · 16.898 · 17.069 · 17.110 · 17.312 | 2.9% |
| B | 16.474 · 16.532 · 16.816 · 17.322 · 17.750 | 7.7% |
| C | 16.465 · 16.625 · 16.816 · 16.819 · 17.030 · 17.262 | 4.8% |
| **pooled** | **band 16.465 – 17.750, median 16.864** | **7.8%** |

**14 of 16 exceed the 16.5 ms budget; 2 do not.** So the figure does not cleanly fail — it
**straddles the budget at its floor**, which means the assertion is **flaky on an unchanged tree**.
That is worse than a clean red, because an intermittent failure is indistinguishable from a real
regression arriving.

**This repository has met this exact pathology before and recorded the remedy.** 012's R14 replaced
008's straddled `network_map` budget with a comparison against the measured **band**, on the stated
ground that *"asserting a straddled budget would fail on an unchanged tree"*. FR-079a adopts that
precedent. It is **not** a fourth raise of the budget — the objection to a raise stands — it is a
change of instrument from a line to a band, which 012 made deliberately and documented.

### Tolerance: 115%, and the sampling lesson behind it

Pooled spread is **7.8%**, which **corroborates** 014's recorded ±4–8% rather than superseding it.
The per-window spreads were 2.9%, 7.7% and 4.8%.

⚠ **This feature revised the tolerance to 110% on the strength of window A alone** — five samples
reading 2.9% — and that was wrong. The narrowest window is not the instrument. **115%** is the
tolerance, and a tolerance claim needs samples from at least two separated windows.

| Path | Branch point (worst observed) | Budget (115%) |
|---|---|---|
| show-document **save** | 14.297 ms | ≤ 16.4 ms |
| descriptor derivation, `script` | 1.060 ms | ≤ 1.22 ms |
| suite | 8.93 ms/test | ≤ 10.3 ms/test |
| show-document **load** | band **16.47–17.75 ms** | compared against the band (FR-079a), not the straddled 16.5 line |

### The same error, three times, and what it actually takes to avoid it

The headline figure was wrong twice before it was right: **32.8–33.5 ms** from three readings taken
under one sustained contention, then **2.0–4.9% exceeded** from five readings in one quiet window.
Both were *internally consistent* and both were wrong. What finally produced a stable answer was 16
samples across three windows, plus one controlled experiment per confounder (method, logging,
warning filters, pytest, conftest, capture, interpreter, box load). **Consistency within a window is
not evidence; it is the thing that makes a bad measurement persuasive.**

## R11 — The documented interpreter, before and after the migration

### Before: the convention named an interpreter that did not exist

`CLAUDE.md` states *"Tests run under pyenv 3.11.9 — conda environments are not used for this
project"*, and every quickstart prefixes commands with `PYENV_VERSION=3.11.9`. Measured: `~/.pyenv`
did not exist, so the variable was inert, and `uvx hatch` resolved an environment based on
`/home/adria/anaconda3/envs/cuems_debian12` — CPython **3.11.2**, a **conda** environment, which the
convention explicitly disclaims. Features 011–014's figures were therefore all taken on 3.11.2.

### After: the version is right, the build is not the documented one

The maintainer migrated the box the same day — pyenv installed with a real 3.11.9 (built `CC=gcc-12`
against system OpenSSL 3.5.6, both verified), the toolchain reinstalled outside conda, anaconda
removed. The suite's interpreter is now CPython **3.11.9**, which matches the convention's version.

⚠ **But it is uv's build, not pyenv's, and they are not interchangeable.** `hatch` resolves
`~/.local/share/uv/python/cpython-3.11.9-linux-x86_64-gnu` — python-build-standalone, `Clang 18.1.8`,
PGO+LTO — while pyenv's is a local `GCC 12.4.0` build with neither optimisation. Measured side by
side on this branch, same method, same session, a contained venv per interpreter:

| Path | pyenv 3.11.9 (GCC 12.4) | uv 3.11.9 (Clang 18, PGO+LTO) | pyenv penalty |
|---|---|---|---|
| show-document load | **23.421 ms** | 17.717 ms | **+32%** |
| show-document save | 19.809 ms | 14.297 ms | **+39%** |
| descriptor derivation | 1.793 ms | 1.045 ms | **+72%** |

**The consequence is concrete**: under pyenv's interpreter the show-document load reads **23.4 ms
against a 16.5 ms budget — 42% over**. Anyone measuring ad hoc with `python` on their `PATH` — which
is pyenv's shim — would record a regression that does not exist. That is exactly the failure mode the
pre-migration version of this finding predicted, now quantified rather than hypothesised.

### Resolved: the rebuild closed the gap entirely

pyenv's 3.11.9 was rebuilt the same day with `PYTHON_CONFIGURE_OPTS="--enable-optimizations
--with-lto" CC=gcc-12` (verified in `sysconfig`: `--enable-optimizations`, `--with-lto`, `-O3`,
`-flto`, OpenSSL 3.5.6). Re-measured **interleaved**, so the comparison is robust to any drift in box
state:

| Path | pyenv, before rebuild | pyenv, after rebuild | uv | gap after |
|---|---|---|---|---|
| show-document load | 23.421 ms | **16.650 / 16.305 ms** | 16.649 / 16.505 ms | **~0%** |
| show-document save | 19.809 ms | 14.177 / 13.742 ms | 13.800 / 13.612 ms | ~2% |
| descriptor derivation | 1.793 ms | 1.060 / 1.042 ms | 1.054 / 1.015 ms | ~2% |

**PGO+LTO was the entire difference.** The residual ~2% is inside the instrument's spread, i.e. the
two builds are now indistinguishable.

**Decision, revised from the pre-rebuild version**: the convention's *"tests run under pyenv 3.11.9"*
is now substantively true, and `CLAUDE.md`'s claim no longer needs contradicting — only
**qualifying**: a pyenv build of this project's interpreter MUST carry
`--enable-optimizations --with-lto`, or recorded figures diverge by **32–72%** and an ad-hoc
measurement reads 42% over budget on unchanged code. That qualification is what goes into
`CLAUDE.md` in the polish phase (FR-092's class) and into this feature's `quickstart.md` now. The
binding interpreter for a recorded figure remains the one `hatch` resolves, because that is what the
suite uses — but it is no longer a *divergence*, just a statement of which one was measured.

**Why this matters beyond this feature**: features 011–014's figures were taken on conda-built 3.11.2
and are not directly comparable with anything measured after the migration. They remain internally
consistent and are not re-measured; one line in each is the proportionate fix, not a re-measurement
campaign.

## R12 — The three items the spec deferred to planning

| Spec item | Resolution |
|---|---|
| FR-026b's per-primitive/per-facet seeding rule | **R3**: seven rules over facets covering 25 of 30 named types and all 7 built-ins, plus a five-entry type-keyed pattern table with a completeness contract test |
| FR-079c's follow-up record — where it lives, who owns it | A new `specs/planning/show-document-load-drift.md`, owned by the maintainer, carrying all 16 of R10's measurements, the budget's history (35.99 → 15.0 → 16.5), R11's interpreter finding, and the fact that the drift **survived a full interpreter migration across two different 3.11.9 builds** — which is what makes it real rather than an instrument artefact. Against 013's own 14.07–14.96 ms the band is +13% to +19%. It is created by this feature and is **not** deleted by FR-091, because its work is open |
| FR-093's per-document dispositions for `specs/planning/xml-rebuild/` | **21 files**: 10 `xml-rebuild-0*.md` design documents and 11 under `010-consumer-prompts/`. Dispositioned in the polish phase as a table in this feature's own `migration-guide.md`, one row per file, with the same three outcomes §9.2 used — kept with a reason, re-homed, or deleted. The 10 design documents are the arc's design argument and are expected to be *kept*; the 11 consumer prompts are one-shot inputs of the same class as §9.3's seven and are expected to be *deletable* |
