<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# `/etc/cuems` first install — schemas, system defaults, and node identity

**Status**: design settled, implementation not started
**Measured**: 2026-09-21, against `feat/xml-refactor`, `debian/bookworm`, and the two
production machines `10.16.10.2` / `10.16.10.3` (§2.6)
**Decisions taken**: 2026-09-21, seventeen of them, recorded in §3 with their reasoning
**Extended**: 2026-09-23 — §7 (the sixth schema, renamed) and §8 (the splitting basis,
writer responsibilities and duplication flags)
**Applies to**: `cuems-utils` (owner), `cuems-common` (hands over two paths, gains one contract)

Paths are relative to this repository's root; `../<repo>` is a sibling checkout.

---

## 1. The problem

A fresh node cannot start. `ConfigManager` needs three XML documents in `/etc/cuems`, **no
package ships any of them in a usable state**, and the six `.xsd` files that define them live
only inside the venv — except one, which `cuems-common` carries as a hand-maintained copy that
has already drifted once.

Two questions govern the design:

1. **The `.xsd` is the single source of truth, so where do the default `.xml` files come from
   without becoming a second source of truth?**
2. **The node's uuid appears in four places. Which one is the source, and who is allowed to
   write it?**

---

## 2. Measured state

### 2.1 What the packages ship today

| | |
|---|---|
| `cuems-utils` `.deb` (`debian/bookworm`) | `dh_virtualenv --python /usr/bin/python3 --install-suffix cuems --use-system-packages`. **No `debian/install`, nothing under `/etc`.** The six XSDs ride inside the venv at `/usr/lib/cuems/lib/python3.11/site-packages/cuemsutils/xml/schemas/` |
| Install-time work today | dh-virtualenv's autoscript only: it re-hardlinks `/usr/bin/python3.11` into the venv, deriving the version from the venv's own `lib/python3.11` dirname. Custom `postinst` code therefore belongs **after** `#DEBHELPER#` |
| `cuems-common` `.deb` | Ships `/etc/cuems/network_map.xml` (an empty `<node_list/>` stub) and `/etc/cuems/network_map.xsd` (**byte-identical mirror**, guarded by `tests/test_schema_mirror.py`, which *skips* when the sibling checkout is absent) |
| `settings.xml`, `settings.xsd` | Shipped by nobody. `cuems-common` already classified this as provenance class **D — hand-placed, authority elsewhere** (`../cuems-common/dev/planning/systemd-service-split-architecture.md` §7.1, §7.3-①) |

### 2.2 A first install needs three documents, and **all three are uuid-coupled**

Traced through `ConfigManager`, in load order:

| # | File | Required by | Generator today |
|---|---|---|---|
| 1 | `settings.xml` | `ConfigBase.__init__` → `load_base_settings` — **unconditional, even with `load_all=False`** | ✅ `descriptor.generate_settings_example()` |
| 2 | `network_map.xml` | `load_network_map()` → the `node_network_map` setter | ❌ trivial stub today |
| 3 | `default_mappings.xml` | `load_net_and_node_mappings()` | ❌ written at runtime by `cuems-display-setup` |

**Measured 2026-09-21** — the shipped-defaults triple (generated `settings.xml` + `cuems-common`'s
`<node_list/>` map + a corpus `default_mappings.xml`):

```
ConfigManager(load_all=True)
  -> ValueError: Node with uuid 00000000-0000-0000-0000-000000000000 not found
```

So documents **2 and 3 both** must contain an entry for *this* node's uuid. An earlier draft of
this document claimed only 1 and 3 were coupled and that a fresh node would be "loadable but
anonymous". **Both claims were wrong**, and the correction is what produced §5.

`set_dir_hierarchy()` then creates `library_path/{projects,media/waveforms,media/thumbnails}`,
their `trash/` counterparts and `tmp_path` — driven by values *inside* `settings.xml`, so
directory creation comes free once that file exists.

### 2.3 `/etc/cuems` is a shared directory

At least five packages, ~20 paths:

| Owner | Paths |
|---|---|
| `cuems-common` (conffiles) | `ap.conf`, `gpu-pin.conf`, `cluster-poweroff.conf`, `network_map.xml`, `network_map.xsd`, `ssh/cuems-org.pub`, two `.example` files |
| `cuems-power-bridge` (runtime) | `power-bridge.conf`, **`power-bridge.key`** (a private SSH key), `power-bridge.key.pub`, `project_id` |
| `cuems-common` helpers (runtime) | `master.ip`, `cluster.conf`, `display.conf`, `default_mappings.xml` |
| `cuems-engine`, `cuems-nodeconf` (readers/writers) | `settings.xml`, `network_map.xml` |

`network_map.xml.dpkg-dist` and `.dpkg-old` appear in `cuems-common`'s tree — **the
conffile-prompt problem is already happening in the field**, on a file `cuems-nodeconf` writes.

### 2.4 Live defects this design closes

- `../cuems-common/usr/lib/cuems/bin/cuems-display-setup:30` validates against
  `/etc/cuems/project_mappings.xsd`, **which no package ships**.
- `../cuems-common/docs/latency-tuning.md:89` tells operators to load `/etc/cuems/settings.xsd`
  — same.
- `ConfigBase.__init__` requires `settings.xml` unconditionally — the precondition blocking the
  `cuems-power-bridge` migration (feature 010, US11, T071(d)(i)).
- **`cuems-common`'s shipped empty `network_map.xml` cannot support `ConfigManager(load_all=True)`
  on any node** (§2.2). Working clusters today rely on hand-maintained maps, because
  `cuems-nodeconf` is disabled cluster-wide.

### 2.5 The constraint that dominates the packaging decisions

`cuems-utils` is the **base dependency of the whole stack** — unavoidable, installed first.
Debian's failure semantics make this asymmetric: a non-zero exit from its `postinst` leaves the
package half-configured and **every dependent package fails to configure**. One bad exit here
blocks the install of every CUEMS component.

Everything in §3 that touches `postinst` is weighed against that.

### 2.6 Production audit — two machines, 2026-09-21

Read-only inspection of `10.16.10.2` and `10.16.10.3` (both `cuems-admin@`, both Debian 12,
both reporting hostname `controller` — two separate installs, not a controller/node pair).
Both are **due for the xml-refactor**, so their files are evidence of *improper* values, not an
authority to copy.

| | host `.2` | host `.3` |
|---|---|---|
| `cuems-utils` | `0.1.0rc14` | `0.1.0rc12` (current is rc16) |
| `cuems-common` | `1.3.0-17` | `1.3.0-21` (neither ≥ `-22`, so `cuems-migrate-network-map` has never run) |
| cluster shape | single node | **two nodes** (`number_of_nodes` 2) |
| `cuems-nodeconf` | **masked** | **active/running** |
| video connectors | `DP-2`, `HDMI-A-2` connected | only `HDMI-A-1` connected |

**Every `.xsd` on both machines is stale, and the two disagree with each other** — the drift D4
exists to end, measured in the field:

| schema | canonical | `.2` | `.3` |
|---|---|---|---|
| `network_map.xsd` | 3652 | **2471** | **3119** |
| `project_mappings.xsd` | 7701 | **5800** | **7301** |
| `script.xsd` | 19408 | **15464** | **15986** |
| `settings.xsd` | 8717 | **6195** | **6195** |

`.2` also carries `network_map.xsd.dpkg-dist`: the conffile prompt fired, the admin kept the
older copy, dpkg parked the new one beside it. **D5's argument, already having happened.**

Validated against the canonical schemas:

```
.2/.3  settings.xml           VALID
.2/.3  default_mappings.xml   VALID
.2/.3  network_map.xml        INVALID -- both still carry <node_type>NodeType.master|slave
```

**Sequencing consequence for feature 010**: the `cuems-power-bridge` defect (US11) is *not yet
live* on these machines, because their maps still carry the retired vocabulary. **The
conversion is what triggers it.**

Two smaller findings: `.3`'s `master.ip` reads `169.254.9.194`, which is **`.2`'s** controller
address (both files dated Sep 2025, never updated); and node identity is not uuid4 — the two
controllers' uuids differ *only* in the MAC-derived node field (`a3811d78-099f-11f0-a075-<mac>`,
a uuid1 cloned and hand-edited), while `.3`'s `node01` is a uuid5. **Three conventions in
production, none of them uuid4** — which D13 assumes. See OPEN-5.

---

## 3. The decisions

### D1 — The XSD is SSOT for **structure**, never for **values**

Two independent reasons, either sufficient:

1. **`xs:default` on an element only fires when the element is present-but-empty, never when
   absent.** (Attributes differ; these schemas are element-only.) It cannot generate a file.
2. `specs/agreements/schema-evolution-convention.md` rule 2 already rules on this: *"The default
   belongs in the model class's `DECLARED_DEFAULTS`, next to the field."*

The duplication to worry about was never XSD-vs-XML values. It is these three axes:

| Axis | Status |
|---|---|
| XSD structure ↔ default-XML structure | **Already closed.** The generator takes field *names* from the descriptor and raises `RuntimeError: … has no example value … — add one` when the XSD gains a required field the values table does not name. FR-034 rests on this |
| XSD ↔ values | **Not duplication.** The XSD never held values. Every settings field is deliberately `Unset` at the model layer, gated by the `*.config.json` goldens (T042/T043a) |
| Canonical XSD ↔ its `/etc/cuems` copy | **The real one.** Drifted once already (T051: `cuems-common`'s copy predated feature 007, wrong `NodeDictType` spelling, still carried `PutType`). D4 closes it |

`descriptor._instance_for` cannot substitute for the values table: it seeds from model-layer
defaults and substitutes `None` wherever the model says `Unset` — which is every settings field.
It guarantees *structural* completeness only.

### D2 — Defaults are **generated at package build**, from the SSOT

No committed default `.xml`. `debian/rules`, after `dh_virtualenv`, runs the generator with the
just-built venv's interpreter and installs the output. Deterministic: the settings generator
emits fixed placeholders, not a fresh uuid4 (unlike `generate_script_example`, unused here), so
the build stays reproducible.

### D3 — The **shipped** documents carry placeholders; the **live** ones are specialized

```xml
<uuid>00000000-0000-0000-0000-000000000000</uuid>   <!-- reserved sentinel -->
<mac>000000000000</mac>                             <!-- reserved sentinel -->
<outputs>2</outputs>                                <!-- hardware guess -->
<oscquery_ws_port>9190</oscquery_ws_port>           <!-- true default -->
```

The pristine copies in `/usr/share` always carry the sentinel. What lands in `/etc/cuems` does
not — see D13.

### D4 — `cuems-utils` ships **all six** `.xsd` to `/etc/cuems`, as real files

The SSOT owns its own artifacts. `cuems-common` drops its mirror and
`tests/test_schema_mirror.py` retires with it — axis 3 closed by construction rather than by a
test that skips when a sibling checkout is missing.

**Why `/etc/cuems` and not the FHS-correct `/usr/share`:** every document this library writes
carries a *relative* schema reference —

```xml
<cms:CuemsSettings … xsi:schemaLocation="https://stagelab.coop/cuems/ settings.xsd" doc_version="1">
```

— a bare filename that only resolves beside the XML. The library ignores it (it uses its bundled
copies) but `xmllint`, the editor and an operator do not. Real files rather than symlinks into
the venv, because a venv path embeds `python3.11` and breaks on an interpreter bump. Six files,
42 KB. There are **no `xs:include`/`xs:import` between them**, so they ship independently.

**Handover, because `dpkg -i` aborts on an overlapping path:**

```
cuems-utils:   Breaks:   cuems-common (<< <version that drops it>)
               Replaces: cuems-common (<< <version that drops it>)
cuems-common:  drops etc/cuems/network_map.xsd and etc/cuems/network_map.xml
               from debian/install; Depends: cuems-utils (>= <version that ships them>)
```

### D5 — Files under `/etc/cuems` are **never conffiles**; `postinst` installs if absent

Shipped references live in `/usr/share/cuems/defaults/`, inside the package manifest, so
`dpkg -V` verifies them and a drifted live file can be diffed against pristine. The `/etc` copy
is created by `postinst` and stays outside dpkg's control.

This is the pattern `cuems-common` already uses for `avahi-daemon.conf` and `dhcpd.conf`, and it
is what makes **upgrade and `--reinstall` preserve machine identity**: the copy is conditional on
the target being absent, so neither ever touches an existing file.

**Why not a conffile.** The mechanism does the opposite of what it promises here:

| Local state | Upstream changed? | dpkg does |
|---|---|---|
| unmodified | yes | replaces silently |
| modified | no | keeps |
| modified | yes | **prompts** — or non-interactively keeps yours and drops `.dpkg-dist` |

A conffile an admin has touched **stops receiving upstream values permanently** — including
fields added in later releases. That is drift wearing a preservation costume, plus a prompt on
every upgrade where both sides moved.

### D6 — Purge removes **only what this package placed**

`/etc/cuems` is shared (§2.3). An `rm -rf` from a *library*'s `postrm` would destroy
`cuems-common`'s conffiles, the cluster identity and a private SSH key — and Debian policy
forbids removing files a package did not create.

```sh
# debian/cuems-utils.postrm
case "$1" in purge)
    for f in settings.xml network_map.xml default_mappings.xml \
             network_map.xsd settings.xsd script.xsd \
             project_mappings.xsd project_settings.xsd outputs.xsd; do
        rm -f "/etc/cuems/$f"
    done
    rmdir --ignore-fail-on-non-empty /etc/cuems || true
esac
```

Whichever CUEMS package is purged last empties the directory and removes it. **Purging the whole
stack erases `/etc/cuems` completely; purging one package never damages another.** `remove` (as
opposed to `purge`) touches nothing, so identity survives a package removal.

**Purge destroys node identity, by design.** That is what purge means. See D13's edge cases.

### D7 — The values table is **promoted** out of the descriptor

`descriptor._SETTINGS_EXAMPLE_VALUES` is documented as *illustrative* values for an example
document. Under D2 it becomes a shipped production artifact, so it moves to a named home and
becomes data (D9).

### D8 — Nothing converts at install; conversion happens **on read**

`postinst` never rewrites an existing document. When a shipped default gains a field a live file
lacks, feature 008's machinery covers it: the schema-evolution convention makes the new element
optional with a model-layer default, so an older document still loads, and the strict load path
converts in memory with the file on disk untouched. Batch conversion stays operator-triggered
(`cuems-convert-documents`).

### D9 — Seed values become **TOML data** with a drop-in overlay

```
/usr/share/cuems/defaults/system-defaults.toml   shipped, NOT a conffile, always
                                                 overwritten -> upstream stays current
/etc/cuems/defaults.d/*.toml                     operator's, never shipped, dpkg never
                                                 touches -> tweaks always survive, no prompt
```

The systemd/sysctl/logrotate pattern. It beats a conffile on **both** axes: upstream values are
never stale *and* site tweaks are never clobbered — a conffile can only give one.

TOML because `tomllib` is stdlib in 3.11 (read-only is all we need), it preserves the int/string
distinction `output_latency_ms` genuinely needs (`35` vs `"auto"`), and it takes comments.

The completeness guarantee survives the move intact: the generator still raises when a required
field has no entry, whatever file the entries came from. The XSD keeps driving structure.

### D10 — `DECLARED_DEFAULTS` stays in Python

Measured 2026-09-21: **every entry across all 15 files is either `Unset` (all document fields,
without exception) or `_`-prefixed runtime scaffolding** — `_player: None`,
`_start_mtc: lambda: CTimecode(framerate=25)`, `_go_thread: None`, `_end_reached: False`. There
is not one operator-relevant value in the table. It is a *field declaration* table that shares a
name with the concept, and externalizing it would move thread handles into TOML.

As the schema-evolution convention accumulates real defaults there (its worked example is
`"gradient_osc_port": 7100`), those stay in Python too, because a decode default is
**file-format semantics, not site policy**:

1. Documents move between machines — the editor writes scripts the engine reads, nodeconf writes
   maps the bridge reads. A host-local decode default means one document decodes two ways in one
   cluster.
2. Feature 008's repair path substitutes "the descriptor's default" and records it in
   `LoadReport`. Host-local defaults make repair non-reproducible across nodes.
3. The `*.config.json` goldens pin decode behaviour.

### D11 — The overlay is applied by `cuems-init-node`, not by `postinst`

The overlay is operator-authored input. Under §2.5, reading it in the base package's `postinst`
means a TOML typo can block the install of the entire stack. Keeping it out has three further
benefits: one generation code path at build, no duplicate-output problem, and a malformed
overlay fails **loudly in a command an operator just ran** instead of silently during an upgrade.

The "extra step" costs nothing, because identity assignment (D12) is mandatory anyway — the
overlay folds into a step that already had to happen.

### D12 — `cuems-init-node` owns node coherence, atomically

```
cuems-init-node [--uuid U] [--mac M] [--overlay /etc/cuems/defaults.d] [--check]
  reads   pristine defaults + overlay + existing /etc/cuems/*.xml
  assigns identity: preserved if already real, minted if the sentinel, or taken from --uuid
  writes  settings.xml, default_mappings.xml, network_map.xml   <- one atomic set
  refuses to leave a half-specialized state on any failure
```

**Re-run policy: identity is preserved, everything else re-applied.** This matches the upgrade
policy and makes the tool safe to re-run from provisioning when a site overlay changes.
Reassignment requires an explicit `--force-new-identity`, which warns loudly.

### D13 — `postinst` mints the uuid4 if, and only if, there is none

A plain `apt install` leaves a node that **loads and is unique**. `postinst` runs
`cuems-init-node --no-overlay`: no operator input is read, so the malformed-overlay failure class
is absent by construction, and it falls back to copying the pristine placeholder if anything goes
wrong.

**A previously-minted uuid4 always persists.** The rule is mint-if-absent, never re-mint:

| Situation | `/etc/cuems/settings.xml` | Outcome |
|---|---|---|
| Fresh install | absent | uuid4 minted, coherent triple written |
| Upgrade | present, real uuid | **untouched** — D5's install-if-absent never fires |
| `--reinstall` | present, real uuid | **untouched** — same |
| `remove` then install | present (remove keeps `/etc`) | **untouched** |
| `purge` then install | absent (D6 removed it) | new uuid minted — identity intentionally destroyed by the purge |
| Pre-existing hand-placed file | present, real uuid | **untouched** |
| Present but carrying the **sentinel** | present, all-zeros | left alone by `postinst`; `--check` reports it; `init-node` fixes it. `postinst` never modifies an existing file, and that invariant is worth more than auto-repairing a rare hand-copied case |

### D14 — The Avahi TXT `uuid` stays `cuems-common`'s, and **must derive from `settings.xml`**

`cuems-common` keeps ownership of `/etc/avahi/services/cuems.service` and of
`cuems-config-node`, which rewrites the `uuid=` TXT record. The contract this design adds:
**that value is derived from the provisioned `/etc/cuems/settings.xml`, never independently
generated or hand-entered.**

This is the one part of the identity invariant that fails *silently* — a mismatch makes discovery
add a second "self" that never merges (`../cuems-nodeconf/specs/planning/09-self-node-seeding.md`
§4). It needs recording in `../cuems-common/docs/node-identity-contract.md`.

### D15 — The seed values are corrected against production, by *consumption*, not by copying

The audit's job was to find **improper** values, not to transcribe a machine. Each field was
classified by who actually reads it (engine source, live `ps` output, `systemctl show`):

| Key | Was | Now | Why |
|---|---|---|---|
| `("SettingsType","editor_url")` | `editor.local` | **`formitgo.local`** | the brand hostname — CueMS is the internal machinery, this is the user-facing entry point |
| `("VideoPlayerType","path")` | `/usr/bin/cuems-player` | **`/usr/bin/cuems-videocomposer`** | see below |
| `("VideoPlayerType","args")` | `""` | `""` (kept) | operator flags live in `videocomposer-flags.env` (`OPERATOR_FLAGS=--verbose` on `.3`) |
| `("AudioPlayerType","path")` | `/usr/bin/cuems-player` | **`/usr/bin/cuems-audioplayer`** | engine-spawned, `NodeEngine.py:514-518` |
| `("AudioPlayerType","args")` | `""` | **`-w -1`** | live, identical on both hosts |
| `("AudioMixerType","path")` | `/usr/bin/cuems-player` | **`/usr/bin/jack-volume`** | engine-spawned, `NodeEngine.py:456-457`; observed running as `jack-volume -c 0_mixer -p 9555 -n 4` |
| `("DmxPlayerType","path")` | `/usr/bin/cuems-player` | **`/usr/bin/cuems-dmxplayer`** | engine-spawned, `NodeEngine.py:628-636` |
| `("DmxPlayerType","args")` | `""` | `""` (kept) | `.2` carries `--mtcfollow`; it is now the binary's own default, so `.2` is the stale one |
| `("SettingsType","controller_url")` | `controller.local` | kept | `.3`'s hardcoded `169.254.9.204` is improper as a default |

**`/usr/bin/cuems-player` never existed** — absent on both machines. It reached all four player
sections through the base-class fallback (D16), which is how one fiction stayed invisible in
four places.

**`xjadeo` is equally improper.** It is installed on both machines and has **zero journal
mentions in 30 days**; the real video application is `cuems-videocomposer`, running as a
systemd service. The engine never reads `videoplayer.path`/`args` at all —
`NodeEngine.set_video_players()` takes only `osc_port` and speaks OSC to the already-running
process. Those two fields are nonetheless **kept and corrected rather than retired**: they are
scheduled to become the SSOT for the videocomposer systemd unit, so `path` naming the real
binary is what that future unit will consume.

Everything else matched both hosts exactly — all eleven `SettingsType` paths, all twelve
`NodeConfType` ports and timeouts, `outputs: 2`, `audio_cards: 1`, `universes: 1`,
`gradient_osc_port: 7100`.

**Two fields are read by nothing** in engine, editor, frontend or `cuems-common` —
`audioplayer.audio_cards` and `dmxplayer.universes` appear only in this library's own model and
values table. Both are XSD-required, so a valid document must carry invented values. Making
them optional is a rule-4 file-format change; logged as OPEN-6, not done here.

### D16 — `PlayerType` keeps its class hierarchy and loses its values fallback

Investigated 2026-09-21. `PlayerType` is an **abstract base no element uses** (`videoplayer` →
`VideoPlayerType`, `audioplayer` → `AudioPlayerType`, `audiomixer` → `AudioMixerType`,
`dmxplayer` → `DmxPlayerType`). The Python hierarchy mirroring the XSD's `xs:extension` —
`PlayerType(ConfigDict)` with MRO-accumulating `DECLARED_DEFAULTS` — is **correct and stays**;
its registry binding is correct and T007 is unaffected. Two defects sit in the values layer:

**Defect A — the mixer section derives from the wrong type.** `descriptor.py:586` passes
`"PlayerType"` as both the lookup name and the `TypeKey` while handing it the `AudioMixerType`
model. It works only because that extension is currently empty. Proven by patching each schema
with a new required field:

| Type patched | Result |
|---|---|
| `DmxPlayerType` (own `TypeKey`) | `RuntimeError: settings.xsd's DmxPlayerType.dmx_probe_field has no example value in descriptor._SETTINGS_EXAMPLE_VALUES — add one` |
| `AudioMixerType` (via `PlayerType`) | documented mechanism **silent**; later `SchemaError: Tag 'mixer_channels' expected` |

So FR-034's *"caught here, at generation time"* has a hole at one of the four sections. The net
holds — T1 still refuses to save an incomplete document — but the error arrives later and names
neither the values table nor the fix. Correction: `"AudioMixerType"` /
`TypeKey("settings","AudioMixerType")`.

**Defect B — the base-class fallback.** `_settings_example_value` falls back to
`("PlayerType", field_name)`, which is precisely how one wrong `path` served four players.
**Drop the fallback**; each concrete type declares its own `path`/`args`, and the
`("PlayerType", …)` entries leave the table. Safe: nothing else consults it — `_instance_for`
seeds from model defaults, not from this table.

Both are fixed in the same pass that lands the corrected table, with a regression test each,
because the table change is what makes the fallback actively wrong.

### D17 — The shipped document carries optional fields **explicitly**

`required_fields()` filters to `f.required`, so the generator emits no optional field today and
the table's `osc_port`/`output_latency_ms` entries are unreachable. Production splits on this:
`.2` omits them, `.3` writes them out. Functionally identical — the engine treats `"auto"` and
absent alike — but an operator opening `settings.xml` should see every knob that exists.

The generator widens past `f.required` for the player sections, and the four optional entries
become reachable.

---

## 4. The design, end to end

```
BUILD  (debian/rules, after dh_virtualenv)
  <built venv>/bin/python -m cuemsutils.xml.make_defaults \
      --out debian/cuems-utils/usr/share/cuems/defaults/
    -> settings.xml          generator + system-defaults.toml, SENTINEL identity
    -> network_map.xml       self-entry at the sentinel uuid, node_role=firstrun
    -> default_mappings.xml  one node at the sentinel uuid        (OPEN-1)
  install -m 0644 src/cuemsutils/xml/schemas/*.xsd   -> usr/share/cuems/schemas/
  install -m 0644 <system-defaults.toml>             -> usr/share/cuems/defaults/

SHIP
  /usr/share/cuems/defaults/*.xml     pristine, in the manifest, never read at runtime
  /usr/share/cuems/defaults/system-defaults.toml   upstream seed values
  /usr/share/cuems/schemas/*.xsd      arch-independent, no python3.11 in the path

INSTALL  (postinst, AFTER #DEBHELPER# so the venv interpreter is settled)
  /etc/cuems/*.xsd   installed always    -> schema always matches the installed library
  /etc/cuems/*.xml   if absent:  cuems-init-node --no-overlay   (mints one uuid4)
                     on failure: copy the pristine placeholders, warn, exit 0
                     if present: UNTOUCHED

PROVISION  (operator or imaging, any time after install)
  cuems-init-node --overlay /etc/cuems/defaults.d
    -> identity PRESERVED, site defaults applied across all three documents

PURGE  (postrm)
  remove this package's 9 paths, then rmdir --ignore-fail-on-non-empty
```

`postinst` must never exit non-zero (§2.5). Every step above either succeeds, or degrades to the
pristine copy with a warning.

### 4.1 Packaging hygiene to fix in the same pass

Found on `debian/bookworm` while measuring; not caused by this work, all in files this work edits:

- **Build artifacts are committed to the branch** — `debian/cuems-utils/` (the whole staging
  tree), `debian/.debhelper/`, `debian/files`, `debian/*.substvars`,
  `debian/debhelper-build-stamp`. Build output; belongs in `.gitignore`.
- `debian/compat 11` — superseded by `debhelper-compat (= 13)` in `Build-Depends`, which
  `cuems-common` and `cuems-power-bridge` already use.
- `Standards-Version: 4.1.4` — current is 4.7.x.
- The generated `postinst` says *"Automatically added by dh_python2"* — cosmetic, old
  dh-virtualenv.

### 4.2 Deliberately out of scope

**Python-version forward compatibility.** `Depends: python3 (>= 3.11), python3 (<< 3.12)`, the
venv's `lib/python3.11/` path, and dh-virtualenv's autoscript deriving the version from that
dirname all pin the package to 3.11. This design adds **no new coupling** — `/usr/share` and
`/etc` paths are version-free by construction — but does not remove the existing one. The related
hazard is recorded in `../cuems-common/dev/planning/systemd-service-split-architecture.md` §7.2
(the engines' `LD_LIBRARY_PATH` hardcodes `python3.11`).

---

## 5. Node identity — the invariant and its practices

The uuid appears in **four** places. Only one is a source:

| Document | Lookup | Failure mode |
|---|---|---|
| `settings.xml` → `Settings/node/uuid` | — | **the source** |
| `network_map.xml` → `node_list/node/uuid` | `ConfigManager.py:202`, `node_network_map` setter | `ValueError: Node with uuid … not found` |
| `default_mappings.xml` → `nodes/node/uuid` | `ConfigManager.py:336`, `load_net_and_node_mappings` | same sentence, different file |
| `/etc/avahi/services/cuems.service` → TXT `uuid=` | discovery matching | **silent** — a second "self" that never merges |

`../cuems-nodeconf/specs/planning/09-self-node-seeding.md` §1 found the same two eager lookups
independently, and its maintainer resolved lookup 2 on 2026-09-17: *"provisioning writes this
node's uuid into `/etc/cuems/default_mappings.xml` as well as `settings.xml`."* **`cuems-init-node`
is that provisioning step** — this design and that research describe one mechanism.

### The eight practices

1. **One source, one minter.** `settings.xml` is the identity SSOT exactly as the XSD is the
   structure SSOT. Only `cuems-init-node` mints a uuid4. Every other writer — nodeconf,
   `cuems-config-node`, the operator — *reads* it. A second minter is how two nodes end up with
   different answers to "who am I".
2. **Self-entry and topology are different concerns with different owners.** That *this node's*
   row exists in `network_map.xml` is seeded (by `init-node`, or by nodeconf at start-up);
   *other* nodes' rows, adoption and `online` flags belong to `cuems-nodeconf`. The split is what
   lets both write the file without a custody fight.
3. **Seed by plain insert, never by `merge`.** `merge` marks every node absent from its argument
   offline, so seeding through `merge({self})` asserts "nobody else is here" before discovery has
   run, corrupting `<online>`'s meaning (nodeconf §2). `NodeIndex` is a `dict`; insert into it.
4. **Seed with `node_role: firstrun`** — the honest value before the election. All five required
   fields are derivable: `uuid`/`mac` from `settings.xml`, `name` from the mDNS service name, `ip`
   from `get_ips()`.
5. **Match by uuid, key by MAC.** `merge` matches on uuid, so a discovered self updates the
   seeded entry in place and keeps the seed's MAC key — more correct than today's `name[:12]`,
   the name-derived key behind the duplicate-controller bug (nodeconf §3).
6. **The Avahi TXT uuid derives from `settings.xml`** (D14). The only silent failure in the set.
7. **`00000000-0000-0000-0000-000000000000` is a reserved sentinel** meaning "not provisioned".
   Tools say so in those words rather than failing obscurely, and **two nodes must never both
   carry it** — a placeholder collision is worse than a missing entry, because both nodes answer
   to one identity. D13 is what keeps it off live nodes.
8. **Ship a verifier.** `cuems-init-node --check` reads all four locations and reports mismatches
   by path. It is what turns `Node with uuid … not found` into something actionable, and the only
   thing that catches practice 6.

---

## 6. Open items

### OPEN-1 — `default_mappings.xml` needs its own values table

`system-defaults.toml` covers `settings.xsd` (D15 corrected it against production).
`project_mappings.xsd` additionally requires seven scalars (`number_of_nodes`,
`default_audio_input`/`_output`, `default_video_input`/`_output`, `default_dmx_input`/`_output`)
plus the node entry of §5, and the same completeness guarantee should apply.

**Do not transcribe the in-repo corpus.** The 2026-09-21 audit found production mappings that
the corpus does not resemble, and *neither* production file is copyable as-is:

- both hosts' documents are **schema-valid** against the canonical `project_mappings.xsd`;
- `.2` is single-node with four audio outputs (`USB analog L/R`, `Alesis iO|2 L/R`) and two
  video outputs mapped to `DP-2` / `HDMI-A-2`, both of which are **connected**;
- `.3` is the richer specimen — two nodes, eight audio outputs, a populated `<dmx>` section —
  but its second video output maps to `DP-2`, which is **disconnected**, and its
  `default_audio_output` uses an output *name* (`…_DP-1 Left`) where `.2` uses an *id*
  (`…_0`). One of those two spellings is wrong and it is not yet established which;
- `.3` also carries eight `default_mappings.xml.bak-*` files, i.e. the live document is the
  product of repeated hand-repair.

So the values table needs a decision per field about what a *fresh, unconfigured* node should
claim, not a copy of what either venue happens to run. The node entry must carry the sentinel
identity (D3) and stay consistent with `settings.xml` (§5).

### OPEN-2 — Does the editor need the XSDs?

`cuems-editor` has no `debian/` directory at all (feature 010, T037b). Whether it validates
against `/etc/cuems/*.xsd` or the venv copies has not been measured.

### OPEN-3 — Ordering between `postinst` and first service start

`cuems-init-node` must complete before any engine starts, or the engines hit the §5 lookups. On a
fresh install `postinst` handles it; on a stack install, package ordering has to be confirmed
rather than assumed, and the units are `cuems-common`'s.

### OPEN-4 — Where `cuems-init-node` lives

Naturally `cuems-utils` (it owns the schemas, the models and the generator). But it writes files
`cuems-common` has historically owned, and it is invoked from `cuems-utils`' `postinst`. The entry
point goes in `[project.scripts]` beside `cuems-convert-documents`; the cross-repo ownership note
belongs in `../cuems-common/docs/node-identity-contract.md` alongside D14's.

### OPEN-5 — ✅ CLOSED 2026-09-23 — uuid4 project-wide (see §9)

Measured 2026-09-21 (§2.6). The two controllers carry
`a3811d78-099f-11f0-a075-<mac>` — identical in every group but the MAC-derived node field, i.e.
a **uuid1 cloned and hand-edited** across machines. `.3`'s `node01` is `07131798-…-a039c6a7d18f`,
a **uuid5**. Three conventions, none of them uuid4.

`network_map.xsd`'s `UuidType` constrains shape only (canonical 8-4-4-4-12 hex), so all three
validate. But D13 says `postinst` mints a uuid4, and provisioning evidently does something else
— possibly deliberately, since a MAC-derived uuid is reproducible if a node is reimaged. Settle
what `cuems-init-node` should mint before implementing D13: uuid4, uuid1-with-MAC, or uuid5 over
a stable name.

### OPEN-6 — Two XSD-required fields nothing reads

`audioplayer.audio_cards` and `dmxplayer.universes` appear nowhere in `cuems-engine`,
`cuems-editor`, `cuems-frontend` or `cuems-common` — only in this library's own model and values
table. Both are required by `settings.xsd`, so every document in existence carries a value
nobody consumes and the defaults table has to invent one.

Making them `minOccurs="0"` is a rule-4 file-format change under
`specs/agreements/schema-evolution-convention.md`, needing a version step and a conversion. Not
done here; logged so the next schema pass can weigh it rather than re-deriving it.

Note the contrast with `videoplayer.path`/`args`, which are *also* unread today but are
**retained deliberately** (D15): they are scheduled to become the videocomposer systemd unit's
SSOT. Unread is not the same as dead.

---

## 7. The sixth schema — `hardware_outputs` (was `outputs`)

**Investigated and renamed 2026-09-23.** This section supersedes OPEN-6's framing: the two
unread count fields are not an isolated wart, they are one symptom of a missing layer.

### 7.1 It was never usable, for three independent reasons

Nothing anywhere loads a `CuemsOutputs` document — every `outputs` hit in engine, editor,
frontend, nodeconf and bridge is `cue.outputs`, the script schema's per-cue list, a different
concept. Three blockers, all re-measured 2026-09-23:

| | Blocker |
|---|---|
| X14 | `OutputsType` collides by name in the same namespace with `script.xsd:142`'s — a list of strings against a choice of `AudioCueOutput`/`VideoCueOutput`/`DmxCueOutput` |
| X15 | the only instance outside this repo, `../cuems-engine/dev/test_xml_files/outputs.xml`, declares `https://stagelab.coop/cuems` against a `targetNamespace` of `https://stagelab.coop/cuems/` |
| — | no registry bindings: `_config_models` has no branch for it, falls through to `{}, {}`, binds `GENERIC` |

`git log` shows three commits ever: the import from `cuems-engine`, a test commit, and 008's
mechanical `doc_version` marker. **It has never been developed.** Yet it *is* deployed —
`/etc/cuems/outputs.xsd` exists on both audited machines with no instance beside it.

**The fossil.** `ConfigManager.get_video_output_id('default')` returns
`self.node_conf['default_video_output']`, and `get_audio_output_id` the audio counterpart.
**`settings.xsd`'s `NodeConfType` declares neither field** — they are declared in exactly two
schemas, `hardware_outputs.xsd` and `project_mappings.xsd`. Someone wired `ConfigManager` to
read this schema's pair out of `node_conf`, expecting a merge that never happened. Both methods
have **zero callers**. So the schema is not unused but *half-wired*, which is worse: it reads
as intentional.

### 7.2 Four representations of "what can this node output"

| Layer | Holds | Read by | Status |
|---|---|---|---|
| `project_mappings` → `nodes/node/{audio,video,dmx}/outputs/output/{id,name,mappings/mapped_to}` | the real per-port inventory | engine (`node_hw_outputs`, `node_mappings`), frontend | **authoritative** |
| `project_mappings` root → `default_{audio,video,dmx}_output` | the three defaults | frontend (`sequence.component.ts:379,449,682`) | **live** |
| `/run/cuems/display.conf` (tmpfs, `cuems-generate-display-conf` as videocomposer's `ExecStartPre`) | canvas size + per-output regions | engine **and** videocomposer | **authoritative for geometry** — the engine ignores XML `canvas_region` by design |
| `settings.xml` → `videoplayer.outputs`, `audioplayer.audio_cards`, `dmxplayer.universes` | bare counts | **nothing** | degenerate |
| `hardware_outputs.xsd` | flat video+audio lists + 2 defaults, **no DMX** | **nothing** | never loadable |

Three cross-responsibility problems: the counts restate `len(outputs)` in a second document
with nothing reconciling them; the schema predates DMX and never caught up; and physical
geometry escaped XML entirely into a tmpfs file no schema describes.

### 7.3 The target: a node hardware capability descriptor

The system lacks a split between **hardware** (per node, discovered, stable across projects,
not human-authored) and **mappings** (per project, authored, referencing hardware). Today they
are fused inside `project_mappings`, which is why a *project* document carries a node's
physical port inventory and why `default_mappings.xml` exists as the node-scoped fallback of a
project-scoped schema.

`hardware_outputs` becomes that missing layer, reached through a public
`ConfigManager` accessor.

| Supersedes | How |
|---|---|
| `settings.xml`'s three counts | derived (`len(video_outputs)`) — the OPEN-6 fields **retire** rather than becoming optional |
| `project_mappings`' `node/{audio,video,dmx}/outputs` inventory | mappings keep *assignment* and reference output **ids**; they stop restating the inventory |
| `ConfigManager.get_{video,audio}_output_id` | the dead pair gets a real backing document — §7.1's assumed merge becomes real |
| — `network_map` | **no overlap.** The map says which nodes exist and are adopted; this says what each node can do. `uuid` is the join key |
| — `script.xsd` | **no overlap**, but requires the X14 rename. Cue outputs are *intent*; hardware outputs are *capability* |

**Scope: per node, aggregated by discovery** (decided 2026-09-23). `/etc/cuems/hardware_outputs.xml`
on each node describes only that node; the controller obtains other nodes' capabilities the way
it already learns topology. The node that owns the hardware describes it.

**`display.conf` is transcribed in, not replaced** (decided 2026-09-23). It is generated
outside the main start-up path — videocomposer's `ExecStartPre`, into tmpfs — and that
ownership stands. Transcribing its contents into the XML is **`cuems-nodeconf`'s**
responsibility: nodeconf is already the per-node agent that runs discovery and writes node
identity, so it is the one process positioned to read the generated geometry and record it.
This keeps videocomposer's generation authoritative at run time while giving the authoring side
a durable, schema-described copy.

Its natural writer is already named in this library's own schema comments: **`cuems-hardware-discovery`**
(`settings.xsd:16`, `xml-rebuild-08` §444, `../cuems-common/docs/latency-tuning.md:15`), which
has no checkout yet. `hardware_outputs.xml` is the document it was always going to write.

### 7.4 Done in rc16, and what is not

**Done**: the file is `hardware_outputs.xsd`; the schema key moved with it (`schema_path()`
builds the filename from the key); `SchemaName.OUTPUTS` takes the new value and keeps its member
name pending the final spelling. Suite green — 2660 passed, 100 skipped, 2 xfailed.

The transcription was then completed literally, in the same release: root element
`CuemsOutputs` → **`CuemsHardwareOutputs`**, type `OutputsType` → **`HardwareOutputsType`**,
enum member `SchemaName.OUTPUTS` → **`SchemaName.HARDWARE_OUTPUTS`**. **X14 is resolved** —
`script.xsd` keeps its own `OutputsType`, now the only declaration of that name. The per-schema
registry split it forced stays, and two tests were rewritten to pin the resolution rather than
the workaround. Suite green: 2660 passed, 100 skipped, 2 xfailed.

**Not done, deliberately**: the missing DMX section and the `id`/`name`/`mapped_to` structure —
the structure pass proper. **X15 still stands** (the external instance's namespace typo), and
the schema still has no model bindings, so it remains reserved rather than usable.

---

## 8. The splitting basis, writer responsibilities, and duplication flags

Written 2026-09-23, after §7's rename. §7 says *what* `hardware_outputs` should become; this
section says on what basis the split is made, who may write what, and which flags keep the split
from re-fusing as new hardware classes arrive.

### 8.1 The basis: two axes, and one cell per fact

Every fact this ecosystem stores has a **scope** (how far it is true) and a **provenance** (how
it came to be known). A document is the container for one cell. Where a document straddles two
cells, that is the defect.

| | **discovered** (machine-probed) | **authored** (human intent) | **derived** (computable) | **runtime** (regenerated at start) |
|---|---|---|---|---|
| **node** | `hardware_outputs.xml` | `settings.xml` | *never stored* | `/run/cuems/display.conf` |
| **cluster** | `network_map.xml` | adoption flags, in the same file | *never stored* | — |
| **project** | — | `mappings.xml` | — | — |
| **show** | — | `script.xml` | — | — |

Three violations are live, all measured:

1. **`project_mappings` straddles node-discovered and project-authored.** It carries each node's
   physical port inventory (`nodes/node/{audio,video,dmx}/outputs`) *and* the project's
   assignment of cues to them. `default_mappings.xml` exists only because of that fusion — it is
   the node-scoped fallback of a project-scoped schema, which is the smell naming itself.
2. **`settings.xml` stores derived facts.** `audioplayer.audio_cards` and `dmxplayer.universes`
   are `len(inventory)` restated in a second document, read by nothing (OPEN-6).
3. **`hardware_outputs.xsd` mixes provenance within itself.** Its `default_video_output` /
   `default_audio_output` are *choices*, not capabilities — authored intent sitting in a
   discovered document, and already declared in `project_mappings`. §8.3's F2 catches this
   mechanically.

### 8.2 Writers and consumers

**Exactly one writer per document.** Anything else has no arbiter, and the loser is whichever
process wrote first.

| Document | Sole writer | Readers |
|---|---|---|
| `settings.xml` | `cuems-init-node` | engine, power-bridge, `cuems-common` tools, editor |
| `hardware_outputs.xml` | `cuems-hardware-discovery` (probe) · `cuems-nodeconf` (transcribes `display.conf`) | editor (authoring), engine (validation) |
| `network_map.xml` | `cuems-nodeconf` | engine, power-bridge, `cuems-common`, editor |
| `mappings.xml` | `cuems-editor` | engine, frontend |
| `script.xml` | `cuems-editor` | engine |
| `/run/cuems/display.conf` | `cuems-videocomposer` (`ExecStartPre`) | engine, videocomposer |

Two entries need their seams stated, because both look like two writers:

**`hardware_outputs.xml`** has one writer per *section*: discovery owns the probed port
inventory, nodeconf owns the transcribed geometry. They never write the same element, so F1
holds at element granularity. `display.conf` keeps its videocomposer ownership at run time —
it is generated outside the main start-up path and that is correct; nodeconf transcribes its
*contents* so the authoring side has a durable, schema-described copy, and records the
provenance rather than claiming authorship.

**`output_latency_ms` is the one field with two legitimate provenances** — a *measured* hardware
property and an *operator override*. Splitting it by document resolves that without a second
writer: the measured value belongs in `hardware_outputs.xml` (discovered), the override stays in
`settings.xml` (authored), and a reader prefers override → measured → `"auto"`. That is the same
layering shape as D9's `defaults.d` overlay, and it keeps `cuems-init-node` the sole writer of
`settings.xml`.

### 8.3 The duplication-avoidance flags

Rules stated so they can be **checked**, not just intended. Each names what it catches today.

**F1 — One writer per document, declared in the schema's annotation.** A document whose writer
is not named is a document with no arbiter. *Catches*: the `settings.xml` two-writer conflict
above, resolved before it lands.

**F2 — A fact is declared in exactly one schema; everywhere else it is referenced by key.** The
join keys are the node `uuid` and the port `id`. **Checkable mechanically** by reporting element
and type names declared in more than one schema, against a curated allowlist of legitimate
references and coincidental generics. Run 2026-09-23, it finds:

| Overlap | Verdict |
|---|---|
| `NodeType` — `network_map` **and** `project_mappings` | **Live X14-class defect.** Same name, same namespace, **different content**: 10 identity fields against `uuid`/`mac` + three device sections. Never audited; only the per-schema registry split stops it misbinding |
| `UuidType` — `network_map` **and** `script` | **Live X14-class defect, and semantic.** `network_map`'s accepts **any** uuid version, case-insensitive, shape only — deliberately (007 research R2). `script`'s requires **uuid4** (version nibble `4`, variant `[89ab]`), lowercase, exactly 36 characters. Production node identities are uuid1 and uuid5 (§2.6): the first accepts them, the second would reject them. Ties directly to **OPEN-5** |
| `BoolType`, `DateType`, `NonEmptyString`, `PositiveUnitFloat`, `UnitFloat` | Identical content across 2–4 schemas. Same standing as `CanvasRegionType`: tolerated, but pinned against drift |
| `CanvasRegionType` — `project_mappings` **and** `script` | Identical content today (`x`/`y`/`width`/`height`). Benign now, an X14 the moment one side gains a field, with nothing checking |
| `default_audio_output`, `default_video_output` — `hardware_outputs` **and** `project_mappings` | §8.1's violation 3 — authored intent duplicated into a discovered document |
| `uuid`, `mac`, `node`, `id`, `output` | **Legitimate**: references by join key, which is what F2 prescribes |
| `name`, `value`, `x`, `y`, `width`, `height` | Coincidental generics — same word, different meaning. Allowlisted |

That the check finds a **live, previously unknown defect** on its first run is the argument for
making it a test rather than a habit.

**F3 — Derived facts are computed, never stored.** If a value is a function of another
document's content, it has no declaration site. *Catches*: `audio_cards`, `universes`, and any
future per-class count. Checkable as a list of known-derived facts asserted absent from the
schemas.

**F4 — One provenance per document.** A discovered document carries no choices; an authored one
carries no probe results. *Catches*: `hardware_outputs`' `default_*` pair; keeps
`output_latency_ms`'s two halves apart.

**F5 — References point from volatile to stable.** show → project → node → cluster, never the
reverse. *Checkable*: `hardware_outputs.xsd` must never name a project or a cue;
`network_map.xsd` must never name an output. A back-reference is how a node document starts
needing a rewrite every time a project changes.

**F6 — A new device class is data, not schema.** See §8.4.

### 8.4 Surviving expansion — the new-hardware-class test

The test a split must pass: *what does adding a fourth device class cost?* Measured today, a new
class touches **four schemas and the code that enumerates them**:

| Site | Cost |
|---|---|
| `settings.xsd` | a player section element + a `PlayerType` extension |
| `project_mappings.xsd` | `default_X_input`/`_output` at the root + an `<X>` element in `NodeType` |
| `script.xsd` | `XCueType` + `XCueOutputsType` + a member in the `OutputsType` choice |
| `hardware_outputs.xsd` | `X_outputs` + `default_X_output` |
| `ConfigManager.py:69` | `_DEVICE_SECTIONS = ('audio', 'video', 'dmx')` — a hardcoded triple |
| `ConfigManager.py:160,283` | the six-key `node_hw_outputs` dict becomes eight |
| `cuems-frontend` | four cue-type unions in `sequence.component.ts` |

Roughly twenty sites, in four repositories, for one new class — and every one of them is a place
the classes can fall out of step.

**The mechanism: XSD 1.1 conditional type assignment**, which this library can already use —
`xmlschema==3.4.3` is pinned and XSD 1.1 is already required by `script.xsd`'s `xs:assert`.
A device becomes `<device class="…">` with `xs:alternative` selecting a type per class:

```xml
<xs:element name="device" minOccurs="0" maxOccurs="unbounded" type="cms:DeviceType">
  <xs:alternative test="@class='video'" type="cms:VideoDeviceType"/>
  <xs:alternative type="cms:DeviceType"/>
</xs:element>
```

**Proven under the pinned version, 2026-09-23**: a document carrying
`<device class="lighting">` validates with **no schema change**, while
`<canvas_region>` on a non-video device is still rejected. So a class needing no special fields
costs *nothing*; one that does costs a single `xs:alternative` line instead of an element in
four schemas.

`_DEVICE_SECTIONS` then derives from the document rather than being declared, and
`node_hw_outputs`' fixed six keys become per-class — which is the same "named rather than
discovered" reasoning T051 already applied, extended one level up.

### 8.5 Sequencing

The flags are worth landing **before** the structure work, not after: F2's overlap report is a
test, it already found a live defect, and it is what stops the split from re-fusing while it is
being made.

1. **F2 as a test** — ✅ **landed 2026-09-23**, `tests/contract/test_schema_name_overlap.py`.
   A ratchet: today's overlaps are enumerated with a verdict each, anything new fails, and an
   entry may not go stale — resolving a collision *requires* removing its entry, so the
   allowlist cannot end up certifying a defect that is already fixed. Proven to bite in all
   three directions (new overlap, a benign duplicate drifting, a recorded divergence resolved).
   It found a **second** live X14 the section above had not: `UuidType`.
2. **`NodeType`** — ✅ **landed 2026-09-23**. `project_mappings.xsd`'s became
   **`NodeMappingType`**; `network_map.xsd` keeps the plain name, identity being the older and
   broader meaning. Invisible to every document on disk — type names are schema-internal and
   nothing uses `xsi:type` — so no version step and no conversion, and zero references in any
   sibling repository. Eight sites, one more than the pre-change statement predicted
   (`test_mappings_shape.py:53`'s `models.NodeType`, which the impact grep missed).
   Its entry left F2's allowlist, which is how a fix is completed there.
   It also produced `tests/contract/test_rule_targets_resolve.py`: the T2 rule
   `one_custom_template_per_node` is keyed on a class **name**, matched by string, so a missed
   rename leaves it registered and silently never firing — the only site in the change that no
   existing test would have caught.
3. **F3/F4** — ✅ **landed 2026-09-23**. `settings.xsd` loses `audio_cards`/`universes`
   (F3: derived facts are computed, never stored — both read by nothing anywhere);
   `hardware_outputs.xsd` loses `default_video_output`/`default_audio_output` (F4: one
   provenance per document — authored choice, already declared in `project_mappings`). Each
   schema moves to **document version 2** with a registered conversion, so documents in the
   field convert on read: a real production `settings.xml` carrying both counts loads clean.
   The **library** version stays `0.1.0rc16` (§12).

   Three things this cost, each recorded where it happened: the golden-capture harness had to
   be fixed first (it could no longer regenerate, and `--force` would have destroyed nine
   correct goldens); the current-dir corpus documents moved to the v2 shape while `pre-008/`
   keeps the v1 shape as the conversions' coverage; and the negative fixtures were moved too,
   because a retired element left in them made them fail for a *second* reason and the
   assertion would have passed on the wrong one.
4. **F6** — the `class`-attribute reshape, which is the file-format migration proper and needs a
   version step under `specs/agreements/schema-evolution-convention.md` rule 4.
5. Only then the inventory move out of `project_mappings`, which is what finally retires
   `default_mappings.xml`.

---

## 9. uuid4 project-wide — the convergence, and why it waits for `cuems-init-node`

**Decided 2026-09-23**, resolving the `UuidType` collision F2 found (§8.3) and closing **OPEN-5**:

1. **uuid4 everywhere**, from here on.
2. **Minting goes through the machinery this library wraps** — `cuemsutils.tools.Uuid` (which
   mints `uuid4()` and *raises* on anything else) and `helpers.new_uuid`.
3. **Non-uuid4 values are updated by the upgrade machinery already in place.**
4. A frontend→editor `get_new_uuid` endpoint **if** the frontend cannot mint uuid4 itself.

### 9.1 Point 4 does not apply — measured

`cuems-frontend` already depends on `uuid@^11.1.0` and mints uuid4 in four places, including
`project-create.handler.ts:23,51` and `sequence.component.ts:1095`. The conditional is not met,
so **no new endpoint is created**. Settled 2026-09-23: the frontend's existing minting stands,
its output is already validated on the way in, and decision 2's "common machinery" binds the
Python side rather than requiring a round trip for every cue the operator creates.

The compound `<uuid>_<output_id>` form survives the change: `projects.service.ts:553` parses it
with `^([a-f0-9]{8}-…-[a-f0-9]{12})_(.+)$`, which is version-agnostic and already lowercase-only,
so uuid1, uuid5 and uuid4 all parse. (Three mixer components use `split('_')` instead, which
mis-splits `system:playback_1` — a pre-existing defect, unrelated to this change, recorded here
because the next reader will find it while looking at the same strings.)

### 9.2 `script.xsd`'s definition survives; `network_map.xsd`'s narrows to it

| | pattern | accepts |
|---|---|---|
| `script.xsd` | `[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}`, `length = 36` | uuid4 only, lowercase |
| `network_map.xsd` | `[0-9a-fA-F]{8}-…-[0-9a-fA-F]{12}` | any version, either case |

`script.xsd`'s is already exactly `Uuid.UUID4_REGEX`, so convergence is on the definition the
code already enforces. Note `script.xsd` carries three **commented-out** `node_uuid` elements
(`:252`, `:290`, `:360`, in the three cue-output types); if they are ever restored they would put
node identities under the strict pattern, which is a second reason the two must agree.

### 9.3 **Narrowing invalidates every node identity in the field**

Measured on both production machines (§2.6): the controllers carry
`a3811d78-099f-11f0-a075-<mac>` — a **uuid1**, cloned and hand-edited — and `node01` carries a
**uuid5**. None is a uuid4. Tightening the schema makes every deployed `network_map.xml` invalid.

So this is a rule-4 file-format migration under
`specs/agreements/schema-evolution-convention.md`: a version step plus a conversion path.

### 9.4 But the re-mint is **not a document conversion**, and that is the sequencing constraint

`convert()` walks **one document at a time** and has no cross-document view. A node's uuid is a
cross-document identity (§5) that also appears **inside compound strings**:

```
settings.xml          Settings/node/uuid
network_map.xml       node_list/node/uuid
default_mappings.xml  nodes/node/uuid
                      default_audio_output   a3811d78-…-00e04c01b7e3_DP-1 Left   <- embedded
                      default_video_output   07131798-…-a039c6a7d18f_0           <- embedded
                      default_dmx_output     a3811d78-…-00e04c01b7e3             <- embedded
/etc/avahi/services/cuems.service   TXT uuid=
```

Converting `network_map.xml` alone leaves `settings.xml` disagreeing, and
`ConfigManager(load_all=True)` raises `Node with uuid … not found` — the failure §2.2 already
measures. A per-document conversion **cannot** perform this safely.

**The division of labour**, therefore:

| Does what | Who |
|---|---|
| detect a non-uuid4 identity, report it by document and path, change nothing | the conversion registry / `cuems-convert-documents --check` |
| perform the re-mint across all of §5's locations, atomically | **`cuems-init-node`** (D12) — it already owns the cross-document write and the preserve-identity rule |
| rewrite the Avahi TXT from the new `settings.xml` value | `cuems-common` (D14's contract) |

**Consequence: the schema tightening cannot land before `cuems-init-node` exists.** Landing it
first would invalidate both production maps with no tool able to repair them — shipping a brick.
The `UuidType` entry therefore stays in F2's `KNOWN_DIVERGENT_DECLARATIONS` until then, with the
decided resolution recorded in its verdict.

### 9.5 One property is lost, and it should be lost knowingly

A MAC-derived uuid1 is **reproducible across a reimage**: rebuild a node from scratch and it
regenerates the same identity. A uuid4 does not. After this change, **reimaging a node produces a
new identity and the node must be re-adopted**.

That is defensible — adoption is a deliberate operator act, and identity that silently survives a
rebuild is arguably the bug — but it is a real change in field behaviour and belongs in the
migration guide rather than being discovered at a venue.

It also sharpens D13: `postinst` mints **if and only if** there is no identity, and purge is the
only thing that discards one. With uuid4, a lost `/etc/cuems/settings.xml` is a lost node
identity, permanently.

---

## 10. Re-minting node identities across a machine — the procedure

§9 establishes *that* every node identity must become a uuid4 and that `convert()` cannot do it.
This section is the procedure that can, written to be executable rather than summarised.

**Verification status.** The file layout below is derived from code — `ConfigBase.project_path`,
`ConfigManager.load_net_and_node_mappings`, the editor's settings dict — and from the corpus.
The two production machines were reachable on 2026-09-21 but **not on 2026-09-23**, so the live
library layout, the configured script filename and the `trash/` shape are **unconfirmed on
hardware**. Confirm them (§10.7) before a first real run.

### 10.1 Everywhere a node uuid lands

| Path | Occurrence | Form |
|---|---|---|
| `/etc/cuems/settings.xml` | `Settings/node/uuid` | bare — **this node only** |
| `/etc/cuems/network_map.xml` | `node_list/node/uuid` | bare — **every** node |
| `/etc/cuems/default_mappings.xml` | `nodes/node/uuid` | bare |
| " | `default_audio_output`, `default_video_output`, `default_dmx_output` | **compound** `<uuid>` or `<uuid>_<output_id>` |
| `<library>/projects/<project>/mappings.xml` | `nodes/node/uuid` | bare |
| " | the three `default_*_output` | **compound** |
| `<library>/projects/<project>/<script_file>` | every `<output_name>` | **compound** `<uuid>_<output_id>`, incl. `<uuid>_custom_<n>` |
| `<library>/trash/...` | the same, in deleted projects | see §10.5 |
| `/etc/avahi/services/cuems.service` | TXT `uuid=` | bare |

**Confirmed NOT to need rewriting**, so the procedure does not touch them:

- **the editor database** (`project-manager.db`) — `db.py:20,35` store *project* and *media*
  uuids as primary keys, both editor-minted uuid4 already. No node uuid is stored;
- media, waveforms and thumbnails — keyed by media uuid;
- anything under `/run` — regenerated at service start.

### 10.2 The trap: structural rewriting silently misses most of it

The majority of occurrences are **inside compound strings**, not in elements of their own:

```xml
<output_name>0367f391-ebf4-48b2-9f26-000000000001_2</output_name>
<default_audio_output>a3811d78-099f-11f0-a075-00e04c01b7e3_DP-1 Left</default_audio_output>
```

A rewrite that walks the XML and replaces `uuid` elements handles `settings.xml` and
`network_map.xml` and **leaves every script in the library wrong** — and wrong in the way that
does not raise, because `output_name` is a `NameStringType`, so a stale prefix is still
schema-valid. It fails later as an output that resolves to nothing.

**Therefore: rewrite by literal text substitution of the 36-character token**, per old uuid,
across whole files. Three reasons:

1. it catches bare and compound occurrences in one pass, which is exactly the distinction a
   structural rewrite gets wrong;
2. a uuid is an opaque 36-char token with no meaningful substring, so an anchored literal
   replacement cannot partially match;
3. it leaves every other byte untouched — no reformatting of documents an operator has hand-
   edited, and no reserialisation diff across the whole library.

The safety this gives up — that a replacement lands somewhere unintended — is bounded by
building the substitution table from **node uuids only** (§10.3), and recovered by validating
every touched document afterwards (§10.6).

### 10.3 Step 1 — build the substitution table, once, on the controller

```
for each node in network_map.xml:
    old = node/uuid
    new = str(cuemsutils.tools.Uuid())        # mints uuid4; raises on anything else
    table[old] = new
```

Rules:

- **Minted through `cuemsutils.tools.Uuid`** (decision 2) — it mints `uuid4()` and refuses any
  other shape, so the table cannot contain a value the tightened schema will reject.
- **Persist the table before writing anything.** It is the only record linking old identity to
  new; a run that dies mid-way and re-mints produces a second new identity for a node already
  half-rewritten.
- **A node already carrying a valid uuid4 is left alone** — `old == new`, no substitution. The
  procedure is re-runnable and must be idempotent (§10.6).
- The table is built **once, on the controller**, and distributed. Each node minting its own
  would give the controller's map and the node's settings different answers.

### 10.4 Step 2 — stop the services that cache identity

`cuems-node-engine`, `cuems-controller-engine`, `cuems-editor`, `cuems-nodeconf` and
`cuems-power-bridge` all read these documents at start and hold the result. Rewriting underneath
a running engine gives a process whose in-memory identity no longer matches disk.

`cuems-nodeconf` matters most: it **writes** `network_map.xml`, so a discovery pass mid-rewrite
can reintroduce an old uuid.

### 10.5 Step 3 — apply, in this order

**Per node** — `/etc/cuems/settings.xml`, `network_map.xml`, `default_mappings.xml`: substitute
every table entry in each file. The map carries *all* nodes, so every entry applies; settings
carries only its own.

**Controller only** — the project library. For every project directory under
`<library_path>/projects/`:

- `mappings.xml`
- the script, whose filename is **configuration, not a constant** — the editor's
  `script_file_name` is `script.xml` in `cli.py:40` and `cue_script.xml` in
  `CuemsProjectManager.py:38`. **Discover it; do not hardcode it.** A procedure that assumes
  `script.xml` skips a library configured the other way, silently and completely.

**`trash/` is included by default.** `set_dir_hierarchy` creates `trash/projects` beside
`projects`, and a project restored from trash after the re-mint would reintroduce stale
identities into a live library. Excluding it is defensible only if restoring from trash is
accepted as requiring a re-run — which is a decision to record, not to assume.

**Backups are not rewritten, and that is the hazard to state plainly.** `.bak-*` files (eight of
them on one audited machine), conversion backups, and the pre-flight backup of §10.4 all contain
old identities by design. Restoring any of them after the re-mint reintroduces a stale identity.
The migration guide must say so; the alternative — rewriting backups — destroys their purpose.

**Finally** the Avahi TXT `uuid=`, derived from the *new* `settings.xml` under D14's contract,
which is `cuems-common`'s to perform.

### 10.6 Step 4 — verify, by measurement rather than by the absence of errors

1. **Zero old uuids remain.** For every `old` in the table, a recursive search of `/etc/cuems`
   and the whole library returns nothing. This is the check that catches a missed compound
   string, and it is the one that would have caught a hardcoded script filename.
2. **Every touched document validates** against its schema — with the tightened `UuidType`, so
   this is also the proof that the narrowing is safe to land.
3. **`ConfigManager(load_all=True)` succeeds on each node.** That exercises §5's two eager
   lookups together: this node's uuid resolves in both `network_map.xml` and the mappings.
4. **Adoption state is preserved** — `adopted`/`online` unchanged per node, since only the uuid
   moved.
5. **Idempotence**: a second run substitutes nothing and changes no file.

### 10.7 Unconfirmed, to check on hardware before a first run

- the live library layout under `<library_path>/projects/`, and whether `trash/` mirrors it;
- the configured `script_file_name` on each machine;
- whether any project carries a `mappings.xml` at all, or relies on `default_mappings.xml`;
- whether any *other* file in a project directory embeds an output name (the corpus shows only
  the script, but the corpus is not the field).

### 10.8 Why this is not `cuems-convert-documents`

It is a **cluster-wide, cross-document re-identification**, not a per-document version step:
one substitution table spans every node and every project; the operation is ordered against
service lifecycle; and it must be idempotent and resumable across a partial failure.
`convert()`'s contract — walk one document's version steps, mutate its root in place — is the
wrong shape for all four. The conversion tool's role here is the one §9.4 assigns it: **detect
and report** a non-uuid4 identity, so an operator knows the procedure is needed, and change
nothing.

---

## 11. `test_schema_scope`, re-based rather than excluded a third time — ✅ done 2026-09-23

**Raised 2026-09-23**, after `project_mappings.xsd` became its second exclusion.

`tests/contract/test_schema_scope.py` pins each schema's **Phase-1-end content** and asserts
that ITEM E's `doc_version` attribute is the only textual difference since. It was written for
feature 008, when the schemas were meant to hold still, and it did its job: it catches an
*unsanctioned* schema edit.

The current work inverts its premise. Leaving the XML in a clean, durable state is the whole
point, so sanctioned schema edits are now the norm rather than the exception. Two have landed
already — `hardware_outputs.xsd`'s rename and `project_mappings.xsd`'s `NodeMappingType` — and
each was handled by dropping the schema from the asserted dict with the reason recorded, because
re-pinning to a recomputed hash would silently re-baseline an attestation whose stated meaning
is *Phase-1-end content*.

That treatment does not scale past where it now is:

| | asserted | excluded |
|---|---|---|
| after feature 008 | 6 | 0 |
| after `hardware_outputs` rename | 5 | 1 |
| after `NodeMappingType` | **4** | **2** |

A third exclusion leaves the test pinning half the schemas against a baseline none of them is
expected to keep — at which point it reads as a tripwire while guarding almost nothing.

**The replacement pins *current* content as the new standard** (landed 2026-09-23, before F3
forced the third exclusion), with its own stated meaning: *these are the schemas as the rebuild left them, and a change to any of them is a
deliberate act that updates this file in the same commit*. That is the same contract, re-based
on the state the feature exists to produce rather than on the state it started from — and it is
what makes the goldens hold true **after** the modifications, as the base for whatever comes
next.

Two things to preserve when it is rewritten, because they are the parts that have actually
caught things:

- `test_every_schema_declares_doc_version_exactly_once` — independent of any baseline, and worth
  keeping as-is;
- `test_only_six_schemas_are_bundled` — the check that a seventh schema cannot appear unnoticed.
  It survives on `ALL_SCHEMA_NAMES`, which is why both excluded schemas were kept in that set
  rather than removed outright.

The production audit (§2.6) is the argument for doing this properly rather than loosening it:
every `.xsd` on both machines is stale, and the two machines disagree with each other. A
baseline that no longer describes anything is how that state is reached.

---

## 12. The version this work merges under — `0.1.0rc16`

**Decided 2026-09-23.** The library version **stays at `0.1.0rc16`** through the whole
xml-refactor. It is the version the coordinated merge deploys, and the final state is tagged
`xml-refactor-merge-candidate`.

Schema changes do **not** move it. They are signalled where the architecture already signals
them: the per-schema **`doc_version`**, with a registered conversion for every step. The library
version answers *what API do you get*; `doc_version` answers *what shape is this file*. Keeping
the two apart is what lets a schema change ship inside an rc line without lying about the API.

### 12.1 Why not `0.1.1`

`0.1.1` is **already spoken for**, and taking it would break two things at once:

- **`_deprecation.REMOVAL_RELEASE = "v0.1.1"`.** Every deprecation warning this library has
  emitted since feature 006 promises the deprecated surface is *gone* in v0.1.1. Releasing it
  with `Settings.py`, `XmlReaderWriter.py`, `Parsers.py`, `CMLCuemsConverter.py`,
  `timeoutloop.py` and the seven aliases still present makes all of them false — which is
  exactly what feature 010's T060 is written to prevent. That removal is gated on T049/T050's
  **measured zero** import census, which is not met.
- **Three consumers would refuse it outright**, by package relation rather than by convention:
  `cuems-common/debian/control:13` (`<< 0.1.1~`), `cuems-nodeconf` (`<0.1.1` and `<< 0.1.1~`),
  and `cuems-power-bridge/pyproject.toml:38` (`<0.1.1`). `cuems-common`'s own rationale, at
  `debian/control:60`, is that the ceiling exists so *"a library that has moved on is refused
  rather than merely documented"*. A `0.2.0` is refused by the same bound.

### 12.2 Why not `rc17` either

An rc bump would pass every consumer ceiling, but it would say nothing true: the API does not
change here, and the ecosystem merges this work as one coordinated deployment rather than as a
sequence of library releases. `rc16` is what the consumers already pin
(`cuems-nodeconf`, `cuems-power-bridge`: `>=0.1.0rc16`), so the merge lands on the version they
were written against.

### 12.3 The gap this leaves, stated

`cuems-common/debian/control:60` records it: *"Inside the 0.1.0 rc line the lock is partial: a
schema change there passes the ceiling, and is caught by the schema-mirror test and by the rule
that nothing in the ecosystem releases alone."* So a package relation will **not** stop a node
running a schema this library has moved past. What does: the per-schema `doc_version` and its
conversions (§8's F-flags), `test_schema_scope`'s hash pin, and D27 — nothing ships alone.
