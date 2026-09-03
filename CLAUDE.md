# cuems-utils

Part of the **CUEMS** ecosystem — see the [`cuems-RELATIONS`](https://github.com/stagesoft/cuems-RELATIONS) repo for the system index, architecture diagram, and protocol/port map.

## Role

Shared Python library (`cuemsutils` on PyPI) used by the engine, editor, and other components. Python 3.11+, mostly stdlib (`enum`, `threading`, `time`) + `xmlschema`. Build/test with `hatch` (see below). **Commits are GPG-signed** (retry on "gpg failed to sign", never `--no-gpg-sign`).

## Submodules

- **`cues/`** — Cue object model: `Cue`, `CueList`, `CuemsScript`, `AudioCue`, `VideoCue`, `DmxCue`, `ActionCue` + output classes. Dictionary-backed objects with `@property` descriptors.
- **`xml/`** — XML serialization (`XmlReaderWriter`, `XmlBuilder`, `Parsers`), XSD schema validation, settings/config file classes. Namespace `xmlns:cms="https://stagelab.coop/cuems/"`. Also ships the node-identity schema `src/cuemsutils/xml/schemas/network_map.xsd` (mirrored to `/etc/cuems/network_map.xsd` by cuems-common) — the node's role lives in `<node_role>`, typed `cms:NodeRoleType` (`controller`/`node`/`firstrun`; renamed from the free-text `<node_type>` carrying `NodeType.master`/`NodeType.slave` in `007-node-model-migration`), plus the identity fields. The typed Python enum is `cuemsutils.tools.NodeList.NodeRole`; renaming the schema element again is an XSD migration that bumps every `cuemsutils.xml`/`cuemsutils.tools.NodeList` consumer. See the cuems-common CLAUDE.md for the node-identity field contract. That repository's phase was descoped from `007-node-model-migration`'s pass in *this* repo, but it has since landed on cuems-common's own local `007-node-model-migration` branch (four commits, 2026-08-24: schema mirror + shipped-map conversion, the conversion script wired into `postinst`, versioned package dependencies, and the documentation pass) — unmerged and unreleased, but **not** "not started", as this line said until 2026-09-03. Corrected by `specs/planning/xml-rebuild/xml-rebuild-09-consumer-audit.md` C9.
- **`tools/`** — `ConfigManager` (system config), `HubServices` (NNG bus / req-rep messaging), `SignalEngine` (systemd lifecycle), `CTimecode` (SMPTE timecode; `milliseconds_exact` is wrap-accumulated / 24h-safe).

## Build

```bash
cd <this repo> && hatch test --show   # tests
hatch build                            # build
```

Env vars: `CUEMS_LOG_LEVEL`, `CUEMS_CONF_PATH`.

## specs/planning — canonical home for non-code artifacts

All planning docs, implementation plans, agent prompts / reusable AI prompt templates, cross-feature/repo specs, contributor-workflow docs, future-development/deferred-work/roadmap notes MUST be stored in `specs/planning/` and looked for there first. Do NOT put them in `docs/`, the repo root, or feature spec dirs. Feature-specific specs (`specs/NNN-feature/`) stay in their own numbered dir. `specs/planning/documentation-prompt.md` is the unified prompt for generating README/CHANGELOG/docs across CueMS / StageLab sibling repos.

## Field notes / gotchas

- **The shared venv `/usr/lib/cuems` is one-way**: it has `include-system-site-packages = true`, so the venv sees system packages but the system `/usr/bin/python3` **cannot** import `cuemsutils`. Any tool whose entry points live in `/usr/bin` (dh-python3) must not `import cuemsutils` — reimplement with stdlib. (See the portable-.deb notes in the cuems-thermalmon CLAUDE.md.)
- Many packages populate that shared venv (`cuemsutils`, pynng, lxml, **websockets** from cuems-utils; **pythonosc** from cuems-engine; plus editor/nodeconf/midi-connector). A `.deb` must not bundle anything another package already ships, or `dpkg -i` aborts on a file-overwrite conflict. lxml is bundled at 5.3.0 (CVE-2026-41066 fixed in 6.1.0; audited across all components — zero parser call sites, reachable risk nil).

### Building the `.deb` — verify the venv interpreter before shipping

Built from the `debian/bookworm` branch (merge `main` in, add a `debian/changelog` entry, then `dpkg-buildpackage -us -uc -b`; artifacts land in the parent dir).

`debian/rules` pins `dh_virtualenv --python /usr/bin/python3` **by absolute path on purpose**. It used to say `--python python3`, which resolves through `PATH` — so building on a dev box with **pyenv** active baked the builder's private interpreter into the package:

```
pyvenv.cfg  home = /home/<user>/.pyenv/versions/3.11.2/bin
bin/python -> /home/<user>/.pyenv/versions/3.11.2/bin/python3.11
```

On every target host that symlink is broken, so `/usr/lib/cuems/bin/python` does not exist and **nothing in the shared venv can start** — every CUEMS Python component at once. There is no build-time error; it only surfaces after `dpkg -i` on a node, and even then the running process survives until the next restart. Always check before shipping:

```bash
dpkg-deb --fsys-tarfile <deb> | tar -xO ./usr/lib/cuems/pyvenv.cfg | grep '^home'
# must be:  home = /usr/bin       (and bin/python -> ../../../bin/python3, relative)
```

### "Editable install" on a host is a no-op unless you remove the packaged copy

The `.deb` installs `cuemsutils/` into `/usr/lib/cuems/lib/python3.11/site-packages/`, which comes **before** any `.pth`-appended path in `sys.path`. So a `_cuemsutils.pth` pointing at `/home/stagelab/src/cuems-utils/src` is silently ignored while the package is installed — which is why past "editable" deploys did nothing and people resorted to rsync-ing source over site-packages (leaving mismatched source/dist-info, e.g. rc13 files under an rc12 `dist-info`). To get a real editable install:

```bash
/usr/lib/cuems/bin/pip uninstall -y cuemsutils
rm -rf /usr/lib/cuems/lib/python3.11/site-packages/cuemsutils   # pip leaves non-RECORD strays
/usr/lib/cuems/bin/pip install -e /home/stagelab/src/cuems-utils --no-deps
```

Note `pip install -e` needs network for the build backend, so it is not an option on an offline node — install the `.deb` there instead. And an `apt install --reinstall cuems-utils` restores the packaged copy and silently re-shadows the editable tree.

## Active Technologies
- Python 3.11+. **Tests run under pyenv 3.11.9** — conda environments are not used for
  this project.
- `xmlschema==3.4.3` (pinned; XSD 1.1 required by `xs:assert` in `script.xsd`),
  `lxml==6.1.0` (**not** in the XML write path — the writer is stdlib `ElementTree`).
- Six bundled XSD schemas under `src/cuemsutils/xml/schemas/`.
- **Suite baseline (measured 2026-08-20, after feature 006): 2222 passed, 94 skipped,
  2 xfailed in ~59 s** — about **27 ms per test**. Take the per-test figure, not the wall
  time: the suite grew from 1485 tests (44.57 s, 30 ms/test) to 2222 across features 005
  and 006, so an absolute wall-time budget compares different suites and reads a growing
  test corpus as a regression. See `specs/006-public-object-api/baseline.md` for the
  measurement context and the per-operation numbers.

## Recent Changes

- `008-rebuild-extension` (**Phase 2/ITEM E landed** 2026-09-02; Phase 1/ITEMs A–D landed
  2026-09-02 at the D30 gate — see `specs/008-rebuild-extension/plan.md`): five structural
  changes landed as one dependency chain across two gated phases. Phase 1 — ITEM A retypes
  `Media.duration` to `cms:CTimecodeType` (the seventh and last time-carrying element) and
  deletes the fade-profile surface and a dead `settings.xsd` timecode pair; ITEM B gives
  `settings`/`project_settings`/`project_mappings` a `save()` path symmetric with `network_map`'s
  (007); ITEM C ports the network-map domain logic (`NodeIndex.merge`/`adopt`/`unadopt`/
  `set_controller_always_adopted`/`missing_adopted`/`signature`, `CuemsNetworkMapType.refresh`) in
  from `cuems-nodeconf`, characterized before the port, with **no first-party caller yet**; ITEM D
  builds a schema descriptor (`xml/descriptor.py`) over all six schemas — types, enums, model-layer
  defaults, and a repairability classification for every field — and retires `create_script()` and
  the hand-maintained `templates/settings.xml` in favour of descriptor-generated examples.
  - **Phase 2 (ITEM E) makes reading strict — the one deliberate reversal of "reading never becomes
    stricter"** (feature 006's FR-026, superseded here as FR-037/FR-038): `CuemsScript.load` and
    every `ConfigManager`/`ConfigBase` accessor now run T1 **and** T2 on every read. Five outcomes:
    valid loads clean; a version-old document converts **in memory** (file on disk untouched); a
    current document with a **repairable** T2 violation loads with the field repaired to the
    descriptor's default; an **unrepairable** one raises `ValidationError`; a document newer than
    the library raises, distinguishably. `CuemsScript.load_with_report(path)` is the new public
    entry point that returns `(script, LoadReport)` — `load()` keeps its old signature and just
    discards the report.
  - **The document-version marker** (`doc_version`, `xs:positiveInteger`, `use="optional"`) is now
    on every schema's root type — D3's **fourth** relaxation, purely additive, invalidates nothing
    on disk. It is a document property, never a domain field: excluded from `spec._derive_attributes`
    and every wire projection, read by a pre-validation stdlib-`ElementTree` probe
    (`xml/versioning.read_version`) before any schema decode is attempted. Versions move **per
    schema** — `script` is now version **2**; the other five stay at **1**. `mapper.build_document`
    emits it on every document this library writes from here on, which is why the goldens under
    `tests/golden/` and two hand-authored corpus documents
    (`tests/data/corpus/cuems-utils/{fade_showcase,unicode_showcase}.xml`) carry it now too —
    FR-010's **third** and last recorded golden event this feature sanctions (after ITEM A's cut and
    ITEM D's generator replacement).
  - **The conversion registry** (`xml/versioning.py`, `(schema_name, from_version) -> Conversion`)
    carries `script` 1→2's three transformations in **one** version step — the duration reshape
    (bare text → `<CTimecode>` wrapper), `action_type` `fade_in`/`fade_out` → `play`/`stop`
    (behaviour-preserving: `cuems-engine` already dispatches both as stubs treated exactly that
    way), and the `fade_profiles` block dropped with every drop named in the report. An
    unregistered step is a valid **identity** step (purely additive schema growth needs no
    transformation, only a version bump). The same registry backs the new
    `cuems-convert-documents` standalone entry point (`xml/convert_documents.py`,
    `[project.scripts]`), which backs up each document before rewriting and treats a backup
    failure as fatal for that document only — the load path itself writes nothing and needs no
    backup (the obligation attaches to *persisting* an upgrade, not to converting).
  - **The repair report** (`cuemsutils.errors.LoadReport`/`Outcome`/`RepairRecord`/
    `ConversionRecord`, new public symbols joining `CuemsError`/`ValidationError`/`SchemaError`/
    `IngestError`) answers which document, which fields were repaired and to what, which
    conversions ran, and whether the file on disk is now stale — from data alone, never `None` in
    place of an empty report. Every substituted value and every repairable/unrepairable decision
    traces to the descriptor (`xml.validators.repair`, built on the closed T2 rule table); zero
    hand-written per-field fallbacks or unrepairable-field lists exist. The library acquires no
    notification/messaging channel — the report is returned, not sent anywhere; forwarding it to an
    operator is 009's job, and saving a repaired document (a plain overwrite, no backup) is only
    safe because 009 must surface the report first, which is a migration-guide obligation this
    library cannot enforce at runtime.
  - **Config domains get the same T1/T2 distinction as the show path**, measured narrowly:
    `project_mappings` is the only configuration schema carrying a registered T2 rule
    (`one_custom_template_per_node`), and it is `repairable=False`, so the only observable change
    there is that its violation now raises `ValidationError` (not the generic `SchemaError` every
    other config failure still gets) — matched on the rule's own exact wording in
    `tools.ConfigBase.load_config_document`, not by exception type, because `xmlschema`'s own T1
    validation errors are *also* `ValueError` subclasses.
  - **Performance, measured and recorded rather than assumed**: show-document load 18.673 ms
    (budget ≤ 35.99 ms), suite 22.06 ms/test (budget ≤ 27.27 ms/test) — both comfortably under.
    `network_map`'s config-domain load (10.14–10.49 ms across three trials) sits **at the edge** of
    its ≤ 10.20 ms budget; recorded as exceeded-or-marginal rather than restated as passing, with
    the mechanism identified (the version probe now routes decode through a pre-parsed
    `ElementTree` instead of a bare file path) and no mitigation applied in this pass — see
    `specs/008-rebuild-extension/baseline.md`.
  - D3 stands relaxed **five times** across this feature (its second through sixth exceptions,
    tabulated in `specs/008-rebuild-extension/migration-guide.md`); three of the five invalidate
    documents already on disk and were granted *only* because ITEM E's conversion registry exists
    to carry them.
  - Nothing ships from this landing alone (D27) — feature 009 (consumer migration across
    `cuems-engine`/`cuems-editor`/`cuems-nodeconf`/`cuems-frontend`) is a hard successor, not a
    follow-up, and `specs/008-rebuild-extension/migration-guide.md` is its hand-off document.

- `007-node-model-migration` (**landed in `cuems-utils` only**, 2026-08-24 — see below): the node
  object model moves in from `cuems-nodeconf`, and `network_map.xsd`'s `<node_type>` (free text,
  `NodeType.master`/`NodeType.slave`) is renamed `<node_role>`, typed `cms:NodeRoleType`
  (`controller`/`node`/`firstrun`). `<uuid>` is typed `cms:UuidType`. `PutType` (unreferenced,
  schema item X9) is deleted from the schema, model and registry.
  - **Scope, stated because it changed mid-feature**: the plan covered three repositories
    (`cuems-utils`, `cuems-nodeconf`, `cuems-common`); only `cuems-utils`'s phases (schema, typed
    model, write path, coercion guard, non-mutating adoption selection) landed this pass.
    `cuems-nodeconf`'s source deletion and `cuems-common`'s conversion/mirror/tooling are **not
    started** — `specs/007-node-model-migration/migration-guide.md` states this per section rather
    than only here, including the release gate's actual (undelivered) enforcement status.
  - **The single-schema typing exception**: `network_map` is now the one config schema whose decode
    runs the adapter table (`SchemaRegistry.runs_adapter_table`, research R1) — `node_role` decodes
    to a `NodeRole` enum, `adopted`/`online` to `bool`, `uuid` to `Uuid`. `settings`,
    `project_mappings` and `project_settings` are untouched and still decode every scalar as text,
    proven by golden comparison (SC-010a) rather than assumed.
  - **D3 relaxed exactly once, by recorded decision**: "wire-compatible with every XML on disk; no
    `.xsd` edits" continues to bind five schemas; `network_map.xsd` is the lifted exception, settled
    by this feature's clarification session (plan.md's "Standing decisions" section).
  - `cuemsutils.tools.NodeList` is new and public — `NodeRole`, `NodeIndex`, and a re-export of
    `node` — the only public path to the node model (`cuemsutils.config` exports nothing, joining
    `cuemsutils.xml` on the internal side).
  - `CuemsNetworkMapType.save()` / `ConfigManager.save_network_map()` are `network_map`'s first
    first-party write path — it had none before. Building it surfaced a real bug in
    `documents.build_document`, never triggered because `script.xsd` was the only schema anything
    had written through: a document root bound to the object's own class (network_map's shape) must
    be filled directly, not wrapped in a synthetic child element the way a `GENERIC`-bound root
    (script's shape) needs to be.
  - Feature 004's declared break (FR-026d — `cuems-nodeconf`'s namespace-injected node handlers
    silently stop being consulted) is closed in this repository: the write path now exists for an
    injection to be provably ignored *by*, where before nothing wrote nodes either way.
  - Suite: 2393 passed / 94 skipped / 2 xfailed, 24.79 ms/test — under the ≤110%-of-006 budget.
    `network_map` load: 10.08 ms, under the ≤110% budget. See `baseline.md`.

- `006-public-object-api` (**landed** 2026-08-20): one public surface. `CuemsScript` gains
  `load`/`save`/`validate`/`from_json`/`to_json`/`to_wire`; `ConfigManager`/`ConfigBase`
  answer with objects; `cuemsutils.xml.__all__` is `[]`; the frozen legacy parser tree is
  deleted. `cuemsutils.errors` is the one new public module — a returned type can stay
  internal because the caller only inspects it, but an exception the caller cannot name is
  one it cannot catch.
  - **`to_wire()` is a direct projection, and the measurement says so**: 0.74 ms, below the
    1.10 ms tree build that is the unavoidable half of the round trip. Round-tripping would
    have cost 33.99 ms against `read()`'s 16.95 ms. The round trip is kept as the **test
    oracle** (`test_wire_oracle.py`), not as the implementation.
  - **The five enumerated behaviour changes all shipped**, each with a test that measured
    the old behaviour and now measures the new one rather than being deleted: payload
    parity, `schemaLocation` dropped from the wire dict, the derived projection replacing
    eight `__json__` methods, the relative schema location, and cue equality widening from
    `id` alone to every declared field.
  - **Load-bearing facts for the next feature.** `Cue.__hash__` is *restated* rather than
    inherited: `CuemsDict.__eq__` sets `__hash__` to `None` on any subclass that does not,
    and an unhashable cue is a `TypeError` in the engine. `config/` decoding runs **no
    adapters and no reshaping** — `adopted`/`online` stay strings and repeated content keeps
    its `{"node": {...}}` wrapper, because `cuems-engine` reads both and consumer repos are
    not edited here. `_initialized` gates value-rejecting setters in **three** classes and is
    deliberately absent from every `RUNTIME_FIELDS`.
  - **Open, carried to the PR**: the suite wall-time budget (≤10% over 44.57 s) is exceeded
    at 59.17 s — because the suite grew by 737 tests. Per test it is 11% *faster*. Recorded
    as exceeded rather than restated as passing; see `baseline.md`.
  - Migration is **feature 009's**: ten call sites across `cuems-engine` and `cuems-editor`,
    listed in `migration-guide.md`. All six retired entry points still resolve and warn in
    `v0.1.0`; they are gone in `v0.1.1`. No frontend change is required — see
    `frontend-note.md`.
  - `specs/planning/schema-evolution-convention.md` is adopted: an element added to an
    existing complex type is optional and carries a model-layer default. X13
    (`gradient_osc_port`, added as required, invalidating every older settings file) is
    recorded there as **scheduled work**; no `.xsd` is edited by this feature.

- `005-object-model-unification` (**landed** 2026-08-17): one construction path for the
  model. Coercion moved from property setters into a schema-resolved adapter table
  (`src/cuemsutils/coercion.py`, cached per class), `CuemsScript` is now a `CuemsDict`, and
  `items()`/defaulting/JSON-wrapping each collapsed to one definition on `CuemsDict`
  (`declared_fields`, `declared_defaults`, `Unset`, `from_decoded`, `_init_runtime`,
  `JSON_SELF_WRAPS`). All seven enumerated behaviour changes shipped (F4, F12/F19, F16, F17,
  F18, F20, root `items()`); **all four golden sets stayed byte-identical**. Suite 1485
  passed / 47 skipped. Coherence coverage 13/18 → **18/18**.
  - **Perf baseline feature 006 inherits**: decode **18.0 ms warm** (unchanged from pre-005's
    18.7 ms — coercion costs nothing measurable) and **49.6 ms** by the `quickstart.md`
    cold-inclusive method. The whole 36.3 → 49.6 ms delta is one fixed cost:
    `coercion._resolve` calls `all_registries()`, building the five config schemas nothing
    else on that path needs. Paid once per process; see `baseline.md`.
  - Load-bearing facts that outlived the feature: decode preserves *arrival* key order (the
    root is `xs:all`, so `items()` is declared-order but `CuemsScript.__json__` is not); the
    two legacy corpus documents stay *rejected* from the same call site
    (`VideoCueOutput.__init__` → `_classify_output_name`); and `_initialized` gates
    value-rejecting setters in **three** classes (`ActionCue`, `FadeCue`, `VideoCueOutput`),
    not one as the spec said — it must stay false during population.
  - **Open, carried to the PR**: SC-001's "zero type differences" is not met as written — 14
    of the original 44 remain, in three groups outside FR-019's enumeration (wildcard
    `None`→`"None"`, `OPAQUE_TYPES`, GENERIC-bound `output_geometry`). Built vs JSON-decoded
    *is* exact. Also open: FR-022's "confirmed harmless to the UI" for the cleared
    `initial_template` identifiers has no owner. See `migration-map.md`.
- `004-xml-serialization-core` (in progress): replacing the four duplicated XML mapping
  implementations with one schema-derived engine. Pure refactor — byte-identical output,
  deprecation shims at every old import path. See `specs/004-xml-serialization-core/`.
  Load-bearing fact: `content.iter_elements()` gives schema order, **but `xs:all` types
  (`CuemsScript`, `DmxSceneType`) are order-free and must keep today's sorted-key
  emission** or every script file's root element changes.
