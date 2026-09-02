from .MediaCue import MediaCue
from ..tools.CTimecode import CTimecode
from ..helpers import ensure_items

REQ_ITEMS = {
    'opacity': 100,  # Default to fully opaque — 0-100 percent scale (cms:PercentType)
}


class VideoCue(MediaCue):
    """A cue for handling video playback and control.

    This class extends MediaCue to provide specific functionality for video playback,
    including frame rate handling and OSC communication for video routing.
    """

    #: Declared fields and their defaults for this class alone;
    #: :meth:`CuemsDict.declared_defaults` accumulates the chain.
    DECLARED_DEFAULTS = REQ_ITEMS

    #: T013. Overrides ``Cue``'s plain ``CTimecode`` factory for the two
    #: timecode marks with a 25fps one.
    # TODO: Adjust framerates for universal use, by now 25 fps for video
    RUNTIME_FIELDS = {
        '_player': None,
        '_osc_route': None,
        '_go_thread': None,
        '_start_mtc': lambda: CTimecode(framerate=25),
        '_end_mtc': lambda: CTimecode(framerate=25),
    }

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

        # The ~18 lines that stood here were **unreachable** and are deleted
        # rather than corrected (T053, FR-017). They sat below an
        # unconditional ``return super().check_mappings()`` — added at some
        # point to short-circuit the method — so no test and no consumer could
        # reach them, and nothing would have noticed if they were wrong.
        #
        # They were wrong. This body indexed
        # ``settings.project_node_mappings['video'][0]['outputs']`` while
        # ``ConfigManager``'s live walk indexed the same data as
        # ``['video']`` groups without the ``[0]``, and a third shape existed
        # in ``ProjectMappings.process_network_mappings``. Three mutually
        # incompatible readings of one document (F15), two of them fossilised.
        #
        # Preserving either fossil would mean choosing between them on **no
        # evidence**: a shape assumption no test can reach is not a contract.
        # The one live shape is ``ConfigManager``'s, and it is now the derived
        # one — ``cuemsutils.config.mappings`` states it, so a fourth reading
        # cannot be invented by accident.
