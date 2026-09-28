# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""``cuems-init-node --check`` (feature 011, US6; FR-032, research R14).

Reads the four places a node's identity lands — ``settings.xml`` (the source),
``network_map.xml``, ``default_mappings.xml`` and the live Avahi service file
— and reports each by path. Four exit classes, precedence **3 > 2 > 1**:

* **0** coherent and provisioned;
* **1** at least one mirror disagrees with the source;
* **2** at least one location absent or unreadable;
* **3** the source carries the sentinel — ``NOT PROVISIONED``. A
  never-provisioned node is coherent but actionable, so it does not share the
  "done" code; an absent Avahi record is *expected* there (nodeconf refuses
  to announce a sentinel) and is reported as such rather than as class 2.

Reads only stdlib XML on purpose: the checker must work on a node whose
documents the library would refuse, since that is when an operator runs it.
It never writes.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path

SENTINEL = "00000000-0000-0000-0000-000000000000"
UUID_TOKEN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
DEFAULT_AVAHI_SERVICE = "/etc/avahi/services/cuems.service"

NOT_PROVISIONED = "NOT PROVISIONED"
FIX_PLAIN = "cuems-init-node"
FIX_RESET = "cuems-init-node --reset"
FIX_NODECONF = "systemctl restart cuems-nodeconf.service"
FIX_UNMASK = "systemctl unmask cuems-nodeconf.service && systemctl enable --now cuems-nodeconf.service"

OK, MISMATCH, ABSENT, UNREADABLE, EXPECTED_ABSENT = "ok", "MISMATCH", "ABSENT", "UNREADABLE", "absent (expected)"


@dataclass
class Location:
    path: str
    status: str
    detail: str = ""
    values: list[str] = field(default_factory=list)


@dataclass
class Report:
    source: dict
    locations: list[Location]
    verdict: str
    exit_code: int
    fix: str


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


def check(conf_dir: Path, avahi_service: Path | None = None) -> Report:
    conf = Path(conf_dir)
    avahi = Path(avahi_service) if avahi_service else Path(DEFAULT_AVAHI_SERVICE)
    source, source_loc = _source(conf)
    uuid = source.get("uuid", "")
    sentinel = uuid == SENTINEL
    locations = [source_loc]
    if uuid:
        locations.append(_network_map(conf, uuid))
        locations.append(_default_mappings(conf, uuid))
        locations.append(_avahi(avahi, uuid, sentinel))
    statuses = {loc.status for loc in locations}
    if sentinel:
        return Report(source, locations, "not provisioned", 3, FIX_PLAIN)
    if not uuid or ABSENT in statuses or UNREADABLE in statuses:
        others_absent = any(loc.status in (ABSENT, UNREADABLE) and loc.path != str(avahi) for loc in locations)
        fix = FIX_PLAIN if others_absent or not uuid else FIX_UNMASK
        return Report(source, locations, "absent or unreadable", 2, fix)
    if MISMATCH in statuses:
        only_avahi = all(loc.status != MISMATCH or loc.path == str(avahi) for loc in locations)
        return Report(source, locations, "mismatch", 1, FIX_NODECONF if only_avahi else FIX_PLAIN)
    return Report(source, locations, "coherent", 0, "")


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
    lines.append(f"verdict: {report.verdict} (exit {report.exit_code})" + (f" — run: {report.fix}" if report.fix else ""))
    return "\n".join(lines)


def render_json(report: Report) -> str:
    return json.dumps({
        "source": report.source,
        "locations": [asdict(loc) for loc in report.locations],
        "verdict": report.verdict,
        "exit_code": report.exit_code,
        "fix": report.fix,
    }, indent=2)
