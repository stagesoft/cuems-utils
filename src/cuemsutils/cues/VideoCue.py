from .MediaCue import MediaCue
from ..tools.CTimecode import CTimecode
from ..log import Logger



class VideoCue(MediaCue):
    """A cue for handling video playback and control.
    
    This class extends MediaCue to provide specific functionality for video playback,
    including frame rate handling and OSC communication for video routing.
    """
    
    def __init__(self, init_dict = None):
        """Initialize a VideoCue.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to set initial properties.
        """
        if not init_dict:
            super().__init__()
        else:
            super().__init__(init_dict)

        self._player = None
        self._osc_route = None
        self._go_thread = None

        # TODO: Adjust framerates for universal use, by now 25 fps for video
        self._start_mtc = CTimecode(framerate=25)
        self._end_mtc = CTimecode(framerate=25)

    def player(self, player):
        """Set the video player instance.
        
        Args:
            player: The video player instance to use.
        """
        self._player = player

    def osc_route(self, osc_route):
        """Set the OSC route for video control.
        
        Args:
            osc_route (str): The OSC route to use for video control.
        """
        self._osc_route = osc_route

    def items(self):
        """Get all items in the cue as a dictionary.
        
        Returns:
            dict_items: A view of the cue's items.
        """
        x = dict(super().items())
        return x.items()

    def stop(self):
        """Stop the video playback.
        
        This method sets the stop request flag to halt video playback.
        """
        self._stop_requested = True

    def check_mappings(self, settings):
        """Check if the video output mappings are valid.
        
        Args:
            settings: The settings containing project node mappings.
            
        Returns:
            bool: True if the mappings are valid, False otherwise.
        """
        return super().check_mappings()

        if not settings.project_node_mappings:
            return True

        found = True
        map_list = ['default']

        # DEV: List first index is an artifact of the way the mappings are parsed
        Logger.debug(f'VideoCue check_mappings: {settings.project_node_mappings}')
        if settings.project_node_mappings['video'][0]['outputs']:
            for elem in settings.project_node_mappings['video'][0]['outputs']:
                elem = elem['output']
                Logger.debug(f'VideoCue elem: {elem}')
                for map in elem['mappings']:
                    Logger.debug(f'VideoCue map: {map}')
                    map_list.append(map['mapped_to'])

        for output in self.outputs:
            if output['output_name'][:36] == settings.node_conf['uuid']:
                self._local = True
                if output['output_name'][37:] not in map_list:
                    found = False
                    break
            else:
                self._local = False
                found = True
            
        return found
