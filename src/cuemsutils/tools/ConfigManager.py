from os import path, environ

from ..log import Logger, logged
from ..xml import Settings, NetworkMap, ProjectMappings
from ..helpers import mkdir_recursive

CUEMS_CONF_PATH = '/etc/cuems/'
LIBRARY_PATH = '.local/share/cuems/'
TMP_PATH = '/tmp/cuems/'
DATABASE_NAME = 'project-manager.db'
SHOW_LOCK_FILE = '.lock_file'
CUEMS_MASTER_LOCK_FILE = 'master.lock'

class ConfigManager():
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
        self.load_base_settings(config_dir)

        if load_all:
            self.library_path = path.join(environ['HOME'], LIBRARY_PATH)
            self.tmp_path = TMP_PATH
            self.database_name = DATABASE_NAME
            self.show_lock_file = SHOW_LOCK_FILE

            self.using_default_mappings = False
            self.number_of_nodes = 1
            self.project_name = ''

            self.load_config()

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
        return self._library_path

    @library_path.setter
    def library_path(self, value: str):
        self._library_path = value

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
            Logger.exception(f'Exception catched while load_node_conf: {e}')
            raise e

    @logged
    def load_config(self) -> None:
        """
        Loads the system configuration.
        """
        # Initialize with empty values
        self.node_conf = {}
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
        
        self.load_node_conf()
        self.load_network_map()
        self.load_net_and_node_mappings()

    def load_network_map(self):
        """
        Loads the network map from the base configuration file.
        """
        try:
            netmap = NetworkMap(self.conf_path('network_map.xml'))
            self.network_map = netmap.get_dict()
        except Exception as e:
            Logger.exception(f'Exception catched while load_network_map: {e}')
            raise e

    def load_node_conf(self):
        """
        Loads the node configuration from the base configuration file.
        """
        if self.settings['library_path'] != '':
            self.library_path = self.settings['library_path']
    
        if self.settings['tmp_path'] != '':
            self.tmp_path = self.settings['tmp_path']

        if self.settings['database_name'] != '':
            self.database_name = self.settings['database_name']

        if self.settings['show_lock_file'] != '':
            self.show_lock_file = self.settings['show_lock_file']

        # Now we know where the library is, let's check it out
        self.set_dir_hierarchy()

        self.node_conf = self.settings['node']
        self.osc_initial_port = self.node_conf['osc_in_port_base']
        self.host_name = f"{self.node_conf['uuid'].split('-')[-1]}.local"

        Logger.info(f'Cuems node_{self.node_conf["uuid"]} config loaded')

    def load_net_and_node_mappings(self):
        """
        Loads the network and node mappings.
        """
        try:
            settings_file = self.project_path(self.project_name, 'mappings.xml')
        except FileNotFoundError as e:
            settings_file = self.conf_path('default_mappings.xml')

        try:
            project_mappings = ProjectMappings(settings_file)
            self.network_mappings = project_mappings.processed
        except Exception as e:
            Logger.exception(f'Exception in load_net_and_node_mappings: {e}')

        self.node_mappings = project_mappings.get_node(self.node_conf['uuid'])

        # Select just output names for node_hw_outputs var
        for section, value in self.node_mappings.items():
            if isinstance(value, dict):
                for subsection, subvalue in value.items():
                    for subitem in subvalue:
                        self.node_hw_outputs[section+'_'+subsection].append(subitem['name'])

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

        self.load_project_settings(project_uname)
        self.load_project_mappings(project_uname)

    def load_project_settings(self, project_uname: str):
        """
        Loads the project settings from the project file.
        """
        try:
            settings_path = self.project_path(project_uname, 'settings.xml')
            conf = Settings(
                schema='project_settings',
                xmlfile=settings_path
            )
        except FileNotFoundError as e:
            Logger.info(
                f'Project {project_uname} settings not found. Keeping default settings.'
            )
            return
        except Exception as e:
            Logger.exception(f'Exception in load_project_settings: {e}')
            raise e

        self.project_conf = conf.get_dict()
        for key, value in self.project_conf.items():
            corrected_dict = {}
            if value:
                for item in value:
                    corrected_dict.update(item)
                self.project_conf[key] = corrected_dict

        Logger.info(f'Project {project_uname} settings loaded')

    def load_project_mappings(self, project_uname: str):
        """
        Loads the project mappings from the project file.
        """
        try:
            mappings_path = self.project_path(project_uname, 'mappings.xml')
            project_mappings = ProjectMappings(mappings_path)
            self.project_mappings = project_mappings.processed
            try:
                self.project_node_mappings = project_mappings.get_node(self.node_conf['uuid'])
            except ValueError:
                Logger.warning(
                    f'No mappings assigned for this node in project {project_uname}'
                )
        except FileNotFoundError as e:
            Logger.info(f'Project mappings not found. Adopting default mappings.')
            self.project_mappings = self.node_mappings
            self.project_node_mappings = self.node_mappings
        except Exception as e:
            Logger.exception(f'Exception in load_project_mappings: {e}')
            raise e

        self.number_of_nodes = int(self.project_mappings['number_of_nodes']) # type: ignore[index]
        Logger.info(f'Project {project_uname} mappings loaded')

    def get_video_player_id(self, mapping_name: str):
        """
        Returns the video player id for the given mapping name.
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
        """
        Checks if the project mappings are correct.
        """
        if self.using_default_mappings:
            return True

        nodes_to_check = [self.project_node_mappings]
        for node in nodes_to_check:
            for area, contents in node.items():
                if isinstance(contents, dict):
                    for section, elements in contents.items():
                        for element in elements:
                            if element['name'] not in self.node_hw_outputs[f'{area}_{section}']:
                                err_str = f'Project {area} {section} mapping incorrect: {element["name"]} not present in node: {self.node_conf["uuid"]}'
                                Logger.error(err_str)
                                raise Exception(err_str)
        return True

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
        if not self.library_path:
            raise AttributeError('Library path not set')
        if not self.tmp_path:
            raise AttributeError('Temporary path not set')
       
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
