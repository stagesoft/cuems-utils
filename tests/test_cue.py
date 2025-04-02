"""Unit testing for Cue objects generation"""

from src.cuemsutils.cues.Cue import Cue
from src.cuemsutils.helpers import new_uuid

def test_simple_cue():
    ## Arrange
    uuid = new_uuid()
    ui_dict = {'id': uuid, 'loop': False}
    
    ## Act
    cue = Cue(ui_dict)

    ## Assert
    assert cue.id == uuid
    assert cue.loop == False
