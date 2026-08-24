# Phase 0 — Research: node model migration

**Feature**: `007-node-model-migration` | **Date**: 2026-08-24
**Input**: [spec.md](spec.md) (5 clarifications resolved), planning Part 2a §§4 and 7,
feature 004's `migration-map.md` §3.

Every decision below was taken against **measured** state of the four repositories, not against
the descriptions in the planning documents. Where the two disagree, the measurement is cited.

---

## R1 — Where typed decoding happens for `network_map`

**Decision**: coercion is opted into **per schema**, declared as data on the schema registry
alongside the type bindings. `Mapper.decode_config` consults that declaration and runs
`adapter_for(field.xsd_type)` on scalar fields when it is set. `network_map` sets it; the other
four configuration schemas do not.

**Rationale**: FR-011a requires typed values for `network_map` and FR-011a-i requires the other
four schemas to be untouched. Three ways to get there:

| Approach | Verdict |
|---|---|
| A flag on the registry, read by the existing walk | **Chosen.** The exception lives in the same object that already declares "these types map to these classes" — one place to look for "what is special about this schema". |
| A separate `decode_network_map` method | Rejected. A second walk over the same shape is exactly the duplication features 004–006 removed; it would drift the day a wrapper rule changes. |
| A per-class opt-in on `ConfigDict` subclasses | Rejected. Coercion is a property of the *document type*, not of one class: `CuemsNetworkMapType`, `node_list` and `node` would each have to carry the same answer, and a new class would default to the wrong one. |

**Measured**: `Mapper.decode_config` docstring currently states "no adapters run" and gives
`adopted`/`online` as its worked example. That paragraph is now wrong for one schema and MUST be
rewritten rather than left to be discovered — feature 006 recorded it as a load-bearing fact, so
overturning it silently would strand the next reader.

---

## R2 — Getting `uuid` typed without reintroducing key-name matching

**Decision**: add a `cms:UuidType` simple type to `network_map.xsd` and type the `<uuid>` element
with it. The `_UuidAdapter` already registered under that qname then binds automatically.

**Rationale**: `network_map.xsd:19` types `uuid` as `cms:NonEmptyString` today, so no amount of
adapter work derives a `Uuid` from it — D2 says the schema decides, and the schema currently says
"any non-blank text". The alternative is binding an adapter by *key name* (`"uuid"`), which is
precisely the `STRING_TYPED_KEYS` mechanism feature 004 deleted: it needs a defensive entry for
every key that might one day appear, and it silently does nothing when a key is renamed.

**Risk, and why it is acceptable**: `Uuid.__init__` rejects anything that is not a real uuid4,
including the nil UUID. `_UuidAdapter.decode` keeps an unparseable value as its **raw string**
(that behaviour is what preserves read parity elsewhere in the corpus), so a node whose `uuid` is
malformed still loads. The XSD pattern is therefore written as the canonical 8-4-4-4-12 hex form,
not as a uuid4-version assertion — the schema constrains *shape*, the value type constrains
*semantics*, and neither is made to do the other's job.

**Verified against the corpus**: all node UUIDs in the three corpus maps are canonical-form and
uuid4-shaped (`0367f391-ebf4-48b2-9f26-000000000001` and siblings).

---

## R3 — The role vocabulary: schema type, Python type, adapter

**Decision**:

- `network_map.xsd` gains `<xs:simpleType name="NodeRoleType">` restricting `xs:string` to
  `controller`, `node`, `firstrun`; `<node_type>` becomes `<node_role>` typed `cms:NodeRoleType`.
- Python gains one enum, **`NodeRole`**, whose member *values* are exactly those three strings.
- `ADAPTERS["NodeRoleType"] = _EnumAdapter(NodeRole)`.

**Rationale**: `_EnumAdapter` already does the three jobs FR-011a asks for and does them the same
way for every other enum in the package — `to_lexical` returns `str(obj.value)`, so the writer
emits `controller` because the enum *value* says so, not because of which dunder was called. That
is the whole of "an explicitly declared adapter rule rather than an accident", and it costs one
table entry.

**Why the name is `NodeRole` and not `NodeType`**: three distinct things would otherwise share
one name — `network_map.xsd`'s complex type `NodeType` (the type of a `<node>` element),
`project_mappings.xsd`'s `NodeType` (already a bound model class in
`cuemsutils/config/mappings.py`), and the role vocabulary. Two of those exist today and are
schema-derived, so the newcomer is the one that renames.

**Considered and rejected**: renaming the complex type `NodeType` → `NodeEntryType` for symmetry.
It is idiomatic XSD as it stands ("the type of a node"), it is bound in the registry and compared
by the coherence test, and the churn buys nothing once the *role* is no longer called a type.

**Note on `_EnumAdapter`'s leniency**: it returns the raw string for a value outside the
enumeration rather than raising, on the stated ground that "the schema has already rejected
values outside the enumeration by the time a document reaches here". For `NodeRoleType` that
ground is true for the first time — it was not true of `node_type` as `NonEmptyString`, which is
how `NodeType.master` became permanent. FR-014's "unknown role is a schema error" is therefore
enforced by T1 validation, and the adapter's leniency is what keeps a *programmatically* built
object from crashing the serializer. Both halves are needed; neither substitutes for the other.

---

## R4 — The free-text guard becomes structural, and what that does to the ported test

**Decision**: no denylist is ported. `name`, `ip`, `mac`, `role_id` and `alias` are
`cms:NonEmptyString` and `hostname` is `xs:string`; none of those qnames is in `ADAPTERS`, so
`adapter_for` returns `PASSTHROUGH` and the value is untouched by construction. The 106-case
regression test ports as a **guarantee test over the derived table**, not as a test of a guard.

**Rationale**: this is the payoff Part 2a §3.1 predicted. F7 existed because an external parser
re-implemented the walk and dropped the `key=` argument; there is no longer a `key=` argument to
drop, because typing comes from the schema. `STRING_TYPED_NODE_FIELDS` has nothing left to
protect and is deliberately **not** migrated — carrying it across would reintroduce the
name-matching mechanism whose absence is the fix.

**What changes in the ported test**:

| Ported case | After |
|---|---|
| 14 adversarial values × 7 text fields | 14 × 6 — `node_type` leaves the set (it is enumerated now), the other six are unchanged |
| `name='none'` survives to a valid write | Unchanged, and now also covered by the write path being first-party |
| `role_id='n'`, `alias='off'`, `hostname='007'` | Unchanged |
| `adopted`/`online` → `bool` | **Now true here** (R1), so the assertions carry across verbatim |
| `uuid` → `Uuid` | **Now true here** (R2), same |

The test must keep stating its field list *from the schema*, as it does today, so it fails on
behaviour rather than erroring on a missing symbol.

---

## R5 — The MAC-keyed working set

**Decision**: it lands as **`NodeIndex`** in `cuemsutils/config/network_map.py` — a mapping of
key → `node`, whose selection API is `by_role(NodeRole)`. `controllers` is kept as a named
convenience for the one selection that has a caller in every repository.

**Rationale**: `node_list` is taken and means the schema container (spec FR-002). The old
selection names cannot survive the vocabulary change: `masters`/`slaves` name values that no
longer exist. And `nodes` as a *role* selection on a collection **of** nodes is ambiguous by
construction — `index.nodes` reads as "all of them" and would mean "the ones whose role is
`node`". `by_role(NodeRole.node)` cannot be misread.

**Measured, and it constrains the key**: `cuems-nodeconf` keys this collection by MAC, and its
own comment records that keying merges on the Avahi-derived MAC created duplicate controller
entries, because the controller advertises as `controller` rather than as its MAC. UUID is the
primary key per the node-identity contract. `NodeIndex` therefore does **not** hard-code a key
function: it is constructed with one, and `cuems-nodeconf` keeps keying by MAC where that is what
its discovery loop needs. Moving the collection must not silently re-key it.

---

## R6 — The network-map write path

**Decision**: `CuemsNetworkMapType` gains `save(path)` — validate, then write — mirroring
`CuemsScript.save`, and `ConfigManager` gains `save_network_map()`. Both are thin: the machinery
(`documents.build_tree`, `documents.iter_schema_errors`, `documents.write_tree`) already exists
and is schema-generic.

**Rationale**: FR-009 needs a first-party write, and `documents.build_tree(obj, schema_name)`
already takes the schema name and looks the root tag up in a table that includes
`network_map` → `CuemsNetworkMap`. `write_tree` is already atomic (temp file in the same
directory + `os.replace`), which is exactly the property `cuems-nodeconf` hand-rolled at
`CuemsNodeConf.write_network_map` — so that hand-rolled atomic write is deleted rather than
ported.

**Measured**: `Settings.data2xml`/`buildxml` were deleted by feature 006 as a never-working
generic builder, and its comment records that "the config classes' byte-identity contract has
always been the read dict and never the written bytes". This feature is what gives config a
written-bytes contract, for one schema.

**Not in scope**: a write path for `settings`, `project_mappings` or `project_settings`. They
have no writer in the ecosystem and no requirement here.

---

## R7 — Non-mutating adoption selection, and a booby trap the typing creates

**Decision**: add `NetworkMap.partition_by_adoption(map)` returning `(adopted, unadopted)` as
tuples of `node` objects, mutating nothing. Keep `get_nodes_by_adoption`, **fix it to accept
already-typed values**, and deprecate it.

**Rationale, and this is the finding that matters**: `helpers.strtobool` takes `val.lower()`.
Once R1 makes `adopted` a `bool`, `strtobool(True)` raises `AttributeError`, not `ValueError` —
so FR-011a *breaks* `NetworkMap.get_nodes_by_adoption` and, through it, `cuems-engine`'s
`ControllerEngine` call at line 249. That is a silent interaction between two requirements, and
it is not optional to handle: Assumption 8 says the mutating function stays available until
feature 008 migrates its caller.

The fix is one line at each read (accept `bool` as itself, `str` through `strtobool`), and it is
**tested before the typing lands**, so the interaction is proven rather than assumed.

---

## R8 — The `cuems-common` conversion

**Decision**: a **textual, line-oriented rewrite** — not an ElementTree round trip — shipped as a
stdlib script in `cuems-common` and invoked from `debian/postinst`. It rewrites
`<node_type>VALUE</node_type>` to `<node_role>MAPPED</node_role>` and touches nothing else.

**Rationale**: an ElementTree round trip reformats the whole document — indentation, attribute
order, self-closing tags, namespace prefix rendering — so it could not honour "every other byte
unchanged", and it would not be idempotent in the byte sense either. A targeted rewrite is
idempotent by inspection (after one pass there is no `<node_type>` left to match), preserves the
`cms:` prefix and the `xsi:schemaLocation` attribute exactly, and is trivially auditable in a
postinst diff. It must import nothing from `cuemsutils`: tools under `/usr/bin` cannot, by the
shared-venv rule in `CLAUDE.md`.

**Value mapping**, accepting both legacy spellings because both exist in the wild:

| Found | Written |
|---|---|
| `NodeType.master`, `master` | `controller` |
| `NodeType.slave`, `slave` | `node` |
| `NodeType.firstrun`, `firstrun` | `firstrun` |
| anything else | **the whole file is refused**: nothing is written, a diagnostic names the node and the value, the upgrade still succeeds (FR-011h) |

**The last row changed during analysis remediation.** It previously said "left alone", which —
paired with FR-014's "an unknown role is a schema error" — described a file the conversion accepts
and the schema then rejects, with nothing specifying what happens to it. Refusing the file whole
also rules out the half-converted map: converting the recognised nodes and skipping one leaves a
document mixing both vocabularies, which no requirement describes and no test could pin.

**A backup precedes any write** (FR-011i): the file being rewritten is the only record of node
aliases and adoption state on a cluster.

**Measured packaging constraint**: `etc/cuems/network_map.xml` is installed through
`debian/install`, which makes it a **dpkg conffile** — and `cuems-nodeconf` rewrites that file on
every adoption, so on a live node it is always locally modified. Consequences the plan must
carry: the conversion runs in `postinst` (after dpkg has resolved the conffile), it must also
handle a `.dpkg-new` / `.dpkg-dist` sibling left behind by a prompt, and the shipped default in
the source tree is updated to the new format so a fresh install never needs converting.

---

## R8a — The corpus must be normalised before a round-trip diff means anything

**Decision** (taken during cross-artifact analysis remediation): the corpus network maps are
normalised to the writer's output form — no indentation, `xsi:schemaLocation` carrying the bare
filename — as a **separate, reviewable step before** the rename lands.

**Measured, and it invalidated the original requirement**: the corpus network maps are 4-space
indented and carry `xsi:schemaLocation="… /etc/cuems/network_map.xsd"`, with one document using
`https://stagelab.coop/cuems/network_map.xsd`. `build_document` emits **no** indentation and
writes the **bare filename** (feature 006's F24 fix). A `save()` round trip therefore produces
four classes of difference, not the two FR-010 permitted — and the failure would have surfaced
only at the round-trip test, after the schema, the model and the write path were all built.

**Why normalisation rather than widening the permitted diff**: the show corpus is already stored
in the writer's output form — `tests/golden/xml/cuems-utils__fade_showcase.xml` and its corpus
source are byte-identical, unindented, bare-filename. That is what makes the script byte-identity
contract checkable at all. The network maps were never given that treatment because config had no
write path until this feature. Normalising them makes the two corpora behave the same way, and
leaves FR-010's diff assertion meaning what it says.

**Kept separate from the rename** so the two transformations are never conflated in one diff: a
reviewer sees "whitespace and schemaLocation" in one change and "node_type → node_role" in
another.

---

## R9 — Goldens

**Decision**: the three `network_map` goldens (`*.reader.json`, `*.config.json`, the XML goldens)
are regenerated with `--force`, and `tests/golden/MANIFEST.sha256` is updated in the **same
commit**, with the justification in the commit message. `tests/golden/api/public_api.json` is a
separate, third permitted modification with its own justification (R10a, FR-007a).

**Rationale**: `test_golden_immutability` pins every recorded hash, and its docstring establishes
the convention — feature 006 modified exactly two goldens and each carried a recorded
justification. This feature modifies the network-map goldens *by design* (FR-026), so it follows
the same ceremony rather than inventing an exemption. The diff must be reviewable line by line:
every changed line is the rename or the value mapping, and SC-010a asserts nothing else moved.

---

## R10a — Why `config/` stays internal and `tools/NodeList.py` is the public face

**Decision** (taken during cross-artifact analysis remediation): `cuemsutils.config` exports
nothing publicly. The ported classes — `NodeRole` and `NodeIndex` — land in a new
`cuemsutils/tools/NodeList.py`, beside `ConfigBase` and `ConfigManager`. The schema-bound
containers stay in `config/network_map.py`.

**Rationale**: the spec originally required "a stable public import path" for the node models,
which contradicted D15 (the public objects are `CuemsScript` and `ConfigManager`/`ConfigBase`) and
Q14→(i). Feature 006 emptied `cuemsutils.xml.__all__` to enforce exactly that boundary; adding a
second public model package would undo it a release later.

**And one direction is forced, not chosen**: `xml/registry.py` imports `config/network_map.py`
(to resolve `_config_models`), and `tools/ConfigManager.py` imports `xml/`. A `config → tools`
import closes that cycle. So the schema-bound classes must stay on the `config/` side and
`tools/NodeList.py` must import downward. `NodeRole` is therefore defined in `tools/` and
`config/network_map.py` does **not** import it — the enum reaches the model through the adapter,
which is registered lazily inside `_register_enums` exactly as `FadeCurveType` already is.

**Consequence for the public API snapshot**: `tests/golden/api/public_api.json` pins
`ConfigManager`'s method signatures and the public symbol set. `save_network_map` and
`tools/NodeList.py` both change it, so the golden needs a third permitted modification with a
recorded justification (FR-007a) — the ceremony feature 006 established, not an exemption from it.

---

## R10 — Where the schema-bound code lands

**Decision**: `cuemsutils/config/network_map.py` — the module feature 006 created for exactly
this, whose docstring reserves the behaviour for feature 007 by name. No new module.
`cuems-nodeconf`'s `CuemsNode.py` and `NodeXmlBuilders.py` are **deleted**, not shimmed.

**Rationale**: the file already declares `node`, `node_list`, `PutType` and
`CuemsNetworkMapType`, already carries the three identity fields (FR-003 is therefore largely
*landed* — verify, do not re-implement), and is already bound in the registry. The migration adds
behaviour to declared containers rather than creating anything.

**Verified state of FR-003**: `config/network_map.py` already declares `role_id`, `alias` and
`hostname` in `node.DECLARED_DEFAULTS`. The drift Part 2a §3.2 measured was in *`cuems-nodeconf`'s*
model, which is the one being deleted. The requirement is met by deletion plus a coherence
assertion, not by adding fields.

**Aliases**: `CuemsNode` and `CuemsNodeDict` (backwards-compatibility names in the file being
deleted) are not recreated — FR-002a is explicit, and `cuems-nodeconf`'s call sites are
reformatted.

---

## R11 — What actually repairs feature 004's FR-026d

**Decision**: the repair is (a) `cuems-nodeconf` deleting the four injections, and (b) the write
path of R6 existing so node serialization works through the registry. The registry binding half
is **already done** — feature 006 bound `NodeType` → `node` and `NodeDictType` → `node_list`.

**Rationale**: the break was never "the classes are unbound"; it was "the injected handlers stop
being consulted and nothing else writes nodes". `tests/contract/test_declared_break_nodeconf.py`
pins the broken state and must be **rewritten to assert the repaired state** (FR-019) — deleting
it would erase the record that the break was declared, dated and closed.

---

## R12 — Sequencing across three repositories

**Decision**:

1. **`cuems-utils`** (this branch): capture pre-state → schema edit → model + adapter + typed
   decode → write path → tests → regenerate goldens → migration guide.
2. **`cuems-nodeconf`**: new branch from `feat/nodeconf-reenable` at `0a3ce37` — verify the
   FR-026d break exists, then delete the model and serializers, reformat call sites, retire
   `XmlReader`/`XmlWriter`, run its suite.
3. **`cuems-common`**: new branch — schema mirror, shipped default map, conversion script,
   postinst wiring, the three tools, the field-contract documentation.

**Rationale**: (1) must be first because (2) and (3) consume its schema. (2) before (3) because
`cuems-nodeconf` is the writer whose output the conversion has to match. Nothing releases until
feature 008 lands the readers (FR-030c) — the gate is stated in the migration guide, not merely
observed here.

**Verified branch point**: `cuems-nodeconf` is currently checked out on `feat/nodeconf-reenable`
at `0a3ce37 fix(parsers): stop coercing string-typed node fields on XML read`, which is the
commit the spec names.

---

## Resolved unknowns

| Unknown from Technical Context | Resolution |
|---|---|
| How to type one config schema without touching four | R1 — per-schema declaration on the registry |
| How `uuid` becomes a `Uuid` when the schema says text | R2 — the schema stops saying text |
| What produces `controller` on the wire | R3 — `_EnumAdapter.to_lexical` over `NodeRole.value` |
| What replaces `STRING_TYPED_NODE_FIELDS` | R4 — nothing; the guard is structural |
| What the MAC-keyed collection is called | R5 — `NodeIndex`, `by_role()` |
| Whether config can be written at all | R6 — yes; the machinery is schema-generic already |
| Whether typing breaks an existing consumer | R7 — **yes**, `strtobool(bool)`; fixed and tested first |
| How a deployed node's file is converted | R8 — textual rewrite from `postinst`, conffile-aware |
| Whether goldens may change | R9 — for `network_map` only, with the manifest ceremony |
