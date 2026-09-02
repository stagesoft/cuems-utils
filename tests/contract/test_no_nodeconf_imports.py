"""SC-009 — zero imports from, and zero runtime dependencies on, cuems-nodeconf.

The node-domain logic (``NodeIndex.merge``/``adopt``/etc., ITEM C) lives in
this repository now; nothing here reaches back into the daemon repository
that used to own it.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "cuemsutils"


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_no_source_file_imports_cuemsnodeconf():
    offenders = []
    for path in SRC_ROOT.rglob("*.py"):
        for name in _imported_names(path):
            if name == "cuemsnodeconf" or name.startswith("cuemsnodeconf."):
                offenders.append(f"{path.relative_to(SRC_ROOT)}: {name}")
    assert offenders == [], offenders


def test_no_pyproject_dependency_on_nodeconf_packages():
    """``systemd`` is deliberately excluded: ``cuemsutils.tools.SignalEngine``
    already depends on ``systemd-python`` for its own reason (CLAUDE.md), and
    that predates and is unrelated to ``cuems-nodeconf``'s ``import
    systemd.daemon``. Checking for it here would flag a coincidence, not a
    dependency this feature introduced.
    """
    pyproject = (SRC_ROOT.parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    for token in ("zeroconf", "netifaces", "cuemsnodeconf"):
        assert token not in pyproject.lower(), (
            f"pyproject.toml names {token!r} — a cuems-nodeconf runtime dependency"
        )
