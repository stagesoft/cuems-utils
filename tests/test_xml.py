'''Integration test for the XML Builder and Parser classes'''
from logging import DEBUG
from os import path
from xml.etree.ElementTree import ElementTree, Element

from cuemsutils.cues import ActionCue, AudioCue, DmxCue, CuemsScript, CueList, VideoCue
from cuemsutils.cues.MediaCue import Media, region

from cuemsutils.xml import XmlReader, XmlWriter
from cuemsutils.xml.XmlBuilder import XmlBuilder

TMP_FILE = path.dirname(__file__) + '/tmp/test_script.xml'

def create_dummy_script():
    target_uuid = '1f301cf8-dd03-4b40-ac17-ef0e5e7988be'
    c = ActionCue({'id': 33, 'loop': 0, 'action_target': target_uuid, 'action_type': 'play'})
    c2 = VideoCue({'id': None, 'loop': 0, 'uuid': target_uuid})
    ac = AudioCue({
        'id': 45,
        'master_vol': 66,
        'media': Media({
            'file_name': 'file.ext',
            'regions': {'region': region({
                'id': 0,
                'loop': 2,
                'in_time': None,
                'out_time': None,
            })}
        })
    })
    c3 = VideoCue({
        'id': None,
        'loop': 0,
        'media': Media({
            'file_name': 'file_video.ext',
            'regions' : {'region': region({
                'id': 0, 'loop': 2, 'in_time': None, 'out_time': None
            })}
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

    cuelist = xmlscript.find('CueList')
    assert type(cuelist) == Element
    assert type(cuelist.find('contents')) == Element

    contents = cuelist.find('contents')
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
    assert audio_media.find('regions').find('region').find('loop').text == '2'
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
    assert type(readed.cuelist) == CueList
    assert type(readed.cuelist.contents) == list
    assert len(readed.cuelist.contents) == 4
    assert type(readed.cuelist.contents[0]) == ActionCue
    assert type(readed.cuelist.contents[1]) == VideoCue
    assert type(readed.cuelist.contents[2]) == AudioCue
    assert type(readed.cuelist.contents[3]) == VideoCue
    assert reloaded_script == readed

# def test_jsondump(caplog):
#     from cuemsutils.log import Logger
#     import json
#     caplog.set_level(DEBUG)

#     json_string = json.dumps(reloaded_script)

#     Logger.debug(json_string)
#     assert type(json_string) == str
#     assert json_string != None

def test_jsonload(caplog):
    from cuemsutils.log import Logger
    from cuemsutils.xml.Parsers import CuemsParser
    from cuemsutils.xml.XmlReaderWriter import XmlWriter
    import json

    TMP_FILE = path.dirname(__file__) + '/tmp/test_json_script.xml'
    
    TEST_JSON_FILE = path.dirname(__file__) + '/tmp/sample_script.json'
    caplog.set_level(DEBUG)

    with open(TEST_JSON_FILE) as json_file:
        data = json.load(json_file)
        Logger.debug(data)
        assert type(data) == dict
        assert data['action'] == 'project_save'
        json_script = data['value']
        assert json_script != None
        assert json_script['CuemsScript']['name'] == 'Prueba'
        assert json_script['CuemsScript']['description'] == None
        parsed = CuemsParser(json_script).parse()
        Logger.info(f'Parsed: {parsed}')

        writer = XmlWriter(
            schema_name = 'script',
            xmlfile = TMP_FILE
        )

        writer.write_from_object(parsed)

        assert True == False
        assert type(parsed) == CuemsScript


# %%
