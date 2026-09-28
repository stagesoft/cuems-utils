<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Feature Specification: `/etc/cuems` first install — a fresh `apt install` leaves a node that loads and is unique

**Feature Branch**: `011-etc-cuems-first-install` — **local only**. It merges into
`feat/xml-refactor` when done; only that integration branch is pushed to origin, unless stated
otherwise during the feature (rule given 2026-09-25).
**Created**: 2026-09-25
**Status**: Draft — clarified 2026-09-25 (eight questions answered, three deferred to the plan
with recorded defaults); ready for `/speckit.plan`
**Input**: User description: "Build the /etc/cuems first install for cuems-utils: a fresh
`apt install` must leave a node that boots, loads its configuration, and is uniquely identified —
where today no package ships any of the three documents ConfigManager requires in a usable state,
and the six XSD files that define them live only inside the venv." The full prompt is
`specs/planning/011-first-install-specify-prompt.md` §2, pasted verbatim (that prompt document was
deleted on 2026-09-28 once every clarification it listed was recorded here — git history keeps it).

**Authoritative inputs** (read in full before this spec was written; this spec does not re-derive
what they measure):

- `specs/planning/etc-cuems-first-install.md` — the **design**: decisions D1–D17 with reasoning
  (§3), the end-to-end flow (§4), the identity invariant and its eight practices (§5), the open
  items (§6), the splitting basis and duplication flags (§8), and the uuid4 sequencing constraint
  (§9.4) that makes this feature a hard prerequisite of feature 012.
- `specs/planning/etc-cuems-first-install-execution.md` — the **measured state**: what is built
  per decision (§3), findings that corrected the design document (§4), this feature's brief (§6),
  and the trap register (§7).

Where this spec restates a decision, the planning document's numbering is kept (D2, D5, OPEN-1,
practice 7) so that the two can be read side by side. Where this spec **corrects** either
document from a measurement taken today, it says so in "Measured since the planning documents"
and the correction is to be applied back to the planning document in the same pass, never
silently.

---

## The problem, stated as measured

`ConfigManager` needs three XML documents in `/etc/cuems`, and all three are uuid-coupled:
`settings.xml` names this node's uuid, and both `network_map.xml` and `default_mappings.xml`
must contain an entry for that same uuid or the manager raises at load. Measured on the shipped
defaults available today:

```
ConfigManager(load_all=True)
  -> ValueError: Node with uuid 00000000-0000-0000-0000-000000000000 not found
```

Only `settings.xml` has a generator. `network_map.xml` ships (from `cuems-common`) as an empty
`<node_list/>` stub that cannot support `load_all=True` on any node. `default_mappings.xml` is
written at runtime by a `cuems-common` helper. The six `.xsd` files live only inside the venv;
`cuems-common` carries one hand-maintained mirror that has already drifted once.

Three live defects depend on schemas nobody ships (two from the planning documents, one measured
today — see below):

1. `cuems-common`'s `cuems-display-setup` validates against `/etc/cuems/project_mappings.xsd`.
2. `cuems-common`'s operator documentation (`docs/latency-tuning.md`) tells people to load
   `/etc/cuems/settings.xsd`.
3. `cuems-editor` hardcodes `/etc/cuems/script.xsd` as the schema path for every script it reads
   or writes (`CuemsProjectManager.py:23`). **Measured 2026-09-25; closes OPEN-2** — the editor
   does need the XSDs, from `/etc/cuems`, today.

Both audited production hosts carry stale `.xsd` copies that disagree with each other and with
this repository, and one carries a `network_map.xsd.dpkg-dist`: the conffile prompt fired, the
admin kept the old copy, dpkg parked the new one beside it. That is the failure mode D5 exists to
prevent, already having happened in the field.

## The constraint that dominates every design choice

`cuems-utils` is the base dependency of the whole stack — unavoidable, installed first. Debian's
failure semantics are asymmetric here: a non-zero exit from **its** `postinst` leaves the package
half-configured and **every dependent package fails to configure**. One bad exit blocks the
install of every CUEMS component at once, on every node it reaches, recoverable only by hand, on
hardware, at a venue.

Therefore `postinst` must never exit non-zero. Every step either succeeds, or degrades to copying
the pristine placeholder, warns, and exits 0. This is also why the operator-authored overlay (D9)
is applied by `cuems-init-node` and never by `postinst` (D11): a TOML typo must not be able to
block the stack.

---

## Measured since the planning documents (2026-09-25)

Each item corrects or extends an authoritative input. They are recorded here so the planning
documents can be updated in this feature's pass rather than left disagreeing with the tree.

| # | Finding | Corrects |
|---|---|---|
| M1 | `../cuems-common/docs/node-identity-contract.md` **exists** (since `cuems-common`'s feature 001: field contract, restore procedure, TXT record vocabulary). It does **not** carry D14's derivation contract — its "Discovery TXT record" section describes the record's vocabulary, not where the `uuid=` value must come from. | Execution doc §3.2 ("No `node-identity-contract.md` in `../cuems-common`"). The deliverable becomes *extend the existing document with D14's contract*, not *create it*. |
| M2 | `cuems-common`'s `usr/bin/cuems-config-node` **mints a `uuid1()` itself** and writes it into both `/etc/cuems/settings.xml` and the three Avahi service templates. It is a **second minter**, and the identity it writes is not uuid4. This is the live violation of practice 1 (one source, one minter) that D14's contract must name. | Design §5 practice 1 lists `cuems-config-node` among the *readers*; today it is a writer. |
| M3 | The three shipped Avahi templates `usr/share/cuems/cuems.service.{firstrun,controller,node}` carry a **hardcoded real controller uuid** (`a3811d78-099f-11f0-a075-00e04c01b7e3`, the same identity §2.6 measured on a production controller) in their `uuid=` TXT record. Every host that announces from an unmodified template announces a production controller's identity — practice 7's placeholder collision, but with a real identity instead of a sentinel. | Not in either document. It is the concrete reason D14 "fails silently". |
| M4 | The editor reads `/etc/cuems/script.xsd` (finding 3 above). | OPEN-2, now closed: the editor needs the XSDs from `/etc/cuems`, and no package ships them. |
| M5 | `cuems-common`'s `postinst` has **no `#DEBHELPER#` token** (pinned by its `tests/test_postinst_ordering.py`), so `dh_installsystemd` injects no service starts into it; the engines start from their targets on boot. On a stack install, dpkg configures `cuems-utils` before `cuems-common` because the latter `Depends:` on the former. | OPEN-3 — an answer to confirm in the plan by test, not a decision to take. |
| M6 | `cuems-common` already carries `Depends: cuems-utils (>= 0.1.0rc16), cuems-utils (<< 0.1.1~)`, and `0.1.0rc16` has **never been built** as a `.deb` (`debian/changelog`: NOT YET BUILT). | Design D4's "`Depends: cuems-utils (>= <version that ships them>)`": the floor already names the version this feature will first build, which is convenient and fragile in equal measure — see clarification Q9. |
| M7 | `cuems-power-bridge`'s `postinst` **creates `/etc/cuems` if it is missing** ("cuems-common normally creates it"). A third package can own the directory's creation. | Extends design §2.3's owner table; confirms D6's `rmdir --ignore-fail-on-non-empty` is the right shape — no package may assume it created the directory. |
| M8 | `cuems-common`'s tests that pin the shipped map and the mirror are five, not one: `test_schema_mirror.py`, `test_shipped_network_map.py`, `test_network_map_example.py`, `test_documented_validation.py`, `test_network_map_conversion.py` (the last three reference the shipped paths or `debian/install`). | Brief §6 names only `test_schema_mirror.py` for retirement; the other four must be re-based or retired with it. |

---

## Clarifications

### Session 2026-09-25

- Q: `default_mappings.xml`'s per-field values for a fresh node, and whether `default_audio_output`
  holds an output **id** or an output **name** (OPEN-1)? → A: **Settle the id-vs-name spelling
  first, by consumption** — who actually reads the field (engine source, frontend, helpers), the
  method D15 used — and let the plan derive the seven values from that finding. Neither production
  file is transcribed. (Option C.)
- Q: Sentinel spellings for the required `name` and `ip` in the pristine `network_map.xml`
  self-entry? → A: `name` = `unprovisioned`, `ip` = `0.0.0.0`, so the placeholder describes itself
  and `--check` can match the words. (Option A.)
- Q: Handover order and the two version numbers? → A: **Fold the drop into `cuems-common`'s
  unreleased `1.3.0-23`**; `cuems-utils` ships the schemas in the first built `0.1.0rc16`. The
  pair lands together under the coordinated merge that the `xml-refactor-merge-candidate` tag
  marks — the existing tag, or the future one for this sequence — never as two independent
  releases. (Option B.)
- Q: Does retiring `cuems-config-node`'s `uuid1()` minting and the hardcoded template uuid land in
  this feature's `cuems-common` handover commit, or only the documented contract (M2/M3)? → A:
  **Land it in the handover.** `cuems-config-node` never mints; the shipped Avahi templates carry
  the sentinel; the contract document records both. (Option A.)
- *(Session 2026-09-28, analysis)* Q: What does `cuems-init-node` write for the map row's
  `name` and `ip` at install time, with no avahi and possibly no network? → A: **`name` = the OS
  hostname**; `ip` = the chosen interface's current IPv4 else `0.0.0.0`; nodeconf's `merge`
  refreshes both in place later (FR-025a).
- *(Session 2026-09-28, analysis)* Q: What if no MAC can be determined and `--mac` is absent? →
  A: **Refuse**, never write a sentinel MAC — the map is keyed by MAC, so two such nodes collide;
  `postinst` falls through to the placeholders (FR-025a). The authoritative link is `ethernet0`.
- *(Session 2026-09-28, plan phase)* Q: Who derives the Avahi record from `settings.xml` —
  `cuems-config-node` in `cuems-common`, or `cuems-nodeconf`? → A: **`cuems-nodeconf`**, as its
  sole writer, at every start and role change, refusing to start unprovisioned; nodeconf becomes
  integral and unmasked fleet-wide with the xml-refactor landing, which is what makes this the
  best shape (research R7/R7a, shape B). `cuems-config-node` only loses duties.
- Q: On a re-run, what happens to an operator's hand edit of a non-identity field in
  `settings.xml`? → A: **Kept, three-way.** A value that differs from what the tool itself last
  wrote is an operator decision and survives; the tool reports every such field as "modified,
  kept"; `--reset` discards them and returns the node to system defaults (upstream seed values
  plus the overlay), identity still preserved. Venue-specific configuration must survive; a
  return-to-defaults path must exist. (Option D, extended.)
- Q: `--check`'s exit-code contract? → A: **Four classes**: 0 coherent and provisioned; 1 mismatch
  between locations; 2 a location absent or unreadable; 3 the source carries the sentinel ("not
  provisioned"). A never-provisioned node is coherent but actionable, so it does not share the
  "done" code; the source's sentinel takes precedence over an absent Avahi record, which is
  expected on such a node. `postinst` never gates on the code. (Option B.)
- Q: Build a `default_mappings.xml` generator that feature 014 retires? → A: **Yes, deliberately**:
  generator, seed values and the `cuems-init-node` write path, with the retirement by 014
  recorded and no new consumer allowed to depend on them. (Option A.)
- Q: F1's writer annotations in the schemas — in or out? → A: **In, as one isolated commit**: the
  writer annotation goes into all six schemas, the six hashes in `test_schema_scope` move in that
  same commit for that reason alone, and the F1 check joins `test_duplication_flags`. (Option B.)

## User Scenarios & Testing *(mandatory)*

Every story below is sliced so that it stands alone: each can be built, tested, deployed and
demonstrated without the ones after it, and the P1 stories together are the minimum that makes
"a plain `apt install` leaves a node that loads and is unique" true.

### User Story 1 — The six schemas ship to `/etc/cuems`, and `cuems-common` hands its mirror over (Priority: P1)

An operator, a helper script, the editor, or `xmllint` opens any CUEMS XML document on a node
and follows its relative schema reference (`xsi:schemaLocation="… settings.xsd"`) to a real
file beside it in `/etc/cuems`, which is the schema the installed library actually uses. On
every node, after any install or upgrade of `cuems-utils`, the six `.xsd` files in `/etc/cuems`
are byte-identical to the library's bundled copies, and no other package ships or maintains a
copy of any of them.

**Why this priority**: viable on its own with no identity work at all. It closes the three live
"validates against a file nobody ships" defects (finding 1–3) and ends the schema drift measured
on both production machines. It is also the prerequisite for the handover's `Breaks`
choreography with `cuems-common`, which is the one cross-package change that can abort a
`dpkg -i`.

**Independent Test**: install the `.deb` on a host with no `/etc/cuems`; confirm six `.xsd`
files appear there, each byte-identical to the venv's bundled copy; confirm `cuems-display-setup`
and the editor's schema path resolve; upgrade a host carrying `cuems-common`'s old mirror and
confirm the mirror is replaced by the current schema with no `.dpkg-dist`/`.dpkg-old` sibling
left behind.

**Acceptance Scenarios**:

1. **Given** a host with no `/etc/cuems`, **When** the `cuems-utils` package is installed,
   **Then** `/etc/cuems/{settings,network_map,project_mappings,project_settings,script,hardware_outputs}.xsd`
   exist as regular files (not symlinks), owned by root, mode 0644, byte-identical to the
   library's bundled schemas.
2. **Given** a host carrying `cuems-common`'s stale `network_map.xsd` mirror (as both audited
   production hosts do), **When** `cuems-utils` is upgraded to this feature's version and
   `cuems-common` to its handover version — in either order, or together, **Then** the stale
   copy is replaced by the current schema, no `network_map.xsd.dpkg-dist`/`.dpkg-old` is created,
   and dpkg reports no file-overwrite conflict.
3. **Given** a host with the schemas installed, **When** the operator runs the validation
   command from `cuems-common`'s `docs/latency-tuning.md` (loading `/etc/cuems/settings.xsd`)
   or `cuems-display-setup` validates against `/etc/cuems/project_mappings.xsd`, **Then** both
   find the file and validate against the schema of the installed library.
4. **Given** a later `cuems-utils` version whose bundled schema changed, **When** the package is
   upgraded, **Then** `/etc/cuems/*.xsd` is replaced by the new schema **unconditionally**, with
   no prompt — the schema always matches the installed library (D4/D5), and the `.xsd` files are
   never conffiles.
5. **Given** the `cuems-common` sibling checkout at its handover version, **When** its test suite
   runs, **Then** no test asserts the existence of `etc/cuems/network_map.xsd` or the shipped
   `etc/cuems/network_map.xml` in that repository, and `debian/install` no longer lists either
   path.

---

### User Story 2 — The three documents are generated at build, shipped pristine, and installed only when absent (Priority: P1)

A package maintainer builds the `.deb`; the build generates the three default documents from
the schema descriptor and the seed values, deterministically, carrying the reserved sentinel
identity. The package ships them under `/usr/share/cuems/defaults/`, inside the manifest, where
`dpkg -V` can verify them and a drifted live file can be diffed against pristine. On install,
each of the three lands in `/etc/cuems` only if it is absent; an existing file — including a
hand-placed one, or one carrying the sentinel — is never modified by the package.

**Why this priority**: it is the half of "a node that loads" that needs no identity logic —
the documents exist, they are structurally complete against the schema, they are reproducible
across builds, and upgrade/`--reinstall`/remove-then-install cannot touch them. On its own it
leaves a node loadable *with the sentinel identity*, which is the honest "not provisioned"
state practice 7 defines, and which User Story 3 then specializes.

**Independent Test**: build the package twice from the same commit and confirm the three
generated documents are byte-identical across builds; install on a clean host and confirm the
three appear in `/etc/cuems` and validate against their schemas; place a marker file at each of
the three paths, `--reinstall`, and confirm all three markers survive byte-for-byte.

**Acceptance Scenarios**:

1. **Given** the source tree at any commit, **When** the package is built twice, **Then**
   `/usr/share/cuems/defaults/{settings,network_map,default_mappings}.xml` are byte-identical
   between the two builds, and each carries `00000000-0000-0000-0000-000000000000` as the uuid
   and `000000000000` as the MAC — never a freshly minted identity.
2. **Given** the three pristine documents, **When** each is validated against its schema (T1)
   and loaded through the library's strict read path (T1 and T2), **Then** all three load with
   no repair and no conversion, and the `LoadReport` for each is empty.
3. **Given** a host with no `/etc/cuems/*.xml`, **When** the package is installed, **Then** the
   three documents exist in `/etc/cuems` (specialized per User Story 3 when that story has
   landed; pristine copies otherwise).
4. **Given** a host where `/etc/cuems/settings.xml` exists with a real identity and the other
   two are absent, **When** the package is installed or upgraded, **Then** `settings.xml` is
   byte-identical before and after, and the two missing documents are created coherent with
   the identity `settings.xml` already carries (never with a second minted identity, never with
   the sentinel).
5. **Given** a host where all three exist, **When** the package is upgraded, re-installed with
   `--reinstall`, or removed (not purged) and installed again, **Then** all three are
   byte-identical before and after.
6. **Given** the schema gains a required field the seed values do not name, **When** the package
   is built, **Then** the build **fails** at generation time with a message naming the schema,
   the type, the field and the file to add the value to — the completeness guarantee from
   FR-034 of feature 008, preserved intact across the move to TOML.

---

### User Story 3 — `cuems-init-node` writes the coherent triple atomically, and `postinst` calls it (Priority: P1)

An operator runs `apt install cuems-utils` on a fresh node and does nothing else. The node
boots, `ConfigManager(load_all=True)` succeeds, and the node's uuid is a freshly minted uuid4
that no other node shares — present, and identical, in `settings.xml`, in its own row of
`network_map.xml`, and in its node entry of `default_mappings.xml`, including inside the
compound `<uuid>_<output>` strings that document carries. A provisioning engineer can run the
same tool later, with a site overlay, and the node's identity is preserved while the site's
values are applied across all three documents in one atomic step.

**Why this priority**: this is the feature's headline — the first time a plain package install
has ever produced a bootable node. It is also the tool feature 012 needs to exist before the
uuid schema can be narrowed (design §9.4). Nothing in it may risk the stack-blocking exit:
`postinst` invokes the tool in a mode that reads no operator input, and if the tool fails for
any reason `postinst` falls back to the pristine placeholders, warns, and exits 0.

**Independent Test**: install the package on two clean hosts (or containers) from the same
`.deb`; confirm `ConfigManager(load_all=True)` succeeds on both with no hand-placed file;
confirm the two uuids differ, both are uuid4, and neither is the sentinel; on one host,
sabotage the tool (e.g. make its interpreter unrunnable) before install and confirm the package
still configures successfully with the pristine placeholders in place and a warning in the
install output.

**Acceptance Scenarios**:

1. **Given** a clean host, **When** `cuems-utils` is installed, **Then** `ConfigManager(load_all=True)`
   succeeds against `/etc/cuems` with no file placed by anything other than dpkg and this
   package's `postinst`.
2. **Given** two clean hosts installed from the same `.deb`, **When** both installs complete,
   **Then** the two nodes carry different uuids, both uuid4, neither the sentinel, and each
   uuid appears in exactly the three documents on its own host with no stale sentinel token
   anywhere in them — including inside compound strings such as `default_video_output`.
3. **Given** a host whose `settings.xml` carries a real identity and one hand-edited field,
   **When** `cuems-init-node` is run again (with or without an overlay), **Then** the uuid and
   MAC are preserved, the hand-edited field is preserved and reported as "modified, kept" with a
   pointer to `--reset`, and every other value is re-applied across all three documents;
   reassignment of identity requires an explicit `--force-new-identity`, which warns loudly
   before writing.
3a. **Given** the same host, **When** `cuems-init-node --reset` is run, **Then** the hand-edited
   field returns to its system default (seed value, or overlay value if one applies), the list of
   reverted fields was printed before writing, and the identity is unchanged.
4. **Given** `cuems-init-node` fails part-way (e.g. the second of three writes cannot complete),
   **When** the failure occurs, **Then** the documents on disk are either all in their previous
   state or all in the new state — never a half-specialized triple — and the tool exits
   non-zero with a message naming the document that failed.
5. **Given** `postinst` invokes the tool and the tool fails or is unrunnable, **When** the
   package is configured, **Then** `postinst` copies the pristine placeholders for any of the
   three that are absent, prints a warning that names the tool and the command the operator
   should run, and exits 0 — the package configures, and every dependent package can configure
   after it.
6. **Given** a `settings.xml` that carries the sentinel identity (a hand-copied pristine file),
   **When** the package is installed or upgraded, **Then** `postinst` leaves the file untouched
   (it never modifies an existing file), `cuems-init-node --check` reports the sentinel with the
   words `NOT PROVISIONED`, and a plain `cuems-init-node` run specializes it.
7. **Given** the operator passes `--uuid` with a value that is not a uuid4, **When** the tool
   runs, **Then** it refuses before writing anything, because the only minter in the ecosystem
   (`cuemsutils.tools.Uuid`) raises on anything but a uuid4.

---

### User Story 4 — Seed values live in TOML with a `defaults.d` overlay, applied by `cuems-init-node` (Priority: P2)

A site engineer wants every node at a venue to carry, say, a different `controller_url` or an
explicit `output_latency_ms`. They drop a small TOML file into `/etc/cuems/defaults.d/` and run
`cuems-init-node`. The upstream seed values ship in `/usr/share/cuems/defaults/system-defaults.toml`,
are overwritten on every upgrade (so upstream never goes stale), and the site's overlay is never
shipped and never touched by the package (so site tweaks never prompt and never clobber). A
typo in the overlay fails loudly in the command the engineer just ran — never during an upgrade,
never in `postinst`.

**Why this priority**: it is the promotion of the values table out of Python (D7) into data
(D9) and its only consumer (D11). It stands alone: without it, the generator reads its values
from the Python table exactly as it does today and nothing else in the feature changes.

**Independent Test**: build the package and confirm the generated `settings.xml` is
byte-identical to the one generated from the Python table before the move; on an installed host,
write an overlay that changes one scalar, run the tool, and confirm the change appears in
`settings.xml` with identity preserved; write a malformed overlay and confirm the tool exits
non-zero with the file and line named and all three documents unchanged.

**Acceptance Scenarios**:

1. **Given** the seed values moved from the Python table to `system-defaults.toml`, **When**
   the package is built, **Then** the generated `settings.xml` is byte-identical to the one the
   Python table produced (the move changes no value).
2. **Given** an overlay file that sets one known scalar, **When** `cuems-init-node` runs,
   **Then** the value appears in `/etc/cuems/settings.xml`, every other value is the upstream
   default (or an operator edit the tool kept and reported), and the uuid and MAC are the ones
   the node already had.
2a. **Given** an overlay sets a field the operator had also hand-edited, **When** the tool runs
   without `--reset`, **Then** the hand edit wins and is reported as "modified, kept"; with
   `--reset`, the overlay value wins.
3. **Given** an overlay file with a syntax error, or one naming a field no schema declares,
   or one attempting to set `uuid` or `mac`, **When** `cuems-init-node` runs, **Then** it exits
   non-zero naming the file (and line, for a syntax error) and writes nothing.
4. **Given** the same malformed overlay is present, **When** the package is installed or
   upgraded, **Then** `postinst` succeeds and exits 0 — it does not read the overlay
   (`--no-overlay`), so the overlay cannot block the stack.
5. **Given** an integer-valued field such as `output_latency_ms`, **When** the overlay writes
   `35` and another overlay writes `"auto"`, **Then** the int/string distinction survives into
   the generated document (the reason TOML was chosen over a format without typed scalars).
6. **Given** several overlay files in `defaults.d`, **When** two set the same field, **Then**
   the later one in lexical filename order wins, and the tool reports which file supplied each
   overridden value when asked (`--verbose` or equivalent).

---

### User Story 5 — Purge removes only this package's paths; the last CUEMS package removed empties the directory (Priority: P2)

An administrator purges `cuems-utils` from a host that still carries `cuems-common`'s
conffiles, `cuems-power-bridge`'s private SSH key and the cluster identity. Only the paths this
package placed are removed — the three documents and the six schemas — and `/etc/cuems` is
removed only if it is then empty. A plain `remove` touches nothing under `/etc/cuems`, so node
identity survives a package removal. Purging the whole stack leaves no `/etc/cuems`.

**Why this priority**: it is the destructive half of the lifecycle and the one with a private
key in the blast radius. It stands alone because it only concerns paths User Stories 1 and 2
create; nothing else depends on it.

**Independent Test**: on a host carrying files from every `/etc/cuems` owner (or markers
standing in for them), purge `cuems-utils` alone and confirm every other package's file is
byte-identical and the directory still exists; purge every CUEMS package and confirm
`/etc/cuems` is gone.

**Acceptance Scenarios**:

1. **Given** a host where `/etc/cuems` holds this package's nine paths plus files from
   `cuems-common`, `cuems-power-bridge` and runtime helpers, **When** `cuems-utils` is purged,
   **Then** exactly the nine paths this package placed are gone, every other file is
   byte-identical, and `/etc/cuems` still exists.
2. **Given** the same host, **When** `cuems-utils` is *removed* but not purged, **Then**
   nothing under `/etc/cuems` changes.
3. **Given** a host where every CUEMS package has been purged, **When** the last one's `postrm`
   runs, **Then** `/etc/cuems` no longer exists.
4. **Given** a host where an operator placed an unrelated file in `/etc/cuems`, **When** every
   CUEMS package is purged, **Then** that file survives and so does the directory — the
   directory is removed only when empty, never recursively.
5. **Given** a host purged of `cuems-utils` and then installed again, **When** the install
   completes, **Then** the node carries a **new** uuid — purge destroys identity by design, and
   the migration guide says so in those words.

---

### User Story 6 — `cuems-init-node --check` reads all four identity locations and reports mismatches by path (Priority: P3)

An operator whose node fails with `Node with uuid … not found`, or whose node appears twice in
discovery, runs `cuems-init-node --check`. It reads `settings.xml`, `network_map.xml`,
`default_mappings.xml` and the Avahi service file, and reports each location's uuid, which ones
disagree with the source (`settings.xml`), whether any carries the sentinel, and what command
fixes it. It changes nothing.

**Why this priority**: it is what turns the `ValueError` into something actionable, and the
only thing that catches the silent Avahi mismatch (practice 6/8). It is P3 because the P1
stories make the mismatch rare; it stands alone because it reads only.

**Independent Test**: on a provisioned host, edit one of the four locations to a different
uuid and confirm `--check` names that path and exits non-zero; restore it and confirm `--check`
exits 0; confirm `--check` never writes.

**Acceptance Scenarios**:

1. **Given** a coherent node, **When** `--check` runs, **Then** it reports all four locations
   agreeing and exits 0.
2. **Given** `network_map.xml` lacks a row for this node's uuid (the empty-stub case measured on
   both production hosts), **When** `--check` runs, **Then** it names `network_map.xml`, states
   that the self-entry is missing, names the fixing command, and exits non-zero.
3. **Given** `/etc/avahi/services/cuems.service` carries a `uuid=` that differs from
   `settings.xml`, **When** `--check` runs, **Then** it names that path and states the two
   values — the one case nothing else in the ecosystem detects.
4. **Given** `settings.xml` carries the sentinel, **When** `--check` runs, **Then** it prints
   `NOT PROVISIONED` and exits 3 — even when the Avahi record is also absent,
   which it reports as expected for an unprovisioned node.
5. **Given** any of the four is missing or unreadable on a provisioned node, **When** `--check`
   runs, **Then** it reports the path and the reason and exits 2, distinct from a mismatch (1),
   so a script can tell "wrong" from "absent".
6. **Given** `--check` is invoked, **When** it completes with any exit code, **Then** no file
   under `/etc/cuems` or `/etc/avahi` has changed.

---

### User Story 7 — The packaging hygiene pass (Priority: P3)

A maintainer building the package finds `debian/` in the state its sibling repositories are
already in: `debhelper-compat (= 13)` in `Build-Depends` instead of `debian/compat 11`, a
current `Standards-Version`, no build artifacts under version control, and a generated
`postinst` that no longer claims to have been "added by dh_python2". The `pyvenv.cfg` check
remains the first thing verified on every build.

**Why this priority**: none of it changes what a node does. It is in scope because every file
it touches is a file this feature edits anyway, and because the intended CI/CD pipeline will run
lintian over the result.

**Independent Test**: build the package; confirm `debian/compat` is gone and
`debhelper-compat (= 13)` is in `Build-Depends`; confirm lintian reports no error on the
`Standards-Version`; confirm `git status` after a build shows no untracked build artifact.

**Acceptance Scenarios**:

1. **Given** the source tree, **When** the package is built, **Then** the build uses debhelper
   compat 13 declared through `Build-Depends`, and `debian/compat` does not exist.
2. **Given** the built package, **When** `dpkg-deb --fsys-tarfile <deb> | tar -xO ./usr/lib/cuems/pyvenv.cfg | grep '^home'`
   runs, **Then** it reports `home = /usr/bin` — the pyenv trap from the trap register.
3. **Given** a build has just completed, **When** `git status` runs, **Then** no build artifact
   (`debian/cuems-utils/`, `debian/.debhelper/`, `debian/files`, `*.substvars`,
   `debhelper-build-stamp`) appears as untracked or modified.
4. **Given** the generated maintainer scripts, **When** they are inspected, **Then** none
   claims provenance from `dh_python2`.

---

### Edge Cases

- **A partial triple on an upgraded host.** `settings.xml` carries a real identity but
  `network_map.xml` is `cuems-common`'s empty `<node_list/>` stub (both production hosts). The
  stub is *present*, so install-if-absent leaves it; the node is exactly as unbootable as today,
  no worse. `--check` names the missing self-entry; `cuems-init-node` seeds it by plain insert
  (practice 3), preserving every other row and its adoption flags. The migration guide MUST tell
  operators of existing hosts to run the tool once after upgrading.
- **`settings.xml` present but unparseable or schema-invalid.** `postinst` leaves it, creates
  nothing that would need an identity it cannot read, warns, exits 0. `--check` reports the
  path and the reason.
- **`/etc/cuems` not writable** (read-only root, or a permissions accident). `postinst` warns
  and exits 0; nothing is created. The next `--check` reports every path as absent.
- **The tool's interpreter is unrunnable** — the broken-symlink venv from the trap register, or
  a partial install. `postinst` copies the pristine placeholders and warns. The node then loads
  **with the sentinel identity**, which is a valid "not provisioned" state: two such nodes on one
  network would answer to one identity (practice 7), so the warning MUST say the node is not
  provisioned and MUST name the command that provisions it.
- **Two nodes imaged from one disk after install.** The sentinel protects against *package*
  imaging, not *disk* imaging: both clones carry the same real uuid4. This is outside the
  package's power to prevent; the migration guide MUST state that imaging workflows purge before
  imaging, or run `cuems-init-node --force-new-identity` on each clone.
- **`--force-new-identity` on an adopted node.** The old row in `network_map.xml` is replaced
  by the new identity's row; the node must be re-adopted by the controller. The tool warns
  before writing and names the old and new uuids. The Avahi record is re-derived by
  `cuems-nodeconf` at its next start (D14, R7) — the tool says to restart it rather than
  touching the record.
- **`cuems-nodeconf` writes `network_map.xml` while the tool runs.** On a fresh install no
  service is running yet. On a re-run, the operator is told to stop `cuems-nodeconf` first; the
  tool's atomic replace guarantees the file is never half-written, but a discovery pass after
  the replace could reintroduce a stale row. The tool MUST warn when it detects the nodeconf
  unit active.
- **The overlay names `uuid` or `mac`.** Refused: identity is not a default and cannot be
  overlaid. `--uuid`/`--mac` on the command line are the only explicit route, and `--uuid`
  goes through the single minter's validation.
- **A hand edit and a changed upstream default collide.** Upstream ships a new default for a
  field the operator had edited: the operator's value stays (it differs from what the tool last
  wrote), and the report shows both values so the operator can choose `--reset` or leave it.
  Upstream never silently wins over a venue decision.
- **The seed values name a field the schema no longer declares.** The generator MUST fail the
  build naming the stale entry, symmetric with the missing-entry failure (FR-034's guarantee in
  both directions), so the TOML cannot silently accumulate dead keys.
- **A `.dpkg-dist`/`.dpkg-old` sibling already exists** beside a document (as on one production
  host). `postinst` neither removes nor reads it. `--check` MAY list such siblings as
  informational. Purge removes only the nine named paths, so the siblings survive a purge — this
  is deliberate: they are the operator's, not the package's.
- **The old `cuems-common` is purged after the handover.** Its `network_map.xml` was a conffile;
  dpkg removes obsolete conffiles on purge of the package that owned them. The handover MUST
  ensure `cuems-common`'s new version relinquishes the conffile in a way that leaves the live
  file in place through upgrade **and** through a later purge of `cuems-common` — the file is
  the cluster topology, and losing it on an unrelated package's purge is a field incident.
- **`network_map.xml` on an upgraded host still carries the retired `<node_type>` vocabulary**
  (both production hosts). This feature converts nothing at install (D8); the read path
  converts in memory, and `cuems-common`'s existing `cuems-migrate-network-map` remains the
  batch conversion. `cuems-init-node` MUST load through the strict read path, so it reads such
  a file correctly, and MUST write back in the current shape.
- **Build on a host whose `python3` is not 3.11** (the intended trixie build). Every new path
  this feature adds is version-free (`/usr/share/cuems/...`, `/etc/cuems/...`) and the
  generator is invoked through the built venv's own `bin/python`, never through a
  `lib/python3.N` path, so the addition is neutral to the interpreter version. The existing
  pin stays; see Out of Scope.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Shipping the schemas (D4)

- **FR-001**: The package MUST install all six bundled schemas to `/etc/cuems/<name>.xsd` as
  regular files (not symlinks into the venv), byte-identical to the library's bundled copies,
  on every install and upgrade, unconditionally and without prompting.
- **FR-002**: The pristine copies of the six schemas MUST live in the package manifest under
  `/usr/share/cuems/schemas/` so that `dpkg -V` verifies them and a drifted live file can be
  diffed against pristine. (Their non-conffile status is FR-020's.)
- **FR-003**: `cuems-common` MUST drop `etc/cuems/network_map.xsd` and `etc/cuems/network_map.xml`
  from its `debian/install`, retire `tests/test_schema_mirror.py`, and re-base or retire the four
  other tests that pin the shipped paths (M8). Its `Depends` on `cuems-utils` MUST name the first
  `cuems-utils` version that ships the schemas.
- **FR-004**: `cuems-utils` MUST declare `Breaks` on every `cuems-common` version that still
  ships either path (`<< 1.3.0-23~`), so apt upgrades the pair together and old `cuems-common` can
  never record an `.xsd` this package rewrote as its conffile. `Replaces` is **deliberately
  absent**: this package ships nothing under `/etc` in its manifest (D5), so there is no file
  overlap for `Replaces` to license (research R3).
- **FR-005**: The custody transfer of `/etc/cuems/network_map.xml` MUST leave an existing live
  file byte-identical through the upgrade of both packages in any order, MUST leave no
  `.dpkg-bak`/`.dpkg-dist`/`.dpkg-old` sibling behind, and MUST leave the file in place through a
  later purge of `cuems-common` (edge case above). The `.xsd` is simply replaced.
- **FR-006**: The three live schema-path defects (findings 1–3) MUST resolve on an installed
  host with no change to their callers: the paths they name exist and hold the current schema.

#### Generated defaults (D2, D3, D7, D17)

- **FR-007**: The three default documents (`settings.xml`, `network_map.xml`,
  `default_mappings.xml`) MUST be generated at package build from the schema descriptor and the
  seed values — no committed default `.xml` exists in the tree — and installed to
  `/usr/share/cuems/defaults/` inside the package manifest.
- **FR-008**: Generation MUST be deterministic: two builds of the same commit produce
  byte-identical documents. The generator MUST emit the reserved sentinel identity
  (`00000000-0000-0000-0000-000000000000`, MAC `000000000000`) and MUST NOT mint a uuid at
  build time.
- **FR-009**: Each generated document MUST validate against its schema and load through the
  strict read path with an empty `LoadReport` (no repair, no conversion), and MUST carry the
  current `doc_version` for its schema.
- **FR-010**: The completeness guarantee MUST hold in both directions: a required schema field
  with no seed value fails the build naming schema, type, field and the file to edit; a seed
  value naming a field no schema declares fails the build naming the stale entry.
- **FR-011**: The generated `network_map.xml` MUST contain exactly one row — this node's
  self-entry at the sentinel uuid, with `node_role` `firstrun` (practice 4), `name` `unprovisioned` and `ip`
  `0.0.0.0` as the placeholders for the remaining required fields, and the sentinel MAC.
- **FR-012**: The generated `default_mappings.xml` MUST contain exactly one node entry at the
  sentinel uuid, with the seven root scalars set per the plan's per-field decision — which
  MUST first settle, by consumption, whether `default_audio_output` (and its siblings) hold an
  output **id** or an output **name**, and MUST record which reader decided it — and MUST be generated by this feature even though feature 014 later
  retires the document. The generator, its seed-values section and the tool's write path for
  it are **scheduled for retirement with 014**: each MUST say so where it is declared, and no
  new consumer in this feature MAY depend on `default_mappings.xml` beyond what `ConfigManager`
  already requires.
- **FR-013**: The seed values table MUST leave `descriptor.py` and become package data (the
  single copy code reads); its shipped locations and precedence are FR-034's. The generator's
  output MUST be byte-identical before and after the move (US4 scenario 1). `DECLARED_DEFAULTS`
  stays in Python (D10, already satisfied).
- **FR-014**: The generator MUST continue to emit optional player-section fields explicitly
  (D17, already landed) — this feature MUST NOT regress the widened generator.

#### Install semantics (D5, D13, the dominant constraint)

- **FR-015**: `postinst` MUST exit 0 on every path. Every step either succeeds, or degrades to
  copying the pristine placeholder for any absent document, prints a warning naming what failed
  and the command that repairs it, and continues.
- **FR-016**: `postinst` MUST NOT modify, rewrite, rename or remove any existing file under
  `/etc/cuems` — including one carrying the sentinel, one that is unparseable, one that is a
  `cuems-common` stub, and one placed by hand. The only files it creates are the three documents
  when absent (and the schemas, which are the package's own and always replaced).
- **FR-017**: `postinst` MUST create the three documents only when absent, per file, and MUST
  leave any present one untouched — including a `cuems-common` stub map or a sentinel document,
  which `cuems-init-node --check` reports and a plain `cuems-init-node` run repairs. When
  `settings.xml` is absent, it MUST obtain a freshly minted uuid4 by invoking `cuems-init-node`
  in its no-operator-input mode (`--no-overlay --install-missing`); when `settings.xml` is present
  and readable, any absent sibling MUST be created coherent with the identity `settings.xml`
  carries, and `settings.xml` itself MUST NOT be rewritten.
- **FR-018**: `postinst` MUST NOT read `/etc/cuems/defaults.d/` (D11). A malformed overlay MUST
  have no effect on install or upgrade.
- **FR-019**: Custom `postinst` logic MUST run after dh-virtualenv's own autoscript (after the
  `#DEBHELPER#` token), so the venv interpreter is settled before the tool is invoked.
- **FR-020**: Nothing under `/etc/cuems` MUST be a conffile of this package — neither the six
  schemas nor the three documents. `DEBIAN/conffiles` contains no `/etc/cuems` path.
- **FR-021**: The identity in an existing `settings.xml` MUST survive upgrade, `--reinstall`,
  and remove-then-install byte-identically (D13's table), and MUST be destroyed by purge and
  nothing else.
- **FR-022**: On a stack install, `cuems-init-node` MUST complete before any engine starts. The
  plan MUST confirm (not assume) the ordering: dpkg configures `cuems-utils` before
  `cuems-common` by dependency, and `cuems-common`'s `postinst` injects no service start (M5).
  A test in the plan MUST pin the premise.

#### `cuems-init-node` (D11, D12, D13, practices 1–5, 7, 8)

- **FR-023**: `cuems-init-node` MUST be a new public entry point of this library, declared
  beside `cuems-convert-documents`, and recorded in the public API surface golden as a sanctioned
  change.
- **FR-024**: It MUST be installed where the shared venv's one-way constraint permits it to
  import `cuemsutils` (the venv's own `bin/`, like `cuems-convert-documents`), and `postinst`
  MUST invoke it by absolute path through the venv interpreter. Any `/usr/bin` convenience
  (symlink or wrapper) MUST NOT itself import `cuemsutils` under `/usr/bin/python3`
  (clarification Q5, recommended default stated in Assumptions).
- **FR-025**: It MUST read the pristine defaults, the overlay (unless `--no-overlay`), and any
  existing `/etc/cuems/*.xml`; assign identity — preserved if the existing `settings.xml`
  carries a real uuid, minted through `cuemsutils.tools.Uuid` if absent or the sentinel, or taken
  from `--uuid`/`--mac` — and write the documents **this run writes** (all three on a plain run;
  only the absent ones under `--install-missing`) as one atomic set: either every document the
  run set out to write is replaced, or none is.
- **FR-025a**: Identity-adjacent fields MUST be derived as follows, at install time and without
  avahi or a live network (clarified 2026-09-28): **`mac`** from `--mac`, else the `ethernet0`
  link (the stable udev name `cuems-common` enforces and `cuems-config-node` uses today), else the
  first non-loopback, non-virtual physical interface under `/sys/class/net`; when none is found
  the tool MUST **refuse** (exit 1, naming the reason) rather than write a sentinel MAC — the map
  is keyed by MAC, so a sentinel MAC on a live node is the practice-7 collision in another field.
  **`name`** is the OS hostname (`socket.gethostname()`). **`ip`** is the chosen interface's
  current IPv4 address, else `0.0.0.0`; `cuems-nodeconf`'s `merge` refreshes `name` and `ip` in
  place at its next discovery pass (it matches by uuid and keys by MAC). Under `postinst`, a
  refusal falls through to the pristine placeholders and the `NOT PROVISIONED` warning.
- **FR-026**: Specialization MUST replace the sentinel token everywhere it occurs in the three
  documents, including inside compound strings (`<uuid>_<output_id>`), by literal token
  substitution (design §10.2's rule) — a structural rewrite of `uuid` elements alone is not
  acceptable, because it leaves compound strings stale and schema-valid.
- **FR-027**: Re-run policy: identity is preserved; operator edits are preserved; everything
  else is re-applied. A field whose on-disk value differs from the value the tool itself **last
  wrote** is an operator decision and MUST be kept; a field whose on-disk value equals what the
  tool last wrote MUST be re-computed from the current seed values and overlay. The tool MUST
  report every kept field as "modified, kept" (path, field, on-disk value) and MUST tell the
  operator that `--reset` returns the node to system defaults.
- **FR-027a**: To make FR-027 possible the tool MUST record what it last wrote (a write record,
  outside the three documents, in a package-owned state location the plan names and `postrm
  purge` removes). When the record is absent — a host provisioned before this feature, or a
  record lost — every difference from the computed output MUST be treated as an operator edit
  and kept, and the tool MUST say the record was missing.
- **FR-027b**: `--reset` MUST discard operator edits to non-identity fields across all three
  documents and re-apply upstream seed values plus the overlay, MUST preserve identity (only
  `--force-new-identity` changes it), MUST list every field it is about to revert before
  writing, and MUST leave other nodes' rows and adoption flags in `network_map.xml` untouched
  (they are `cuems-nodeconf`'s, never "defaults").
- **FR-028**: Reassignment of identity MUST require `--force-new-identity`, MUST warn loudly
  naming the old and new uuids, and MUST state that the node must be re-adopted and that
  `cuems-nodeconf` must be restarted so the Avahi record is re-derived.
- **FR-029**: The self-entry in `network_map.xml` MUST be seeded by plain insert into the node
  index (practice 3), never through `merge`, so that other nodes' rows and their `adopted`/
  `online` flags are preserved. The insert MUST go through one library primitive
  (`NodeIndex.ensure`, added by this feature inside `0.1.0rc16`) that inserts the caller's node
  object **by reference** — honouring the aliasing contract pinned upstream on 2026-09-28 — so
  `cuems-nodeconf`'s feature 003 can seed from `settings.xml` through the same call. The row MUST be keyed by MAC and matched by uuid (practice 5),
  with `node_role` `firstrun` unless the file already carries a role for this uuid.
- **FR-030**: The tool MUST load existing documents through the strict read path (so a
  version-old file converts in memory) and write in the current shape, and MUST NOT write a
  routine backup — the no-routine-backups rule stands; backups belong to the operator-triggered
  conversion tool only.
- **FR-031**: On any failure the tool MUST exit non-zero, name the document and reason, and
  leave the triple in its previous state. Only `postinst` may translate that into a warning and
  a 0 exit; the tool itself never hides a failure.
- **FR-032**: `--check` MUST read all four identity locations (`settings.xml`, `network_map.xml`,
  `default_mappings.xml`, `/etc/avahi/services/cuems.service`), report each value by path,
  report every mismatch against the source (`settings.xml`), report the sentinel as
  `NOT PROVISIONED`, name the fixing command, change nothing, and exit with one of
  four codes: **0** coherent and provisioned; **1** at least one location disagrees with the
  source; **2** at least one location absent or unreadable; **3** the source (`settings.xml`)
  carries the sentinel. Precedence when several apply: 3 over 2 over 1 — a not-provisioned node
  with no Avahi record (expected after FR-040a) exits 3 and reports the absent record as
  expected. `postinst` MUST NOT gate on `--check`'s exit code.
- **FR-033**: The tool MUST refuse an overlay that sets `uuid` or `mac`, a `--uuid` that is not
  a uuid4, and any overlay key that no schema declares — each before writing anything.

#### Seed values and the overlay (D9, D11)

- **FR-034**: Upstream seed values MUST ship in `/usr/share/cuems/defaults/system-defaults.toml`,
  not a conffile, always overwritten on upgrade. The operator overlay directory MUST be
  `/etc/cuems/defaults.d/`, never shipped, never touched by the package, applied only by
  `cuems-init-node`, in lexical filename order with later files winning.
- **FR-035**: The overlay MUST preserve the typed-scalar distinction the schema needs (`35` vs
  `"auto"` for `output_latency_ms`).
- **FR-036**: Applying an overlay MUST fail loudly (file, and line for syntax errors) and write
  nothing on any error.

#### Purge (D6)

- **FR-037**: `postrm purge` MUST remove exactly the nine paths this package placed under
  `/etc/cuems` (three documents, six schemas) plus the tool's write record (FR-027a, outside
  `/etc/cuems`), and then remove `/etc/cuems` only if empty.
  It MUST NOT remove recursively and MUST NOT remove any path it did not place, including
  `.dpkg-*` siblings, `defaults.d/`, and every other package's files.
- **FR-038**: `postrm remove` (not purge) MUST touch nothing under `/etc/cuems`.

#### The identity invariant and the `cuems-common` contract (D14, practices 1, 6, 7, 8)

- **FR-039**: `cuemsutils.tools.Uuid` MUST remain the only uuid minter this feature uses; the
  feature MUST NOT add a second one, and M2's second minter (`cuems-config-node`'s
  `uuid1()`) is retired by the handover (FR-040a).
- **FR-040**: D14's contract — the Avahi TXT `uuid=` value is derived from the provisioned
  `/etc/cuems/settings.xml`, never independently generated or hand-entered — MUST be recorded in
  `cuems-common`'s existing `docs/node-identity-contract.md` (M1), naming: the source document,
  the sole minter, the tool that verifies (`--check`), the second minter to retire (M2), and the
  hardcoded production uuid in the shipped templates (M3) as the live violation the contract
  closes.
- **FR-040a**: The `cuems-common` handover MUST strip `cuems-config-node` of uuid minting and
  of every Avahi/template duty, MUST ship the three `usr/share/cuems/cuems.service.*` templates
  with the sentinel uuid as package content that no tool rewrites, and MUST retire the dead
  template-copy sudoers rules. **`cuems-nodeconf` is the sole writer of
  `/etc/avahi/services/cuems.service`**: at every start and every role change it derives the
  record from `/etc/cuems/settings.xml`, and it refuses to start on a node whose `settings.xml`
  is absent or carries the sentinel — an unprovisioned node announces nothing. After the
  handover, `cuemsutils.tools.Uuid` is the only minter in the ecosystem. (Clarified 2026-09-28:
  research R7a, shape B; the `cuems-nodeconf` change is delivered by that repository's feature
  `003-startup-readiness` inside the same coordinated merge, rendering **before** its IPC socket is
  created, with the existing mutual `Breaks` covering the transition — research R20.)
- **FR-041**: The sentinel `00000000-0000-0000-0000-000000000000` MUST be treated as "not
  provisioned" by every tool this feature adds, spelled **`NOT PROVISIONED`** wherever it is
  printed (one constant, asserted verbatim in the tool's tests and the script tests), and MUST
  never be written to a live node by `cuems-init-node` — only `postinst`'s degraded fallback may
  leave it there, with the warning FR-015 requires.

#### Packaging hygiene (design §4.1)

- **FR-042**: `debian/compat` MUST be replaced by `debhelper-compat (= 13)` in `Build-Depends`;
  `Standards-Version` MUST be raised to the current release the sibling packages use or newer;
  the generated maintainer scripts MUST NOT claim `dh_python2` provenance; build artifacts MUST
  remain ignored (already done) and none MAY be committed.
- **FR-043**: `debian/rules` MUST keep the absolute-path interpreter pin, and the built package
  MUST report `home = /usr/bin` in `pyvenv.cfg`.
- **FR-044**: Nothing this feature adds to `debian/` MAY assume a single Debian flavour or embed
  an interpreter version in a new path; the generator MUST be invoked through the built venv's
  `bin/python`.

#### Documentation and record

- **FR-045**: The feature MUST produce a migration guide covering: what an operator of an
  existing host must run after upgrading (the partial-triple edge case); that purge destroys
  identity; the disk-imaging hazard; the `--check` exit codes; the `cuems-common` handover
  order and versions; and a **pointer** to the manual hardware verification, whose one record is
  entry §5 of `cuems-nodeconf`'s hardware-verification ledger (decision D3, 2026-09-28) — the
  guide carries the pointer and the acceptance line (unmask, enable and start `cuems-nodeconf`;
  `cuems-init-node --check` exit 0 after the unmask and after a reboot), not a second copy of the
  steps.
- **FR-046**: The planning documents MUST be corrected for M1–M9 (M9: the suite's dependence on a
  host `/etc/cuems`, found at plan time) in this feature's pass, with the correction recorded (not
  applied silently), per the execution document's own §0 rule.
- **FR-047**: Each of the six schemas MUST carry an `xs:annotation` on its root element naming
  the document's sole writer (F1, design §8.2): `settings` → `cuems-init-node`; `network_map` →
  `cuems-nodeconf` for topology rows, `cuems-init-node` for this node's self-entry (the seam of
  practice 2, stated at element granularity); `project_mappings` → `cuems-editor` for a
  project's `mappings.xml`, `cuems-init-node` for `default_mappings.xml` until 014 retires it;
  `script` and `project_settings` → `cuems-editor`; `hardware_outputs` → `cuems-hardware-discovery`
  for the probed inventory and `cuems-nodeconf` for the transcribed geometry. The annotations
  MUST land in **one isolated commit** that also updates the six hashes in `test_schema_scope`
  and adds the F1 check (every schema declares exactly one writer annotation) to
  `test_duplication_flags`. No document on disk changes and no `doc_version` moves — an
  annotation is not a shape change.
- **FR-UX-001**: `cuems-init-node`'s flags, messages and exit codes MUST follow the conventions
  `cuems-convert-documents` established (argparse, path-first messages, non-zero on any skipped
  or failed document); the `NOT PROVISIONED` wording MUST be identical in `--check` and in
  `postinst`'s fallback warning.
- **FR-PERF-001**: The feature MUST define and validate three budgets (constitution IV; a
  previous feature was pulled up for declaring this inapplicable): `postinst` wall time,
  `cuems-init-node` wall time (write and `--check`), and the library suite's per-test figure.
  Proposed values are in Success Criteria; the plan measures on the reference hardware class
  and records the numbers in `baseline.md`.

### Key Entities

- **Pristine defaults**: the three generated documents plus `system-defaults.toml` under
  `/usr/share/cuems/defaults/`. In the manifest, never read at runtime, always carry the
  sentinel, replaced on every upgrade.
- **Shipped schemas**: the six `.xsd` under `/usr/share/cuems/schemas/` (manifest) and their
  installed copies under `/etc/cuems/` (not conffiles, always replaced).
- **Live documents**: `/etc/cuems/{settings,network_map,default_mappings}.xml`. Created by
  `postinst` when absent, owned thereafter by their sole writers (`cuems-init-node` for
  `settings.xml`; `cuems-nodeconf` for topology rows in `network_map.xml`; `cuems-init-node` for
  the self-entry and for `default_mappings.xml`).
- **Node identity**: the uuid4 + MAC pair whose source is `settings.xml`, mirrored in the two
  other documents (bare and inside compound strings) and in the Avahi TXT record.
- **The sentinel**: `00000000-0000-0000-0000-000000000000` / `000000000000`, meaning "not
  provisioned". Reserved; never a real identity.
- **Seed values**: the upstream per-field table, keyed by (schema type, field), typed scalars,
  one file, read at build and by `cuems-init-node`.
- **Overlay**: operator-authored TOML fragments in `/etc/cuems/defaults.d/`, same key space as
  the seed values minus identity, applied only by `cuems-init-node`.
- **Check report**: `--check`'s output — per location: path, value found, agreement with the
  source, sentinel status; plus the fixing command and an exit code class.
- **Write record**: what `cuems-init-node` last wrote, per document and field, kept outside
  the three documents in a package-owned state location; the reference that distinguishes an
  operator edit from the tool's own previous output (FR-027a).
- **The owned paths**: the nine under `/etc/cuems` plus the write record — the exact set
  `postrm purge` may remove.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `ConfigManager(load_all=True)` succeeds on a machine whose `/etc/cuems` was
  populated only by `dpkg -i` of this package, with no hand-placed file.
- **SC-002**: Upgrade, `--reinstall`, and remove-then-install each leave an existing
  `settings.xml`, `network_map.xml` and `default_mappings.xml` byte-identical (measured by
  checksum before and after).
- **SC-003**: Purge of `cuems-utils` alone leaves every other package's file under `/etc/cuems`
  byte-identical and the directory present; purge of the whole stack leaves no `/etc/cuems`.
- **SC-004**: `dpkg-deb --fsys-tarfile <deb> | tar -xO ./usr/lib/cuems/pyvenv.cfg | grep '^home'`
  reports `home = /usr/bin` for every build shipped.
- **SC-005**: Two builds of the same commit produce byte-identical
  `/usr/share/cuems/defaults/*.xml` and `system-defaults.toml`.
- **SC-006**: After install, each `/etc/cuems/*.xsd` is byte-identical to the bundled schema of
  the installed library (six of six), and on a host that carried `cuems-common`'s stale mirror
  the count of `network_map.xsd.dpkg-*` siblings after the upgrade is zero.
- **SC-007**: Two clean hosts installed from one `.deb` end with two different uuid4 identities,
  neither the sentinel, and a recursive search of each host's `/etc/cuems` for the sentinel
  token returns nothing.
- **SC-008**: With `cuems-init-node` made unrunnable before install, the package still
  configures (exit 0), a warning containing "not provisioned" and the repair command appears in
  the install output, and every dependent package configures after it.
- **SC-009**: A malformed overlay in `defaults.d` changes nothing about install or upgrade
  (exit 0, identical documents), and makes `cuems-init-node` exit non-zero naming the file with
  all three documents unchanged.
- **SC-010**: `--check` exits 0 on a coherent provisioned node, 1 when any location disagrees
  with `settings.xml`, 2 when a location is absent or unreadable, 3 when `settings.xml` carries
  the sentinel (also when the Avahi record is absent); it never modifies a file (checksums before
  and after equal).
- **SC-010a**: A hand-edited non-identity field survives a plain re-run byte-for-byte and is
  named in the tool's output as kept; after `--reset` it equals the system default and the uuid
  is unchanged. On a host with no write record, zero on-disk values change on a plain re-run.
- **SC-011**: The three live schema-path defects resolve on an installed host with no change to
  their callers.
- **SC-012**: The `cuems-common` sibling at its handover version has zero tests asserting the
  shipped `network_map.{xml,xsd}` and zero `etc/cuems/network_map.*` lines in `debian/install`,
  and its `docs/node-identity-contract.md` states D14's derivation rule and names the retired
  second minter; `cuems-config-node` contains no uuid minting call, and no shipped Avahi template
  contains a non-sentinel uuid.
- **SC-PERF-001** (proposed here; **re-based on measurement in `plan.md`/research R10 — those figures bind**: tool write ≤ 4 s, `--check` ≤ 3 s, `postinst` ≤ 10 s fresh / ≤ 2 s upgrade, 60 s hard cap; the values below are the original proposal kept for the record):
  - `postinst` wall time on the reference node hardware, excluding dh-virtualenv's own
    autoscript: **≤ 5 s** on a fresh install (one tool invocation), **≤ 1 s** on an upgrade
    where all three documents exist (no invocation).
  - `cuems-init-node` write mode: **≤ 2 s** wall, cold process, including interpreter start,
    library import and three atomic writes; `--check`: **≤ 2 s** wall, cold.
  - The library suite's per-test figure stays within **110%** of the figure measured at plan
    start (the execution document's 2719-test audit is the reference population); a regression
    is recorded as such, never restated as passing.
- **SC-QUALITY-001**: No new lint, type or deprecation warning in the default project tooling;
  the public API surface golden changes by exactly the new entry point and nothing else.
- **SC-TEST-001**: Every functional requirement above has at least one automated test that
  fails before the implementation and passes after it. Package-lifecycle criteria (SC-001–003,
  SC-006–010) are exercised in a container or chroot as an integration test the plan defines;
  the schema-hash pin (`test_schema_scope`) moves exactly once, in FR-047's annotation
  commit, and in no other commit of this feature.

---

## Clarification register

Carried from the (since deleted) `specs/planning/011-first-install-specify-prompt.md` §4, extended by today's
measurements. Eight are answered (three at specify time, five in the `/speckit.clarify` session —
see "Clarifications" above). The three that remain (Q4, Q5, Q6) are confirmable by test or by
reading the build tooling and are **deferred to the plan** with their recorded defaults; none
changes what the feature delivers.

| Q | Topic | State in this spec |
|---|---|---|
| Q1a | **OPEN-1** — `default_mappings.xml`'s per-field values for a *fresh, unconfigured* node (`number_of_nodes`, the six `default_*_input`/`_output`), and whether `default_audio_output` holds an output **id** or an output **name** (the two production hosts disagree; one is wrong). | **Answered (C)**: spelling settled by consumption in the plan; values derived from it. FR-012. |
| Q1b | The pristine `network_map.xml` self-entry's placeholders for the required `name` and `ip` (practice 4 derives them at init time; the pristine copy needs a sentinel spelling). | **Answered (A)**: `unprovisioned` / `0.0.0.0`. FR-011. |
| Q2 | Build a `default_mappings.xml` generator that feature 014 retires. | **Answered (A)**: built deliberately, retirement recorded. FR-012. |
| Q3 | OPEN-2 — does the editor need the XSDs? | **Closed by M4**: yes, `/etc/cuems/script.xsd`. Ship all six regardless. |
| Q4 | OPEN-3 — `postinst` before first engine start. | M5 gives the mechanism; **deferred to the plan**, which pins it by test (FR-022). |
| Q5 | OPEN-4 — where `cuems-init-node` lives and how `postinst` invokes it. | **Deferred to the plan** with A1 as the default (venv `bin/`, absolute-path invocation, optional `/usr/bin` symlink); the venv constraint leaves no other location. |
| Q6 | How the generator runs at build (after `dh_virtualenv`, through the built venv's interpreter, into the staging tree) and its neutrality to a trixie build. | **Deferred to the plan** with A2 as the default; confirm against dh-virtualenv's autoscript ordering. |
| Q7 | `--check`'s exit-code contract vs. `postinst`'s never-fail rule. | **Answered (B)**: four classes, 0/1/2/3, precedence 3 > 2 > 1. FR-032, A4. |
| Q8 | Re-run on a changed overlay may overwrite an operator's hand edit of `settings.xml`. | **Answered (D, extended)**: operator edits are kept and reported; `--reset` returns to defaults. FR-027/027a/027b. |
| Q9 | Handover order and the two version numbers. | **Answered (B)**: `cuems-common 1.3.0-23` drops the paths; `cuems-utils 0.1.0rc16` ships them; both land under the `xml-refactor-merge-candidate` coordinated merge. A3. |
| Q10 | *New (M2/M3)*: does retiring `cuems-config-node`'s `uuid1()` minting and the hardcoded template uuid land in this feature's `cuems-common` handover commit, or is it recorded in the contract as `cuems-common`'s follow-up? | **Answered (A)**: lands in the handover. FR-040a. |
| Q11 | *New*: F1 (one writer per document, declared in each schema's `xs:annotation`) is "packaging work" per the execution document §3.3, and every schema hash would move. | **Answered (B)**: in scope, one isolated hash-updating commit. FR-047. |

---

## Assumptions

- **A1 — Entry-point location (Q5 default)**: `cuems-init-node` is declared in
  `[project.scripts]` and lands in `/usr/lib/cuems/bin/`, exactly as `cuems-convert-documents`
  does, with a shebang rewritten to the venv interpreter by dh-virtualenv. `postinst` invokes
  `/usr/lib/cuems/bin/cuems-init-node` by absolute path. A `/usr/bin/cuems-init-node` symlink
  via `debian/cuems-utils.links` is acceptable because a symlink to a venv script executes under
  the venv interpreter, not `/usr/bin/python3`; a wrapper that itself imports `cuemsutils` is not.
- **A2 — Build mechanics (Q6 default)**: `debian/rules` runs the generator in
  `override_dh_virtualenv` after `dh_virtualenv`, as
  `debian/cuems-utils/usr/lib/cuems/bin/python -m <generator module> --out debian/cuems-utils/usr/share/cuems/defaults/`,
  then installs the six schemas and the TOML into the staging tree. The venv's `bin/python` is
  runnable on the build host because it is pinned to `/usr/bin/python3`. No path added contains
  `python3.11`.
- **A3 — Handover order and versions (Q9, answered)**: `cuems-utils` ships the schemas in the
  first built `0.1.0rc16` `.deb`, with `Breaks`/`Replaces: cuems-common (<< 1.3.0-23)`;
  `cuems-common`'s unreleased `1.3.0-23` entry absorbs the drop of the two paths and keeps
  `Depends: cuems-utils (>= 0.1.0rc16)`. Because `rc16` has never been built (M6), the existing
  floor already names the shipping version. The pair is not two releases: both land under the
  coordinated merge the `xml-refactor-merge-candidate` tag marks (D27), so apt only ever sees
  them together and the `Breaks` is a safety net rather than the ordering mechanism.
- **A4 — Exit codes (Q7, answered)**: `--check` uses 0 = coherent and provisioned,
  1 = mismatch, 2 = absent or unreadable, 3 = sentinel in the source; the first three map onto
  the convention `cuems-common`'s own `apply-identity` documents (0 no drift / 1 drift /
  2 error), and 3 is the class that convention lacks because it never had a "never provisioned"
  state to name. Write mode uses 0 / 1.
- **A5 — Overlay precedence**: files in `defaults.d` apply in lexical filename order, later
  wins, the sysctl/systemd convention.
- **A6 — `postinst`'s partial-triple rule**: "absent" is evaluated per file. When
  `settings.xml` exists and parses, its identity is the identity; the tool is invoked in a mode
  that creates only the missing siblings and never rewrites `settings.xml`. When `settings.xml`
  is absent, the tool mints and writes all three. The exact flag is the plan's.
- **A7 — Reference hardware for the budgets**: the N97-class node the sibling packaging already
  targets; the plan records the exact machine.
- **A8 — The pristine fallback is loadable**: three pristine documents sharing the sentinel are
  mutually coherent, so a node left with them by the degraded path loads, in the "not
  provisioned" state, rather than raising.
- **A9 — the Avahi record's writer**: `/etc/avahi/services/cuems.service` is derived from
  `settings.xml` by `cuems-nodeconf` at every start and role change (D14, research R7, decided
  2026-09-28); the templates are `cuems-common`'s package content carrying the sentinel. This
  feature's tool reads the record (`--check`) and never writes it. Nodeconf is unmasked
  fleet-wide as part of the same landing; a node where it stays masked has an unmaintained
  record, which `--check` reports.
- **A10 — Container-based lifecycle tests**: the package-lifecycle success criteria are measured
  in a bookworm container or chroot on the build host, since both production machines have been
  unreachable since 2026-09-23 and are evidence, not a test bed.

## Dependencies

- **Depends on**: nothing — this is the entry point of the 011–014 sequence. The landed
  prerequisites (D8, D10, D15–D17; features 006–008's strict read path, conversion registry and
  descriptor) are in the tree at `feat/xml-refactor`.
- **Blocks**: feature 012 (hard — design §9.4: narrowing `UuidType` without this tool
  invalidates every node identity in the field with nothing able to repair them), and every
  "fresh node" claim in the ecosystem.
- **Cross-repository**: `cuems-common` (hands over two paths, extends one contract document,
  re-bases six tests, retires the second minter in `cuems-config-node` per FR-040a) and `cuems-nodeconf` (renders the Avahi record from `settings.xml`, FR-040a; ~30 lines). Both changes land on
  `cuems-common`'s working branch; nothing ships from either repository alone (D27 — the
  coordinated merge is tagged after 011–014).
- **Closes**: OPEN-1, OPEN-2 (by M4), OPEN-3 (by M5 + FR-022's test), OPEN-4.

## Out of Scope

- **Python-version forward compatibility.** The package is pinned to 3.11 by three independent
  mechanisms (`Depends: python3 (<< 3.12)`, the venv's `lib/python3.11/` path, dh-virtualenv's
  autoscript deriving the version from that dirname). This feature adds **no** new coupling —
  every path it adds is version-free by construction — and removes none. It is stated here so
  it is not silently inherited as a goal.
- **uuid4 convergence** — narrowing `network_map.xsd`'s `UuidType` and the cross-document
  re-mint: feature 012. This feature builds the tool 012 needs and does not tighten the schema;
  `UuidType` stays in `KNOWN_DIVERGENT_DECLARATIONS`.
- **The `hardware_outputs` structure pass and the port-inventory move**: feature 014, which is
  also what finally retires `default_mappings.xml`.
- **The device-class reshape (F6)**: feature 013.
- **The library version**: stays `0.1.0rc16` (design §12). Schema shape is signalled by
  `doc_version`, not by the library version.
- **Converting existing documents at install** (D8, satisfied): the read path converts in
  memory; `cuems-convert-documents` and `cuems-common`'s `cuems-migrate-network-map` remain the
  batch tools.
- **Trixie packaging and the CI/CD matrix**: recorded intentions in `debian/README.source`;
  this feature must not make either harder (FR-044) and does not deliver either.
