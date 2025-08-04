from os import path
from typing import Any

from .ConfigBase import ConfigBase
from ..log import Logger, logged
from ..xml import ProjectSettings, NetworkMap, ProjectMappings

CUEMS_CONF_PATH = '/etc/cuems/'

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
        return self._network_map

    @network_map.setter
    def network_map(self, value: dict[str, Any]):
        self._network_map = value

    @property
    def node_network_map(self):
        return self._node_network_map
    
    @node_network_map.setter
    def node_network_map(self, value: NetworkMap | dict):
        if isinstance(value, NetworkMap):
            self._node_network_map = value.get_node(self.node_uuid)
        else:
            self._node_network_map = value

    @property
    def mappings(self):
        return self._mappings

    @mappings.setter
    def mappings(self, value: dict[str, Any]):
        self._mappings = value
    
    @property
    def node_mappings(self):
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
        try:
            netmap = NetworkMap(self.conf_path('network_map.xml'))
            self.network_map = netmap.get_dict()
            self.node_network_map = netmap
        except Exception as e:
            Logger.exception(f'Exception catched while loading network map: {e}')
            raise e

    def load_net_and_node_mappings(self):
        """
        Loads the network and node mappings.
        """
        try:
            mappings_file = self.project_path(self.project_name, 'mappings.xml')
        except FileNotFoundError as e:
            mappings_file = self.conf_path('default_mappings.xml')

        try:
            project_mappings = ProjectMappings(mappings_file)
            self.mappings = project_mappings.processed # type: ignore[attr-defined]
        except Exception as e:
            Logger.exception(f'Exception catched while loading mappings file: {e}')
            raise e

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

        self.project_name = project_uname

        self.load_project_settings(project_uname)
        self.load_project_mappings(project_uname)

    def load_project_settings(self, project_uname: str):
        """
        Loads the project settings from the project file.
        """
        try:
            settings_path = self.project_path(project_uname, 'settings.xml')
            conf = ProjectSettings(
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
