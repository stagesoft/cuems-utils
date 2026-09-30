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

## The six things that will cost you a revert

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
5. **Never restore a rewritten file's modification time.** The substitution replaces 36
   characters with 36, so every rewritten file is *exactly the size it was*. The library reaches
   the nodes by `rsync -rt` with no checksum — size and time are all it compares. Preserving
   times would leave every node's replica stale forever, with no error anywhere (FR-011b,
   research R11). `os.replace` already does the right thing; the trap is "helpfully" adding
   `shutil.copystat`.
6. **"Converged" means uuid4, never uuid4-or-sentinel.** The set the schemas accept is the
   *admitted* set, and it is two named definitions unioned, not one widened pattern. FR-021b's
   decode table and the published coercion rule both give the wrong answer if the two words blur
   (data-model §1.2, FR-021c).

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
C  the re-mint        US2   the bulk; needs the foundational phase only, not A
D  the narrowing      US3   LAST — three schemas, three version steps, no conversions (R5)
E  the migration guide US5  needs C and D measured — not B
```

**Where the re-mint runs.** The configuration documents are per node: every node rewrites its
own, from the table the controller built and handed it. The library is controller-authoritative:
rewritten once, on the controller, and replicated to the nodes by the project deployer on the
next project load. A plain node with no table refuses rather than minting one — but a table whose
`controller` is another node is the **normal** case, not a refusal (FR-011a, contracts/cli-remint.md).

## The budget, in numbers

| Budget | Value |
|---|---|
| Re-mint throughput | ≥ 500 MB/s scanned and rewritten |
| Agreement between **2 and 10** nodes | slower elapsed time ≤ **1.10×** the faster |
| Fixture `remint_200` (200 projects, ~4 MB) | ≤ 2.0 s — **provisional**, lower it to the measured figure, never raise it |
| Operator estimate vs. actual | within ±25% |
| Read path — show document | feature 008's recorded **budget** |
| Read path — `network_map` | feature 008's recorded **measured band**, 10.14–10.49 ms (its budget is recorded there as exceeded-or-marginal) |

**The estimate divides surveyed bytes by the throughput the survey measured on this machine — not by
the 500 MB/s constant.** 500 is a *floor* T077 asserts the implementation beats, so dividing by it
would overstate every estimate by the margin of the beating and fail the ±25% while the
implementation was correct. The floor is the fallback only, for a survey too small to time, and the
output must say when it was used.

**The agreement bound is a ratio, not a percentage**, because the fixture runs in single-digit
milliseconds: 1% of that is below this machine's jitter. 1.10× still catches the defect it exists to
catch, since a per-node repeated pass makes the 10-node run about 5× the 2-node run.

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
- Create a `tests/performance/` directory — the timing tests go in `tests/integration/`, where
  this repository already keeps them.
- Raise the fixture ceiling to make a slow implementation pass. It moves downward only.
