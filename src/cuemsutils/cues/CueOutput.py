from ..helpers import CuemsDict
class CueOutput(CuemsDict):
    def __init__(self, init_dict = None):
        if init_dict:
            super().__init__(init_dict)
    
    def __json__(self):
        return {type(self).__name__: dict(self.items())}

class AudioCueOutput(CueOutput):
    pass

class VideoCueOutput(CueOutput):
    pass

class DmxCueOutput(CueOutput):
    pass
