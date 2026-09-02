"""The standalone document-conversion tool (ITEM E, US6) — contracts §5, FR-042.

``cuems-convert-documents <path>...`` — batch, offline and post-install use,
over a directory of documents, with no application running. **The only
implementation** (SC-019): this walks the same ``versioning.convert`` registry
the load path (``CuemsScript.load``, ``xml.settings.Settings.read``) consults,
rather than a second, hand-rolled rewriter.

Unlike the load path, this tool **persists** — so it carries the obligation
the load path deliberately does not (FR-041a): a timestamped backup is written
before any document is rewritten, and a backup failure is fatal **for that
document only**. The batch continues; the failure is reported, not raised.
"""

from __future__ import annotations

import shutil
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from .documents import write_tree
from .schema import SCHEMA_ROOTS, get_schema
from .versioning import CURRENT_VERSION, DOC_VERSION_ATTR, convert, read_version


def _schema_name_for_root(tag: str) -> str | None:
    """Which bundled schema a document belongs to, from its root element tag.

    Read off the root's **local name** against ``SCHEMA_ROOTS`` rather than
    trusted from the document's own ``xsi:schemaLocation`` hint — that hint is
    never resolved for validation either (``mapper.build_document``'s
    docstring), and a tool meant to *fix up* documents should not take a
    self-reported, possibly stale value as ground truth for what it is.
    """
    local = tag.rsplit("}", 1)[-1]
    for schema_name, root in SCHEMA_ROOTS.items():
        if root == local:
            return schema_name
    return None


class ConversionOutcome:
    """One document's outcome — a status string a caller can act on."""

    CURRENT = "current"
    CONVERTED = "converted"
    BACKUP_FAILED = "backup-failed"
    UNRECOGNISED = "unrecognised"


def convert_file(path: Path) -> str:
    """Convert one document **in place**, if its version precedes current.

    Idempotent (SC-018): a document already at its schema's current version
    is left untouched and reported :data:`ConversionOutcome.CURRENT`, so a
    second run over an already-converted file changes no bytes.

    Returns:
        str: one of :class:`ConversionOutcome`'s four values.

    Raises:
        Nothing on a recognised failure — every failure mode this function
        anticipates is a return value, not an exception, so :func:`main` can
        continue the batch. A document that is not well-formed XML at all
        propagates ``ParseError`` — the tool cannot report *anything*
        structured about a file it cannot parse.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    schema_name = _schema_name_for_root(root.tag)
    if schema_name is None:
        return ConversionOutcome.UNRECOGNISED

    version = read_version(tree)
    current = CURRENT_VERSION[schema_name]
    if version >= current:
        return ConversionOutcome.CURRENT

    backup = path.with_name(f"{path.name}.{time.strftime('%Y%m%dT%H%M%S')}.bak")
    try:
        shutil.copy2(path, backup)
    except OSError:
        return ConversionOutcome.BACKUP_FAILED

    convert(schema_name, tree, version, current)
    root.set(DOC_VERSION_ATTR, str(current))

    # Validate before persisting (SC-017): a conversion that produced a
    # document the schema itself rejects must not overwrite the original —
    # the backup just written is what makes this check affordable to run
    # before writing rather than a source of a second corrupt file.
    get_schema(schema_name).validate(tree)

    write_tree(tree, path)
    return ConversionOutcome.CONVERTED


def main(argv: list[str] | None = None) -> int:
    """The entry point — ``cuems-convert-documents <path>...``.

    Returns:
        int: ``0`` if every document converted or was already current,
        ``1`` if any document was skipped (backup failure, unrecognised
        document, or an unexpected error) — never partial: every document is
        attempted regardless of an earlier one's outcome.
    """
    argv = sys.argv[1:] if argv is None else list(argv)
    if not argv:
        print("usage: cuems-convert-documents <path>...", file=sys.stderr)
        return 2

    exit_code = 0
    for arg in argv:
        path = Path(arg)
        try:
            status = convert_file(path)
        except Exception as exc:  # noqa: BLE001 - reported, batch continues (FR-042)
            print(f"{path}: skipped ({exc})", file=sys.stderr)
            exit_code = 1
            continue

        if status == ConversionOutcome.BACKUP_FAILED:
            print(f"{path}: skipped (backup failed; document left unrewritten)", file=sys.stderr)
            exit_code = 1
        elif status == ConversionOutcome.UNRECOGNISED:
            print(f"{path}: skipped (root element names no bundled schema)", file=sys.stderr)
            exit_code = 1
        elif status == ConversionOutcome.CONVERTED:
            print(f"{path}: converted")
        else:
            print(f"{path}: already current")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
