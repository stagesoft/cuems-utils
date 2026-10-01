# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which files in the project library carry a node identity (feature 012, T008).

**Shared between the read-only check and the re-mint**, which is why it is its
own module rather than part of ``remint.py``: folding it in would make a
read-only diagnostic import the module that performs the destructive operation,
and that coupling is what FR-003 exists to keep out.

Three things it resolves, each measured rather than assumed:

* ``library_path`` comes from ``settings.xml`` (``settings.xsd:34``), read with
  **stdlib XML only** — the check must work on a node whose documents the
  library would refuse, since that is when an operator runs it (research R9).
* Both ``<library_path>/projects/*/`` and ``<library_path>/trash/projects/*/``
  are in reach. ``trash/`` mirrors ``projects/`` because ``ConfigBase``
  *creates* it that way (``ConfigBase.py:154``, research R7) — confirmed in
  code, which is stronger than one machine's layout.
* A script is identified by its **root element**, never by its filename
  (research R3). ``script_file_name`` is an editor-internal dict key and appears
  in no document this library reads, so a tool that "discovered" it would be
  reading another program's private state. Root-element identification finds a
  script under any name, including one neither repository uses.

``mappings.xml`` is **optional per project**: whether every project carries one
is the §10.7 item that research could not settle from code, and treating it as
optional is the mitigation rather than a guess (research R10).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "MAPPINGS_ROOT",
    "SCRIPT_ROOT",
    "LibraryReach",
    "Project",
    "is_backup",
    "library_path_from_settings",
    "reach_library",
    "root_local_name",
]

#: ``script.xsd``'s sole global element. A file whose root is this **is** a
#: show script, whatever it is called.
SCRIPT_ROOT = "CuemsProject"

#: ``project_mappings.xsd``'s root. The same schema backs ``/etc/cuems``'s
#: ``default_mappings.xml`` and a project's own ``mappings.xml`` — one schema,
#: two filenames, which is another reason the reach keys on the root element.
MAPPINGS_ROOT = "CuemsProjectMappings"

#: Backups, in every spelling this project makes them.
#: ``xml/convert_documents.py`` writes ``<name>.<timestamp>.bak``; the migration
#: procedure tells an operator to take ``.bak-<date>`` copies. Neither is
#: rewritten (FR-015) — and the migration guide must say that restoring one
#: reintroduces a stale identity, because nothing here can stop that.
_BACKUP_MARKERS = (".bak", ".orig", ".save")


def is_backup(path) -> bool:
    """Whether ``path`` is a backup, and therefore out of the re-mint's reach.

    Matched on the name rather than on content: a backup *is* a valid document
    — that is the point of it — so nothing inside distinguishes one.
    """
    name = Path(path).name
    if name.endswith("~"):
        return True
    return any(marker in name for marker in _BACKUP_MARKERS)


def root_local_name(path) -> str | None:
    """The local name of ``path``'s root element, or ``None`` if unreadable.

    Uses ``iterparse`` and stops at the first ``start`` event, so identifying a
    24 KB script costs the first few hundred bytes rather than a full parse.
    That matters: this runs once per candidate file across the whole library,
    and the throughput budget is stated over the library's *total* bytes.
    """
    try:
        for _event, element in ET.iterparse(str(path), events=("start",)):
            return element.tag.rsplit("}", 1)[-1]
    except (ET.ParseError, OSError):
        return None
    return None


@dataclass(frozen=True)
class Project:
    """One project directory and the documents in it that carry an identity."""

    name: str
    directory: Path
    trashed: bool
    scripts: tuple[Path, ...] = ()
    mappings: tuple[Path, ...] = ()

    @property
    def documents(self) -> tuple[Path, ...]:
        return self.scripts + self.mappings


@dataclass
class LibraryReach:
    """Everything in the library the re-mint may touch, and what it could not read.

    ``degraded`` is not an error field: a configuration-only survey is a
    **valid result** that must say so (FR-005), and a caller distinguishes it by
    this being non-empty rather than by catching something.
    """

    library_path: Path | None
    projects: tuple[Project, ...] = ()
    degraded: str = ""
    unreadable: tuple[tuple[Path, str], ...] = ()
    skipped: tuple[Path, ...] = field(default_factory=tuple)

    @property
    def documents(self) -> tuple[Path, ...]:
        out: list[Path] = []
        for project in self.projects:
            out.extend(project.documents)
        return tuple(out)

    @property
    def total_bytes(self) -> int:
        total = 0
        for path in self.documents:
            try:
                total += path.stat().st_size
            except OSError:
                pass
        return total


def library_path_from_settings(settings_path) -> tuple[str | None, str]:
    """``(library_path, why-not)`` from ``settings.xml``, stdlib XML only.

    Returns the reason as the second element rather than raising, because every
    way this can fail — absent, unreadable, or present but carrying no
    ``<library_path>`` — is a degradation the survey reports and continues past
    (FR-005), not a failure that should end it.
    """
    path = Path(settings_path)
    if not path.exists():
        return None, f"{path} is absent; surveying the configuration directory only"
    try:
        root = ET.parse(str(path)).getroot()
    except (ET.ParseError, OSError) as exc:
        return None, f"{path} is unreadable ({exc}); surveying the configuration directory only"
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == "library_path":
            value = (element.text or "").strip()
            if value:
                return value, ""
            break
    return None, f"{path} carries no library_path; surveying the configuration directory only"


def reach_library(library_path) -> LibraryReach:
    """Every project under ``library_path``, live and trashed.

    A file in a project directory that is neither a script nor a mappings
    document is **skipped and recorded**, not rewritten: §10.7 leaves open
    whether any other file embeds an output name, and root-element
    identification answers that question per file instead of assuming it either
    way (research R3).
    """
    root = Path(library_path)
    if not root.is_dir():
        return LibraryReach(None, degraded=f"{root} is not a directory; no library surveyed")

    projects: list[Project] = []
    unreadable: list[tuple[Path, str]] = []
    skipped: list[Path] = []
    for trashed, base in ((False, root / "projects"), (True, root / "trash" / "projects")):
        if not base.is_dir():
            continue
        for directory in sorted(p for p in base.iterdir() if p.is_dir()):
            scripts: list[Path] = []
            mappings: list[Path] = []
            for candidate in sorted(p for p in directory.iterdir() if p.is_file()):
                if is_backup(candidate):
                    skipped.append(candidate)
                    continue
                name = root_local_name(candidate)
                if name == SCRIPT_ROOT:
                    scripts.append(candidate)
                elif name == MAPPINGS_ROOT:
                    mappings.append(candidate)
                elif name is None and candidate.suffix == ".xml":
                    unreadable.append((candidate, "root element could not be read"))
                else:
                    skipped.append(candidate)
            projects.append(
                Project(directory.name, directory, trashed, tuple(scripts), tuple(mappings))
            )

    return LibraryReach(
        root,
        projects=tuple(projects),
        unreadable=tuple(unreadable),
        skipped=tuple(skipped),
    )


def resolve(conf_dir, library_override=None) -> LibraryReach:
    """The reach a tool actually uses: ``--library`` if given, else configured.

    ``--library`` overrides; its absence falls back to ``settings.xml``; and a
    ``settings.xml`` that cannot supply one degrades to a configuration-only
    survey **that says so** (FR-005, contract cli-check.md).
    """
    if library_override:
        return reach_library(library_override)
    value, why_not = library_path_from_settings(Path(conf_dir) / "settings.xml")
    if value is None:
        return LibraryReach(None, degraded=why_not)
    return reach_library(value)
