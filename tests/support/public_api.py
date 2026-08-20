"""Helpers for the "public surface only" assertions (US1).

Several US1 tests make the same two claims — *this module reaches the library
through ``CuemsScript`` alone*, and *these are the six supported methods*.
Stating them once means a test cannot accidentally weaken the claim by
retyping it.
"""

from __future__ import annotations

import ast
from pathlib import Path

#: The six methods FR-007 names as the only supported way script data moves.
PUBLIC_SCRIPT_METHODS = (
    "load",
    "save",
    "validate",
    "from_json",
    "to_json",
    "to_wire",
)


def imported_modules(module) -> set[str]:
    """Every module name ``module``'s **source** imports, dotted paths included.

    Read from the AST rather than from ``sys.modules``: the question is what
    the *consumer* had to name, not what got loaded underneath it. A test that
    never writes ``cuemsutils.xml`` still causes it to be imported, because the
    coercion table resolves through the registry — and that is exactly the
    machinery FR-019 makes internal rather than absent.
    """
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{a.name}" for a in node.names)
    return names


def assert_no_xml_import(module) -> None:
    """``module`` names nothing from ``cuemsutils.xml`` (FR-008, SC-002)."""
    offending = sorted(
        name
        for name in imported_modules(module)
        if name == "cuemsutils.xml" or name.startswith("cuemsutils.xml.")
    )
    assert not offending, (
        f"{module.__name__} reaches into the internal xml package: {offending}"
    )
