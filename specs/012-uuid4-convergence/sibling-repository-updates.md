<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# What feature 012 requires of each sibling repository

**Written for: the maintainers of the six CUEMS sibling repositories.** It says
what breaks, what to change, and in what order — not why the library was built
this way, which is [spec.md](spec.md) and [plan.md](plan.md).

This goes further than [consumer-census.md](consumer-census.md) in one specific
way. The census was a **grep and a reading of exception handlers**, which is what
FR-032 asked for. This is a **measurement**: every sibling's own test suite, run
twice — once against `cuems-utils` at `a451036` (immediately before this feature)
and once against the feature branch — with everything else held fixed.

---

## 1. The measured result

| Repository | Before (`a451036`) | After (012) | Δ | Action |
|---|---|---|---|---|
| **`cuems-engine`** | 939 passed | 939 passed | **0** | none required |
| **`cuems-nodeconf`** | 173 passed | **169 passed, 4 failed** | **−4** | **§2 — one-line fixture fixes** |
| **`cuems-power-bridge`** | 276 passed | 276 passed | **0** | none required; see §5.2 |
| **`cuems-editor`** | 54 passed, 7 failed | 54 passed, 7 failed | **0** | none from this feature; see §5.3 |
| `cuems-common` | no Python reader | — | — | none |
| `cuems-frontend` | TypeScript, consumes JSON | — | — | none |

**One repository has work to do, and it is four lines.**

### How to reproduce

```bash
# the "after" arm
cd <sibling>
PYENV_VERSION=3.11.9 uvx --with-editable /path/to/cuems-utils \
    --with pytest --with pytest-asyncio <repo's own extras> \
    --from pytest pytest -q

# the "before" arm: same command against a worktree of a451036
git -C /path/to/cuems-utils worktree add /tmp/utils-base a451036
```

`cuems-engine` needs `pyossia`, which is native and not installable this way —
its existing `.venv` already carries it, and already has `cuemsutils` installed
editable, so it runs directly. The control arm shadows the library with
`PYTHONPATH=/tmp/utils-base/src`.

`cuems-editor`'s `tests/test_media.py` and `tests/test_repair_durations.py` fail
to **import** in both arms: they import `cuemsutils.create_script`, which
**feature 008 retired**. That is pre-existing debt from the 008/010 migration and
is excluded from both arms so the comparison is like-for-like. It is listed in
§5.3 because someone should still fix it.

---

## 2. `cuems-nodeconf` — required, and small

All four failures have **one cause**: test fixtures whose node identities are not
uuid4. The narrowed `cms:NodeUuidType` refuses them, so the map fails validation
on write and the test's later assertions fall over somewhere else entirely —
which is why the failures *look* like four different problems.

| Test | Symptom | Real cause |
|---|---|---|
| `test_network_map.py::TestRefreshWritesOnlyWhatItMust::test_an_unchanged_map_is_not_rewritten` | `assert os.path.exists(map_path)` is False | the save was refused, so no file was written |
| `test_network_map.py::TestReadNetworkMap::test_reads_a_map_that_does_not_list_this_node_yet` | `SchemaError` on `settings.xml` | the fixture mints a **uuid1** at line 207 |
| `test_node_adoption.py::TestNodeAdoption::test_adopt_node_writes_a_schema_valid_map_end_to_end` | `SchemaError` on the map | the fixture identity is uuid5-shaped |
| `test_phase1_changes.py::test_roundtrip_preserves_role_id_alias_hostname` | `KeyError: 'aabbccddeeff'` | the save was refused, so the re-read map is empty |

### The change

Replace each non-converged fixture identity with a uuid4. Any lowercase uuid4
will do; the values below keep the existing visual pattern so diffs stay
readable.

| File | Line(s) | From | To |
|---|---|---|---|
| `tests/test_network_map.py` | 132, 161 | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` | `aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee` |
| `tests/test_network_map.py` | 207 | `uuid.uuid1()` | `uuid.uuid4()` |
| `tests/test_node_adoption.py` | 241, 251, 262 | `12345678-1234-5678-1234-567812345678` | `12345678-1234-4678-8234-567812345678` |
| `tests/test_phase1_changes.py` | 28, 54, 141 | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` | `aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee` |

Only two nibbles move per value: the **version** nibble (third group, must be
`4`) and the **variant** nibble (fourth group, must be `8`, `9`, `a` or `b`).

### One comment goes stale with it

`tests/test_network_map.py`'s docstring around line 200 says:

> `cuems-config-node write` gives settings.xml a new uuid and leaves
> network_map.xml alone…

`cuems-config-node` **no longer mints** — feature 011's D14 (shape B) moved that
to `cuems-init-node`, and the shipped templates carry the sentinel. The test's
*premise* (nodeconf must be able to read a map that does not yet list this node)
is still exactly right and still worth testing; only the sentence naming the
minter is wrong. Worth correcting in the same commit, since changing the uuid on
line 207 puts a reader right next to it.

### What does **not** need changing

Nothing in `cuemsnodeconf/` itself. The static fixtures under
`tests/fixtures/etc_cuems/` are already converged (`0367f391-ebf4-48b2-…` is a
valid uuid4 — version nibble `4`, variant `9`), and the sentinel fixture is
*admitted* by the narrowed type by design.

---

## 3. The operational finding neither suite could catch

**A `cuems-utils` downgrade after the upgrade is a one-way door, and the reason
is not the re-mint.**

Measured:

| Action | `doc_version` in `network_map.xml` | Readable by the **old** library? |
|---|---|---|
| the re-mint rewrites the map | **stays 1** | **yes** |
| anything writes the map through the library | **becomes 2** | **no** — `DocumentTooNewError` |

The re-mint is a literal token substitution and never touches the version
marker, so a re-minted document remains readable by `0.1.0rc16`. But
`CuemsNetworkMapType.save()` emits the current marker, and **`cuems-nodeconf`
writes the map on every debounced Avahi event or every 30 seconds regardless**
(`CuemsNodeConf.py:538-540`, resident loop at `:655`).

So within about a minute of starting `cuems-nodeconf` on an upgraded node, the
map carries `doc_version="2"` and rolling `cuems-utils` back makes every reader
on that node fail with:

```
network_map document is version 2, newer than this library's current version 1
for network_map.xsd — upgrade cuemsutils to read it
```

That is the version marker working exactly as feature 008 designed it — a clear
diagnosis instead of a confusing decode failure. It is still a fact an operator
must know **before** the upgrade window, because the usual rollback plan does not
work after it.

**Actions**: the migration guide gains a "no rollback after restart" statement
(this repository's job, done); `cuems-nodeconf` and `cuems-common` maintainers
should know that a staged rollback is not available once the daemon has run.

---

## 4. Two requirement-level findings this measurement changes

### 4.1 FR-035's stated reason no longer holds — re-check the coupling

FR-035 couples the re-mint to `cuems-engine 0.1.0rc7`, because an older engine's
`cluster_status` *"cannot sort the resulting identities"*.

**FR-029 fixes that at the library level.** `Uuid` now has a total ordering
consistent with its string form, and it crosses the `str` boundary in both
directions:

```python
sorted([Uuid(b), a, Uuid(a)])   # works
a < Uuid(b)                      # True — via the reflected operator
```

So the specific failure FR-035 names would no longer occur under an older
engine.

**This is not an argument for dropping the coupling** — rc7 carries other work,
and nobody has measured a pre-rc7 engine against this branch. It is an argument
for re-stating *why* the coupling exists, because a precondition justified by a
failure that can no longer happen is a precondition people will eventually
ignore. Owner: whoever amends FR-035.

### 4.2 `cuems-engine`'s `as_id` can now be deleted

`cuems-engine/src/cuemsengine/tools/ids.py:21` defines `as_id`, which is the
hand-written mirror of this library's coercion rule that M-c recorded. It is now
published as `cuemsutils.tools.coerce_identity`, and the two **agree on every
input** — converged → `Uuid`, sentinel → `str`, anything else non-empty → `str`,
empty → `None`.

```python
from cuemsutils.tools import coerce_identity as as_id
```

Optional, and the point of publishing the rule: the copy can be deleted rather
than left to drift. `id_str` has no library equivalent and stays.

---

## 5. Things that did not fail, and are worth knowing anyway

### 5.1 `cuems-engine` needs nothing (939/939, both arms)

rc7 already did the work the census predicted would be needed. Every measured
site goes through `as_id` on ingress and `id_str` on egress, `cluster_status`
sorts via `id_str`, and `_cluster_warning_payload` serialises strings — so
nothing meets a `Uuid` where a `str` is required, and `json.dumps` never sees
one. The type change is invisible to it.

### 5.2 `cuems-power-bridge` is safe but will describe a collision wrongly

276/276 in both arms — nothing to fix. But its error classifier has no branch for
the new node-identity uniqueness violation, so a colliding map falls through to
its final case (`network_map.py:250-257`) and tells the operator:

> *"…is not a valid document (…). Every node needs uuid, mac, name, node_role
> and ip; fix the document (or restore it from the package) and retry."*

Every node **does** have all five. The fault is that two of them share an
identity, and the advice sends the operator looking for a missing field. No test
covers this because no fixture has a colliding map.

**Suggested change** — one branch in `_classify`, matching the rule's own
wording the way the existing `_RETIRED_MARKERS` branch does:

```python
if "node identities are not unique" in low:
    return TopologyError(
        TopologyErrorKind.NETWORK_MAP_INVALID,      # or a new kind
        f"{network_map_path} has two rows carrying one node identity ({text}). "
        f"Resolve it by hand before re-minting — see the cuems-utils migration "
        f"guide, section 7.",
    )
```

Priority: low. It costs nothing until a cluster actually collides, and then it
costs an operator an hour.

### 5.3 `cuems-editor` has pre-existing debt, none of it this feature's

- **7 failures in both arms**, all in
  `test_nodelist_actions.py::TestNodeconfAvailableFlag`. Unrelated to identities.
- **2 modules that will not import in either arm**: `tests/test_media.py` and
  `tests/test_repair_durations.py` import `cuemsutils.create_script`, retired by
  **feature 008**. These have been broken since that landed and nobody noticed,
  which is itself worth knowing.

Two live sites are worth a maintainer's attention even though they pass today:

- `CuemsWsUser.py:407` — `if not node_uuid or not isinstance(node_uuid, str)`.
  `Uuid` is **not** a `str` subclass, so this would reject one. It is fed from
  the websocket (the frontend sends JSON), so it is unreachable today. Keep it
  unreachable: do not let a library-decoded identity into a wire payload.
- `CuemsWsServer.py:447` — `reload_network_map_nodes` retries **three times with
  exponential back-off** and then logs and returns `False`. The retries exist for
  a map being written concurrently; a colliding map is permanent, so all three
  are spent and the settings panel shows a stale node list. The operator-visible
  symptom — "the node list stopped updating" — does not point at the map.

### 5.4 One false lead, named so nobody chases it

`cuems-editor/src/cuemseditor/cli.py:36` does
`settings_dict['session_uuid'] = str(uuid.uuid1())`. It is a **uuid1** and it is
**fine**: it is an editor *session* id in the editor's own settings dict — the
same private dict that holds `script_file_name` (research R3) — and it reaches no
schema-validated document. Nothing to change.

---

## 6. Ordering

1. **`cuems-nodeconf`'s fixture fixes land first**, and can land now: they are
   correct against the current library too — `aaaaaaaa-bbbb-4ccc-8ddd-…` is as
   valid a uuid4 today as it will be after. Landing them ahead of time removes
   this repository from the critical path.
2. **Everything else ships together**, at the coordinated
   `xml-refactor-merge-candidate` tag after features 011–014 (D27). Nothing ships
   from feature 012's branch alone.
3. **The re-mint itself is an operator procedure, not a release step.** See
   [migration-guide.md](migration-guide.md) — and §7 of it, the pre-existing
   collision procedure, must run **before** the narrowing reaches a cluster,
   while the map still loads.
4. **Optional follow-ups**, in no particular order and none blocking: the
   power-bridge classifier branch (§5.2), deleting `as_id` (§4.2), re-stating
   FR-035 (§4.1), and the editor's pre-existing failures (§5.3).

---

## 7. What the census got right, and what this adds

The census (FR-032, FR-032a) was right about the **shape** of the risk, and its
second column earned its place: it found that the map-read change reaches four
repositories rather than the two that read the own-identity accessor, and that
`cuems-editor` — absent from research R4 entirely — is one of them.

What measurement adds is **proportion**, and it is not what the census would have
led you to expect:

- the census's *loud* risk (a map read raising) produced **zero** test failures,
  because no sibling has a colliding-map fixture. It remains real in the field
  and invisible in CI, which is the worst combination and the reason §7 of the
  migration guide exists;
- the census's *silent* risk (the changed accessor type) also produced **zero**
  failures — rc7 had already absorbed it;
- the actual failures came from somewhere the census did not look at all: **test
  fixtures carrying identities that are not uuid4**. A census of *call sites*
  cannot find those, because they are data.

The lesson for the next schema narrowing: audit the fixtures as well as the code,
in every repository that has any. The query is two lines and it would have found
all four of these before anything was written.
