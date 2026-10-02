<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# What the next features in this repository must carry — measured 2026-10-02

Inbound requirements for **feature 014** and for whichever feature **cuts the release**, collected
after `cuems-editor`'s feature `001-cuems-utils-migration` landed on its `feat/xml-refactor`
(`bf57d95`, 62 of 63 tasks). Everything here was measured against this repository at `6213b16` and
that one at `bf57d95`; nothing is carried forward from an earlier reading.

**This is a planning document, not a spec.** Each item names the consumer evidence it comes from, so
a later `/speckit.specify` pass can turn it into an FR without re-deriving the measurement. Delete
it once every row below is either in a feature's `spec.md` or recorded as declined.

---

## 1. Blocking a landed consumer task — `cuems-editor` UR-5

**One public ingestion per configuration domain, symmetric with `CuemsScript.from_json`.**

This is the only item here that holds another repository's task open. `cuems-editor`'s T059 is 1 of
63 and is not implementable without it; its test is `xfail(strict=True)` and turns **XPASS** the day
the call exists, so the consumer needs no edit to pick it up — only a re-run.

| | |
|---|---|
| Report | `../cuems-editor/specs/001-cuems-utils-migration/upstream-reports/UR-5-no-public-config-json-ingestion.md` |
| Consumer need | the `config_save` websocket action (its FR-045): a client edits a document built from `get_schema_descriptor`'s `instance` and sends it back to be persisted |
| What exists | `ConfigManager.save_settings` / `save_network_map` / `save_project_mappings` / `save_project_settings` (feature 008) — each writes **the object the `ConfigManager` already holds** |
| What is missing | anything public that turns a wire-shaped `dict` into that object |
| Shape asked for | `ConfigManager.from_json(SchemaName, payload)` returning the root object `save_*` writes, or `ConfigManager.set_document(SchemaName, payload)` decoding through the same mapper and adapters as `load_*` |

**Three near-misses, so a future pass does not re-propose them:**

- `ConfigDict.from_decoded` is on an internal class (`cuemsutils.config.base`), takes the **decoded**
  shape rather than the wire shape, and stores values verbatim by design. For `network_map` the
  adapters run *before* it, in the mapper, so a wire `"node_role": "node"` would stay a `str` where
  `save_network_map` expects a `NodeRole`. Publishing it would publish the wrong half.
- the `network_map` property setter accepts a `dict`, and then `save_network_map` calls `.save` on
  it.
- `validate_config_document` (013, FR-036) validates a **path**. It is the right surface for
  *checking* a document and the wrong one for *ingesting* a payload. These two are easy to conflate
  because both closed a report numbered UR-5 — see §4.

**Constraint from 007, worth restating**: `network_map` is the one configuration schema whose decode
runs the adapter table (`SchemaRegistry.runs_adapter_table`). An ingestion path must respect that
per-schema asymmetry rather than normalising it, or it silently retires the measured guarantee
feature 007 established for the other four.

## 2. A consumer is parsing this library's prose — `cuems-editor` UR-4

**Put the colliding identities on the exception.**

| | |
|---|---|
| Report | `../cuems-editor/specs/001-cuems-utils-migration/upstream-reports/UR-4-collision-identity-not-structured.md` |
| Observed | `ConfigManager.load_network_map()` on a map carrying one identity on two rows raises `ValidationError` with `violation = None` and `__cause__` a plain `ValueError`. The identities and their MACs exist only inside `check_node_identities_unique`'s sentence (`xml/validators.py`). `cuemsutils.errors.node_identity_collision_message` recognises the case and also returns a string |
| Consumer need | its `network_map_error` frame sends `{"kind": "duplicate_identity", "identity": "<string>", "file": "<path>"}` and logs once per **distinct** identity. Both need the identity as data |
| Workaround now shipping | `../cuems-editor/src/cuemseditor/node_reads.py`, `collided_identity` — one anchored regex over our sentence, falling back to `"identity": ""` if it ever changes |
| Shape asked for | a `Violation` with `location=(identity, "uuid")`, or an attribute on a dedicated exception subclass |

**Why this is worth a requirement rather than a shrug.** The workaround is correct and degrades
safely, but it makes a sentence in `validators.py` a load-bearing interface that no test on either
side declares. This library can reword it in a patch release and break a consumer's error reporting
with no failing test anywhere. That is the same class of fault as the `<< 0.1.1~` bound in §3: a
cross-repository contract carried by one side only.

## 3. The release gate now forbids the release — T060 is not a standalone task

**Measured 2026-10-02.** With `cuems-editor` and `cuems-engine` closing the last two edges
(010 T037b/T038), **five** sibling `debian/control` files carry `cuems-utils (<< 0.1.1~)`:
`cuems-common`, `cuems-engine`, `cuems-editor`, `cuems-nodeconf`, `cuems-power-bridge`. Each also
pins `>=0.1.0rc16,<0.1.1` in `pyproject.toml`.

010's **T060** moves this library's `__version__` to the release
`_deprecation.REMOVAL_RELEASE` has promised since feature 006 — `v0.1.1`. `dpkg` refuses `0.1.1`
against every one of those bounds.

**That is the gate working, not a defect.** `0.1.1` *is* the release that deletes the surface a
pre-migration consumer would import, and the bound exists to stop exactly that pairing. The
requirement is about **atomicity**:

> The version move and the re-bound of five sibling packages are **one step**. A library at `0.1.1`
> beside five packages bounded `<< 0.1.1~` is an ecosystem that will not install at all, and the
> failure surfaces at `dpkg` time on a node.

What each sibling needs is the same two lines raised in lockstep (`>= 0.1.1`, `<< 0.2.0~` if the
next break is minor) **plus** the `pyproject.toml` bound — which `dpkg` does not enforce but
`pip`/`poetry` resolves. `cuems-frontend` has no package and uses the payload handshake instead
(010 FR-108); the editor now sends `payload_version: 1` as its first frame, so that half exists.

**Record it in whichever feature cuts the release, not only here.** This feature has already found
twice that a cross-repository requirement living in one side's task list gets built on one side
(FR-UX-002's missing consumer; T076's upper bound).

## 4. One naming rule, because it has already caused a wrong reading

**Upstream report numbers are per repository and collide.** `cuems-engine`'s UR-5 (the `validate`
deprecation advice, closed by 013 FR-036) and `cuems-editor`'s UR-5 (§1 above, open) are different
findings with the same number. 010's `migration-guide.md` §5b carried "UR-1 and UR-5 are open" after
013 had closed both of the engine's, which read as if §1 were already done.

Cite them as **`<repo> UR-<n>`**, never as a bare UR number, in specs, tasks, commit messages and
`CLAUDE.md`.

## 5. Already settled, carried so nobody re-opens it

| Item | Disposition |
|---|---|
| `to_wire()` projects a model default for an optional element the document omitted (`opacity: 100` on a `<video>` cue with no `<opacity>`) | **Not a defect.** Raised as `cuems-editor` UR-3, **withdrawn** on a maintainer ruling 2026-10-02: `opacity` is a `script.xsd` field of `VideoCue`, so a document omitting it carries the default and projecting it is the library doing its work. The consumer sanctioned it as payload delta (d). ⚠️ It is a **general** property of the projection, not a fact about `opacity` — any consumer diffing a payload against the file it came from will meet it on some other field. Worth stating once in the public-API documentation rather than per field |
| `FR-044`'s "fold the repair tool's rewriting pass into `cuems-convert-documents`" | **Superseded by a better answer** the consumer found: the tool writes no script at all. It repairs the DB and lists `NEEDS_SAVE`. Do not re-propose the fold — see 010 `migration-guide.md` §4d and the note on 010 T028 |
| `if 'Cue' in item: cue_data = item['Cue']`, prescribed by 013's own migration guide §4 | **Withdrawn, corrected in place 2026-10-02.** It walks the wire dict to reach an object-level result (010 FR-013b). The landed form matches on cue identity: `isinstance(cue, (AudioCue, VideoCue, DmxCue, MediaCue))`, with the bare `MediaCue` present because an unknown `class` decodes to it |
| `xml/XmlBuilder.py` (frozen legacy) still emits per-class element names | Already scheduled for `v0.1.1` by 013; it has no live caller. Nothing new here |

## 6. 014's own inbound items, as the consumers measure them

Not new requirements — confirmations that 014's stated scope is still the scope, re-measured today.

| Site | Reads | Note |
|---|---|---|
| `../cuems-editor/src/cuemseditor/cli.py:59` | `default_mappings.xml` through `ProjectMappings` | still the only `cuemsutils.xml`-side import that repository carries, deliberately deferred to 014 in its own tasks (its T063 keeps it in Complexity Tracking) rather than omitted |
| `../cuems-editor/src/cuemseditor/CuemsWsUser.py` `config_save` | refuses `SchemaName.HARDWARE_OUTPUTS` with *"no model bindings"* | if 014 gives `hardware_outputs` a writable model, that refusal becomes a `save_*` call. Its `schema_descriptor` already serves it: all six schemas answer, `hardware_outputs` with 3 types |
| `../cuems-frontend` | the port inventory, and `sequence.component.ts:294-304`'s four cue-type unions | flow 05 has not started and is the last consumer flow. 013 landed, which was its stated precondition |

## 7. A field note from measuring this, not a requirement

This development box's `/etc/cuems/settings.xml` is in the **pre-013 device shape**, so
`ConfigManager()` refuses it:

```
cuemsutils.errors.SchemaError: settings document /etc/cuems/settings.xml is in the pre-013 device
shape (<videoplayer>/<audioplayer>/<dmxplayer> on <node>). Run `cuems-reshape-devices` to migrate it.
```

The diagnostic is exactly right and names its own remedy — worth recording as evidence that 013's
refusal path reads well in the one place it matters, and as a reminder that any tool run on this box
against the host configuration (rather than a fixture `CUEMS_CONF_PATH`) needs that migration first.
