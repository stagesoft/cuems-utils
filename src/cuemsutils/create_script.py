# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>

from .cues import ActionCue, AudioCue, CueList, CuemsScript, DmxCue, FadeCue, VideoCue
from .cues.CueOutput import AudioCueOutput, DmxCueOutput, VideoCueOutput
from .cues.DmxCue import DmxChannel, DmxScene, DmxUniverse
from .cues.FadeCue import FadeCurveType
from .cues.MediaCue import Media, Region
from .helpers import new_datetime, new_uuid
from .log import Logger

now = new_datetime()
def create_script():
    """Create a minimal script with available cues.

    This function creates a minimal script with available cues.
    It includes an audio cue, a video cue and an action cue.
    The script is returned as a CuemsScript object.

    Returns:
        CuemsScript: A minimal script with configured cues.
    """
    target_uuid = '1f301cf8-dd03-4b40-ac17-ef0e5e7988be'
    act = ActionCue({'action_target': target_uuid, 'action_type': 'play', 'ui_properties' : {'warning' : 0}})
    ac = AudioCue({
        'master_vol': 66,
        'Media': Media({
            'file_name': 'file.ext',
            # An explicit id, because F16 stopped the empty string from
            # silently becoming one: ``Uuid('')`` used to mint a uuid4 for any
            # falsy argument, so ``'id': ''`` produced a populated media id by
            # accident. ``MediaType.id`` is a required uuid4 in the schema, so
            # the template needs a real one — asked for, not stumbled into.
            'id': new_uuid(),
            'duration': '00:00:00.000',
            'regions': [
                Region({
                    'id': 0,
                    'loop': 1,
                    'in_time': None,
                    'out_time': None
                })
            ]
        }),
        'ui_properties' : {
            'warning': None
            }
    })
    vc = VideoCue({
        'Media': Media({
            'file_name': 'file_video.ext',
            'id': new_uuid(),  # explicit, per the note on the audio Media above
            'duration': '00:00:00.000',
            'regions' : [
                Region({
                    'id': 0, 'loop': 1, 'in_time': None, 'out_time': None
                })
            ]
        }),
        'ui_properties' : {
            'warning': None
            }
    })
    dc = DmxCue({
        'fadein_time':0.0,
        'fadeout_time':0.0,
        'DmxScene': DmxScene({
            'id': 0,
            'DmxUniverse': DmxUniverse({
                'universe_num': 0,
                'dmx_channels': [
                    DmxChannel({
                        'channel': 0,
                        'value': 0
                    })
                ]

            })

        }),
        'time': 0,
        'ui_properties' : {
            'warning': None
            }
    })
    ac.outputs = [AudioCueOutput({
        "output_name": "0367f391-ebf4-48b2-9f26-000000000001_system:playback_1",
        "output_vol": 80,
        "channels": [
            {
                "channel": {
                    "channel_num": 0,
                    "channel_vol": 80
                }
            }
        ]
    })]

    vc.outputs = [
        VideoCueOutput({
            "output_name": "0367f391-ebf4-48b2-9f26-000000000001_0",
            "output_geometry": {
                "x_scale": 1,
                "y_scale": 1,
                "corners": {
                    "top_left": {
                        "x": 0,
                        "y": 0
                    },
                    "top_right": {
                        "x": 0,
                        "y": 0
                    },
                    "bottom_left": {
                        "x": 0,
                        "y": 0
                    },
                    "bottom_right": {
                        "x": 0,
                        "y": 0
                    }
                }
            }
        }),
        VideoCueOutput({
            "output_name": "0367f391-ebf4-48b2-9f26-000000000001_custom_0",
            "output_geometry": {
                "x_scale": 1,
                "y_scale": 1,
                "corners": {
                    "top_left": {"x": 0, "y": 0},
                    "top_right": {"x": 0, "y": 0},
                    "bottom_left": {"x": 0, "y": 0},
                    "bottom_right": {"x": 0, "y": 0}
                }
            },
            "canvas_region": {
                "x": 0.1,
                "y": 0.1,
                "width": 0.5,
                "height": 0.5
            }
        })
    ]

    dc.outputs = [DmxCueOutput({
        "output_name": "0367f391-ebf4-48b2-9f26-000000000001"
    })]


    fc = FadeCue({
        'action_target': target_uuid,
        'curve_type': FadeCurveType.linear,
        'duration': '00:00:02.000',
        'target_value': 0,
        'ui_properties': {'warning': None},
    })

    custom_cue_list = CueList({'contents': [ac]})
    custom_cue_list.append(vc)
    custom_cue_list.append(dc)
    custom_cue_list.append(act)
    custom_cue_list.append(fc)

    script = CuemsScript({'CueList': custom_cue_list})
    script.name = "Test Script"
    script.description = "This is a test script"

    # set dates and ids so it can be validated
    script.created = now
    script.modified = now
    script['id'] = new_uuid()
    script['CueList']['id'] = new_uuid()
    script.cuelist['contents'][0]['id'] = new_uuid()
    script.cuelist['contents'][1]['id'] = new_uuid()
    script.cuelist['contents'][2]['id'] = new_uuid()
    script.cuelist['contents'][3]['id'] = new_uuid()
    script.cuelist['contents'][4]['id'] = new_uuid()
    # Through the property, not ``script['ui_properties'] = …``: bracket
    # assignment on a dict subclass is raw ``dict.__setitem__`` and bypasses
    # ``set_ui_properties``, so the root alone ended up holding a plain ``dict``
    # while every cue held a ``CuemsDict``. That is the divergence FR-008 exists
    # to remove, and it was hiding in the template builder rather than in the
    # model. The emitted XML is unchanged — wildcard content has no declared
    # field set, so both types serialize identically.
    script.ui_properties = {
        'warning': 0,
    }
    Logger.debug(f'Created test script: {script.cuelist}')

    validate_template(script)

    # remove dates and ids so we send it empty
    script.created = None
    script.modified = None
    script.id = None
    script.cuelist.id = None
    script.cuelist.contents[0]['id'] = None
    script.cuelist.contents[1]['id'] = None
    script.cuelist.contents[2]['id'] = None
    script.cuelist.contents[3]['id'] = None
    script.cuelist.contents[4]['id'] = None

    return script


def validate_template(project_template):
    """Validate the blank template before it is handed to the editor.

    Migrated to the public surface (T064). It used to be
    ``XmlReaderWriter(schema_name="script", xmlfile=None).validate_object(...)``
    — the ``xmlfile=None`` idiom that existed only so a *reader/writer* could
    be built without a file to read or write. ``validate()`` has no file to
    pass, which is the point of it.

    This is the one first-party consumer that migrates **in** this feature.
    Everything else is listed in the migration guide for feature 009.
    """
    report = project_template.validate()
    Logger.debug(f'initial template validation result: {report!r}')
    return report



