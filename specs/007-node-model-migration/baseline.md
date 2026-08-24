# Baseline — feature 007, pre-feature state

**Captured**: 2026-08-24, on `007-node-model-migration` before any source change (T001–T006f).
Environment: `PYENV_VERSION=3.11.9`, `hatch` 1.16.1.

---

## Suite figures (T002)

```
hatch test
========== 2222 passed, 94 skipped, 2 xfailed, 333 warnings in 59.53s ==========
```

Per-test: 59.53 s / 2222 = **26.79 ms/test**. Matches the feature 006 baseline recorded in
`CLAUDE.md` (~27 ms/test, 2222 passed / 94 skipped / 2 xfailed in ~59 s) — the suite is unchanged
since 006 landed. FR-PERF-001 budget for this feature: ≤ 110% of this figure, i.e. ≤ 29.47 ms/test.

## `network_map` load timing (T003)

`ConfigManager.load_network_map()` against `tests/data/network_map.xml`, median of 5 runs (process
warm, imports already paid):

```
runs (ms): [10.167, 11.098, 12.56, 10.351, 9.721]
median (ms): 10.351
```

FR-PERF-001 budget for this feature: ≤ 110% of this figure, i.e. ≤ 11.39 ms.

## `tests.support.capture_goldens` — a pre-existing, unrelated anomaly (T001)

Running `pyenv exec python -m tests.support.capture_goldens` (no `--force`) on unmodified HEAD
reports 10 conflicts, all in the **legacy** `dict/*.config.json` golden set (the `.xml_dict`
property of the deprecated `cuemsutils.xml.{Settings,NetworkMap,ProjectMappings,ProjectSettings}`
aliases — removed in v0.1.1, see `CLAUDE.md`'s 006 entry): the recorded golden carries a
`schemaLocation` key that the value produced today sometimes does not. Investigated at length:

- Reproduces on a **clean tree**, before this feature touches a single byte — not caused by 007.
- Affects `settings`, `network_map`, `project_mappings` and `project_settings` goldens alike — not
  scoped to the `network_map` schema this feature edits.
- **Non-deterministic across otherwise-identical runs**: the same call sequence
  (`capture_read_dict` → `capture_config_dict` → `capture_written_xml`, exactly as
  `tests.support.capture_goldens.capture()` executes it) sometimes returns the key and sometimes
  does not, even isolated to a single document in a fresh process. Bisection ruled out simple
  explanations (call order, prior-document processing, `writer.put`'s I/O) without finding a single
  deterministic trigger.
- **Not a live regression**: `tests/contract/test_byte_identity_dict.py`, which exercises the
  *current* `cuemsutils.xml.settings` module directly (not the deprecated package-root alias) and
  is part of the gating suite above, passes clean at 2222/2222.

Treated as out of scope: no task in `tasks.md` touches the deprecated `.xml_dict` property or this
capture path, and the suite this feature is actually gated on (`hatch test`, above) is green. Not
fixed here. If feature 008 or a `v0.1.1` cleanup revisits the removal of these shims, this note is
the pointer to why `tests.support.capture_goldens` cannot be trusted as a clean-tree check until
then.

## FR-026d break, demonstrated on `cuems-nodeconf` (T005)

```
cd ../cuems-nodeconf   # 0a3ce37 on feat/nodeconf-reenable
pyenv exec python -c "from cuemsnodeconf import NodeXmlBuilders"
```

```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File ".../cuemsnodeconf/NodeXmlBuilders.py", line 10, in <module>
    from cuemsutils.xml.Parsers import GenericDict, GenericParser
ImportError: cannot import name 'GenericParser' from 'cuemsutils.xml.Parsers'
```

The break is more severe than research R11's framing ("the injected handlers stop being
consulted") states for *this* checkout: `NodeXmlBuilders.py` cannot even be imported against the
current `cuemsutils`, because `GenericParser` — the symbol its four `setattr` injections target —
no longer exists in `cuemsutils.xml.Parsers` (removed by a later `cuems-utils` feature, per
`CLAUDE.md`'s 006 entry: "the frozen legacy parser tree is deleted"). Either way the conclusion
holds: `cuems-nodeconf` has no working node write path against this repository today. This is the
state T046/T079 close.

## Symbol inventory (T006, partial — extended in `migration-guide.md` for Phase 9)

`node_type` / `NodeType.` occurrence counts, `.py`/`.xsd`/`.xml`/`.md` files, at this commit:

| Repository | Occurrences |
|---|---|
| `cuems-utils/src` | 3 |
| `cuems-utils/tests` | 9 |
| `cuems-nodeconf` | 146 |
| `cuems-common` | 27 |
| `cuems-engine/src` | 5 |
| `cuems-editor/src` | 2 |
| **Total** | **192** |

Raw per-file grep dumps saved for T092's final re-verification at
`/tmp/claude-1000/-disk-Projects-StageLab-cuems-utils/6df4f127-d613-4d22-9b78-8375c91b6253/scratchpad/007-inventory/`
(session-scoped; the counts above are the durable record). Notable call sites, carried into
`migration-guide.md`:

- `cuems-engine/src/cuemsengine/core/BaseEngine.py:33,354,402,410,440` — `CONTROLLER_NETWORK_FLAG =
  "NodeType.master"` and two comparison sites (feature 008's work, FR-028).
- `cuems-editor/src/cuemseditor/CuemsWsServer.py:384,425` — the node field list including
  `node_type` (feature 008's work, FR-028).
