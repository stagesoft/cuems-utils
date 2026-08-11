"""Public API snapshot (T019a) — FR-024, SC-018.

"No public API change" is the kind of claim that gets reviewed rather than
measured, and review does not catch a keyword argument that quietly acquired a
default. So the surface is captured as a golden from **unmodified** code, like
every other artifact in this feature, and compared.

Captured: ``cuemsutils.xml.__all__``, the five exported symbols, and every
public callable's ``inspect.signature``. Not captured: docstrings and source —
those may change freely, and pinning them would make the snapshot fail on every
comment edit, which is how a golden gets regenerated out of habit.

Like the D14 chain test, this must still be green **and unedited** after the
swap (T050).
"""

from __future__ import annotations

import inspect
import json

import pytest

from tests.support.corpus import GOLDEN_ROOT

GOLDEN = GOLDEN_ROOT / "api" / "public_api.json"

EXPECTED_EXPORTS = [
    "NetworkMap",
    "ProjectMappings",
    "ProjectSettings",
    "Settings",
    "XmlReaderWriter",
]


def _snapshot() -> dict:
    import cuemsutils.xml as xml_package

    snapshot: dict = {"__all__": sorted(xml_package.__all__), "symbols": {}}
    for name in sorted(xml_package.__all__):
        obj = getattr(xml_package, name)
        entry: dict = {"kind": type(obj).__name__, "bases": []}
        if inspect.isclass(obj):
            entry["bases"] = [b.__name__ for b in obj.__bases__]
            entry["methods"] = {}
            for attr in sorted(dir(obj)):
                if attr.startswith("_") and attr != "__init__":
                    continue
                member = getattr(obj, attr, None)
                if not callable(member):
                    continue
                try:
                    entry["methods"][attr] = str(inspect.signature(member))
                except (TypeError, ValueError):
                    entry["methods"][attr] = "<no signature>"
        snapshot["symbols"][name] = entry
    return snapshot


@pytest.fixture(scope="module", autouse=True)
def _ensure_golden():
    """Generate the snapshot on first run; never overwrite it afterwards.

    Same rule as every other golden (FR-021): missing is generated freely,
    existing is never replaced silently. Regenerating this one to make a
    signature change pass would defeat the only thing it measures.
    """
    if not GOLDEN.exists():
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(_snapshot(), indent=2, sort_keys=True))


def test_public_api_matches_the_snapshot():
    assert _snapshot() == json.loads(GOLDEN.read_text())


def test_exports_are_exactly_the_five_documented_symbols():
    """Stated independently of the golden.

    The golden would happily accept a sixth export if it were captured with
    one. This assertion is the one that cannot drift, because the list is
    written out here.
    """
    import cuemsutils.xml as xml_package

    assert sorted(xml_package.__all__) == EXPECTED_EXPORTS


@pytest.mark.parametrize("name", EXPECTED_EXPORTS)
def test_every_export_is_importable_from_the_package_root(name):
    import cuemsutils.xml as xml_package

    assert hasattr(xml_package, name)


def test_config_classes_still_descend_from_xml_reader_writer():
    """The inheritance the config classes' whole public surface rests on.

    ``Settings`` extends ``XmlReaderWriter``, and the three others extend
    ``Settings``. Routing them through the engine (T053) must not flatten that
    — consumers call inherited methods on them.
    """
    from cuemsutils.xml import (
        NetworkMap,
        ProjectMappings,
        ProjectSettings,
        Settings,
        XmlReaderWriter,
    )

    assert issubclass(Settings, XmlReaderWriter)
    for cls in (NetworkMap, ProjectMappings, ProjectSettings):
        assert issubclass(cls, Settings)
