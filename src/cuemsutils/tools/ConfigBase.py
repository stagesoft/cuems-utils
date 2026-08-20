from os import environ, path

from ..errors import SchemaError
from ..log import Logger, logged
# The concrete module, not the package root: ``cuemsutils.xml.Settings``
# is a deprecation shim as of T061, and contract C8 forbids the library
# calling one of its own deprecated names.
from ..xml.settings import Settings
from ..helpers import mkdir_recursive


def load_config_document(cls, xmlfile: str, schema_name: str):
    """Open one configuration document with the **accessor's** error posture.

    One function, every call site (FR-014b, contract C2). The two failure kinds
    a consumer must tell apart are kept apart here rather than at each of the
    six places a configuration file is opened:

    * ``OSError``/``FileNotFoundError`` propagate **unwrapped** — every
      consumer already handles them, and wrapping would force callers to
      unwrap to find out what actually happened (FR-035);
    * anything else is a schema failure and becomes ``SchemaError``, carrying
      the original reason so the offending element is still named.

    The internal reader (``xml/settings.py``) deliberately does **not** wrap:
    its raw verdicts are what ``tests/golden/outcomes.json`` pins document by
    document, and the accessor is where contract C2 places the posture.
    """
    try:
        return cls(xmlfile)
    except OSError:
        raise
    except SchemaError:
        raise
    except Exception as exc:
        message = f'{xmlfile} is not a valid {schema_name} document: {exc}'
        Logger.error(message)
        raise SchemaError(message) from exc


class ConfigBase():
    def __init__(self, config_dir: str):
        self.load_base_settings(config_dir)

    @logged
    def load_base_settings(self, base_dir: str):
        """Read ``settings.xml`` from the resolved configuration directory.

        Raises:
            OSError: **unwrapped** — ``FileNotFoundError`` when the directory
                or the file is absent, ``PermissionError`` when it cannot be
                read. Identical to ``CuemsScript.load`` (FR-035), and
                deliberately distinct from the next entry: *a node with no
                config and a node with a corrupt one are different operational
                problems* (FR-014b).
            SchemaError: the file exists and does not match ``settings.xsd``,
                naming the offending element. The measured case is **X13** —
                ``gradient_osc_port`` was added to the schema as required,
                which invalidated every settings file written before it,
                including two this project shipped. That is *reported* here and
                *fixed* under the schema evolution convention, not in this
                feature; no ``.xsd`` is edited (FR-033).
        """
        try:
            dir = environ['CUEMS_CONF_PATH']
        except KeyError:
            dir = base_dir
        self.config_dir = dir

        self.settings = load_config_document(
            Settings, self.conf_path('settings.xml'), 'settings'
        ).get_dict()

    # HELPER FUNCTIONS #
    def conf_path(self, file_name: str) -> str:
        """
        Returns the path to the configuration file.

        Args:
            file_name (str): The name of the file to be checked.

        Returns:
            str: The path to the configuration file.

        Raises:
            FileNotFoundError: If the configuration file does not exist.
        """
        conf_path = path.join(self.config_dir, file_name)
        if not path.exists(conf_path):
            raise FileNotFoundError(f'Configuration file {conf_path} not found')
        return conf_path
    
    def set_dir_hierarchy(self) -> None:
        """
        Sets the directory hierarchy for the library path.
        """      
        dirs = [
            'projects',
            'media',
            path.join('media', 'waveforms'),
            path.join('media', 'thumbnails')
        ]
        trash = [path.join('trash', i) for i in dirs]
        dirs.extend(trash)

        paths_to_check = [path.join(self.library_path, i) for i in dirs]
        paths_to_check.append(self.tmp_path)

        try:
            for each_path in paths_to_check:
                mkdir_recursive(each_path)
        except Exception as e:
            Logger.error("error: {} {}".format(type(e), e))
    
    # CLASS PROPERTIES #
    @property
    def config_dir(self):
        return self._config_dir
    
    @config_dir.setter
    def config_dir(self, value: str):
        if not path.exists(value):
            raise FileNotFoundError(f'Configuration directory {value} not found')
        self._config_dir = value

    @property
    def library_path(self):
        return self.settings['library_path']
    
    @property
    def tmp_path(self):
        return self.settings['tmp_path']
    
    @property
    def database_name(self):
        return self.settings['database_name']
    
    @property
    def show_lock_file(self):
        return self.settings['show_lock_file']

    @property
    def editor_url(self):
        return self.settings['editor_url']
    
    @property
    def controller_url(self):
        return self.settings['controller_url']
    
    @property
    def templates_path(self):
        return self.settings['templates_path']

    @property
    def controller_interfaces_template(self):
        return self.settings['controller_interfaces_template']

    @property
    def node_interfaces_template(self):
        return self.settings['node_interfaces_template']

    @property
    def controller_lock_file(self):
        return self.settings['controller_lock_file']

    # -- what the accessors return (T055, FR-014, FR-018) -------------------
    #
    # **Every name above and below is frozen**, and so is what it means. Only
    # return *types* change, and only where the value is a structure rather
    # than a scalar: the fourteen accessors that answer with a path, a URL or a
    # filename still answer with a ``str``, and ``osc_initial_port`` still
    # answers with an ``int``. The recorded inventory in
    # ``tests/golden/api/config_accessors.json`` is the arbiter — it was
    # captured by introspection *before* any of this landed, which is what
    # makes "every name that exists today" verifiable rather than merely
    # assertable.
    #
    # The structural ones — ``node_conf`` here, and ``network_map``,
    # ``node_network_map``, ``mappings``, ``node_mappings`` and the project
    # accessors on ``ConfigManager`` — now answer with declared-field objects
    # from ``cuemsutils.config`` instead of raw nested dicts. Those objects are
    # ``dict`` subclasses, so ``isinstance(x, dict)``, ``x['key']``,
    # ``x.get(...)`` and iteration all behave exactly as before. That is what
    # allowed the object layer to land without editing a consumer repository.

    @property
    def node_conf(self):
        """The ``<node>`` section of ``settings.xml``.

        Returns:
            cuemsutils.config.settings.NodeConfType: a declared-field object,
            not a raw nested dict (FR-014). Its ``videoplayer`` /
            ``audioplayer`` / ``audiomixer`` / ``dmxplayer`` sections are
            objects too, each of the type its schema declares.

        Raises:
            KeyError: if the settings document carries no ``<node>`` element.
                ``settings.xsd`` requires one, so a document that reaches here
                without it did not come through :meth:`load_base_settings`.
        """
        return self.settings['node']

    @property
    def node_uuid(self):
        return self.node_conf['uuid']

    @property
    def host_name(self):
        return f"{self.node_uuid.split('-')[-1]}.local"

    @property
    def node_url(self):
        return f'http://{self.host_name}'

    @property
    def osc_initial_port(self):
        return self.node_conf['osc_in_port_base']
