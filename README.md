# cuems-utils
Reusable classes and methods for CueMS system

[![PyPI - Version](https://img.shields.io/pypi/v/cuemsutils.svg)](https://pypi.org/project/cuemsutils)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cuemsutils.svg)](https://pypi.org/project/cuemsutils)

-----

## Table of Contents

- [Installation](#installation)
- [Release notes](#v005)
- [License](#license)

## Installation

```console
pip install cuemsutils
```

## Release notes

### v0.0.5
 - All properties of objects are lowercase exept the ones representing classes (e.g. `CueList` at `CuemsScript` and `Media` at `MediaCue`).
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
