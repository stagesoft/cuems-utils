<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Prompt — `cuems-nodeconf`: make the test fixtures uuid4 (cuems-utils feature 012)

**Run this in `cuems-nodeconf`, on `feat/xml-refactor`.** It is written to be
self-contained: you do not need to have read `cuems-utils`' feature 012 to
execute it, and the background you do need is in §1.

Authored in `cuems-utils` at `specs/planning/` (this repository's canonical home
for agent prompts) because that is where the measurement was taken. The change
it asks for is entirely in `cuems-nodeconf`.

**Size**: four fixture values and one stale comment. Roughly a fifteen-minute
change. Most of this document is *why*, so that you do not pattern-match the
diff and miss the one judgement call in §6.

---

## 1. Background — what changed upstream

`cuems-utils` feature 012 (*uuid4 convergence*) narrows the node-identity type in
three schemas. `network_map.xsd`, `project_mappings.xsd` and `settings.xsd` now
type every node `uuid` as `cms:NodeUuidType`, which is the union of exactly two
things:

```
ConvergedUuidType       uuid4, lowercase, exactly 36 characters
NotProvisionedUuidType  00000000-0000-0000-0000-000000000000  (the sentinel, one value)
```

Anything else — a uuid1, a uuid5, an upper-case uuid4, or a plausible-looking
hex string that is neither — is **refused at read and at write**.

Two consequences that shape everything below:

- **The sentinel is still accepted.** A freshly installed node carries it, and
  `cuems-nodeconf`'s `settings_sentinel.xml` fixture is unaffected.
- **A refused *write* is where this bites you**, not a refused read.
  `CuemsNetworkMapType.save()` validates before writing, so a map holding a
  non-uuid4 identity is simply never written — and the test then fails several
  steps later, somewhere that looks unrelated.

## 2. The failures

Measured 2026-09-30, running `cuems-nodeconf`'s suite against `cuems-utils` at
feature 012 versus at `a451036` (the commit immediately before it), everything
else held fixed:

| | Before | After |
|---|---|---|
| `cuems-nodeconf` | **173 passed** | **169 passed, 4 failed** |

| Test | Symptom | Actual cause |
|---|---|---|
| `test_network_map.py::TestRefreshWritesOnlyWhatItMust::test_an_unchanged_map_is_not_rewritten` | `assert os.path.exists(map_path)` is False | the save was refused, so no file was written |
| `test_network_map.py::TestReadNetworkMap::test_reads_a_map_that_does_not_list_this_node_yet` | `SchemaError` on `settings.xml` | the fixture mints a **uuid1** |
| `test_node_adoption.py::TestNodeAdoption::test_adopt_node_writes_a_schema_valid_map_end_to_end` | `SchemaError` on the map | the fixture identity is uuid5-shaped |
| `test_phase1_changes.py::test_roundtrip_preserves_role_id_alias_hostname` | `KeyError: 'aabbccddeeff'` | the save was refused, so the re-read map is empty |

**Four symptoms, three of them misleading, one cause.** Do not fix them
individually.

### Reproduce

```bash
cd cuems-nodeconf
PYENV_VERSION=3.11.9 uvx \
  --with-editable /path/to/cuems-utils \
  --with pytest --with zeroconf --with netifaces --with pyyaml \
  --from pytest pytest -q
```

Use a `cuems-utils` checkout on `012-uuid4-convergence` (or later). The control
arm is the same command against a worktree of `a451036`.

## 3. The change

Replace each non-converged fixture identity with a uuid4. The values below keep
the existing visual pattern so the diff stays readable — only two nibbles move
per value.

| File | Line(s) | From | To |
|---|---|---|---|
| `tests/test_network_map.py` | 132, 161 | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` | `aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee` |
| `tests/test_network_map.py` | 207 | `uuid.uuid1()` | `uuid.uuid4()` |
| `tests/test_node_adoption.py` | 241, 251, 262 | `12345678-1234-5678-1234-567812345678` | `12345678-1234-4678-8234-567812345678` |
| `tests/test_phase1_changes.py` | 28, 54, 141 | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` | `aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee` |

A whole-file substitution is safe and is what was verified:

```bash
sed -i 's/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee/g' \
    tests/test_network_map.py tests/test_phase1_changes.py
sed -i 's/12345678-1234-5678-1234-567812345678/12345678-1234-4678-8234-567812345678/g' \
    tests/test_node_adoption.py
sed -i 's/uuid\.uuid1()/uuid.uuid4()/g' tests/test_network_map.py
```

**Check the `uuid1` → `uuid4` substitution by eye afterwards.** It is the one
that could in principle catch an unrelated call; at the time of measurement
`tests/test_network_map.py` had exactly one `uuid.uuid1()`, at line 207.

### Why these values, so you can pick your own if you prefer

A uuid4 is constrained in exactly two places:

```
xxxxxxxx-xxxx-Mxxx-Nxxx-xxxxxxxxxxxx
              ^    ^
              |    variant nibble: must be 8, 9, a or b
              version nibble: must be 4
```

Everything else is free hex, and it must be **lowercase**. `cccc` → `4ccc` sets
the version; `dddd` → `8ddd` sets the variant. Nothing else about the value
matters to the schema.

Sanity-check any value you invent:

```bash
python3 -c "
from cuemsutils.tools import ids
print(ids.classify('aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'))"   # -> converged
```

`cuemsutils.tools.ids.classify` is public and returns one of `converged`,
`not-converged`, `not-provisioned`, `unrecognised`.

## 4. One comment goes stale with it

`tests/test_network_map.py`, in the docstring above the line-207 fixture:

> `cuems-config-node write` gives settings.xml a new uuid and leaves
> network_map.xml alone, so on first boot the map lists other nodes…

**`cuems-config-node` no longer mints.** `cuems-utils` feature 011's D14
(shape B) moved identity minting to `cuems-init-node`, and the shipped templates
carry the sentinel.

The test's *premise* — nodeconf must be able to read a map that does not yet
list this node — is still exactly right and still worth testing. Only the
sentence naming the minter is wrong. Correct it in the same commit: you are
editing the line directly beneath it, and a reader who arrives at the fixed uuid
will read the stale sentence on the way.

Suggested replacement for that clause: *"`cuems-init-node` gives settings.xml
its identity and seeds this node's own row; on a node provisioned before that
existed, the map lists other nodes but not this one."*

## 5. What **not** to do

- **Do not change anything in `cuemsnodeconf/`.** No production code is
  implicated. If you find yourself editing the daemon, you have mis-diagnosed.
- **Do not touch `tests/fixtures/etc_cuems/*.xml`.** Those identities are
  already converged (`0367f391-ebf4-48b2-9f26-…` is a valid uuid4 — version
  nibble `4`, variant `9`) and `settings_sentinel.xml` is *supposed* to carry
  the sentinel.
- **Do not add a `pytest.skip`, an `xfail`, or a try/except around a save.** The
  schema is refusing invalid data and it is right to.
- **Do not pin `cuemsutils` to an older version to make this go away.** The
  narrowing ships in the coordinated tag; the pin would have to come back out.
- **Do not "fix" the four tests separately.** Three of them fail with symptoms
  that have nothing to do with identities; chasing those symptoms produces four
  unrelated-looking changes and leaves the cause in place.

## 6. Recommended, not required — the unguarded `ValidationError`

This is the one judgement call, and it is yours (or your maintainer's). It is
**not** needed to make the suite pass.

`CuemsNodeConf.read_network_map` (around `CuemsNodeConf.py:859`) catches
`ValueError` only:

```python
try:
    manager.load_network_map()
except ValueError:
    # this node is not in the map yet -- every freshly provisioned node
    ...
```

Feature 012 adds a registered, **not repairable** uniqueness rule: a map with
two rows carrying one identity now raises `cuemsutils.errors.ValidationError`
for every reader. `ValidationError` subclasses `CuemsError(Exception)` and is
**not** a `ValueError`, so it propagates straight out of `read_network_map` and
takes the daemon's startup with it.

**The outcome is right** — a daemon whose job is to write the map must not write
over a collision. **The presentation is not**: it arrives as an unhandled
traceback, on the one component an operator would look to for a diagnosis.

If you take it, the shape is a diagnosis plus a deliberate exit, not a recovery:

```python
from cuemsutils.errors import ValidationError

except ValidationError as e:
    # Two rows share one identity. cuemsutils refuses to guess which is the
    # real node -- and so must we: the compound <identity>_<output> prefix in
    # the project library is the only record of which node an output belongs
    # to, so splitting the pair would silently reassign one node's outputs.
    Logger.error(f'network_map.xml cannot be read: {e}')
    Logger.error('Resolve the collision by hand before starting nodeconf -- see '
                 'the cuems-utils migration guide, section 7.')
    raise SystemExit(1)
```

Do **not** make it recoverable. Do not merge, de-duplicate or pick a row.

Two related observations, neither requiring action:

- `cuems-power-bridge` has the same gap with a different symptom: its classifier
  has no branch for this message and tells the operator the document is missing
  a required field. That is the bridge's own follow-up.
- No repository has a colliding-map test fixture, which is why this whole class
  of behaviour is invisible in CI and real in the field.

## 7. Verification

```bash
# 1. against feature 012 -- must be 173 passed
PYENV_VERSION=3.11.9 uvx --with-editable /path/to/cuems-utils \
  --with pytest --with zeroconf --with netifaces --with pyyaml \
  --from pytest pytest -q

# 2. against a451036 -- must ALSO be 173 passed
git -C /path/to/cuems-utils worktree add /tmp/utils-base a451036
PYENV_VERSION=3.11.9 uvx --with-editable /tmp/utils-base \
  --with pytest --with zeroconf --with netifaces --with pyyaml \
  --from pytest pytest -q
git -C /path/to/cuems-utils worktree remove /tmp/utils-base
```

**Both arms must be 173 passed.** That is the property that lets this land
*before* the coordinated tag instead of inside it — see §8. Both were verified
on 2026-09-30 with exactly these substitutions applied to a scratch copy.

If arm 2 fails, you have used a value that is not valid under the *old* schema
either; check it is 36 lowercase hex-and-hyphen characters.

## 8. Why this can land ahead of the coordinated tag

`aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee` is as valid under `cuems-utils` `0.1.0rc16`
as it is under feature 012 — the old `UuidType` accepted *any* canonical uuid
shape, and the new one accepts this particular one. The change is therefore
**forward- and backward-compatible**, and there is no reason to hold it inside
the `xml-refactor-merge-candidate` coordination.

Landing it now takes `cuems-nodeconf` off the critical path: the tag set can
then be re-cut once, for content, rather than twice.

**It does mean the tag should be re-cut after this lands** — see
`cuems-utils`' `specs/012-uuid4-convergence/sibling-repository-updates.md` §6
for the ordering, and note that moving a *published* tag is the maintainer's
call, not an agent's.

## 9. Context worth carrying, requiring no change here

**There is no `cuems-utils` rollback once `cuems-nodeconf` restarts.** The three
schemas take a document-version step (`network_map` 1→2, `project_mappings`
1→2, `settings` 2→3). The re-mint itself is a literal token substitution and
never touches the marker, so a re-minted document is still readable by the old
library — but `CuemsNetworkMapType.save()` emits the *current* marker, and
**this daemon rewrites the map on every debounced Avahi event or every 30
seconds regardless**. So within about a minute of starting nodeconf on an
upgraded node, the map carries `doc_version="2"` and an older `cuems-utils`
refuses it:

```
network_map document is version 2, newer than this library's current version 1
for network_map.xsd — upgrade cuemsutils to read it
```

Nothing to fix — that is the version marker doing its job. But it is worth
knowing that this daemon is what closes the rollback window, and how fast.

## 10. Commit

One commit. Suggested message, adapt as you see fit:

```
test: node identities in fixtures must be uuid4 (cuems-utils feature 012)

cuems-utils narrows the node-identity type in network_map.xsd,
project_mappings.xsd and settings.xsd to uuid4 lowercase plus the
not-provisioned sentinel. Four fixtures here carried values that are neither:
three uuid-shaped-but-not-uuid4 constants and one uuid.uuid1() call.

Four tests failed and three of them misleadingly. CuemsNetworkMapType.save()
validates before writing, so a map holding a refused identity is never written
and the test falls over later -- a missing file, a KeyError on a re-read map --
rather than where the fault is. One cause, four symptoms.

Only the version and variant nibbles move, so every replacement value is also
valid under the current cuemsutils: 173 passed against both 0.1.0rc16 and the
feature-012 branch. That is why this does not need to wait for the coordinated
xml-refactor-merge-candidate tag.

Also corrected: the docstring above the last of them still credited
cuems-config-node with minting the identity. Feature 011's D14 (shape B) moved
that to cuems-init-node. The test's premise is unchanged and still right.

No production code is touched.
```

Commits in this ecosystem are **GPG-signed**. On `gpg failed to sign`, retry;
never `--no-gpg-sign`.

## 11. If something does not match

This was measured on 2026-09-30 against `cuems-nodeconf` `feat/xml-refactor` at
`e63fb6e`. If the line numbers have moved, the values in §3 are still the thing
to search for — grep for them rather than trusting the numbers. If a *fifth*
test fails, it is probably a fixture identity too: run

```bash
grep -rnE "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}" tests/ \
  | grep -v "0367f391-ebf4-48b2\|00000000-0000-0000"
```

and classify each hit with `ids.classify`.
