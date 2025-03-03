"""Unit testing for Cue objects generation"""

from cuemsutils.cues.Cue import Cue

def test_simple_cue():
    ## Arrange
    ui_dict = {'id': 10, 'loop': False}
    
    ## Act
    cue = Cue(ui_dict)

    ## Assert
    assert cue.id == 10
    assert cue.loop == False
