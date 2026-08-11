""" For the moment it works with pip3 install xmlschema==1.1.2
 """

import os
import xml.etree.ElementTree as ET
from typing import Any

from ..helpers import strtobool
from ..log import Logger
from ..tools.CTimecode import CTimecode
from .mapper import read_config_document
from .validators import validate_custom_templates
from .xml_reader_writer import XmlReaderWriter


class Settings(XmlReaderWriter):
    """
    Settings class that extends XmlReaderWriter to handle configuration file operations.
    """
    def __init__(self, xmlfile, schema_name = 'settings', **kwargs):
      if 'xml_root_tag' not in kwargs:
        kwargs['xml_root_tag'] = "CuemsSettings"
      super().__init__(
          schema_name = schema_name,
          xmlfile = xmlfile,
          **kwargs
      )
      if not hasattr(self, 'main_key'):
        self.main_key = 'Settings'
      self.xml_dict = {}
      self.processed = {}
      self.loaded = False

      if self.schema is not None and self.xmlfile is not None:
          self.read()

    def get_dict(self) -> dict[str, Any]:
        if self.main_key == '':
            return self.xml_dict if isinstance(self.xml_dict, dict) else {}
        value = self.xml_dict.get(self.main_key) # type: ignore[index]
        if isinstance(value, dict):
            return value
        # If main_key value is not a dict (e.g., list), wrap it in a dict
        return {self.main_key: value} if value is not None else {}

    def backup(self):
        if os.path.isfile(self.xmlfile):
            Logger.info("File exist")
            try:
                os.rename(self.xmlfile, "{}.back".format(self.xmlfile))
            except OSError:
                Logger.error("Cannot create settings backup")
        else:
            Logger.error("Settings file not found")

    def read(self) -> None:
        """Read this configuration document (T053).

        Reader configuration **B** of the two FR-013 preserves:
        ``strip_namespaces=True``, explicit ``dict``/``list`` containers, and
        ``attr_prefix=''``. It differs from ``XmlReaderWriter.read`` — that is
        deliberate, load-bearing, and asserted by
        ``tests/contract/test_reader_configs.py``.

        Decoding runs on the same engine as the show-document path: the schema
        comes from the shared cache and the converter is ``CuemsConverter``,
        inherited from ``CuemsXml``. What these classes do **not** yet have is
        a model layer — the four of them hand back raw dicts, which is why
        their registry bindings are all ``GENERIC``. Giving configuration
        documents real objects is feature 006.
        """
        self.xml_dict = read_config_document(
            self.schema_object,
            self.xmlfile,
        )
        if (hasattr(self, 'process_xml_dict')):
            self.process_xml_dict() # type: ignore[attr-defined]
        self.loaded = True

    def data2xml(self, obj):
        xml_tree = ET.Element(self.main_key)
        self.xmldata = self.buildxml(xml_tree, obj)

    def buildxml(self, xml_tree, d): #TODO: clean variable names, simplify¿
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(k, str):
                    s = ET.SubElement(xml_tree, k)

                elif isinstance(k, (dict)):
                    s = ET.SubElement(xml_tree, type(k).__name__)
                    s.text = str(k)
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

class NetworkMap(Settings):
    """
    NetworkMap class that extends Settings to handle network map operations.
    """
    def __init__(self, xmlfile, schema_name = 'network_map', **kwargs):
        if not hasattr(self, 'main_key'):
            self.main_key = ''
        super().__init__(
            xmlfile,
            schema_name,
            xml_root_tag='CuemsNetworkMap',
            **kwargs
        )

    def get_node(self, uuid):
        out = None
        network_dict = self.get_dict()
        nodes_list = network_dict.get('node_list')
        for node_item in nodes_list:
            node = node_item.get('node')
            if node.get('uuid') == uuid:
                out = node
                break
        if not out:
            raise ValueError(f'Node with uuid {uuid} not found')
        return out

    @staticmethod
    def get_nodes_by_adoption(network_map_dict: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        nodes = []
        new_nodes = []

        if not network_map_dict:
            raise ValueError('No network map dictionary found')
        node_list = network_map_dict.get('node_list', [])
        if not node_list:
            raise ValueError('No node list found in network map dictionary')
        for node_item in node_list:
            if 'node' in node_item:
                # Convert boolean strings directly in the node_item structure
                node_item['node']['online'] = strtobool(node_item['node'].get('online', 'False'))
                node_item['node']['adopted'] = strtobool(node_item['node'].get('adopted', 'False'))

                # Append the node_item directly (it already has the wrapper structure)
                if node_item['node']['adopted']:
                    nodes.append(node_item)
                else:
                    new_nodes.append(node_item)

        return nodes, new_nodes

class ProjectMappings(Settings):
    """
    Mappings class that extends Settings to handle hardware mappings operations.
    """

    # Absorb float round-trip noise; mirrors cues.CueOutput._CONTAINMENT_EPS.
    _CONTAINMENT_EPS = 1e-6

    def __init__(self, xmlfile, schema_name = 'project_mappings', **kwargs):
        if not hasattr(self, 'main_key'):
            self.main_key = ''
        super().__init__(
            xmlfile,
            schema_name,
            xml_root_tag='CuemsProjectMappings',
            **kwargs
        )

    def get_node(self, uuid):
        out = None
        for node in self.processed['nodes']: # type: ignore[index]
            node = node['node']
            if node['uuid'] == uuid:
                out = node
                break
        if not out:
            raise ValueError(f'Node with uuid {uuid} not found')
        return out

    def process_xml_dict(self):
        self.processed = self.get_dict()
        self._validate_custom_templates()

    def _validate_custom_templates(self):
        """Delegate to the named T2 validators (T055, FR-017).

        The rules themselves live in :mod:`cuemsutils.xml.validators`, in a
        tier kept explicitly separate from schema-derived T1 validation. They
        stayed inline here for as long as this class was the only thing that
        needed them; naming them makes the boundary checkable — anything in
        that module is a rule XSD *cannot* express, and anything XSD can
        express does not belong there.

        Kept as a method rather than replaced by a direct call, because it is
        part of this class's surface and subclasses may override it.
        """
        validate_custom_templates(self.processed)

    def process_network_mappings(self, mappings):
        '''Temporary process instead of reviewing xml read and convert to objects'''
        # By now we need to correct the data structure from the xml
        # the converter is not getting what we really intended but we'll
        # correct it here by the moment
        temp_nodes = []

        Logger.info(f'Processing network mappings: {mappings}')

        for node in mappings['nodes']:
            temp_node = {}
            for section, contents in node['node'].items():
                if not isinstance(contents, list):
                    temp_node[section] = contents
                else:
                    temp_node[section] = {}
                    for item in contents:
                        for key, values in item.items():
                            temp_node[section][key] = []
                            if values:
                                for elem in values:
                                    for subkey, subvalue in elem.items():
                                        temp_node[section][key].append(subvalue)
            temp_nodes.append(temp_node)

        mappings['nodes'] = temp_nodes
        return mappings

class ProjectSettings(Settings):
    """
    ProjectSettings class that extends Settings to handle project settings operations and override system-wide settings.
    """
    def __init__(self, xmlfile, schema_name = 'project_settings', **kwargs):
        if not hasattr(self, 'main_key'):
            self.main_key = 'CuemsProjectSettings'
        super().__init__(
            xmlfile,
            schema_name,
            xml_root_tag='CuemsProjectSettings',
            **kwargs
        )
