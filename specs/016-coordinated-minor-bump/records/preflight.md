# Preflight record (FR-018)

| # | Item | Command | Result | Maintainer action |
|---|---|---|---|---|
| T001 | records + evidence dirs | `mkdir`, seeded `records/*.md` | ✅ | — |
| T002 | start worktree | `git worktree add --detach .016-utils-start b83d5c2` | ✅ `0.1.0rc16`, clean | — |
| T003 | sibling venvs (pyenv 3.11.9) | `python -m venv`; `cuemsutils` editable from `US` first, then `pip install -e .` + dev packages | ✅ nodeconf, power-bridge, editor: `/home/adria/.pyenv/versions/3.11.9/bin/python3.11` 3.11.9, `cuemsutils` from `.016-utils-start` | — |
| T003 | **cuems-engine venv** | ⚠ **deviation**: `cuems-engine` **tracks `.venv/pyvenv.cfg` in git** (`a4b7294 dev: poetry environment`), so rebuilding `.venv` modified a tracked file. Restored with `git checkout -- .venv/pyvenv.cfg` (tree clean). The venv lives at **`cuems-engine/.venv-016/`**, excluded via `.git/info/exclude` | ✅ 3.11.9, `pyossia 2.0.0rc6+124.cuems.3`, `poetry 2.4.1`, `systemd-python 235`, `cuemsutils` from `US` | Finding for cuems-engine: a tracked venv file, outside this feature's scope |
| T004 | cuems-common venv | pyenv venv + `pytest` | ✅ | — |
| T005 | frontend toolchain | `npm ci`, `npm run build`, `test:ci` | ✅ build OK, **288/288** specs; tree clean (`evidence/cuems-frontend/preflight-toolchain.txt`) | — |
| T006 | bookworm build script | `tools/bookworm-build.sh`; smoke test on `cuems-common@e595e67` with `UTILS=US` | ✅ `cuems-common_1.3.0-23_all.deb` built in Debian 12 / Python 3.11.2 / dh-virtualenv 1.2.2-1.3, versions match | — |
| T007 | engine inputs gate | `cuems-engine` @ `7d0bda3`, `fc9e9af`+`729f8b6` present; `curl -sfIL` wheel URL | ✅ 200 | — |
| T008 | network | `deb.debian.org` bookworm Release, `pypi.org/simple/pip/` | ✅ 200 / 200 | — |
| T008 | tools | mmdebstrap newuidmap newgidmap equivs-build dpkg-buildpackage dpkg-parsechangelog dpkg-deb dh dh_virtualenv fakeroot uv uvx git gpg node npm google-chrome | ✅ all present (`equivs`, `debhelper` installed by the maintainer 2026-10-15) | — |
| T008 | subuid/subgid | `adria:100000:65536` both | ✅ | — |
| T008 | pyenv 3.11.9 build flags | `CONFIG_ARGS` | ✅ `--enable-optimizations --with-lto CC=gcc-12` | — |
| T008 | GPG | `commit.gpgsign=true` ×7, key `B25EB0EDCB9F13C2`, clearsign test | ✅ | — |
| T009 | verdicts fail-before | `tools/verdicts.sh` → `evidence/relation-verdicts-before.txt` | ✅ exit 1: **70 of 119 FAIL**, every row 1–25 has ≥ 1 FAIL | — |
| T011 | tag folder README | `../.xml-refactor-tag-messages/README.md` | ✅ | — |

## SC-006 baseline (T011), measured 2026-10-15

| Repo | `xml-refactor-merge-candidate^{commit}` | `origin/feat/xml-refactor` | HEAD at start |
|---|---|---|---|
| cuems-utils | none | `b83d5c2` (016 branch not on origin) | `b65a213` (016 docs commit) |
| cuems-common | `e3c9430` | `e595e67` | `e595e67` |
| cuems-nodeconf | `5be6cf0` | `82b0a69` | `82b0a69` |
| cuems-power-bridge | `399baf7` | `dd1256f` | `dd1256f` |
| cuems-engine | none | `7d0bda3` | `7d0bda3` |
| cuems-editor | none | `e5e6ac1` | `e5e6ac1` |
| cuems-frontend | `f5453a3` | `6b69b41` | `6b69b41` |

## T010 start runs and the environment fixes they needed (2026-10-15)

| Repo | Fix (local, no root) | Start result |
|---|---|---|
| cuems-common | `pip install lxml` into `.venv` (test dependency, not declared) | 101 passed, 3 skipped |
| cuems-nodeconf | `pip install zeroconf netifaces` into `.venv` (system packages on a node: `python3-zeroconf`, `python3-netifaces`) | 206 + 15 passed |
| cuems-engine | `libmtcmaster_0.0.2-0_amd64.deb` (GitHub release) and bookworm `librtmidi6_5.0.0-3_amd64.deb` **extracted** (`dpkg-deb -x`) into `/disk/Projects/StageLab/.016-native/root`; every engine run sets `LD_LIBRARY_PATH=$N/usr/lib:$N/usr/lib/x86_64-linux-gnu`. The host has trixie's `librtmidi7`, while the bookworm-built `libmtcmaster` links `librtmidi.so.6` | 885 + 32 passed |
| others | — | power-bridge 276; editor 271/3s; utils 3756/114s/2xf; frontend 288 |

`.016-native/` is removed with the worktrees at T126. T008 preflight: **all rows ✅**.
