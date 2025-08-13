from os import environ, path

from ..log import Logger, logged
from ..xml import Settings
from ..helpers import mkdir_recursive

class ConfigBase():
    def __init__(self, config_dir: str):
        self.load_base_settings(config_dir)

    @logged
    def load_base_settings(self, base_dir: str):
        try:
            dir = environ['CUEMS_CONF_PATH']
        except KeyError:
            dir = base_dir
        self.config_dir = dir

        try:
            settings = Settings(self.conf_path('settings.xml'))
            self.settings = settings.get_dict()
        except Exception as e:
            Logger.exception(f'Exception catched while loading settings: {e}')
            raise e

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

    @property
    def node_conf(self):
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
