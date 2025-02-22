class CueOutput(dict):
    def __init__(self, init_dict = None):
        if init_dict:
            super().__init__(init_dict)

class AudioCueOutput(CueOutput):
    pass

class VideoCueOutput(CueOutput):
    pass

class DmxCueOutput(CueOutput):
    pass
