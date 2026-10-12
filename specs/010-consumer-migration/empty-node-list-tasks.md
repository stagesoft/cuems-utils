# Tasks — empty `<node_list/>` raises `TypeError` (upstream report, 2026-09-21)

Companion checklist to [`empty-node-list-report.md`](empty-node-list-report.md), in this
repository's task format and continuing its numbering (**T085** follows T084, the last task in
`tasks.md`). Fold these into `tasks.md` under
**"Upstream findings from `cuems-nodeconf`"** (US7) if preferred — they are written to drop in
unchanged.

**Story**: US7 — upstream findings from `cuems-nodeconf`, second report.
**Priority**: blocking. It stops the coordinated feature-010 merge: on the shipped empty map
`cuems-nodeconf` fails start-up every 10 s on every fresh install, and only `cuems-nodeconf`
can write the map that would end the loop.
**Measured against**: `cuems-utils` `6fd85fc`, `../cuems-common` `f2fc0f5`,
`../cuems-nodeconf` `3e526e1`.

---

### Tests for the fix (REQUIRED, failing first) ⚠️

- [ ] **T085 [US7] Add `tests/contract/test_empty_node_list.py`, written failing-first against today's behaviour** — five cases, all on inline XML constants so the test needs no sibling checkout (the empty document is byte-identical to what `../cuems-common` ships at `f2fc0f5`, 200 bytes): (a) `NetworkMap.get_node` on an **empty** `<node_list/>` raises `ValueError` whose message is still `Node with uuid <uuid> not found` — today it raises `TypeError: 'NoneType' object is not iterable`; (b) the same for a document with **no** `node_list` element at all, the other `minOccurs="0"` shape; (c) `ConfigManager.load_network_map()` against an empty map raises `ValueError`, so the contract holds at the public boundary consumers actually use; (d) the empty document still **round-trips** — load, refill `node_list` with one node, `save`, re-load and find it, which is the fresh-node boot sequence and what makes the fix sufficient rather than merely quieter; (e) a non-empty map still resolves a present uuid and still raises `ValueError` for an absent one, so the guard does not change the found case. Cases (a)-(c) MUST fail before T086 and pass after. Precedent for the file's shape: `tests/contract/test_save_permissions.py`, written the same way for the previous report from this consumer

### Implementation

- [ ] **T086 [US7] Guard the one unguarded iteration in `src/cuemsutils/xml/settings.py:158-160`** (`NetworkMap.get_node`): `nodes_list = network_dict.get('node_list') or []`. **The trap to avoid**: a `.get('node_list', [])` default does **not** work — an empty `<node_list/>` decodes to a key that is *present* with value `None`, so the default never fires; this is why the neighbouring code at `:187` and `:236` is safe by its `if not node_list:` check rather than by its default. Add the comment explaining that "no nodes at all" is the same answer as "no node with this uuid" — `ValueError` — which is what `ConfigManager.node_network_map` already documents and what `../cuems-nodeconf`'s fresh-node path catches. Keep the message unchanged: consumers log it and a consumer test pins it (FR-1, FR-2)
- [ ] **T087 [P] [US7] Confirm no sibling path is unguarded**, so the fix is known to be complete rather than assumed: `xml/settings.py:187-190` and `:236-242` (guarded by falsy check), `config/network_map.py:181` `refresh`/merge (`or []`), and `save` on an empty document. All four were measured safe on 2026-09-21; re-measure after T086 and record the result. If any is not, it belongs in this same change, not a later one

### Recording it

- [ ] **T088 [P] [US7] Record the finding in `specs/010-consumer-migration/migration-guide.md`**, beside the existing §4a: the shipped map has had an empty `<node_list/>` since `../cuems-common`'s `f78c876`, so **the failing case was the default case on every node**, and `get_node`'s contract now holds for it. Note why three suites missed it — XSD-only validation in `cuems-common`, no empty-map `ConfigManager` test here, and non-empty fixtures in `cuems-nodeconf` — because that gap, not the one line, is the reusable lesson
- [ ] **T089 [P] [US7] Answer the consumer**: tell `../cuems-nodeconf` (feature `002-public-network-map-path`, whose research.md R3 is blocked on this) when the fix lands — it lands **inside `0.1.0rc16`** (T090), so that repository's pins do not move and its merge candidate is not re-cut; it only needs to rebuild `cuemsutils` from the fixed commit. Its option A — seeding a fresh node with the same empty map and loading it back — is unimplementable until then, and its `except ValueError` catch needs **no** change once this lands

### The release decision — already taken

- [ ] **T090 [P] [US7] Record that this patch ships inside `0.1.0rc16`, with no version bump** (maintainer, 2026-09-21). Keep `src/cuemsutils/__init__.py` at `__version__ = "0.1.0rc16"`. It is sound because **rc16 was never released**: this repository's tags stop at `v0.1.0rc14`, there is no `debian/` directory, and consumers build the wheel from a checkout — rc16 is the in-development candidate. Precedent: the previous report's `save_document` permissions fix landed inside rc16 the same way (`6fe2d3f`). Consequences are all absence of work: consumers' pins stay exactly as they are (`cuems-utils (>= 0.1.0rc16), (<< 0.1.1~)` in `../cuems-nodeconf`'s `debian/control` plus the matching `pyproject.toml` floor, FR-091 satisfied untouched), and **the merge candidate is not re-cut** — its tag moves only for packaged content, and none changes. **The caveat to write down with it**: inside rc16 the version cannot distinguish a build made before this fix from one made after, since `>= 0.1.0rc16` matches both. Nothing in packaging can express that, so the rule is operational — rebuild or reinstall `cuemsutils` from the fixed commit in every dev venv and packaging run, with T085's tests as the discriminator

---

## Dependencies & execution order

```
T085 (failing tests)  →  T086 (the fix)  →  T087 (completeness re-check)
                                         ↘  T088, T089  [P, after T086]
T090 is a recording task (decision already taken); it blocks nothing
```

- **T085 before T086** — the point is a test that fails first; writing it after proves nothing.
- **T087, T088, T089** are `[P]`: different files, no shared state.
- **T090** is a recording task now that the decision is taken; no re-cut follows from it.

## Definition of done

- [ ] The three failing cases in T085 pass, and the library's own suite stays green
- [ ] No other `node_list` consumer is unguarded (T087, measured not assumed)
- [ ] `../cuems-nodeconf` boots on the shipped empty map against the fixed library, with its
      `except ValueError` unchanged — already demonstrated by monkeypatch from the consumer
      side (report §6: read 0 nodes → write → re-read 1 node)
- [ ] T090 is recorded: the fix ships inside `0.1.0rc16`, `__version__` unchanged, no pin moves,
      no candidate re-cut, and the rebuild caveat written down
