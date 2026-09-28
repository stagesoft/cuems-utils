<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — `cuems-init-node` (public entry point)

Declared in `[project.scripts]` as `cuemsutils.tools.init_node:main`. Installed at
`/usr/lib/cuems/bin/cuems-init-node` (venv), linked from `/usr/bin/cuems-init-node`.

## Synopsis

```
cuems-init-node [--uuid U] [--mac M]
                [--overlay DIR | --no-overlay]
                [--install-missing] [--reset] [--force-new-identity]
                [--conf-dir DIR] [--state-dir DIR] [--defaults FILE]
                [--dry-run] [--verbose] [--yes]
cuems-init-node --check [--json] [--conf-dir DIR] [--avahi-service FILE]
cuems-init-node --version
```

## Modes

| Invocation | Reads | Writes | Identity rule |
|---|---|---|---|
| *(plain)* | pristine seed values + overlay + existing documents + write record | all three documents + write record | preserved if `settings.xml` carries a real uuid; minted if absent or sentinel; from `--uuid` if given |
| `--install-missing` | as above, **no overlay** unless `--overlay` given explicitly | only documents that are **absent** | from `settings.xml` if present and readable; minted only if absent |
| `--reset` | as plain | all three | preserved; every non-identity field reverts to seed + overlay |
| `--force-new-identity` | as plain | all three | a **new** uuid is minted (or `--uuid`); requires `--yes` or an interactive confirmation |
| `--check` | the four locations | **nothing** | — |
| `--dry-run` | as the selected mode | **nothing**; prints what would change | — |

`--no-overlay` and `--install-missing` are what `postinst` passes; together they read no
operator input.

## Exit codes

| Mode | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| write modes | all documents written (or nothing needed) | refused before writing (invalid overlay, bad `--uuid`, identity field in overlay, nodeconf active without `--yes`) or a write failed with the triple restored | a required input unreadable (`settings.xml` present but unparseable; pristine defaults missing) | — |
| `--check` | coherent and provisioned | at least one mirror disagrees with the source | at least one location absent or unreadable | the source carries the sentinel ("not provisioned") |

Precedence in `--check`: 3 > 2 > 1. In write modes the tool **never** exits 0 after a partial
write.

## Output

- stdout: the report — one line per document/location, path first, then a `verdict:` line.
  With `--json`, one JSON object instead.
- stderr: warnings (`WARNING: …`) and errors (`ERROR: …`); the library's own log lines only at
  `--verbose` or when `CUEMS_LOG_LEVEL` is set.
- Required wording, identical in `--check` and in `postinst`'s fallback: **`NOT PROVISIONED`**
  (sentinel), **`modified, kept`** (operator edit preserved), and the fixing command spelled
  `cuems-init-node` / `cuems-init-node --reset` / `systemctl restart cuems-nodeconf.service`
  (and, where the record is absent because the unit is masked, `systemctl unmask cuems-nodeconf.service`).

## Guarantees

- G1 Nothing under `/etc/cuems` is modified unless all three documents validated in memory.
- G2 Either all three documents are replaced or none is (three `os.replace` calls with
  in-memory restore on failure — research R6).
- G3 `--check` and `--dry-run` never write.
- G4 The sentinel token never appears in a document this tool writes to a live node — checked on
  the serialized bytes, including compound strings.
- G5 Other nodes' rows and their `adopted`/`online` flags in `network_map.xml` are never
  modified, in any mode.
- G6 Re-running with unchanged inputs changes no file (idempotent; the write record's hashes
  match and no replace happens).
- G7 Only `cuemsutils.tools.Uuid()` mints; `--uuid` is validated by the same class.
- G8 `--install-missing` never rewrites an existing document, including one carrying the
  sentinel or a `cuems-common` stub.

## Overlay refusals (before any write)

| Condition | Message names |
|---|---|
| TOML syntax error | file, line, column |
| unknown table or key | file, table, key, and the nearest declared field if one is close |
| `uuid`/`mac` in any table | file, "identity is not a default" |
| scalar of the wrong type | file, key, expected, found |
