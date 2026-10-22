# TPM endorsement-key fingerprint (`tpm_ek_sha256`)

**Status:** decisions settled 2026-10-22. Blocked on the hardware spike (§3). Nothing is implemented yet.
**Path:** reduced SDD, following 014's precedent: `plan.md`, `tasks.md` and `baseline.md`, with no
`spec.md` story pass and no `research.md`. That omission is a tracked exception, recorded here. The
spike's measurements stand in for `research.md`.
**Release:** this goes inside the coordinated release, before the maintainer re-cuts the candidate
tags. That re-cut is still owed, for both `cuems-utils` and `cuems-nodeconf`. If the way-out rule
(§5) fires, the feature moves to the next release and nothing in that release changes.

## 1. What and why

The field records a stable hardware fingerprint for each node: the SHA-256 of its TPM's endorsement
key (EK). It goes into the node's own `settings.xml` and into the controller's `network_map.xml`.

It is **informational only (scope B)**. No code path changes behaviour because of it. Using it as a
hardware anchor is deferred (§6). Whatever the anchor work eventually becomes, an optional field that
already holds the value is a precondition for it, so the field comes first.

## 2. Settled decisions

| # | Decision |
|---|---|
| D1 | **Scope B.** The node writes the fingerprint to `settings.xml`, and the controller's map carries it. Nothing reads it for behaviour. |
| D2 | **Name `tpm_ek_sha256`, type `cms:Sha256Type`**: 64 lowercase hex characters, defined facet for facet like `Md5Type`/`UuidType`. Uppercase **raises**; it is not normalised (014's case rule). It is not a UUID, so the name says what it is. A different algorithm later means a new element, never a reinterpretation of this one. |
| D3 | **The value** is SHA-256 over the DER SubjectPublicKeyInfo of the **ECC P-256** EK, created from the TCG default template: `tpm2_createek -c <ctx> -G ecc -u <out> -f der`, then hashed, as a transient object with nothing written to the TPM. ECC was chosen over RSA for speed (RSA EK creation can take seconds on a discrete TPM). DER SPKI was chosen so the value can be checked against the EK certificate's key later. **Fixed forever.** |
| D4 | **Placement:** an optional element (`minOccurs="0"`) directly after `mac` in `settings.xsd` `NodeConfType` and in `network_map.xsd` `NodeType`. Absent means "no TPM, or not measured". `Sha256Type` is declared in both schemas and registered in `KNOWN_IDENTICAL_DUPLICATES` (`tests/contract/test_schema_name_overlap.py`). |
| D5 | **Version:** folded into the current, **unreleased** steps (`settings` 3, `network_map` 2). There is no bump and no conversion. The addition is purely additive, so every existing document stays valid. The only window is a pre-fold build meeting a document that carries the field, which it rejects at the same `doc_version`. That window closes when the coordinated release ships, the same as 014's. |
| D6 | **Producer: `cuems-init-node`**, running as root from `postinst`, with its own subprocess timeout well inside `postinst`'s 60 s. It is an **identity-class** value, so it is injected and never seeded (seed rule "no identity"). **It never refuses** when the value can't be read, which is unlike the MAC: if there is no TPM, no `tpm2-tools`, an error or a timeout, the element is left out and a single line is logged. **When a value is already stored and a fresh read differs**, the fresh value is written and a WARNING names both values. That is the one useful signal at scope B. **When the read fails** but a value is stored, the stored value is kept and a note is logged. |
| D7 | **Transport: the Avahi TXT record**, `tpm_ek_sha256=<64 hex>` (78 bytes, under the 255-byte limit per string). The **adoption handshake** the maintainer first named **does not exist**: `adopt_node` only changes the controller's own map (`cuems-nodeconf` `CuemsNodeConf.py:867`), and the TXT record is the only channel from node to controller (`CuemsAvahiListener.py:91-105`). Measured 2026-10-22, maintainer re-decided the same day. |
| D8 | **`cuems-nodeconf` inserts the TXT entry itself** in `_render_service_record`, next to every `uuid=` entry, only when `settings.xml` carries the field. **`cuems-common`'s templates are untouched**, so the sentinel-substitution contract (`specs/003-startup-readiness/contracts/service-record-render.md` there) stays as it is and `cuems-common` stays out of the re-cut. That contract document gains one clause. |
| D9 | **Listener:** the property is optional and is passed through unvalidated. **The library is the authority on what a valid value is (D12)**; the listener doesn't repeat that check, because a second copy of the pattern would drift from the XSD. A bad fingerprint never costs a node its map row. |
| D12 | **`NodeIndex.merge` copies any field it is given, if that field validates against the XSD** (maintainer, 2026-10-22). The rules: (a) a key that is not a declared `NodeType` field is dropped, now including from a plain dict; (b) a declared field is copied only if its lexical form (`adapter_for(xsd_type).to_lexical`) is valid for its XSD simple type (`is_valid`). An invalid value is dropped, the existing value is kept, and one WARNING names the node uuid, the field and the value. **The merge never fails.** (c) A *new* node whose required field is missing or invalid is not inserted (WARNING). (d) Unchanged: an existing node's `mac` is never overwritten, `adopted` is preserved and `online` is forced. (e) A field that isn't given is not touched, so a stored value survives a node that stops announcing it. That is acceptable at scope B, and the node-side WARNING (D6) is where a change shows up. The checks are per-field T1 checks, using machinery that already exists (`derive(...).fields`, `seed_values._simple_type`); `NodeType` carries no T2 rule. |
| D10 | **Packaging:** `cuems-utils` gains `Recommends: tpm2-tools`, not `Depends`, because nodes without a TPM are expected. |
| D11 | **The TXT record is broadcast and unauthenticated**, so any host on the LAN can announce any value. At scope B that is acceptable, because nothing trusts the value. It is the first thing the deferred anchor work (§6) has to answer. |

## 3. The spike, which blocks `plan.md`

Nothing here has been run on a TPM yet: the development box has none. Each item needs a measurement
on the node hardware that actually ships.

| # | Question | Pass condition |
|---|---|---|
| S1 | Which shipped node models have a TPM, and of which kind (discrete, Intel PTT, AMD fTPM)? | A table by model. |
| S2 | How long does `tpm2_createek -G ecc` plus the hash take on each kind? | Comfortably under the producer's timeout (D6). |
| S3 | Is the value the same across a reboot, a `tpm2_clear`, and a BIOS update where one can be tried? | Identical after reboot and clear. A BIOS change is recorded either way. |
| S4 | Does it work from `postinst` as root, with only `/dev/tpmrm0` and no `tpm2-abrmd`? | The value is produced. |
| S5 | Does `swtpm` (CI) produce a value of the right shape, and a fresh one per instance? | It does, so the suite needs no hardware. |

## 4. Work by repository

**`cuems-utils`**
- Schemas: `Sha256Type` and the element in both schemas (D2, D4, D5), plus an entry in `KNOWN_IDENTICAL_DUPLICATES`.
- Model and descriptor: the field on the settings node and on the map `Node`. `network_map` runs the
  adapter table, so the value decodes as `str`. Check that the descriptor seeds no placeholder value
  for it.
- `cuems-init-node`: the probe (D3, D6), with the decision on override flags recorded in `plan.md`.
  Candidates are `--tpm-ek-sha256 <hex>` (mirroring `--mac`) and `--no-tpm`.
- `NodeIndex.merge`: **D12 implemented 2026-10-22, ahead of the feature** (`2b3b7a1`). It is a fix to an existing defect and does not depend on the spike, so it stays even if
  the way-out rule (§5) fires. The simple-type lookup moved from `seed_values._simple_type` to
  `xml.schema.simple_type`, so both callers share it. Before the fix, characterised against
  `feat/xml-refactor` at `8135841`:
  - `merge` copied every given key except `mac` with `dict.update`, validating nothing;
  - an undeclared key was already dropped for `node` objects, by `CuemsDict.items()` (which yields
    declared fields only), not by `merge`. A caller passing plain dicts had no such protection;
  - **one node announcing one invalid value** (measured with `ip=""`) makes
    `CuemsNetworkMapType.refresh` raise `SchemaError` from `save`. The file is left unchanged, but the
    bad value **stays in the in-memory map**, so every later refresh fails the same way. The
    controller's map stops persisting for every node until that one node announces a valid value.
  `tests/contract/test_merge_validates_against_schema.py` pins (a)–(e) and the poisoned-map scenario
  through `refresh`. Against the unfixed source, 10 of its 13 cases fail; the 3 that pass pin behaviour
  that was already correct. **One characterisation fixture was edited** (data only, assertions
  unchanged): `test_merge_adds_a_genuinely_new_node_keyed_by_its_own_mac` used `uuid="u2"` and no
  `ip`, a node the schema refuses, which rule (c) now keeps out. This document had predicted the
  suite would pass unedited; that was wrong. Full suite: 4230 passed, 3 failed. All three failures
  are sibling-state assertions that fail identically without the change. Ruff 0. mypy +1, the
  missing `pytest` stub every test module reports in that environment. **Not run:** `cuems-nodeconf`'s
  own suite (it needs `zeroconf`, which isn't installed on this box). Its listener always builds full
  `node` objects, and the NOT PROVISIONED sentinel uuid is valid `NodeUuidType`, so a `firstrun` node
  is still added.
- `debian/control` (D10). Goldens: only if a generated default document changes, which it shouldn't,
  since the field is absent by default.
- Tests: with `swtpm` for the probe, and without a TPM for the absent path.

**`cuems-nodeconf`**
- `_render_service_record` (D8) and the listener (D9), plus one clause in its render contract.
- A two-arm gate against this library.

**`cuems-common`**: none (D8).

## 5. Release gates and the way-out rule

Before the re-cut:
- the two-arm sibling suites for `cuems-nodeconf`;
- `specs/016-coordinated-minor-bump/tools/verdicts.sh` re-run, since D10 changes a relation;
- a bookworm chroot build, with `postinst` exercised on a TPM-less root;
- the candidate-tag messages re-checked.

**Way-out rule:** if S1–S4 have not passed on the shipped hardware by the time the coordinated
release's other fixes are ready, this feature leaves the release whole and rides the next one. The
field is optional, so leaving it out costs nothing, and the re-cut is never held for it.

## 6. Deferred (not this feature)

- **Use as a hardware anchor**: in 012's "identity minted for different hardware" check, alongside or
  instead of the MAC, or in `cuems-init-node --remint`. Deferred because how many shipped nodes have a
  TPM chip at all is unknown. This would need the **full SDD path**, because it changes what identity
  means across the cluster. It has to answer D11 (spoofing) and the cloned-VM case: `swtpm` state
  cloned with a VM produces a duplicate EK.
- **A real handshake** between node and controller (an NNG req-rep exchange at adopt time). It is
  only worth building if the anchor work needs an authenticated channel.
- **EK certificate verification / attestation** (`tpm2_getekcertificate`). D3's choice of DER SPKI
  keeps this possible.
