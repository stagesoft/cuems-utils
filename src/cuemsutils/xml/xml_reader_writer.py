""" For the moment it works with pip3 install xmlschema==1.2.2
 """
from xml.etree.ElementTree import ElementTree

from deprecated import deprecated
from xmlschema import XMLSchema11

from ..log import Logger, logged
from .converter import CuemsConverter
from .documents import get_pkg_schema as _get_pkg_schema
from .mapper import build_document
from .Parsers import CuemsParser

# Resolved in ``documents`` now, so that module can stay the one place the
# schema path is computed while ``XmlReaderWriter`` becomes a shim over it
# (US4). Re-exported under its old name because consumers — and
# ``xml/XmlReaderWriter.py``'s deprecated path — import it from here.
get_pkg_schema = logged(_get_pkg_schema)

class CuemsXml():
    def __init__(self, schema_name, xmlfile, namespace={'cms':'https://stagelab.coop/cuems/'}, xml_root_tag='CuemsProject'):
        # Decoding goes through the D5 converter, which preserves the
        # repeated-element shape the UI payload depends on (FR-014, C5).
        self.converter = CuemsConverter
        # Retained unresolved: ``self.schema`` is the absolute .xsd path, and
        # the engine keys its derivation and registry on the bare name.
        self.schema_name = schema_name.removesuffix('.xsd')
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
        # INFO is declared at the level of XML file access -- read, write,
        # validate (FR-033). Everything below this level is DEBUG or lower, so
        # the record count scales with files touched rather than with cues: a
        # 1000-cue script is one file and stays one record.
        Logger.info(f"Validating {self.schema_name} document {self.xmlfile}")
        return self.schema_object.validate(self.xmlfile)

class XmlReaderWriter(CuemsXml):
    def write(self, xml_data: ElementTree):
        Logger.info(f"Writing {self.schema_name} document {self.xmlfile}")
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
        """Build XML data from a project object, via the schema-derived engine.

        **The swap** (T047). Element order, cardinality and scalar conversion
        now come from the XSD instead of from ``XmlBuilder``'s dict iteration
        plus its hardcoded ``master_vol``/``opacity`` branch. The serializer is
        untouched — stdlib ``ElementTree``, same declaration, same spelling —
        because changing it would change every byte (R10).
        """
        return build_document(
            project_object,
            schema_name=self.schema_name,
            namespace=self.namespace,
            xsd_path=self.schema,
            xml_root_tag=self.xml_root_tag,
        )

    def write_from_object(self, project_object):
        """Write a project object to an XML file"""
        xml_data = self.build_xml_from_object(project_object)
        self.write(xml_data)

    def validate_object(self, project_object):
        """Validate a project object against the schema"""
        xml_data = self.build_xml_from_object(project_object)
        return self.schema_object.validate(xml_data)

    def read(self, **kwargs):
        Logger.info(f"Reading {self.schema_name} document {self.xmlfile}")
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
