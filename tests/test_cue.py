"""Unit testing for Cue objects generation"""

from cuemsutils.cues.Cue import Cue
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
