"""Would the loader accept this document? — internal (feature 017, S-3, FR-029c).

``cuems-reshape-devices`` and ``cuems-convert-documents`` validate T1 before they write. The loader
runs T1 **and** T2. So a document can be written by a tool that reports success, and then be
refused by every node that loads it. ``stop_project`` was the first value to make that happen
(S-1′).

After writing, each tool asks this module the loader's question, through the **public** entry
points (``CuemsScript.load_with_report`` for a script, ``validate_config_document`` for a
configuration document), and **reports** the answer. It never changes what was written or the
tool's exit status: both tools run in ``postinst``, which never fails (spec Q3).

Kept out of ``documents``, whose contract is that nothing in it validates semantics: T2 is
invoked from the public surface, and this module is a caller of that surface, not part of it.
"""

from __future__ import annotations

from os import PathLike

#: The configuration schemas ``validate_config_document`` accepts.
_CONFIG_SCHEMAS = frozenset({"settings", "network_map", "project_mappings", "project_settings"})


def loader_refusal(path: str | PathLike, schema_name: str | None) -> str | None:
    """``None`` if the loader would accept *path*, else the refusal's first line.

    The refusal is the loader's own message, for example
    ``[T2] action_target_required at <cue>/action_target: action_target is required``, so a
    tool can print it as is. A schema with no public loader (``hardware_outputs``) and an
    unrecognised document both answer ``None``: there is no loader whose verdict could differ
    from the T1 check the tools already ran.
    """
    from ..errors import CuemsError

    try:
        if schema_name == "script":
            from ..cues.CuemsScript import CuemsScript

            CuemsScript.load_with_report(str(path))
        elif schema_name in _CONFIG_SCHEMAS:
            from ..tools import validate_config_document

            validate_config_document(path)
        else:
            return None
    except CuemsError as exc:
        text = str(exc).strip()
        return text.splitlines()[0] if text else type(exc).__name__
    return None
