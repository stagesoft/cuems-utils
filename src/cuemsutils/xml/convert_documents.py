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

``cuems-convert-documents --check <path>...`` (010 T037, FR-103, research R4)
answers "has this library been converted?" without converting: one line per
document with its version, a library summary, and nothing written. It is how an
operator finds which side of the rollback boundary a library is on. Since 013
the conversion is a **pair** (``cuems-reshape-devices`` first), so the full
answer is both tools' ``--check``.
"""

from __future__ import annotations

import argparse
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from .documents import backup_document, write_tree
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


def _classify(root: ET.Element) -> tuple[str | None, int, int]:
    """``(schema_name, version, current)``, the one read :func:`convert_file`
    and :func:`check_file` share — so ``--check`` cannot disagree with what a
    conversion would do. ``schema_name`` is ``None`` (and both versions ``0``)
    for a root that names no bundled schema."""
    schema_name = _schema_name_for_root(root.tag)
    if schema_name is None:
        return None, 0, 0
    return schema_name, read_version(root), CURRENT_VERSION[schema_name]


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
    schema_name, version, current = _classify(root)
    if schema_name is None:
        return ConversionOutcome.UNRECOGNISED
    if version >= current:
        return ConversionOutcome.CURRENT

    try:
        backup_document(path, time.strftime("%Y%m%dT%H%M%S"))
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


def check_file(path: Path) -> tuple[str, int | None, int | None]:
    """Classify one document **without writing anything** (T037, FR-103).

    Returns:
        tuple: ``(outcome, version, current)``. ``outcome`` is
        :data:`ConversionOutcome.CURRENT` or :data:`ConversionOutcome.CONVERTED`
        (read as *would convert*) with both versions, or
        :data:`ConversionOutcome.UNRECOGNISED` with ``None`` for both.

    Raises:
        Exactly what :func:`convert_file` raises before it acts: a document that
        is not well-formed XML propagates ``ParseError``. The two functions
        share the read, so the check cannot disagree with what a conversion
        would do.
    """
    schema_name, version, current = _classify(ET.parse(path).getroot())
    if schema_name is None:
        return ConversionOutcome.UNRECOGNISED, None, None
    if version >= current:
        return ConversionOutcome.CURRENT, version, current
    return ConversionOutcome.CONVERTED, version, current


def _check(paths: list[Path]) -> int:
    """``--check``: report every document's version and a summary; write nothing."""
    counts = {"current": 0, "needs conversion": 0, "skipped": 0}
    for path in paths:
        try:
            status, version, current = check_file(path)
        except Exception as exc:  # reported, batch continues, as for a conversion
            print(f"{path}: skipped ({exc})", file=sys.stderr)
            counts["skipped"] += 1
            continue
        if status == ConversionOutcome.UNRECOGNISED:
            print(f"{path}: skipped (root element names no bundled schema)", file=sys.stderr)
            counts["skipped"] += 1
        elif status == ConversionOutcome.CURRENT:
            print(f"{path}: already current (version {version})")
            counts["current"] += 1
        else:
            print(f"{path}: version {version}, current {current} — needs conversion")
            counts["needs conversion"] += 1
    total = len(paths)
    parts = ", ".join(f"{count} {name}" for name, count in counts.items() if count)
    print(f"{total} document{'' if total == 1 else 's'}: {parts or 'nothing to check'}")
    return 0 if counts["needs conversion"] == 0 and counts["skipped"] == 0 else 1


def main(argv: list[str] | None = None) -> int:
    """The entry point — ``cuems-convert-documents <path>...``.

    ``--check`` reports instead of converting and writes nothing.

    Returns:
        int: ``0`` if every document converted or was already current,
        ``1`` if any document was skipped (backup failure, unrecognised
        document, or an unexpected error) — never partial: every document is
        attempted regardless of an earlier one's outcome. Under ``--check``,
        ``1`` also means a document still needs conversion. ``2`` is usage.
    """
    parser = argparse.ArgumentParser(
        prog="cuems-convert-documents", usage="cuems-convert-documents [--check] <path>..."
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(sys.argv[1:] if argv is None else list(argv))
    if not args.paths:
        print("usage: cuems-convert-documents [--check] <path>...", file=sys.stderr)
        return 2
    if args.check:
        return _check([Path(arg) for arg in args.paths])

    exit_code = 0
    for arg in args.paths:
        path = Path(arg)
        try:
            status = convert_file(path)
        except Exception as exc:  # reported, batch continues (FR-042)
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
