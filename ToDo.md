## Changes to develop
- leave `loaded` flag to be used only for `arm()`
- `unix_name` is missing on `script.xsd` for `CuemsScript` class
- `ActionCue` `fade_out` can edit by osc the volume of the target cue and move it gradually to 0
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
- implement `check_mappings` as `@singledispatch`
