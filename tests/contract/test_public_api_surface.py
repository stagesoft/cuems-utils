"""Public API snapshot (T019a, extended by T057/T065) — FR-019, FR-022, SC-018.

"No public API change" is the kind of claim that gets reviewed rather than
measured, and review does not catch a keyword argument that quietly acquired a
default. So the surface is captured as a golden and compared.

**What the surface is changed in feature 006, so what the golden records
changed with it.** Until then it was ``cuemsutils.xml.__all__`` and the five
classes it exported. Now:

* ``cuemsutils.xml`` exports **nothing** — ``__all__ == []`` (FR-019);
* the public surface is ``CuemsScript``, ``ConfigManager``/``ConfigBase`` and
  the ``cuemsutils.errors`` hierarchy;
* the six retired entry points stay **reachable by dotted access for one
  release** and warn on use (FR-019a). That is deliberately *not* asserted
  away: the deprecation shims resolve through those same paths, so emptying
  ``__all__`` and making the names unreachable are different changes. Genuine
  lockdown is feature 009's.

The golden update is T065, one of exactly two permitted in this feature
(standing rule 1). Its justification and the enumerated diff are in
``specs/006-public-object-api/api-surface-diff.md``.

Not captured: docstrings and source. Those may change freely, and pinning them
would make the snapshot fail on every comment edit — which is how a golden gets
regenerated out of habit.
"""

from __future__ import annotations

import inspect
import json

import pytest

from tests.support.corpus import GOLDEN_ROOT

GOLDEN = GOLDEN_ROOT / "api" / "public_api.json"

#: The two public entry points, and the one public module of exceptions.
PUBLIC_CLASSES = {
    "CuemsScript": ("cuemsutils.cues.CuemsScript", "CuemsScript"),
    "ConfigManager": ("cuemsutils.tools.ConfigManager", "ConfigManager"),
    "ConfigBase": ("cuemsutils.tools.ConfigBase", "ConfigBase"),
}

#: The exception hierarchy, plus the repair-report types feature 008 (ITEM E)
#: adds to the same module — ``LoadReport``/``Outcome``/``RepairRecord``/
#: ``ConversionRecord`` are data, not exceptions, but they join
#: ``cuemsutils.errors`` on 006's precedent (data-model.md §4): a repair the
#: caller cannot inspect is one it cannot surface.
PUBLIC_ERRORS = (
    "ConversionRecord",
    "CuemsError",
    "IngestError",
    "LoadReport",
    "Outcome",
    "RepairRecord",
    "SchemaError",
    "ValidationError",
)

#: Reachable by dotted access for one release, warning on use (FR-019a).
DEPRECATED_DOTTED = [
    "CuemsParser",
    "NetworkMap",
    "ProjectMappings",
    "ProjectSettings",
    "Settings",
    "XmlReaderWriter",
]

#: The six methods FR-007 names.
SCRIPT_METHODS = ("from_json", "load", "save", "to_json", "to_wire", "validate")


def _members(obj) -> dict:
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
    return entry


def _snapshot() -> dict:
    import importlib

    import cuemsutils.errors as errors_module
    import cuemsutils.xml as xml_package

    snapshot: dict = {
        "xml_exports": sorted(xml_package.__all__),
        "deprecated_dotted": sorted(
            name for name in DEPRECATED_DOTTED if hasattr(xml_package, name)
        ),
        "errors": {
            name: _members(getattr(errors_module, name))
            for name in sorted(PUBLIC_ERRORS)
        },
        "symbols": {},
    }
    for label, (module_name, attribute) in sorted(PUBLIC_CLASSES.items()):
        module = importlib.import_module(module_name)
        snapshot["symbols"][label] = _members(getattr(module, attribute))
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


# --- FR-019: the machinery is machinery (T057) -----------------------------


def test_the_xml_package_exports_nothing():
    """Stated independently of the golden.

    The golden would happily accept an export if it were captured with one.
    This assertion is the one that cannot drift, because the value is written
    out here.
    """
    import cuemsutils.xml as xml_package

    assert xml_package.__all__ == []


def test_star_import_binds_nothing():
    namespace: dict = {}
    exec("from cuemsutils.xml import *", namespace)  # noqa: S102 - that is the test
    bound = {k for k in namespace if not k.startswith("__")}
    assert bound == set(), f"star-import bound {sorted(bound)}"


@pytest.mark.parametrize("name", DEPRECATED_DOTTED)
def test_dotted_access_still_resolves_this_release(name):
    """FR-019a, and asserted **positively**.

    Emptying ``__all__`` and making the names unreachable are different
    changes, and only the first is this feature's. The deprecation shims
    resolve through dotted access, so a test that asserted these names *gone*
    would be asserting the shims broken.
    """
    import cuemsutils.xml as xml_package

    assert hasattr(xml_package, name)


@pytest.mark.parametrize("name", DEPRECATED_DOTTED)
def test_every_dotted_name_is_a_class_not_a_module(name):
    import cuemsutils.xml as xml_package

    assert inspect.isclass(getattr(xml_package, name))


# --- SC-004: no public signature takes a schema name -----------------------


def _public_methods(cls):
    for attr in dir(cls):
        if attr.startswith("_") and attr != "__init__":
            continue
        member = getattr(cls, attr, None)
        if not callable(member):
            continue
        try:
            yield attr, inspect.signature(member)
        except (TypeError, ValueError):
            continue


@pytest.mark.parametrize("label", sorted(PUBLIC_CLASSES))
def test_no_public_signature_accepts_a_schema_name(label):
    import importlib

    module_name, attribute = PUBLIC_CLASSES[label]
    cls = getattr(importlib.import_module(module_name), attribute)
    offenders = [
        f"{label}.{name}{signature}"
        for name, signature in _public_methods(cls)
        if "schema_name" in signature.parameters or "schema" in signature.parameters
    ]
    assert not offenders, offenders


def test_the_six_methods_are_on_the_script_class():
    from cuemsutils.cues.CuemsScript import CuemsScript

    for name in SCRIPT_METHODS:
        assert callable(getattr(CuemsScript, name, None))


def test_the_error_hierarchy_is_importable_from_one_module():
    import cuemsutils.errors as errors_module

    for name in PUBLIC_ERRORS:
        assert inspect.isclass(getattr(errors_module, name))
    assert sorted(errors_module.__all__) == sorted(PUBLIC_ERRORS)


def test_config_classes_still_descend_from_xml_reader_writer():
    """The inheritance the config classes' whole public surface rests on.

    Asserted against the **implementation** module, not the package root: as of
    T061 the root's names are deprecation aliases, and an alias subclasses the
    real class rather than the other way round. Consumers still call inherited
    methods on them either way, which is what this measures.
    """
    from cuemsutils.xml.settings import (
        NetworkMap,
        ProjectMappings,
        ProjectSettings,
        Settings,
    )
    from cuemsutils.xml.xml_reader_writer import XmlReaderWriter

    assert issubclass(Settings, XmlReaderWriter)
    for cls in (NetworkMap, ProjectMappings, ProjectSettings):
        assert issubclass(cls, Settings)


def test_the_deprecated_aliases_are_still_instances_of_the_real_classes():
    """Mixing an old and a new import path must not break ``isinstance``."""
    import cuemsutils.xml as xml_package
    from cuemsutils.xml.settings import Settings as RealSettings
    from cuemsutils.xml.xml_reader_writer import XmlReaderWriter as RealWriter

    assert issubclass(xml_package.Settings, RealSettings)
    assert issubclass(xml_package.XmlReaderWriter, RealWriter)
