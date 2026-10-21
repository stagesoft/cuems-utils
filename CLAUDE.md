# cuems-utils

Part of the **CUEMS** ecosystem — see the [`cuems-RELATIONS`](https://github.com/stagesoft/cuems-RELATIONS) repo for the system index, architecture diagram, and protocol/port map.

## Role

Shared Python library (`cuemsutils` on PyPI) used by the engine, editor, and other components. Python 3.11+, mostly stdlib (`enum`, `threading`, `time`) + `xmlschema`. Build/test with `hatch` (see below). **Commits are GPG-signed** (retry on "gpg failed to sign", never `--no-gpg-sign`).

## Submodules

- **`cues/`** — Cue object model: `Cue`, `CueList`, `CuemsScript`, `AudioCue`, `VideoCue`, `DmxCue`, `ActionCue` + output classes. Dictionary-backed objects with `@property` descriptors.
- **`xml/`** — XML serialization (`XmlReaderWriter`, `XmlBuilder`, `Parsers`), XSD schema validation, settings/config file classes. Namespace `xmlns:cms="https://stagelab.coop/cuems/"`. Also ships the node-identity schema `src/cuemsutils/xml/schemas/network_map.xsd` (mirrored to `/etc/cuems/network_map.xsd` by cuems-common) — the node's role lives in `<node_role>`, typed `cms:NodeRoleType` (`controller`/`node`/`firstrun`; renamed from the free-text `<node_type>` carrying `NodeType.master`/`NodeType.slave` in `007-node-model-migration`), plus the identity fields. The typed Python enum is `cuemsutils.tools.NodeList.NodeRole`; renaming the schema element again is an XSD migration that bumps every `cuemsutils.xml`/`cuemsutils.tools.NodeList` consumer. See the cuems-common CLAUDE.md for the node-identity field contract. That repository's phase was descoped from `007-node-model-migration`'s pass in *this* repo, but it has since landed on cuems-common's own local `007-node-model-migration` branch (four commits, 2026-08-24: schema mirror + shipped-map conversion, the conversion script wired into `postinst`, versioned package dependencies, and the documentation pass) — unmerged and unreleased, but **not** "not started", as this line said until 2026-09-03. Corrected by the 010 consumer audit's C9 (`xml-rebuild-09`, deleted 2026-10-17 by 010 T069c; in git history).
- **`tools/`** — `ConfigManager` (system config), `HubServices` (NNG bus / req-rep messaging), `SignalEngine` (systemd lifecycle), `CTimecode` (SMPTE timecode; `milliseconds_exact` is wrap-accumulated / 24h-safe).

## Build

```bash
cd <this repo> && hatch test --show   # tests
hatch build                            # build
```

Env vars: `CUEMS_LOG_LEVEL`, `CUEMS_CONF_PATH`.

## specs/planning and specs/agreements — canonical homes for non-code artifacts

Two folders, two different lifecycles — do not conflate them:

- **`specs/planning/`** — in-progress and exploratory material: planning docs, implementation
  plans, agent prompts / reusable AI prompt templates, defect records, contributor-workflow docs,
  future-development/deferred-work/roadmap notes. MUST be looked for here first; do NOT put them in
  `docs/`, the repo root, or feature spec dirs.
- **`specs/agreements/`** — settled, binding conventions and cross-repo decisions the team has
  actually agreed on (e.g. `schema-evolution-convention.md`, `xml-architecture-invariants.md` — the
  binding rules of the XML layer, compiled from the deleted `xml-rebuild/` series —, `canvas_region.md`,
  `documentation-prompt.md` — the last is the unified prompt for generating README/CHANGELOG/docs
  across CueMS / StageLab sibling repos). Unlike `specs/planning/`, these are **living, binding
  references** that current and future work is expected to actually follow and link to — keep
  their paths accurate, since active docs (including this file) point at them.

**Deletion policy, not just addition policy**: a `specs/planning/` document whose content has been
fully implemented — and whose resolution is captured elsewhere (the landed feature's own
`specs/NNN-feature/` dir, this file's "Recent Changes", or promoted into `specs/agreements/` if it
turns out to be a durable, binding convention) — MUST be **deleted**, not left behind as stale,
redundant history. Git history preserves it; a planning doc's job ends when the decision it was
tracking is made and acted on. (Example: `dmx-universe-channel-conversion-defect.md` was deleted
2026-09-03 once `specs/009-fix-dmx-channel-conversion/` landed the fix it was written to prompt.)

Feature-specific specs (`specs/NNN-feature/`) stay in their own numbered dir regardless, and — once
landed — are treated as frozen historical record: their cross-references to a `specs/planning/` or
`specs/agreements/` file as it was named/located *at the time* are not retroactively rewritten when
that file later moves, any more than a past git commit message would be.

## Field notes / gotchas

- **`script.xsd` `ActionType` has `stop_project` since 0.1.0rc17** (the engine's authored end-of-show cue, ClickUp 869fhjdq5). Project-scope: `action_target` is written empty and parses to `None` (the parsers bypass the setter; the constructor/setter still refuse `None`). **Skew rule:** every box of a cluster on ≥ rc17 before such a project is saved; ≤ rc16 rejects it at validation (editor cannot save or open, controller load fails early, a node fails its load after tearing the old project down → "Load stalled"). **Rollback hazard:** a utils downgrade strands such a project until the `stop_project` `<ActionCue>` is removed from `cue_script.xml` by hand.

- **The shared venv `/usr/lib/cuems` is one-way**: it has `include-system-site-packages = true`, so the venv sees system packages but the system `/usr/bin/python3` **cannot** import `cuemsutils`. Any tool whose entry points live in `/usr/bin` (dh-python3) must not `import cuemsutils` — reimplement with stdlib. (See the portable-.deb notes in the cuems-thermalmon CLAUDE.md.)
- Many packages populate that shared venv (`cuemsutils`, pynng, lxml, **websockets** from cuems-utils; **pythonosc** from cuems-engine; plus editor/nodeconf/midi-connector). A `.deb` must not bundle anything another package already ships, or `dpkg -i` aborts on a file-overwrite conflict. lxml is bundled at 5.3.0 (CVE-2026-41066 fixed in 6.1.0; audited across all components — zero parser call sites, reachable risk nil).

### Building the `.deb` — verify the venv interpreter before shipping

Built from **`debian/` on the working branch** — add a `debian/changelog` entry, then `dpkg-buildpackage -us -uc -b`; artifacts land in the parent dir. **Changed 2026-09-24**: packaging used to live on a separate `debian/bookworm` branch whose workflow was "merge `main` in first", and that merge stopped happening — the branch sat seven weeks and 132 commits behind at `0.1.0rc14` while the source reached rc16, so two release candidates left the tree with no changelog entry at all (both written retrospectively, marked NOT BUILT). ⚠ **Corrected 2026-10-16 (feature 016):** that note was wrong. `origin/debian/bookworm` is **still the active release line**: it cut `0.1.0rc16+1` and `0.1.0rc17` by exactly the merge-`main`-in workflow, and **no `packaging-rc14` tag exists**. So this repository has two packaging lines. The refactor's `debian/` lives on the working branch, and the release line keeps shipping `0.1.0rcN` from `debian/bookworm` until rule 4's reconciliation (`specs/planning/coordinated-release-version-bump.md`). Measure against `debian/bookworm`, never `main`. This also matches `cuems-common`, `cuems-power-bridge` and `cuems-nodeconf`, which all keep `debian/` on the working branch. See `debian/README.source` for the trixie and CI/CD intentions.

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
- **Feature 010 adds no new technology to this repository.** It is an ecosystem migration:
  seven repositories (this library, five Python consumers, one Angular UI) move onto the
  public API and release together. This repository's own share is the descriptor's public
  path, the deprecated-surface removal and the migration guide. Suite baseline re-measured
  2026-09-03: **2573 passed, 96 skipped, 2 xfailed in 53.34 s = 20.73 ms/test**.
- **Feature 011 (`011-etc-cuems-first-install`, landed 2026-09-28 on its local branch) adds no new runtime dependency.**
  It adds POSIX `sh` maintainer scripts (`debian/cuems-utils.{postinst,postrm}`), stdlib
  `tomllib`/`importlib.resources`/`fcntl` use, and `debhelper-compat (= 13)` +
  `dh-virtualenv (>= 1.2)` at build. New on-disk state: `/etc/cuems/*.xml|*.xsd` (never
  conffiles), `/usr/share/cuems/{schemas,defaults}/`, `/etc/cuems/defaults.d/*.toml` (operator
  overlay), `/var/lib/cuems-utils/init-node/last-written.json` (the tool's write record). One new
  public entry point, `cuems-init-node`. **`hatch` is not installed on the current dev box** —
  use `uvx hatch run test.py3.11:run -- -q` (the `hatch test` env lacks `hypothesis`); see
  `specs/011-etc-cuems-first-install/quickstart.md`.
- **Feature 012 (`012-uuid4-convergence`, landed on its branch 2026-09-30) adds no new runtime
  dependency.**
  It converges every node identity on uuid4: three schemas narrow (`network_map` 1→2,
  `project_mappings` 1→2, `settings` 2→3, each admitting the NOT PROVISIONED sentinel by union),
  a read-only check classifies identities across `/etc/cuems` and the library, and a cluster-wide
  re-mint rewrites them by literal 36-character token substitution — including the compound
  `<uuid>_<output>` prefixes in every script, which a structural rewrite misses while they stay
  schema-valid. **No registered conversion accompanies the version steps**: the machinery
  represents an identity step as the *absence* of a registry entry, and the repair is
  cross-document and out-of-band by design. Scripts are found by **root element, not filename**
  — `script_file_name` is an editor-internal dict key, in no document this library reads.
  Three new modules: `tools/{ids,library_reach,remint}.py`. Suite after landing:
  **3239 passed, 115 skipped, 2 xfailed, 52.90–53.57 s = 16.33–16.54 ms/test** (from 2800 /
  15.64–15.76 ms before).
- **Feature 014 (`014-xs-boolean-and-media-elements`, landed on its branch 2026-10-12) adds no new
  runtime dependency**, and it is the feature where booleans stop being this project's own
  invention. `cms:BoolType` — an `xs:string` enum of `True`/`False`, declared three times — is
  retyped to the standard **`xs:boolean`**, so element text is `true`/`false` and the JSON wire
  carries real booleans. `MediaType` gains **four** optional elements (`pixel_width`,
  `pixel_height`, `file_size`, `file_md5`), `FadeCurveType` gains `ease_in`/`ease_out`, and
  **`ConfigManager.from_json(SchemaName, payload)`** is the first public way to build a
  configuration document from JSON. All of it lands in the **existing, unreleased** `script` 1 → 2
  and `network_map` 1 → 2 steps — **no version 3**. Suite after landing: **3565 passed, 113 skipped,
  2 xfailed** (from 3432 at the branch point).
  - **`_Bool` is a *swap*, not a deletion**, and this is the load-bearing implementation fact.
    `to_wire` goes, a lowercase `to_lexical` map arrives, and `decode`'s literal table widens to the
    four lexical forms XSD actually permits (`true`/`false`/`1`/`0`). It cannot simply be deleted
    because **`Mapper._lexical` is the only producer of element text** on a stdlib-`ElementTree`
    write path — `ElementTree` never encodes a value, so the inherited `str(obj)` would write
    `"True"` and `save()` (which validates before writing) would fail on every document. Noted in
    `xml/adapters.py` beside the class.
  - **`doc_version="2"` is briefly ambiguous, and the version marker cannot resolve it** — it means
    both the pre- and post-boolean shape, because the rewrite joined a version step already in
    flight. That is feature 012's situation verbatim and the same answer applies: the step is
    represented by the *absence* of a registry entry and the repair is out-of-band by design. The
    trade was measured, not assumed: **51 documents convert free, nine need hands**, and six of the
    nine were goldens already due for re-cutting. The ninth is in a sibling
    (`cuems-engine` `complex_test_v2/script.xml`) and was closed by the T028 gate, not by the task
    that claimed it. The window shuts when the coordinated tag ships, since nothing outside these
    checkouts has ever been written at version 2.
  - **`file_size` is unbounded by type, and `0` is invalid by design.** 100 GiB is
    107,374,182,400 bytes, which overflows a 32-bit int; `xs:positiveInteger` has no upper bound and
    decodes to an arbitrary-precision `int` (2⁶³ verified), so the requirement is met by the type
    alone. Absent means *unknown* and a zero-byte file is not playable media. **`file_md5` is
    `cms:Md5Type`, 32 lowercase hex**, matching `UuidType` facet for facet — uppercase **raises**
    rather than being normalised, which diverges from the rc15 line deliberately and is why
    `cuems-editor` must `.lower()` a client digest before assigning (a no-op against rc15).
  - **The `get_schema` mitigation feature 013 identified and deliberately left is applied**, and it
    is the largest single result: the `schema` setter built a fresh `XMLSchema11` per instance, so
    the configuration path paid XSD *compilation* per load while `xml/schema.py`'s cached
    `get_schema` sat unused by that one call site. `project_mappings` **18.292 → 3.690 ms (−80%)**,
    `settings` **14.702 → 1.646 ms (−89%)**, suite **57.66 → 24.3 s (−58%)**. ⚠ It does **not** touch
    the mechanism 013 named as dominant (`elementpath` rebuilding a node tree per `xs:alternative`
    evaluation), and `script` is unmoved — `CuemsScript.load` does not go through that setter.
  - **The budget shape is the finding, not the overruns.** Two of three budgets are recorded as
    exceeded by 0.01–8.6% — and the same three paths measured on the pre-edit tree in the same
    session are exceeded by the same margin, so there is nothing measured to mitigate. Run-to-run
    spread on one unchanged tree is **±4–8%**, so **a 110%-of-baseline budget is below this
    instrument's resolution**. Anything tighter measures the afternoon, not the code
    (`specs/014-xs-boolean-and-media-elements/baseline.md` §6.1).
- **Feature 015 (`015-consumer-gate-closure`, specified 2026-10-13, implemented on its branch 2026-10-14) adds no new technology** — no
  runtime dependency, no new module in `src/`, no schema version step. (One tooling change: `ruff>=0.17.0,<0.18` and `mypy>=2.4.0,<3`, because their finding counts are now gates.) It closes the five gates of
  the coordinated tag plus the straggler sweep; `specs/015-consumer-gate-closure/research.md` holds
  the twelve measured findings.
  - **The box was migrated 2026-10-13, and line 88's claim is now substantively true.** Anaconda is
    **removed**, pyenv is installed with a real **3.11.9**, and the toolchain (`uv`, `hatch`,
    `specify`) lives under `~/.local`. One qualification is load-bearing and must travel with it:
    **a pyenv build of this interpreter MUST carry `--enable-optimizations --with-lto`** (and
    `CC=gcc-12`, since GCC 14 will not build CPython 3.11). Measured 2026-10-13: without those
    flags pyenv's build is **32–72% slower** than the uv-managed python-build-standalone build that
    `hatch` resolves, and the show-document load reads **23.4 ms against a 16.5 ms budget — 42% over
    on unchanged code**. With them, the two builds agree to within **0–2%**. Record *which build* a
    figure came from, never just "3.11.9".
  - **Features 011–014's performance figures were all taken on conda-built CPython 3.11.2** and are
    not directly comparable with anything measured after the migration. They remain internally
    consistent and are not re-measured.
  - **The show-document load straddles its 16.5 ms budget**, measured over **16 samples in three
    windows**: band **16.465–17.750 ms**, median 16.864, **14 of 16 over**. So the assertion is
    *flaky* on an unchanged tree rather than failing — and feature 015 adopts 012's R14 precedent
    (band comparison, not a straddled line) rather than raising the budget a fourth time. Against
    013's own 14.07–14.96 ms the drift is **+13% to +19%**, and it survived the interpreter
    migration, so it is real.
  - **Budget tolerance is 115%**, corroborating 014's ±4–8%: the pooled spread over those 16 samples
    is **7.8%** (individual windows 2.9%, 7.7%, 4.8%). ⚠ **The sampling lesson, which cost feature
    015 three wrong headline figures**: 3 samples under one sustained contention gave "32.8–33.5 ms,
    a 2× regression"; 5 samples in one quiet window gave "exceeded by 2.0–4.9%" and a 110% tolerance;
    only 16 samples across three windows gave the stable answer. **Consistency within a window is
    not evidence — it is what makes a bad measurement persuasive.**
- **Feature 016 (`016-coordinated-minor-bump`, planned 2026-10-15, implemented 2026-10-16) adds no new technology.** It is
  the first feature allowed to **commit in sibling repositories** (on their `feat/xml-refactor`,
  never pushed, no tag moved). It bumps all seven repositories to their next stable minor and writes
  the candidate-tag messages to `../.xml-refactor-tag-messages/`. Sibling suites run on **pyenv
  3.11.9** from a per-repository `.venv` (excluded through `.git/info/exclude`). This repository
  keeps its hatch matrix. Builds run in an `mmdebstrap` bookworm chroot (`equivs` and `debhelper`
  are now on the host).
- **Feature 017 (`017-release-line-reconciliation`, planned 2026-10-21) adds no new runtime
  dependency.** It merges `origin/debian/bookworm` (`0.1.0rc17`) and `origin/main` into the
  refactor, under the unchanged `0.1.1`. One **test-only** addition: `pyyaml` in the hatch `test`
  environment, for the static check of `.github/workflows/tests.yml`. PyPI's 0.1.0 line, measured
  through its JSON API: rc1–rc4, rc7, rc8, rc10, rc11, rc14–rc16. **rc5, rc6, rc9, rc12, rc13 and
  rc17 are not on PyPI** (rc9, rc12 and rc17 are Debian-only; rc5, rc6 and rc13 were never
  published anywhere). `pip index` omits yanked releases, so query the JSON API.

## Recent Changes

- **`016-coordinated-minor-bump` IMPLEMENTED and MERGED** (2026-10-15/16; merged into
  `feat/xml-refactor` and pushed with the six siblings; **no tag created or moved by the feature**, and
  the re-cut is left to the maintainer). The first feature to **commit in sibling repositories**, each
  on its own `feat/xml-refactor`. The coordinated set:

  | Repo | Version | Commit |
  |---|---|---|
  | cuems-utils | **0.1.1** | bump `8f6eede`, record `67f18f7`, merge `8a4bc42` |
  | cuems-common | 1.3.1-1 | `fb450b5` |
  | cuems-nodeconf | 0.1.1-1 | `334db12` |
  | cuems-power-bridge | **0.4.0-1** | `666cb25` (re-signed from `f0da390`, same tree) |
  | cuems-engine | 0.1.1-1 | `e994a5e` |
  | cuems-editor | 0.1.1-1 | `a2431f0` |
  | cuems-frontend | **0.2.0** | `9e91464` |

  - **`REMOVAL_RELEASE` is `v0.1.2`**, and every consumer bounds this library `>= 0.1.1`, `<< 0.1.2~`.
    The removal plan is now `specs/planning/deprecated-surface-removal-v0-1-2.md`. All 25 relation
    sites hold: `specs/016-coordinated-minor-bump/tools/verdicts.sh` is **121/121**, and it failed
    70/119 before.
  - **The parallel release lines kept taking our numbers *during* the feature**, twice in one day:
    `cuems-power-bridge` released `0.3.1-2`, `0.3.2-1` and `0.3.2-2`, and `cuems-frontend`'s `dev`
    tagged `v0.1.0-rc1`. Hence `0.4.0-1` and `0.2.0`, recorded exceptions to "the last component
    advances" (research R2a, R2b). ⚠ **Both teams must be told the refactor's numbers.** Each
    renumbering amended the `cuems-utils` bump (`055ec52` → `67df8bc` → `8f6eede`) and re-ran every
    dependent build, suite and demo (FR-021).
  - **A fifth defeated relation, in maintainer scripts**: `cuems-common`'s `rm_conffile`
    prior-version `1.3.0-23~` would have skipped the network-map handover and left the retired
    `99-cuems` sudo rules active on upgrade from the released `1.3.0-23`…`-25`. Now `1.3.1~`, proven
    by its demo (G2–G4) and by this repository's chroot custody test from a `1.3.0-25` stub.
  - `cuems-engine` declares `libmtcmaster (>= 0.0.2-0)` (never declared before). Its `poetry.lock` is
    **not** relocked (`0.1.1` unresolvable until published); `tests/test_lock_is_current.py` is a
    strict xfail that turns red the day it is.
  - **Evidence**: every package built in a bookworm chroot (`tools/bookworm-build.sh`); every suite
    two-armed and interleaved ×3, with no new failure and no library effect; the `cuems-common`
    (13/13) and `cuems-nodeconf` (9/9) install demonstrations, against the released field baseline.
  - **Rule 4 is NOT met.** No release line was merged: `cuems-utils` 77, `cuems-common` 22,
    `cuems-engine` 119, `cuems-editor` 43, `cuems-power-bridge` 59 commits behind, and
    `cuems-frontend` 31 behind its own `dev` (which tagged `v0.1.0-rc1`), including `stop_project`
    on every side and `CACHEDIR.TAG`. **Do not publish** until they are reconciled and the
    relations re-verified. Every changelog and tag message says so.
  - **Found, out of scope, recorded**:
    - `cuems-engine` tracks `.venv/pyvenv.cfg` in git;
    - `cuems-nodeconf`'s demo rejects a `git worktree` (`[ -d .git ]`) and labels a ref with the tag
      object, not the commit;
    - 011's `test_fresh_install_loads_and_is_unique` fails on its own since 012 (the XSDs carry the
      sentinel), which is pre-existing;
    - mypy measures 283 on this box against 015's 72, unchanged by 016.
  - **Re-cut and pushed 2026-10-16** by the maintainer (`../.xml-refactor-tag-messages/recut-and-push.sh`).
    Every tag sits on its repository's `feat/xml-refactor` head, `cuems-utils`' at `4b336cd`.
    **Still owed by the maintainer**:
    tell the power-bridge and frontend maintainers the refactor's numbers; rule 4; §11.1 validation
    on the re-cut tags (then again after rule 4); the engine relock; publication.
    `specs/planning/coordinated-release-version-bump.md` holds this list.

- **015's consumer halves, all closed** (2026-10-15). Every row of
  `specs/015-consumer-gate-closure/consumers_works.md` is `verified done`, measured at each sibling's
  commit; that file's 2026-10-15 section has the table. The siblings' commits are GPG-signed and were
  **local and unpushed** when this was written. No tag was cut or moved; that stays maintainer-only.
  - **Library side, one commit (`0b3690e`): seeding rule 0.** `script.xsd` gains the first `default=`
    attributes in any schema (`output_vol`/`channel_vol` 80, `x_scale`/`y_scale` 1), and the
    descriptor seeds a field from its own declaration's XSD default, after the model default and
    before the facet rules. It is a **seed, never a `FieldDescriptor.default`**, so repairability and
    the read path are unchanged: the library refuses an omitted or empty element with and without the
    attribute (measured). Read **per declaration**, never per name (`channel` is an integer in one
    type and complex in another). This let `cuems-frontend` delete its starting-values table with no
    value authored there.
  - **Moving literal defaults into the schemas in general is planned, not done**:
    `specs/planning/xsd-literal-defaults.md`. 22 of the 52 default declarations can move. Its cost is
    semantic (an XSD element default means "when present and empty", never "when absent"), not
    performance: cold start, construction and show-document decode were measured unchanged.
  - **Siblings:**
    - `cuems-editor` `6de91fb` (G1), `35a79d1` (G2), `fc025a7` (G3 cue + row 5), `2360936` (S1),
      `e5e6ac1` (tag readiness **READY**). Suite 271 passed, 3 skipped, no xfail.
    - `cuems-frontend` `6b69b41`: the transform is deleted, and the fixtures were re-recorded with its
      own capture script beside the old ones. 288 specs pass.
    - `cuems-nodeconf`'s `node_set` (`3d3601d`) was verified with a control arm, not just a pass.
  - ⚠ **`to_wire('project_settings')` keys items by class, `{"SettingType": …}`.** The editor's G2
    test had predicted bare items. The shape is the shared projection by contract and round-trips,
    so it stays. But it is a class name on the wire, and changing it is a library-wide decision.
  - ⚠ **A client building a media cue from the descriptor must drop `Media`'s four media values**:
    they are seeded with placeholders and are the editor's to write from the library row.
  - **Running a sibling's suite on this box**: `cuems-editor` has no hatch environment here. This
    repository's `test.py3.11` interpreter has its runtime dependencies (`peewee`, `websockets`) and
    resolves `cuemsutils` to this checkout. `cuems-nodeconf`'s own suite needs `zeroconf`, which is not
    installed; its `node_set` is exercised through the editor's G4 test instead. `cuems-frontend`:
    `CHROME_BIN=/usr/bin/google-chrome npm run test:ci`.

- **Descriptor instance cache** (2026-10-14, `bed5d53`, directly on `feat/xml-refactor`, no feature
  dir; the plan `specs/planning/descriptor-instance-cache.md` is deleted by this entry's commit and
  lives in git history). It **clears 015's recorded descriptor-derivation exception**.
  - **Mechanism, measured.** G3 rebuilt every instance on every call, and
    `get_schema_descriptor` had no cache (015's baseline calling it "an `lru_cache`d path" was
    wrong; only `derive` is cached). There was no single hotspot: each type re-expanded its whole
    subtree (~105 builds for 29 types), and each node was walked twice (build, then
    `encode_wire`), at ~7 µs per node.
  - **Fix.** `SchemaDescriptor.describe()` caches per `TypeKey` and returns
    `replace(cached, instance=_copy_instance(...))`. The structural copy is complete because every
    leaf is exactly `str`/`int`/`float`/`bool`/`None`, which `_assert_scalar_leaves` enforces on a
    cache miss (it raises naming key and path). The cache has no environment input:
    `get_schema` reads the package's own `schemas/`, never `CUEMS_CONF_PATH`. No lock, by design;
    the reason is in the docstring.
  - **Result.** 16 interleaved A/B samples per arm, three windows, hatch interpreter: `script` warm
    **2.850 → 0.165 ms (17×)**, 7.4× under the ≤ 1.22 ms budget and faster than pre-015's 1.052.
    Other schemas 7–17×. First call unchanged (~260 ms, schema compilation). Suite ms/test
    unchanged. Instances byte-identical (sha256 over all six schemas), no golden moved.
  - **Reusable probe**: `python -m tests.support.perf_descriptor --arm A=<src> --arm B=<src>`
    alternates arms in fresh processes and counts `_instance_for` calls per warm call, which must
    be 0. It reproduces 015's 1.06 → 2.83 ms. 015's "slow state", where every path reads ~2×, is
    the same operation measured on a slower box. GC and logging were ruled out; CPU frequency
    scaling (governor `powersave`) is the **unproven** hypothesis. Check `scaling_cur_freq`
    before trusting an absolute figure.
  - **Guard lesson.** A mutation-isolation test must also assert that its marker never appears
    in a fresh result. A before/after comparison alone passed against a deliberately broken
    cache, because an earlier test had already vandalised the shared objects.
  - ⚠ **Open, needs an owner — a pre-existing flake, not caused by this change.**
    `test_descriptor_laziness.py::test_no_individual_schema_regresses_where_it_is_measurable[project_mappings]`
    compares two ~2 ms first-call timings within 110%, just above its own 1 ms floor. It failed in
    **2 of 12 runs on `9d2f337` without the cache** and 1 of 12 with it. The likely remedy is that
    file's own precedent: raise the floor or compare a band. One more suite run reported two
    failures that 8 reruns did not reproduce; probably two cases of this flake, but unconfirmed.
  - `cuems-editor` needs no change. Its JSON round trip of instances is no longer needed for
    isolation (`CHANGELOG.md` 0.1.1).

- **Foreign-controller scoping** (2026-10-14, directly on `feat/xml-refactor`, no feature dir; the
  request is `../cuems-nodeconf/specs/upstream-reports/foreign-controller-scoping.md`). Several
  clusters on one LAN made `merge` + `set_controller_always_adopted` adopt *other* clusters'
  controllers. `refresh(discovered, path, *, cluster=None)` now filters discovered foreign
  controllers and **removes** saved ones (deletes the key; never marks it offline). The caller
  computes `cluster` with the new `NodeIndex.cluster_controllers(own_uuid, own_role)` **before**
  the pass. `foreign_controllers` is for logging, and `drop_foreign_controllers` /
  `is_foreign_controller` are the primitives. Without `cluster` the behaviour is byte-for-byte the
  old one (the characterization suite is unedited). Only `cuems-nodeconf` passes it, and it must
  ship inside `0.1.1` (rule 4 of the bump document). Known limitation, kept on purpose: a fresh
  node that hears two controllers accepts both. `api/public_api.json` was re-hashed once to add
  four `NodeIndex` entries.

- **`015-consumer-gate-closure` IMPLEMENTED** on its branch 2026-10-14 (all tasks ticked; **nothing
  committed from the final session — the working tree holds Phase 10–11**). The five gates
  (G1 `must_exist`, G2 public `project_settings`, G3 wire-shaped saveable descriptor instances, G4
  `NodeIndex.set_alias`, G5 the settings version step vs the reshape) and S1–S4 landed; the coordinated
  `xml-refactor-merge-candidate` tag now waits on the **consumers' halves** (`cuems-editor` G1/G2/S1 and
  the G3 cue construction, `cuems-nodeconf`'s `node_set`, `cuems-frontend`'s `toWireShape` deletion) —
  `specs/015-consumer-gate-closure/consumers_works.md`, re-verified 2026-10-14. **All closed
  2026-10-15**: see "015's consumer halves" above.
  - **S3: the writer indents, through ONE serializer.** `documents.serialize_tree` is the only place
    an `ElementTree` is written (encoding, declaration, `cms` prefix, `ET.indent`); `write_tree`,
    `cuems-init-node`'s `_serialize` (the `/etc/cuems` documents) and `XmlReaderWriter.write` all call it,
    and `test_only_documents_serializes_an_element_tree` stops a fourth writer. Six XML goldens and
    two API goldens were re-cut as **one** event (`migration-guide.md` §7); `config_accessors.json` was
    edited **surgically**, not re-cut, because it is the pre-006 baseline other tests compare *against*,
    and `outcomes.json` must never be a `--force` target.
  - **Tag values: record the COMMIT, not the tag object.** `git rev-parse <tag>` prints an annotated tag's
    object id; `<tag>^{commit}` is the commit. 015's first draft thought three candidate values had moved
    — only `cuems-nodeconf` had (`b305c1c` → `5be6cf0`). `tests/support/sibling_tags.py` is the shared
    resolver: cross-repository claims about *what the coordinated release contains* are asserted at the
    tag, and *provenance pins* are dated, not asserted. `test_no_version_bump` was a third offender.
  - **Measured exceptions, recorded as exceeded** (`baseline.md`, 2026-10-14, hatch interpreter,
    contended box — a Chrome renderer held a core, load 2–3, so verdicts rest on **interleaved A/B**,
    not absolutes): descriptor derivation **1.04 → 2.83 ms (+170%) vs ≤ 1.22** — ~80% is G3's eager
    `_instance_for`, accepted and carried; suite **+4.3% per test** relative. Writer did not move the
    reader (load +0.5%). The show-document load is now compared against its **band**
    (16.465–17.750 ms), owned by `specs/planning/show-document-load-drift.md`.
  - **The quality ratchet descended**: ruff **606 → 0**, mypy **80 → 72**, both tools now bounded;
    goldens byte-identical across the sweep. Judgement calls worth keeping: `E721` → `type(x) is Y`
    never `isinstance`; the 166 `W293` left after the safe fixes were all inside docstrings (checked by
    AST) before applying the unsafe fix.
  - **Sibling two-arm result**: `cuems-editor` 1 real regression (an indentation-sensitive assertion,
    fixed in its checkout, uncommitted) + 3 intended `XPASS(strict)` flips; `cuems-nodeconf` 0;
    `cuems-power-bridge` 0 of 57 pre-existing; `cuems-engine` (read on `feat/xml-refactor`; an earlier read on `format/module_extraction` was the wrong branch) 28 failures identical in both arms, but **against a mock `pyossia`** — needs a host with the real package. SC-012's
    "four flips on landing" is **three** — the fourth (G3 cue) is a test-construction problem in the editor.
  - Planning folder swept: nine documents deleted (T115), `refactor-sequencing` re-homed to
    `adoption-liveness-ui-tier.md`, 010's eleven prompts **deletable but kept** until 010 closes.
  - **Suite**: 3707 passed, 115 skipped, 2 xfailed; remint timing tests
    (`test_remint_*`, `test_estimate_tolerance`) are flaky under box contention, not defects.

- **`014-xs-boolean-and-media-elements` LANDED** on its own branch 2026-10-12 (scaffolded 2026-10-03
  off `feat/xml-refactor` at `84705b9`); merges into `feat/xml-refactor`, and nothing ships until the
  coordinated `xml-refactor-merge-candidate` tag after 011–015. **46 of 46 tasks** — **T039 closed
  2026-10-12 by `cuems-editor` 002**, the last one: its two outward obligations (`cuems-editor`'s
  `.lower()`, the unenforceable AudioCue pixel rule) are pinned by **six** red tests in that
  repository's `tests/test_media_values.py`, passing from `1502d64`, plus a **seventh** that greps
  its own source so the dict idiom cannot return. Evidence:
  `../cuems-editor/specs/002-config-round-trip/evidence/t039-absorbed.md`. Reduced SDD path — `plan.md` (twelve settled
  decisions, relocated from `specs/planning/`), `baseline.md`, `tasks.md` and the rule-4 release
  note; **no `spec.md` story pass and no `research.md`**, recorded as a tracked exception in that
  plan's §11.1 rather than quietly skipped. Four changes in one unreleased `script`/`network_map`
  1 → 2 step: `cms:BoolType` → **`xs:boolean`**, a **four**-element media block, `main`'s
  `ease_in`/`ease_out`, and `ConfigManager.from_json`.
  - **All five sibling gates are green, and the number that matters is the ratio**: **eight test
    failures across five repositories are attributable to 014, against 183 that were already
    broken.** Without the control arm, `cuems-engine` and `cuems-power-bridge` would between them
    have reported **151 failures against this feature, every one someone else's**. The
    cross-cutting finding is that **013's device migration was never completed in three of the five
    siblings**, so 014's gates paid that debt (11 `settings.xml` hand-rewritten, five documents
    reshaped in `cuems-engine`) — **015 must close its own sibling fixtures in its own feature**, or
    the next gate discovers them with its own signal buried underneath.
  - **`cuems-editor`'s T059 did *not* close by re-run**, which this feature's own T023 had predicted
    it would; the correction is in `migration-guide.md` §3.1. It closed in that repository the same
    session (`365d57f`, `d6fa83b`), so **UR-5 is resolved** and its `xfail(strict=True)` is gone —
    161 passed / 2 skipped. One new report came back from the same work: **`cuems-editor` UR-6**,
    `conf_path`/`project_path` refuse the file a first save would create.
  - **`cuems-frontend`'s hard coupling is discharged, and it landed *ahead* of this feature.**
    `plan.md` §6.2 called `sequence.component.ts:997` mutually hard-coupled — *"014 cannot ship
    without that one line"*. Measured 2026-10-12: that write is gone, `:1082` sends the native
    boolean, landed as that repository's T046 (`ff9dc3b`, 2026-10-06). Every remaining
    string-boolean there is a **read or a type union, never a write** — write native, read either —
    so the two repositories can now land in either order. ⚠ Do not re-cite `:997`; the file moved
    ~85 lines. That repository's 001 is also landed at `f5453a3` and **carries an
    `xml-refactor-merge-candidate` tag**, which this file recorded as absent until now.
  - **A process defect in the gate prompt itself, found by being used.** Its arm-A instruction had
    every parallel session point the *shared* `../cuems-utils` checkout at the branch point — a race
    by construction, since the gates are marked `[P]`. Caught by `cuems-nodeconf`'s session before
    any number was trusted, corrected to a **per-session `git worktree`**, and confirmed working
    mid-flight by the next gate. **The lesson that outlives it**: a prompt that tells N parallel
    sessions to mutate one shared resource is a defect in the prompt, not in the sessions.
  - **The `get_schema` mitigation feature 013 identified and deliberately left is applied**, and it
    is the largest single result here: the `schema` setter built a fresh `XMLSchema11` per
    instance, so the configuration path paid XSD *compilation* per load while `xml/schema.py`'s
    cached `get_schema` sat unused by that one call site. Measured, same session:
    `project_mappings` **18.292 → 3.690 ms (−80%)**, `settings` **14.702 → 1.646 ms (−89%)**, and
    the **suite 57.66 → 24.3 s (−58%)** over three runs. `script` is unmoved — `CuemsScript.load`
    does not go through that setter. 013's SC-PERF-001 miss is not merely recovered: the config
    load is now about a quarter of the *pre-013* 15.153 ms figure. ⚠ It does **not** touch the
    mechanism 013 named as dominant (`elementpath` rebuilding a node tree per `xs:alternative`
    evaluation); on this evidence the "smaller, one-off part" was the larger one for that path,
    because it was being paid per call.
  - **`file_size` must hold a file past 100 GB** — 100 GiB is 107,374,182,400 bytes, which
    overflows a 32-bit int. `xs:positiveInteger` is unbounded and decodes to an
    arbitrary-precision `int` (2⁶³ verified), so the requirement is met by the type alone. `0` is
    **invalid by design** for all three integers: absent means unknown, and a zero-byte file is not
    playable media. `file_md5` is `cms:Md5Type`, 32 **lowercase** hex, matching `UuidType`'s
    existing pattern — uppercase refused for the same reason `_Bool` refuses `"true"`.
  - **Renamed 2026-10-06 (plan.md decision 13, §10.5): `file_hash` → `file_md5`,
    `Md5HashType` → `Md5Type`.** 014 chose the original names when its input document specified
    only three elements and the fourth was its own; the successor document
    (`specs/planning/stored-media-values-preimplementation.md` *(deleted 2026-10-14, feature 015; in git history)*, D18) ships four and names the
    fourth, and **rc15 has already shipped that name** — into rc15 plus back-patches to rc14 and
    `pre_release_1`. An element name is an **instance-document** name, so matching it is an
    obligation: two spellings would mean an rc15-written project carrying a `Media` child version 2
    does not declare, refused by T1 at the point where the reason reads worst. The type half is
    cosmetic (no document names a type) and was done so the two lines' schemas diff as one type.
    ⚠ `\b` in `sed` does **not** match `get_file_hash`/`set_file_hash` — `_` is a word character —
    so grep for the old name after any rename here.
  - **Two divergences from the rc15 line survive the rename, both deliberate, and one is somebody
    else's one-liner.** (a) **The case rule**: rc15's setter lowercases an uppercase digest, this
    one **raises**. The strict form is the consistent one — `Uuid` raises on an uppercase uuid too
    (measured), and `Md5Type` matches `UuidType` facet for facet — so **`cuems-editor` must
    `.lower()` a client md5 before assigning**, which is a no-op against rc15's setter and should
    land before the merge. (b) **`pixel_width`/`pixel_height` are VideoCue-only by convention and
    no schema here can enforce it**: `MediaType` is shared, so only the editor's strip keeps a
    pixel size off an AudioCue. Both are pinned, the second as an explicit negative-knowledge test.
  - **Two obligations that document places on this package were already met**, verified rather than
    assumed: *"never coerce `file_md5`"* — an all-digit md5 loads as a `str`, because the adapter
    table binds **types** and `Md5Type` restricts `xs:string`, so `STRING_TYPED_KEYS`' defect class
    cannot recur; and *"keep the old file's mode"* — `write_tree` already `chmod`s the temporary to
    the target's mode before `os.replace` (`xml/documents.py:273-333`, **010 T080**).
  - Two commits landed on `feat/xml-refactor` before the branch was cut and are **preconditions,
    not this feature's diff**: `be3e86e` (strict `_Bool.decode`) and `84705b9` (`CTimecode`'s
    notice). Marked settled as S1/S2 in `tasks.md`.
- **Feature numbering, renumbered twice — read this before any feature number in `specs/`.**
  The `xs:boolean` + media-elements gate took the **014** slot on 2026-10-02, moving
  `hardware_outputs becomes real` to **015**. On **2026-10-12** the maintainer moved it again:
  `hardware_outputs` leaves the numbered sequence entirely for
  `specs/planning/hardware-outputs-capability-layer.md` — **deferred, unnumbered, and re-owned**
  — and the **015 slot now holds the consumer-gate closure**,
  `specs/planning/upcoming-feature-requirements-2026-10-02.md` *(deleted 2026-10-14, feature 015; in git history)* (its G1–G5 plus the §9 straggler
  sweep). The coordinated `xml-refactor-merge-candidate` tag still comes after **011–015**; the
  capability layer is **outside** it and may ride a later one.
  - **`cuems-hardware-discovery` is not a repository and will not be one.** The probe role, the
    `display.conf` transcription and any related machinery are **`cuems-nodeconf`'s**. The seam is
    **`cuems-common` generates `display.conf`, `cuems-nodeconf` probes and transcribes,
    `cuems-utils` describes and persists** — and the real gate was nodeconf accepting that. **It
    has, as of 2026-10-13** (`2bbec36`, verified 2026-10-14): `../cuems-nodeconf/specs/planning/13-atomization-remeasured.md`
    rows 13 (hardware probe → `hardware_outputs.xml`, with `CuemsHwDiscovery.py` on its
    `origin/main` as prior art) and 14 (`display.conf` transcription) are assigned to that
    repository. One condition remains open there: `cuems-common` must agree to a second reader of
    `display.conf`. (Measured 2026-10-12, its `specs/` had zero mentions of any of this.)
  - **The renumbering left eight code and test sites naming a feature number for that work**, one
    of them a refusal message a consumer reads at runtime (`ConfigManager`'s `hardware_outputs is
    reserved…until feature 015`). All are re-pointed. ⚠ The lesson: **a comment that names a
    feature number for work in another document ages badly** — numbers get reassigned, comments do
    not get swept. Name the document, or name the behaviour. Landed specs keep their stale numbers
    by policy; code does not get that exemption.
  **Features 012 and 013 are landed and say "feature 014" for what is now 015.** They are frozen
  record and are *not* retroactively rewritten (see this file's policy on landed specs), so every
  such reference in `specs/012-uuid4-convergence/` and `specs/013-device-class-reshape/` — the
  `hardware_outputs` structure pass, `UuidType`'s FR-020b hand-off, the `xs:anyType`/no-instance
  notes — means **015**. The step sequence and the per-feature briefs are current in
  `specs/planning/etc-cuems-first-install-execution.md` §5–§6.

- **`cuems-editor` migrated, and 010 moved with it** (2026-10-02, reviewed from this repository).
  `cuems-editor`'s feature `001-cuems-utils-migration` landed on its `feat/xml-refactor` at
  `bf57d95` — **62 of 63 tasks**, suite **154 passed / 2 skipped / 1 xfailed**, where its branch
  point's websocket server did not import at all (`cuemsutils.create_script`, retired by 008).
  **Five of six consumer flows have now landed; only `cuems-frontend` has not started.** Nine of
  010's gate tasks closed here — T020, T021, T026, T027, T027a, T027b, T037b, T038, T049 (010 at
  **68/118**), recorded in that feature's `migration-guide.md` §4d, `baseline.md` and
  `import-census.md`.
  - **The deprecated-surface census over shipped source is zero across all six consumers.** The
    five module deletions, the seven aliases and the **`v0.1.1` version move** are no longer
    held by any consumer's *source*. **Re-scoped 2026-10-03**: they are no longer feature 010's at
    all — T050–T061 migrated to `specs/planning/deprecated-surface-removal-v0-1-2.md` as R1–R12,
    because this arc lands at `0.1.0rc16` and the coordinated tag cuts no stable release. Measured
    with `dpkg`, the siblings' `<< 0.1.1~` bound admits `0.1.0rc17`, so **deleting the surface
    without the version move defeats the gate** — the two are one step, at `v0.1.1`, which is
    unplanned. 010 keeps the census, the vocabulary count, the corrections and the guide.
  - **Closing the last package edge created a new precondition for the version move.** Five
    siblings now carry `cuems-utils (<< 0.1.1~)`, which `dpkg` refuses `0.1.1` against — correctly,
    since `0.1.1` is the release that deletes the surface. **The version move and a re-bound of five
    sibling packages are one atomic step, not two**, and no task in 010 carried that; it is now
    R11 and §3 of the migrated document.
  - **Four payload deltas, not two.** 010's FR-010/FR-011/SC-004 say two; (c) is 013's cue key and
    (d) is `to_wire()` projecting a model default for an optional element the document omitted —
    ruled correct (reported as `cuems-editor` UR-3, **withdrawn**) and a **general** property of the
    projection, not a fact about `opacity`.
  - **013's own migration guide prescribed a fix that would have been a regression**, and the
    consumer declined it: `if 'Cue' in item: cue_data = item['Cue']` walks the wire dict to reach an
    object-level result (010 FR-013b). The landed form matches on cue identity, with a bare
    `MediaCue` in the `isinstance` tuple because an unknown `class` decodes to it. 013's guide is
    corrected in place, and the red test that proves it is the consumer's: porting the old walk
    against a 013-shape document nulls a *valid* `action_target`, after which this library refuses
    the save.
  - **FR-044 was superseded by a better answer than the one it asked for.** `repair_durations.py`
    does not fold its rewriting pass into `cuems-convert-documents`; it writes **no script under
    any flag**, repairing `project-manager.db` and *listing* projects as `NEEDS_SAVE`. So "exactly
    one document rewriter in the ecosystem" is the wrong count — this library ships two by design
    (`cuems-convert-documents`, `cuems-reshape-devices`, in that order) plus `cuems-init-node` and
    `--remint`. What the requirement protects is that **no consumer** is one of them. 010's **T028
    is deliberately left open**: its premise moved.
  - **Two open asks on this library**, both gaps in the public surface rather than defects, and both
    for the next feature's public-surface pass:
    `cuems-editor` **UR-5** — no public way to build a configuration document from JSON, which
    holds that repository's T059 open (its test is `xfail(strict=True)` and turns XPASS the day the
    call lands); and `cuems-editor` **UR-4** — a duplicate node identity carries no structured
    identity, so a consumer is parsing `check_node_identities_unique`'s **prose** with an anchored
    regex. Collected with the release obligation in
    `specs/planning/upcoming-feature-requirements-2026-10-02.md` *(deleted 2026-10-14, feature 015; in git history)*.

- `013-device-class-reshape` (**landed on its local branch** 2026-10-01; merges into
  `feat/xml-refactor`; nothing ships until the coordinated `xml-refactor-merge-candidate` tag
  after 011–015): an element named after a device class becomes **one element carrying a
  `class` attribute**, so a new class costs nothing unless it needs special fields.
  - **Four axes, one shape.** `<audio>`/`<video>`/`<dmx>` under a mappings node become
    `<device class="…">` inside `<devices>`; the six root `default_*` elements become
    `<default class="…" direction="…">` inside `<defaults>`;
    `<videoplayer>`/`<audioplayer>`/`<dmxplayer>` become `<player class="…">` inside
    `<players>`; `<AudioCue>`/`<VideoCue>`/`<DmxCue>` and the three `*CueOutput` elements
    become `<Cue class="…">` and `<CueOutput class="…">`; and `hardware_outputs`' two flat
    lists become `<output_groups>` of `<outputs class="…">`.
  - **The container elements exist because a type may not mix single children with a repeated
    one** (research R2): `converter.py` silently drops the single ones, so a repeated `device`
    beside `uuid` and `mac` would lose both. That is why `devices`, `defaults` and `players`
    are there and why axis D needs **no** container — both cue choices were already
    repeated-only. `audiomixer` stays exactly where it is: it has no device class, and
    folding it in would invent one (FR-040a).
  - **The type is selected by `xs:alternative test="@class='VALUE'"`**, derived into
    `FieldSpec.alternatives` and dispatched in **one** function, `Mapper._alternative_for`.
    Every conditional element ends with one unconditional alternative, which is what an
    unknown class validates as — and an unknown class is *valid*, reported by a single INFO
    line. Because xmlschema requires every alternative type to derive from the element's
    declared type, each conditional element's declared type is a **class-only derivation
    root** (`DeviceClassType`, `PlayerClassType`, `CueClassType`, `CueOutputClassType`);
    `DmxCueType` could never extend `MediaCueType`, since it carries no `<Media>`.
  - **The Python classes survive.** `AudioCue` is still an `AudioCue` when its class is
    `audio`, with the same fields, equality and hash, so `cuems-engine`'s ~30 `isinstance`
    and `singledispatch` sites are untouched. **The one wire change** is the key:
    `{"AudioCue": {...}}` becomes `{"Cue": {…, "class": "audio"}}`, which is the whole of
    FR-032's contract to `cuems-frontend`.
  - **New public entry point `cuems-reshape-devices`** (`xml/reshape_devices.py`): discovers
    `CUEMS_CONF_PATH` and the library, finds scripts by **root element rather than filename**,
    backs up before each rewrite, never writes a document that would not validate, and
    changes no bytes on a second run. It validates the reshaped tree **as the load path will
    see it** — registered version conversions applied to a throwaway copy, nothing written —
    because without that the two migration tools **deadlock** on a version-old script:
    reshape-first sees a version-1 `<duration>`, convert-first sees old-shape cues, and
    neither order completes. The order is therefore **reshape, then convert**.
  - **Two names published** (`cuems-engine` UR-1, `cuems-engine` UR-5 — **report numbers are per
    repository and collide**: `cuems-editor`'s UR-5 is a different, still-open finding, so always
    cite `<repo> UR-<n>`): `partition_by_adoption` from
    `cuemsutils.tools.NodeList` (FR-035) and `validate_config_document` from
    `cuemsutils.tools` (FR-036) — the first non-mutating adoption split and the first way to
    validate a configuration document without constructing a `ConfigManager`. Both are lazy
    module `__getattr__` re-exports: a module-level import of `xml.settings` from `NodeList`
    raises `ImportError`, because `adapters._register_enums()` imports `NodeRole` back out of
    `NodeList` while it is still initializing. `validate_object`'s deprecation advice is now
    **per schema** — a configuration document is sent at `validate_config_document`, not at
    `CuemsScript.validate`, which cannot validate one.
  - **No version step** (FR-020): `CURRENT_VERSION`, the conversion registry and
    `DELIBERATE_IDENTITY_STEPS` are untouched, so an older library meets a new-shape document
    with a raw schema error rather than `DocumentTooNewError`. The device shape and
    `doc_version` are **orthogonal**, which is why one `pre-008` fixture is carried in the new
    device shape at version 1.
  - **`write_tree` now registers the `cms` prefix**, and the bug it fixes was latent in
    `cuems-convert-documents` too: `ElementTree.parse` discards prefix declarations, and
    `register_namespace` writes a module-global, so the prefix survived only when
    `mapper.build_document` happened to run first in the same process. Neither standalone tool
    builds a document. The symptom is a file that still validates and still loads with every
    `cms:` rewritten to `ns0:`.
  - **Two budgets recorded as exceeded, not restated as passing** (`baseline.md` §T062).
    SC-PERF-001 is missed by 23% — the mappings load went 15.153 → 20.4 ms, and every
    reshaped schema's load got slower (`settings` +20%, `script` +12%, `hardware_outputs`
    +41%). One mechanism, profiled: `elementpath` builds a **fresh node tree over the
    document per `xs:alternative` or `xs:assert` evaluation**, so the cost scales with
    document size × class-carrying elements, not with the number of alternatives declared. A
    smaller, one-off part is schema-build time, which the config path pays per call because
    `XmlReaderWriter`'s `schema` setter builds a fresh `XMLSchema11` per instance instead of
    using the cached `get_schema` — a pre-existing shim this feature made more expensive, and
    the identified one-line mitigation, deliberately not applied here. SC-PERF-003 is missed
    by ~480× because the budget is the wrong instrument: it calibrated read + atomic rewrite
    with no validation, while the tool's cost is per-document schema validation — the thing
    that makes "a document that would not validate is not written" true. The actionable
    figure is **~30 ms per script, so a 200-project library migrates in ~6 s, once**.
    SC-PERF-002 is met (16.66–16.81 ms/test against ≤ 18.04).
  - **`cuems-engine` measured in three arms, not inferred**
    (`specs/013-device-class-reshape/sibling-repository-updates.md`): 923 passed at the branch
    point, **70 failed / 827 passed / 26 errors** on this branch, and **1 failed / 922 passed**
    after one `cuems-reshape-devices` invocation over `dev/test_xml_files/`. All 96 failures
    were old-shape **fixtures**; no engine source file is implicated, so every compatibility
    surface (`node_hw_outputs`, `node_mappings["audio"]`, `node_conf["videoplayer"]`) did its
    job. Feature 012's lesson arrived a second time: the breakage was in data a call-site
    census cannot see, and the same old-shape fixtures sit in `cuems-power-bridge` (nine) and
    `cuems-nodeconf` (two).
  - **The residual engine failure is the migration guide's half-migrated-library case**, and
    it surfaced a fixture that has been invalid for several releases:
    `dev/test_xml_files/projects/complex_test/project_mappings.xml` has an `<output>` with no
    `<id>` and no `<new_nodes>` at all. The branch-point library rejects it too, verified. The
    tool refusing to rewrite an invalid document is T034's specified behaviour, not a failure
    of the reshape — but it means a long-invalid document now blocks a migration where before
    it merely failed quietly.
  - The frozen legacy `xml/XmlBuilder.py` still emits per-class element names and so now
    writes documents the current schema rejects. It has no live caller and goes in `v0.1.1`;
    recorded in the migration guide rather than fixed.

- `012-uuid4-convergence` (**landed on its local branch** 2026-09-30; merges into
  `feat/xml-refactor`; nothing ships until the coordinated `xml-refactor-merge-candidate` tag
  after 011–015): one identity shape across the project, and the machinery that gets a deployed
  cluster there without losing a node.
  - **`UuidType` leaves `KNOWN_DIVERGENT_DECLARATIONS`** — the allowlist in
    `tests/contract/test_schema_name_overlap.py` is now **empty**, which is this feature's
    completion marker (FR-025) and closes the last X14-class defect the F2 ratchet recorded.
    It got there by **deletion, not narrowing** (research R13): the node identity must admit the
    sentinel (the package's own build-time generation emits it), `script.xsd`'s `UuidType` types
    cue and media `id` and must not, so the two could never match — which closed the
    identical-duplicate route while the divergent route *requires* the entry to stay. Retyping
    the element to `cms:NodeUuidType` and deleting network_map's declaration leaves the name
    declared once, the only state in which the stale-entry test *demands* the removal.
  - **Three named types, three schemas each** (`ConvergedUuidType`, `NotProvisionedUuidType`,
    and their union `NodeUuidType` — the only one any element references). None of the six
    schemas includes or imports another, so the anti-drift guarantee is a **test**
    (`KNOWN_IDENTICAL_DUPLICATES`), not a schema mechanism.
  - **`cuems-init-node --check` widens exit class 1** to "an identity is not converged", adds
    the verdict `migration-needed` and reaches the project library. Every shipped verdict keeps
    its exact spelling and meaning; the shipped contract test was extended **in the same
    commit**, since its identities are uuid4 and it would otherwise have stayed green while
    testing a superseded vocabulary.
  - **`cuems-init-node --remint`** (`tools/remint.py`): survey → abort on collision *before the
    table is built* → build once on the controller → persist before the first write → estimate
    and confirm → apply → verify → completion record. **The scope is split** (FR-011a): the
    controller rewrites its configuration *and* the library, every other node rewrites only its
    own configuration from a table the operator copies to it, and its library replica arrives by
    the project deployer's existing `rsync -rt`. A plain node without a table **refuses**; a
    table whose controller is *another node* is the **normal** case, not a refusal.
  - **Never restore a modification time.** The substitution is length-preserving and the
    replication compares size and time with no checksum (research R11), so the time is rsync's
    only signal. `os.replace` does the right thing; `shutil.copystat` is the trap. Pinned by
    `test_remint_mtime_advances.py`.
  - **Two collision routes closed in `init_node`**, and one of them **amends feature 011's D13**
    (recorded in *that* feature's spec, where a later reader finds it first): "mint iff there is
    none" becomes "…or the identity on disk was minted for different hardware". It **refuses**
    rather than re-minting, because the same evidence describes a replaced NIC, where preserving
    is correct; `--mac` is the operator answering that question.
  - **One type for one value** (FR-021b) via a per-**field** adapter opt-in — not by flipping
    `runs_adapter_table` for `settings`, which would re-decode every scalar in that document and
    silently retire feature 007's measured guarantee. `ConfigManager.node_uuid` answers with
    `Uuid` on a provisioned node and the published sentinel constant on one that is not; `Uuid`
    gains a total ordering. `specs/012-uuid4-convergence/consumer-census.md` is the **blocking
    precondition** (FR-032) and found what R4's question could not: the **map read** change
    reaches four repositories, not two — `cuems-editor` reads the map and appears nowhere in R4.
  - **The sibling impact was then *measured*, not inferred**
    (`specs/012-uuid4-convergence/sibling-repository-updates.md`): each sibling's own suite run
    against `a451036` and against this branch. `cuems-engine` 939/939 both arms,
    `cuems-power-bridge` 276/276 both, `cuems-editor` unchanged (7 pre-existing failures, plus
    two modules that have not imported since feature 008 retired `create_script`).
    **`cuems-nodeconf` is the only repository with work to do: 4 failures, one cause, four
    lines** — test fixtures whose node identities are not uuid4. The fix is verified to pass
    against **both** library versions, so it can land ahead of the coordinated tag. Note what
    this reverses: both risks the census predicted produced zero failures, and the real breakage
    was in *data* a call-site census cannot see.
  - **No rollback once `cuems-nodeconf` restarts**, measured: the re-mint is a literal
    substitution and leaves `doc_version` alone, so a re-minted document is still readable by the
    old library — but `CuemsNetworkMapType.save()` bumps the marker and nodeconf rewrites the map
    every 30 s, after which an older `cuems-utils` refuses it with `DocumentTooNewError`. Stated
    in the migration guide §9b.
  - **Two budgets recorded as exceeded, not restated as passing** (`baseline.md` §3, §6).
    FR-PERF-001's 500 MB/s floor is **unreachable** for this operation — a pass that reads and
    atomically rewrites `remint_200` with *no substitution at all* measures 298 MB/s, so the
    budget conflates bulk throughput with per-file syscall cost on 400 small files. SC-PERF-003's
    ±25% estimate tolerance is missed by ~2×, **pessimistically**: the survey scans for *any*
    uuid shape while the apply pass substitutes *known literals*, so dividing by the survey's
    throughput overstates. `ids.scan_values` took that from +884% to +121%; the rest is inherent.
  - Corrections applied to `specs/planning/etc-cuems-first-install{,-execution}.md` (FR-037),
    never silently: §9.2's narrowing description, §9.4's detection assignment (it is
    `cuems-init-node --check`, not the conversion tool), §10.5's script-filename procedure, the
    two-versus-three schema count, and §10.7's items now answered from code.

- `011-etc-cuems-first-install` (**landed on the local feature branch** 2026-09-28; merges into
  `feat/xml-refactor`; nothing ships until the coordinated `xml-refactor-merge-candidate` tag after
  011–015): a plain `apt install cuems-utils` leaves a node that loads and is unique.
  - **Packaging**: the six XSDs ship to `/usr/share/cuems/schemas` and are copied to `/etc/cuems` on
    every configure — never a conffile (D4/D5); `cuems-common 1.3.0-23` hands over
    `network_map.{xml,xsd}` with a snapshot-and-`rm_conffile` recipe so a live map survives and a
    later purge of `cuems-common` cannot delete it (research R3); `Breaks: cuems-common (<< 1.3.0-23~)`,
    no `Replaces`. The three documents are **generated at build** (`xml/make_defaults.py`, through the
    just-built venv's `bin/python`, deterministic, sentinel identity) and installed by `postinst`
    **only where absent**. `postinst` begins its custom block with `set +e` because dh-virtualenv's
    injected autoscript starts with `set -e`, runs the tool under a 60 s `timeout`, falls back to
    the pristine placeholders with a `NOT PROVISIONED` warning, and **never exits non-zero** — it is
    the base package of the stack. `postrm purge` removes exactly nine paths plus the write record,
    never `rm -r` (`/etc/cuems` holds another package's private SSH key). `debhelper-compat (= 13)`,
    `Standards-Version 4.6.2`. **No version bump anywhere** (`tests/packaging/test_no_version_bump.py`
    pins `0.1.0rc16` / `1.3.0-23` / `0.1.0-8`).
  - **Seed values are data** (D7/D9): `src/cuemsutils/defaults/system-defaults.toml` (package data,
    the one copy code reads; also installed under `/usr/share/cuems/defaults/`), loaded by
    `xml/seed_values.py` with four rules — completeness naming schema/type/field/file, no stale key,
    no identity (`uuid`/`mac` are injected, never seeded), scalar type matches the XSD type — and an
    `/etc/cuems/defaults.d/*.toml` overlay applied only by the tool, lexical order, later wins.
    `descriptor._SETTINGS_EXAMPLE_VALUES` is gone; the generated `settings.xml` is byte-identical.
  - **`cuems-init-node`** (`tools/init_node.py`, new public entry point, `[project.scripts]`,
    venv `bin/` + `/usr/bin` symlink): mints one uuid4 through `cuemsutils.tools.Uuid` (the only
    minter) or preserves the identity `settings.xml` carries; writes the three documents as one set
    (temporaries, ordered `os.replace`, in-memory restore); substitutes the sentinel token in every
    string leaf including compound `<uuid>_<id>` strings; seeds this node's map row through the new
    **`NodeIndex.ensure`** (by reference, pinned in `test_node_aliasing.py`); MAC from `--mac`,
    `ethernet0`, else the first physical interface, else **refuses** (a sentinel MAC on a live node
    collides in the MAC-keyed map); map row `name` = OS hostname. Operator edits are kept three-way
    against a write record (`/var/lib/cuems-utils/init-node/last-written.json`) and reported as
    `modified, kept`; `--reset` returns to defaults; `--force-new-identity --yes` re-mints; `--check`
    (`tools/identity_check.py`, stdlib XML only) reads the four identity locations and exits
    **0 / 1 mismatch / 2 absent / 3 NOT PROVISIONED**, precedence 3 > 2 > 1.
  - **D14, shape B**: the Avahi record is derived from `settings.xml` by **`cuems-nodeconf`** at every
    start and role change (its feature `003-startup-readiness`, gated here as T049, not implemented
    here); `cuems-config-node` no longer mints and the shipped templates carry the sentinel.
    **Both counterparts landed on their own branches** 2026-09-28: `cuems-nodeconf` 003 at
    `b305c1c`, which re-cut its `xml-refactor-merge-candidate` from `6c0cca7` and cleared T049
    here; and `cuems-common`'s handover (`b3dd7e1`, `f6750d7`, `e3c9430`), three direct commits
    with no feature dir of its own. **All four candidate tags were reconciled 2026-09-29** —
    `cuems-common` `3af31cc` → `e3c9430`, `cuems-power-bridge` `d5c4226` → `13a9af4`,
    `cuems-nodeconf` held at `b305c1c` with its message corrected to name `e3c9430`; `cuems-utils`
    still tags last by D27. **`cuems-power-bridge` moved once more the same day, `13a9af4` →
    `399baf7`, for one line of `debian/control`** — verified 2026-09-30 against the tag itself,
    which says so in its own message; this line said `13a9af4` until then, which is exactly the
    drift the lesson below warns about. Local tags verified in sync with `origin` on that date:
    `cuems-common` → `e3c9430`, `cuems-nodeconf` → `b305c1c`, `cuems-power-bridge` → `399baf7`;
    `cuems-engine`, `cuems-editor`, `cuems-frontend` and `cuems-utils` carry **no** tag yet.
    **Re-verified 2026-10-14 against the tags themselves (feature 015, T102)**, as *commits*
    (`<tag>^{commit}`): `cuems-common` → `e3c9430` and `cuems-power-bridge` → `399baf7` **hold**;
    `cuems-nodeconf` **moved** `b305c1c` → `5be6cf0` (re-cut over four commits, `b305c1c` is its
    ancestor); `cuems-frontend` now carries a tag, at `f5453a3`; `cuems-engine`, `cuems-editor` and
    `cuems-utils` still carry none. ⚠ Feature 015's first draft read `91b2d25`/`c29c25c`/`cabbb3e`
    as moved values — those are the **annotated tag objects**, not commits (`git rev-parse <tag>`
    versus `<tag>^{commit}`), which is the mistake the shared resolver
    (`tests/support/sibling_tags.py`) exists to make impossible.
    Tag messages are authored as files in `../.xml-refactor-tag-messages/` and applied with
    `git tag -a -F`. Dated before/after tables in
    `specs/011-etc-cuems-first-install/baseline.md` §"UX pass and announcements".
    **The lesson that outlives the incident**: for one day the tag set did not compose, because
    nodeconf's renderer `sys.exit(-1)`s on a template with no sentinel and `cuems-common`'s tag
    still pointed at a tree shipping the production uuid in `cuems.service.controller`. Both
    working trees were already correct and the reciprocal `Breaks:` could not see it — both
    packages sat at exactly their intended versions. **A candidate tag set is only as current as
    its least current member, and no packaging relation expresses that**; re-cutting one tag means
    re-checking its counterparts. Moving a published tag is maintainer-only, never an agent's.
  - **Measured corrections** (M1–M9 in the spec): `cuems-common`'s `node-identity-contract.md`
    already existed; `cuems-config-node` was a second minter; the editor hardcodes
    `/etc/cuems/script.xsd`; the fossil `get_{video,audio}_output_id('default')` raise `KeyError` on
    every node (feature 015's); 25 tests needed a host `/etc/cuems` because
    `tests/support/config_inventory.py` pops `CUEMS_CONF_PATH` at import — now a session guard in
    `tests/conftest.py` names any such test.
  - Lifecycle tests run in an unprivileged `mmdebstrap --mode=unshare` bookworm chroot
    (`CUEMS_CHROOT_TAR`; `quickstart.md`); no container runtime needed.

- `009-fix-dmx-channel-conversion` (**landed** 2026-09-03): `DmxUniverse.set_dmx_channels`
  (`cues/DmxCue.py`) no longer swallows a per-entry conversion failure and silently stores the raw,
  unconverted input — it raises `DmxChannelDecodeError` (new, `cuemsutils.errors`, joining
  `CuemsError`/`ValidationError`/`SchemaError`/`IngestError`), naming the universe and the failing
  entry's index/type, mirroring feature 005's `DmxSceneWriteError` precedent on the read side.
  Confirmed unreachable from a schema-valid `script.xml` (T1 already rejects a malformed
  `<DmxChannel>`) — reachable only from `CuemsScript.from_json` or direct/programmatic
  construction, so this feature makes **no `.xsd` change**. A batch mixing already-`DmxChannel`
  instances with still-raw-but-valid entries is now correctly converted on both sides instead of
  silently dropping one (today's original code raced two independent per-branch reassignments,
  order-dependently). Performance budget (SC-PERF-001) measured rather than assumed: ≤3 ms for a
  realistic universe (met, 0.71-0.74 ms/call unchanged), no regression for the 512-channel maximum
  (met, 37.07 ms/call pre-fix vs. 37.6-37.8 ms/call post-fix, within measurement noise — the
  redundant per-iteration reassignment this fix removes was never the dominant cost there; the 512
  individual `DmxChannel(...)` constructions are, untouched by this fix). See
  `specs/009-fix-dmx-channel-conversion/` for the full spec/plan/research, including a
  `/speckit.analyze` pass that caught a genuine contradiction in the original fix design for the
  mixed-batch case and a constitution-required performance budget stated as "N/A".
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
    (`fade_in` is behaviour-preserving — the engine's handler dispatched `_handle_play`'s body
    verbatim; **`fade_out` is not**, corrected 2026-10-01 from `cuems-engine`'s measured UR-7: its
    `_handle_fade_out` never called `disarm()`, so a converted document now disarms its target
    where it previously leaked player processes. An improvement, but not a preservation, and the
    wrong reason would stop a consumer checking its own handler), and the `fade_profiles` block
    dropped with every drop named in the report. An
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
  - `specs/agreements/schema-evolution-convention.md` (written to `specs/planning/` at the time,
    relocated 2026-09-03 once promoted to a binding cross-repo convention) is adopted: an element
    added to an
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
