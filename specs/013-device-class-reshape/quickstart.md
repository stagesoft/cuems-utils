<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Quickstart — feature 013, device-class reshape

For a contributor or agent session picking this up cold.

## Environment

`hatch` is **not installed** on this dev box, and the `hatch test` env lacks `hypothesis`. Use the
project's `test` env through `uvx`:

```bash
cd /disk/Projects/StageLab/cuems-utils
PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:run -- -q                     # full suite
PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:run -- -q tests/contract      # one directory
```

Commits are **GPG-signed**. On `gpg failed to sign`, retry — never `--no-gpg-sign`.

## Read before touching anything

| Document | Why |
|---|---|
| [spec.md](spec.md) | the requirements, and the seven clarification answers in two sessions |
| [research.md](research.md) | R1–R15. **R2 is the one that constrains the schema design** |
| [data-model.md](data-model.md) | the four document shapes, before and after |
| [contracts/schema-conventions.md](contracts/schema-conventions.md) | the five rules every conditional element follows |
| `specs/planning/etc-cuems-first-install.md` §8.4 | the original design of this reshape |

---

## Run these four experiments before writing any schema

They are the feature's go/no-go, and **E1 and E2 together decide whether axis D is affordable at
all**. Each has a stated fallback in [research.md](research.md); none can be run from plan mode, so
they are the first implementation tasks.

### E1 — does `xs:alternative` decode at all under the pinned `xmlschema`?

```bash
PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:python - <<'PY'
import xmlschema
s = xmlschema.XMLSchema11("""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root">
    <xs:complexType><xs:sequence>
      <xs:element name="d" maxOccurs="unbounded" type="B">
        <xs:alternative test="@class='video'" type="V"/>
        <xs:alternative type="B"/>
      </xs:element>
    </xs:sequence></xs:complexType>
  </xs:element>
  <xs:complexType name="B"><xs:sequence>
    <xs:element name="a" type="xs:string"/></xs:sequence>
    <xs:attribute name="class" type="xs:string" use="required"/></xs:complexType>
  <xs:complexType name="V"><xs:complexContent><xs:extension base="B">
    <xs:sequence><xs:element name="extra" type="xs:string"/></xs:sequence>
  </xs:extension></xs:complexContent></xs:complexType>
</xs:schema>""")
print(s.decode("""<root>
  <d class="audio"><a>x</a></d>
  <d class="video"><a>y</a><extra>z</extra></d>
</root>"""))
PY
```

**Pass**: both children decode, and the `video` one keeps `extra`. **Fail**: the feature's mechanism
is wrong and planning restarts at R3's alternatives.

### E2 — can the library's own derivation see the alternatives?

```bash
PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:python - <<'PY'
# against the E1 schema object: what does xmlschema expose for the conditional element?
el = s.elements["root"].type.content[0]          # the <d> particle
print(type(el), getattr(el, "alternatives", "NO ATTRIBUTE"))
for alt in getattr(el, "alternatives", ()):
    print(repr(getattr(alt, "path", None)), getattr(alt, "token", None), alt.type)
PY
```

**What this decides**: whether `spec.derive` can read the class→type map off the schema (FR-010,
SC-002) or whether the convention has to be re-parsed from the `.xsd` source. The second is still
acceptable — it is still *derived* — but it is slower and uglier, and the plan's task list differs.

### E3 — does `distinct-values` work in an `xs:assert`?

```bash
PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:python - <<'PY'
import xmlschema
s = xmlschema.XMLSchema11("""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root"><xs:complexType><xs:sequence>
    <xs:element name="d" maxOccurs="unbounded">
      <xs:complexType><xs:attribute name="class" type="xs:string"/></xs:complexType>
    </xs:element></xs:sequence>
    <xs:assert test="count(d) = count(distinct-values(d/@class))"/>
  </xs:complexType></xs:element>
</xs:schema>""")
print(s.is_valid('<root><d class="a"/><d class="b"/></root>'))   # expect True
print(s.is_valid('<root><d class="a"/><d class="a"/></root>'))   # expect False
PY
```

**Fail**: FR-013 falls back to `xs:unique`, or to a T2 rule — which does **not** reach
`cuems-editor`, so that fallback changes what the clarification decided and must be recorded.

### E4 — the denominators, before anything changes

```bash
git switch --detach HEAD            # the pre-change tree
PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:run -- -q      # 3 runs: per-test time
# mappings-document load, show-document load: the timing tests in tests/integration/
```

Record every number in `baseline.md` **before** the first schema edit. SC-PERF-001 is stated as a
ratio to a measurement that does not exist yet; measuring it afterwards is not measuring it.

---

## The six things that will cost you a revert

1. **A type may not mix single element children with a repeated one** (R2,
   `converter.py:144-148`). The converter's content assembler replaces the accumulated dict with a
   list the first time it sees a repeated name, so a `NodeMappingType` holding `uuid`, `mac` **and**
   repeated `device` loses `uuid` and `mac` — silently, with the document still schema-valid. This is
   why `<devices>`, `<players>` and `<defaults>` are containers and not a flattening.
2. **FR-027's diagnosis lands in the same commit as the first schema edit.** A commit that narrows a
   schema without it leaves exactly the bare `xs:sequence` complaint the requirement exists to
   prevent — and that is the shape of the X13 incident this repository vendors two broken settings
   files as evidence of.
3. **The schema hash pin moves with the schema** (`CURRENT_SCHEMA_HASHES`,
   `tests/contract/test_schema_scope.py:65`), in the same commit, with the reason in the message.
   Never exclude a schema from the pin to avoid updating it.
4. **`KNOWN_DIVERGENT_DECLARATIONS` stays empty.** It reached empty as feature 012's completion
   marker (FR-025 there). Any new type this feature declares in more than one schema goes in
   `KNOWN_IDENTICAL_DUPLICATES`, byte-identical, or it does not go in at all.
5. **`tests/unit/test_mappings_shape.py:136-141` asserts the thing this feature deletes** —
   `assert "_DEVICE_SECTIONS" in source`. It is a source-level ratchet, so it stays green while the
   behaviour it guards is gone. Invert it in the same commit that removes the constant (R13).
6. **No version step.** Not `CURRENT_VERSION`, not the conversion registry, not
   `DELIBERATE_IDENTITY_STEPS` (FR-020, SC-006). The mutually exclusive element shapes *are* the
   marker — that is feature 007's route through the schema-evolution convention, and
   `cuems-reshape-devices` is the documented one-shot tool rule 4 requires.

## Golden and corpus discipline

- `tests/golden/` **will** change — the wire key moves from `AudioCue` to `Cue` + class. That is a
  named, justified golden event (FR-054): regenerate deliberately, in its own commit, with the
  reason, and update `MANIFEST.sha256` with it.
- **Do not regenerate `tests/golden/outcomes.json`.** It records pre-refactor verdicts a test asserts
  the *difference* against.
- **Snapshot the old shape before touching it**: `tests/data/corpus/pre-013/` holds an old-shape
  example of every reshaped document, and it is the migration tool's fixture *and* FR-027's. Once a
  schema narrows, no old-shape document can be produced from this tree any more (R13).
- `tests/golden/api/public_api.json` changes by exactly the two names FR-035 and FR-036 add
  (SC-016) — nothing else.

## The suite baseline

Quote a **range**, not a single run: `test_descriptor_laziness` skips a varying number of schemas
below its noise floor, so passed/skipped totals move by ±1 on an unmodified tree. Re-run before
recording a delta, and record per-test time, not wall clock — the suite grows.

## Packaging and the chroot

`debian/rules:27-29` regenerates the three default documents through the just-built venv's
`bin/python`, so a schema change that breaks generation breaks the **build**, not a test. Feature
011's lifecycle tests run in an unprivileged `mmdebstrap --mode=unshare` bookworm chroot
(`CUEMS_CHROOT_TAR`) — no container runtime needed; see
`specs/011-etc-cuems-first-install/quickstart.md` for setup.

## Do not

- Move the library version off `0.1.0rc16` — `tests/packaging/test_no_version_bump.py` pins it,
  along with `cuems-common 1.3.0-23` and `cuems-nodeconf 0.1.0-8`.
- Ship from this branch alone (D27). The coordinated `xml-refactor-merge-candidate` tag comes after
  011–014, and `cuems-utils` tags **last**.
- Declare a list, tuple, set or enum of device-class names anywhere in `src/cuemsutils/`
  (FR-010, SC-003). The whole feature is that no such thing exists.
- Fold `audiomixer` into `<players>` (FR-040a). It has no device class; folding it in invents one.
- Touch feature 012's identity surface — `SENTINEL`, `coerce_identity`, `node_uuid`, `--remint` (A8).
- Create a `tests/performance/` directory. Timing tests go in `tests/integration/`.
