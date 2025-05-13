""" For the moment it works with pip3 install xmlschema==1.1.2
 """

import xml.etree.ElementTree as ET
import xmlschema
import os

from cuemsutils.log import Logger
from cuemsutils.CTimecode import CTimecode
from cuemsutils.xml.CMLCuemsConverter import CMLCuemsConverter
from .xml.XmlReaderWriter import XmlWriter

SETTINGS_DIR = '/etc/cuems'
SETTINGS_FILE = 'settings.xml'
SETTINGS_PATH = os.path.join(SETTINGS_DIR, SETTINGS_FILE)

class Settings(XmlWriter):
    """
    Settings class that extends XmlWriter to handle configuration file operations.
    """
    def __init__(self, schema_name = 'settings', xmlfile = SETTINGS_PATH, *args, **kwargs):
      super().__init__(
          schema_name = schema_name,
          xmlfile = xmlfile,
          *args,
          **kwargs
      )
      self.loaded = False
    
      if self.schema is not None and self.xmlfile is not None:
          self.read()
    
    def __backup(self):
        if os.path.isfile(self.xmlfile):
            Logger.info("File exist")
            try:
                os.rename(self.xmlfile, "{}.back".format(self.xmlfile))
            except OSError:
                Logger.error("Cannot create settings backup")
        else:
            Logger.error("Settings file not found")

    def read(self):
        xml_dict = self.schema_object.to_dict(
            self.xmlfile,
            dict_class = dict,
            list_class = list,
            validation = 'strict',
            strip_namespaces = True,
            attr_prefix = ''
        )

        super().__init__(xml_dict)
        self.loaded = True
        return self

    def data2xml(self, obj):
        xml_tree = ET.Element(type(obj).__name__)
        self.xmldata = self.buildxml(xml_tree, obj)

    def buildxml(self, xml_tree, d): #TODO: clean variable names, simplify¿
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(k, str):
                    s = ET.SubElement(xml_tree, k)
                    
                elif isinstance(k, (dict)):
                    s = ET.SubElement(xml_tree, type(k).__name__)
                    s.text = k
                elif isinstance(k, (int, float)):
                    s = ET.SubElement(xml_tree, type(v).__name__, id=str(k))
                    if not isinstance(v, dict):
                        s.text =str(v)
                else:
                    s = ET.SubElement(xml_tree, type(k).__name__)
                
                if isinstance(v, (type(None), CTimecode, dict, list, tuple, int, float, str)): #TODO: filter without using explicit classes (like CTimecode)
                    self.buildxml(s, v)
        elif isinstance(d, tuple) or isinstance(d, list):
            for v in d:
                s = ET.SubElement(xml_tree, type(v).__name__)
                self.buildxml(s, v)
        elif isinstance(d, str):
            xml_tree.text = d
        elif isinstance(d, (float, int)):
      #  elif type(d) is int:
            xml_tree.text = str(d)
        else:
            s = ET.SubElement(xml_tree, type(d).__name__)
            self.buildxml(s, str(d))
        return xml_tree
