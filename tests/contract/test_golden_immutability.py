"""Golden-immutability guard (T002).

Standing rule 1 (tasks.md): no existing golden is ever regenerated to make a
test pass. Exactly two tasks in this feature (T065, T080) **modify** a
recorded golden, and each does so with a recorded justification; every other
change under ``tests/golden/`` must be an **addition**.

``MANIFEST.sha256`` pins the hash of every file under this directory at the
moment T002 ran (after T003b/T003c added the two new corpus documents' goldens,
so their addition is captured as a baseline rather than as a violation). A
file whose hash no longer matches was regenerated; a file with no entry at all
was added since, which is allowed and expected — this test does not require
the manifest to be exhaustive going forward, only that entries it does have
still hold.
"""

from __future__ import annotations

import hashlib

from tests.support.corpus import GOLDEN_ROOT

MANIFEST_PATH = GOLDEN_ROOT / "MANIFEST.sha256"


def _load_manifest() -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in MANIFEST_PATH.read_text().splitlines():
        if not line.strip():
            continue
        digest, relpath = line.split("  ", 1)
        entries[relpath] = digest
    return entries


def test_manifest_exists_and_is_non_empty():
    assert MANIFEST_PATH.is_file()
    assert _load_manifest()


def test_every_manifested_golden_is_unchanged():
    manifest = _load_manifest()
    changed = []
    missing = []
    for relpath, expected in manifest.items():
        path = GOLDEN_ROOT / relpath
        if not path.is_file():
            missing.append(relpath)
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            changed.append(relpath)

    assert not missing, (
        "golden(s) removed since the manifest was recorded: " + ", ".join(missing)
    )
    assert not changed, (
        "golden(s) regenerated since the manifest was recorded (forbidden "
        "except T065/T080, each with a recorded justification): "
        + ", ".join(changed)
    )


def test_manifest_entries_are_relative_and_sorted():
    """Reviewable as a diff: stable order, no absolute paths, no ``./`` noise."""
    lines = [
        line for line in MANIFEST_PATH.read_text().splitlines() if line.strip()
    ]
    relpaths = [line.split("  ", 1)[1] for line in lines]
    assert relpaths == sorted(relpaths)
    assert all(not p.startswith(("/", "./")) for p in relpaths)
