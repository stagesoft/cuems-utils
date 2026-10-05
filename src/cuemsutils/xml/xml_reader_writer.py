""" For the moment it works with pip3 install xmlschema==1.2.2
 """
from xml.etree.ElementTree import ElementTree

from deprecated import deprecated

from .._deprecation import deprecated_symbol
from ..log import Logger, logged
from .converter import CuemsConverter
from .documents import get_pkg_schema as _get_pkg_schema
from .mapper import Mapper, build_document
from .schema import get_schema

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
        """Resolve the ``.xsd`` path and take the **cached** compiled schema.

        ``get_schema`` is keyed on ``(name, converter)`` and is what makes
        "schema load once per process" an implementation fact rather than an
        aspiration. This setter used to call ``XMLSchema11(...)`` directly, so
        every instance recompiled the XSD — and because the configuration path
        constructs one of these per call, that cost was paid per load rather
        than per process. Feature 013 identified it while profiling
        SC-PERF-001 and deliberately left it; feature 014 applies it, because
        014 edits the schemas and so has to measure them anyway.

        The converter is part of the cache key on purpose: ``XMLSchema11``
        stores it, and the two reader configurations need different ones, so a
        single-key cache would hand one configuration the other's converter.

        ``self._schema`` stays the absolute path — ``read()`` passes it as
        ``xsd_path`` and the engine keys its derivation on the bare name.
        """
        self._schema = get_pkg_schema(name)
        # Keyed on *this call's* name, not on ``self.schema_name``: nothing
        # reassigns this property today, but reading the attribute would hand a
        # reassignment the previous schema's compiled object, silently.
        self.schema_object = get_schema(name.removesuffix('.xsd'), self.converter)

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
        """Decode a payload and write it.

        Calls ``Mapper.decode_document`` directly (T061a). It used to go
        through ``CuemsParser``, which delegates to exactly this — so the
        result is unchanged and the hop is gone.

        The hop had to go **before** ``CuemsParser`` could be deprecated:
        contract C8 asserts that no internal caller invokes a deprecated
        symbol, so a library that both deprecates a name and calls it fails its
        own test. C8 is satisfied here, not amended.
        """
        self._write_object(Mapper(self.schema_name).decode_document(project_dict))

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

    # --- the private cores (feature 014) --------------------------------
    #
    # The four public methods below are deprecated, and two of them used to
    # call the other two. Contract C8 says no internal caller invokes a
    # deprecated symbol, so a library that both deprecates a name and calls it
    # fails its own test — the same reasoning that moved the ``CuemsParser``
    # hop out of ``write_from_dict`` in feature 004. The bodies move here and
    # every caller, deprecated or not, goes through these.

    def _raw_decode(self, **kwargs):
        """The document as ``xmlschema`` decodes it: **no version conversion**.

        This is what ``read()`` always did and the reason it is now deprecated.
        A document is decoded against the *current* schema with no step
        applied, so one written for an older version reaches a strict decode
        that refuses it. The public path (:meth:`CuemsScript.load_with_report`,
        :func:`ConfigBase.load_config_document`) converts in memory first;
        this does not.
        """
        Logger.info(f"Reading {self.schema_name} document {self.xmlfile}")
        return self.schema_object.to_dict(
            self.xmlfile,
            validation = 'strict',
            strip_namespaces = False,
            **kwargs
        )

    def _write_object(self, project_object):
        self.write(self.build_xml_from_object(project_object))

    # --- the deprecated surface (feature 014, X1) -----------------------

    @deprecated_symbol(
        "cuemsutils.cues.CuemsScript.CuemsScript.save",
        note=(
            "this path writes without applying a version conversion; the "
            "public save validates and reports"
        ),
    )
    def write_from_object(self, project_object):
        """Write a project object to an XML file"""
        self._write_object(project_object)

    def validate_object(self, project_object):
        """Validate a project object against the schema.

        **Deliberately NOT decorated here**, unlike its three neighbours above,
        and the first attempt at feature 014 got this wrong: a blanket
        ``deprecated_symbol`` pointing at ``CuemsScript.validate`` **regressed
        feature 013's FR-036**, which made this method's advice *per schema*
        because ``CuemsScript.validate`` builds a **show** document and so
        cannot validate a ``settings.xml`` at all. A consumer following that
        advice is sent somewhere that cannot work, with no reason to doubt it —
        013's UR-5 finding, and worse than no advice.

        The replacement depends on the **instance**, so it is decided at the
        call by ``_deprecation._per_instance_deprecated`` and wired in
        ``cuemsutils.xml.__init__``'s ``per_instance``. Decorating the method
        here would shadow that with a single wrong string.
        """
        return self.schema_object.validate(self.build_xml_from_object(project_object))

    @deprecated_symbol(
        "cuemsutils.cues.CuemsScript.CuemsScript.to_wire",
        note=(
            "the returned dict no longer contains the schemaLocation key, and "
            "this path applies **no version conversion** — a document written "
            "for an older schema version is refused here and converted in "
            "memory by the public load"
        ),
    )
    def read(self, **kwargs):
        """DEPRECATED — a raw schema decode, with no version conversion.

        **Deprecated by feature 014**, and the trigger is X1: retyping
        ``cms:BoolType`` to ``xs:boolean`` means a document carrying the old
        ``True``/``False`` text is refused by the current schema. The
        registered 1 -> 2 conversion rewrites it, but only on the **public**
        read path — this method has never applied a conversion, which was
        invisible while every schema change happened to be additive.

        So the narrowing is not new behaviour; it is an existing property that
        X1 made observable. Deprecating the method rather than teaching it to
        convert is the honest answer: 008 put conversion in the public path on
        purpose (D19/D21's three load outcomes are reported, which a raw decode
        cannot do), and this surface is removed at ``v0.1.1`` regardless.

        Use :meth:`cuemsutils.cues.CuemsScript.CuemsScript.to_wire` for a show
        document, or the ``ConfigManager`` accessors for a configuration one.
        """
        return self._raw_decode(**kwargs)

    @deprecated_symbol(
        "cuemsutils.cues.CuemsScript.CuemsScript.load",
        note=(
            "this path applies no version conversion; the public load converts "
            "in memory and returns a LoadReport saying what it did"
        ),
    )
    def read_to_objects(self):
        """DEPRECATED — read and decode, with no version conversion.

        Same narrowing as :meth:`read`, for the same reason: it decodes what
        ``_raw_decode`` returns, so a document written for an older schema
        version never reaches the mapper.
        """
        return Mapper(
            self.schema_name, document=self.xmlfile
        ).decode_document(self._raw_decode())

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
