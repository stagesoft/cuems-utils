# Upstream report — an empty `<node_list/>` raises `TypeError`, not `ValueError`

**Raised 2026-09-21 from `../cuems-nodeconf`'s feature `002-public-network-map-path`.**
**Severity: blocks the coordinated feature-010 merge.** Measured against `cuems-utils`
`6fd85fc` (`0.1.0rc16`), `../cuems-common` `f2fc0f5` (= tag `xml-refactor-merge-candidate`),
`../cuems-nodeconf` `3e526e1`.

Second report from that repository; the first (`save_document`'s `0600`, two docstrings) was
received in `b6b5eb5` and closed by `6fe2d3f` / `9e5e79f`. Nothing here has been patched from
the consumer side, for the same reason as last time: the yardstick's guarantee depends on this
library's files not being edited by a consumer.

---

## 1. What happens

`NetworkMap.get_node` raises **`TypeError: 'NoneType' object is not iterable`** when the
document's `node_list` is empty, instead of the `ValueError` that `ConfigManager` documents.
Every consumer that loads a network map through `ConfigManager.load_network_map()` hits it,
because that method's last step resolves *this node* through `get_node`.

`../cuems-common` has shipped `/etc/cuems/network_map.xml` with an empty `<node_list/>` since
its `f78c876` (feature 001, T040 — removing the placeholder controller, which was correct).
**That file is what every node now installs**, so the failing case is the default case.

### Why it is a merge blocker

On any host whose map is the shipped one — every fresh install, and every upgrade where the
operator answers the conffile prompt with the maintainer's version — `cuems-nodeconf`:

1. finds the file present, so `run()` takes the "read the existing map" branch;
2. calls `read_network_map()`, which catches `ValueError` (its fresh-node case) but not
   `TypeError`;
3. fails start-up. The unit has `Restart=on-failure` / `RestartSec=10`, so it retries every
   ten seconds and fails identically.

Nothing breaks that loop: **only `cuems-nodeconf` writes a node into the map**, and it never
gets that far. `cuems-engine`'s `load_config()` calls the same `load_network_map()`, so it is
exposed the same way (the call was measured; the engine process was not run).

### How three test suites missed it

| Repository | Why it did not catch this |
|---|---|
| `cuems-common` | T040 validated the empty map against the **XSD** only; it never loaded it through `ConfigManager` |
| `cuems-utils` | no test loads an empty `node_list` through `ConfigManager` or `get_node` |
| `cuems-nodeconf` | every fixture map in `tests/fixtures/` contains nodes |

---

## 2. Root cause — one unguarded iteration

`src/cuemsutils/xml/settings.py:158-160`, `NetworkMap.get_node`:

```python
def get_node(self, uuid):
    out = None
    network_dict = self.get_dict()
    nodes_list = network_dict.get('node_list')   # ← None when <node_list/> is empty
    for node_item in nodes_list:                 # ← TypeError here
```

**The key exists and its value is `None`**, so a `.get('node_list', [])` default would *not*
help — this is the trap to avoid when fixing it. The neighbouring code already handles it,
which is why only this one path fails:

| Site | Guard | Safe? |
|---|---|---|
| `xml/settings.py:159` `get_node` | none | ❌ **the defect** |
| `xml/settings.py:187-190` | `if not node_list: return ...` | ✅ (by the falsy check, not the default) |
| `xml/settings.py:236-242` | `if not node_list: return ...` | ✅ (same) |
| `config/network_map.py:181` `refresh`/merge | `(self.get("node_list") or [])` | ✅ |
| `../cuems-nodeconf` `_index_from_document` | `document.get('node_list') or []` | ✅ |

So `refresh`, `merge` and `save` already work on an empty document. **`get_node` is the only
thing standing between a fresh node and a working boot.**

### The contract it breaks

`src/cuemsutils/tools/ConfigManager.py` documents, on `node_network_map`:

> `ValueError`: if no node in the map carries this node's uuid.

An empty map is precisely "no node carries this uuid". It should raise `ValueError`.
Consumers already rely on that: `../cuems-nodeconf`'s `read_network_map` catches `ValueError`
alone, deliberately narrowly, so that `SchemaError` and friends still fail loudly.

---

## 3. Reproduction — self-contained, no sibling checkouts needed

Verified verbatim on 2026-09-21 against `6fd85fc` (run it in a venv where `cuemsutils` and its
dependencies are installed — a bare interpreter fails earlier, on `deprecated`):

```python
# From the cuems-utils repository root.
import tempfile, os
from cuemsutils.xml.settings import NetworkMap

EMPTY = b"""<?xml version='1.0' encoding='utf-8'?>
<cms:CuemsNetworkMap xmlns:cms="https://stagelab.coop/cuems/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <node_list/>
</cms:CuemsNetworkMap>
"""
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "network_map.xml")
    open(p, "wb").write(EMPTY)
    nm = NetworkMap(p)
    nm.get_node("0367f391-ebf4-48b2-9f26-000000000001")
    # expected: ValueError("Node with uuid ... not found")
    # actual  : TypeError: 'NoneType' object is not iterable
```

That XML is byte-identical to what `../cuems-common` ships at `f2fc0f5`
(`etc/cuems/network_map.xml`, 200 bytes).

---

## 4. Requirements

- **FR-1**: `NetworkMap.get_node` MUST raise `ValueError` when the document has no node
  carrying the requested uuid, **including** when `node_list` is absent, empty or `None`. It
  MUST NOT raise `TypeError` for that input.
- **FR-2**: The `ValueError` message MUST stay as it is (`Node with uuid <uuid> not found`).
  `../cuems-nodeconf` logs it, and its test
  `test_reads_a_map_that_does_not_list_this_node_yet` pins the behaviour.
- **FR-3**: A document with an empty `node_list` MUST remain loadable, refillable, savable and
  re-readable through the public path — `ConfigManager.load_network_map()`, then `refresh` /
  `save`. (Already true apart from FR-1; it needs a test so it stays true.)
- **FR-4**: The fix MUST NOT change the schema, and MUST NOT reintroduce a placeholder node
  into any shipped document. An empty `node_list` is valid: `node_list` and `node` are both
  `minOccurs="0"` in `xml/schemas/network_map.xsd`.
- **FR-5**: The behaviour MUST be pinned by a test that **fails against today's library**.

## 5. Implementation plan

### 5.1 The change (`src/cuemsutils/xml/settings.py`)

```python
    def get_node(self, uuid):
        out = None
        network_dict = self.get_dict()
        # ``node_list`` is minOccurs="0"; an empty <node_list/> decodes to a
        # present key whose value is None, so a .get() default never fires.
        # "No nodes at all" is the same answer as "no node with this uuid":
        # ValueError, which ConfigManager.node_network_map documents and
        # cuems-nodeconf's fresh-node path catches.
        nodes_list = network_dict.get('node_list') or []
        for node_item in nodes_list:
            ...
```

One line plus the comment. It matches the guard style already used at `:187` and `:236` and in
`config/network_map.py:181`.

### 5.2 Tests — write them failing first

New file `tests/contract/test_empty_node_list.py`, following the precedent of
`tests/contract/test_save_permissions.py` (written failing-first for the previous report):

1. `get_node` on a document whose `<node_list/>` is empty raises **`ValueError`**, and the
   message still reads `Node with uuid ... not found`. *(Fails today with `TypeError`.)*
2. The same for a map with **no** `node_list` element at all — the other `minOccurs="0"` shape.
3. `ConfigManager.load_network_map()` against an empty map raises `ValueError`, not
   `TypeError`, so the documented contract holds at the public boundary consumers use.
4. The empty document still round-trips: load → refill `node_list` with one node → `save` →
   re-load finds that node. This is the fresh-node boot sequence; it is what makes the fix
   sufficient rather than merely quieter.
5. A non-empty map still resolves a present uuid, and still raises `ValueError` for an absent
   one — the guard must not change the found case.

Use an inline XML constant (as in §3), not a sibling checkout, so the test is self-contained.

### 5.3 Record it

Add a short subsection to `specs/010-consumer-migration/migration-guide.md`, beside the
existing §4a, noting that the empty shipped map is the default case and that `get_node`'s
contract now holds for it.

### 5.4 Release and pin impact — none: the patch lives in `0.1.0rc16`

**Decided by the maintainer, 2026-09-21: this fix ships inside `0.1.0rc16`. There is no
version bump.** `src/cuemsutils/__init__.py` keeps `__version__ = "0.1.0rc16"`.

That is sound rather than convenient: **rc16 has never been released.** This repository's tags
stop at `v0.1.0rc14` — there is no `v0.1.0rc16` — and it carries no `debian/` directory, so
consumers build the wheel straight from a checkout (`../cuems-nodeconf`'s packaging
demonstration takes `UTILS=<path>` and builds it). rc16 is the in-development candidate, and
this belongs in it. The **precedent is the previous report from the same consumer**: the
`save_document` permissions fix landed inside rc16 too (`6fe2d3f`), without a bump.

Consequences, all of them the absence of work:

- Consumers' pins stay **exactly** as they are — `cuems-utils (>= 0.1.0rc16), (<< 0.1.1~)` in
  `../cuems-nodeconf`'s `debian/control`, and the matching floor in its `pyproject.toml`. FR-091's
  "both files agree" still holds, untouched.
- **No re-cut of the merge candidate.** The tag `xml-refactor-merge-candidate` moves only when
  packaged content changes; no consumer's packaging changes here, so the commits the two merge
  gates cite stay put and no flow has to be told the candidate moved.

**The one caveat, stated plainly**: within rc16 the version string cannot tell a build made
before this fix from one made after — `>= 0.1.0rc16` is satisfied by both. Nothing in the
packaging can express the difference, so the discipline has to: **rebuild or reinstall
`cuemsutils` from the fixed commit** in every development venv and in any packaging run, and
treat T085's tests as the discriminator — if they fail, the installed build predates the fix.

## 6. Acceptance

- [ ] `get_node` raises `ValueError` for empty, missing and `None` `node_list`; never `TypeError`
- [ ] `ConfigManager.load_network_map()` on the shipped empty map raises `ValueError`
- [ ] The empty document loads → refills → saves → re-reads (the fresh-node sequence)
- [ ] The new tests fail against `6fd85fc` and pass after the change
- [ ] The library's own suite stays green
- [ ] `__version__` is **unchanged** at `0.1.0rc16`, and no consumer pin moves
- [ ] `../cuems-nodeconf` boots on the empty shipped map — verified there, against the fixed
      library, with no change to its `except ValueError` catch

### Already verified from the consumer side

With the fix applied only as a runtime monkeypatch (this library's files untouched), driving
`cuems-nodeconf`'s real code against `cuems-common`'s shipped empty map:

| Step | Before | After |
|---|---|---|
| 1. `read_network_map()` on the empty shipped map | `TypeError` | **OK, 0 nodes** |
| 2. write this node into the map | not reached | **OK, 513 bytes on disk** |
| 3. re-read the written map | not reached | **OK, 1 node** |

So the one-line fix is sufficient: no consumer-side change is needed, and no other guard is
missing along that path.

## 7. What NOT to do

- **Do not** have consumers catch `TypeError`. It patches a library defect from the outside,
  the catch is broad enough to swallow genuine bugs, and it leaves `cuems-engine` exposed.
- **Do not** ship a placeholder node again. `../cuems-common` removed it deliberately
  (`f78c876`), and it misrouted chrony and the log collector.
- **Do not** change `network_map.xsd`. An empty `node_list` is valid by design.
- **Do not** return `None` instead of raising. Consumers distinguish "not in the map yet" by
  catching `ValueError`; a `None` would surface later as an unrelated failure.
- **Do not** edit `tests/contract/test_nodeindex_characterization.py` — the vendored yardstick,
  byte-identical in `../cuems-nodeconf`.
