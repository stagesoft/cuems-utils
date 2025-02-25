'''Integration test for the XML Builder and Parser classes'''
from cuemsutils.cues.Cue import Cue
from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.cues.DmxCue import DmxCue
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.cues.CueList import CueList

from cuemsutils.xml.DictParser import CuemsParser
from cuemsutils.xml.XmlBuilder import XmlBuilder
from cuemsutils.xml.XmlReaderWriter import XmlReader, XmlWriter


def create_dummy_script():
    c = Cue({'id': 33, 'loop': False})
    c2 = Cue(None, { 'loop': False})
    c3 = Cue(5, {'loop': False})
    ac = AudioCue(
        45, {'loop': True, 'media': 'file.ext', 'master_vol': 66} )

    #ac.outputs = {'stereo': 1}
    #d_c = DmxCue(time=23, scene={0:{0:10, 1:50}, 1:{20:23, 21:255}, 2:{5:10, 6:23, 7:125, 8:200}}, init_dict={'loop' : True})
    #d_c.outputs = {'universe0': 3}
    g = Cue(33, {'loop': False})

    #custom_cue_list = CueList([c, c2])
    custom_cue_list = CueList( c )
    custom_cue_list.append(c2)
    custom_cue_list.append(ac)
    #custom_cue_list.append(d_c)


    script = CuemsScript(cuelist=custom_cue_list)
    script.name = "Test Script"
    script.description = "This is a test script"
    return script

def test_cues():
    script = create_dummy_script()

    assert script.cuelist.contents[0] == Cue(33, {'loop': False})
    assert script.cuelist.contents[1] == Cue(None, { 'loop': False})
    assert script.cuelist.contents[2] == AudioCue(45, {'loop': True, 'media': 'file.ext', 'master_vol': 66} )
    #assert script.cuelist.contents[3] == d_c

    assert isinstance(script, CuemsScript)
    assert isinstance(script.cuelist.contents[0], Cue)


"""
script = test_cues()
# script.name = "Test Script"
print('OBJECT:')
print(script)

xml_data = XmlBuilder(script, {'cms':'http://stagelab.net/cuems'}, '/etc/cuems/script.xsd').build()


writer = XmlWriter(schema = '/home/ion/src/cuems/python/cuems-engine/src/cuems/cues.xsd', xmlfile = '/home/ion/src/cuems/python/cuems-engine/src/cuems/cues.xml')

writer.write(xml_data)

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
