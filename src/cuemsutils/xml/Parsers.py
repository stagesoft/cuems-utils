from ..log import Logger
from ..helpers import strtobool, Uuid

from ..cues import *
from ..CTimecode import CTimecode
from ..cues.Cue import Cue
from ..cues.MediaCue import Media, region


PARSER_SUFFIX = 'Parser'
GENERIC_PARSER = 'GenericParser'
#TODO: XML_ROOT_TAG get from constants storage
XML_ROOT_TAG = 'CuemsScript'

class GenericDict(dict):
    pass

class CuemsParser():
    def __init__(self, init_dict):
        try:
            if next(iter(init_dict)) != XML_ROOT_TAG:
                root_value = init_dict[XML_ROOT_TAG]
                self.init_dict = {XML_ROOT_TAG: root_value}
                Logger.debug("Found root tag and is not the firs one, extracting")
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
                f"Could not find class {class_string}, reverting to generic parser class"
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

    def str_to_value(self, _string):
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
        parser_class, class_string = self.get_parser_class(
            self.get_first_key(self.init_dict)
        )
        return parser_class(
            init_dict = self.get_contained_dict(self.init_dict),
            class_string = class_string
        ).parse()

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
                    self.item_csp[k.lower()] = parser_class(init_dict=v, class_string=class_string).parse()                    
            else:
                v = self.str_to_value(v)
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
                    parser_class, unused_class_string = self.get_parser_class(self.get_first_key(cue))
                    item_obj = parser_class(init_dict=self.get_contained_dict(cue), class_string=self.get_first_key(cue)).parse()
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
                v = self.str_to_value(v)
                self.item_clp[k] = v
                
        return self.item_clp

class GenericParser(CuemsScriptParser): 
    def __init__(self, init_dict, class_string):
        self.init_dict = init_dict
        self.class_string = class_string
        self._class = self.get_class(class_string)
        self.item_gp = self._class()
        
    def parse(self):
        if self._class == GenericDict:
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
                elif isinstance(dict_value, list):
                    local_list = []
                    parser_class, class_string = self.get_parser_class(dict_key)
                    for list_item in dict_value:

                        item_obj = parser_class(init_dict=list_item, class_string=class_string).parse()
                        local_list.append(item_obj)
                    self.item_gp[dict_key] = local_list
                else:
                    dict_value = self.str_to_value(dict_value)
                    self.item_gp[dict_key] = dict_value

        return self.item_gp

class GenericSubObjectParser(GenericParser):
    def parse(self):
        self.item_gp = self._class(self.init_dict)
        return self.item_gp

class CTimecodeParser(GenericParser):  
    def parse(self):
        self.item_gp = self.init_dict
        return self.item_gp

class OutputsParser(GenericParser):
    def __init__(self, init_dict, class_string, parent_class=None):
        self.init_dict = init_dict

    def parse(self):
        for dict_key, dict_value in self.init_dict.items():
            self._class = self.get_class(dict_key)
            self.item_op = self._class(dict_value)

        return self.item_op

class regionsParser(GenericParser):
    def __init__(self, init_dict, class_string, parent_class=None):
        self.init_dict = init_dict
        self.class_string = class_string
        self._class = self.get_class(class_string)
        self.item_rp = self._class()
        
    def parse(self):
        for dict_key, dict_value in self.init_dict.items():
            key_parser_class, key_class_string = self.get_parser_class(dict_key)
            self.item_rp = key_parser_class(init_dict=dict_value, class_string=key_class_string).parse()

        return self.item_rp

class CuemsNodeDictParser(OutputsParser):
    def parse(self):
        self.item_rp = list()
        for item in self.init_dict:
            for dict_key, dict_value in item.items():
                key_parser_class, key_class_string = self.get_parser_class(dict_key)
                self.item_rp.append(key_parser_class(init_dict=dict_value, class_string=key_class_string).parse()) 

        return self.item_rp

class NoneTypeParser():
    def __init__(self, init_dict, class_string):
        pass

    def parse(self):
        return None
