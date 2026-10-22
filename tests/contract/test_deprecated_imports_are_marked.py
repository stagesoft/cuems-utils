# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""A test that imports the deprecated XML surface says so (feature 017, FR-029b, SC-006).

``XmlReaderWriter``, ``Parsers`` and ``XmlBuilder`` are deprecated in ``0.1.1`` and deleted in
``v0.1.2``. A test module that imports any of them on purpose carries
``pytestmark = pytest.mark.expects_deprecation``, so that:
- ``v0.1.2``'s removal (``specs/planning/deprecated-surface-removal-v0-1-2.md``, R10) can list
  every module that must be deleted or ported with it;
- an import that slips in unmarked, for example an absorbed release-line test that was not
  ported (017 D4), fails here instead of breaking on the day the surface is deleted.

The check reads the source (AST), so it needs no collection, and it fails naming the module and
the import.
"""
import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1]
DEPRECATED = ("cuemsutils.xml.XmlReaderWriter", "cuemsutils.xml.Parsers", "cuemsutils.xml.XmlBuilder")
DEPRECATED_NAMES = {"XmlReaderWriter", "Parsers", "XmlBuilder", "CuemsParser"}


def _deprecated_imports(tree: ast.Module) -> list[str]:
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names = {a.name for a in node.names}
            if node.module.startswith(DEPRECATED) or (
                node.module == "cuemsutils.xml" and names & DEPRECATED_NAMES
            ):
                found.append(f"from {node.module} import {', '.join(sorted(names))}")
        elif isinstance(node, ast.Import):
            found += [f"import {a.name}" for a in node.names if a.name.startswith(DEPRECATED)]
    return found


def _is_marked(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets
        ):
            return "expects_deprecation" in ast.unparse(node.value)
    return False


def test_every_module_importing_the_deprecated_surface_is_marked():
    unmarked = []
    for path in sorted(TESTS.rglob("*.py")):
        tree = ast.parse(path.read_text())
        imports = _deprecated_imports(tree)
        if imports and not _is_marked(tree):
            unmarked.append(f"{path.relative_to(TESTS.parent)}: {'; '.join(imports)}")
    assert not unmarked, (
        "these test modules import the deprecated XML surface without "
        "`pytestmark = pytest.mark.expects_deprecation` (port them to the public API, "
        "or mark them and list them in deprecated-surface-removal-v0-1-2.md R10):\n  "
        + "\n  ".join(unmarked)
    )


def test_the_check_finds_the_marked_modules():
    """Guard against a check that passes because it finds nothing."""
    marked = [
        p for p in TESTS.rglob("*.py")
        if _deprecated_imports(ast.parse(p.read_text()))
    ]
    assert len(marked) >= 14, [str(p) for p in marked]
