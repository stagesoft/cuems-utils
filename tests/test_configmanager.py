import pytest
from os import environ, path
from pathlib import Path
from cuemsutils.tools.ConfigManager import ConfigManager

TEST_DATA_PATH = path.join(Path(__file__).parent, 'data')

@pytest.fixture
def config_manager():
    environ['CUEMS_CONF_PATH'] = TEST_DATA_PATH
    return ConfigManager()

def test_fail_no_conf_path():
    with pytest.raises(
        FileNotFoundError,
        match = 'Configuration directory /etc/cuems/ not found'
    ):
        ConfigManager()

def test_fail_no_conf_parameter():
    with pytest.raises(
        FileNotFoundError,
        match = 'Configuration directory /etc/cuems_test/ not found'
    ):
        ConfigManager(config_dir='/etc/cuems_test/')

def test_base_settings(config_manager):
    assert config_manager.config_dir == TEST_DATA_PATH
    assert config_manager.library_path == '/opt/cuems_library'
    assert config_manager.tmp_path == '/tmp/cuems'
    assert config_manager.database_name == 'project-manager.db'
    assert config_manager.show_lock_file == 'show.lock'
    assert config_manager.editor_url == 'formitgo.local'
    assert config_manager.controller_url == 'controller.local'
    assert config_manager.templates_path == '/usr/share/cuems'
    assert config_manager.controller_interfaces_template == 'interfaces.controller'
    assert config_manager.node_interfaces_template == 'interfaces.node'
    assert config_manager.controller_lock_file == 'controller.lock'
    assert config_manager.node_uuid == '0367f391-ebf4-48b2-9f26-000000000001'
    assert config_manager.node_uuid == config_manager.node_conf['uuid']
    assert config_manager.node_conf['mac'] == '2cf05d21cca3'
    assert config_manager.node_conf['osc_dest_host'] == 'localhost'
    assert config_manager.node_conf['oscquery_ws_port'] == 9090
    assert config_manager.node_conf['oscquery_osc_port'] == 9091
    assert config_manager.node_conf['websocket_port'] == 9092
    assert config_manager.node_conf['load_timeout'] == 15000
    assert config_manager.node_conf['nodeconf_timeout'] == 5000
    assert config_manager.node_conf['discovery_timeout'] == 15000
    assert config_manager.node_conf['mtc_port'] == 'Midi Through Port-0'
    assert config_manager.node_conf['osc_in_port_base'] == 7000
    assert config_manager.host_name == '000000000001.local'
    assert config_manager.node_url == 'http://000000000001.local'
    assert config_manager.osc_initial_port == 7000

def test_network_map(config_manager):
    assert config_manager.network_map == {
        'nodes': {
            '0367f391-ebf4-48b2-9f26-000000000001': {
                'name': 'test_node',
                'url': 'http://000000000001.local'
            }
        }
    }

def test_project_load(config_manager):
    config_manager.load_project_config('test_project')
    assert config_manager.project_name == 'test_project'
    assert type(config_manager.project_mappings) == dict
    assert type(config_manager.project_node_mappings) == dict
    assert type(config_manager.project_settings) == dict
    assert config_manager.project_mappings == config_manager.mappings
