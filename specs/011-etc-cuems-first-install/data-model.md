<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Data model — `/etc/cuems` first install (feature 011)

**Phase 1 output.** Entities from `spec.md` "Key Entities", made concrete by `research.md`.
No schema's *shape* changes in this feature (the only `.xsd` edit is R13's annotation), so the
XML documents' models are the existing `cuemsutils.config.*` classes; what is new is the data
*around* them: seed values, overlay, write record, check report, and the package's owned paths.

## 1. Seed values (`system-defaults.toml`)

One TOML document. Tables are `[<schema>.<TypeName>]`; keys are the type's scalar field names
as the descriptor derives them (`spec.derive(TypeKey(schema, TypeName)).fields`); values are
TOML scalars whose type must match the field's adapter (`int` for `xs:integer` kinds, `str`
otherwise; `"auto"` vs `35` for `output_latency_ms`).

| Table | Fields (all required unless noted) | Notes |
|---|---|---|
| `settings.SettingsType` | `conf_path`, `library_path`, `tmp_path`, `database_name`, `show_lock_file`, `editor_url`, `controller_url`, `templates_path`, `controller_interfaces_template`, `node_interfaces_template`, `controller_lock_file` | values from `descriptor._SETTINGS_EXAMPLE_VALUES` as corrected by D15 (e421e31), moved verbatim |
| `settings.NodeConfType` | `osc_dest_host`, `oscquery_ws_port`, `oscquery_osc_port`, `websocket_port`, `load_timeout`, `nodeconf_timeout`, `discovery_timeout`, `mtc_port`, `osc_in_port_base`, `nng_hub_port`, `gradient_osc_port` | **`uuid` and `mac` are absent by rule** — identity is injected, never seeded |
| `settings.VideoPlayerType` | `path`, `args`, `outputs`, `osc_port` (opt), `output_latency_ms` (opt) | D17: optional knobs emitted |
| `settings.AudioPlayerType` | `path`, `args`, `output_latency_ms` (opt) | |
| `settings.AudioMixerType` | `path`, `args` | D16: its own table, no base-class fallback |
| `settings.DmxPlayerType` | `path`, `args`, `output_latency_ms` (opt, integer) | |
| `network_map.NodeType` | `name = "unprovisioned"`, `ip = "0.0.0.0"`, `node_role = "firstrun"` | Q1b; `uuid`/`mac` injected; `adopted`/`online` omitted (nodeconf's) |
| `project_mappings.CuemsProjectMappingsType` | `number_of_nodes = 1`, `default_audio_input = ""`, `default_audio_output = ""`, `default_video_input = ""`, `default_video_output = ""`, `default_dmx_input = ""`, `default_dmx_output = ""` | R12: empty on a fresh node; spelling rule for a non-empty value is `<uuid>_<output id>` |
| `project_mappings.NodeMappingType` | *(none)* | the node entry carries injected `uuid`/`mac` and empty `audio`/`video`/`dmx`; table present so the completeness check has a declaration site |

**Validation rules** (enforced by the generator and by `cuems-init-node` on the merged result):

- V1 every required scalar of every type the three documents use has an entry (missing ⇒
  error naming schema, type, field, file).
- V2 every entry names a declared field of its type (stale ⇒ error naming the key).
- V3 no table names `uuid` or `mac` (⇒ error, "identity is not a default").
- V4 scalar type matches the adapter (⇒ error naming key, expected, found).

## 2. Overlay (`/etc/cuems/defaults.d/*.toml`)

Same table layout and rules V2–V4 as §1 (V1 does not apply: an overlay is partial by nature).
Files are applied in lexical filename order; a later file's key overrides an earlier one's.
Parse error ⇒ error naming file and line; the run writes nothing. Never read by `postinst`.

## 3. Identity

| Field | Type | Source | Rule |
|---|---|---|---|
| `uuid` | uuid4, lowercase, 36 chars (`Uuid.UUID4_REGEX`) | `settings.xml` `Settings/node/uuid` | minted only by `cuemsutils.tools.Uuid()`; `--uuid` must satisfy the regex |
| `mac` | 12 lowercase hex chars | `settings.xml` `Settings/node/mac` | from `--mac`, else the first non-loopback physical interface (`/sys/class/net/*/address`), else the sentinel with a warning |

**Sentinel**: `uuid = 00000000-0000-0000-0000-000000000000`, `mac = 000000000000` — "not
provisioned". A document carrying the sentinel is valid and loadable; a *live* node carrying it
is reported by `--check` (exit 3) and only `postinst`'s degraded fallback may leave it there.

**Where the identity lands** (all written by `cuems-init-node`, all checked by `--check`):

| Document | Element(s) | Form |
|---|---|---|
| `settings.xml` | `Settings/node/uuid`, `Settings/node/mac` | bare |
| `network_map.xml` | `node_list/node[uuid,mac]` — this node's row only | bare; row keyed by MAC in `NodeIndex`, matched by uuid |
| `default_mappings.xml` | `nodes/node[uuid,mac]`; the six `default_*` when non-empty | bare, and compound `<uuid>_<id>` |
| `/etc/avahi/services/cuems.service` | `txt-record uuid=` | read by `--check` only; written by `cuems-nodeconf`, derived from `settings.xml` at every start and role change (R7) |

**State transitions of a node's identity**:

```
absent ──(postinst / init-node: mint)──▶ real ──(--force-new-identity)──▶ real' (re-adopt)
absent ──(postinst fallback)──▶ sentinel ──(init-node)──▶ real
real ──(remove, upgrade, --reinstall, --reset)──▶ real   (unchanged)
real ──(purge)──▶ absent
```

## 4. Pristine defaults (`/usr/share/cuems/defaults/`)

| File | Content | Invariants |
|---|---|---|
| `settings.xml` | §1's settings tables + sentinel identity | byte-identical across builds; `doc_version` = `versioning.CURRENT_VERSION["settings"]`; loads with empty `LoadReport` |
| `network_map.xml` | one `node` row: sentinel uuid/mac, `unprovisioned`, `0.0.0.0`, `firstrun` | same |
| `default_mappings.xml` | §1's mappings root + one node entry at the sentinel, empty device sections, empty `new_nodes` | same |
| `system-defaults.toml` | §1 verbatim | byte-identical to the package-data copy |

`/usr/share/cuems/schemas/*.xsd`: the six bundled schemas, byte-identical to
`src/cuemsutils/xml/schemas/`.

## 5. Live documents (`/etc/cuems/`)

`settings.xml`, `network_map.xml`, `default_mappings.xml` — the three `ConfigManager` loads, plus
the six `.xsd`. Ownership and write rules:

| Path | Created by | Rewritten by | Removed by |
|---|---|---|---|
| `*.xsd` (6) | `postinst`, always | `postinst`, always (upgrade) | `postrm purge` |
| `settings.xml` | `postinst` (via tool) if absent | `cuems-init-node` only | `postrm purge` |
| `network_map.xml` | `postinst` (via tool) if absent | self-entry: `cuems-init-node`; topology rows: `cuems-nodeconf` | `postrm purge` |
| `default_mappings.xml` | `postinst` (via tool) if absent | `cuems-init-node` (until 014) | `postrm purge` |
| `defaults.d/` | operator | operator | never by this package |

## 6. Write record (`/var/lib/cuems-utils/init-node/last-written.json`)

```json
{
  "version": 1,
  "written_at": "2026-09-25T09:05:22Z",
  "documents": {
    "settings": {
      "path": "/etc/cuems/settings.xml",
      "sha256": "…",
      "fields": {"Settings.node.uuid": "…", "Settings.editor_url": "formitgo.local", "…": "…"}
    },
    "network_map": {"path": "…", "sha256": "…", "fields": {"self.uuid": "…", "self.name": "…"}},
    "default_mappings": {"path": "…", "sha256": "…", "fields": {"number_of_nodes": 1, "…": "…"}}
  }
}
```

- `fields` for `network_map` covers **only this node's row** (other rows are never compared).
- Absent file ⇒ "no record" mode (every difference kept and reported).
- Written after a successful triple write, atomically (`write_tree`-style temp + replace).
- Removed by `postrm purge`; never by `remove`.

**Decision per field on a re-run** (FR-027):

| on disk vs record | action |
|---|---|
| equal | recompute from seed + overlay |
| different | keep on-disk value; report "modified, kept" |
| field not in record | take computed value (new upstream field) |
| `--reset` | computed value for every non-identity field; list reverted fields first |

## 7. Check report (`cuems-init-node --check`)

One line per location, then a verdict line and (when non-zero) the fixing command:

```
/etc/cuems/settings.xml: source uuid=2f1c…  mac=…
/etc/cuems/network_map.xml: ok (self-entry present, role=node)
/etc/cuems/default_mappings.xml: MISMATCH (node entry uuid=0367…; no sentinel token)
/etc/avahi/services/cuems.service: ok (2 records agree)
verdict: mismatch (exit 1) — run: cuems-init-node
```

Exit classes and precedence: `3` sentinel in source > `2` any location absent/unreadable >
`1` any mismatch > `0`. `--check --json` emits the same as one JSON object for scripts.

## 8. Owned paths (the purge inventory)

Exactly these, and nothing else, may be removed by `postrm purge`:

```
/etc/cuems/settings.xml            /etc/cuems/settings.xsd
/etc/cuems/network_map.xml         /etc/cuems/network_map.xsd
/etc/cuems/default_mappings.xml    /etc/cuems/project_mappings.xsd
                                   /etc/cuems/project_settings.xsd
                                   /etc/cuems/script.xsd
                                   /etc/cuems/hardware_outputs.xsd
/var/lib/cuems-utils/init-node/last-written.json
/var/lib/cuems-utils/init-node/    (rmdir)
/var/lib/cuems-utils/              (rmdir --ignore-fail-on-non-empty)
/etc/cuems/                        (rmdir --ignore-fail-on-non-empty)
```

## 9. Package relations

| Package | Relation | Value | Why |
|---|---|---|---|
| `cuems-utils` | `Breaks` | `cuems-common (<< 1.3.0-23~)` | old `cuems-common` records the two `/etc/cuems/network_map.*` paths as conffiles (R3) |
| `cuems-utils` | `Replaces` | *(none)* | no manifest overlap under `/etc` (D5) |
| `cuems-common 1.3.0-23` | `Depends` | `cuems-utils (>= 0.1.0rc16)` | already present; rc16 is the first build that ships the schemas |
