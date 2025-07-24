from os import path, mkdir, environ

from ..log import Logger, logged
from ..xml import Settings, NetworkMap, ProjectMappings

CUEMS_CONF_PATH = '/etc/cuems/'
LIBRARY_PATH = '.local/share/cuems/'
TMP_PATH = '/tmp/cuems/'
DATABASE_NAME = 'project-manager.db'
SHOW_LOCK_FILE = '.lock_file'
CUEMS_MASTER_LOCK_FILE = 'master.lock'

class ConfigManager():
    def __init__(self, config_dir: str = CUEMS_CONF_PATH):
        """
        ConfigManager constructor.
        This class is responsible for loading the configuration files and providing
        the configuration data to the rest of the application.

        It also provides methods to check the project files and to load them on demand.

        Args:
            config_dir (str): The directory containing the configuration files.

        Raises:
            Exception: If the configuration files are not found.
        """
        # Initialize with default values
        if config_dir == CUEMS_CONF_PATH:
            try:
                config_dir = environ['CUEMS_CONF_PATH']
            except KeyError:
                pass
        self.config_dir = config_dir

        self.library_path = path.join(environ['HOME'], LIBRARY_PATH)
        self.tmp_path = TMP_PATH
        self.set_dir_hierarchy()

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
    def config_dir(self, value):
        if not path.exists(value):
            raise FileNotFoundError(f'Configuration directory {value} not found')
        self._config_dir = value

    @property
    def library_path(self):
        return self._library_path

    @library_path.setter
    def library_path(self, value):
        self._library_path = value

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
        
        self._load_node_conf()
        self._load_network_map()
        self._load_net_and_node_mappings()

    def _load_network_map(self):
        try:
            netmap = NetworkMap(self.conf_path('network_map.xml'))
            self.network_map = netmap.get_dict()
        except Exception as e:
            Logger.exception(f'Exception catched while load_network_map: {e}')
            raise e

    def _load_node_conf(self):
        try:
            engine_settings = Settings(self.conf_path('settings.xml'))
            engine_settings = engine_settings.get_dict()
        except Exception as e:
            Logger.exception(f'Exception catched while load_node_conf: {e}')
            raise e

        if engine_settings['library_path'] != '':
            self.library_path = engine_settings['library_path']
    
        if engine_settings['tmp_path'] != '':
            self.tmp_path = engine_settings['tmp_path']

        if engine_settings['database_name'] != '':
            self.database_name = engine_settings['database_name']

        if engine_settings['show_lock_file'] != '':
            self.show_lock_file = engine_settings['show_lock_file']

        # Now we know where the library is, let's check it out
        self.set_dir_hierarchy()

        self.node_conf = engine_settings['node']
        self.osc_initial_port = self.node_conf['osc_in_port_base']
        self.host_name = f"{self.node_conf['uuid'].split('-')[-1]}.local"

        Logger.info(f'Cuems node_{self.node_conf["uuid"]} config loaded')

    def _load_net_and_node_mappings(self):
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

        self._load_project_settings(project_uname)
        self._load_project_mappings(project_uname)

    def _load_project_settings(self, project_uname):
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
            Logger.exception(f'Exception in _load_project_settings: {e}')
            raise e

        self.project_conf = conf.get_dict()
        for key, value in self.project_conf.items():
            corrected_dict = {}
            if value:
                for item in value:
                    corrected_dict.update(item)
                self.project_conf[key] = corrected_dict

        Logger.info(f'Project {project_uname} settings loaded')

    def _load_project_mappings(self, project_uname):
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
            Logger.exception(f'Exception in _load_project_mappings: {e}')
            raise e

        self.number_of_nodes = int(self.project_mappings['number_of_nodes']) # type: ignore[index]
        Logger.info(f'Project {project_uname} mappings loaded')

    def get_video_player_id(self, mapping_name):
        if mapping_name == 'default':
            return self.node_conf['default_video_output']
        else:
            if 'outputs' in self.project_node_mappings['video'].keys():
                for each_out in self.project_node_mappings['video']['outputs']:
                    for each_map in each_out['mappings']:
                        if mapping_name == each_map['mapped_to']:
                            return each_out['name']

        raise Exception(f'Video output wrongly mapped')

    def get_audio_output_id(self, mapping_name):
        if mapping_name == 'default':
            return self.node_conf['default_audio_output']
        else:
            for each_out in self.project_mappings['audio']['outputs']: # type: ignore[index]
                for each_map in each_out[0]['mappings']:
                    if mapping_name == each_map['mapped_to']:
                        return each_out[0]['name']

        raise Exception(f'Audio output wrongly mapped')

    def check_project_mappings(self):
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
        paths_to_check = [
            path.join(self.library_path, 'projects'),
            path.join(self.library_path, 'media'),
            path.join(self.library_path, 'trash', 'projects'),
            path.join(self.library_path, 'trash', 'media'),
            self.tmp_path
        ]
        try:
            for each_path in paths_to_check:
                self.mkdir_recursive(each_path)
        except Exception as e:
            Logger.error("error: {} {}".format(type(e), e))

    def mkdir_recursive(self, folder: str) -> None:
        """
        Creates a directory recursively.

        Args:
            folder (str): The folder to be created.
        """
        if path.exists(folder):
            return
        if not path.exists(path.dirname(folder)):
            self.mkdir_recursive(path.dirname(folder))
        mkdir(folder)
