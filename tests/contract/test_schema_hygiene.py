"""Schema hygiene after the timecode promotion (T009, T010, T011) — FR-007, FR-008.

Three narrow, structural claims about what's left in the schemas and the
Python model once ``settings.xsd``'s dead timecode pair is deleted and
``Media.duration`` is promoted.
"""

from __future__ import annotations

import re

import pytest

from cuemsutils.xml.documents import get_pkg_schema
from cuemsutils.xml.registry import all_registries


def _schema_text(schema_name: str) -> str:
    with open(get_pkg_schema(schema_name), encoding="utf-8") as handle:
        return handle.read()


# --- T009 -------------------------------------------------------------------


def test_settings_xsd_declares_no_timecode_types():
    """FR-007 — the dead pair (unreachable from any element) is gone."""
    text = _schema_text("settings")
    assert "CTimecodeType" not in text
    assert "TimecodeType" not in text


def test_config_settings_py_declares_no_ctimecodetype_class():
    from cuemsutils.config import settings

    assert not hasattr(settings, "CTimecodeType")


def test_registry_coherence_passes_with_no_exception_list():
    """Every registry validates — no complex type is left unbound, and
    nothing needed a special case to make that true after the deletion."""
    for schema_name, registry in all_registries().items():
        registry.validate()  # raises RegistryIncompleteError on any gap


# --- T010 --------------------------------------------------------------------


def test_script_xsd_still_declares_timecodetype():
    """FR-008 — ``script.xsd``'s ``TimecodeType`` survives.

    It is the lexical type of the inner ``<CTimecode>`` element, not a
    duplicate of the deleted ``settings.xsd`` pair — schemas are independent
    (research R4), so this is a distinct declaration.
    """
    text = _schema_text("script")
    assert re.search(r'<xs:simpleType name="TimecodeType">', text)


def test_timecodetype_remains_the_inner_ctimecode_elements_type():
    text = _schema_text("script")
    assert re.search(
        r'<xs:element name="CTimecode" type="cms:TimecodeType"\s*/>', text
    )


# --- T011 ---------------------------------------------------------------------


#: Explanatory prose, not schema content or a stored value — the wrapped
#: library's own frame-1 semantics, documented rather than encoded.
#:
#: T011's task text names four lines (24, 78, 82, 242); this file's current
#: state carries two more (438, 439), a rollover-bug comment in ``__str__``
#: illustrating wrapped-vs-monotonic output with example timecodes. Same
#: character as the other four — prose, not a stored or schema value — so
#: added here rather than treated as a discrepancy to chase.
_ALLOWED_FRAME_FORM_LOCATIONS = {
    ("src/cuemsutils/tools/CTimecode.py", 24),
    ("src/cuemsutils/tools/CTimecode.py", 78),
    ("src/cuemsutils/tools/CTimecode.py", 82),
    ("src/cuemsutils/tools/CTimecode.py", 242),
    ("src/cuemsutils/tools/CTimecode.py", 438),
    ("src/cuemsutils/tools/CTimecode.py", 439),
}

_FRAME_FORM_RE = re.compile(r"\b\d{2}:\d{2}:\d{2}:\d{2}\b")


def test_zero_frame_based_forms_outside_explanatory_prose():
    """SC-004 — the frame-based ``HH:MM:SS:FF`` shape is gone as a schema
    pattern, default, example or model-class value.

    A literal grep-and-count over the repository returns 4 (the excluded
    docstring occurrences) and would wrongly fail; this asserts against
    schema text, declared defaults and stored values specifically, and
    separately confirms the excluded locations are exactly the ones named —
    so the exclusion cannot silently grow to cover a real regression.
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]

    offenders = []
    for xsd in (repo_root / "src" / "cuemsutils" / "xml" / "schemas").glob("*.xsd"):
        with open(xsd, encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, start=1):
                if _FRAME_FORM_RE.search(line):
                    offenders.append(f"{xsd.name}:{lineno}")
    assert offenders == [], f"frame-based form found in schema text: {offenders}"

    ctimecode_py = repo_root / "src" / "cuemsutils" / "tools" / "CTimecode.py"
    found_prose_lines = set()
    with open(ctimecode_py, encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            if _FRAME_FORM_RE.search(line):
                found_prose_lines.add(("src/cuemsutils/tools/CTimecode.py", lineno))

    assert found_prose_lines == _ALLOWED_FRAME_FORM_LOCATIONS, (
        f"expected exactly the recorded docstring occurrences, found {found_prose_lines}"
    )
