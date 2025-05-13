from ..helpers import CuemsDict

class CueOutput(CuemsDict):
    """Base class for cue output configurations.
    
    This class provides the basic structure for configuring how cues are output
    to different types of devices or systems.
    """
    
    def __init__(self, init_dict = None):
        """Initialize a CueOutput.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to set initial properties.
        """
        if init_dict:
            super().__init__(init_dict)
    
    def __json__(self):
        """Convert the output configuration to a JSON-compatible dictionary.
        
        Returns:
            dict: A dictionary representation of the output configuration.
        """
        return {type(self).__name__: dict(self.items())}

class AudioCueOutput(CueOutput):
    """Output configuration for audio cues.
    
    This class extends CueOutput to provide specific functionality for audio output
    routing and configuration.
    """
    pass

class VideoCueOutput(CueOutput):
    """Output configuration for video cues.
    
    This class extends CueOutput to provide specific functionality for video output
    routing and configuration.
    """
    pass

class DmxCueOutput(CueOutput):
    """Output configuration for DMX cues.
    
    This class extends CueOutput to provide specific functionality for DMX output
    routing and configuration.
    """
    pass
