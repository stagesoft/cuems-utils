# cuems-utils
Reusable classes and methods for CueMS system

[![PyPI - Version](https://img.shields.io/pypi/v/cuemsutils.svg)](https://pypi.org/project/cuemsutils)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cuemsutils.svg)](https://pypi.org/project/cuemsutils)

-----

## Table of Contents

- [Installation](#installation)
- [Release notes](#release-notes)
- [License](#license)

## Installation

```console
pip install cuemsutils
```

## Release notes

### v0.0.9
 - Extended `Settings` parameters class
 - New `tools` submodule for clarity with documentation
 - Added class `SignalEngine` and `run_daemon` method for running daemons
 - Improved `ProjectMappings` and `NetworkMap` content processing
 - Added class `Timeoutloop` for running methods with timeout
 - `get_media` methods return extended information

### v0.0.8
 - `Settings` class added to xml module. Allows for easy access to configuration files.
 - Child classes `NetworkMap` and `ProjectMappings` inherit from `Settings` class.
 - `CueList.get_media` method fixed to create usable dictionaries
 - `CuemsScript.get_media` as a wrapper for `CueList.get_media`
 - `CueList.get_[own_]media_filenames` method now returns a sorted list of filenames
 - `Region` class improved to support proper `Media` recreation from json
 - `setter` method moved up to `CuemsDict` class

### v0.0.7
 - `XmlReaderWriter` class added, previous classes `XmlReader` and `XmlWriter` marked as deprecated.
 - fixed `Communicator` error handling on path checking.
 - `Logger.exception` and `Logger.critical` methods added.

### v0.0.6
 - `CuemsScript` now includes `ui_properties` property to store UI related properties as a dictionary without restrictions.
 - fixed misspelling at `Communicator` class
 - internal method `to_cuemsdict` renamed to `as_cuemsdict` for clarity

### v0.0.5
 - All properties of objects are lowercase except the ones representing classes (e.g. `CueList` at `CuemsScript` and `Media` at `MediaCue`).
 - Parameters renamed for clarity:
    - `uuid`    -> `id`
    - `loaded`  -> `autoload`
    - `bott_*`  -> `bottom_*`
 - User facing classes can be exported directly (e.g. `from cuemsutils.cues import AudioCue, VideoCue`)
 - `Cue` is not longer an accepted object for script validation
 - `ui_properties` has become an `CuemsDict` object to facilitate modifications and requierements for UI development.
 - `CuemsScript` object has method `to_json` to convert its contents to json format. Internally works via `json.dumps` and specific calls to methods `__json__` when available at class level.

### v0.0.4
 - `Logger` fixed to allow empty `extra` parameter

## License

`cuemsutils` is distributed under the terms of the [GPL v3](https://www.gnu.org/licenses/gpl-3.0.html) license.

Copyright (C) 2025 StageLab

**This program is free software**: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
