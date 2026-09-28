# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""The write record — what ``cuems-init-node`` last wrote (feature 011, FR-027a,
research R5, data-model.md §6).

It is the reference that lets a re-run tell an operator's hand edit from the
tool's own previous output: a field whose on-disk value equals the recorded
one is recomputed; one that differs is the operator's and is kept. Absent
record ⇒ every difference is kept (the safe default on a host provisioned
before this feature). Lives outside ``/etc/cuems`` — it is state, not
configuration — and ``postrm purge`` removes it.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RECORD_NAME = "last-written.json"
VERSION = 1


@dataclass
class DocumentRecord:
    path: str
    sha256: str
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class WriteRecord:
    written_at: str
    documents: dict[str, DocumentRecord] = field(default_factory=dict)

    def fields_of(self, name: str) -> dict[str, Any] | None:
        entry = self.documents.get(name)
        return None if entry is None else entry.fields


def record_path(state_dir: Path) -> Path:
    return Path(state_dir) / "init-node" / RECORD_NAME


def load(state_dir: Path) -> WriteRecord | None:
    """The record, or ``None`` when absent or unreadable (both mean "no record")."""
    path = record_path(state_dir)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        documents = {
            name: DocumentRecord(entry["path"], entry["sha256"], dict(entry.get("fields", {})))
            for name, entry in raw.get("documents", {}).items()
        }
        return WriteRecord(raw.get("written_at", ""), documents)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save(state_dir: Path, record: WriteRecord) -> Path:
    """Atomic: a temporary beside the target, then ``os.replace``."""
    path = record_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": VERSION,
        "written_at": record.written_at,
        "documents": {
            name: {"path": entry.path, "sha256": entry.sha256, "fields": entry.fields}
            for name, entry in record.documents.items()
        },
    }
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(payload, out, indent=2, sort_keys=True)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return path


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def leaves(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Dotted path → scalar for every scalar reachable through dict keys.

    Lists are not descended: a document's repeated children (map rows, device
    sections) are not "fields" the three-way decision applies to.
    """
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                out.update(leaves(value, path))
            elif isinstance(value, list):
                continue
            else:
                out[path] = _plain(value)
    return out


def _plain(value: Any) -> Any:
    """A JSON-stable scalar: enums by value, uuid objects by string."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "value") and not callable(value.value):
        return value.value
    return str(value)
