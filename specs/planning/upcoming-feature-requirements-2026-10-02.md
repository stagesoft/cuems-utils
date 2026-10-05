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

## 0. Closed and newly opened — the 2026-10-05 consumer round

Two sibling gates have landed and reported. This section is the index; the detail is below.

| Item | State |
|---|---|
| **`cuems-editor` UR-5** — no public config ingestion (§1) | ✅ **CLOSED** by 014's `ConfigManager.from_json`, pinned to `429f8d2` in that repository's own report. Its T059 `xfail(strict=True)` is **removed** and the suite is **161 passed / 2 skipped** (was 154/2/1 at the branch point). §1 below is now history, kept because it is the statement of the requirement the call was built against |
| **`cuems-editor` UR-6** — `conf_path`/`project_path` refuse a file a first save would create | 🔴 **NEW, open** — §8. Found *by* closing UR-5, which is the usual shape: the ingestion works, and now the write target is the thing missing |
| **`cuems-editor` UR-4** — a duplicate identity carries no structured identity (§2) | Still open, unchanged |
| **The descriptor flattens a union into a one-value enumeration** (§5) | Still open, unchanged — still not 014's |
| **013's reshape defeats F3's `settings` 1 → 2 conversion** | 🔴 **NEW, and it blocks the tag.** Not a requirement — a **defect**, with its own record: [`settings-reshape-defeats-f3-conversion-defect.md`](settings-reshape-defeats-f3-conversion-defect.md). Found by `cuems-nodeconf`'s gate, verified here, and narrower than that report states |

## 1. Blocking a landed consumer task — `cuems-editor` UR-5 — ✅ CLOSED 2026-10-05

> **✅ CLOSED 2026-10-05 by feature 014**, `429f8d2`. `ConfigManager.from_json(SchemaName, payload)`
> is the call this section asked for, and `cuems-editor` has taken it up at `365d57f` / `22093fd`.
> The requirement text below is left as written, because it is what the call was specified against;
> the follow-on gap it exposed is §8.
>
> **✅ ASSIGNED 2026-10-02: this lands in feature `014`.** Reviewed against 014's work and folded
> into its plan as §9 — `specs/014-xs-boolean-and-media-elements/plan.md`, decision 10.
> The reason it belongs there rather than in a later feature is a measured correlation: **the only
> configuration domain that needs typed ingestion is `network_map`, which is also the only one
> carrying a `cms:BoolType` and the only one 014 retypes.** Building the ingestion first would
> specify a brand-new public API, and the descriptor-driven form that feeds it, against a field
> whose type 014 then changes — two halves of one round trip, both migrating before either shipped.
> The detail below stays as the statement of the requirement; §9 is now the authority on the work.

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

## 3. The release gate now forbids the release — the version move is not a standalone task

> **➡ MIGRATED 2026-10-03 to `specs/planning/deprecated-surface-removal-v0-1-1.md` §3.** That document is now the home for this
> requirement, because the task it constrains moved there with it: 010's T060 is **R11** there.
> Two things were added on the way: the `dpkg --compare-versions` table showing the bound admits
> `0.1.0rc17` — so deleting the surface at any `rc` defeats the gate — and therefore that the
> deletions and the version move are one indivisible step. The statement below is unchanged and
> kept as the record of where it was first worked out.

**Measured 2026-10-02.** With `cuems-editor` and `cuems-engine` closing the last two edges
(010 T037b/T038), **five** sibling `debian/control` files carry `cuems-utils (<< 0.1.1~)`:
`cuems-common`, `cuems-engine`, `cuems-editor`, `cuems-nodeconf`, `cuems-power-bridge`. Each also
pins `>=0.1.0rc16,<0.1.1` in `pyproject.toml`.

010's **T060** — now **R11** — moves this library's `__version__` to the release
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
| **The descriptor flattens a union type into an enumeration of one.** Measured 2026-10-02: `network_map`'s `NodeType/uuid` comes back as `xsd_type='NodeUuidType'`, `enum_values=('00000000-0000-0000-0000-000000000000',)` — 012's union surfacing as a dropdown containing only the NOT PROVISIONED sentinel, where a uuid field belongs | **Open, and deliberately not 014's.** It is the same family as the boolean finding 014 fixes (a type the descriptor flattens into the wrong widget), but the boolean case is in scope only because 014 retypes that field anyway; this one needs `xml/descriptor.py` to learn about unions, with no other driver in 014. Found by whoever builds the descriptor-driven forms — see the gate's §9.5 |

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

---

## 8. `cuems-editor` UR-6 — the write target a first save needs does not exist

**Report**: `../cuems-editor/specs/001-cuems-utils-migration/upstream-reports/UR-6-config-path-helpers-require-existence.md`,
2026-10-05, measured against this repository at `b8b44e7` (i.e. *including* UR-5's fix).
**Verified here the same day**, all three of its claims, by test rather than by reading.

**The gap.** `ConfigBase.conf_path(file_name)` and `ConfigManager.project_path(project_uname,
file_name)` both check `path.exists` and raise `FileNotFoundError` — and every `save_*` accessor
defaults its `path` argument to exactly that call. So there is **no public way to obtain the
canonical write target for a configuration file that does not exist yet**, which is the ordinary
state of a project's `settings.xml`/`mappings.xml`: `load_project_settings` explicitly tolerates it
(*"Keeping default settings"*).

**Measured, 2026-10-05:**

| Claim | Result |
|---|---|
| `conf_path('never_existed.xml')` | `FileNotFoundError: Configuration file …/never_existed.xml not found` |
| `project_path('some_project', 'settings.xml')` | `FileNotFoundError: Project file …/projects/some_project/settings.xml not found` |
| `document.save(<path that has never existed>)` | **writes it correctly** — 1901 bytes |
| `document.save(<path whose parent directory is absent>)` | `FileNotFoundError` on the temp file — a separate and correct matter |

**So the limitation is entirely in the two helpers, not in `.save()`.** That is the finding, and it
is what makes the fix small.

⚠ **The strongest evidence is this repository's own test suite**, which the report found and quoted:
`tests/integration/test_config_manager_save_accessors.py:59-65` documents the limitation in a
docstring and then works around it with
`monkeypatch.setattr(config_manager, "project_path", _project_path)` — **replacing the method**,
because there is no supported way to get a tolerant write target. A library whose own tests
monkeypatch a public method to exercise a public save path has named the gap itself; the consumer
merely read it.

**What the consumer did.** Nothing hand-rolled: it declines to duplicate the
`library_path/projects/<uname>/<file>` convention this library owns, calls the real `project_path`,
and lets the error surface. `cuems-editor`'s
`test_config_save_of_project_settings_fails_before_the_file_exists_pending_ur6` pins today's
behaviour so it flips to a round-trip assertion the day this lands, and
`test_config_save_of_project_settings_persists_once_the_file_exists` proves the rest of its wiring
already works. That is the right posture and it is the second time that repository has taken it
(UR-5's `xfail(strict=True)` was the first).

**Two candidate shapes**, from the report, with this repository's reading of each:

| Shape | Reading |
|---|---|
| `conf_path(file_name, must_exist=False)` / `project_path(…, must_exist=False)` | **Preferred.** Smallest surface, keeps one path convention in one place, and is purely additive — the default stays `True`, so `load_*`'s reliance on a missing file being reported as missing is untouched. A keyword-only parameter, so no positional call site can acquire it by accident |
| One call that ingests, resolves the target and persists | Larger, and it re-opens the installer question 014 settled deliberately (plan.md §9.3: `from_json` returns the object; `save_*` writes what the manager holds). It would also have to answer "which project" for two of the four domains, which is the consumer's own lookup |

**Non-negotiable either way, and the report says so first**: this is an **addition**, not a
loosening. `conf_path`/`project_path` must keep refusing a missing file for every existing caller.

**Carry it with the test fix.** Whichever feature takes this should also retire
`test_config_manager_save_accessors.py`'s monkeypatch, because that workaround *is* the defect's
in-repository footprint — leaving it would keep a passing test that documents a gap as permanent.
