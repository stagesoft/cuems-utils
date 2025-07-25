from enum import Enum
from xml.etree.ElementTree import Element, ElementTree, SubElement, register_namespace

from .Parsers import GenericDict
from ..helpers import as_cuemsdict
from ..tools.Uuid import Uuid
from ..log import Logger

PARSER_SUFFIX = 'XmlBuilder'
GENERIC_BUILDER = 'GenericCueXmlBuilder'

SCHEMA_INSTANCE_URI = 'http://www.w3.org/2001/XMLSchema-instance'
# VALUE_TYPES = (str, bool, int, float, Enum)
VALUE_TYPES = (str, bool, int, float, Enum, Uuid)

## "<target /> | <target><Uuid>sadqaweasd-as-das-dasd</Uuid></target> | <uuid><Uuid>asdas-das-da-sd-asd</Uuid></uuid>"

class XmlBuilder():
    def __init__(self, _object, namespace, xsd_path, xml_tree = None, xml_root_tag='CuemsProject'):
        self._object = _object
        self.xml_tree = xml_tree
        self.xml_root_tag = xml_root_tag
        self.class_name = type(_object).__name__
        self.xsd_path = xsd_path
        self.namespace =  namespace
        if self.namespace:
            register_namespace(next(iter(self.namespace)), next(iter(self.namespace.values())))

    def get_builder_class(self, _object):
        object_class_name = type(_object).__name__
        builder_class_name = object_class_name + PARSER_SUFFIX
        try:
            builder_class = globals()[builder_class_name]
        except KeyError as err:
            #logger.debug("Could not find class {0}, reverting to generic builder class".format(err))
            builder_class = globals()[GENERIC_BUILDER]
        return builder_class

    def build(self):
        #xml_root = Element(f'{{{next(iter(self.namespace.values()))}}}CuemsProject')
        xml_root = Element(f'{{{next(iter(self.namespace.values()))}}}{self.xml_root_tag}')
        xml_root.attrib= {f'{{{SCHEMA_INSTANCE_URI}}}schemaLocation': next(iter(self.namespace.values())) + " " + self.xsd_path}   
        builder_class = self.get_builder_class(self._object)
        self.xml_tree = builder_class(self._object, xml_tree = xml_root).build()
        self.xml_tree = ElementTree(self.xml_tree)
        return self.xml_tree

class CuemsScriptXmlBuilder(XmlBuilder):
    def __init__(self, _object, xml_tree):
        self._object = _object
        self.xml_tree = xml_tree
        self.class_name = type(_object).__name__

    def build(self):
        cue_element = SubElement(self.xml_tree, self.class_name)
        for key, value in self._object.items():
            if key == "CueList":
                _ = CueListXmlBuilder(value, xml_tree = cue_element).build()
                continue
            cue_subelement = SubElement(cue_element, str(key))
            if isinstance(value, VALUE_TYPES):
                cue_subelement.text = str(value)
            elif isinstance(value, GenericDict):
                cue_subelement = SubElement(cue_element, str(key))
                for sub_key, sub_value in value.items():
                    sub_dict_element = SubElement(cue_subelement, str(sub_key))
                    sub_dict_element.text = str(sub_value)
            elif not isinstance(value, (type(None))):
                builder_class = self.get_builder_class(value)
                sub_object_element = builder_class(value, xml_tree = cue_subelement).build()
        return self.xml_tree
    
class CuemsNodeDictXmlBuilder(CuemsScriptXmlBuilder):
    def build(self):
        cue_element = SubElement(self.xml_tree, self.class_name)
        for value in self._object.values():

                builder_class = self.get_builder_class(value)
                sub_object_element = builder_class(value, xml_tree = cue_element).build()
        return self.xml_tree

class CueListXmlBuilder(CuemsScriptXmlBuilder):
    def build(self):
        cuelist_element = SubElement(self.xml_tree, self.class_name)
        for key, value in self._object.items():
            cue_subelement = SubElement(cuelist_element, str(key))          
            if isinstance(value, VALUE_TYPES):
                cue_subelement.text = str(value)
            elif isinstance(value, (type(None))):
                pass
            elif isinstance(value, list):
                for cuelist_item in value:
                    builder_class = self.get_builder_class(cuelist_item)
                    sub_object_element = builder_class(cuelist_item, xml_tree = cue_subelement).build()
            else:
                builder_class = self.get_builder_class(value)
                sub_object_element = builder_class(value, xml_tree = cue_subelement).build()
        return self.xml_tree
  
class GenericCueXmlBuilder(CuemsScriptXmlBuilder):
    def build(self):
        Logger.info("Building generic cue with:")
        Logger.info(f"{self.class_name} and {self._object}")
        if self.class_name == "dict" or self.class_name == "CuemsDict":
            Logger.info("dict class recieved")
            sub_element = as_cuemsdict(self._object)
            sub_element.build(self.xml_tree)  # type: ignore[attr-union]
            return
        cue_element = SubElement(self.xml_tree, self.class_name)
        for key, value in self._object.items():
            if isinstance(value, VALUE_TYPES):
                cue_subelement = SubElement(cue_element, str(key))
                cue_subelement.text = str(value)
            elif isinstance(value, (type(None))):
                cue_subelement = SubElement(cue_element, str(key))
            elif isinstance(value, list):
                cue_subelement = SubElement(cue_element, str(key))
                for list_item in value:
                    builder_class = self.get_builder_class(list_item)
                    sub_object_element = builder_class(list_item, xml_tree = cue_subelement).build()
            elif isinstance(value, GenericDict):
                cue_subelement = SubElement(cue_element, str(key))
                for sub_key, sub_value in value.items():
                    sub_dict_element = SubElement(cue_subelement, str(sub_key))
                    sub_dict_element.text = str(sub_value)
            else:
                cue_subelement = SubElement(cue_element, str(key))
                builder_class = self.get_builder_class(value)
                sub_object_element = builder_class(value, xml_tree = cue_subelement).build()

class DmxSceneXmlBuilder(CuemsScriptXmlBuilder):
 
    def build(self):
        cue_element = SubElement(self.xml_tree, self.class_name)
        universe_list = list(self._object.items())
        for universe in universe_list:
            builder_class = self.get_builder_class(universe[1])
            sub_object_element = builder_class(universe, xml_tree = cue_element).build()

class DmxUniverseXmlBuilder(CuemsScriptXmlBuilder):
        
    def build(self):
        cue_element = SubElement(self.xml_tree, type(self._object[1]).__name__, id=str(self._object[0]))
        channel_list = list(self._object[1].items())
        for channel in channel_list:
            builder_class = self.get_builder_class(channel[1])
            sub_object_element = builder_class(channel, xml_tree = cue_element).build()
    
class DmxChannelXmlBuilder(CuemsScriptXmlBuilder):
    def build(self):
        cue_element = SubElement(self.xml_tree, type(self._object[1]).__name__, id=str(self._object[0]))
        cue_element.text = str(self._object[1])

class GenericSimpleSubObjectXmlBuilder(CuemsScriptXmlBuilder):
    def build(self):
        cue_element = SubElement(self.xml_tree, self.class_name)
        cue_element.text = str(self._object)

class GenericComplexSubObjectXmlBuilder(CuemsScriptXmlBuilder):
    def build(self):
        if isinstance(self._object, dict):
            for key, value in self._object.items():
                if isinstance(value, VALUE_TYPES):
                    sub_dict_element = SubElement(self.xml_tree, str(key))
                    sub_dict_element.text = str(value)
                elif isinstance(value, (type(None))):
                    sub_dict_element = SubElement(self.xml_tree, str(key))
                elif isinstance(value, dict):
                    sub_dict_element = SubElement(self.xml_tree, str(key))
                    self.recurser(value, sub_dict_element)
                elif isinstance(value, list):
                    sub_dict_element = SubElement(self.xml_tree, str(key))
                    self.recurser(value, sub_dict_element)

    def recurser(self, group, xml_tree):
        if isinstance(group, dict):
            for key, value in group.items():
                if isinstance(value, VALUE_TYPES):
                    cue_subelement = SubElement(xml_tree, key)
                    cue_subelement.text = str(value)
                elif isinstance(value, (type(None))):
                    cue_subelement = SubElement(xml_tree, key)
                elif isinstance(value, dict):
                    cue_subelement = SubElement(xml_tree, key)
                    self.recurser(value, cue_subelement)
        elif isinstance(group, list):
            for item in group:
                if isinstance(item, dict):
                    self.recurser(item, xml_tree)

class CTimecodeXmlBuilder(GenericSimpleSubObjectXmlBuilder):
    pass

class MediaXmlBuilder(GenericComplexSubObjectXmlBuilder):
    def build(self):
        if isinstance(self._object, dict):
            for key, value in self._object.items():
                if isinstance(value, VALUE_TYPES):
                    cue_subelement = SubElement(self.xml_tree, key)
                    cue_subelement.text = str(value)
                elif isinstance(value, (type(None))):
                    cue_subelement = SubElement(self.xml_tree, key)
                elif isinstance(value, dict):
                    cue_subelement = SubElement(self.xml_tree, key)
                    self.recurser(value, cue_subelement)
                elif isinstance(value, list):
                    cue_subelement = SubElement(self.xml_tree, key)
                    for list_item in value:
                        builder_class = self.get_builder_class(list_item)
                        sub_object_element = builder_class(list_item, xml_tree =cue_subelement).build()

class UI_propertiesXmlBuilder(GenericComplexSubObjectXmlBuilder):
    pass

class OutputsXmlBuilder(GenericComplexSubObjectXmlBuilder):
    def build(self):
        if isinstance(self._object, dict):
            for key, value in self._object.items():
                if isinstance(value, VALUE_TYPES):
                    sub_dict_element = SubElement(self.xml_tree, str(key))
                    sub_dict_element.text = str(value)
                elif isinstance(value, (type(None))):
                    sub_dict_element = SubElement(self.xml_tree, str(key))
                elif isinstance(value, dict):
                    sub_dict_element = SubElement(self.xml_tree, str(key))
                    self.recurser(value, sub_dict_element)
                elif isinstance(value, list):
                    sub_dict_element = SubElement(self.xml_tree, str(key))
                    for item in value:
                        self.recurser(item, sub_dict_element)
        
        return self.xml_tree

    def recurser(self, group, xml_tree):
        if isinstance(group, dict):
            for key, value in group.items():
                if isinstance(value, VALUE_TYPES):
                    output_subelement = SubElement(xml_tree, key)
                    output_subelement.text = str(value)
                elif isinstance(value, (type(None))):
                    output_subelement = SubElement(xml_tree, key)
                elif isinstance(value, dict):
                    output_subelement = SubElement(xml_tree, key)
                    self.recurser(value, output_subelement)
                elif isinstance(value, list):
                    for item in value:
                        output_subelement = SubElement(xml_tree, key)
                        self.recurser(item, output_subelement)
        elif isinstance(group, list):
            for item in group:
                if isinstance(item, VALUE_TYPES):
                    xml_tree.text = str(item)
                elif isinstance(item, dict):
                    self.recurser(item, xml_tree)
        elif isinstance(group, VALUE_TYPES):
            xml_tree.text = str(group)

class CueOutputsXmlBuilder(GenericComplexSubObjectXmlBuilder):

    def build(self):
        cue_element = SubElement(self.xml_tree, self.class_name)

        if isinstance(self._object, dict):
            

            for key, value in self._object.items():
                if isinstance(value, VALUE_TYPES):
                    cue_subelement = SubElement(cue_element, key)
                    cue_subelement.text = str(value)
                elif isinstance(value, (type(None))):
                    cue_subelement = SubElement(cue_element, key)
                elif isinstance(value, dict):
                    cue_subelement = SubElement(cue_element, key)
                    self.recurser(value, cue_subelement)
                elif isinstance(value, list):
                    cue_subelement = SubElement(cue_element, key)
                    self.recurser(value, cue_subelement)

        else:   
            cue_element.text = str(self._object)

class AudioCueOutputXmlBuilder(CueOutputsXmlBuilder):
    pass

class VideoCueOutputXmlBuilder(CueOutputsXmlBuilder):
    pass

class DmxCueOutputXmlBuilder(CueOutputsXmlBuilder):
    pass

class NoneTypeXmlBuilder(GenericSimpleSubObjectXmlBuilder): # TODO: clean, not need anymore? 
    pass
