<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — `system-defaults.toml` and the `defaults.d` overlay

## Locations

| File | Role | Written by | Read by |
|---|---|---|---|
| `src/cuemsutils/defaults/system-defaults.toml` (package data) | the upstream seed values — **the one copy code reads** | this repository | build-time generator; `cuems-init-node` (via `importlib.resources`) |
| `/usr/share/cuems/defaults/system-defaults.toml` | operator-visible reference, `dpkg -V`-verifiable | `debian/rules` (same bytes) | operators |
| `/etc/cuems/defaults.d/*.toml` | site overlay | operator | `cuems-init-node` only |

## Grammar

```toml
# Tables: [<schema>.<TypeName>]  — schema ∈ settings | network_map | project_mappings
# Keys:   the type's scalar element names, exactly as the schema spells them
# Values: TOML scalars; the type must match the field (integer for integer-typed elements,
#         string otherwise). Booleans and dates are not used by any current field.
[settings.NodeConfType]
oscquery_ws_port = 9190

[settings.DmxPlayerType]
output_latency_ms = 35          # integer form
[settings.VideoPlayerType]
output_latency_ms = "auto"      # string form — the distinction is preserved end to end
```

## Rules

- **Completeness (seed file only)**: every required scalar of every type the three generated
  documents use has an entry; the build fails otherwise, naming `(schema, type, field)` and
  this file.
- **No stale keys (both)**: an entry naming a field no schema declares is an error naming the key.
- **No identity (both)**: `uuid` and `mac` may not appear in any table.
- **Type match (both)**: an integer-typed element rejects a string and vice versa, with the
  key, expected and found types named.
- **Precedence**: seed file < `defaults.d/*.toml` in lexical filename order (later wins) <
  operator edits kept by FR-027 (unless `--reset`).
- **Comments** are allowed and encouraged; the shipped file explains each non-obvious value
  (the D15 provenance notes move here from `descriptor.py`).

## Stability

Adding a field to a schema (per `specs/agreements/schema-evolution-convention.md`) requires an
entry here in the same commit, or the build fails — the same guarantee `descriptor.py` gave,
relocated. Removing a field requires removing its entry, or the build fails on the stale key.
