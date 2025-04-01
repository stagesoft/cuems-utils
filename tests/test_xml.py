'''Integration test for the XML Builder and Parser classes'''
from logging import DEBUG, INFO
from os import path
from xml.etree.ElementTree import ElementTree, Element

from src.cuemsutils.cues import ActionCue, AudioCue, DmxCue, CuemsScript, CueList, VideoCue
from src.cuemsutils.cues.MediaCue import Media, Region

from src.cuemsutils.xml import XmlReader, XmlWriter
from src.cuemsutils.xml.XmlBuilder import XmlBuilder

TMP_FILE = path.dirname(__file__) + '/tmp/test_script.xml'

def create_dummy_script():
    target_uuid = '1f301cf8-dd03-4b40-ac17-ef0e5e7988be'
    c = ActionCue({'id': 33, 'loop': 0, 'action_target': target_uuid, 'action_type': 'play'})
    c2 = VideoCue({
        'id': None,
        'loop': 0,
        'media': Media({
            'file_name': 'file_video.ext',
            'regions' : [
                Region({
                    'id': 0, 'loop': 2, 'in_time': None, 'out_time': None
                })
            ]
        }),
        'uuid': target_uuid
    })
    ac = AudioCue({
        'id': 45,
        'master_vol': 66,
        'media': Media({
            'file_name': 'file.ext',
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
        'id': None,
        'loop': 0,
        'media': Media({
            'file_name': 'file_video.ext',
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
    
    script = CuemsScript({'cuelist': custom_cue_list})
    script.name = "Test Script"
    script.description = "This is a test script"
    return script, [c, c2, ac, c3]

def test_cues():
    script, cues = create_dummy_script()

    assert script.cuelist.contents[0] == cues[0]
    assert script.cuelist.contents[1] == cues[1]
    assert script.cuelist.contents[2] == cues[2]
    #assert script.cuelist.contents[3] == d_c

    assert isinstance(script, CuemsScript)
    assert isinstance(script.cuelist.contents[0], ActionCue)
    assert isinstance(script.cuelist.contents[1], VideoCue)
    assert isinstance(script.cuelist.contents[2], AudioCue)

def test_XmlBuilder():
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
    assert type(xmlscript.find('uuid')) == Element
    assert type(xmlscript.find('modified')) == Element
    assert type(xmlscript.find('modified')) == Element
    assert xmlscript.find('created').text == xmlscript.find('modified').text

    cuelist = xmlscript.find('cuelist')
    assert type(cuelist) == Element
    assert type(cuelist.find('CueList')) == Element
    assert type(cuelist.find('CueList').find('contents')) == Element

    contents = cuelist.find('CueList').find('contents')
    assert contents.__len__() == 4
    assert contents[0].tag == 'ActionCue'
    assert contents[0].find('id').text == '33'
    assert contents[0].find('loop').text == '0'
    assert contents[1].find('id').text == None
    assert contents[1].tag == 'VideoCue'
    assert contents[2].tag == 'AudioCue'
    assert contents[2].find('master_vol').text == '66'
    assert contents[2].find('media').find('file_name').text == 'file.ext'
    audio_media = contents[2].find('media')
    assert audio_media.find('regions').find('Region').find('loop').text == '2'
    assert contents[3].tag == 'VideoCue'
    assert contents[3].find('media').find('file_name').text == 'file_video.ext'

reloaded_script, _ = create_dummy_script()

def test_XmlWriter():
    tmpfile = TMP_FILE
    writer = XmlWriter(
        schema_name = 'script',
        xmlfile = tmpfile
    )

    writer.write_from_object(reloaded_script)

    assert writer.validate() == None
    assert path.isfile(tmpfile) == True

def test_XmlReader(caplog):
    caplog.set_level(DEBUG)
    tmpfile = TMP_FILE
    assert path.isfile(tmpfile) == True

    reader = XmlReader(
        schema_name = 'script',
        xmlfile = tmpfile
    )
    readed = reader.read_to_objects()
    assert type(readed) == CuemsScript
    assert type(readed.created) == str
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
    from src.cuemsutils.xml.Parsers import CuemsParser
    from src.cuemsutils.xml.XmlReaderWriter import XmlWriter
    import json

    caplog.set_level(INFO)

    with open(TEST_JSON_FILE) as json_file:
        data = json.load(json_file)
        assert type(data) == dict
        assert data['action'] == 'project_save'
        json_script = data['value']

    ## ACT
    parsed = CuemsParser(json_script).parse()
    writer = XmlWriter(
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

def test_json_dump():
    import json

    json_string = json.dumps(reloaded_script)

    json_string = '{"CuemsScript": ' + json_string + '}'

    assert json_string != None
    assert type(json_string) == str

    json_self_str = reloaded_script.to_json()
    assert json_self_str != None
    assert type(json_self_str) == str
    assert json_string == json_self_str


def test_json_readwrite(caplog):
    ## ARRANGE
    from src.cuemsutils.xml.Parsers import CuemsParser
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
        loaded_parsed = json.dumps({'action': 'project_save', 'value': {'CuemsScript': parsed}}, indent = 4)
        json_file.write(loaded_parsed)

    with open(TMP_PARSED_FILE) as tmp_json_file:
        tmp_data = json.load(tmp_json_file)
        assert type(tmp_data) == dict
        assert tmp_data['action'] == 'project_save'
        json_parsed = tmp_data['value']

    assert json_script == json_parsed

# %%
