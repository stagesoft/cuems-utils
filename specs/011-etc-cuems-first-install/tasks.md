---
description: "Task list for feature 011 — /etc/cuems first install"
---

# Tasks: `/etc/cuems` first install

**Input**: Design documents from `/specs/011-etc-cuems-first-install/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: REQUIRED by the constitution (Principle II). Written first, failing before implementation.
A packaging-level test that needs a built `.deb` or the chroot tarball **skips** when neither exists
and is marked as such; it still has to fail-before-pass when the artifact is present.

**Organization**: grouped by user story (seven, from `spec.md`), after a foundational phase that
carries the two things three stories share: the seed-values loader (research R4) and the
`NodeIndex.ensure` primitive (R7 item 7, decision D-R20-2). Sibling-repository work
(`cuems-common`'s handover, `cuems-nodeconf`'s feature 003) appears as **gate references** — the
verification this repository owes — following the convention `specs/010-consumer-migration/tasks.md`
set; the edits themselves live in those repositories.

## ⚠️ Read before using this file

- **`postinst` must never exit non-zero.** Every task that touches `debian/cuems-utils.postinst`
  keeps the final `exit 0` and the fallback path (research R8). **dh-virtualenv's injected
  autoscript begins with `set -e`**, so the custom block starts with `set +e` right after
  `#DEBHELPER#`; the script tests simulate that stanza (research R21).
- **Nothing under `/etc/cuems` is modified by the package.** Install-if-absent per file; the six
  schemas are the only files it replaces, always.
- **`/etc/cuems` is shared** — `power-bridge.key` is a private SSH key. No task may `rm -r` it.
- **No version bump on any package** (R19): `cuems-utils 0.1.0rc16`, `cuems-common 1.3.0-23`,
  `cuems-nodeconf 0.1.0-8`, entries amended in place. `test_no_version_bump.py` (T070) pins it.
- **No schema shape change.** The only `.xsd` edit is F1's annotation (T078), one isolated commit
  that also moves the six hashes in `tests/contract/test_schema_scope.py`.
- **Goldens are never regenerated to make a test pass** (FR-021). The public API golden is
  *extended* once, by T042, with a `scripts` key.
- **Tests run as** `uvx hatch run test.py3.11:run -- -q` (`hatch` is not on this host's PATH; the
  `hatch test` env lacks `hypothesis`). Chroot tests need `CUEMS_CHROOT_TAR`; see `quickstart.md`.
- **Commits are GPG-signed.** On `gpg failed to sign`, retry — never `--no-gpg-sign`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US7 from `spec.md`

## Path conventions

Every path is relative to this repository's root; `../<repo>` is a sibling checkout. New code:
`src/cuemsutils/defaults/`, `src/cuemsutils/xml/{seed_values,make_defaults}.py`,
`src/cuemsutils/tools/{init_node,identity_check,write_record}.py`; packaging under `debian/`; tests
under `tests/packaging/`, `tests/contract/`, `tests/integration/`.

---

## Phase 1: Setup

**Purpose**: the measurement scaffolding and test infrastructure every later phase writes into.

- [X] T001 Complete `specs/011-etc-cuems-first-install/baseline.md`'s suite row from a fresh `uvx hatch run test.py3.11:run -- -q` run on this host, quoted as a **range** over two runs (per research R20's flakiness note), and keep the 41.1 ms/test reference
- [X] T002 [P] Create `specs/011-etc-cuems-first-install/migration-guide.md` with the section skeleton FR-045 requires (upgraded hosts, purge destroys identity, disk imaging, `--check` exit codes, handover order and versions, hardware verification pointer) — it accumulates as stories land, never retrofitted
- [X] T003 [P] Create `tests/packaging/__init__.py` and `tests/packaging/conftest.py` with fixtures: `etc_dir`/`share_dir`/`state_dir` under `tmp_path`, a `run_maintainer_script(name, arg, env, simulate_autoscript=True)` helper that executes `debian/cuems-utils.<name>` with `CUEMS_ETC`/`CUEMS_SHARE`/`CUEMS_STATE`/`CUEMS_INIT_NODE`/`CUEMS_INIT_TIMEOUT` overrides (contract packaging.md) and, by default, **prepends a `set -e` stanza standing in for dh-virtualenv's injected autoscript**, a `sibling_deb(name)` fixture that builds `../cuems-common` or `../cuems-nodeconf` with `dpkg-buildpackage -us -uc -b` when the checkout exists (recording the version used in `baseline.md`) or skips with that reason, a `built_deb` fixture that finds the newest `../cuems-utils_*.deb` or skips, and a `chroot` fixture that extracts `$CUEMS_CHROOT_TAR` into `tmp_path` and runs commands through `unshare --map-auto --map-root-user … chroot` (research R9) or skips
- [X] T004 [P] Create `tests/packaging/stubs/cuems-init-node` — an executable stub honouring `CUEMS_STUB_EXIT` (exit code) and `CUEMS_STUB_SLEEP` (seconds), writing a marker file listing its argv — for the `postinst` fallback and `timeout` tests
- [X] T005 [P] Add the chroot tarball recipe to `specs/011-etc-cuems-first-install/quickstart.md` as the one command T003's fixture expects, and record its measured build time in `baseline.md` (38 s, 200 MB, measured 2026-09-25)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: what three or more stories depend on. **⚠️ No user story starts before this phase is green.**

### Step 0 — make the suite independent of a host `/etc/cuems` (plan, finding M9)

- [X] T006 Add `tests/conftest.py` assertion fixture (autouse, session) that fails the run with a named message if any test constructs `ConfigManager()` without `config_dir` while `/etc/cuems` is absent — written first, failing on this host against the four modules below
- [X] T007 [P] Pass `config_dir=<engine corpus>` explicitly in `tests/contract/test_public_surface.py`, `tests/contract/test_descriptor_instances.py`, `tests/contract/test_public_descriptor.py` and `tests/contract/test_descriptor_laziness.py` (the four modules that fell back to `/etc/cuems/` because `tests/support/config_inventory.py:55` pops `CUEMS_CONF_PATH` at import); suite green on a host with no `/etc/cuems`

### The seed-values loader (research R4; contract system-defaults-toml.md) — serves US2, US3, US4

- [X] T008 [P] Contract test `tests/contract/test_seed_values.py`: V1 a required scalar with no entry fails naming `(schema, type, field)` and the file; V2 an entry naming no declared field fails naming the key; V3 `uuid`/`mac` in any table is refused ("identity is not a default"); V4 an integer-typed field rejects a string and vice versa, naming key/expected/found; the shipped file passes all four for `settings`, `network_map` and `project_mappings`; `settings` values equal `descriptor._SETTINGS_EXAMPLE_VALUES` entry for entry (the byte-identity precondition) — all failing first
- [X] T009 Create `src/cuemsutils/defaults/__init__.py` and `src/cuemsutils/defaults/system-defaults.toml` with the tables of data-model.md §1 (settings values moved **verbatim** from `descriptor._SETTINGS_EXAMPLE_VALUES` with their D15 provenance comments; `network_map.NodeType` `name = "unprovisioned"`, `ip = "0.0.0.0"`, `node_role = "firstrun"`; `project_mappings.CuemsProjectMappingsType` `number_of_nodes = 1` and six empty `default_*`; an empty `project_mappings.NodeMappingType` table), and add `src/cuemsutils/defaults` to `[tool.hatch.build] include` in `pyproject.toml` so it ships as package data
- [X] T010 Create `src/cuemsutils/xml/seed_values.py`: `load_seed_values()` via `importlib.resources` + `tomllib`; `validate(tables)` implementing V1–V4 against `spec.derive(TypeKey(schema, type))`; `value_for(schema, type, field)`; `merge(base, overlays: list[Path])` (lexical order, later wins, same V2–V4 checks, syntax errors reported with file/line/column, identity keys refused) — overlay behaviour tested in US4
- [X] T011 Replace `descriptor._SETTINGS_EXAMPLE_VALUES` and `_settings_example_value` with calls into `seed_values` in `src/cuemsutils/xml/descriptor.py`, keeping `generate_settings_example()`'s signature and output; re-point the imports in `tests/contract/test_settings_example_generation.py` so its eleven tests keep their meaning (the "names the table and the fix" test now names `system-defaults.toml`)
- [X] T012 Contract test `tests/contract/test_seed_values.py::test_generated_settings_is_byte_identical_after_the_move`: the SHA-256 of `generate_settings_example().save()` output equals the value recorded from the pre-move tree in `baseline.md` (record it **before** T011 lands, in T001's pass)

### `NodeIndex.ensure` (research R7 item 7, D-R20-2) — serves US3 and nodeconf feature 003

- [X] T013 [P] Extend `tests/contract/test_node_aliasing.py` with an `ensure` case: `NodeIndex.ensure(node)` inserts the **same object** the caller holds (`index[mac] is node`), returns `True` on insert and `False` when a node with that uuid already exists (leaving the existing one untouched, other rows and flags unchanged), and fails against a `dict(node)` copy — failing first
- [X] T014 Add `NodeIndex.ensure(node) -> bool` to `src/cuemsutils/tools/NodeList.py` with a docstring stating the by-reference contract (T091/T092 upstream), practice 3 (never `merge` for seeding), and that `cuems-nodeconf`'s feature 003 consumes it; update `tests/golden/api/public_api.json` for the new method on the public `NodeIndex` (a recorded golden event, reason in the commit message)

**Checkpoint**: suite green on a bare host; seed values load and validate; `ensure` pinned.

---

## Phase 3: User Story 1 — The six schemas ship to `/etc/cuems`, and `cuems-common` hands its mirror over (Priority: P1) 🎯 MVP

**Goal**: every node carries the installed library's six schemas at `/etc/cuems/*.xsd`, replaced on
every install, never a conffile; `cuems-common` stops shipping its mirror and the two live
"validates against a file nobody ships" defects plus the editor's `script.xsd` path close.

**Independent Test**: build, install into the chroot, six files byte-identical to the bundled copies;
upgrade a chroot carrying the old `cuems-common` stub in both orders — live map byte-identical, zero
`.dpkg-*` siblings.

### Tests for User Story 1 (REQUIRED) ⚠️

- [X] T015 [P] [US1] `tests/packaging/test_built_package.py::test_schemas_ship_under_usr_share`: the `.deb` lists `usr/share/cuems/schemas/{settings,network_map,project_mappings,project_settings,script,hardware_outputs}.xsd`, each byte-identical to `src/cuemsutils/xml/schemas/`, and `DEBIAN/conffiles` contains no `/etc/cuems` path (skips without a build)
- [X] T016 [P] [US1] `tests/packaging/test_postinst.py::test_schemas_are_installed_always`: with `CUEMS_ETC` pre-seeded with a stale `network_map.xsd`, `postinst configure` replaces all six with the `CUEMS_SHARE` copies, mode 0644, and creates none of the `.xml` beyond what T017's tests cover
- [X] T017 [P] [US1] `tests/packaging/test_lifecycle_chroot.py::test_custody_transfer_both_orders` (slow): build a stub old `cuems-common` `.deb` from `tests/packaging/stubs/old-cuems-common/` that ships `/etc/cuems/network_map.{xml,xsd}` as conffiles; install it; write a modified live map; then install new `cuems-utils` and the new `cuems-common` from `sibling_deb("cuems-common")` (skips when the sibling is absent) in **both** unpack orders and via `apt install ./a ./b`; assert live map byte-identical, `ls /etc/cuems/network_map.*` shows exactly the two files, `/etc/cuems/network_map.xsd` equals the bundled schema, and a subsequent `dpkg --purge cuems-common` leaves the map (research R3)
- [X] T018 [P] [US1] `tests/packaging/test_lifecycle_chroot.py::test_live_defects_resolve` (slow): after install, `/etc/cuems/project_mappings.xsd`, `/etc/cuems/settings.xsd` and `/etc/cuems/script.xsd` exist and validate the corpus documents with `xmlschema.XMLSchema11` (SC-011)

### Implementation for User Story 1

- [X] T019 [US1] Add to `debian/rules` `override_dh_virtualenv`: after `dh_virtualenv`, `install -d` + `install -m 0644 src/cuemsutils/xml/schemas/*.xsd debian/cuems-utils/usr/share/cuems/schemas/` (research R2; no interpreter-version path)
- [X] T020 [US1] Create `debian/cuems-utils.postinst` (POSIX `sh`, `#DEBHELPER#` first, then **`set +e` with the comment that the injected dh-virtualenv autoscript begins with `set -e`** — contract packaging.md step 0 — `exit 0` last): the path-override preamble (including `CUEMS_INIT_TIMEOUT` and the "empty `CUEMS_INIT_NODE` ⇒ skip the tool" rule), `install -d -m 0755 "$CUEMS_ETC"`, and the six-schema `install -m 0644` block — the document and tool blocks are US2/US3's
- [X] T021 [US1] Add `Breaks: cuems-common (<< 1.3.0-23~)` to `debian/control` with the comment that `Replaces` is deliberately absent (no manifest overlap under `/etc`, D5) — research R3
- [X] T022 [US1] Gate — `../cuems-common` handover, custody transfer (contract cuems-common-handover.md §1): verify `debian/install` no longer lists `etc/cuems/network_map.xml` / `.xsd`; `preinst` snapshots the live map to `/var/backups/cuems-common.network_map.xml.presave` and runs `rm_conffile` for both paths with prior-version `1.3.0-23~`; `postinst` runs the same two `rm_conffile`, restores the map from the snapshot if absent, removes only a `.dpkg-bak` identical to the snapshot, and reinstalls `network_map.xsd` from `/usr/share/cuems/schemas/` if absent; `postrm` carries the two `rm_conffile`; `etc/cuems/network_map.xsd` deleted from that repository; record the verifying run in `baseline.md`
- [X] T023 [P] [US1] Gate — `../cuems-common` tests (contract §3): `tests/test_schema_mirror.py` and `tests/test_shipped_network_map.py` retired; `test_network_map_example.py`, `test_documented_validation.py`, `test_network_map_conversion.py` re-based to the sibling's bundled schema (skip when absent); a new test asserts `debian/install` names no `etc/cuems/network_map.*`; record in `baseline.md`
- [X] T024 [P] [US1] Gate — `../cuems-common` `debian/control` description paragraph rewritten (the "mirrored network_map.xsd" floor reason becomes "the release that ships the schemas to `/etc/cuems`"), `1.3.0-23` changelog entry amended, **no version bump**; record in `baseline.md`
- [X] T025 [US1] Write the US1 section of `specs/011-etc-cuems-first-install/migration-guide.md`: what changes on an upgraded host (six schemas appear/replace; the stale mirror and any `network_map.xsd.dpkg-dist` are gone), the handover order and the two unreleased versions (A3, R19), and the announced re-cut of `cuems-common`'s `3af31cc`

**Checkpoint**: US1 is shippable on its own — schema drift ended, three live defects closed, no identity work.

---

## Phase 4: User Story 2 — The three documents are generated at build, shipped pristine, and installed only when absent (Priority: P1)

**Goal**: `/usr/share/cuems/defaults/{settings,network_map,default_mappings}.xml` generated
deterministically at build with the sentinel identity; installed to `/etc/cuems` per file only when
absent; never modified afterwards by the package.

**Independent Test**: two builds byte-identical; pristine documents validate and load with an empty
`LoadReport`; markers placed at the three paths survive `--reinstall` byte-for-byte.

### Tests for User Story 2 (REQUIRED) ⚠️

- [X] T026 [P] [US2] `tests/contract/test_make_defaults.py`: generating into two temp dirs yields byte-identical files; each carries the sentinel uuid and MAC and no other uuid-shaped token; each validates (T1) and `load_with_report`/the config accessors return an empty `LoadReport`; `doc_version` equals `versioning.CURRENT_VERSION[schema]`; `network_map.xml` has exactly one row (`unprovisioned`, `0.0.0.0`, `firstrun`); `default_mappings.xml` has one node entry with empty `audio`/`video`/`dmx`, `number_of_nodes` 1, six empty defaults, empty `new_nodes`; a stale key or a missing required entry in a patched TOML fails naming it (FR-010) — failing first
- [X] T027 [P] [US2] `tests/integration/test_default_mappings_fresh.py`: `ConfigManager(load_all=True)` over the three pristine documents in `tmp_path` succeeds (the sentinel triple is coherent, A8); `get_video_output_id('default')` and `get_audio_output_id('default')` — **measured 2026-09-28: both raise `KeyError` on every node today** (they read `node_conf` keys `settings.xsd` never declared; zero callers; feature 014's fossil) — pinned as measured rather than changed (research R12 corrected)
- [X] T028 [P] [US2] `tests/packaging/test_postinst.py::test_documents_installed_only_when_absent`: with `CUEMS_INIT_NODE` **empty** (the tool step skipped — this test must not depend on US3's block), `postinst configure` copies each of the three from `CUEMS_SHARE/defaults` only where absent; a pre-existing file (real identity, sentinel, or garbage) is byte-identical after; `defaults.d/` under `CUEMS_ETC` is never read (a syntactically broken overlay present changes nothing and the exit is 0)
- [X] T029 [P] [US2] `tests/packaging/test_built_package.py::test_pristine_defaults_ship`: the `.deb` lists the three documents and `system-defaults.toml` under `usr/share/cuems/defaults/`, the documents carry the sentinel, and the TOML is byte-identical to `src/cuemsutils/defaults/system-defaults.toml` (skips without a build)
- [X] T030 [P] [US2] `tests/packaging/test_lifecycle_chroot.py::test_identity_survives_upgrade_reinstall_remove` (slow): install, record checksums of the three documents, then upgrade (reinstall the same `.deb` as a newer changelog build), `dpkg -i --reinstall`, `dpkg -r` then `dpkg -i`; checksums unchanged each time (SC-002)

### Implementation for User Story 2

- [X] T031 [US2] Create `src/cuemsutils/xml/make_defaults.py` (`python -m cuemsutils.xml.make_defaults --out DIR`): builds the three documents from the descriptor and `seed_values` (settings via `generate_settings_example`; a `network_map` document with one `node` row; a `project_mappings` document with one `NodeMappingType` entry and empty `NewNodesType`) injecting the sentinel identity, validates each, loads each back asserting an empty report, generates **twice** into temp dirs and refuses on any byte difference, then writes to `--out` — every `default_mappings` piece carries a "retires with feature 014" note (FR-012)
- [X] T032 [US2] Add the generator invocation to `debian/rules` `override_dh_virtualenv`: `debian/cuems-utils/usr/lib/cuems/bin/python -m cuemsutils.xml.make_defaults --out debian/cuems-utils/usr/share/cuems/defaults` and `install -m 0644 src/cuemsutils/defaults/system-defaults.toml` to the same directory (research R2)
- [X] T033 [US2] Add to `debian/cuems-utils.postinst` the install-if-absent block for the three documents (copy from `$CUEMS_SHARE/defaults` only where `! -e`), placed **after** the tool invocation block US3 adds (so the copy is the fallback), and the two `WARNING:` lines with the exact `NOT PROVISIONED` wording from contract cuems-init-node.md
- [X] T034 [US2] Write the US2 section of `migration-guide.md`: where the pristine copies live, that `dpkg -V` verifies them, how to diff a live document against pristine, and that the package never modifies an existing file

**Checkpoint**: a node installs loadable, sentinel-identity documents; upgrade/reinstall/remove leave them untouched.

---

## Phase 5: User Story 3 — `cuems-init-node` writes the coherent triple atomically, and `postinst` calls it (Priority: P1)

**Goal**: a plain `apt install` mints one uuid4 and leaves `settings.xml`, `network_map.xml` and
`default_mappings.xml` coherent; `postinst` never exits non-zero; the tool is public, re-runnable,
and preserves identity.

**Independent Test**: two chroot installs from one `.deb` give two different uuid4 identities, no
sentinel token anywhere in `/etc/cuems`, and `ConfigManager(load_all=True)` succeeds inside each;
with the tool sabotaged, the package still configures and warns.

### Tests for User Story 3 (REQUIRED) ⚠️

- [X] T035 [P] [US3] `tests/integration/test_init_node_triple.py`: on an empty `conf_dir`, a plain run writes all three; the uuid is a uuid4 (matches `Uuid.UUID4_REGEX`); the MAC comes from `--mac`, else a stubbed `ethernet0`, else the first physical interface (a `--sysfs` override under `tmp_path`), and with **no** determinable MAC the run refuses (exit 1) writing nothing (FR-025a); `init_node.py`/`identity_check.py`/`write_record.py` import no `uuid` module directly (source assertion, FR-039); the same uuid appears bare in all three and the serialized bytes of each contain **no** sentinel token, including inside a compound `default_video_output` value seeded as `<sentinel>_0` for the test (FR-026); `ConfigManager(load_all=True)` over the result succeeds; `network_map.xml`'s self-row is `firstrun` with `name` = the OS hostname and `ip` = the chosen interface's IPv4 or `0.0.0.0` (FR-025a) and was inserted via `NodeIndex.ensure` with other rows and their `adopted`/`online` untouched (FR-029) — failing first
- [X] T036 [P] [US3] `tests/integration/test_init_node_triple.py::test_identity_preserved_and_install_missing`: a re-run on a real-identity `settings.xml` keeps uuid and MAC; `--install-missing` with `settings.xml` present and `network_map.xml` absent creates only the absent siblings coherent with that identity and leaves `settings.xml` byte-identical; `--install-missing` on a present sentinel `settings.xml` or a present stub map **does not touch them** (G8); `--install-missing` with `settings.xml` absent mints; `--uuid` with a non-uuid4 is refused before writing (exit 1); `--force-new-identity` without `--yes` refuses, with it re-mints and prints old/new and the "restart cuems-nodeconf" line
- [X] T037 [P] [US3] `tests/integration/test_init_node_triple.py::test_atomic_restore_on_failure`: monkeypatch `os.replace` to fail on the second document; all three paths hold their previous content afterwards (or remain absent), exit is 1 and the message names the document (G2); a second run with unchanged inputs replaces nothing (G6, checksums and mtimes equal)
- [X] T037a [P] [US3] Extend `tests/contract/test_no_routine_backups.py` with an `init-node` case: after a plain run, a `--reset` and a `--force-new-identity --yes`, `conf_dir` and `state_dir` hold zero `.bak`-like files (FR-030, contract G9) — failing first if any backup is written
- [X] T038 [P] [US3] `tests/integration/test_init_node_triple.py::test_lock_and_nodeconf_warning`: two concurrent invocations serialize on `/run/lock/cuems-init-node.lock` (`--lock-file` override under `tmp_path`); when `systemctl is-active cuems-nodeconf.service` (stubbed via `--systemctl` override) reports active, a write run warns and requires `--yes`
- [X] T039 [P] [US3] `tests/packaging/test_postinst.py::test_tool_invocation_and_fallback` (run with the simulated `set -e` autoscript stanza, so a missing `set +e` fails these cases): `postinst configure` invokes `$CUEMS_INIT_NODE --no-overlay --install-missing` under `timeout 60s` (assert argv from the stub's marker); with `CUEMS_STUB_EXIT=1` it copies the pristine placeholders for absent documents, prints both `WARNING:` lines including `NOT PROVISIONED`, and exits 0; with `CUEMS_STUB_SLEEP=2` and the timeout overridden to 1 s (`CUEMS_INIT_TIMEOUT`), it falls back the same way; the block sits after `#DEBHELPER#` and before `exit 0` (text assertion on the script)
- [X] T040 [P] [US3] `tests/packaging/test_lifecycle_chroot.py::test_fresh_install_loads_and_is_unique` (slow): two fresh chroots from one `.deb`; inside each, `/usr/lib/cuems/bin/python -c 'from cuemsutils.tools.ConfigManager import ConfigManager; ConfigManager(load_all=True)'` succeeds; the two uuids differ, both uuid4; `grep -r 00000000-0000-0000-0000-000000000000 /etc/cuems` finds nothing (SC-001, SC-007); a third chroot with `/usr/lib/cuems/bin/python` replaced by a non-executable file configures with exit 0 and the warning in the captured output (SC-008)
- [X] T041 [P] [US3] `tests/packaging/test_ordering_premise.py` (research R16): this package's `postinst` invokes the tool after `#DEBHELPER#` and before the final `exit 0`; when `../cuems-common` exists, its `debian/control` still depends on `cuems-utils` and its `postinst` still has no `#DEBHELPER#` token (skip otherwise)
- [X] T042 [P] [US3] Extend `tests/support/public_api.py` with `PUBLIC_SCRIPTS = {"cuems-convert-documents", "cuems-init-node"}` and `_snapshot()` with a `"scripts"` key from `importlib.metadata.entry_points(group="console_scripts")`; extend `tests/golden/api/public_api.json` **once** with that key (research R11; reason in the commit message) so that `tests/contract/test_public_api_surface.py` fails until the entry point exists

### Implementation for User Story 3

- [X] T043 [P] [US3] Create `src/cuemsutils/tools/write_record.py`: `WriteRecord` dataclass per data-model.md §6 (`version`, `written_at`, per-document `path`/`sha256`/`fields`), `load(state_dir) -> WriteRecord | None`, `save(state_dir, record)` atomic (temp + `os.replace`), `fields_of(document_obj)` flattening dotted paths — `network_map` limited to this node's row
- [X] T044 [US3] Create `src/cuemsutils/tools/init_node.py`: argparse per contract cuems-init-node.md (`--uuid`, `--mac`, test override `--sysfs`, `--overlay/--no-overlay`, `--install-missing`, `--reset`, `--force-new-identity`, `--conf-dir`, `--state-dir`, `--defaults`, `--dry-run`, `--verbose`, `--yes`, `--check`, `--json`, `--version`, plus test overrides `--lock-file`, `--systemctl`); library log level `WARNING` unless `--verbose`/`CUEMS_LOG_LEVEL` (R15); `flock`; identity resolution (preserve / mint via `Uuid()` / `--uuid`); MAC from `--mac`, else `ethernet0`, else the first non-loopback non-virtual physical interface under `/sys/class/net`, else **refuse exit 1** (FR-025a); map row `name` = `socket.gethostname()`, `ip` = the chosen interface's IPv4 else `0.0.0.0`; build the three documents from `seed_values` + descriptor, substitute the sentinel token in every string leaf, validate all three in memory, write via temp files and ordered `os.replace` with in-memory restore (R6), assert no sentinel in the bytes (G4), self-row via `NodeIndex.ensure`, then `write_record.save`; report lines in the `<path>: <verdict> (<detail>)` idiom; exit codes per contract; `--check` delegates to `identity_check` (US6)
- [X] T045 [US3] Add `cuems-init-node = "cuemsutils.tools.init_node:main"` to `[project.scripts]` in `pyproject.toml` and create `debian/cuems-utils.links` with `usr/lib/cuems/bin/cuems-init-node usr/bin/cuems-init-node` (research R1)
- [X] T046 [US3] Add to `debian/cuems-utils.postinst` the tool block: `install -d -m 0755 "$CUEMS_STATE/init-node"`, `timeout "${CUEMS_INIT_TIMEOUT:-60s}" "$CUEMS_INIT_NODE" --no-overlay --install-missing`, falling through to T033's placeholder copy on non-zero, skipped entirely when `CUEMS_INIT_NODE` is empty — placed after the schema block, after `#DEBHELPER#` and after the `set +e`
- [X] T047 [US3] Gate — `../cuems-common` handover, D14 half (contract §4): `cuems-config-node` contains no `uuid1`/`uuid4` call and rewrites no template or Avahi file (a new `tests/test_config_node_no_minting.py` there); the three `usr/share/cuems/cuems.service.*` templates carry the sentinel uuid (`test_avahi_vocabulary.py` extended); the three `cp` rules are gone from `etc/sudoers.d/99-cuems-avahi` and `test_template_consumers.py` is re-based; `debian/postinst` makes no new Avahi call; record in `baseline.md`
- [X] T048 [P] [US3] Gate — `../cuems-common/docs/node-identity-contract.md` gains the "Where the `uuid=` value comes from" subsection (contract §5): source `settings.xml`, sole minter `cuemsutils.tools.Uuid`, sole writer of the record `cuems-nodeconf`, verifier `cuems-init-node --check`, the retired second minter and the retired hardcoded template uuid with their versions, the sentinel never announced, the role-flip step "restart `cuems-nodeconf`", and the ownership table matching data-model.md §5; record in `baseline.md`
- [ ] T049 [P] [US3] Gate — `../cuems-nodeconf` feature `003-startup-readiness` (contract §4a; brief `specs/planning/10-readiness-window.md` §9, decisions D1–D3): verify the render from `settings.xml` runs **before** `set_comms()`, reloads only on change, refuses to start unprovisioned with `NOT PROVISIONED` and creates no socket, renders at the three role-change sites, asserts the discovered self uuid, and seeds through `NodeIndex.ensure` naming the `cuems-utils` commit that added it; verify that repository's hardware ledger entry §5 exists; record the tests and the run in `baseline.md`. **This is a gate, not an edit** — the code lands in that repository under its own constitution
- [X] T050 [US3] Write the US3 section of `migration-guide.md`: the partial-triple edge case on upgraded hosts (run `cuems-init-node` once), that `postinst` never modifies an existing file, the degraded fallback and its `NOT PROVISIONED` state, the disk-imaging hazard (purge or `--force-new-identity` before imaging), that identity changes end with "restart `cuems-nodeconf`", and the announced re-cut of nodeconf's `6c0cca7`

**Checkpoint**: a plain install leaves a node that loads and is unique; the tool is public and re-runnable.

---

## Phase 6: User Story 4 — Seed values live in TOML with a `defaults.d` overlay, applied by `cuems-init-node` (Priority: P2)

**Goal**: site overlays under `/etc/cuems/defaults.d/` applied only by the tool, in lexical order,
typed scalars preserved; operator edits preserved three-way against the write record; `--reset`
returns to defaults; `postinst` never reads the overlay.

**Independent Test**: an overlay changing one scalar shows up in `settings.xml` with identity kept;
a malformed overlay exits non-zero naming file and line with nothing written; a hand edit survives a
plain re-run and is reverted by `--reset`.

### Tests for User Story 4 (REQUIRED) ⚠️

- [X] T051 [P] [US4] `tests/integration/test_init_node_overlay.py`: one overlay scalar lands in `settings.xml`, everything else upstream, identity unchanged; two overlay files — the lexically later wins and `--verbose` names the winning file per overridden key; `35` vs `"auto"` for `output_latency_ms` survive as int vs string in the document; a syntax error exits 1 naming file/line/column and writes nothing; an unknown key exits 1 naming table and key; `uuid`/`mac` in an overlay exits 1 with "identity is not a default"; `--no-overlay` ignores everything under `defaults.d` — failing first
- [X] T052 [P] [US4] `tests/integration/test_init_node_overlay.py::test_operator_edits_three_way`: after a first run, hand-edit `library_path`; a plain re-run keeps it and prints `modified, kept` with path/field/value and the `--reset` hint; `--dry-run` shows it without writing; `--reset` reverts it (listing it first), keeps identity, and leaves other nodes' rows and adoption flags in `network_map.xml` untouched (FR-027b); with the write record deleted, a re-run changes **zero** on-disk values and says the record was missing (FR-027a, SC-010a); an overlay value that collides with a hand edit loses without `--reset` and wins with it
- [X] T053 [P] [US4] `tests/packaging/test_postinst.py::test_overlay_never_read`: a malformed `defaults.d/00.toml` under `CUEMS_ETC` and a real tool on `CUEMS_INIT_NODE` — `postinst configure` exits 0 and the three documents equal what a `--no-overlay` run produces (SC-009)

### Implementation for User Story 4

- [X] T054 [US4] Implement overlay application in `src/cuemsutils/tools/init_node.py`: `--overlay DIR` (default `/etc/cuems/defaults.d`), `seed_values.merge` over sorted `*.toml`, refusal messages per contract, `--verbose` provenance per key
- [X] T055 [US4] Implement the three-way decision in `src/cuemsutils/tools/init_node.py` using `write_record`: per dotted field — equal to record ⇒ recompute; different ⇒ keep and report `modified, kept`; absent from record ⇒ computed; `--reset` ⇒ computed for every non-identity field with the reverted list printed before writing; no record ⇒ keep every difference and say so
- [X] T056 [US4] Write the US4 section of `migration-guide.md` and the operator example in `quickstart.md` (already drafted): the overlay grammar with a pointer to contract system-defaults-toml.md, precedence, the "modified, kept" behaviour, and `--reset`

**Checkpoint**: site values apply without clobbering venue decisions; a return to defaults exists.

---

## Phase 7: User Story 5 — Purge removes only this package's paths; the last CUEMS package removed empties the directory (Priority: P2)

**Goal**: `postrm purge` removes exactly the nine `/etc/cuems` paths plus the write record and
`rmdir`s the directories only when empty; `remove` touches nothing.

**Independent Test**: purge in a chroot seeded with every other owner's files — those files
byte-identical, directory present; purge of the whole stack — no `/etc/cuems`.

### Tests for User Story 5 (REQUIRED) ⚠️

- [X] T057 [P] [US5] `tests/packaging/test_postrm.py`: with `CUEMS_ETC` holding the nine paths plus `ap.conf`, `power-bridge.key`, `cluster.conf`, `network_map.xml.dpkg-dist`, `defaults.d/10.toml`, and `CUEMS_STATE/init-node/last-written.json` — `postrm purge` removes exactly the nine and the record, leaves everything else byte-identical, leaves the directory; with only the nine present, the directory is gone afterwards; `postrm remove`, `upgrade`, `failed-upgrade`, `abort-*` change nothing; the script contains no `rm -r` (text assertion) — failing first
- [X] T058 [P] [US5] `tests/packaging/test_lifecycle_chroot.py::test_purge_alone_and_whole_stack` (slow): install `cuems-utils` plus `sibling_deb("cuems-common")` and `sibling_deb("cuems-nodeconf")` where available, seed the chroot's `/etc/cuems` with marker files for the other owners, `dpkg --purge cuems-utils`, markers byte-identical and directory present; then remove the markers and purge every CUEMS package present — `/etc/cuems` absent (SC-003); purge then install again yields a **new** uuid

### Implementation for User Story 5

- [X] T059 [US5] Create `debian/cuems-utils.postrm` (POSIX `sh`, path overrides, `#DEBHELPER#`, `exit 0`): on `purge` only, `rm -f` the nine `$CUEMS_ETC` paths and `$CUEMS_STATE/init-node/last-written.json`, then `rmdir --ignore-fail-on-non-empty` for `$CUEMS_STATE/init-node`, `$CUEMS_STATE`, `$CUEMS_ETC`; every other argument is a no-op (data-model.md §8)
- [X] T060 [US5] Write the US5 section of `migration-guide.md`: purge destroys identity by design; remove does not; what survives a purge (other packages' files, `.dpkg-*` siblings, `defaults.d/`)

**Checkpoint**: destructive lifecycle proven against a shared directory holding a private key.

---

## Phase 8: User Story 6 — `cuems-init-node --check` reads all four identity locations and reports mismatches by path (Priority: P3)

**Goal**: one command that turns `Node with uuid … not found` into a named path and a fixing
command, and the only detector of a drifted Avahi record; four exit classes with precedence 3 > 2 > 1.

**Independent Test**: edit one location, `--check` names it and exits 1; restore, exit 0; sentinel
source, exit 3; missing location, exit 2; never writes.

### Tests for User Story 6 (REQUIRED) ⚠️

- [X] T061 [P] [US6] `tests/contract/test_identity_check.py`: coherent fixture ⇒ exit 0 and four `ok` lines; map lacking the self-row ⇒ exit 1 naming `network_map.xml` and "self-entry missing"; `default_mappings.xml` with a sentinel token inside a compound string ⇒ exit 1 naming it; Avahi service file (fixture under `--avahi-service`) whose two records disagree with the source or with each other ⇒ exit 1 with both values; sentinel source ⇒ exit 3 with `NOT PROVISIONED`, also when the Avahi file is absent (precedence 3 > 2); a missing or unparseable location on a provisioned node ⇒ exit 2 (precedence 2 > 1 when both apply); `--json` emits one object with the same content; checksums of every input equal before and after every run (G3) — failing first

### Implementation for User Story 6

- [X] T062 [US6] Create `src/cuemsutils/tools/identity_check.py`: read the source (`settings.xml` via the strict path), the two mirrors (self-row presence; node entry presence and a byte-level sentinel scan), and `/etc/avahi/services/cuems.service` (`<txt-record>uuid=…</txt-record>`, both service blocks); build the report of data-model.md §7; compute the exit class with precedence; render text and JSON; name the fixing command (`cuems-init-node`, `cuems-init-node --reset`, `systemctl restart cuems-nodeconf.service`, or `systemctl unmask …` when the Avahi record is absent) — research R14
- [X] T063 [US6] Wire `--check`/`--json`/`--avahi-service` in `src/cuemsutils/tools/init_node.py` and make the `NOT PROVISIONED`, `modified, kept` and fixing-command strings module-level constants shared with the write path and asserted by `tests/packaging/test_postinst.py` against the script's warning text (FR-UX-001)
- [X] T064 [US6] Write the US6 section of `migration-guide.md`: the four locations, the four exit codes with precedence, and one worked example per non-zero class

**Checkpoint**: every identity failure has a named path and a next command.

---

## Phase 9: User Story 7 — The packaging hygiene pass (Priority: P3)

**Goal**: `debhelper-compat (= 13)`, current `Standards-Version`, no `dh_python2` provenance, no
build artifacts, the `pyvenv.cfg` check pinned, the three versions pinned.

**Independent Test**: build; the built-package test passes every assertion; `git status` clean after a build.

### Tests for User Story 7 (REQUIRED) ⚠️

- [X] T065 [P] [US7] `tests/packaging/test_built_package.py::test_hygiene`: `debian/compat` absent; `Build-Depends` names `debhelper-compat (= 13)`; `Standards-Version` ≥ `4.6.2`; the built `DEBIAN/postinst` contains no `dh_python2`, the dh-virtualenv autoscript block precedes a `set +e` which precedes the tool block; no line this feature adds to `debian/rules`, `cuems-utils.postinst`, `cuems-utils.postrm` or `cuems-utils.links` matches `python3\.1[0-9]` (FR-044); `pyvenv.cfg` `home = /usr/bin` and `bin/python` is a relative symlink; `.deb` size delta against the previous build ≤ 100 KB when a previous build is beside it (skips without a build) — failing first where the tree is wrong today (compat, Standards-Version)
- [X] T066 [P] [US7] `tests/packaging/test_built_package.py::test_no_manifest_overlap_with_siblings`: no path in the `.deb` under `/usr/lib/cuems`, `/usr/bin` or `/usr/share/cuems` is also installed by `../cuems-common/debian/install`, `../cuems-nodeconf` or `../cuems-power-bridge` (skip absent siblings)
- [X] T067 [P] [US7] `tests/packaging/test_no_version_bump.py` (research R19): `debian/changelog` head is `0.1.0rc16`; when present, `../cuems-common` head is `1.3.0-23` and `../cuems-nodeconf` head is `0.1.0-8`; `src/cuemsutils/__init__.py` says `0.1.0rc16`

### Implementation for User Story 7

- [X] T068 [US7] Edit `debian/control`: `Build-Depends: debhelper-compat (= 13), dh-virtualenv (>= 1.2), python3, python3-setuptools, python3-pip, python3-dev`; `Standards-Version: 4.6.2`; delete `debian/compat`; keep the `Depends` line unchanged (Python pin out of scope)
- [X] T069 [P] [US7] Rewrite `debian/README.Debian` (point at `README.source`, the first-install layout, `cuems-init-node --check`) and extend `debian/README.source`: replace the "/etc/cuems first install — planned" paragraph with the landed description (what ships where, the never-conffile rule, the postinst never-fail rule, the purge inventory, the chroot lifecycle test)
- [X] T070 [US7] Amend the `0.1.0rc16` entry in `debian/changelog` **in place** (no new version): the schemas to `/etc/cuems`, the generated defaults, `cuems-init-node`, install-if-absent, purge inventory, the `Breaks` on `cuems-common`, compat 13, `Standards-Version`, the removed "still ships nothing under /etc" bullet replaced by what now ships; keep the NOT YET BUILT preamble until the first build
- [X] T071 [US7] Build **twice** with `dpkg-buildpackage -us -uc -b`, compare `usr/share/cuems/defaults/*` between the two `.deb`s by checksum (SC-005 at build level), run the `pyvenv.cfg` check from `README.source`, confirm `git status` shows no artifact, and record the build time, the `.deb` size, the checksum comparison and the check's output in `baseline.md` (SC-004, SC-005)

**Checkpoint**: the package is built the way the sibling packages are, and a bump is a deliberate act.

---

## Phase 10: F1 writer annotations (FR-047, research R13) — one isolated commit

- [X] T072 Extend `tests/contract/test_duplication_flags.py` with `test_every_schema_declares_its_writer`: each of the six schemas' root element carries exactly one `xs:annotation` whose `xs:appinfo` holds ≥ 1 `cms:writer` element with a `scope` attribute, every writer name is in the allowed set (`cuems-init-node`, `cuems-nodeconf`, `cuems-editor`, `cuems-hardware-discovery`), and the scopes match the table in FR-047 — failing first
- [X] T073 Add the annotations to all six `src/cuemsutils/xml/schemas/*.xsd` per FR-047, update the six hashes in `tests/contract/test_schema_scope.py::CURRENT_SCHEMA_HASHES` **in the same commit** with the reason in the message; confirm every golden and every corpus document still validates and no `doc_version` moves

---

## Phase 11: Polish & cross-cutting concerns

- [X] T074 Validate every performance budget and record each in `baseline.md`, exceeded ones **recorded as exceeded**: tool write and `--check` cold in the chroot (≤ 4 s / ≤ 3 s), `postinst` fresh and upgrade (≤ 10 s / ≤ 2 s, minus an empty-postinst baseline), suite per-test ≤ 110 % of T001's figure, package size delta (FR-PERF-001, SC-PERF-001)
- [X] T075 [P] UX consistency pass over `cuems-init-node`'s output, `--check`'s report, `postinst`'s warnings and `cuems-convert-documents` — one reporting idiom, the three pinned strings identical everywhere (Constitution III, FR-UX-001)
- [X] T076 [P] Run `quickstart.md` end to end (build, verify, chroot lifecycle, on-node commands) and correct anything it gets wrong; keep the operator hardware-verification list pointing at nodeconf's ledger entry §5 (D-R20-3)
- [X] T077 Complete `migration-guide.md` (FR-045): all seven story sections, the exit-code table, the handover order and the two unreleased versions, the two announced tag re-cuts, and the **pointer** to nodeconf's hardware-verification ledger entry §5 with the acceptance line (unmask/enable/start `cuems-nodeconf`; `--check` exit 0 after the unmask and after a reboot) — no second copy of the steps (D3)
- [X] T078 [P] Correct the planning documents for findings M1–M9 (FR-046), recorded not silent: `specs/planning/etc-cuems-first-install-execution.md` §3.2 (`node-identity-contract.md` exists; D14's mechanism is nodeconf's, research R7) and §4 (a new M-row block naming each finding); `specs/planning/etc-cuems-first-install.md` D14, §5 practice 1 (`cuems-config-node` was a writer), OPEN-2/OPEN-3/OPEN-4 closed with the answers; delete `specs/planning/011-first-install-specify-prompt.md` per the deletion policy once its clarifications are all recorded in `spec.md`
- [X] T079 [P] Add the feature 011 entry to `CLAUDE.md` "Recent Changes" and correct the Active Technologies bullet from "in progress" to landed, with the suite figure as a range
- [X] T080 Announce the two candidate re-cuts (`cuems-common` `3af31cc`, `cuems-nodeconf` `6c0cca7`) in each repository's changelog entry and in `migration-guide.md`, and confirm `cuems-utils` creates **no** tag in this feature (D27: after 011–014); record in `baseline.md`
- [X] T081 Run the full suite twice, record the range in `baseline.md`, and confirm `ruff check src/ tests/` and `sh -n debian/cuems-utils.postinst debian/cuems-utils.postrm` are clean (SC-QUALITY-001)

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: none
- **Phase 2 (Foundational)**: after Phase 1 — **blocks every story**: T006/T007 make the suite hermetic; T008–T012 give US2/US3/US4 their values; T013/T014 give US3 (and nodeconf 003) `ensure`
- **US1 (Phase 3)**: after Phase 2; independent of every other story. **MVP**
- **US2 (Phase 4)**: after Phase 2; T033's placeholder block is US3's fallback, so US2 and US3 share `debian/cuems-utils.postinst` — write US2's block first, US3's before it in the file
- **US3 (Phase 5)**: after US2 (the pristine documents are the fallback and the generator is the tool's builder). T049 is a gate on `../cuems-nodeconf` feature 003, which depends on T014's commit
- **US4 (Phase 6)**: after US3 (extends the tool)
- **US5 (Phase 7)**: after US3 (needs the write record path to purge); otherwise independent
- **US6 (Phase 8)**: after US3 (shares the CLI); independent of US4/US5
- **US7 (Phase 9)**: after US1 (`control` edits) — T068–T071 may run in parallel with US2–US6
- **Phase 10 (F1)**: any time after Phase 2, as one isolated commit
- **Phase 11 (Polish)**: after everything above; T074 needs a build and the chroot

### Story dependencies

| Story | Depends on | Note |
|---|---|---|
| US1 schemas + handover | Phase 2 | shippable alone; closes three live defects |
| US2 defaults | Phase 2 | leaves a node loadable at the sentinel |
| US3 init-node | US2 | the headline; gates `cuems-common` D14 half (T047/T048) and nodeconf 003 (T049) |
| US4 overlay | US3 | data half landed in Phase 2 |
| US5 purge | US3 | write-record path |
| US6 --check | US3 | shares the CLI |
| US7 hygiene | US1 | `control`; the build task T071 is what every chroot test consumes |

### Within each story

- Tests written and failing before implementation; packaging tests that need a build skip until T071 and are re-run after it
- The three pinned strings (`NOT PROVISIONED`, `modified, kept`, the fixing commands) are constants defined once (T063) and asserted in both the tool's tests and the script tests
- Guide sections written as the story lands

---

## Parallel opportunities

**Phase 2**: T006 ∥ T008 ∥ T013 (three files); T007 after T006; T009 → T010 → T011 → T012 sequential; T014 after T013.

**US1**: T015 ∥ T016 ∥ T017 ∥ T018 (four test files); then T019 ∥ T020 ∥ T021; the three `cuems-common` gates T022/T023/T024 in parallel with each other once that repository's handover commit exists.

**US3**: T035–T042 are eight independent test files/sections; T043 ∥ T045 before T044; T047 ∥ T048 ∥ T049 are gates on two sibling repositories and run whenever those land.

**Across stories**: US7's T065–T070 touch `debian/control`, `README.*` and `changelog` only and can run beside US2–US6; Phase 10 (F1) touches only the six schemas and two tests and can land any time after Phase 2.

```bash
# US3 tests, launched together (different files/sections, all failing first):
Task: "triple coherence and sentinel substitution in tests/integration/test_init_node_triple.py"
Task: "postinst invocation, fallback and timeout in tests/packaging/test_postinst.py"
Task: "chroot: two fresh installs are unique and load in tests/packaging/test_lifecycle_chroot.py"
Task: "ordering premise in tests/packaging/test_ordering_premise.py"
Task: "public API scripts key in tests/support/public_api.py + tests/golden/api/public_api.json"
```

---

## Implementation strategy

### MVP (US1 only)

1. Phase 1 → Phase 2 → Phase 3.
2. **Stop and validate**: build; six schemas under `/etc/cuems` byte-identical; custody transfer in
   both orders leaves the live map intact; the three live defects resolve. Nothing about identity
   has changed and the fleet is already better.

### Incremental delivery

US2 next (a loadable sentinel node), then US3 (the headline: a plain install leaves a unique node),
then US4/US5/US6 in any order, US7 alongside, F1 as its own commit, polish last. Nothing ships
between increments: D27 holds, and the two sibling re-cuts are announced when their gates close.

### The things this strategy must not permit

- A `postinst` that can exit non-zero or hang (T039 guards both).
- A version bump anywhere (T067 guards it).
- A schema edit outside T073's commit (`test_schema_scope` guards it).
- Implementing nodeconf's half in this repository: T049 is a gate; the code is feature 003's.
