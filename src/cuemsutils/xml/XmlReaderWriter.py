""" For the moment it works with pip3 install xmlschema==1.2.2
 """
from os import path
from xmlschema import XMLSchema11, XMLSchemaConverter
from xml.etree.ElementTree import ElementTree

from deprecated import deprecated
from .CMLCuemsConverter import CMLCuemsConverter
from .Parsers import CuemsParser
from .XmlBuilder import XmlBuilder
from ..log import logged

@logged
def get_pkg_schema(schema_name: str):
    """Get the schema file from package resources"""
    schemas_dir = path.join(path.dirname(__file__), 'schemas')
    if not schema_name[len(schema_name)-4:] == '.xsd':
        schema_name = schema_name + '.xsd'
    schema = path.join(schemas_dir, schema_name)
    if not path.isfile(schema):
        raise FileNotFoundError(f"Schema file {schema_name} not found")
    return schema

class CuemsXml():
    def __init__(self, schema_name, xmlfile, namespace={'cms':'https://stagelab.coop/cuems/'}, xml_root_tag='CuemsProject'):
        # Needed to implement to_dict respecting array elements
        self.converter = CMLCuemsConverter
        self.namespace = namespace
        self.schema = schema_name
        self.xmlfile = xmlfile
        self.xml_root_tag = xml_root_tag
    
    @property
    def schema(self):
        return self._schema

    @schema.setter
    def schema(self, name):
        self._schema = get_pkg_schema(name)
        self.schema_object = XMLSchema11(
            self.schema,
            converter = self.converter
        )

    @property
    def xmlfile(self):
        return self._xmlfile

    @xmlfile.setter
    def xmlfile(self, path):
        self._xmlfile = path
            
    def validate(self):
        return self.schema_object.validate(self.xmlfile)

class XmlReaderWriter(CuemsXml):
    def write(self, xml_data: ElementTree):
        self.schema_object.validate(xml_data)
        xml_data.write(
            self.xmlfile,
            encoding = "utf-8",
            xml_declaration = True
        )

    def write_from_dict(self, project_dict):
        project_object = CuemsParser(project_dict).parse()
        self.write_from_object(project_object)

    def build_xml_from_object(self, project_object):
        """Build XML data from a project object"""
        xml_data = XmlBuilder(
            project_object,
            namespace=self.namespace,
            xsd_path=self.schema,
            xml_root_tag=self.xml_root_tag
        ).build()
        return xml_data

    def write_from_object(self, project_object):
        """Write a project object to an XML file"""
        xml_data = self.build_xml_from_object(project_object)
        self.write(xml_data)

    def validate_object(self, project_object):
        """Validate a project object against the schema"""
        xml_data = self.build_xml_from_object(project_object)
        return self.schema_object.validate(xml_data)

    def read(self, **kwargs):
        return self.schema_object.to_dict(
            self.xmlfile,
            validation = 'strict',
            strip_namespaces = False,
            **kwargs
        )

    def read_to_objects(self):
        xml_dict = self.read()
        return CuemsParser(xml_dict).parse()

@deprecated(
    reason="Use XmlReaderWriter instead",
    version="0.0.7"
)
class XmlWriter(XmlReaderWriter):
    pass

@deprecated(
    reason="Use XmlReaderWriter instead",
    version="0.0.7"
)
class XmlReader(XmlReaderWriter):
    pass
