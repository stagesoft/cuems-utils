# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""``cuems-reshape-devices`` — one installation, old device shape to new (FR-022).

Stdlib ``ElementTree`` only. The document it reads is invalid against the
current schema, which is the ordinary case. This module ships the axis A
transformation. Settings and scripts are not applicable until their schemas
narrow; the tool names that instead of rewriting them.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from ..tools.library_reach import is_backup, library_path_from_settings
from .documents import write_tree
from .schema import SCHEMA_ROOTS, get_schema

#: Old element names being deleted. Not a vocabulary the library supports.
_OLD_DEFAULTS = (
    ("default_audio_input", "audio", "input"),
    ("default_audio_output", "audio", "output"),
    ("default_video_input", "video", "input"),
    ("default_video_output", "video", "output"),
    ("default_dmx_input", "dmx", "input"),
    ("default_dmx_output", "dmx", "output"),
)
_OLD_DEFAULT_NAMES = frozenset(name for name, _, _ in _OLD_DEFAULTS)
_OLD_DEVICE_ELEMENTS = frozenset({"audio", "video", "dmx"})
_OLD_PLAYER_ELEMENTS = frozenset({"videoplayer", "audioplayer", "dmxplayer"})


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _schema_name(tag: str) -> str | None:
    local = _local(tag)
    for schema_name, root in SCHEMA_ROOTS.items():
        if root == local:
            return schema_name
    return None


def _has_old_mappings(root: ET.Element) -> bool:
    if any(_local(child.tag) in _OLD_DEFAULT_NAMES for child in list(root)):
        return True
    for node in root.iter():
        if _local(node.tag) != "node":
            continue
        if any(_local(child.tag) in _OLD_DEVICE_ELEMENTS for child in list(node)):
            return True
    return False


def _has_new_mappings(root: ET.Element) -> bool:
    if any(_local(child.tag) == "defaults" for child in list(root)):
        return True
    for node in root.iter():
        if _local(node.tag) != "node":
            continue
        if any(_local(child.tag) == "devices" for child in list(node)):
            return True
    return False


def _node_has(root: ET.Element, names: frozenset[str]) -> bool:
    for node in root.iter():
        if _local(node.tag) != "node":
            continue
        if any(_local(child.tag) in names for child in list(node)):
            return True
    return False


def classify(schema_name: str | None, root: ET.Element) -> str:
    """``old``, ``current``, ``not-applicable``, or ``unrecognised``."""
    if schema_name is None:
        return "unrecognised"
    if schema_name == "project_mappings":
        if _has_old_mappings(root):
            return "old"
        if _has_new_mappings(root):
            return "current"
        return "not-applicable"
    if schema_name == "settings":
        if _node_has(root, _OLD_PLAYER_ELEMENTS):
            return "old"
        return "current"
    return "not-applicable"


def reshape_mappings(root: ET.Element) -> None:
    """Axis A. No value is computed or dropped. ``doc_version`` is not touched."""
    children = list(root)
    indexes = [i for i, child in enumerate(children) if _local(child.tag) in _OLD_DEFAULT_NAMES]
    if indexes:
        by_name = {_local(children[i].tag): children[i].text or "" for i in indexes}
        defaults = ET.Element("defaults")
        for name, device_class, direction in _OLD_DEFAULTS:
            if name not in by_name:
                continue
            element = ET.SubElement(defaults, "default")
            element.set("class", device_class)
            element.set("direction", direction)
            if by_name[name]:
                element.text = by_name[name]
        first = indexes[0]
        for index in reversed(indexes):
            root.remove(children[index])
        root.insert(first, defaults)

    for node in root.iter():
        if _local(node.tag) != "node":
            continue
        kids = list(node)
        found = [child for child in kids if _local(child.tag) in _OLD_DEVICE_ELEMENTS]
        if not found:
            continue
        devices = ET.Element("devices")
        first = kids.index(found[0])
        for child in found:
            device = ET.Element("device")
            device.set("class", _local(child.tag))
            for grand in list(child):
                device.append(grand)
            devices.append(device)
            node.remove(child)
        node.insert(first, devices)


def reshape_players(root: ET.Element) -> None:
    """Axis C. ``audiomixer`` stays where it is. ``doc_version`` is not touched."""
    for node in root.iter():
        if _local(node.tag) != "node":
            continue
        kids = list(node)
        found = [child for child in kids if _local(child.tag) in _OLD_PLAYER_ELEMENTS]
        if not found:
            continue
        players = ET.Element("players")
        first = kids.index(found[0])
        for child in found:
            player = ET.Element("player")
            player.set("class", _local(child.tag).removesuffix("player"))
            for grand in list(child):
                player.append(grand)
            players.append(player)
            node.remove(child)
        node.insert(first, players)


def _backup_path(path: Path, clock: str) -> Path:
    return path.with_name(f"{path.name}.{clock}.bak")


def reshape_file(path: Path, *, write: bool, dry_run: bool, clock: str) -> str:
    """One document. Returns the verdict word the line is built from.

    ``write`` is false for ``--check``. ``dry_run`` names the backup and
    writes nothing.
    """
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as exc:
        return f"skipped ({exc})"
    root = tree.getroot()
    schema_name = _schema_name(root.tag)
    shape = classify(schema_name, root)
    if shape == "unrecognised":
        return f"skipped (unrecognised root {_local(root.tag)})"
    if shape == "not-applicable":
        return "not applicable"
    if shape == "current":
        return "already current"
    if not write:
        return "old-shape"
    backup = _backup_path(path, clock)
    if dry_run:
        return f"would reshape (backup {backup})"
    try:
        shutil.copy2(path, backup)
    except OSError:
        return "skipped (backup failed; document left unrewritten)"
    if schema_name == "project_mappings":
        reshape_mappings(root)
    elif schema_name == "settings":
        reshape_players(root)
    if schema_name is None:
        return "skipped (unrecognised root)"
    try:
        get_schema(schema_name).validate(tree)
    except Exception as exc:  # noqa: BLE001 - named, and the original stays
        return f"skipped (would not validate: {exc})"
    write_tree(tree, path)
    return "reshaped"


def _xml_files(directory: Path, *, recursive: bool) -> list[Path]:
    found = directory.rglob("*.xml") if recursive else directory.glob("*.xml")
    return sorted(path for path in found if path.is_file() and not is_backup(path))


def _discover(conf: Path, library: Path | None) -> tuple[list[Path], str | None]:
    """Documents to visit, or an error string when the installation will not resolve.

    Every XML file is visited, including one whose root this library does not
    know. Recognition happens later; a stranger is named, not silently dropped.
    """
    settings = conf / "settings.xml"
    if not settings.is_file():
        return [], f"{settings} is absent"
    documents = _xml_files(conf, recursive=False)
    if library is None:
        library_path, _why = library_path_from_settings(settings)
        library = Path(library_path) if library_path else None
    if library is None:
        return documents, None
    if not library.is_dir():
        return [], f"{library} is not a directory"
    documents.extend(_xml_files(library, recursive=True))
    return documents, None


def _summary(verdicts: list[str]) -> str:
    counts: dict[str, int] = {}
    for verdict in verdicts:
        key = verdict.split(" ", 1)[0]
        counts[key] = counts.get(key, 0) + 1
    parts = [f"{count} {name}" for name, count in sorted(counts.items())]
    if not parts:
        return "nothing to do"
    if counts.get("reshaped", 0) == 0 and counts.get("old-shape", 0) == 0 and counts.get("would", 0) == 0:
        return "nothing to do (" + ", ".join(parts) + ")"
    line = ", ".join(parts)
    if counts.get("reshaped"):
        line += "; backups are <name>.<YYYYMMDDTHHMMSS>.bak beside each rewritten file"
    return line


def main(argv: list[str] | None = None) -> int:
    """Entry point. ``0`` current, ``1`` skipped or ``--check`` found old, ``2`` usage."""
    parser = argparse.ArgumentParser(prog="cuems-reshape-devices")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--conf", default=None)
    parser.add_argument("--library", default=None)
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(sys.argv[1:] if argv is None else list(argv))
    if args.check and args.dry_run:
        print("usage: --check and --dry-run are different modes", file=sys.stderr)
        return 2

    if args.paths:
        documents = [Path(path) for path in args.paths]
    else:
        conf = Path(args.conf or os.environ.get("CUEMS_CONF_PATH", "/etc/cuems"))
        library = Path(args.library) if args.library else None
        documents, error = _discover(conf, library)
        if error:
            print(error, file=sys.stderr)
            return 2

    clock = time.strftime("%Y%m%dT%H%M%S")
    write = not args.check
    verdicts: list[str] = []
    exit_code = 0
    for path in documents:
        if not path.is_file():
            print(f"{path}: skipped (not a file)", file=sys.stderr)
            verdicts.append("skipped")
            exit_code = 1
            continue
        verdict = reshape_file(path, write=write, dry_run=args.dry_run, clock=clock)
        print(f"{path}: {verdict}")
        verdicts.append(verdict)
        if verdict.startswith("skipped") or verdict == "old-shape":
            exit_code = 1
    print(_summary(verdicts))
    return exit_code
