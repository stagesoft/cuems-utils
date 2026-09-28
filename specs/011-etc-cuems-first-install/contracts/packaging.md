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

0. `set +e` **immediately after `#DEBHELPER#`**: dh-virtualenv's injected autoscript begins with
   `set -e`, which would otherwise turn any failing command below — including the `timeout`ed
   tool — into the non-zero exit FR-015 forbids. The script test simulates the injected stanza.
1. `install -d -m 0755 /etc/cuems /var/lib/cuems-utils/init-node`.
2. For each of the six schemas: `install -m 0644 /usr/share/cuems/schemas/X.xsd /etc/cuems/X.xsd`
   — **always**, replacing whatever is there.
3. `timeout 60s /usr/lib/cuems/bin/cuems-init-node --no-overlay --install-missing`.
4. On non-zero exit or timeout: copy each **absent** document from `/usr/share/cuems/defaults/`,
   print two `WARNING:` lines (what failed; `NOT PROVISIONED`, run `cuems-init-node`).
5. Never: modify an existing `/etc/cuems/*.xml`, read `/etc/cuems/defaults.d/`, exit non-zero.

Every path has an override for tests: `CUEMS_ETC` (default `/etc/cuems`), `CUEMS_SHARE`
(`/usr/share/cuems`), `CUEMS_STATE` (`/var/lib/cuems-utils`), `CUEMS_INIT_NODE` (the tool's
absolute path; empty ⇒ the tool step is skipped and only the copy block runs), and
`CUEMS_INIT_TIMEOUT` (default `60s`).

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
- `DEBIAN/postinst` contains no `dh_python2`; `set +e` follows the autoscript block; the tool
  invocation appears after it and before the final `exit 0`.
- No line this feature adds to `debian/rules`, `postinst`, `postrm` or `links` contains an
  interpreter version (`python3.1[0-9]`) — FR-044.
- The three pristine documents carry the sentinel and validate; the six schemas are
  byte-identical to `src/cuemsutils/xml/schemas/`.
- The `.deb` bundles no path another CUEMS package ships (`/usr/lib/cuems` overlap check
  against the sibling packages' `debian/install` when the checkouts are present).
