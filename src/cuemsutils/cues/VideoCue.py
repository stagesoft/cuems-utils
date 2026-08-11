from .MediaCue import MediaCue
from ..tools.CTimecode import CTimecode
from ..helpers import ensure_items
from ..log import Logger

REQ_ITEMS = {
    'opacity': 100,  # Default to fully opaque — 0-100 percent scale (cms:PercentType)
    # Declared here rather than on MediaCue because script.xsd declares
    # fade_profiles on AudioCueType and VideoCueType, not on MediaCueType
    # (feature 004, T059).
    'fade_profiles': None,
}


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
            init_dict = REQ_ITEMS
        else:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
        super().__init__(init_dict)

        self._player = None
        self._osc_route = None
        self._go_thread = None

        # TODO: Adjust framerates for universal use, by now 25 fps for video
        self._start_mtc = CTimecode(framerate=25)
        self._end_mtc = CTimecode(framerate=25)

    def get_opacity(self):
        """Get the cue's configured opacity level.

        Returns:
            int: The opacity level, 0-100 (applied uniformly across all
                layers of this cue).
        """
        return super().__getitem__('opacity')

    def set_opacity(self, opacity):
        """Set the cue's configured opacity level.

        Args:
            opacity (int): The new opacity level, 0-100.
        """
        super().__setitem__('opacity', opacity)

    opacity = property(get_opacity, set_opacity)

    def items(self):
        """Get all items in the cue as a dictionary.

        Returns:
            dict_items: A view of the cue's items, with required items sorted first.
        """
        x = dict(super().items())
        for k in sorted(REQ_ITEMS.keys()):
            x[k] = self[k]
        return x.items()

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
