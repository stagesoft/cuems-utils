## Code to reubicate from cuems repositories
- cuems_nodeconf/CuemsSettings.py

## Changes to develop
- `loaded` property to `load`|`preload`, and leave `loaded` flag to be used only for `arm()`
- reason about moving `id` property content to `ui_properties` and use it to hold `Uuid` instances instead
- `unix_name` is missing on `script.xsd` for `CuemsScript` class
- improve `regions` structure
- `region` property is missing on as `Region` class on `MediaCue` builds and parsers:
  - ```python
    # @test_xml.py:225
    assert type(parsed.cuelist.contents[0].region) == list
    assert type(parsed.cuelist.contents[0].region[0]) == Region
    ```
