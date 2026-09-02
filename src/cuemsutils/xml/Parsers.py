from ..cues import *
from ..cues.MediaCue import Media, Region
from ..cues.CueOutput import AudioCueOutput, VideoCueOutput, DmxCueOutput
from ..cues.Cue import Cue, UI_properties
from ..log import Logger
from ..helpers import strtobool
from ..tools.CTimecode import CTimecode
from ..tools.Uuid import Uuid

PARSER_SUFFIX = 'Parser'
GENERIC_PARSER = 'GenericParser'
#TODO: XML_ROOT_TAG get from constants storage
XML_ROOT_TAG = 'CuemsScript'

# Keys that must never be type-coerced by str_to_value(). Without this, a cue named
# "n" is saved as False, one named "1" as int 1, and one named "none" becomes None ->
# <name/> -> XSD minLength violation, i.e. a hard save error. See ClickUp 869cqbpxa.
#
# 'name', 'description' and 'file_name' are the keys actually reachable today. The
# rest are defensive only: they are currently shielded by bypasses in outputsParser
# (builds output objects directly), _normalize_fade_parameters (diverts 'parameters'
# before the scalar branch) and the GenericDict fallback in GenericParser.parse()
# (get_class('ui_properties') misses because the class is UI_properties). They are
# listed so that fixing any of those bypasses cannot silently reintroduce this bug.
#
# 'id' is deliberately ABSENT: the Uuid() branch in str_to_value is the only thing
# that produces Uuid objects on parse (parsers assign via raw dict.__setitem__ and so
# never hit the property setters). Adding 'id' here would downgrade every cue, script
# and media id to a plain str.
STRING_TYPED_KEYS = frozenset({
    # reachable today
    'name', 'description', 'file_name',
    # defensive -- see above
    'output_name', 'parameter_name', 'icon', 'color', 'unix_name',
})

class GenericDict(dict):
    pass

class CuemsParser():
    def __init__(self, init_dict):
        try:
            if next(iter(init_dict)) != XML_ROOT_TAG:
                root_value = init_dict[XML_ROOT_TAG]
                self.init_dict = {XML_ROOT_TAG: root_value}
                Logger.debug("Found root tag and is not the first one, extracting")
                Logger.debug(self.init_dict)
            else:
                self.init_dict = init_dict
        except KeyError:
            self.init_dict = init_dict
            Logger.debug("No root tag found, using provided dictionary")
            Logger.debug(self.init_dict)

    def get_parser_class(self, class_string):
        parser_name = class_string + PARSER_SUFFIX
        try:
            parser_class = (globals()[parser_name], class_string)
        except KeyError:
            Logger.debug(
                f"Could not find class {parser_name}, reverting to generic parser class"
            )
            parser_class = (globals()[GENERIC_PARSER], class_string)
        return parser_class

    def get_class(self, class_string):
        try:
            _class = globals()[class_string]
        except KeyError:
            Logger.debug(f"Could not find class {class_string}")
            _class = GenericDict
        return _class

    def get_first_key(self, _dict):
        return list(_dict.keys())[0]

    def get_contained_dict(self, _dict):
        return list(_dict.values())[0]

    def str_to_value(self, _string, key = None):
        """Decode a string-encoded scalar into its Python type.

        Args:
            _string: The value to decode. Non-str values pass through unchanged.
            key: The dict key ``_string`` was stored under, when known. Values
                whose key is in :data:`STRING_TYPED_KEYS` are returned verbatim
                so free-text fields are never coerced (ClickUp 869cqbpxa).

        Returns:
            The decoded value, or ``_string`` unchanged for string-typed keys.
        """
        # Must precede every coercion branch below, including the none/null one:
        # a cue legitimately named "none" would otherwise become None.
        if key in STRING_TYPED_KEYS:
            return _string
        if not isinstance(_string, str):
            return _string
        if _string in ['none', 'null', '']:
            return None
        if _string.isdigit():
            return int(_string)
        for f in [float, strtobool, Uuid]:
            try:
                return f(_string)
            except ValueError:
                pass
        return _string
    

    def parse(self):
        """Delegate to the schema-derived engine (T048, FR-026d).

        **A facade, not a shim.** ``CuemsParser`` is not deprecated and emits no
        warning: it was already library-internal before this feature
        (``XmlReaderWriter.write_from_dict`` and ``read_to_objects`` both call
        it) and it is `cuems-editor`'s primary JSON -> object path at five call
        sites. Contract C8 depends on its silence.

        Everything below this method in the module is the frozen legacy tree it
        used to drive. It is unreachable from here now, kept only so external
        callers keep resolving until feature **006** removes it with the
        deprecation shims (corrected 2026-08-17, T028a: this said 007, which
        disagreed with 004's spec and with feature 005's research).

        Delegating is **not optional given the write swap**: this method and
        ``build_xml_from_object`` are two ends of one round trip, so leaving
        decode on the old parsers while encode ran on the engine would mean two
        different type systems meeting in the middle.
        """
        from .mapper import Mapper

        return Mapper('script').decode_document(self.init_dict)


# --- the frozen legacy tree, deleted (T063, D3) ------------------------------
#
# ~355 lines stood here: ``CuemsScriptParser``, ``CueListParser``,
# ``GenericParser`` and the fifteen ``*Parser`` classes below them — the
# name-mangled dispatch tree ``CuemsParser.parse()`` used to drive.
#
# Feature 004 replaced the dispatch with ``Mapper.decode_document`` and kept
# the tree frozen "until feature 006 removes it with the deprecation shims".
# This is that removal, and the shims are in ``xml/__init__.py``.
#
# **Unreachability was measured, not assumed** (T060): the whole suite run
# under coverage restricted to this file reports every line below
# ``CuemsParser.parse()`` as unexecuted. The record is in
# ``specs/006-public-object-api/legacy-coverage.md``.
#
# What stays above, and why each one:
#
# ``CuemsParser``
#     the entry point itself. ``parse()`` still delegates, and the class now
#     carries a deprecation warning at ``cuemsutils.xml.CuemsParser`` (T061) —
#     which it could not do while the library still called it, hence T061a.
# ``CuemsParser.str_to_value`` and ``STRING_TYPED_KEYS``
#     the type-guessing heuristic and the denylist that held its damage back.
#     Retired in favour of schema-declared adapters and kept as named history:
#     ``test_name_coercion`` reads both to assert the defect class is
#     unrepresentable rather than merely unreached.
# ``GenericDict``
#     imported by ``XmlBuilder.py``, which is itself a frozen shim. Deleting it
#     would break that module's import, not just its behaviour.


# ---------------------------------------------------------------------------
# Deprecation surface (T028, FR-026b/c — trimmed by T063)
#
# What is left of the facade after the tree below it was deleted. The sixteen
# frozen ``*Parser`` classes it used to decorate are gone; the two symbols that
# survive are decorated here for the same reason they always were.
#
# The decorators are applied here rather than inline so the frozen bodies keep a
# zero-line diff — a legacy implementation nobody is allowed to change should
# also be one nobody has a reason to open.
#
# ``deprecated`` patches ``__init__`` and returns the *same* class object, so
# class identity is preserved. That matters: ``XmlBuilder`` does
# ``isinstance(value, GenericDict)`` in four places, and replacing the name with
# a warning subclass would silently make every one of those checks False.
# ---------------------------------------------------------------------------

from ._deprecation import deprecated_symbol  # noqa: E402

_MIGRATION = "the schema-derived engine (see specs/004-xml-serialization-core/migration-map.md)"

#: ``CuemsParser`` is deliberately absent **from this list**, and that is no
#: longer the same statement it was in feature 004.
#:
#: Then, it was not deprecated at all: it was the engine's delegating facade and
#: `cuems-editor`'s primary JSON -> object path, and contract C8 depended on its
#: silence because the library itself called it.
#:
#: Now it *is* deprecated — as the sixth retired entry point (contract C3) — but
#: at ``cuemsutils.xml.CuemsParser``, where the alias lives, rather than here.
#: The library stopped calling it in T061a, which is what makes that possible
#: without failing C8. Decorating the class in place instead would also warn for
#: ``xml/__init__.py``'s own import.
deprecated_symbol(_MIGRATION)(GenericDict)

# The type-guessing heuristic itself (FR-003). Deprecated on ``CuemsParser``
# even though the class object is not decorated here, because the class survives
# and the heuristic must not: nothing in this library calls it, and this warning
# is what makes that checkable rather than asserted.
CuemsParser.str_to_value = deprecated_symbol(
    "schema-declared types; the engine no longer guesses"
)(CuemsParser.str_to_value)

# ``STRING_TYPED_KEYS`` has no call to hook: it is a ``frozenset`` read as a
# value, not invoked. It is deprecated in the same breath as ``str_to_value`` —
# the denylist exists only to protect the heuristic — but it cannot warn, and
# saying so here is better than implying a guarantee that is not there. Its
# retirement is recorded in the migration map instead.
