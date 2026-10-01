<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Phase 0 research — device-class reshape

**Feature**: `013-device-class-reshape` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

Every item below was measured on this branch on 2026-10-01 by reading the code it cites. Four
questions could not be settled that way and are stated as **experiments** (E1–E4) with the exact
command that answers them; they are the feature's first tasks and they gate the design, which is
why each one also records what the design does under either outcome.

The spec forbids re-litigating one thing — that `xs:alternative` **validates** under the pinned
`xmlschema==3.4.3` (measured 2026-09-23). Nothing here revisits that. What R1–R5 establish is a
different question the spec could not have known to ask: whether this library's **own** mapping
engine can decode such a document, and what it costs to teach it.

---

## R1 — The engine resolves a model class from a *static* type per element tag

**Decision**: add a per-instance dispatch to exactly one function, `Mapper._decode_member`, fed by a
new `FieldSpec.alternatives` recorded at derivation time.

**Evidence**. Derivation fixes one child type per element name, once, at compile time:

```181:198:src/cuemsutils/xml/spec.py
        fields.append(
            FieldSpec(
                name=element.local_name,
                xsd_type=element.type.local_name if element.type is not None else None,
                ...
                child=_type_key(schema_name, element.type),
            )
        )
```

The model class then comes from the registry, keyed by that type's name — never from the instance:

```245:253:src/cuemsutils/xml/mapper.py
    def _model_for_spec(self, spec: TypeSpec):
        binding = (
            self.registry.binding_for_path(spec.key.name)
            if spec.key.is_path
            else self.registry.binding_for(spec.key.name)
        )
```

And a repeated block resolves its member by the **wrapper tag**, which is how an `xs:choice` of six
cue types works today (`mapper.py:193-211`, comment at `:196-198`). Nothing in `src/cuemsutils`
reads `xsd_element.alternatives` or calls `xsd_element.get_type(elem)` — conditional type
assignment exists only inside `xmlschema` itself.

**Why the fix is small**: both the repeated path and the wrapper path funnel into one place.

```213:218:src/cuemsutils/xml/mapper.py
    def _decode_member(self, body, member):
        """Decode one member of a repeated block, honouring ``OPAQUE_TYPES``."""
        if member.child.name in self.OPAQUE_TYPES:
            model = self._model_for_spec(derive(member.child))
            return model(body) if model is not None else body
        return self.decode(body, derive(member.child))
```

`member.child` is the single static type. With `alternatives: dict[str, TypeKey]` on `FieldSpec`,
this becomes `member.alternatives.get(body.get(DISCRIMINATOR), member.child)` — and because the
converter puts attributes into the decoded dict under their bare names (R4), the discriminating
value is already in `body` when the dispatch runs. **No cooperation from `xmlschema`'s instance
typing is required on the decode path.** That is what makes FR-050a affordable.

**Alternatives considered**. (a) Bind one superset model per element and carry the class as data —
rejected for the cue side by FR-050a, which requires `AudioCue`/`VideoCue`/`DmxCue` to survive, and
rejected for devices because `VideoDeviceType`'s `canvas_region` must stay invalid elsewhere (FR-003).
(b) Dispatch inside each model's `from_decoded` — rejected: it would put type resolution back in the
model layer that `spec.py`'s docstring says is "not allowed to decide" it.

---

## R2 — The converter cannot decode a type that mixes single children with a repeated child

**This is the single most load-bearing finding in Phase 0, and it rules out the naive shape.**

**Decision**: every reshaped repeated element lives inside a **container element** whose type holds
nothing else — the idiom `OutputsType`, `NodesType` and `RegionsType` already use. `NodeMappingType`
keeps `uuid` and `mac` as single children and gains `<devices>`; `NodeConfType` gains `<players>`;
the `project_mappings` root gains a container for the reshaped `default_*` pairs.

**Evidence**. The fork's content assembler switches the whole result from dict to list the moment a
repeated child appears, discarding what it had accumulated:

```121:127:src/cuemsutils/xml/converter.py
    def _decode_content(self, content):
        """Assemble decoded children under the three rules above.

        Note the shape switch: as soon as a repeated child appears, the result
        becomes a **list** rather than a dict, and every subsequent child is
        appended to it. That is what produces ``"contents": [{...}, {...}]``
        rather than a dict keyed by cue type.
        """
```

```144:148:src/cuemsutils/xml/converter.py
            if name not in result:
                if repeated:
                    result = self.list([{name: value}])
                else:
                    result[name] = value
                continue
```

A `NodeMappingType` declaring `uuid`, `mac` and a repeated `device` would therefore decode to a list
whose first element is the first `device` — **`uuid` and `mac` silently gone**. The same code says
the companion case does not arise today:

```186:190:src/cuemsutils/xml/converter.py
        if isinstance(content, list):
            # A repeated block carries no room for attributes; upstream's
            # result is the only defined shape here. Does not occur in the six
            # schemas.
```

Both statements hold only because **no type in the six schemas mixes single and repeated element
children**. The reshape would introduce the first one, in three types at once.

**Why the container is the right answer rather than a converter fix**: the wrapper is already a
first-class concept with decode support, and the wrapper element deliberately does not appear in the
object model, so the model keeps a plain list field:

```221:229:src/cuemsutils/xml/mapper.py
    @staticmethod
    def _is_wrapper(child_spec: TypeSpec) -> bool:
        """A type whose only job is to hold repeated children.

        ``RegionsType`` holds ``Region``, ``OutputsType`` holds the three
        output types. The wrapper element exists in the XML but not in the
        object model, where the field holds the list directly.
        """
```

`_decode_wrapper` (`mapper.py:231-243`) then routes every item through `_decode_member` — the exact
function R1 adds the dispatch to. The two findings compose: **container + one dispatch point**.

**Alternatives considered**. Changing `_decode_content` to keep a dict and collect repeated children
into lists was rejected on scope and risk: it is the shape every golden, every `outcomes.json` entry
and the whole wire contract is cut against (`converter.py:22-26`), and feature 006's measured
C2 guarantee is stated in terms of it. A reshape is not the feature in which to re-cut the decoded
shape of all six schemas.

**Cost this imposes**: `script.xsd`'s two choices (`CueListContentsType`, `OutputsType`) are already
repeated-only, so axis D needs **no** new container. Axis A needs two (devices, root defaults) and
axis C needs one (players). Three containers are three new element names in documents on disk, which
the migration tool writes — not a new cost, just a bigger diff.

---

## R3 — The class→type table must be derived from the schema, not declared in Python

**Decision**: the dispatch map is read out of the schema's own `xs:alternative` declarations, under a
pinned authoring convention: a conditional test is **exactly** `@class='VALUE'`, one value per
alternative, plus one unconditional fallback. A contract test enforces the convention over all six
schemas, and `spec.derive` extracts `VALUE` from each test.

**Rationale**. SC-002 requires a class with special fields to cost **one** conditional-type
declaration plus the type it names, in **one** schema. A Python-side table mapping `"video"` to
`VideoDeviceType` would be a second declaration site, and FR-010 forbids the library declaring a
device-class list at all. Deriving the map keeps the schema the only place a class is ever named.

**Evidence it is extractable**: `xmlschema`'s `XsdElement` exposes `alternatives` as a sequence of
`XsdAlternative`, each carrying its `test` as an XPath selector object; the library already depends
on the same XPath engine for `xs:assert` (`script.xsd:43`). The convention is what keeps extraction
from becoming XPath interpretation — see **E2**.

**Alternatives considered**. Interpreting arbitrary XPath tests (rejected: unbounded, and a
mis-parsed test fails silently by selecting the fallback type, which is the `one_custom_template_per_node`
trap in a new costume — see R12). A naming convention mapping class value to type name, e.g.
`"video"` → `VideoDeviceType` (rejected: that is name-mangling, which `registry.py`'s own docstring
records as having cost this project thirteen silently-missed bindings).

---

## R4 — `class` is the third kind of declared attribute, and it cannot be a Python property

**Decision**: the discriminator is spelled `class` in the document, as §8.4's proven measurement
used; it is a **declared** attribute, so it becomes a model field automatically; it is read in Python
as the dict key `class`, and any accessor that needs a name gets `device_class`.

**Evidence**. Declared attributes are derived into `FieldSpec`s with `kind=ATTRIBUTE`
(`spec.py:227-259`) and emitted on build via `element.set` (`mapper.py:781-783`), so round-tripping
is existing machinery. Two things follow that the plan must carry:

1. `spec._derive_attributes`' docstring makes a **counting claim** that this feature falsifies:
   *"Only two attribute declarations exist across all six schemas"* (`spec.py:227-235`). It is
   updated in the same commit as the first schema that adds a third.
2. The decoded key is the bare name, because the converter is configured `attr_prefix=""`
   (`converter.py:66`, `mapper.py:966`). `class` is a Python keyword, so no `@property` of that name
   can exist on the dictionary-backed models — a dict **key** is fine, a descriptor is not.

`doc_version` is excluded from the model by name (`spec.py:225`'s
`ATTRIBUTES_THE_MODEL_DOES_NOT_OWN`); `class` is **not** added to that set — it is domain data, and
it must round-trip.

---

## R5 — Class uniqueness as `xs:assert`: one precedent, one dependency, one unknown

**Decision**: express FR-013 as an `xs:assert` on the container type, not as a T2 rule.

**Evidence**. Exactly one assert exists today, and nothing in Python reads its message:

```43:43:src/cuemsutils/xml/schemas/script.xsd
            <xs:assert test="modified &gt;= created" />
```

So the precedent exists and the failure mode is a plain T1 validation error. The clarification
session chose schema enforcement because `cuems-editor` validates the document it writes directly
(`CuemsDBProject.py:304-305`, `:876-877`) rather than through this library's load path, and a T2 rule
would not hold there.

**The unknown**: whether the pinned `xmlschema` evaluates `count(devices/device) = count(distinct-values(devices/device/@class))`
— an XPath 2.0 function — inside `xs:assert`. See **E3**. If it does not, the fallback is a T2 rule
plus a documented gap for third-party writers, recorded rather than hidden.

---

## R6 — The migration tool: a new entry point, with `cuems-convert-documents`' discipline reused

**Decision (FR-029, recorded here as the planning decision the spec asked for)**: a **new** entry
point, `cuems-reshape-devices`, reusing `tools/library_reach.py` for discovery and the backup and
atomic-write discipline of `convert_documents`/`documents.write_tree`. `cuems-convert-documents` is
not extended.

**Evidence that extending it does not work as-is**. Its entire "does this need work?" decision is the
version marker, and this feature moves no marker:

```76:79:src/cuemsutils/xml/convert_documents.py
    version = read_version(tree)
    current = CURRENT_VERSION[schema_name]
    if version >= current:
        return ConversionOutcome.CURRENT
```

It also takes explicit paths only — no installation discovery, no library walk, no flags at all
(`convert_documents.py:103-134`) — while FR-022 requires one run over the three configuration
documents **and** every project in the library. And its module docstring stakes a claim this feature
would falsify: *"**The only implementation** (SC-019): this walks the same `versioning.convert`
registry … rather than a second, hand-rolled rewriter"* (`convert_documents.py:1-13`).

**Evidence for the new tool's shape**: feature 012's `remint` is the worked precedent for an
out-of-band, installation-wide rewrite that the version registry has no key for — survey, abort
before writing, persist, apply, verify, record (`remint.py:903-1048`) — and `library_reach` already
exists as the **shared** enumerator, deliberately split out so a read-only diagnostic need not import
the destructive module (`library_reach.py:3-8`). Scripts are found by root element, not filename
(`remint.py:671-679`, `library_reach.py:19-23`), which is FR-023 already implemented.

**What this costs, and the one thing it buys back**: a third operator CLI alongside
`cuems-init-node` and `cuems-convert-documents`. It buys a tool whose discriminator is the
document's *shape*, which can therefore say exactly what FR-027 requires, and leaves the
version-driven tool's contract — including its silent treatment of too-new documents — untouched.
Tracked as a justified deviation in [plan.md](plan.md)'s Complexity Tracking.

**Backup model**: `convert_documents`' timestamped sidecar (`path.with_name(f"{path.name}.{ts}.bak")`
+ `shutil.copy2`, `convert_documents.py:81-85`) satisfies FR-025 directly, including "fatal for that
document only". `remint`'s table-and-record model is **not** copied: it exists because a re-mint is
cluster-wide and resumable across machines, which a single-installation reshape is not.

---

## R7 — `cuems-common` has three XML readers in scope, not one, and one of them exits

**This widens the spec.** M8/M8a name `cuems-extract-video-latency` and classify it as axis C. There
are two more, both on **axis A**, both reading `default_mappings.xml`'s `<video>` tree by XPath from
`/usr/bin`-class scripts that cannot import `cuemsutils`:

| Site | Reads | Fault class | Consequence on an un-ported node |
|---|---|---|---|
| `usr/lib/cuems/bin/cuems-extract-video-latency:39` | `.//videoplayer/output_latency_ms` (axis C) | keeps resolving and becomes wrong | writes an empty `OUTPUT_LATENCY_FLAG`; configured video latency silently discarded |
| `usr/lib/cuems/bin/cuems-generate-display-conf:66-84` | `.//video/outputs/output`, `mappings/mapped_to`, `canvas_region` (axis A) | keeps resolving and becomes wrong | empty or wrong `display.conf` |
| `usr/lib/cuems/bin/cuems-display-setup:527-571` | `./video/outputs`, `.//video/outputs/output/...` (axis A) | **raises** — `sys.exit` when `./video/outputs` is absent | display setup fails outright |

Measured at `cuems-common` `feat/xml-refactor` `6ab4655`, clean. Its `xml-refactor-merge-candidate`
tag points at `91b2d254`, **not** at HEAD — so the candidate tag will have to be re-cut for this
feature regardless, which is the reciprocal-tag lesson `CLAUDE.md` already records.

**Consequence for the spec**: FR-042's second bullet is one of three sites, and the display pipeline
— the thing that drives monitors on a node — is in axis A's blast radius, not axis C's. Phase 0
folds this into the spec as **M10**.

---

## R8 — `cuems-editor` is not only a pass-through

**This widens the spec.** M5 classifies the editor's site as `CuemsWsServer.py:439`'s merge over a
dict passed verbatim. Confirmed — the merge really is a pass-through, and `:439` is a comment with no
keyed access. But the editor has **keyed cue access elsewhere**, on its database/script path:

| Site | Code | Fault class |
|---|---|---|
| `CuemsDBProject.py:385` | `CUE_TYPES = ['AudioCue', 'VideoCue', 'DmxCue', 'ActionCue', 'FadeCue', 'CueList']` | keeps resolving and becomes wrong for the three hardware keys |
| `CuemsDBProject.py:408-436` | `_collect_cue_ids` / `_nullify_dangling_refs` iterate `CUE_TYPES` | same — dangling-reference cleanup stops seeing hardware cues |
| `CuemsDBProject.py:78-82` | `'AudioCue' in item` / `'VideoCue' in item` in `_walk_media_durations` | same |
| `CuemsDBProject.py:886-896`, `:873-884`, `repair_durations.py:204,231` | `XmlReaderWriter` read/write of project scripts | raises on an un-migrated document (the safer direction, spec §Edge Cases) |

Measured at `cuems-editor` `feat/xml-refactor` `36260e2`, clean, pinning `cuemsutils>=0.1.0rc10`.
Its suite measured 2026-10-01: **54 passed, 7 failed, 2 collection errors** — and all nine failures
have **one** cause, `ModuleNotFoundError: No module named 'cuemsutils.create_script'`, reached
through `CuemsWsServer.py:27`. The spec's "7 pre-existing failures plus two modules that have not
imported since feature 008 retired `create_script`" is therefore one fault, not three.

Folded into the spec as **M11** in Phase 0. It does not change FR-033's claim — the merge is still
not among flow 02's fourteen call sites — it adds sites FR-030 must name.

---

## R9 — `cuems-frontend`'s reach is eight files, not two

**This widens the spec.** M1 and M3 name `projects.service.ts:34-60`, five sites in
`project-edit/sequence.component.ts` and one chain in `project-show/sequence.component.ts`. All
confirmed at `3183845` (clean). The measured total is about **45 line-ranges across eight files**:

- Axis A: `projects.service.ts:38-43,504-534,613-631`; `settings.component.ts:68-88` and its template
  `settings.component.html:40-130`; `project-show/audio-mixer.component.ts:94-100`;
  `project-show/video-mixer.component.ts:107-114`; `project-edit/sequence.component.ts:379,449,682-683`
  (the `default_*` keys).
- Axis D: `project-edit/sequence.component.ts` at thirteen ranges including the save wrapper
  `{ [cueTypeKey]: newCue }` at `:1088` (`:922-940` sets the key); `project-show/sequence.component.ts:95-97,117-193`;
  `shared/audio-mixer/*` reading `output.AudioCueOutput` at `:53-76`.
- Unaffected and worth saying so, because they look affected: the TS unions at `:28,292,643`, the
  icon service, OSC paths, i18n keys and route names are internal UI vocabulary, not wire keys.

**It also has no characterization tests**: five `.spec.ts` files exist, none covering
`projects.service.ts`, either `sequence.component.ts`, or `settings.component.ts` — so flow 05's
US8/T032 precondition is unmet in the tree today, which is exactly why FR-032 exists. Folded into the
spec as **M12**.

---

## R10 — A third compatibility surface the spec does not cover: `node_mappings["audio"]`

**Decision**: `ConfigManager.node_mappings` keeps answering to a device-class key, derived from the
document, by the same reasoning the clarification session applied to axis C.

**Evidence**. `cuems-engine` reads the mappings device sections by name on its port-setup path:

```508:508:/disk/Projects/StageLab/cuems-engine/src/cuemsengine/NodeEngine.py
        for port_type_dict in self.cm.node_mappings.get("audio", []):
```

and the same shape at `:598` for `"video"`. These are **`.get(..., [])`**, so after the reshape they
would return the default and the engine would configure **no ports at all** — silently. That is
FR-031's middle class on a startup path, and neither FR-012 (which is about `node_hw_outputs`) nor
FR-042 (which is about `node_conf`) covers it.

The spec's settled answer for axis C was "the Python accessors keep resolving"; this is the same
question one document over, so the plan applies the same answer rather than inventing a new one. It
is **not** a declared class list: the projection resolves any class the document carries, so FR-010
still holds. Recorded as decision **D1** in [plan.md](plan.md) and folded into the spec as **M13**.

---

## R11 — `node_hw_outputs` can satisfy FR-010, FR-012 and A4 at once, with no class list

**Decision**: one derivation, into a mapping whose `__missing__` returns an empty list for any
`{class}_{inputs|outputs}` key.

**Evidence of what has to hold simultaneously**: FR-010 deletes `_DEVICE_SECTIONS`
(`ConfigManager.py:69`); FR-011 wants one definition rather than the two six-key literals
(`:159-166`, `:283-290`); FR-012 and M2 require `node_hw_outputs["video_outputs"]` not to raise on a
node with no video device, because `NodeEngine.py:566` subscripts it unguarded; A4 keeps the three
legacy spellings answering. Pre-seeding the three classes would satisfy all but FR-010 — it is a
declared class list with extra steps. `__missing__` satisfies all four, and it degrades correctly at
both engine sites: `.get("audio_outputs")` at `:456` still returns `None` (`dict.get` does not
consult `__missing__`) and is used for truthiness, while the bare subscript at `:566` yields `[]`
and the engine logs "No video outputs detected" and returns.

Measured consumer reads: three, all in `NodeEngine.py` (`:456`, `:457`, `:566`), confirming M2.

---

## R12 — The T2 rule is bound to a field this feature deletes, and a test pins the binding

**Decision**: the rule's target moves to the container field in the same commit as the schema, and
its body filters by class; the pin moves with it.

**Evidence**. The registration names the literal field:

```792:798:src/cuemsutils/xml/validators.py
    [("NodeMappingType", "video")],
```

`run_rules` **skips a rule whose field is absent from the object** (`validators.py:431-432`), so a
stale binding does not fail — it stops running, and a document with two custom templates would start
loading. A contract test pins the exact pair today and must change with it:

```123:125:tests/contract/test_rule_targets_resolve.py
    assert RULES["one_custom_template_per_node"].applies_to == (("NodeMappingType", "video"),)
```

The live call site walks the same name — `node.get("video")` at `validators.py:90-92`, inside
`validate_custom_templates`, reached from `ProjectMappings.process_xml_dict`
(`xml/settings.py:318-335`) — and `check_canvas_region_containment` runs from there (FR-016). The
descriptor's repairability map raises `RepairabilityTargetError` on a target class that does not
exist (`descriptor.py:200-201`), which catches a renamed *class* but not a renamed *field*: the field
half is what `test_rule_targets_resolve.py` exists for.

---

## R13 — What the test estate requires, including one test that asserts the opposite of SC-003

**Decisions**: (a) the old shape is preserved as a corpus snapshot `tests/data/corpus/pre-013/`,
following `pre-008/`'s precedent, so the migration has real documents to prove itself on; (b)
`tests/unit/test_mappings_shape.py` is **inverted**, not deleted; (c) `outcomes.json` is edited
surgically, never recaptured.

**Evidence**. A test currently requires the constant SC-003 forbids:

```136:141:tests/unit/test_mappings_shape.py
        source = inspect.getsource(method)
        assert "_DEVICE_SECTIONS" in source
        assert "_unwrap_put" in source
```

Same-commit obligations, each with its mechanism: `CURRENT_SCHEMA_HASHES`
(`tests/contract/test_schema_scope.py:65-72`, sha256 of file bytes); the overlap allowlists
(`test_schema_name_overlap.py:80-97` identical, `:105-126` divergent and **empty**), where a stale
entry fails as loudly as a missing one (`:235-249`); `EXPECTED_VERSIONS`
(`test_version_marker.py:122-129`) and `DELIBERATE_IDENTITY_STEPS` (`:148-152`), both of which this
feature leaves **untouched** — FR-020 means `test_each_schema_is_at_its_pinned_version` and
`test_every_schema_past_version_1_has_a_conversion_for_every_step` keep passing with no edit.

Golden discipline: `tests/support/capture_goldens.py` with `--force` only as a recorded decision
(`:13-15`, `:374-378`), `tests/golden/MANIFEST.sha256` updated for any listed file that changes, and
`outcomes.json` explicitly **not a regeneration target** (`capture_goldens.py:242-256`). The
corpus holds 12 `project_mappings`, 12 `settings`, 4 `hardware_outputs` instances and ~14 scripts
across current and `pre-008/` trees; every current-shape one is migrated by this feature, and
`pre-008/` is left alone, since it exists to feed the version conversions and is already invalid
against current schemas by design (`tests/data/corpus/pre-008/README.md:12-15`).

The closest precedents for SC-003's source-level ratchet are `tests/contract/test_node_field_coercion.py:168-193`
(an AST walk asserting a name appears nowhere) and `test_retired_script_generator.py:46-61` (a
substring grep with an explicit exemption list).

---

## R14 — The build generates three of the documents this feature reshapes

**Decision**: seeds and generators move with each axis, in the same commit, and the determinism check
the build already runs is the gate.

**Evidence**. `make_defaults.DOCUMENT_NAMES = ("settings.xml", "network_map.xml", "default_mappings.xml")`
(`make_defaults.py:37`) — two of the three are reshaped by this feature — generated at package build
through the just-built venv (`debian/rules:27-29`) and installed by `postinst` only where absent
(`debian/cuems-utils.postinst:64-73`). The seed loader enforces four rules, two of which fail
closed on a rename: **V2** every entry names a declared field, **V1** every required scalar is seeded
(`seed_values.py:12-22`, `:151-178`), with tables keyed by `[schema.Type]` (`TABLE_KEYS`, `:54-66`).
`src/cuemsutils/defaults/system-defaults.toml` carries the six `default_*` strings at `:105-110` and
the three player tables at `:55,69,84`. The settings example generator names the four player sections
as literals (`descriptor.py:550-566`), so axis C touches it directly. FR-043 is therefore not a
check — it is work, in `system-defaults.toml`, `seed_values.TABLE_KEYS` and
`descriptor.generate_settings_example`.

`postinst` always refreshes `/etc/cuems/*.xsd` on configure (`:43-54`) and never rewrites an existing
`.xml`, which is precisely why FR-022's tool is the only thing that migrates a live node.

---

## R15 — Measurement method, and the denominators this feature must set

**Decision**: re-measure every budget's denominator on this branch before any code change, and record
ranges rather than single runs, as feature 012 did after finding two inherited numbers unable to fail.

Harness facts: performance tests live in `tests/integration/` (no `tests/performance/`);
`test_read_path_regression.py:76-102` takes the best of 3 medians of 5 warm runs with
`time.perf_counter()`; `tests/support/library_fixture.py` provides `remint_200` (200 projects, ~4 MB)
which this feature reuses as its named throughput fixture; the suite runs
`PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:run -- -q`. Budgets to set from **E4**: the load path
for `project_mappings`, `settings`, `script` and the suite's per-test time (the spec already fixes
that one at ≤ 18.04 ms/test), plus the tool's throughput over `remint_200`.

---

## Experiments — the four things reading cannot settle

Each is a Phase 0 task, each writes its result into `baseline.md`, and each has a stated fallback so
no outcome blocks the feature.

| # | Question | Command / method | If it fails |
|---|---|---|---|
| **E1** | Does a container + `xs:alternative` document decode through `CuemsConverter` with the discriminator present in the item dict, and the alternative's content intact? | build a throwaway schema and document in `tmp_path`, decode with `XMLSchema11(..., converter=CuemsConverter).to_dict(...)`, print the dict | if the discriminator is absent from the item dict, the dispatch reads it from `xsd_element.get_type(elem)` instead and the decode path gains a cooperation with `xmlschema` that R1 avoided |
| **E2** | Does `xmlschema==3.4.3` expose each `xs:alternative`'s test in a form from which `@class='VALUE'` is extractable without interpreting XPath? | inspect `schema.elements[...].alternatives` / the element's `alternatives` attribute on a compiled schema | fall back to declaring the map in the schema's `xs:appinfo` — still one schema, still one declaration, satisfying SC-002 |
| **E3** | Does `xs:assert` with `count(...) = count(distinct-values(.../@class))` compile and reject a duplicate class? | validate a two-`audio`-device document against a schema carrying the assert | fall back to a T2 rule (`repairable=False`), and record the gap for third-party writers in the migration guide rather than leaving it implied |
| **E4** | What are this branch's pre-change load times for all four axes, and the suite's per-test time? | `test_read_path_regression.py`'s method, 3×5 warm runs per document; full suite 3 runs | nothing to fall back on — this one sets FR-PERF-001's denominator, and the spec's own checklist makes it a precondition |

**E1 and E2 together are the feature's go/no-go on FR-050a's "the public classes stay".** If both
fail, the honest options are a converter change (R2's rejected alternative) or re-opening the
clarification that chose option A for axis D depth — and the plan says so rather than discovering it
in Phase 3.
