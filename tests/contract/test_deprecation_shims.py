"""Contract C9 (T030) — consumer imports still resolve, and say so on every use.

The compatibility half of this feature. Twelve known call sites across
`cuems-editor`, `cuems-engine` and `cuems-nodeconf` import from the pre-rename
paths; all of them must keep working (SC-013, FR-026).

**Per-call, not per-import** (FR-027b). A module-level re-export warns at most
once per process, and never again in a daemon that imported at startup — which
is exactly the consumer who most needs telling that they are still routing
production traffic through a retired path. So each symbol is called once and
then twice under ``simplefilter("always")``, and the record count must
*double*. A shim that only rebinds names emits the same count either way and
fails. See ``assert_warns_per_call`` for why the assertion is a ratio rather
than the literal "two records" the contract text uses.

One symbol must stay **silent**: ``CuemsParser``. It is not a retired path but
the engine's delegating facade (Assumption 3a, FR-026d), and contract C8
depends on its silence.
"""

from __future__ import annotations

import importlib
import warnings

import pytest

from cuemsutils.xml._deprecation import REMOVAL_RELEASE

OLD_IMPORT_PATHS = [
    "cuemsutils.xml.XmlReaderWriter",
    "cuemsutils.xml.Settings",
    "cuemsutils.xml.Parsers",
    "cuemsutils.xml.XmlBuilder",
    "cuemsutils.xml.CMLCuemsConverter",
]

SETTINGS_FILE = "tests/data/corpus/cuems-utils/settings.xml"
SCRIPT_FILE = "tests/data/corpus/cuems-editor/script_minimal.xml"


def _records(fn, times=2):
    """Call ``fn`` ``times`` times and return the DeprecationWarnings raised."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for _ in range(times):
            fn()
    return [w for w in caught if issubclass(w.category, DeprecationWarning)]


def assert_warns_per_call(fn):
    """The C9 assertion: warnings scale with calls, and never reach zero.

    Expressed as a **ratio**, not an exact count. A symbol whose class
    hierarchy is deprecated at several levels emits one record per decorated
    ancestor — ``GenericCueXmlBuilder`` emits three, through
    ``CuemsScriptXmlBuilder`` and ``XmlBuilder`` — and that is still per-call.
    Pinning an exact number would pin the legacy inheritance graph, which is
    frozen but not part of any contract.

    What the contract actually forbids is a *constant*: a shim that warns once
    per import scores the same for one call as for two, which is what this
    catches.
    """
    once = len(_records(fn, times=1))
    twice = len(_records(fn, times=2))
    assert once >= 1, "no DeprecationWarning emitted at all"
    assert twice == 2 * once, (
        f"{once} record(s) for one call but {twice} for two — "
        f"warnings do not scale with calls, so this is not per-call emission"
    )


# --- the import surface ---------------------------------------------------


@pytest.mark.parametrize("path", OLD_IMPORT_PATHS)
def test_old_import_path_still_resolves(path):
    assert importlib.import_module(path) is not None


@pytest.mark.parametrize("path", OLD_IMPORT_PATHS)
def test_importing_is_silent(path):
    """Importing a shim must not warn — only *using* it does.

    Not a technicality. Import-time warnings fire once, at startup, in whatever
    context happened to import first, and are routinely filtered away before
    anyone sees them. Deferring the warning to the call site is what makes it
    reach the code that needs changing.
    """
    importlib.import_module(path)  # ensure it is cached, so the next import is a no-op
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(importlib.import_module(path))
    assert [w for w in caught if issubclass(w.category, DeprecationWarning)] == []


# --- per-call emission ----------------------------------------------------


def test_shimmed_class_warns_on_every_instantiation():
    from cuemsutils.xml.XmlReaderWriter import XmlReaderWriter

    assert_warns_per_call(lambda: XmlReaderWriter(schema_name="script", xmlfile=SCRIPT_FILE))


def test_shimmed_config_class_warns_on_every_instantiation():
    from cuemsutils.xml.Settings import Settings

    # ``Settings.__init__`` calls ``self.read()``, itself a wrapped method, so
    # each construction emits the class warning *and* the method warning.
    assert_warns_per_call(lambda: Settings(SETTINGS_FILE))


def test_shimmed_method_warns_on_every_call():
    from cuemsutils.xml.XmlReaderWriter import XmlReaderWriter

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        reader = XmlReaderWriter(schema_name="script", xmlfile=SCRIPT_FILE)
    assert_warns_per_call(reader.read)


def test_shimmed_function_warns_on_every_call():
    from cuemsutils.xml.XmlReaderWriter import get_pkg_schema

    assert_warns_per_call(lambda: get_pkg_schema("script"))


def test_frozen_parser_warns_on_every_instantiation():
    from cuemsutils.xml.Parsers import GenericDict

    assert_warns_per_call(GenericDict)


def test_frozen_builder_warns_on_every_instantiation():
    from cuemsutils.xml.XmlBuilder import GenericCueXmlBuilder

    assert_warns_per_call(lambda: GenericCueXmlBuilder({}, xml_tree=None))


def test_type_guessing_heuristic_warns_on_every_call():
    """FR-003 — ``str_to_value`` must not be reachable from a live path.

    It stays callable for external code, and every call says so. After the swap
    this warning is what makes "nothing internal calls it" checkable (C8) rather
    than merely claimed.
    """
    from cuemsutils.xml.Parsers import CuemsParser

    assert_warns_per_call(lambda: CuemsParser.str_to_value(None, "n", key="name"))


# --- message content ------------------------------------------------------


def test_message_names_the_replacement_and_the_removal_release():
    from cuemsutils.xml.Settings import NetworkMap

    records = _records(lambda: NetworkMap("tests/data/corpus/cuems-utils/network_map.xml"), times=1)
    assert records
    text = str(records[0].message)
    assert "cuemsutils.xml.settings.NetworkMap" in text
    assert REMOVAL_RELEASE in text


def test_removal_release_is_a_version_not_a_feature_id():
    """FR-027a — a consumer cannot act on "removed in feature 007"."""
    assert REMOVAL_RELEASE == "v0.1.1"


def test_warning_is_reported_at_the_callers_line():
    """FR-027b — the stacklevel points at consumer code, not at the shim.

    A warning attributed to ``_deprecation.py`` tells the reader nothing about
    which of their call sites to fix.
    """
    from cuemsutils.xml.XmlReaderWriter import XmlReaderWriter

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        XmlReaderWriter(schema_name="script", xmlfile=SCRIPT_FILE)  # <- this line

    records = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert records
    assert records[0].filename == __file__


# --- the one symbol that must stay silent ---------------------------------


def test_cuems_parser_emits_no_warning():
    """FR-026d, Assumption 3a — ``CuemsParser`` is supported, not retired.

    It was already library-internal before this feature
    (``XmlReaderWriter.write_from_dict`` and ``read_to_objects`` both call it)
    and is `cuems-editor`'s primary JSON -> object path at five call sites. C8
    runs the whole corpus through the library's own entry points and expects
    zero deprecation warnings; a warning here would fail that test by design.
    """
    from cuemsutils.xml.Parsers import CuemsParser

    assert _records(lambda: CuemsParser({"CuemsScript": {}})) == []


def test_cuems_parser_parse_emits_no_warning():
    from cuemsutils.xml.Parsers import CuemsParser

    assert _records(lambda: CuemsParser({"CuemsScript": {}}).parse) == []


# --- shims stay equivalent, not merely importable -------------------------


def test_shimmed_class_is_the_real_class_by_isinstance():
    """A shim that warns but returns something incompatible is not a shim.

    ``GenericDict`` is the sharp case: ``XmlBuilder`` does
    ``isinstance(value, GenericDict)`` in four places, so a warning *subclass*
    at that name would turn all four checks False and silently change what gets
    serialized.
    """
    from cuemsutils.xml.Settings import Settings as ShimSettings
    from cuemsutils.xml.settings import Settings as RealSettings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert isinstance(ShimSettings(SETTINGS_FILE), RealSettings)


def test_frozen_symbols_keep_their_identity():
    """The frozen modules are decorated in place, not replaced.

    ``deprecated`` patches ``__init__`` and returns the same class object, so
    ``Parsers.GenericDict`` is still the class ``XmlBuilder`` imported.
    """
    from cuemsutils.xml.Parsers import GenericDict
    from cuemsutils.xml.XmlBuilder import GenericDict as BuilderView

    assert GenericDict is BuilderView
    assert issubclass(GenericDict, dict)


def test_shim_and_new_path_read_identically():
    """The compatibility claim, measured rather than assumed."""
    from cuemsutils.xml.Settings import Settings as ShimSettings
    from cuemsutils.xml.settings import Settings as RealSettings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert ShimSettings(SETTINGS_FILE).xml_dict == RealSettings(SETTINGS_FILE).xml_dict


# --- symbols that cannot warn, stated rather than implied -----------------


# --- the shim/class name collision ----------------------------------------


@pytest.mark.parametrize("name", ["Settings", "XmlReaderWriter"])
def test_package_root_still_exports_a_class_not_a_module(name):
    """The shims are submodules whose names collide with exported classes.

    Importing ``cuemsutils.xml.Settings`` makes Python set that submodule as an
    attribute of the package — overwriting the ``Settings`` *class* the package
    exports. Whichever happens last wins, so before ``__init__`` was made to
    import the shims up front, ``from cuemsutils.xml import Settings`` returned
    a module to anyone who had touched the old path first, and calling it raised
    ``TypeError: 'module' object is not callable``.

    A latent public-API break with no error at import time and a failure far
    from its cause. This test imports the shim submodules *first*, on purpose,
    to reproduce exactly that ordering.
    """
    importlib.import_module(f"cuemsutils.xml.{name}")

    import cuemsutils.xml as xml_package

    exported = getattr(xml_package, name)
    assert isinstance(exported, type), (
        f"cuemsutils.xml.{name} is a {type(exported).__name__}, not a class — "
        f"the shim submodule has shadowed the exported class"
    )
    assert callable(exported)


@pytest.mark.parametrize(
    "module,name",
    [
        ("cuemsutils.xml.Parsers", "STRING_TYPED_KEYS"),
        ("cuemsutils.xml.XmlBuilder", "VALUE_TYPES"),
    ],
)
def test_non_callable_deprecated_symbols_still_resolve(module, name):
    """Deprecated, importable, and *unable* to warn — recorded honestly.

    Both are values read in ``isinstance``/membership checks, never invoked, so
    "warns on each call" has nothing to attach to. They are listed in the
    migration map instead. Asserting their continued existence is the only
    compatibility guarantee that can be made here, so it is the one made.
    """
    assert hasattr(importlib.import_module(module), name)
