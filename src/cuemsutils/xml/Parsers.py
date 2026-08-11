from ..cues import *
from ..cues.FadeProfile import FadeFunctionParameter, FadeProfile
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
        callers keep resolving until feature 007 removes it.

        Delegating is **not optional given the write swap**: this method and
        ``build_xml_from_object`` are two ends of one round trip, so leaving
        decode on the old parsers while encode ran on the engine would mean two
        different type systems meeting in the middle.
        """
        from .mapper import Mapper

        return Mapper('script').decode_document(self.init_dict)

class CuemsScriptParser(CuemsParser):
    def __init__(self, init_dict, class_string):
        self.init_dict = init_dict
        self.class_string = class_string
        self._class = self.get_class(class_string)
        self.item_csp = self._class()
    
    def parse(self):
        for k, v in self.init_dict.items():
            if type(v) is dict:
                if (len(list(v))> 0):
                    parser_class, class_string = self.get_parser_class(k)
                    self.item_csp[k] = parser_class(init_dict=v, class_string=class_string).parse()                    
            else:
                v = self.str_to_value(v, key = k)
                self.item_csp[k] = v

        return self.item_csp

class CueListParser(CuemsScriptParser):
    def __init__(self, init_dict, class_string):
        super().__init__(init_dict, class_string)
        self.item_clp = self._class()

    def parse(self):
        for k, v in self.init_dict.items():
            if isinstance(v, list):
                local_list = []
                for cue in v:
                    Logger.debug(f"Parsing cue {next(iter(cue.keys()))}")
                    parser_class, unused_class_string = self.get_parser_class(self.get_first_key(cue))
                    item_obj = parser_class(
                        init_dict=self.get_contained_dict(cue),
                        class_string=self.get_first_key(cue)
                    ).parse()
                    local_list.append(item_obj)

                self.item_clp['contents'] = local_list
            elif isinstance(v, dict):
                key_parser_class, key_class_string = self.get_parser_class(k)
                if key_parser_class == GenericParser:
                    value_parser_class, value_class_string = self.get_parser_class(self.get_first_key(v))
                    if value_parser_class == GenericParser:
                        self.item_clp[k] = key_parser_class(init_dict=v, class_string=key_class_string).parse()
                    else:
                        self.item_clp[k] = value_parser_class(init_dict=v, class_string=value_class_string).parse()

            else:
                v = self.str_to_value(v, key = k)
                self.item_clp[k] = v
        return self.item_clp

class GenericParser(CuemsScriptParser): 
    def __init__(self, init_dict, class_string):
        self.init_dict = init_dict
        self.class_string = class_string
        self._class = self.get_class(class_string)
        self.item_gp = self._class()
        
    def parse(self):
        Logger.debug(f"Parsing {self.class_string} with GenericParser")
        if self._class == GenericDict:
            Logger.debug("GenericDict class found, using default dict")
            self.item_gp = self.init_dict
        elif isinstance(self.init_dict, dict):
            for dict_key, dict_value in self.init_dict.items():
                if isinstance (dict_value, dict):
                    key_parser_class, key_class_string = self.get_parser_class(dict_key)
                    if key_parser_class == GenericParser:
                        value_parser_class, value_class_string = self.get_parser_class(self.get_first_key(dict_value))
                        if value_parser_class == GenericParser:
                            self.item_gp[dict_key] = key_parser_class(init_dict=dict_value, class_string=key_class_string).parse()
                        else:
                            self.item_gp[dict_key] = value_parser_class(init_dict=dict_value, class_string=value_class_string).parse()
                    else:
                        self.item_gp[dict_key] = key_parser_class(
                            init_dict=dict_value, class_string=key_class_string
                        ).parse()
                elif isinstance(dict_value, list):
                    parser_class, class_string = self.get_parser_class(dict_key)
                    local_list = []
                    for list_item in dict_value:
                        item_obj = parser_class(
                            init_dict=list_item, class_string=class_string
                        ).parse()
                        local_list.append(item_obj)
                    if class_string == 'fade_profiles':
                        merged: list = []
                        for x in local_list:
                            if isinstance(x, list):
                                merged.extend(x)
                            elif x is not None:
                                merged.append(x)
                        self.item_gp[dict_key] = merged if merged else None
                    else:
                        self.item_gp[dict_key] = local_list
                else:
                    dict_value = self.str_to_value(dict_value, key = dict_key)
                    self.item_gp[dict_key] = dict_value
        return self.item_gp

class GenericSubObjectParser(GenericParser):
    def parse(self):
        self.item_gp = self._class(self.init_dict)
        return self.item_gp
    


class CTimecodeParser(GenericParser):  
    def parse(self):
        for dict_key, dict_value in self.init_dict.items():
            self.item_gp = self._class(dict_value)
        return self.item_gp

# class CTimecodeKeyParser(GenericParser):
#     def parse(self):
#         if not self.init_dict:
#             pass
#         if not "CTimecode" in self.init_dict.keys():
#             raise KeyError("CTimecode key not found in dictionary")
#         self.item_gp = CTimecode(self.init_dict["CTimecode"])
#         return self.item_gp

# class offsetParser(CTimecodeKeyParser):
#     pass

# class prewaitParser(CTimecodeKeyParser):
#     pass

# class postwaitParser(CTimecodeKeyParser):
#     pass

# class in_timeParser(CTimecodeKeyParser):
#     pass

# class out_timeParser(CTimecodeKeyParser):
#     pass

class mediaParser(GenericParser):
    def parse(self):
        Logger.debug(f"Parsing with mediaParser {self.init_dict}")
        if not self.init_dict:
            pass
        if not "Media" in self.init_dict.keys():
            try:
                self.item_gp = Media(self.init_dict)
            except:
                raise KeyError("Media key not found in dictionary")
        if not isinstance(self.item_gp, Media):
            try:
                regions = self.init_dict["Media"]["regions"]
                if regions:
                    parsed_regions = []
                    for region in regions:
                        parsed_regions.append(
                            Region(GenericParser(self.get_contained_dict(region), "Region").parse())
                        )
                    self.init_dict["Media"]["regions"] = parsed_regions
            except KeyError:
                pass
            self.item_gp = Media(self.init_dict["Media"])
        return self.item_gp

class outputsParser(GenericParser):
    def __init__(self, init_dict, class_string, parent_class=None):
        self.init_dict = init_dict

    def parse(self):
        Logger.debug("Parsing Outputs")
        for dict_key, dict_value in self.init_dict.items():
            self._class = self.get_class(dict_key)
            # Schema may produce a list when multiple outputs (e.g. DmxCueOutput maxOccurs)
            if isinstance(dict_value, list):
                self.item_op = [self._class(item) for item in dict_value if isinstance(item, dict)]
            else:
                self.item_op = self._class(dict_value)

        return self.item_op

# class regionsParser(GenericParser):
#     def __init__(self, init_dict, class_string, parent_class=None):
#         self.init_dict = init_dict
#         self.class_string = class_string
#         self._class = self.get_class(class_string)
#         self.item_rp = self._class()
        
#     def parse(self):
#         for dict_key, dict_value in self.init_dict.items():
#             key_parser_class, key_class_string = self.get_parser_class(dict_key)
#             self.item_rp = key_parser_class(init_dict=dict_value, class_string=key_class_string).parse()

#         return self.item_rp

class CuemsNodeDictParser(GenericParser):
    def parse(self):
        self.item_rp = list()
        for item in self.init_dict:
            for dict_key, dict_value in item.items():
                key_parser_class, key_class_string = self.get_parser_class(dict_key)
                self.item_rp.append(key_parser_class(init_dict=dict_value, class_string=key_class_string).parse()) 

        return self.item_rp

class AudioCueOutputParser(outputsParser):
    pass

class VideoCueOutputParser(outputsParser):
    pass

class DmxCueOutputParser(outputsParser):
    pass

class DmxCueParser(CuemsScriptParser):
    def parse(self):
        Logger.debug(f"Parsing DmxCue with DmxCueParser, {self._class}, {self.init_dict}")
        self.item_gp = self._class(self.init_dict)
        return self.item_gp


class fade_profilesParser(GenericParser):
    """Parse ``fade_profiles`` wrapper content into a list of :class:`FadeProfile`."""

    def parse(self):
        if not self.init_dict or not isinstance(self.init_dict, dict):
            return []
        raw = self.init_dict.get('fade_profile')
        if raw is None:
            return []
        if not isinstance(raw, list):
            raw = [raw]
        return [
            item
            if isinstance(item, FadeProfile)
            else fade_profileParser(
                init_dict=item, class_string='fade_profile'
            ).parse()
            for item in raw
        ]


def _normalize_fade_parameters(raw):
    if raw is None:
        return None
    if isinstance(raw, dict):
        if 'parameter' in raw:
            raw = raw['parameter']
        else:
            return []
    if not isinstance(raw, list):
        raw = [raw]
    out = []
    for p in raw:
        if isinstance(p, FadeFunctionParameter):
            out.append(p)
            continue
        if isinstance(p, dict) and 'parameter' in p:
            p = p['parameter']
        out.append(FadeFunctionParameter(p))
    return out


class fade_profileParser(GenericParser):
    """Parse a single ``fade_profile`` element into a :class:`FadeProfile`."""

    def parse(self):
        d = {}
        for dict_key, dict_value in self.init_dict.items():
            if dict_key == 'parameters':
                d['parameters'] = _normalize_fade_parameters(dict_value)
            elif isinstance(dict_value, dict):
                sub_parser, sub_cls = self.get_parser_class(dict_key)
                d[dict_key] = sub_parser(
                    init_dict=dict_value, class_string=sub_cls
                ).parse()
            elif isinstance(dict_value, list):
                pcls, pstr = self.get_parser_class(dict_key)
                d[dict_key] = [
                    pcls(init_dict=li, class_string=pstr).parse() for li in dict_value
                ]
            else:
                d[dict_key] = self.str_to_value(dict_value, key = dict_key)
        return FadeProfile(d)


class NoneTypeParser():
    def __init__(self, init_dict, class_string):
        pass

    def parse(self):
        return None


# ---------------------------------------------------------------------------
# Deprecation surface (T028, FR-026b/c)
#
# Everything above this line is FROZEN. It is not edited by feature 004, only
# deprecated: the engine stops routing through it, and contract C8 proves no
# live path reaches it. Removal belongs to feature 007's migration.
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

#: **``CuemsParser`` is deliberately absent.** It is not a retired symbol: it
#: becomes the engine's delegating facade at T048 and stays a supported entry
#: point (Assumption 3a, FR-026d). It is also `cuems-editor`'s primary
#: JSON -> object path at five call sites, and contract C8 depends on its
#: silence — a warning here would fail the very test that proves the library no
#: longer calls its own deprecated code.
_FROZEN_PARSERS = (
    GenericDict,
    CuemsScriptParser,
    CueListParser,
    GenericParser,
    GenericSubObjectParser,
    CTimecodeParser,
    mediaParser,
    outputsParser,
    CuemsNodeDictParser,
    AudioCueOutputParser,
    VideoCueOutputParser,
    DmxCueOutputParser,
    DmxCueParser,
    fade_profilesParser,
    fade_profileParser,
    NoneTypeParser,
)

for _frozen in _FROZEN_PARSERS:
    deprecated_symbol(_MIGRATION)(_frozen)
del _frozen

# The type-guessing heuristic itself (FR-003). Deprecated on ``CuemsParser``
# even though the class is not, because the class survives and the heuristic
# must not: after the swap nothing in this library calls it, and this warning is
# what makes that checkable rather than asserted.
CuemsParser.str_to_value = deprecated_symbol(
    "schema-declared types; the engine no longer guesses"
)(CuemsParser.str_to_value)

# ``STRING_TYPED_KEYS`` has no call to hook: it is a ``frozenset`` read as a
# value, not invoked. It is deprecated in the same breath as ``str_to_value`` —
# the denylist exists only to protect the heuristic — but it cannot warn, and
# saying so here is better than implying a guarantee that is not there. Its
# retirement is recorded in the migration map instead.
