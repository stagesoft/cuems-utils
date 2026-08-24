""" For the moment it works with pip3 install xmlschema==1.1.2
 """

import os
from typing import Any

from ..helpers import strtobool
from ..log import Logger
from ._deprecation import deprecated_symbol
from .mapper import Mapper, read_config_document
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
        inherited from ``CuemsXml``.

        **The result is now objects** (T049, FR-014). These four classes handed
        back raw nested dicts for as long as their registry bindings were all
        ``GENERIC``; feature 006 binds the twenty-two config types to
        ``cuemsutils.config`` models and routes the decoded dict through
        ``Mapper.decode_config``, which substitutes classes and changes nothing
        else — no coercion, no reshaping. See that method's docstring for why
        both of those are the config domain stating a fact about itself rather
        than the engine acquiring a mode.
        """
        # A missing file raises ``FileNotFoundError`` rather than
        # ``urllib.error.URLError``. Without the check ``xmlschema`` treats the
        # path as a URL, and the resulting error — an ``OSError`` subclass that
        # ``except FileNotFoundError`` does **not** catch, with a message about
        # "urlopen error" — is the wrong answer to "is there a config file?".
        #
        # A **schema** failure is deliberately *not* wrapped here. This class
        # is internal machinery (US4 makes it a deprecation shim), and its raw
        # verdicts are what ``tests/golden/outcomes.json`` pins document by
        # document. FR-014b's ``SchemaError`` belongs on the **accessor** — see
        # ``ConfigBase.load_base_settings`` and ``ConfigManager`` — which is
        # where contract C2 places it and where a consumer meets it.
        if not os.path.exists(self.xmlfile):
            raise FileNotFoundError(f'No such file: {self.xmlfile}')

        raw = read_config_document(self.schema_object, self.xmlfile)
        self.xml_dict = Mapper(self.schema_name).decode_config(raw)
        if (hasattr(self, 'process_xml_dict')):
            self.process_xml_dict() # type: ignore[attr-defined]
        self.loaded = True

    # ``data2xml`` / ``buildxml`` **deleted** (T056, D3).
    #
    # A ~35-line generic dict→ElementTree builder, on a class that has never
    # had a working write path: building XML from a settings dict raised
    # ``AttributeError`` inside the legacy ``XmlBuilder``, which is why the
    # config classes' byte-identity contract has always been the read dict
    # (C2) and never the written bytes. Nothing in this repository, in
    # cuems-engine, in cuems-editor or in cuems-nodeconf called either method.
    #
    # It is deleted rather than fixed because the replacement already exists
    # and is derived: ``Mapper.encode_xml`` builds from the schema, and the
    # config types are registry-bound model classes as of this feature. A
    # second, shape-guessing builder beside it is precisely the duplication
    # 004 and 006 exist to remove.

def _as_bool(val: Any) -> bool:
    """``val`` as itself if already ``bool``, else through ``strtobool`` (R7).

    ``get_nodes_by_adoption`` predates ``network_map`` running the adapter
    table and was written against the ``"True"``/``"False"`` strings
    ``cms:BoolType`` decodes to. It stays callable with either shape rather
    than only the new one, because Assumption 8 keeps this method available
    until feature 008 migrates its caller.
    """
    return val if isinstance(val, bool) else strtobool(val)


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
    @deprecated_symbol(
        f"{__name__}.NetworkMap.partition_by_adoption",
        note=(
            "the replacement returns node objects, not {'node': ...}-wrapped "
            "dicts, and does not mutate its argument"
        ),
    )
    def get_nodes_by_adoption(network_map_dict: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Deprecated (T083) — mutates its argument in place (FR-015's
        opposite), kept working until feature 008 migrates its
        ``cuems-engine`` caller (Assumption 8). See
        :meth:`partition_by_adoption` for the non-mutating replacement."""
        nodes = []
        new_nodes = []

        if not network_map_dict:
            raise ValueError('No network map dictionary found')
        node_list = network_map_dict.get('node_list', [])
        if not node_list:
            raise ValueError('No node list found in network map dictionary')
        for node_item in node_list:
            if 'node' in node_item:
                # ``network_map``'s adapter table (this feature, R1) now
                # decodes ``adopted``/``online`` as ``bool`` — so a caller may
                # hand this method either the pre-typing strings or the typed
                # values directly. ``strtobool`` only accepts ``str`` (research
                # R7); a ``bool`` is already the answer.
                node_item['node']['online'] = _as_bool(node_item['node'].get('online', 'False'))
                node_item['node']['adopted'] = _as_bool(node_item['node'].get('adopted', 'False'))

                # Append the node_item directly (it already has the wrapper structure)
                if node_item['node']['adopted']:
                    nodes.append(node_item)
                else:
                    new_nodes.append(node_item)

        return nodes, new_nodes

    @staticmethod
    def partition_by_adoption(network_map) -> tuple[tuple, tuple]:
        """Split a network map's nodes into ``(adopted, unadopted)`` (research R7, contract C6).

        The non-mutating replacement for :meth:`get_nodes_by_adoption`
        (Assumption 8 keeps that one available until feature 008 migrates its
        caller). Every node value in ``network_map`` is unchanged, field by
        field, before and after this call — it only reads ``adopted``,
        through the same tolerant :func:`_as_bool` conversion (a caller may
        still hold the pre-typing string shape), and never writes back.

        Args:
            network_map: a ``CuemsNetworkMapType`` (or a plain dict of the
                same shape) — whatever :attr:`ConfigManager.network_map`
                or :meth:`get_dict` returns.

        Returns:
            tuple[tuple[node, ...], tuple[node, ...]]: adopted nodes, then
            unadopted — bare node objects, not ``{"node": ...}`` wrappers
            (unlike the deprecated method, whose shape this does not carry
            across).

        Raises:
            ValueError: no network map, or no node list, exactly as
                :meth:`get_nodes_by_adoption`.
        """
        if not network_map:
            raise ValueError('No network map dictionary found')
        node_list = network_map.get('node_list', [])
        if not node_list:
            raise ValueError('No node list found in network map dictionary')

        adopted = []
        unadopted = []
        for node_item in node_list:
            candidate = node_item.get('node')
            if candidate is None:
                continue
            is_adopted = _as_bool(candidate.get('adopted', False))
            (adopted if is_adopted else unadopted).append(candidate)

        return tuple(adopted), tuple(unadopted)

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

    # ``process_network_mappings`` **deleted** (T056, D3).
    #
    # Its own docstring said what it was: *"Temporary process instead of
    # reviewing xml read and convert to objects"* — a hand-written reshaping of
    # the mappings dict, kept until the read path produced objects. It does
    # now (T049), and nothing called this method.
    #
    # It was also F15's **third** incompatible reading of the node mappings,
    # alongside the two unreachable ``check_mappings`` bodies deleted from
    # ``VideoCue`` and ``AudioCue``. All three are gone; the one live shape is
    # ``ConfigManager``'s, and ``cuemsutils.config.mappings`` states it.

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
