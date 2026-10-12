# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""``cuems-init-node --check`` (feature 011, US6; feature 012, US1).

Reads the four places a node's identity lands — ``settings.xml`` (the source),
``network_map.xml``, ``default_mappings.xml`` and the live Avahi service file
— **and, since feature 012, the project library** — and reports each by path.
Four exit classes, precedence **3 > 2 > 1**:

* **0** coherent, provisioned, and every identity converged;
* **1** at least one mirror disagrees with the source **or** at least one
  identity is not converged (feature 012 widened this one);
* **2** at least one location absent or unreadable;
* **3** the source carries the sentinel — ``NOT PROVISIONED``. A
  never-provisioned node is coherent but actionable, so it does not share the
  "done" code; an absent Avahi record is *expected* there (nodeconf refuses
  to announce a sentinel) and is reported as such rather than as class 2.

Reads only stdlib XML on purpose: the checker must work on a node whose
documents the library would refuse, since that is when an operator runs it.
It never writes. Feature 012 turns that from a technique into a requirement
(FR-001a, FR-003): after the narrowing, *every* document this tool is run on to
diagnose a migration is one the schema refuses.

## The vocabulary is extended, not replaced (Principle III)

The four shipped verdicts — ``coherent``, ``mismatch``, ``absent or
unreadable`` and ``NOT PROVISIONED`` — keep their exact spellings and their
exact meanings. One value joins them: ``migration-needed``, for the condition
that used to report ``coherent`` because nothing classified an identity's
*shape*. Where both a mirror disagreement and a non-converged identity are
present the verdict is ``mismatch``, the shipped one, so a consumer keying on
it sees it for the same condition as before; the migration is named in ``fix``
and enumerated in ``occurrences`` rather than hidden.

``Report`` grows fields and loses none: ``occurrences``, ``counts``,
``scanned``, ``library`` and ``notes`` are additions (data-model §3), and every
field a caller reads today is still there and still means the same thing.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import ids, library_reach

__all__ = [
    "SENTINEL",
    "NOT_PROVISIONED",
    "FIX_PLAIN",
    "FIX_RESET",
    "FIX_NODECONF",
    "FIX_REMINT",
    "FIX_UNMASK",
    "Location",
    "Occurrence",
    "Report",
    "check",
    "render",
    "render_json",
]

#: The not-provisioned placeholder **as a value** — the nil uuid a node carries
#: as its identity, which answers *"is this node provisioned?"*. Public surface
#: (FR-031), re-exported from :mod:`cuemsutils.tools`.
#:
#: Bound to ``ids.NOT_PROVISIONED_UUID`` rather than spelled again, so the two
#: cannot drift. The name stays here, where it already was (assumption 7) —
#: nothing a consumer imports has moved.
#:
#: Not to be confused with :data:`NOT_PROVISIONED`, the human-readable status
#: string below, which answers a different question: *"what should this line of
#: output say?"*. Both are published; each says which question it answers.
SENTINEL = ids.NOT_PROVISIONED_UUID

UUID_TOKEN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
DEFAULT_AVAHI_SERVICE = "/etc/avahi/services/cuems.service"

#: The human-readable status string, and the shipped verdict for exit class 3.
#: See :data:`SENTINEL` for the distinction.
NOT_PROVISIONED = "NOT PROVISIONED"
FIX_PLAIN = "cuems-init-node"
FIX_RESET = "cuems-init-node --reset"
FIX_NODECONF = "systemctl restart cuems-nodeconf.service"
FIX_REMINT = "cuems-init-node --remint"
FIX_UNMASK = "systemctl unmask cuems-nodeconf.service && systemctl enable --now cuems-nodeconf.service"

OK, MISMATCH, ABSENT, UNREADABLE, EXPECTED_ABSENT = "ok", "MISMATCH", "ABSENT", "UNREADABLE", "absent (expected)"

#: The one verdict feature 012 adds. Every other verdict this tool reports is
#: the one it reported before, spelled exactly as before.
MIGRATION_NEEDED = "migration-needed"

#: The three configuration documents that carry a node identity, and are
#: therefore surveyed for occurrences as well as checked for coherence.
CONFIG_DOCUMENTS = ("settings.xml", "network_map.xml", "default_mappings.xml")


@dataclass
class Location:
    """One of the four places a node's identity lands, and whether it agrees.

    ``classification`` is feature 012's addition: the shape class of whatever
    identity this location carries (data-model §1.3). The four shipped fields
    are unchanged in name and meaning.
    """

    path: str
    status: str
    detail: str = ""
    values: list[str] = field(default_factory=list)
    classification: str = ""


@dataclass
class Occurrence:
    """One identity token, where it was found (data-model §3).

    ``embedded`` is the field worth having: it is the distinction that makes a
    structural rewrite wrong (design §10.2), and an operator reading the report
    should be able to see how much of the work is invisible to a naive tool.
    """

    #: Absolute path of the document it was found in.
    path: str

    #: Where within the document — the enclosing element's local name, so a
    #: compound output name reads as ``output_name``.
    location: str

    #: The identity exactly as found, case included.
    value: str

    #: One of :data:`cuemsutils.tools.ids.CLASSES`.
    classification: str

    #: ``True`` when found inside a compound string rather than as an element's
    #: whole value.
    embedded: bool

    #: The element's full text when ``embedded`` — the compound form an
    #: operator will recognise. Equal to ``value`` otherwise.
    context: str = ""


@dataclass
class Report:
    """What the check produces. **Data only, never ``None`` in place of an
    empty report** — the convention feature 008 set for ``LoadReport``.

    The five shipped fields come first and are unchanged. The five below them
    are feature 012's, and every one of them is additive: a caller reading this
    report today reads the same values from the same names afterwards.
    """

    source: dict
    locations: list[Location]
    verdict: str
    exit_code: int
    fix: str

    #: Every occurrence the survey reports. The configuration documents
    #: contribute all of theirs; the library contributes the ones that are not
    #: converged plus the ones matching a known node identity — a converged cue
    #: id in a show script is neither this feature's business nor an operator's,
    #: and reporting thousands of them would bury the ones that matter.
    #: Nothing is *dropped* by that filter: :attr:`counts` and :attr:`scanned`
    #: account for every token seen, which is what makes SC-005's "100%
    #: classified" a checkable claim rather than a hopeful one.
    occurrences: list[Occurrence] = field(default_factory=list)

    #: Per-class totals over **everything** scanned.
    counts: dict[str, int] = field(default_factory=dict)

    #: How many tokens were scanned in total. Equals ``sum(counts.values())``.
    scanned: int = 0

    #: The library actually surveyed, or ``""`` when the survey degraded to the
    #: configuration directory alone (FR-005).
    library: str = ""

    #: Everything the survey could not do, in the words an operator needs. A
    #: degradation is a *reported condition*, not an error: a survey that
    #: silently covered less would be worse than one that failed.
    notes: list[str] = field(default_factory=list)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_texts(root: ET.Element, name: str) -> list[str]:
    return [(el.text or "").strip() for el in root.iter() if _local(el.tag) == name]


def _source(conf: Path) -> tuple[dict, Location]:
    path = conf / "settings.xml"
    if not path.exists():
        return {}, Location(str(path), ABSENT, "settings.xml is the identity source; run cuems-init-node")
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        return {}, Location(str(path), UNREADABLE, str(exc))
    node = next((el for el in root.iter() if _local(el.tag) == "node"), None)
    uuid = (node.findtext("uuid") if node is not None else None) or ""
    mac = (node.findtext("mac") if node is not None else None) or ""
    if not uuid:
        return {}, Location(str(path), UNREADABLE, "no Settings/node/uuid element")
    if uuid == SENTINEL:
        return {"uuid": uuid, "mac": mac}, Location(str(path), NOT_PROVISIONED, f"source uuid={uuid} (sentinel)")
    return {"uuid": uuid, "mac": mac}, Location(str(path), OK, f"source uuid={uuid} mac={mac}")


def _network_map(conf: Path, uuid: str) -> Location:
    path = conf / "network_map.xml"
    if not path.exists():
        return Location(str(path), ABSENT)
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        return Location(str(path), UNREADABLE, str(exc))
    rows = [el for el in root.iter() if _local(el.tag) == "node"]
    mine = [r for r in rows if (r.findtext("uuid") or "").strip() == uuid]
    if not mine:
        return Location(str(path), MISMATCH, f"self-entry missing ({len(rows)} row(s), none with uuid={uuid})")
    role = (mine[0].findtext("node_role") or "").strip()
    return Location(str(path), OK, f"self-entry present, role={role or '?'}")


def _default_mappings(conf: Path, uuid: str) -> Location:
    path = conf / "default_mappings.xml"
    if not path.exists():
        return Location(str(path), ABSENT)
    try:
        raw = _text(path)
        root = ET.fromstring(raw)
    except (ET.ParseError, OSError) as exc:
        return Location(str(path), UNREADABLE, str(exc))
    nodes = [el for el in root.iter() if _local(el.tag) == "node"]
    present = any((n.findtext("uuid") or "").strip() == uuid for n in nodes)
    has_sentinel = SENTINEL in raw and uuid != SENTINEL
    if not present:
        return Location(str(path), MISMATCH, f"no node entry with uuid={uuid}")
    if has_sentinel:
        return Location(str(path), MISMATCH, "sentinel token still present (a compound string was not specialised)")
    return Location(str(path), OK, "node entry present, no sentinel token")


def _avahi(avahi: Path, uuid: str, source_is_sentinel: bool) -> Location:
    if not avahi.exists():
        if source_is_sentinel:
            return Location(str(avahi), EXPECTED_ABSENT, "an unprovisioned node announces nothing")
        return Location(str(avahi), ABSENT, "no live record — is cuems-nodeconf unmasked and running?")
    try:
        root = ET.parse(avahi).getroot()
    except (ET.ParseError, OSError) as exc:
        return Location(str(avahi), UNREADABLE, str(exc))
    values = [t[len("uuid="):] for t in _find_texts(root, "txt-record") if t.startswith("uuid=")]
    if not values:
        return Location(str(avahi), MISMATCH, "no uuid= txt-record", values)
    if len(set(values)) > 1:
        return Location(str(avahi), MISMATCH, f"records disagree with each other: {sorted(set(values))}", values)
    if values[0] != uuid:
        return Location(str(avahi), MISMATCH, f"record uuid={values[0]} but source uuid={uuid}", values)
    return Location(str(avahi), OK, f"{len(values)} records agree", values)


# -- the shape survey (feature 012, T015-T018) ------------------------------------------


def _known_identities(conf: Path) -> set[str]:
    """Every identity the configuration names, for the library filter.

    Read leniently: an unreadable document contributes nothing and stops
    nothing, because the survey it feeds is the one an operator runs *because*
    something is already wrong.
    """
    known: set[str] = set()
    for name in CONFIG_DOCUMENTS:
        path = conf / name
        if not path.is_file():
            continue
        for occurrence in ids.scan_file(path):
            if not occurrence.embedded:
                known.add(occurrence.value)
    return known


def _survey(conf: Path, library: str | Path | None) -> tuple[list[Occurrence], dict[str, int], int, str, list[str]]:
    """``(occurrences, counts, scanned, library, notes)``.

    Every token is classified; :attr:`Report.counts` accounts for all of them.
    The occurrence *list* carries every configuration-document token and, from
    the library, the ones that are not converged or that match a known node
    identity — see :class:`Report`.
    """
    occurrences: list[Occurrence] = []
    counts: dict[str, int] = {}
    scanned = 0
    notes: list[str] = []

    def record(path, found, keep):
        nonlocal scanned
        for occurrence in found:
            classification = occurrence.classification
            counts[classification] = counts.get(classification, 0) + 1
            scanned += 1
            if keep(occurrence):
                occurrences.append(Occurrence(
                    path=str(path),
                    location=occurrence.element or "<no enclosing element>",
                    value=occurrence.value,
                    classification=classification,
                    embedded=occurrence.embedded,
                    context=occurrence.context,
                ))

    for name in CONFIG_DOCUMENTS:
        path = conf / name
        if not path.is_file():
            continue
        try:
            record(path, ids.scan_file(path), lambda _o: True)
        except OSError as exc:
            notes.append(f"{path}: unreadable ({exc}); not surveyed")

    reach = library_reach.resolve(conf, library)
    if reach.degraded:
        notes.append(reach.degraded)
        return occurrences, counts, scanned, "", notes

    known = _known_identities(conf)

    def keep(occurrence):
        return occurrence.classification != ids.CONVERGED or occurrence.value in known

    for path in reach.documents:
        try:
            record(path, ids.scan_file(path), keep)
        except OSError as exc:
            notes.append(f"{path}: unreadable ({exc}); not surveyed")
    for path, why in reach.unreadable:
        notes.append(f"{path}: {why}; named and skipped, the survey continued")

    return occurrences, counts, scanned, str(reach.library_path or ""), notes


def check(conf_dir: Path, avahi_service: Path | None = None,
          library: str | Path | None = None) -> Report:
    """The four identity locations, the shape of every identity, and the library.

    Args:
        conf_dir: the configuration directory.
        avahi_service: the live Avahi service file; the packaged default when
            omitted.
        library: overrides the configured library path (``--library``). Its
            absence reads ``library_path`` from ``settings.xml``, and a
            ``settings.xml`` that cannot supply one degrades to a
            configuration-only survey **that says so** (FR-005, research R9).

    Returns:
        Report: never ``None``, and never a partial object — a degraded survey
        is a complete report of a smaller thing, with the smallness named in
        :attr:`Report.notes`.
    """
    conf = Path(conf_dir)
    avahi = Path(avahi_service) if avahi_service else Path(DEFAULT_AVAHI_SERVICE)
    source, source_loc = _source(conf)
    uuid = source.get("uuid", "")
    sentinel = uuid == SENTINEL
    source_loc.classification = ids.classify(uuid) if uuid else ids.UNRECOGNISED
    locations = [source_loc]
    if uuid:
        for locate in (_network_map, _default_mappings):
            location = locate(conf, uuid)
            location.classification = source_loc.classification
            locations.append(location)
        avahi_loc = _avahi(avahi, uuid, sentinel)
        avahi_loc.classification = (
            ids.classify(avahi_loc.values[0]) if avahi_loc.values else ""
        )
        locations.append(avahi_loc)

    occurrences, counts, scanned, library_used, notes = _survey(conf, library)
    migration_needed = counts.get(ids.NOT_CONVERGED, 0) > 0

    def report(verdict, code, fix):
        # The migration is named in ``fix`` whenever it is needed, including
        # where a higher-precedence condition owns the verdict — an operator
        # must not have to run the check twice to learn the second thing.
        if migration_needed and FIX_REMINT not in fix:
            fix = f"{fix}; then: {FIX_REMINT}" if fix else FIX_REMINT
        return Report(source, locations, verdict, code, fix,
                      occurrences=occurrences, counts=counts, scanned=scanned,
                      library=library_used, notes=notes)

    statuses = {loc.status for loc in locations}
    if sentinel:
        return report(NOT_PROVISIONED, 3, FIX_PLAIN)
    if not uuid or ABSENT in statuses or UNREADABLE in statuses:
        others_absent = any(loc.status in (ABSENT, UNREADABLE) and loc.path != str(avahi) for loc in locations)
        fix = FIX_PLAIN if others_absent or not uuid else FIX_UNMASK
        return report("absent or unreadable", 2, fix)
    if MISMATCH in statuses:
        only_avahi = all(loc.status != MISMATCH or loc.path == str(avahi) for loc in locations)
        return report("mismatch", 1, FIX_NODECONF if only_avahi else FIX_PLAIN)
    if migration_needed:
        return report(MIGRATION_NEEDED, 1, FIX_REMINT)
    return report("coherent", 0, "")


def render(report: Report) -> str:
    lines = []
    for loc in report.locations:
        detail = f" ({loc.detail})" if loc.detail and loc.status not in (OK, NOT_PROVISIONED) else ""
        if loc.status == OK and loc.detail:
            detail = f" ({loc.detail})" if not loc.detail.startswith("source uuid=") else f": {loc.detail}"
            lines.append(f"{loc.path}{detail}" if detail.startswith(":") else f"{loc.path}: ok{detail}")
            continue
        if loc.status == NOT_PROVISIONED:
            lines.append(f"{loc.path}: {NOT_PROVISIONED} — {loc.detail}")
            continue
        lines.append(f"{loc.path}: {loc.status}{detail}")
    lines.extend(_render_survey(report))
    lines.append(f"verdict: {report.verdict} (exit {report.exit_code})" + (f" — run: {report.fix}" if report.fix else ""))
    return "\n".join(lines)


#: How many non-converged occurrences the human rendering lists in full before
#: it stops and gives a count. A 200-project library can hold thousands; a
#: report an operator will not read is a report that does not exist.
RENDER_OCCURRENCE_LIMIT = 20


def _render_survey(report: Report) -> list[str]:
    lines = [f"library: {report.library or 'not surveyed (configuration only)'}"]
    lines.extend(f"note: {note}" for note in report.notes)
    if not report.scanned:
        return lines
    summary = ", ".join(
        f"{count} {name}" for name, count in sorted(report.counts.items())
    )
    embedded = sum(1 for o in report.occurrences if o.embedded)
    lines.append(f"{report.scanned} identity occurrence(s) scanned: {summary}")
    lines.append(
        f"{embedded} of the {len(report.occurrences)} reported are embedded in a "
        "compound string, where a structural rewrite would not reach them"
    )
    actionable = [o for o in report.occurrences if o.classification != ids.CONVERGED]
    for occurrence in actionable[:RENDER_OCCURRENCE_LIMIT]:
        where = f"{occurrence.location}" + (" (embedded)" if occurrence.embedded else "")
        lines.append(f"  {occurrence.path}: {where} = {occurrence.context or occurrence.value} "
                     f"[{occurrence.classification}]")
    if len(actionable) > RENDER_OCCURRENCE_LIMIT:
        lines.append(f"  ... and {len(actionable) - RENDER_OCCURRENCE_LIMIT} more "
                     f"(use --json for all of them)")
    return lines


def render_json(report: Report) -> str:
    return json.dumps({
        "source": report.source,
        "locations": [asdict(loc) for loc in report.locations],
        "verdict": report.verdict,
        "exit_code": report.exit_code,
        "fix": report.fix,
        "library": report.library,
        "notes": report.notes,
        "scanned": report.scanned,
        "counts": report.counts,
        "occurrences": [asdict(o) for o in report.occurrences],
    }, indent=2)
