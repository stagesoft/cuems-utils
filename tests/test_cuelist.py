"""Test CueList object generation and manipulation"""
from cuemsutils.cues import AudioCue, CueList
from cuemsutils.cues.Cue import Cue

def test_simple_cuelist():
    ## Arrange
    c = Cue({'loop': False})
    c2 = Cue({'loop': False})
    ac = AudioCue({'loop': True, 'media': 'file.ext', 'master_vol': 66} )
    
    ## Act
    custom_cue_list = CueList({'contents': [c]})
    custom_cue_list.append(c2)
    custom_cue_list.append(ac)

    ## Assert
    assert custom_cue_list.contents[0] == c
    assert custom_cue_list.contents[1] == c2
    assert custom_cue_list.contents[2] == ac

    assert isinstance(custom_cue_list.contents[0], Cue)


def test_cuelist_errors():
    ## Arrange
    c = Cue({'loop': False})
    c2 = {'loop': False}

    ## Act
    custom_cue_list = CueList({'contents': [c]})
    try:
        custom_cue_list.append(c2)
    except TypeError as e:
        assert str(e) == f'Item {c2} is not a Cue object'

    ## Assert
    assert custom_cue_list.contents[0] == c
    try:
        custom_cue_list.contents[1]
    except IndexError as e:
        assert str(e) == 'list index out of range'
