from time import sleep
from deprecated import deprecated

from .MediaCue import MediaCue
from ..helpers import ensure_items
from ..log import logged, Logger

REQ_ITEMS = {
    # Declared here rather than on MediaCue because script.xsd declares
    # fade_profiles on AudioCueType and VideoCueType, not on MediaCueType
    # (feature 004, T059).
    'fade_profiles': None,
    'master_vol': 100,  # Default to full volume — 0-100 percent scale (cms:PercentType)
}

class AudioCue(MediaCue):
    """A cue for handling audio playback and control.
    
    This class extends MediaCue to provide specific functionality for audio playback,
    including volume control and OSC communication for audio routing.
    """

    #: Declared fields and their defaults for this class alone;
    #: :meth:`CuemsDict.declared_defaults` accumulates the chain.
    DECLARED_DEFAULTS = REQ_ITEMS

    #: T012.
    RUNTIME_FIELDS = {
        '_player': None,
        '_osc_route': None,
    }

    def __init__(self, init_dict = None):
        """Initialize an AudioCue.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to set initial properties.
        """
        if not init_dict:
            init_dict = REQ_ITEMS
        else:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
        super().__init__(init_dict)

    def get_master_vol(self):
        """Get the master volume level.
        
        Returns:
            float: The master volume level.
        """
        return super().__getitem__('master_vol')

    def set_master_vol(self, master_vol):
        """Set the master volume level.
        
        Args:
            master_vol (float): The new master volume level.
        """
        super().__setitem__('master_vol', master_vol)

    master_vol = property(get_master_vol, set_master_vol)

    def player(self, player):
        """Set the audio player instance.
        
        Args:
            player: The audio player instance to use.
        """
        self._player = player

    def osc_route(self, osc_route):
        """Set the OSC route for audio control.
        
        Args:
            osc_route (str): The OSC route to use for audio control.
        """
        self._osc_route = osc_route

    @deprecated(
        reason="Use loop_cue from CueHandler instead",
        version="0.0.9rc5"
    )
    @logged
    def audio_media_loop(self, ossia, mtc):
        """Handle the audio media playback loop.
        
        This method manages the playback loop for audio media, including handling
        looping behavior and OSC communication for timing control.
        
        Args:
            ossia: The OSC communication interface.
            mtc: The MIDI Time Code interface.
        """
        try:
            loop_counter = 0
            duration = self.media.regions[0].out_time - self.media.regions[0].in_time

            while not self.media.regions[0].loop or loop_counter < self.media.regions[0].loop:
                while self._player.is_alive() and (mtc.main_tc.milliseconds_rounded < self._end_mtc.milliseconds_rounded):
                    sleep(0.005)

                if self._local:
                    # Recalculate offset and apply
                    self._end_mtc = self._start_mtc + (duration)
                    offset_to_go = -self._start_mtc.milliseconds_exact + self.media.regions[0].in_time.milliseconds_exact
                    try:
                        key = f'{self._osc_route}/offset'
                        ossia.send_message(key, offset_to_go)
                    except KeyError:
                        Logger.debug(
                            f'Key error 3 in go_callback {key}',
                            extra = {"caller": self.__class__.__name__}
                        )

                loop_counter += 1

            if self._local:                
                try:
                    key = f'{self._osc_route}/mtcfollow'
                    ossia.send_message(key, 0)
                except KeyError:
                    Logger.debug(
                        f'Key error 4 in go_callback {key}',
                        extra = {"caller": self.__class__.__name__}
                    )

        except AttributeError:
            pass

    def stop(self):
        """Stop the audio playback.
        
        This method stops the audio player and sets the stop request flag.
        """
        self._stop_requested = True
        if self._player and self._player.is_alive():
            self._player.kill()

    def check_mappings(self, settings):
        """Check if the audio output mappings are valid.
        
        Args:
            settings: The settings containing project node mappings.
            
        Returns:
            bool: True if the mappings are valid, False otherwise.
        """
        return super().check_mappings()

        # The ~18 lines that stood here were **unreachable** and are deleted
        # rather than corrected (T054, FR-017). They sat below an
        # unconditional ``return super().check_mappings()`` — added at some
        # point to short-circuit the method — so no test and no consumer could
        # reach them, and nothing would have noticed if they were wrong.
        #
        # They were wrong. This body indexed
        # ``settings.project_node_mappings['audio'][0]['outputs']`` while
        # ``ConfigManager``'s live walk indexed the same data as
        # ``['audio']`` groups without the ``[0]``, and a third shape existed
        # in ``ProjectMappings.process_network_mappings``. Three mutually
        # incompatible readings of one document (F15), two of them fossilised.
        #
        # Preserving either fossil would mean choosing between them on **no
        # evidence**: a shape assumption no test can reach is not a contract.
        # The one live shape is ``ConfigManager``'s, and it is now the derived
        # one — ``cuemsutils.config.mappings`` states it, so a fourth reading
        # cannot be invented by accident.
