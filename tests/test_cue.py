"""Unit testing for Cue objects generation"""

from cuemsutils.cues.Cue import Cue
from cuemsutils.cues.MediaCue import MediaCue
from cuemsutils.cues.CueOutput import AudioCueOutput, VideoCueOutput, DmxCueOutput
from cuemsutils.helpers import new_uuid

def test_simple_cue():
    ## Arrange
    uuid = new_uuid()
    ui_dict = {'id': uuid, 'loop': False}
    
    ## Act
    cue = Cue(ui_dict)

    ## Assert
    assert cue.id == uuid
    assert cue.loop == False

def test_cue_as_dict_key():
    ## Arrange
    uuid = new_uuid()
    ui_dict = {'id': uuid, 'loop': False}
    dict_obj = {}
    ## Act
    cue = Cue(ui_dict)
    dict_obj[cue] = 'value'

    ## Assert
    assert dict_obj[cue] == 'value'

def test_cue_and_uuid_hash_are_equal():
    ## Arrange
    uuid = new_uuid()
    ui_dict = {'id': uuid, 'loop': False}
    ## Act
    cue = Cue(ui_dict)
    ## Assert
    assert hash(cue) == hash(uuid)

def test_media_cue_get_all_output_names():
    ## Arrange
    media_cue = MediaCue()
    media_cue.outputs = [
        AudioCueOutput({
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
        }),
        AudioCueOutput({
            "output_name": "0367f391-ebf4-48b2-9f26-000000000001_system:playback_2",
            "output_vol": 80,
            "channels": [
                {
                    "channel": {
                        "channel_num": 0,
                        "channel_vol": 80
                    }
                }
            ]
        }),
        VideoCueOutput({
            "output_name": "0367f391-ebf4-48b2-9f26-000000000001_0",
            "output_geometry": {
                "x_scale": 1,
                "y_scale": 1,
            }
        }),
        DmxCueOutput({
            "output_name": "0367f391-ebf4-48b2-9f26-000000000001"
        })
    ]
    ## Act
    output_names = media_cue.get_all_output_names()
    ## Assert
    assert output_names == [
        ('0367f391-ebf4-48b2-9f26-000000000001', 'system:playback_1'),
        ('0367f391-ebf4-48b2-9f26-000000000001', 'system:playback_2'),
        ('0367f391-ebf4-48b2-9f26-000000000001', '0'),
        ('0367f391-ebf4-48b2-9f26-000000000001', '')
    ]


def test_media_cue_localize_cue():
    ## Arrange
    media_cue = MediaCue()
    media_cue.outputs = [
        AudioCueOutput({
            "output_name": "0367f391-ebf4-48b2-9f26-000000000001_system:playback_1",
        })
    ]
    ## Act
    media_cue.localize_cue('0367f391-ebf4-48b2-9f26-000000000001')
    ## Assert
    assert media_cue._local == True
    media_cue.localize_cue('0367f391-ebf4-48b2-9f26-000000000002')
    ## Assert
    assert media_cue._local == False
