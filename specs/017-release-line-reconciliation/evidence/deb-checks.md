# The 0.1.1 `.deb`, built in a bookworm chroot (T050, FR-035, SC-007)

Built with 016's tool, through its real interface: `UTILS=<clean worktree at 009fb94>`,
`OUT=evidence/bookworm-build.txt`, `WORK=<scratchpad>/buildwork`. That is an unprivileged
`mmdebstrap --mode=unshare` bookworm chroot, thrown away afterwards. Full log:
`evidence/bookworm-build.txt` (Debian 12, `/usr/bin/python3` → Python 3.11.2, dh-virtualenv
1.2.2-1.3, debhelper 13.11.4; pass 1 and build OK; verdict OK).

`cuems-utils_0.1.1_amd64.deb`, sha256 `8e354473e932b70f6e98edbd68f0dd7083bbf6668f7062c8625ed3ea4d29a765`.

## FR-035 checks

```
Version:  0.1.1
Replaces: cuems-engine (<< 0.1.0rc6-2~)
Breaks:   cuems-common (<< 1.3.1~)
pyvenv:   home = /usr/bin
bin/python: ./usr/lib/cuems/bin/python -> ../../../bin/python3
CACHEDIR.TAG entries: 0
cffi-gen-src: ./usr/lib/cuems/bin/cffi-gen-src
cuems-init-node / convert / reshape entry points: 4
schemas under /usr/share/cuems/schemas: 6
dpkg-parsechangelog top: 0.1.1
```

All four FR-035 checks hold:
- `Version: 0.1.1`;
- `home = /usr/bin` and a **relative** `bin/python` link;
- **no `CACHEDIR.TAG`**;
- `cffi-gen-src` **present**, as expected: this package owns it, which is why it `Replaces:` the
  old engine.

## Tests against this `.deb`

For each run the `.deb` was copied beside the checkout, where `tests/packaging/conftest.py`'s
`built_deb` looks for it, and removed afterwards. `CUEMS_CHROOT_TAR=/home/adria/.cache/cuems-lifecycle/bookworm-deps.tar`.

**`tests/packaging/test_built_package.py`: 7 passed**, including 017's `test_no_cachedir_tag_ships`
and `test_cffi_gen_src_ships`.

**Lifecycle (`test_lifecycle_chroot`, `test_postinst`, `test_postinst_reshape`, `test_postrm`):
20 passed, 1 failed.** The failure, `test_lifecycle_chroot.py::test_fresh_install_loads_and_is_unique`,
is **pre-existing**: CLAUDE.md records "011's `test_fresh_install_loads_and_is_unique` fails on its
own since 012 (the XSDs carry the sentinel)". Its message confirms it:
`sentinel token still present: /etc/cuems/{project_mappings,network_map,settings}.xsd: <xs:enumeration value="00000000-…" />`.
The test's grep matches the schemas' own legitimate sentinel enumeration. 017 changes none of this.
