## Code to reubicate from cuems repositories
- cuems_nodeconf/CuemsSettings.py

## Changes to develop
- `loaded` property to `load`|`preload`, and leave `loaded` flag to be used only for `arm()`
- reason about moving `id` property content to `ui_properties` and use it to hold `Uuid` instances instead
- `script.xsd` should not accept `Cue`, since is not an user-facing class
- `unix_name` is missing on `script.xsd` for `CuemsScript` class
- improve `regions` structure
