from time import sleep

from .MediaCue import MediaCue
from ..helpers import ensure_items
from ..log import logged, Logger

REQ_ITEMS = {
    'master_vol': 0
}

class AudioCue(MediaCue):
    """A cue for handling audio playback and control.
    
    This class extends MediaCue to provide specific functionality for audio playback,
    including volume control and OSC communication for audio routing.
    """
    
    def __init__(self, init_dict = None):
        """Initialize an AudioCue.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to set initial properties.
        """
        if init_dict:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
            super().__init__(init_dict)

        self._player = None
        self._osc_route = None

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
                while self._player.is_alive() and (mtc.main_tc.milliseconds < self._end_mtc.milliseconds):
                    sleep(0.005)

                if self._local:
                    # Recalculate offset and apply
                    self._end_mtc = self._start_mtc + (duration)
                    offset_to_go = float(-(self._start_mtc.milliseconds) + self.media.regions[0].in_time.milliseconds)
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
        if not settings.project_node_mappings:
            return True

        found = True
        map_list = ['default']

        if settings.project_node_mappings['audio']['outputs']:
            for elem in settings.project_node_mappings['audio']['outputs']:
                for map in elem['mappings']:
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
