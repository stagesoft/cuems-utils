<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Quickstart — feature 011

## Tests (library)

`hatch` is not on this host's PATH; `uvx` runs it. The project's `test` env (not `hatch test`'s
own env) carries `hypothesis`:

```bash
cd ~/cuems-utils
export PYENV_VERSION=3.11.9
uvx hatch env create test.py3.11                 # once
uvx hatch run test.py3.11:run -- -q              # full suite
uvx hatch run test.py3.11:run -- -q tests/packaging tests/contract/test_duplication_flags.py
```

## Build the package and verify it

```bash
dpkg-buildpackage -us -uc -b                       # artifacts land in ../
DEB=$(ls -t ../cuems-utils_*.deb | head -1)
dpkg-deb --fsys-tarfile "$DEB" | tar -xO ./usr/lib/cuems/pyvenv.cfg | grep '^home'   # home = /usr/bin
dpkg-deb -c "$DEB" | grep -E 'usr/share/cuems/(schemas|defaults)/|usr/bin/cuems-init-node'
dpkg-deb -e "$DEB" /tmp/ctl && grep -c '/etc/cuems' /tmp/ctl/conffiles                 # 0
```

## Lifecycle tests in an unprivileged bookworm chroot

```bash
S=~/.cache/cuems-lifecycle
mkdir -p "$S" && cd "$S"
# the package's runtime dependencies must be inside (dpkg -i needs them); ~40 s, once
mmdebstrap --mode=unshare --variant=apt --include=python3,python3-systemd,python3-daemon \
    bookworm bookworm-deps.tar
export CUEMS_CHROOT_TAR="$S/bookworm-deps.tar"
cd ~/cuems-utils && uvx hatch run test.py3.11:run -- -q -m slow tests/packaging/test_lifecycle_chroot.py
```

The test extracts a fresh copy per case (skipping the device nodes tar cannot create in the
namespace, with a plain-file `/dev/null` and a fake `sys/class/net/ethernet0` for the tool's MAC)
and runs `dpkg -i`, upgrades, `--reinstall`, remove, purge, and the `cuems-common` custody
transfer in both unpack orders, all through `unshare --map-auto --map-root-user … chroot`.
Nothing needs `sudo`. The custody case builds `../cuems-common`'s package itself and skips when
that checkout is absent.

## On a node (after `apt install cuems-utils`)

```bash
cuems-init-node --check                    # 0 coherent · 1 mismatch · 2 absent · 3 not provisioned
/usr/lib/cuems/bin/python -c 'from cuemsutils.tools.ConfigManager import ConfigManager; ConfigManager(load_all=True)'

# site overlay, then apply — identity and operator edits preserved
install -d /etc/cuems/defaults.d
cat > /etc/cuems/defaults.d/10-venue.toml <<'T'
[settings.SettingsType]
controller_url = "controller.venue.local"
T
cuems-init-node                            # reports "modified, kept" for any hand edit
cuems-init-node --reset --dry-run          # what returning to defaults would revert

# the Avahi record is derived from settings.xml by cuems-nodeconf at every start (R7):
systemctl unmask cuems-nodeconf.service      # masked on fleet hosts before the xml-refactor landing
systemctl enable --now cuems-nodeconf.service
avahi-browse -rtp _cuems_nodeconf._tcp | grep "$(sed -n 's:.*<uuid>\(.*\)</uuid>.*:\1:p' /etc/cuems/settings.xml)"
cuems-init-node --check                    # must now exit 0
```

## Operator hardware verification (manual, per node)

**The one record of these steps is `cuems-nodeconf`'s hardware-verification ledger, entry §5**
(`../cuems-nodeconf/specs/002-public-network-map-path/checklists/hardware-verification.md`,
decision D3). Do not maintain a second copy here. Acceptance, per node class: unmask, enable and
start `cuems-nodeconf`; `cuems-init-node --check` exits **0** after the unmask and again after a
reboot; a second node lists this one exactly once with the `settings.xml` uuid.

## Purge check

```bash
ls /etc/cuems                              # note the other packages' files
apt purge cuems-utils
ls /etc/cuems                              # same files minus the nine this package placed
```
