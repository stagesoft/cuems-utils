<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Quickstart — feature 012, uuid4 convergence

For a contributor or agent session picking this up cold.

## Environment

`hatch` is **not installed** on the current dev box, and the `hatch test` env lacks `hypothesis`.
Use the project's `test` env through `uvx`:

```bash
cd /disk/Projects/StageLab/cuems-utils
PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:run -- -q                    # full suite, ~2 min
PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:run -- -q tests/contract/test_schema_name_overlap.py
```

Commits are **GPG-signed**. On `gpg failed to sign`, retry — never `--no-gpg-sign`.

## Read before touching anything

| Document | Why |
|---|---|
| [spec.md](spec.md) | requirements, and the five clarification answers |
| [research.md](research.md) | R1–R10. Three of them contradict the planning documents |
| [data-model.md](data-model.md) | the classification vocabulary and the table's invariants |
| `specs/planning/etc-cuems-first-install.md` §9, §10 | the design and the re-mint procedure |

## The four things that will cost you a revert

1. **Do not narrow anything before the re-mint exists.** It invalidates every deployed identity
   with nothing able to repair it. Phase D is last for this reason, not by preference.
2. **The schema hash pin and the schema change move in the same commit**
   (`tests/contract/test_schema_scope.py`, `CURRENT_SCHEMA_HASHES`), with the reason in the commit
   message. Do not exclude a schema from the pin to avoid the update.
3. **The divergence entry and the narrowing move together.** While `UuidType` is listed in
   `KNOWN_DIVERGENT_DECLARATIONS`, that test *requires* the collision to still exist. Removing the
   entry is the feature's completion marker (FR-025).
4. **Negative fixtures fail for a reason, and the reason is the assertion.** After tightening,
   re-check *which* error each one raises — a fixture that still fails while testing the wrong
   thing keeps the suite green and the coverage gone (trap 7.3, FR-027).

## Verifying the sentinel premise

The single measurement that shapes FR-021. If it ever stops holding, the narrowing design changes:

```bash
PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:python -c "
from cuemsutils.xml.make_defaults import generate
from pathlib import Path; import tempfile
d = Path(tempfile.mkdtemp()); generate(d)
print((d/'network_map.xml').read_text())
"
# the node row must carry 00000000-0000-0000-0000-000000000000
```

If the tightened pattern does not admit that value, the package's own build-time generation
fails and every freshly installed node becomes unloadable.

## Suite baseline

Quote a **range**, not a single run: `test_descriptor_laziness` skips a varying number of schemas
below its noise floor, so passed/skipped totals move by ±1 between runs on an unmodified tree, and
it fails its 1.10× cap on roughly two runs in three on a 2-vCPU VM. Re-run before recording a
delta.

## Order of work

```
A  the check          US1   writes nothing; ships value alone
B  the library surface US4  blocked on the census artifact (FR-032)
C  the re-mint        US2   the bulk
D  the narrowing      US3   LAST — three schemas, three version steps, no conversions (R5)
E  the migration guide US5  needs C and D measured
```

## Two tasks that edit things outside this feature

- **Feature 011's D13 is amended** (FR-019d): "mint iff there is none" becomes "iff there is
  none, **or** the identity on disk was minted for different hardware". Record it against 011's
  decision record — a later reader finds that text first.
- **The planning documents get this feature's corrections applied** (FR-037), never silently:
  §9.2's narrowing description, §9.4's detection assignment, §10.5's script-filename procedure,
  and the two-versus-three schema count.

## Do not

- Move the library version off `0.1.0rc16` — pinned by `tests/packaging/test_no_version_bump.py`.
- Ship from this branch alone (D27). The coordinated tag comes after 011–014.
- Regenerate `tests/golden/outcomes.json` — it records pre-refactor verdicts that a test asserts
  the *difference* against.
