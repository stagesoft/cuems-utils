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
  lockdown is feature 010's (renumbered from 009 on 2026-08-25).

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
from tests.support.public_api import PUBLIC_SCRIPTS, installed_scripts

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
#: caller cannot inspect is one it cannot surface. ``DmxChannelDecodeError``
#: joins in feature 009 (FR-006) — a DMX channel entry that cannot be
#: converted, replacing that setter's former swallow-and-log fallback.
PUBLIC_ERRORS = (
    "ConversionRecord",
    "CuemsError",
    "DmxChannelDecodeError",
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

#: Published **functions**, recorded with their signatures (feature 013, T061).
#:
#: They need their own section, and the reason is a limitation of ``_members``
#: rather than a style choice: it only records the methods *of a class*, so a
#: function lands as ``{"kind": "function", "bases": []}`` with no signature at
#: all. Growing ``symbols`` by the name alone would pin that the name exists and
#: nothing about what it takes — and ``partition_by_adoption(network_map)`` is a
#: signature consumers call positionally.
#:
#: ``NodeList`` is deliberately **not** in ``PUBLIC_CLASSES``: it is a module,
#: not a class, and ``_members`` would record it as
#: ``{"kind": "module", "bases": []}``.
PUBLIC_FUNCTIONS = {
    # feature 013, FR-035: the non-mutating adoption split, published from the
    # node model's public face. The body stays in ``xml/settings.py``.
    "partition_by_adoption": ("cuemsutils.tools.NodeList", "partition_by_adoption"),
    # feature 013, FR-036: validate a configuration document without an
    # installation. Reached through the ``cuemsutils.tools`` façade, which is
    # the published path — not through ``tools.config_validate``.
    "validate_config_document": ("cuemsutils.tools", "validate_config_document"),
}


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


def _function_entry(fn) -> dict:
    """A published function: its kind and its signature, nothing else."""
    entry: dict = {"kind": type(fn).__name__}
    try:
        entry["signature"] = str(inspect.signature(fn))
    except (TypeError, ValueError):
        entry["signature"] = "<no signature>"
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
        # Feature 013 (FR-035, FR-036): published functions, with signatures.
        "functions": {},
        # Feature 011 (FR-023, research R11): the entry points are a surface too.
        "scripts": installed_scripts(),
    }
    for label, (module_name, attribute) in sorted(PUBLIC_CLASSES.items()):
        module = importlib.import_module(module_name)
        snapshot["symbols"][label] = _members(getattr(module, attribute))
    for label, (module_name, attribute) in sorted(PUBLIC_FUNCTIONS.items()):
        module = importlib.import_module(module_name)
        snapshot["functions"][label] = _function_entry(getattr(module, attribute))
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


#: SC-004's one recorded exception, added by feature 010 (FR-028b).
#:
#: SC-004 exists to stop a consumer naming a schema to do **domain** work —
#: loading a document, reading a value. Feature 006 replaced
#: ``manager.load("network_map")`` with ``manager.network_map`` for exactly that
#: reason, and that replacement stands untouched.
#:
#: Describing a schema is **meta**, not domain, and is inherently parameterised
#: by schema: there is no version of "describe this schema" that does not name
#: one. The alternative designs were considered and rejected on 2026-09-04 —
#: six per-schema properties (loses iteration, which is what the frontend's
#: generic form renderer actually does), and classmethods on the owning model
#: classes (``outputs`` has no class at all, and three of five ``ConfigManager``
#: accessors raise or return a bare ``dict`` before a document is loaded, which
#: is precisely when the editor needs the descriptor).
#:
#: The parameter is a :class:`SchemaName` **enum member**, never a string, so
#: SC-004's deeper intent — no stringly-typed schema naming on the public
#: surface — is preserved rather than merely worked around.
#: The **third** exception, added by feature 014 (T022, plan.md §9.3):
#: ``ConfigManager.from_json``.
#:
#: Unlike the two above it, this one *is* domain work — it builds a document —
#: so the exemption is argued differently and the argument is recorded rather
#: than inherited. ``CuemsScript.from_json`` names no schema because the schema
#: is a property of the **type**: the caller holds a ``CuemsScript`` and the
#: class carries ``SCHEMA_NAME``. A JSON payload carries no type. The symmetric
#: design — ``CuemsSettingsType.from_json(payload)`` as a classmethod per root
#: — would name no schema either, and it is unreachable: ``cuemsutils.config``
#: exports nothing and is internal by decision (feature 006), which is exactly
#: why UR-5 asked for this shape (*"the editor would either import
#: cuemsutils.config (Q14) or hand-build an object"* — it does neither).
#:
#: The alternative that keeps SC-004 literally — four methods, one per domain —
#: was rejected: the one consumer that asked for this dispatches on a
#: ``SchemaName`` it is already holding, so four names would make it build a
#: dispatch table to get back to the parameter it started with.
#:
#: As with the other two, the parameter is a :class:`SchemaName` member and
#: never a string, which ``test_the_exceptions_take_the_enum_not_a_string``
#: checks for all three.
SCHEMA_PARAMETER_EXCEPTIONS = frozenset({
    "ConfigManager.get_schema_descriptor",
    "ConfigManager.generate_example",
    "ConfigManager.from_json",
})


@pytest.mark.parametrize("label", sorted(PUBLIC_CLASSES))
def test_no_public_signature_accepts_a_schema_name(label):
    import importlib

    module_name, attribute = PUBLIC_CLASSES[label]
    cls = getattr(importlib.import_module(module_name), attribute)
    offenders = [
        f"{label}.{name}{signature}"
        for name, signature in _public_methods(cls)
        if ("schema_name" in signature.parameters or "schema" in signature.parameters)
        and f"{label}.{name}" not in SCHEMA_PARAMETER_EXCEPTIONS
    ]
    assert not offenders, offenders


def test_the_schema_parameter_exceptions_all_exist():
    """An exception list is a place stale entries hide.

    If an exempted method is renamed or removed, the entry silently starts
    exempting nothing — and the next method to acquire a schema parameter by
    accident inherits a weakened check.
    """
    import importlib

    for entry in SCHEMA_PARAMETER_EXCEPTIONS:
        label, name = entry.split(".", 1)
        module_name, attribute = PUBLIC_CLASSES[label]
        cls = getattr(importlib.import_module(module_name), attribute)
        assert hasattr(cls, name), f"{entry} is exempted and does not exist"


def test_the_exceptions_take_the_enum_not_a_string():
    """FR-028b — the exception is granted *because* the parameter is typed.

    An exempted method that took a bare ``str`` would be the thing SC-004
    forbids, wearing the exemption granted to the thing it does not do.
    """
    import importlib

    from cuemsutils.tools.ConfigManager import SchemaName

    for entry in SCHEMA_PARAMETER_EXCEPTIONS:
        label, name = entry.split(".", 1)
        module_name, attribute = PUBLIC_CLASSES[label]
        cls = getattr(importlib.import_module(module_name), attribute)
        parameter = inspect.signature(getattr(cls, name)).parameters["schema"]
        assert parameter.annotation is SchemaName, (
            f"{entry} is exempted from SC-004 on the grounds that it takes "
            f"SchemaName, but its annotation is {parameter.annotation!r}"
        )


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


def test_the_published_scripts_are_the_declared_set():
    """Feature 011: ``[project.scripts]`` and the allowlist agree both ways."""
    assert set(installed_scripts()) == PUBLIC_SCRIPTS


@pytest.mark.parametrize("label", sorted(PUBLIC_FUNCTIONS))
def test_every_published_function_resolves_from_its_published_path(label):
    """The path in ``PUBLIC_FUNCTIONS`` is the one a consumer is told to use.

    Both names are published *lazily*, through a module ``__getattr__``, so
    resolving them is the assertion: a typo in the lazy table is an
    ``AttributeError`` nothing else would catch.
    """
    import importlib

    module_name, attribute = PUBLIC_FUNCTIONS[label]
    module = importlib.import_module(module_name)
    assert callable(getattr(module, attribute))


@pytest.mark.parametrize("label", sorted(PUBLIC_FUNCTIONS))
def test_a_published_function_is_visible_to_dir(label):
    """A lazily published name must still be enumerable.

    ``dir()`` is how the snapshot and anything else that walks the surface finds
    it; a module ``__getattr__`` without a matching ``__dir__`` publishes a name
    that only someone who already knows it can discover.
    """
    import importlib

    module_name, attribute = PUBLIC_FUNCTIONS[label]
    assert attribute in dir(importlib.import_module(module_name))


def test_the_golden_pins_each_published_function_signature():
    """Not only the name. ``partition_by_adoption(network_map)`` is called
    positionally by consumers, so the parameter is part of the contract."""
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    functions = golden["functions"]
    assert set(functions) == set(PUBLIC_FUNCTIONS)
    assert functions["partition_by_adoption"]["signature"] == (
        "(network_map) -> tuple[tuple, tuple]"
    )
    for label, entry in functions.items():
        assert entry["signature"] != "<no signature>", label
