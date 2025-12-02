## TO develop for stable version

## Changes to develop
- leave `loaded` flag to be used only for `arm()`
- `unix_name` is missing on `script.xsd` for `CuemsScript` class
- `ActionCue` `fade_out` can edit by osc the volume of the target cue and move it gradually to 0
- implement `check_mappings` as `@singledispatch` 
- complete testing for `ConfigManager` to ensure all methods work
- complete 100% usage of `test_logging.py` to ensure syslog is working properly
- edit `ConfigManager.get_audio|video|dmx_output_id` to accomodate new mapping layer

### Settings additional info
- revisar osc puertos hub
- crear xml schema de audiomixer

### Parsers-Builders
- Remove duplication and ensure all elements are handled properly
- All modules from `xml` should be 100% tested for proven accuracy of the code
- Ensure `Settings` and child classes write objects properly as xml files
    ```python
    # tests/test_xml.py
    def test_networkmap():
        ...

        altered_networkmap = networkmap.xml_dict
        assert altered_networkmap['CuemsNodeDict'][0]['CuemsNode']['online'] == 'True'
        altered_networkmap['CuemsNodeDict'][0]['CuemsNode']['port'] = 3

        xml_data = networkmap.data2xml(altered_networkmap)
        
        networkmap.xmlfile = path.dirname(__file__) + '/tmp/network_map_altered.xml'
        with raises(ValueError):
            networkmap.write(xml_data)
    ```
