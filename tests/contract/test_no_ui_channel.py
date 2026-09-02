"""The library gains no notification/messaging/socket channel (ITEM E, US7,
T113) — FR-047, SC-022.

The repair report is *returned*; it is 009's job to forward it to a UI. This
file asserts the negative directly, over the modules this feature adds or
edits, rather than trusting review to notice an import that was never meant
to be there.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.support.corpus import REPO_ROOT

#: Every messaging/socket-carrying module already in this codebase — a new
#: import of any of these, from any of the modules this feature touches,
#: would be the acquired channel FR-047 forbids.
MESSAGING_MODULES = {
    "pynng",
    "websockets",
    "cuemsutils.tools.HubServices",
    "cuemsutils.tools.CommunicatorServices",
    "cuemsutils.tools.SignalEngine",
    "socket",
    "asyncio",
}

#: The modules ITEM E adds or materially edits.
ITEM_E_MODULES = [
    "src/cuemsutils/errors.py",
    "src/cuemsutils/xml/versioning.py",
    "src/cuemsutils/xml/convert_documents.py",
    "src/cuemsutils/cues/CuemsScript.py",
    "src/cuemsutils/xml/validators.py",
    "src/cuemsutils/xml/documents.py",
    "src/cuemsutils/xml/mapper.py",
    "src/cuemsutils/tools/ConfigBase.py",
    "src/cuemsutils/tools/ConfigManager.py",
]


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_no_item_e_module_imports_a_messaging_channel():
    offenders = {}
    for relpath in ITEM_E_MODULES:
        path = REPO_ROOT / relpath
        imported = _imported_names(path)
        hit = imported & MESSAGING_MODULES
        if hit:
            offenders[relpath] = hit
    assert not offenders, f"messaging import(s) found: {offenders}"


def test_load_report_has_no_send_publish_or_notify_method():
    from cuemsutils.errors import LoadReport

    forbidden_prefixes = ("send", "publish", "notify", "emit", "broadcast")
    methods = [
        name
        for name in dir(LoadReport)
        if not name.startswith("_") and name.startswith(forbidden_prefixes)
    ]
    assert methods == []


def test_convert_documents_tool_module_imports_no_messaging_channel():
    """The one new user-facing surface besides the report itself (contracts
    §5) — checked directly, since it is exactly the kind of module a future
    "notify the operator" feature would be tempted to wire a channel into."""
    imported = _imported_names(REPO_ROOT / "src/cuemsutils/xml/convert_documents.py")
    assert not (imported & MESSAGING_MODULES)
