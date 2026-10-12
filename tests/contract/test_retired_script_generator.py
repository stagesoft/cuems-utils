"""No reference to the retired ``create_script``/settings-template surface remains (T079, FR-033/FR-034).

**Counted, not reviewed**: a plain occurrence count of the two retired
identifiers across ``src/``, ``tests/`` and packaging metadata, so a
docstring is caught exactly as a call would be. Anything deliberately kept
must be listed in ``EXEMPT`` — a passing grep that quietly excludes what it
should have caught is exactly the failure mode this test exists to prevent.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
#: This file itself is excluded from the scan below — its entire job is
#: naming the two retired identifiers, so it is necessarily its own
#: offender otherwise.
THIS_FILE = Path(__file__).resolve()

SEARCH_ROOTS = (
    REPO_ROOT / "src",
    REPO_ROOT / "tests",
    REPO_ROOT / "pyproject.toml",
)

NEEDLES = ("create_script", "templates/settings.xml")

#: (relpath, needle) pairs deliberately kept, with why. Empty by design —
#: ``PROVENANCE.md`` was a candidate (T069) but was rewritten instead of
#: exempted, since it named a since-deleted file path rather than merely
#: recalling history.
EXEMPT: frozenset[tuple[str, str]] = frozenset()


def _files():
    for root in SEARCH_ROOTS:
        if root.is_file():
            if root != THIS_FILE:
                yield root
        elif root.is_dir():
            for path in root.rglob("*"):
                if path.is_file() and path != THIS_FILE:
                    yield path


def test_no_reference_to_the_retired_surface_remains():
    offenders = []
    for path in _files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        relpath = str(path.relative_to(REPO_ROOT))
        for needle in NEEDLES:
            if needle in text and (relpath, needle) not in EXEMPT:
                offenders.append(f"{relpath}: {needle!r}")

    assert not offenders, (
        "reference(s) to the retired create_script/settings-template surface "
        "remain (add to EXEMPT with a reason, or rewrite): " + "\n".join(offenders)
    )


def test_the_retired_files_are_gone():
    assert not (REPO_ROOT / "src/cuemsutils/create_script.py").exists()
    assert not (REPO_ROOT / "templates/settings.xml").exists()
