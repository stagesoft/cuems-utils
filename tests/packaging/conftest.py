# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fixtures for the packaging tests (feature 011, T003).

Three tiers, each with its own skip rule:

* **script-level** — ``run_maintainer_script`` executes ``debian/cuems-utils.<name>``
  with every path redirected into ``tmp_path`` through the overrides contract
  ``packaging.md`` defines (``CUEMS_ETC``, ``CUEMS_SHARE``, ``CUEMS_STATE``,
  ``CUEMS_INIT_NODE``, ``CUEMS_INIT_TIMEOUT``). Always runs. By default it
  **prepends a ``set -e`` stanza** standing in for dh-virtualenv's injected
  autoscript, because that autoscript begins with ``set -e`` and the custom
  block must survive it (research R21).
* **built package** — ``built_deb`` finds the newest ``../cuems-utils_*.deb`` or
  skips.
* **chroot** — ``chroot`` extracts ``$CUEMS_CHROOT_TAR`` into ``tmp_path`` and
  runs commands as fake root through ``unshare --map-auto --map-root-user``
  (research R9), or skips. ``sibling_deb`` builds a sibling checkout's package
  on demand for the custody-transfer and whole-stack cases, or skips.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEBIAN = REPO_ROOT / "debian"
STUBS = Path(__file__).resolve().parent / "stubs"

#: What dh-virtualenv's autoscript starts with; the maintainer scripts run under it.
AUTOSCRIPT_STANZA = "# dh-virtualenv postinst autoscript (simulated by tests)\nset -e\n"


def _script(name: str) -> Path:
    path = DEBIAN / f"cuems-utils.{name}"
    if not path.exists():
        # A missing maintainer script is a failing test, not a skipped one:
        # the script-level tests are written before the scripts exist.
        pytest.fail(f"{path.relative_to(REPO_ROOT)} does not exist yet")
    return path


@dataclass
class ScriptDirs:
    etc: Path
    share: Path
    state: Path

    def env(self, init_node: str | None = None, timeout: str = "60s") -> dict:
        return {
            "CUEMS_ETC": str(self.etc),
            "CUEMS_SHARE": str(self.share),
            "CUEMS_STATE": str(self.state),
            "CUEMS_INIT_NODE": "" if init_node is None else init_node,
            "CUEMS_INIT_TIMEOUT": timeout,
        }


@pytest.fixture
def dirs(tmp_path: Path) -> ScriptDirs:
    """``etc``, ``share`` and ``state`` under ``tmp_path``; ``share`` pre-seeded
    with the bundled schemas so the schema block has something to install."""
    share = tmp_path / "share"
    (share / "schemas").mkdir(parents=True)
    (share / "defaults").mkdir()
    for xsd in (REPO_ROOT / "src/cuemsutils/xml/schemas").glob("*.xsd"):
        shutil.copy2(xsd, share / "schemas" / xsd.name)
    return ScriptDirs(etc=tmp_path / "etc", share=share, state=tmp_path / "state")


@pytest.fixture
def run_maintainer_script(tmp_path: Path):
    """Run ``debian/cuems-utils.<name> <arg>`` with the overrides in ``env``.

    Returns the ``CompletedProcess``. With ``simulate_autoscript`` (default) the
    script text is prefixed with :data:`AUTOSCRIPT_STANZA` after its shebang,
    exactly where ``#DEBHELPER#`` sits in the source; the ``#DEBHELPER#``
    token itself is replaced by that stanza.
    """

    def _run(name: str, arg: str, env: dict, simulate_autoscript: bool = True,
             extra_args: tuple[str, ...] = ()) -> subprocess.CompletedProcess:
        source = _script(name).read_text(encoding="utf-8")
        if simulate_autoscript:
            assert "#DEBHELPER#" in source, f"{name}: no #DEBHELPER# token to inject at"
            source = source.replace("#DEBHELPER#", AUTOSCRIPT_STANZA, 1)
        else:
            source = source.replace("#DEBHELPER#", "", 1)
        runnable = tmp_path / f"run-{name}.sh"
        runnable.write_text(source, encoding="utf-8")
        full_env = {**os.environ, **env}
        return subprocess.run(
            ["sh", str(runnable), arg, *extra_args],
            env=full_env, capture_output=True, text=True, timeout=120,
        )

    return _run


@pytest.fixture
def stub_init_node() -> Path:
    """The executable stub (T004). Honours ``CUEMS_STUB_EXIT`` and
    ``CUEMS_STUB_SLEEP`` and writes its argv to ``$CUEMS_STUB_MARKER``."""
    stub = STUBS / "cuems-init-node"
    assert os.access(stub, os.X_OK), f"{stub} is not executable"
    return stub


# -- built package --------------------------------------------------------------


@pytest.fixture(scope="session")
def built_deb() -> Path:
    debs = sorted((REPO_ROOT.parent).glob("cuems-utils_*.deb"), key=lambda p: p.stat().st_mtime)
    if not debs:
        pytest.skip("no built cuems-utils .deb beside the checkout (run dpkg-buildpackage -us -uc -b)")
    return debs[-1]


def deb_paths(deb: Path) -> list[str]:
    out = subprocess.run(["dpkg-deb", "-c", str(deb)], check=True, capture_output=True, text=True).stdout
    return [line.split()[-1].lstrip(".") for line in out.splitlines() if line.strip()]


def deb_file(deb: Path, member: str) -> bytes:
    """One file's bytes out of the ``.deb``'s data tarball (``member`` like ``usr/share/…``)."""
    tar = subprocess.run(["dpkg-deb", "--fsys-tarfile", str(deb)], check=True, capture_output=True).stdout
    return subprocess.run(["tar", "-xO", f"./{member}"], input=tar, check=True, capture_output=True).stdout


def deb_control_file(deb: Path, name: str) -> str:
    out = subprocess.run(["dpkg-deb", "-I", str(deb), name], capture_output=True, text=True)
    if out.returncode != 0:
        return ""
    return out.stdout


# -- chroot ---------------------------------------------------------------------


@dataclass
class Chroot:
    root: Path

    def run(self, argv: list[str], check: bool = True, timeout: int = 600) -> subprocess.CompletedProcess:
        cmd = [
            "unshare", "--map-auto", "--map-root-user", "--",
            "sh", "-c",
            'export PATH=/usr/sbin:/usr/bin:/sbin:/bin CUEMS_LOG_LEVEL=CRITICAL; exec chroot "$0" "$@"',
            str(self.root), *argv,
        ]
        return subprocess.run(cmd, check=check, capture_output=True, text=True, timeout=timeout)

    def copy_in(self, src: Path, dest: str) -> None:
        target = self.root / dest.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)

    def read(self, path: str) -> bytes:
        return (self.root / path.lstrip("/")).read_bytes()

    def exists(self, path: str) -> bool:
        return (self.root / path.lstrip("/")).exists()

    def dpkg_install(self, deb: Path, *flags: str) -> subprocess.CompletedProcess:
        """``dpkg -i`` inside the chroot. A sibling package whose dependency tree
        is not under test is installed with ``--force-depends``."""
        self.copy_in(deb, f"/tmp/{deb.name}")
        return self.run(["dpkg", "-i", *flags, f"/tmp/{deb.name}"], check=False)


def _prepare_root(tar: str, root: Path) -> Chroot:
    # Measured 2026-09-28: the mmdebstrap tarball carries device nodes that tar
    # cannot mknod without CAP_MKNOD, and a bind mount of the host's /dev is
    # refused in this user namespace. dpkg and the maintainer scripts only need
    # a /dev/null sink, which a regular file provides; uuid4 uses getrandom(2),
    # not /dev/urandom. There is no sysfs either, so a fake ethernet0 gives the
    # tool its MAC (FR-025a) — a different one per root.
    import hashlib

    root.mkdir(parents=True, exist_ok=True)
    mac = "02" + hashlib.sha256(str(root).encode()).hexdigest()[2:12]
    prepare = (
        'tar -xf "$1" -C "$2" --exclude="./dev/*" && mkdir -p "$2/dev" "$2/proc" '
        '"$2/sys/class/net/ethernet0" && : > "$2/dev/null" && chmod 666 "$2/dev/null" '
        '&& printf "%s\n" "$3" > "$2/sys/class/net/ethernet0/address"'
    )
    result = subprocess.run(
        ["unshare", "--map-auto", "--map-root-user", "--", "sh", "-c", prepare, "sh", tar, str(root),
         ":".join(mac[i:i + 2] for i in range(0, 12, 2))],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"chroot extraction failed: {result.stderr[-800:]}"
    return Chroot(root=root)


@pytest.fixture
def make_chroot(tmp_path: Path):
    """A factory: a fresh bookworm root per call (``chroot`` is ``make_chroot("rootfs")``)."""
    tar = os.environ.get("CUEMS_CHROOT_TAR")
    if not tar or not Path(tar).exists():
        pytest.skip("CUEMS_CHROOT_TAR is unset or missing (see quickstart.md)")
    if shutil.which("unshare") is None:
        pytest.skip("unshare(1) not available")

    def _make(name: str = "rootfs") -> Chroot:
        return _prepare_root(tar, tmp_path / name)

    return _make


@pytest.fixture
def chroot(make_chroot) -> Chroot:
    return make_chroot("rootfs")


@pytest.fixture(scope="session")
def sibling_deb():
    """Build ``../<name>``'s package once per session, or skip with the reason."""
    built: dict[str, Path] = {}

    def _build(name: str) -> Path:
        if name in built:
            return built[name]
        checkout = REPO_ROOT.parent / name
        if not (checkout / "debian" / "control").exists():
            pytest.skip(f"sibling checkout ../{name} with debian/ not present")
        if shutil.which("dpkg-buildpackage") is None:
            pytest.skip("dpkg-buildpackage not available")
        subprocess.run(["dpkg-buildpackage", "-us", "-uc", "-b"], cwd=checkout, check=True,
                       capture_output=True, timeout=900)
        debs = sorted((REPO_ROOT.parent).glob(f"{name}_*.deb"), key=lambda p: p.stat().st_mtime)
        assert debs, f"no {name}_*.deb produced"
        built[name] = debs[-1]
        return debs[-1]

    return _build
