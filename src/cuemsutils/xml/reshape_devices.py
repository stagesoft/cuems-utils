# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""``cuems-reshape-devices`` — one installation, old device shape to new (FR-022).

Stdlib ``ElementTree`` only. The document it reads is invalid against the
current schema, which is the ordinary case. All four axes are here:
``project_mappings`` devices and root defaults (A), ``settings`` players (C),
``script`` cues and cue outputs plus ``hardware_outputs``' two flat lists (D).
``network_map`` and ``project_settings`` are not reshaped by this feature and
are named "not applicable" rather than silently skipped.
"""

from __future__ import annotations

import argparse
import copy
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
#: Axis D. ``ActionCue``, ``FadeCue`` and ``CueList`` are deliberately absent:
#: they are cue *kinds*, keep their own elements, and are not rewritten
#: (FR-050a). Each entry is ``old element name -> class value``; the new name is
#: the schema's one element.
_OLD_CUES = {"AudioCue": "audio", "VideoCue": "video", "DmxCue": "dmx"}
_OLD_CUE_OUTPUTS = {
    "AudioCueOutput": "audio",
    "VideoCueOutput": "video",
    "DmxCueOutput": "dmx",
}
_NEW_CUE = "Cue"
_NEW_CUE_OUTPUT = "CueOutput"
#: Axis D's second half: ``hardware_outputs``'s two flat lists.
_OLD_OUTPUT_GROUPS = (("video_outputs", "video"), ("audio_outputs", "audio"))
_OLD_OUTPUT_GROUP_NAMES = frozenset(name for name, _ in _OLD_OUTPUT_GROUPS)


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
    if schema_name == "script":
        for element in root.iter():
            local = _local(element.tag)
            if local in _OLD_CUES or local in _OLD_CUE_OUTPUTS:
                return "old"
        return "current"
    if schema_name == "hardware_outputs":
        if any(_local(child.tag) in _OLD_OUTPUT_GROUP_NAMES for child in list(root)):
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


def reshape_cues(root: ET.Element) -> None:
    """Axis D's cue half. A **rename in place**, which is the whole of it.

    No container, because both ``xs:choice`` groups were already
    repeated-only (research R2), and renaming in place is also what preserves
    order: a cue list interleaves cue types and that order is the running order
    of the show. Compound documents need no special case for the same reason —
    a cue output inside a cue is reached by the same walk, because every
    element is visited rather than only a document-level section.

    ``doc_version`` is not touched. No value is read, computed or dropped: the
    class comes from the element name being deleted.
    """
    for parent in root.iter():
        for child in list(parent):
            local = _local(child.tag)
            if local in _OLD_CUES:
                child.tag = _NEW_CUE
                child.set("class", _OLD_CUES[local])
            elif local in _OLD_CUE_OUTPUTS:
                child.tag = _NEW_CUE_OUTPUT
                child.set("class", _OLD_CUE_OUTPUTS[local])


def reshape_output_groups(root: ET.Element) -> None:
    """Axis D's ``hardware_outputs`` half. ``doc_version`` is not touched."""
    children = list(root)
    indexes = [
        i for i, child in enumerate(children)
        if _local(child.tag) in _OLD_OUTPUT_GROUP_NAMES
    ]
    if not indexes:
        return
    by_name = {_local(children[i].tag): children[i] for i in indexes}
    groups = ET.Element("output_groups")
    for name, output_class in _OLD_OUTPUT_GROUPS:
        old = by_name.get(name)
        if old is None:
            continue
        outputs = ET.SubElement(groups, "outputs")
        outputs.set("class", output_class)
        for grand in list(old):
            outputs.append(grand)
    first = indexes[0]
    for index in reversed(indexes):
        root.remove(children[index])
    root.insert(first, groups)


def _backup_path(path: Path, clock: str) -> Path:
    return path.with_name(f"{path.name}.{clock}.bak")


def _as_the_load_path_sees_it(schema_name: str, tree: ET.ElementTree) -> ET.ElementTree:
    """``tree`` with any registered version conversion applied, on a **copy**.

    Validating the reshaped tree as it stands is wrong for a document whose
    ``doc_version`` precedes current, and the two tools deadlock if it is not
    done here. A version-1 script carries ``<duration>00:00:00.000</duration>``
    as text; ``script`` 1→2 wraps it. So:

    * reshape first, validating the reshaped tree directly — the device shape is
      now right, but ``duration`` is still version 1, so the document "would not
      validate" and this tool declines to write it;
    * convert first — ``cuems-convert-documents`` validates after converting
      (its SC-017 check), the devices are still old-shape, and it raises.

    Neither order completes, and an installation holding version-old scripts
    (which is why feature 008 shipped the conversion registry at all) could not
    migrate. Verifying against the document *as the load path will see it*
    resolves it in one direction: reshape, then convert, in that order, which is
    what the migration guide states.

    This reads the conversion registry; it does **not** convert the file.
    Nothing is written from the copy, ``doc_version`` is not moved (FR-020), and
    the version *gate* — ``DocumentTooNewError`` — is still never this tool's to
    apply, which is what T036 asks. A document newer than this library is handed
    to the schema unconverted and fails there, naming itself.
    """
    from .versioning import CURRENT_VERSION, convert, read_version

    version = read_version(tree)
    current = CURRENT_VERSION.get(schema_name)
    if current is None or version >= current:
        return tree
    probe = ET.ElementTree(copy.deepcopy(tree.getroot()))
    convert(schema_name, probe, version, current)
    return probe


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
    elif schema_name == "script":
        reshape_cues(root)
    elif schema_name == "hardware_outputs":
        reshape_output_groups(root)
    if schema_name is None:
        return "skipped (unrecognised root)"
    try:
        get_schema(schema_name).validate(_as_the_load_path_sees_it(schema_name, tree))
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
