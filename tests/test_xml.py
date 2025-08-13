'''Integration test for the XML Builder and Parser classes'''
import typing
from logging import DEBUG, INFO
from os import path
from xml.etree.ElementTree import ElementTree, Element

from cuemsutils.cues import ActionCue, AudioCue, DmxCue, CuemsScript, CueList, VideoCue
from cuemsutils.cues.MediaCue import Media, Region

from cuemsutils.xml import XmlReaderWriter
from cuemsutils.xml.XmlBuilder import XmlBuilder

def create_dummy_script():
    target_uuid = '1f301cf8-dd03-4b40-ac17-ef0e5e7988be'
    c = ActionCue({
        'loop': 0,
        'action_target': target_uuid,
        'action_type': 'play',
        'ui_properties': {
            'icon': 'icon.png',
            'color': '#ffffff',
            'timeline_position': {
                'x': 0,
                'y': 0
            },
            'warning': 0
        }
    })
    c2 = VideoCue({
        'id': target_uuid,
        'loop': 0,
        'Media': Media({
            'file_name': 'file_video.ext',
            'id': '',
            'duration': '00:00:00.000',
            'regions' : [
                Region({
                    'id': 0, 'loop': 2, 'in_time': None, 'out_time': None
                })
            ]
        })
    })
    ac = AudioCue({
        'master_vol': 66,
        'Media': Media({
            'file_name': 'file.ext',
            'id': '',
            'duration': '00:00:00.000',
            'regions': [
                Region({
                    'id': 0,
                    'loop': 2,
                    'in_time': None,
                    'out_time': None
                })
            ]
        })
    })
    c3 = VideoCue({
        'loop': 0,
        'Media': Media({
            'file_name': 'file_video.ext',
            'id': '',
            'duration': '00:00:00.000',
            'regions' : [
                Region({
                    'id': 0, 'loop': 2, 'in_time': None, 'out_time': None
                })
            ]
        })
    })
    #ac.outputs = {'stereo': 1}
    #d_c = DmxCue(time=23, scene={0:{0:10, 1:50}, 1:{20:23, 21:255}, 2:{5:10, 6:23, 7:125, 8:200}}, init_dict={'loop' : 3})
    #d_c.outputs = {'universe0': 3}
    
    custom_cue_list = CueList({'contents': [c]})
    custom_cue_list.append(c2)
    custom_cue_list.append(ac)
    custom_cue_list.append(c3)
    
    script = CuemsScript({
        'CueList': custom_cue_list,
        'ui_properties': {'icon': 'icon.png', 'color': '#000000'}
    })
    script.name = "Test Script"
    script.description = "This is a test script"
    return script, [c, c2, ac, c3]

def test_cues():
    script, cues = create_dummy_script()

    assert script.ui_properties['icon'] == 'icon.png'
    assert script.ui_properties['color'] == '#000000'

    assert script.cuelist.contents[0] == cues[0]
    assert script.cuelist.contents[1] == cues[1]
    assert script.cuelist.contents[2] == cues[2]
    #assert script.cuelist.contents[3] == d_c

    assert isinstance(script, CuemsScript)
    assert isinstance(script.cuelist.contents[0], ActionCue)
    assert isinstance(script.cuelist.contents[1], VideoCue)
    assert isinstance(script.cuelist.contents[2], AudioCue)

    assert script.cuelist.contents[0].action_target == script.cuelist.contents[1].id
    assert script.cuelist.contents[0].action_type == 'play'

@typing.no_type_check
def test_XmlBuilder(caplog):

    caplog.set_level(DEBUG)
    script, _ = create_dummy_script()
    xml_data = XmlBuilder(
        script,
        {'cms':'https://stagelab.coop/'},
        'script'
    ).build()

    assert isinstance(xml_data, ElementTree)
    assert xml_data.getroot().tag == '{https://stagelab.coop/}CuemsProject'
    assert xml_data.getroot().find('CuemsScript').find('name').text == 'Test Script'

    xmlscript = xml_data.getroot().find('CuemsScript')
    assert xmlscript.find('description').text == 'This is a test script'
    assert type(xmlscript.find('id')) == Element
    assert type(xmlscript.find('modified')) == Element
    assert type(xmlscript.find('modified')) == Element
    assert xmlscript.find('created').text == xmlscript.find('modified').text

    script_ui_properties = xmlscript.find('ui_properties')
    assert script_ui_properties.find('icon').text == 'icon.png'
    assert script_ui_properties.find('color').text == '#000000'

    cuelist = xmlscript.find('CueList')
    assert type(cuelist) == Element
    assert type(cuelist.find('contents')) == Element

    contents = cuelist.find('contents')
    assert contents.__len__() == 4
    assert contents[0].tag == 'ActionCue'
    assert contents[0].find('loop').text == '0'
    action_cue_ui_properties = contents[0].find('ui_properties')
    assert type(action_cue_ui_properties) == Element
    assert action_cue_ui_properties.find('icon').text == 'icon.png'
    assert action_cue_ui_properties.find('color').text == '#ffffff'
    assert contents[1].tag == 'VideoCue'
    assert contents[2].tag == 'AudioCue'
    assert contents[2].find('master_vol').text == '66'
    audio_media = contents[2].find('Media')
    assert type(audio_media) == Element
    assert audio_media.find('file_name').text == 'file.ext'
    assert audio_media.find('regions').find('Region').find('loop').text == '2'
    assert contents[3].tag == 'VideoCue'
    assert contents[3].find('Media').find('file_name').text == 'file_video.ext'

reloaded_script, _ = create_dummy_script()
TMP_FILE = path.dirname(__file__) + '/tmp/test_script.xml'

def test_XmlWriter(caplog):
    caplog.set_level(DEBUG)
    tmpfile = TMP_FILE
    writer = XmlReaderWriter(
        schema_name = 'script',
        xmlfile = tmpfile
    )

    writer.write_from_object(reloaded_script)

    assert writer.validate() == None
    assert path.isfile(tmpfile) == True

def test_XmlReader(caplog):
    from cuemsutils.log import Logger
    caplog.set_level(INFO)
    tmpfile = TMP_FILE

    reader = XmlReaderWriter(
        schema_name = 'script',
        xmlfile = tmpfile
    )
    readed = reader.read_to_objects()
    
    assert path.isfile(tmpfile) == True
    assert type(readed) == CuemsScript
    assert type(readed.created) == str
    Logger.info(readed.__dict__)
    assert type(readed.cuelist) == CueList
    assert len(readed.cuelist.contents) == 4
    assert type(readed.cuelist.contents[0]) == ActionCue
    assert type(readed.cuelist.contents[1]) == VideoCue
    assert type(readed.cuelist.contents[2]) == AudioCue
    assert type(readed.cuelist.contents[3]) == VideoCue
    assert reloaded_script == readed

TEST_JSON_FILE = path.dirname(__file__) + '/data/sample_script.json'
TMP_JSON_FILE = path.dirname(__file__) + '/tmp/test_json_script.xml'

def test_jsonload(caplog):
    ## ARRANGE
    from cuemsutils.xml.Parsers import CuemsParser
    from cuemsutils.xml.XmlReaderWriter import XmlWriter
    from cuemsutils.cues import CuemsScript, CueList
    from cuemsutils.tools.CTimecode import CTimecode
    import json

    caplog.set_level(DEBUG)

    with open(TEST_JSON_FILE) as json_file:
        data = json.load(json_file)
        assert type(data) == dict
        assert data['action'] == 'project_save'
        json_script = data['value']

    ## ACT
    parsed = CuemsParser(json_script).parse()
    writer = XmlReaderWriter(
        schema_name = 'script',
        xmlfile = TMP_JSON_FILE
    )
    writer.write_from_object(parsed)

    ## ASSERT
    assert writer.validate() == None
    assert json_script != None
    assert json_script['CuemsScript']['name'] == 'Prueba'
    assert json_script['CuemsScript']['description'] == None
    assert type(parsed) == CuemsScript
    assert type(parsed.cuelist) == CueList
    assert len(parsed.cuelist.contents) == 4
    assert parsed.cuelist.offset == None
    assert type(parsed.cuelist.postwait) == CTimecode
    assert type(parsed.cuelist.prewait) == CTimecode

def test_json_dump():
    import json
    from cuemsutils.create_script import create_script

    script = create_script()
    audio_cue = script.cuelist.contents[0]
    json_string = json.dumps(script)
    json_string = '{"CuemsScript": ' + json_string + '}'
    json_self_str = script.to_json()

    assert json_string != None
    assert type(json_string) == str

    assert json_self_str != None
    assert type(json_self_str) == str

    assert json_string == json_self_str

    assert isinstance(audio_cue, AudioCue)
    assert isinstance(audio_cue.media, Media)
    assert isinstance(audio_cue.media.regions, list)
    assert isinstance(audio_cue.media.regions[0], Region)

    assert "Region" in json_self_str

def test_json_readwrite(caplog):
    ## ARRANGE
    from cuemsutils.xml.Parsers import CuemsParser
    import json

    caplog.set_level(DEBUG)
    TMP_PARSED_FILE = path.dirname(__file__) + '/tmp/test_script.json'

    with open(TEST_JSON_FILE) as json_file:
        data = json.load(json_file)
        assert type(data) == dict
        assert data['action'] == 'project_save'
        json_script = data['value']

    parsed = CuemsParser(json_script).parse()

    with open(TMP_PARSED_FILE, 'w') as json_file:
        loaded_parsed = json.dumps(
            {
                'action': 'project_save',
                'value': {'CuemsScript': parsed}
            },
            indent = 4
        )
        json_file.write(loaded_parsed)

    with open(TMP_PARSED_FILE) as tmp_json_file:
        tmp_data = json.load(tmp_json_file)
        assert type(tmp_data) == dict
        assert tmp_data['action'] == 'project_save'
        json_parsed = tmp_data['value']

    assert json_script == json_parsed

def test_settings():
    from cuemsutils.xml import Settings
    SETTINGS_PATH = path.dirname(__file__) + '/data/settings.xml'

    settings = Settings(SETTINGS_PATH)
    assert settings.validate() == None
    assert settings.read() == None
    assert settings.loaded == True
    assert isinstance(settings.get_dict(), dict)

def test_networkmap():
    from cuemsutils.xml import NetworkMap
    NETWORKMAP_PATH = path.dirname(__file__) + '/data/network_map.xml'
    
    networkmap = NetworkMap(NETWORKMAP_PATH)
    assert networkmap.validate() == None
    assert networkmap.read() == None
    assert networkmap.loaded == True
    assert isinstance(networkmap.processed, list)
    assert networkmap.processed[0]['CuemsNode']['online'] == 'True'

def test_projectmappings():
    from cuemsutils.xml import ProjectMappings
    PROJECTMAPPINGS_PATH = path.dirname(__file__) + '/data/project_mappings.xml'
    
    projectmappings = ProjectMappings(PROJECTMAPPINGS_PATH)
    assert projectmappings.validate() == None
    assert projectmappings.read() == None
    assert projectmappings.loaded == True
