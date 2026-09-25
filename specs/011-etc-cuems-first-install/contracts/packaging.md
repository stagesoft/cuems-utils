<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — the `cuems-utils` package's install-time behaviour

## Manifest additions

```
/usr/share/cuems/schemas/{settings,network_map,project_mappings,project_settings,script,hardware_outputs}.xsd
/usr/share/cuems/defaults/{settings,network_map,default_mappings}.xml
/usr/share/cuems/defaults/system-defaults.toml
/usr/lib/cuems/bin/cuems-init-node                    (venv console script)
/usr/bin/cuems-init-node -> ../lib/cuems/bin/cuems-init-node
```

Nothing under `/etc` is in the manifest. `DEBIAN/conffiles` contains no `/etc/cuems` path.

## `postinst configure` (after `#DEBHELPER#`; script ends `exit 0`)

1. `install -d -m 0755 /etc/cuems /var/lib/cuems-utils/init-node`.
2. For each of the six schemas: `install -m 0644 /usr/share/cuems/schemas/X.xsd /etc/cuems/X.xsd`
   — **always**, replacing whatever is there.
3. `timeout 60s /usr/lib/cuems/bin/cuems-init-node --no-overlay --install-missing`.
4. On non-zero exit or timeout: copy each **absent** document from `/usr/share/cuems/defaults/`,
   print two `WARNING:` lines (what failed; `NOT PROVISIONED`, run `cuems-init-node`).
5. Never: modify an existing `/etc/cuems/*.xml`, read `/etc/cuems/defaults.d/`, exit non-zero.

Every path has an override for tests: `CUEMS_ETC` (default `/etc/cuems`), `CUEMS_SHARE`
(`/usr/share/cuems`), `CUEMS_STATE` (`/var/lib/cuems-utils`), `CUEMS_INIT_NODE` (the tool's
absolute path).

## `postrm`

| Argument | Action |
|---|---|
| `remove`, `upgrade`, `failed-upgrade`, `abort-*` | nothing under `/etc/cuems` or `/var/lib/cuems-utils` |
| `purge` | `rm -f` the nine `/etc/cuems` paths and the write record; `rmdir` `/var/lib/cuems-utils/init-node`, `/var/lib/cuems-utils`, `/etc/cuems` — each `--ignore-fail-on-non-empty`; never `rm -r` |

## `debian/control`

```
Build-Depends: debhelper-compat (= 13), dh-virtualenv (>= 1.2), python3, python3-setuptools, python3-pip, python3-dev
Standards-Version: 4.6.2
Breaks: cuems-common (<< 1.3.0-23~)
```

No `Replaces`. The existing `Depends` line is unchanged (Python pin out of scope).

## Build (`debian/rules`)

`override_dh_virtualenv`: `dh_virtualenv --python /usr/bin/python3 --install-suffix cuems --use-system-packages`,
then the generator through `debian/cuems-utils/usr/lib/cuems/bin/python -m cuemsutils.xml.make_defaults`,
which generates twice and refuses on any byte difference, then `install` of schemas and TOML.
No new path contains an interpreter version.

## Invariants a test asserts on the built `.deb`

- `pyvenv.cfg` `home = /usr/bin`; `bin/python` is a relative symlink.
- `DEBIAN/conffiles` has no `/etc/cuems` entry.
- `DEBIAN/postinst` contains no `dh_python2`; the tool invocation appears after the
  dh-virtualenv autoscript block and before the final `exit 0`.
- The three pristine documents carry the sentinel and validate; the six schemas are
  byte-identical to `src/cuemsutils/xml/schemas/`.
- The `.deb` bundles no path another CUEMS package ships (`/usr/lib/cuems` overlap check
  against the sibling packages' `debian/install` when the checkouts are present).
