from os import path
from typing import Any

from .ConfigBase import ConfigBase, load_config_document
from ..log import Logger, logged
# The concrete module, not the package root — see ConfigBase.
from ..xml.settings import NetworkMap, ProjectMappings, ProjectSettings

CUEMS_CONF_PATH = '/etc/cuems/'

#: The three device sections a node can carry, in ``NodeType``'s schema order.
#:
#: Named rather than discovered, and that is the point of T051: the walk that
#: built ``node_hw_outputs`` used to iterate every key of the node mapping and
#: test ``isinstance(content, list)`` to decide which ones were devices. Which
#: keys are devices is stated by ``project_mappings.xsd``.
_DEVICE_SECTIONS = ('audio', 'video', 'dmx')

#: The accessors whose value is a config **object** and can therefore project
#: itself (T056b). The scalar accessors are excluded because a ``str`` has no
#: wire form distinct from itself.
_PROJECTABLE_SECTIONS = frozenset({
    'settings',
    'network_map',
    'node_network_map',
    'mappings',
    'node_mappings',
    'node_conf',
    'project_mappings',
    'project_node_mappings',
})


def _hw_name(put) -> str:
    """The hardware identity of a port — ``mapped_to``, or ``name``.

    ``<name>`` is a human-readable label; ``<mapped_to>`` is the real target
    (the JACK port for audio, the DRM connector for video). Legacy entries
    carry no mappings, so ``name`` is the fallback.

    **One definition, both call sites**, and that is the point rather than
    tidiness. ``load_net_and_node_mappings`` derived this to build
    ``node_hw_outputs``; ``check_project_mappings`` compared a bare ``name``
    against that same list. On the vendored fixture the node advertises
    ``salida_001`` (a ``mapped_to``) while the port is named ``0``, so the two
    could never agree — and nobody noticed, because the comparison sat behind
    an ``isinstance(contents, dict)`` guard over a value that is a list and
    therefore never ran. Waking the check up without also fixing the
    comparison would reject every valid project.
    """
    mappings = put.get('mappings') or []
    return mappings[0]['mapped_to'] if mappings else put['name']


def _unwrap_put(port):
    """One port, from the ``{"output": {...}}`` wrapper the document carries.

    The wrapper's key is the element name — ``output`` or ``input`` — and the
    body is the port. Config decoding preserves that wrapper rather than
    collapsing it, because ``cuems-engine`` reads it and this feature does not
    edit consumer repositories; see ``Mapper.decode_config``.

    A bare port (no wrapper) is accepted too, so the accessor keeps working if
    a future feature does collapse it.
    """
    if isinstance(port, dict) and len(port) == 1:
        only = next(iter(port.values()))
        if isinstance(only, dict):
            return only
    return port

class ConfigManager(ConfigBase):
    def __init__(self, config_dir: str = CUEMS_CONF_PATH, load_all: bool = True):
        """
        ConfigManager constructor.
        This class is responsible for loading the configuration files and providing
        the configuration data to the rest of the application.

        It also provides methods to check the project files and to load them on demand.

        If load_all is True, the configuration files will be loaded and the configuration
        will be available for the rest of the application on object initialization.
        If load_all is False, the configuration will be loaded on demand.

        Base configuration directory is set to /etc/cuems/ by default.
        If the environment variable CUEMS_CONF_PATH is set, it will be used instead.
        If config_dir parameter is set, it will override the default value.

        Specifically, base configuration directory precedence is:
        - Environment variable CUEMS_CONF_PATH
        - config_dir parameter
        - /etc/cuems/ (i.e. CUEMS_CONF_PATH constant value) (default value)

        Args:
            config_dir (str): The directory containing the configuration files.
            load_all (bool): Whether to load all the configuration files.

        Raises:
            Exception: If the configuration files are not found.
        """
        # Initialize with default values
        self.project_name = ''
        self.using_default_mappings = False
        self.network_map = {}
        self.network_mappings = {}
        self.node_mappings = {}
        self.node_hw_outputs = {
            'audio_inputs':[],
            'audio_outputs':[],
            'video_inputs':[],
            'video_outputs':[],
            'dmx_inputs':[],
            'dmx_outputs':[]
        }
        super().__init__(config_dir)

        if load_all:
            self.load_config()

    @property
    def network_map(self):
        """The whole network map — every node the controller knows about.

        Returns:
            cuemsutils.config.network_map.CuemsNetworkMapType: a declared-field
            object (FR-014), not a raw nested dict. Its ``node_list`` is a list
            of ``{"node": <node>}`` wrappers, and the wrapper is **kept** —
            ``cuems-engine`` iterates it in that shape and this feature does
            not edit consumer repositories.

        Raises:
            AttributeError: before :meth:`load_config` has run.
        """
        return self._network_map

    @network_map.setter
    def network_map(self, value: dict[str, Any]):
        self._network_map = value

    @property
    def node_network_map(self):
        """**This** node's entry in the network map, resolved by uuid.

        Returns:
            cuemsutils.config.network_map.node: identity fields for this node
            (also reachable as ``cuemsutils.tools.NodeList.node``, its public
            path). ``network_map`` is the one config schema that runs the
            adapter table (feature 007, research R1): ``node_role`` is a
            ``NodeRole``, ``adopted``/``online`` are ``bool``, and ``uuid`` is
            a ``Uuid`` (or raw text if unparseable). The other three config
            schemas' ``cms:BoolType`` fields still decode as the strings
            ``"True"``/``"False"`` — that exception is per schema, declared on
            the registry, not a package-wide rule (see ``config/base.py``).

        Raises:
            AttributeError: before :meth:`load_network_map` has run.
            ValueError: if no node in the map carries this node's uuid.
        """
        return self._node_network_map
    
    @node_network_map.setter
    def node_network_map(self, value: NetworkMap | dict):
        if isinstance(value, NetworkMap):
            self._node_network_map = value.get_node(self.node_uuid)
        else:
            self._node_network_map = value

    @property
    def mappings(self):
        """The system-wide hardware mappings — every node's ports.

        From the project's ``mappings.xml`` when one exists, and from
        ``default_mappings.xml`` otherwise.

        Returns:
            cuemsutils.config.mappings.CuemsProjectMappingsType: a
            declared-field object (FR-014). Each level of the nesting — device,
            port group, port, mapping — is a named type, which is what let the
            five-level rediscovery walk in
            :meth:`load_net_and_node_mappings` be deleted (T051).

        Raises:
            AttributeError: before :meth:`load_config` has run.
        """
        return self._mappings

    @mappings.setter
    def mappings(self, value: dict[str, Any]):
        self._mappings = value
    
    @property
    def node_mappings(self):
        """**This** node's hardware mappings, resolved by uuid.

        Returns:
            cuemsutils.config.mappings.NodeType: audio, video and dmx sections,
            each a list of port groups. Distinct from
            ``network_map``'s ``NodeType``, which describes node *identity*
            rather than node *mappings* — two schemas, two types, two classes.

        Raises:
            AttributeError: before :meth:`load_config` has run.
            ValueError: if the mappings name no node with this uuid.
        """
        return self._node_mappings

    @node_mappings.setter
    def node_mappings(self, value: ProjectMappings | dict[str, Any]):
        if isinstance(value, ProjectMappings):
            self._node_mappings = value.get_node(self.node_uuid)
        else:
            self._node_mappings = value

    @logged
    def load_config(self) -> None:
        """
        Loads the system configuration.
        """
        # Initialize with empty values
        self.network_map = {}
        self.network_mappings = {}
        self.node_mappings = {}
        self.node_hw_outputs = {
            'audio_inputs':[],
            'audio_outputs':[],
            'video_inputs':[],
            'video_outputs':[],
            'dmx_inputs':[],
            'dmx_outputs':[]
        }

        self.set_dir_hierarchy()
        self.load_network_map()
        self.load_net_and_node_mappings()

    def load_network_map(self):
        """
        Loads the network map from the base configuration file.
        """
        netmap = load_config_document(
            NetworkMap, self.conf_path('network_map.xml'), 'network_map'
        )
        self.network_map = netmap.get_dict()
        self.node_network_map = netmap

    def save_network_map(self, path: str | None = None) -> None:
        """Write the current ``network_map`` back to disk (research R6).

        A thin façade over :meth:`cuemsutils.config.network_map.CuemsNetworkMapType.save`
        — validates (T1), then writes atomically. ``path`` defaults to this
        instance's own ``network_map.xml``, so the common case
        (``manager.save_network_map()``) writes back where :meth:`load_network_map`
        read from.

        Args:
            path (str | None): where to write. Defaults to
                ``self.conf_path('network_map.xml')``.

        Raises:
            SchemaError: the in-memory map does not match ``network_map.xsd``
                — a role value outside the enumeration, most commonly.
            AttributeError: before :meth:`load_network_map` has run.
        """
        self.network_map.save(path or self.conf_path('network_map.xml'))

    def save_settings(self, path: str | None = None) -> None:
        """Write the system-wide ``settings`` back to disk (feature 008, T035).

        Symmetric with :meth:`save_network_map`. ``path`` defaults to where
        :meth:`load_base_settings` (run by ``__init__``) read from.

        Args:
            path (str | None): where to write. Defaults to
                ``self.conf_path('settings.xml')``.

        Raises:
            SchemaError: the in-memory settings do not match ``settings.xsd``.
            AttributeError: before construction has run (``_settings_document``
                is set unconditionally by ``load_base_settings``, so this can
                only happen mid-construction).
        """
        self._settings_document.save(path or self.conf_path('settings.xml'))

    def load_net_and_node_mappings(self):
        """
        Loads the network and node mappings.
        """
        try:
            mappings_file = self.project_path(self.project_name, 'mappings.xml')
        except FileNotFoundError as e:
            mappings_file = self.conf_path('default_mappings.xml')

        project_mappings = load_config_document(
            ProjectMappings, mappings_file, 'project_mappings'
        )
        self.mappings = project_mappings.processed # type: ignore[attr-defined]

        self.node_mappings = project_mappings.get_node(self.node_conf['uuid'])
        Logger.debug(f"Node uuid is: {self.node_conf['uuid']}")

        # Build node_hw_outputs: the physical port name (mapped_to) is what the
        # engine needs (e.g. the JACK port for audio, DRM connector for video).
        # <name> is a human-readable label; <mapped_to> is the real target.
        # Fall back to <name> for legacy entries that have no mappings.
        # e.g: node_hw_outputs["audio_outputs"] = ["system:playback_1", "system:playback_2"]
        #
        # **Compensation #2, deleted** (T051, FR-016). This was five levels of
        # ``for k, v in something.items()`` — ``content`` → ``port_type_dict``
        # → ``port_types`` → ``port`` → ``port_type_content`` — with a variable
        # name at each level that named nothing, because nothing stated the
        # shape.
        #
        # The nesting has **not** gone and is not meant to: a node has devices,
        # a device has port groups, a group has ports, a port has mappings, and
        # that is what the document says. What has gone is rediscovering it by
        # iteration. Each level below is addressed by the name the schema gives
        # it, so a reader can check the code against ``project_mappings.xsd``
        # instead of against a sample document.
        for section in _DEVICE_SECTIONS:
            device_groups = self.node_mappings.get(section)
            if not isinstance(device_groups, list):
                # Absent (``<dmx />`` decodes to None) or scalar. Not an error:
                # every device element is ``minOccurs="0"``.
                continue
            for group in device_groups:
                for direction, ports in group.items():
                    for port in ports:
                        self.node_hw_outputs[f'{section}_{direction}'].append(
                            _hw_name(_unwrap_put(port))
                        )

        Logger.debug(f"Node hardware outputs are: {self.node_hw_outputs}")

    @logged
    def load_project_config(self, project_uname: str) -> None:
        """
        Loads the project configuration.

        Args:
            project_uname (str): The name of the project.
        """
        ## Initialize with empty values
        self.project_conf = {}
        self.project_mappings = {}
        self.project_node_mappings = {}
        self.project_default_outputs = {}
        self._project_settings_document = None

        self.project_name = project_uname

        self.load_project_settings(project_uname)
        self.load_project_mappings(project_uname)

    def load_project_settings(self, project_uname: str):
        """
        Loads the project settings from the project file.
        """
        try:
            settings_path = self.project_path(project_uname, 'settings.xml')
            conf = load_config_document(
                ProjectSettings, settings_path, 'project_settings'
            )
        except FileNotFoundError:
            Logger.info(
                f'Project {project_uname} settings not found. Keeping default settings.'
            )
            return

        # **Compensation #1, deleted** (T050, FR-016).
        #
        # This used to flatten a list of single-key dicts into one dict by
        # hand, key by key, because nothing stated what a project setting
        # looked like. ``project_settings.xsd`` always did — ``SettingType`` is
        # a name/value pair — and ``cuemsutils.config.settings.SettingType``
        # now says so in Python too.
        #
        # Recorded rather than glossed: the loop was **already unreachable**.
        # ``ProjectSettings.main_key`` is ``'CuemsProjectSettings'``, but the
        # decoded dict is the root element's *content*, so ``get_dict()`` looks
        # up a key that is never present and returns ``{}`` — and a loop over
        # ``{}`` does nothing. So this deletion cannot change behaviour, and
        # the compensation it removes is the *second* fossil in this file
        # rather than a live one. The ``main_key`` mismatch is a separate
        # latent defect: fixing it would change ``project_conf`` from ``{}`` to
        # the settings the document carries, which is a behaviour change no
        # requirement in this feature enumerates. Left alone deliberately.
        self.project_conf = conf.get_dict()
        # The root object (feature 008, T035) — ``conf.get_dict()`` is always
        # ``{}`` (the ``main_key`` mismatch above), so ``save_project_settings``
        # needs the object ``load_config_document`` actually decoded, not that.
        self._project_settings_document = conf.xml_dict

        Logger.info(f'Project {project_uname} settings loaded')

    def save_project_settings(self, project_uname: str, path: str | None = None) -> None:
        """Write a project's ``settings.xml`` back to disk (feature 008, T035).

        Args:
            project_uname (str): the project whose settings to write.
            path (str | None): where to write. Defaults to
                ``self.project_path(project_uname, 'settings.xml')``.

        Raises:
            SchemaError: the in-memory settings do not match
                ``project_settings.xsd``.
            AttributeError: before :meth:`load_project_settings` has loaded a
                document for this project (``_project_settings_document`` is
                ``None`` until then).
        """
        self._project_settings_document.save(
            path or self.project_path(project_uname, 'settings.xml')
        )

    def load_project_mappings(self, project_uname: str):
        """
        Loads the project mappings from the project file.
        """
        try:
            mappings_path = self.project_path(project_uname, 'mappings.xml')
            project_mappings = load_config_document(
                ProjectMappings, mappings_path, 'project_mappings'
            )
            self.project_mappings = project_mappings.processed
            try:
                self.project_node_mappings = project_mappings.get_node(self.node_uuid)
            except ValueError:
                Logger.warning(
                    f'No mappings assigned for this node in project {project_uname}'
                )
        except FileNotFoundError as e:
            Logger.info(f'Project mappings not found. Adopting default mappings.')
            self.project_mappings = self.mappings
            self.project_node_mappings = self.node_mappings
        except Exception as e:
            Logger.exception(f'Exception in load_project_mappings: {e}')
            raise e

        self.number_of_nodes = int(self.mappings['number_of_nodes']) # type: ignore[index]
        Logger.info(f'Project {project_uname} mappings loaded')

    def save_project_mappings(self, project_uname: str, path: str | None = None) -> None:
        """Write a project's ``mappings.xml`` back to disk (feature 008, T035).

        ``self.project_mappings`` is already the document root object
        (``ProjectMappings.main_key`` is ``''``, so ``get_dict()``/
        ``.processed`` return the root itself, not a nested field) — no
        separate tracking attribute is needed the way settings needs one.

        Args:
            project_uname (str): the project whose mappings to write.
            path (str | None): where to write. Defaults to
                ``self.project_path(project_uname, 'mappings.xml')``.

        Raises:
            SchemaError: the in-memory mappings do not match
                ``project_mappings.xsd``.
            AttributeError: before :meth:`load_project_mappings` has run.
        """
        self.project_mappings.save(
            path or self.project_path(project_uname, 'mappings.xml')
        )

    def get_video_output_id(self, mapping_name: str):
        """
        Returns the video output id for the given mapping name.
        """
        if mapping_name == 'default':
            return self.node_conf['default_video_output']
        else:
            if 'outputs' in self.project_node_mappings['video'].keys():
                for each_out in self.project_node_mappings['video']['outputs']:
                    for each_map in each_out['mappings']:
                        if mapping_name == each_map['mapped_to']:
                            return each_out['name']

        raise Exception(f'Video output wrongly mapped')

    def get_audio_output_id(self, mapping_name: str):
        """
        Returns the audio output id for the given mapping name.
        """
        if mapping_name == 'default':
            return self.node_conf['default_audio_output']
        else:
            for each_out in self.project_mappings['audio']['outputs']: # type: ignore[index]
                for each_map in each_out[0]['mappings']:
                    if mapping_name == each_map['mapped_to']:
                        return each_out[0]['name']

        raise Exception(f'Audio output wrongly mapped')

    def check_project_mappings(self) -> bool:
        """Check that every port the project asks for exists on this node.

        **Compensation #3, deleted** (T052, FR-016). The previous body walked
        the node mapping generically — ``for area, contents in node.items()``,
        then ``for section, elements in contents.items()`` — *because the shape
        was not stated anywhere*. Now that it is, this addresses the sections
        by name and unwraps each port the same way ``load_net_and_node_mappings``
        does.

        Worth recording: the old walk was also **unreachable in practice**. It
        was guarded by ``isinstance(contents, dict)``, and a device section
        decodes to a *list* of port groups — so the inner loops never ran and
        no project mapping was ever actually checked. Rewriting it against the
        stated shape is what makes the check run at all; that is a behaviour
        change in the sense that a dormant validation wakes up, and it is
        exactly the change FR-016 asks for. A project whose mappings are
        correct is unaffected.

        Returns:
            bool: ``True`` when every mapped port is present on this node.

        Raises:
            Exception: naming the first port that is not, the section it was
                declared in, and this node's uuid.
        """
        if self.using_default_mappings:
            return True

        node = self.project_node_mappings
        if not node:
            return True

        for section in _DEVICE_SECTIONS:
            device_groups = node.get(section)
            if not isinstance(device_groups, list):
                continue
            for group in device_groups:
                for direction, ports in group.items():
                    available = self.node_hw_outputs.get(f'{section}_{direction}', [])
                    for port in ports:
                        put = _unwrap_put(port)
                        name = _hw_name(put)
                        if name not in available:
                            err_str = (
                                f'Project {section} {direction} mapping incorrect: '
                                f'{name} not present in node: '
                                f'{self.node_conf["uuid"]}'
                            )
                            Logger.error(err_str)
                            raise Exception(err_str)
        return True

    # -- projection (T056b, Contracts §W8) ----------------------------------

    def to_wire(self, section: str = 'settings') -> dict:
        """Project one configuration section through the **show projection**.

        The same ``encode_wire`` that produces the UI's ``project_load``
        payload, reached through the same ``to_wire()`` method body on
        ``CuemsDict`` — one implementation, two domains (FR-014a, SC-017).
        A config object and a script differ only in which ``Mapper`` they
        resolve, which is what makes that claim true of the code rather than of
        the intent.

        **Configuration is not transmitted to the UI in this feature.** This is
        the seam the planned follow-on work uses, and building it here is what
        stops a second projection being written then — the drift mechanism
        behind F15's three incompatible mappings shapes. It costs almost
        nothing: the config types are registry-bound model classes anyway, and
        the guarantee is testable immediately against the already-recorded
        ``tests/golden/dict/*.config.json``.

        Args:
            section: ``'settings'``, ``'network_map'``, ``'mappings'``,
                ``'node_conf'``, ``'node_network_map'`` or ``'node_mappings'``.

        Returns:
            dict: JSON-safe, in the wire format §W2 states.

        Raises:
            ValueError: for an unknown section name, naming the ones that
                exist rather than raising ``AttributeError`` from inside.
            AttributeError: if the named section has not been loaded — a
                project section before :meth:`load_project_config` has run.
        """
        if section not in _PROJECTABLE_SECTIONS:
            raise ValueError(
                f"unknown configuration section {section!r}; expected one of "
                f"{sorted(_PROJECTABLE_SECTIONS)}"
            )
        value = getattr(self, section)
        project = getattr(value, 'to_wire', None)
        if project is None:
            raise TypeError(
                f"configuration section {section!r} is a "
                f"{type(value).__name__}, which carries no projection"
            )
        return project()

    ## helper functions
    def project_path(self, project_uname: str, file_name: str) -> str:
        """
        Returns the path to the project file if it exists.

        Args:
            project_uname (str): The name of the project.
            file_name (str): The name of the file to be checked.

        Returns:
            str: The path to the project file.

        Raises:
            FileNotFoundError: If the project file does not exist.
        """
        project_path = path.join(self.library_path, 'projects', project_uname, file_name)
        if not path.exists(project_path):
            raise FileNotFoundError(f'Project file {project_path} not found')
        return project_path
