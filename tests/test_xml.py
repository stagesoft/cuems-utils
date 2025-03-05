'''Integration test for the XML Builder and Parser classes'''
from os import path
from xml.etree.ElementTree import ElementTree, Element
from logging import DEBUG

from cuemsutils.cues.Cue import Cue
from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.cues.DmxCue import DmxCue
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.cues.CueList import CueList

from cuemsutils.xml.XmlBuilder import XmlBuilder
from cuemsutils.xml.XmlReaderWriter import XmlReader, XmlWriter
from cuemsutils.xml.DictParser import CuemsParser

FOPO = int(DEBUG)

def create_dummy_script():
    c = Cue({'id': 33, 'loop': 0})
    c2 = Cue({'id': None, 'loop': 0})
    ac = AudioCue({'id': 45, 'loop': 2, 'media': {'file_name': 'file.ext'}, 'master_vol': 66} )
    #ac.outputs = {'stereo': 1}
    #d_c = DmxCue(time=23, scene={0:{0:10, 1:50}, 1:{20:23, 21:255}, 2:{5:10, 6:23, 7:125, 8:200}}, init_dict={'loop' : 3})
    #d_c.outputs = {'universe0': 3}
    c3 = Cue({'id': 5, 'loop': 0})
    g = Cue({'id': 33, 'loop': 0})
    
    custom_cue_list = CueList({'contents': [c]})
    custom_cue_list.append(c2)
    custom_cue_list.append(ac)
    #custom_cue_list = CueList([c, c2])
    #custom_cue_list.append(d_c)
    
    script = CuemsScript({'cuelist': custom_cue_list})
    script.name = "Test Script"
    script.description = "This is a test script"
    return script, [c, c2, ac]

def test_cues():
    script, cues = create_dummy_script()

    assert script.cuelist.contents[0] == cues[0]
    assert script.cuelist.contents[1] == cues[1]
    assert script.cuelist.contents[2] == cues[2]
    #assert script.cuelist.contents[3] == d_c

    assert isinstance(script, CuemsScript)
    assert isinstance(script.cuelist.contents[0], Cue)

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
    assert contents.__len__() == 3
    assert contents[0].find('id').text == '33'
    assert contents[0].find('loop').text == '0'
    assert contents[1].find('id').text == None
    assert contents[1].tag == 'Cue'
    assert contents[2].tag == 'AudioCue'
    assert contents[2].find('media').text == 'file.ext'
    assert contents[2].find('master_vol').text == '66'
    assert contents[2].find('loop').text == '2'

def test_XmlWriter():
    script, _ = create_dummy_script()
    tmpfile = '/tmp/test_script.xml'
    writer = XmlWriter(
        schema_name = 'script',
        xmlfile = tmpfile
    )

    writer.write_from_object(script)

    # assert writer.validate() == True
    assert path.isfile(tmpfile) == True

"""

reader = XmlReader(schema = '/home/ion/src/cuems/python/cuems-engine/src/cuems/cues.xsd', xmlfile = '/home/ion/src/cuems/python/cuems-engine/src/cuems/cues.xml')
xml_dict = reader.read()
print("-------++++++---------")
print('DICT from XML:')
print(xml_dict)
print("-------++++++---------")
store = CuemsParser(xml_dict).parse()
print("--------------------")
print('Re-build object from xml:')
print(store)
print("--------------------")

if str(script) == str(store):
    print('original object and rebuilt object are EQUAL :)')
else:
    print('original object and rebuilt object are NOT equal :(')



print('xxxxxxxxxxxxxxxxxxxx')
for o in store.cuelist.contents:
    print(type(o))
    print(o)
    if isinstance(o, DmxCue):
        print('Dmx scene, universe0, channel0, value : {}'.format(o.scene.universe(0).channel(0)))

"""
# %%
