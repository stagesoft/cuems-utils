from .cues import ActionCue, AudioCue, DmxCue, CuemsScript, CueList, VideoCue
from .cues.MediaCue import Media, Region
from .cues.CueOutput import AudioCueOutput, VideoCueOutput
from .helpers import new_datetime, new_uuid
from .xml import XmlReaderWriter
from .log import Logger
import xmlschema.validators.exceptions as xmlschema_exceptions

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
            'id': '',
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
            'id': '',
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
    
    vc.outputs = [VideoCueOutput({
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
    })]

                            
    #d_c = DmxCue(time=23, scene={0:{0:10, 1:50}, 1:{20:23, 21:255}, 2:{5:10, 6:23, 7:125, 8:200}}, init_dict={'loop' : 3})
    #d_c.outputs = {'universe0': 3}
    
    custom_cue_list = CueList({'contents': [ac]})
    custom_cue_list.append(vc)
    custom_cue_list.append(act)
    
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
    script['ui_properties'] = {
        'warning': 0,
    }

    try:
        validate_template(script)
    except xmlschema_exceptions.XMLSchemaValidationError as e:
        Logger.error("Script validation failed. Please check the template.")
        Logger.error(f"Validation error: {e}")
    finally:
        # remove dates and ids so we send it empty
        script.created = None
        script.modified = None
        script.id = None
        script.cuelist.id = None
        script.cuelist.contents[0]['id'] = None
        script.cuelist.contents[1]['id'] = None
        script.cuelist.contents[2]['id'] = None

        return script

    
def validate_template(project_template):
    writer = XmlReaderWriter(schema_name = "script", xmlfile = None)
    result=writer.validate_object(project_template)
    Logger.debug(f'initial template validation result: {result}')


    