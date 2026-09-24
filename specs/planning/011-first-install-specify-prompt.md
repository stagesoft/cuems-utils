<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Feature 011 — `/speckit.specify` prompt

**Purpose**: start feature `011-etc-cuems-first-install` in a fresh session without re-deriving
three weeks of audit. **Written for** an agent or contributor with no memory of the xml-refactor
work.

**Prepared** 2026-09-24, against `feat/xml-refactor` at `8c67465`, library `0.1.0rc16`, suite
2719 passed / 100 skipped / 2 xfailed.

---

## 1. How to run it

```
/speckit.specify <paste §2 verbatim>
```

Then **stop and run `/speckit.clarify`** before `/speckit.plan`. §4 lists nine questions that
must be *asked*, not assumed — several have no defensible default, and one (OPEN-1) has two
production spellings that contradict each other with no established winner.

Do not begin implementing from the spec alone. This feature can block the install of every
CUEMS package if it is wrong (§3.1).

---

## 2. The prompt — paste this verbatim

```text
Build the /etc/cuems first install for cuems-utils: a fresh `apt install` must leave a node
that boots, loads its configuration, and is uniquely identified — where today no package ships
any of the three documents ConfigManager requires in a usable state, and the six XSD files that
define them live only inside the venv.

AUTHORITATIVE INPUTS — read both in full before writing the spec, and do not re-derive what
they already measure:

  specs/planning/etc-cuems-first-install.md
      The design. Seventeen decisions D1-D17 with their reasoning (§3), the end-to-end flow
      (§4), the node-identity invariant and its eight practices (§5), the open items (§6),
      the splitting basis and duplication flags (§8).

  specs/planning/etc-cuems-first-install-execution.md
      The measured state. What is actually built, per decision (§3); findings that correct the
      design document (§4); this feature's brief (§6); and the trap register (§7), which is
      eight entries every one of which already cost a revert or a destroyed file.

THE PROBLEM, STATED AS MEASURED

ConfigManager needs three XML documents in /etc/cuems and all three are uuid-coupled. Measured:
the shipped-defaults triple available today raises

    ValueError: Node with uuid 00000000-0000-0000-0000-000000000000 not found

Only settings.xml has a generator. network_map.xml ships as a trivial empty stub that cannot
support ConfigManager(load_all=True) on any node. default_mappings.xml is written at runtime by
a cuems-common helper. Two live defects already depend on schemas nobody ships: a cuems-common
helper validates against /etc/cuems/project_mappings.xsd, and cuems-common's own operator
documentation tells people to load /etc/cuems/settings.xsd. Neither file exists on any machine.

Both audited production hosts carry stale .xsd copies that disagree with each other and with
this repository, and one carries a network_map.xsd.dpkg-dist — the conffile prompt fired, the
admin kept the old copy, dpkg parked the new one beside it. That is the failure mode D5 exists
to prevent, already having happened in the field.

SCOPE — what this feature delivers

  D2   default documents generated at package build, from the SSOT, deterministically
  D3   shipped documents carry the reserved sentinel identity; live ones are specialized
  D4   all six .xsd ship to /etc/cuems as real files, and cuems-common drops its mirror
  D5   nothing under /etc/cuems is a conffile; postinst installs if absent, never overwrites
  D6   purge removes only the paths this package placed, then rmdir --ignore-fail-on-non-empty
  D7   the seed values table is promoted out of descriptor.py into a named home
  D9   seed values become TOML with an /etc/cuems/defaults.d drop-in overlay
  D11  the overlay is applied by cuems-init-node, never by postinst
  D12  cuems-init-node owns node coherence and writes all three documents atomically
  D13  postinst mints a uuid4 if and only if there is none; a real identity always persists
  D14  the Avahi TXT uuid must derive from settings.xml — a cross-repo contract with
       cuems-common, and the one part of the identity invariant that fails SILENTLY

  plus the new public entry point cuems-init-node (including --check), the cuems-common
  handover, and the packaging hygiene listed at §4.1 of the design document.

ALREADY SATISFIED — do not re-litigate, do not re-implement:

  D1   the XSD is SSOT for structure, never values — a stance, no artifact
  D8   nothing converts at install; conversion happens on read — feature 008's machinery
       plus two registered conversions from F3/F4
  D10  DECLARED_DEFAULTS stays in Python — every entry is Unset or runtime scaffolding
  D15  the seed values corrected against production by consumption (landed e421e31)
  D16  PlayerType's values fallback removed, the mixer section re-keyed (landed e421e31)
  D17  the generator widened past f.required, so optional knobs are emitted (landed e421e31)

EXPLICITLY OUT OF SCOPE

  - Python-version forward compatibility. The package is pinned to 3.11 by three independent
    mechanisms. This work adds NO new coupling — /usr/share and /etc paths are version-free by
    construction — but removes none either. Say so; do not silently inherit it as a goal.
  - uuid4 convergence: narrowing network_map.xsd's UuidType is feature 012, and it CANNOT land
    before cuems-init-node exists (see the design document §9.4). This feature builds the tool
    that 012 needs; it does not tighten the schema.
  - The hardware_outputs structure pass and the port-inventory move: feature 014.
  - The device-class reshape: feature 013.

THE CONSTRAINT THAT DOMINATES EVERY DESIGN CHOICE

cuems-utils is the base dependency of the whole stack — unavoidable, installed first. Debian's
failure semantics are asymmetric here: a non-zero exit from ITS postinst leaves the package
half-configured and EVERY dependent package fails to configure. One bad exit blocks the install
of every CUEMS component at once.

Therefore: postinst must never exit non-zero. Every step either succeeds or degrades to copying
the pristine placeholder, warns, and exits 0. This is also why D11 keeps the operator-authored
overlay OUT of postinst — a TOML typo must not be able to block the stack.

REQUIREMENTS THE SPEC MUST CARRY, because getting any of them wrong is a field incident

  - /etc/cuems is SHARED by at least five packages across roughly twenty paths, including
    cuems-common's conffiles, the cluster identity, and /etc/cuems/power-bridge.key — A PRIVATE
    SSH KEY belonging to another package. Nothing in this feature may rm -rf /etc/cuems.
    Debian policy forbids removing files a package did not create.
  - The shared venv /usr/lib/cuems is ONE-WAY: it has include-system-site-packages = true, so
    the venv sees system packages but /usr/bin/python3 CANNOT import cuemsutils. Any entry
    point placed in /usr/bin must not import cuemsutils. cuems-init-node imports it heavily, so
    where it is installed and how postinst invokes it is a real design decision, not a detail.
  - A .deb must not bundle anything another package already ships: dpkg -i aborts on a
    file-overwrite conflict. The cuems-common handover therefore needs matched Breaks/Replaces
    and Depends, landing in a defined order.
  - Identity must survive upgrade, --reinstall, and remove-then-install, and must be destroyed
    only by purge. postinst never modifies an existing file — including one carrying the
    sentinel, which --check reports and init-node fixes.
  - The generator must stay deterministic so the package build is reproducible: it emits the
    reserved sentinel identity, never a fresh uuid4. Minting at build time would give every
    machine imaged from one package the same "real" identity.
  - uuid4 minting goes through cuemsutils.tools.Uuid, which mints uuid4() and raises on
    anything else. No second minter exists anywhere in the ecosystem.

USER STORY SLICING — suggested, and each slice must stand alone

  P1  the six .xsd ship to /etc/cuems and cuems-common hands its mirror over. Viable on its
      own: it closes the two live "validates against a file nobody ships" defects and ends the
      schema drift measured on both production machines, with no identity work at all.
  P1  the three documents are generated at build, shipped pristine to /usr/share, and installed
      to /etc/cuems only when absent.
  P1  cuems-init-node writes the coherent triple atomically and postinst calls it, so a plain
      apt install leaves a node that loads and is unique.
  P2  seed values move to TOML with the defaults.d overlay, applied by init-node.
  P2  purge removes only this package's paths; the last CUEMS package removed empties the
      directory.
  P3  cuems-init-node --check reads all four identity locations and reports mismatches by path.
      It is what turns "Node with uuid ... not found" into something actionable, and the only
      thing that catches the silent Avahi mismatch.
  P3  the packaging hygiene pass (§4.1): committed build artifacts, debian/compat 11,
      Standards-Version 4.1.4, a postinst still claiming dh_python2.

SUCCESS CRITERIA — measured, not asserted

  - ConfigManager(load_all=True) succeeds on a machine whose /etc/cuems was populated only by
    dpkg -i, with no hand-placed file.
  - Upgrade, --reinstall, and remove-then-install each leave an existing identity byte-identical.
  - purge of cuems-utils alone damages no other package's files; purge of the whole stack
    leaves no /etc/cuems.
  - dpkg-deb --fsys-tarfile <deb> | tar -xO ./usr/lib/cuems/pyvenv.cfg | grep '^home' reports
    home = /usr/bin — see the trap register.
  - The constitution requires a measurable performance budget rather than "N/A": state one for
    postinst wall time and for cuems-init-node, and validate it. A previous feature was pulled
    up for declaring this inapplicable.

BRANCHES AND REPOSITORIES

  cuems-utils   owner. Work spans TWO branches: feat/xml-refactor (source, generator, entry
                point, tests) and debian/bookworm (packaging). This is the first feature that
                needs both trees at once, and how they meet is a question the spec must answer.
  cuems-common  hands over etc/cuems/network_map.xml and etc/cuems/network_map.xsd from its
                debian/install and retires tests/test_schema_mirror.py; gains
                docs/node-identity-contract.md carrying D14's contract.

Commits are GPG-signed; on "gpg failed to sign", retry, never --no-gpg-sign.
```

---

## 3. Context the session needs that the prompt does not carry

### 3.1 Why "do not begin implementing" is not boilerplate

The failure mode is not a bad commit. It is a `postinst` that exits non-zero on the base package
of the stack, which leaves every CUEMS component un-configured on every node it reaches. That is
recoverable, but only by hand, on hardware, at a venue.

### 3.2 The two production machines are evidence, not a source

Both were audited 2026-09-21 and have been **unreachable since 2026-09-23**. Both predate this
refactor. D15's method is the one to repeat: classify each value by *who actually reads it* —
engine source, live `ps` output, `systemctl show` — rather than transcribing a host. That method
is what found `/usr/bin/cuems-player`, a binary named in four places that **has never existed**.

### 3.3 The tests that will push back

| Test | What it will refuse |
|---|---|
| `tests/contract/test_schema_scope.py` | a schema edited without its hash updated in the same commit |
| `tests/contract/test_schema_name_overlap.py` | a name declared in two schemas without a verdict |
| `tests/contract/test_duplication_flags.py` | a derived fact stored, a choice in a discovered document, a back-reference |
| `tests/contract/test_public_api_surface.py` + `tests/golden/api/public_api.json` | a new public symbol not recorded |
| `tests/contract/test_no_routine_backups.py` | a write path that backs up as a matter of course |

`cuems-init-node` is a **new public entry point**, so the API surface golden moves. That is a
sanctioned, recorded change — not a reason to avoid the entry point.

---

## 4. Clarifications that must be asked, not assumed

Take these into `/speckit.clarify`. Each has either no defensible default or two candidate
answers already in conflict.

1. **OPEN-1 — `default_mappings.xml`'s values table, per field.** What should a *fresh,
   unconfigured* node claim for `number_of_nodes` and the six `default_*_input`/`_output`
   values? **Neither production file is copyable**: one maps a **disconnected** `DP-2`, and the
   two hosts disagree on whether `default_audio_output` holds an output **id** or an output
   **name**. One of those spellings is wrong and which has never been established.
2. **The `default_mappings.xml` tension.** §8.5 item 5 retires this document; this feature is
   about to build a generator for it. Recommendation: build it anyway — a node must boot long
   before 014 lands, and the table is seven scalars plus a node entry — but the spec should
   decide it deliberately rather than discover it in review.
3. **OPEN-2 — does the editor need the XSDs?** `cuems-editor` has no `debian/` directory at
   all. Whether it validates against `/etc/cuems/*.xsd` or the venv copies has never been
   measured.
4. **OPEN-3 — ordering between `postinst` and first service start.** `cuems-init-node` must
   complete before any engine starts, or the engines hit the two eager uuid lookups. The units
   belong to `cuems-common`. Confirm, do not assume.
5. **OPEN-4 — where `cuems-init-node` lives**, given §3's one-way venv constraint: it belongs
   naturally to `cuems-utils`, but it writes files `cuems-common` has historically owned and is
   invoked from `cuems-utils`' `postinst`.
6. **How the two branches meet.** Does packaging merge `main`/`feat/xml-refactor` into
   `debian/bookworm` as today, and does the generator run at build from the just-built venv?
   The design says yes; the mechanics are unspecified.
7. **What `--check` exits with.** A verifier that reports a mismatch and exits 0 is a verifier
   nothing can gate on; one that exits non-zero from `postinst` is the stack-blocking hazard of
   §3.1. These are not the same invocation and probably need different answers.
8. **Re-run policy on a changed overlay.** D12 says identity is preserved and everything else
   re-applied. Confirm that re-applying may overwrite an operator's hand-edit to
   `settings.xml`, which is the observable consequence, and whether that wants a warning.
9. **Whether `cuems-common`'s handover lands first or simultaneously.** `Breaks`/`Replaces`
   makes this orderable, but somebody has to state the order and the two versions.

---

## 5. Do not

- **Do not narrow `UuidType`.** That is 012, and landing it before `cuems-init-node` exists
  invalidates every node identity in the field with nothing able to repair them.
- **Do not move the library version off `0.1.0rc16`.** `0.1.1` is reserved by
  `_deprecation.REMOVAL_RELEASE` — every deprecation warning since feature 006 promises the
  deprecated surface is *gone* there — and it is refused outright by three consumers'
  `<< 0.1.1~` ceilings. `rc17` would pass the ceilings while saying nothing true.
- **Do not regenerate goldens to make a test pass** (FR-021). `tests/golden/outcomes.json` in
  particular is a **pre-refactor baseline** that a test compares *against* live behaviour;
  regenerating it destroys the comparison.
- **Do not claim anything in this library is unused from an in-repo grep.** It is a library.
  Check `../cuems-engine`, `../cuems-editor`, `../cuems-frontend`, `../cuems-nodeconf`,
  `../cuems-power-bridge`, `../cuems-common` — and note that `cuems-wsclient` **is**
  `cuems-power-bridge`, the same repository renamed, which once inflated the ecosystem count
  from seven to eight.
- **Do not ship from this branch alone.** Nothing in this ecosystem releases by itself; the
  `xml-refactor-merge-candidate` tag comes after 011–014.
