from collections.abc import Mapping
from cuemsutils.log import Logger
from ..helpers import ensure_items
from .Cue import Cue, CuemsDict
from .CueOutput import DmxCueOutput

REQ_ITEMS = {
    'fadein_time': 0.0,
    'fadeout_time': 0.0,
    'outputs': None,
    'DmxScene': None
}

SCENE_REQ_ITEMS = {
    'id': 0,
    'DmxUniverse': None
}

UNIVERSE_REQ_ITEMS = {
    'universe_num': 0,
    'dmx_channels': None
}

DMXCHANNEL_REQ_ITEMS = {
    'channel': 0,
    'value': 0
}

class DmxCue(Cue):
    """A cue for handling DMX lighting control.
    
    This class extends Cue to provide specific functionality for DMX lighting control,
    including scene management, fade timing, and OSC communication for DMX routing.
    """
    
    def __init__(self, init_dict = None):
        """Initialize a DmxCue.
        
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
        self._offset_route = '/offset'

    def get_fadein_time(self):
        """Get the fade-in time for the DMX cue.
        
        Returns:
            The fade-in time value.
        """
        return super().__getitem__('fadein_time')

    def set_fadein_time(self, fadein_time):
        """Set the fade-in time for the DMX cue.
        
        Args:
            fadein_time: The new fade-in time value.
        """
        super().__setitem__('fadein_time', fadein_time)

    fadein_time = property(get_fadein_time, set_fadein_time)

    def get_fadeout_time(self):
        """Get the fade-out time for the DMX cue.
        
        Returns:
            The fade-out time value.
        """
        return super().__getitem__('fadeout_time')

    
    def set_fadeout_time(self, fadeout_time):
        """Set the fade-out time for the DMX cue.
        
        Args:
            fadeout_time: The new fade-out time value.
        """
        super().__setitem__('fadeout_time', fadeout_time)

    fadeout_time = property(get_fadeout_time, set_fadeout_time)

    def get_outputs(self):
        """Get the output routing configuration.
        
        Returns:
            list: The list of output configurations.
        """
        return super().__getitem__('outputs')

    def set_outputs(self, outputs):
        """Set the output routing configuration.
        
        Args:
            outputs (list): The list of output configurations. Each item can be
                a DmxCueOutput object or a dict that will be converted to DmxCueOutput.
        """
        if outputs is None:
            super().__setitem__('outputs', None)
            return
        
        if not isinstance(outputs, list):
            outputs = [outputs]
        
        converted_outputs = []
        for output in outputs:
            if output is None:
                continue
            if not isinstance(output, DmxCueOutput):
                # Convert dict to DmxCueOutput
                if isinstance(output, dict):
                    # Handle nested dict structure like {"DmxCueOutput": {...}}
                    if 'DmxCueOutput' in output:
                        converted_outputs.append(DmxCueOutput(output['DmxCueOutput']))
                    else:
                        converted_outputs.append(DmxCueOutput(output))
                else:
                    converted_outputs.append(output)
            else:
                converted_outputs.append(output)
        
        super().__setitem__('outputs', converted_outputs)

    outputs = property(get_outputs, set_outputs)

    def get_DmxScene(self):
        """Get the DMX scene for this cue.
        
        Returns:
            DmxScene: The current DMX scene.
        """
        return super().__getitem__('DmxScene')

    
    def set_DmxScene(self, dmxscene):
        """Set the DMX scene for this cue.
        
        Args:
            dmxscene (DmxScene or dict): The new DMX scene or a dictionary to create one.
            
        Raises:
            NotImplementedError: If the scene type is not supported.
        """
        if not isinstance(dmxscene, DmxScene):
            dmxscene = DmxScene(dmxscene)
        super().__setitem__('DmxScene', dmxscene)
        
    DmxScene = property(get_DmxScene, set_DmxScene)

    def osc_route(self, osc_route):
        """Set the OSC route for DMX control.
        
        Args:
            osc_route (str): The OSC route to use for DMX control.
        """
        self._osc_route = osc_route

    def offset_route(self, offset_route):
        """Set the offset route for DMX timing.
        
        Args:
            offset_route (str): The new offset route.
        """
        self._offset_route = offset_route

    def player(self, player):
        """Set the DMX player instance.
        
        Args:
            player: The DMX player instance to use.
        """
        self._player = player

    def review_offset(self, timecode):
        """Calculate the offset for DMX timing review.
        
        Args:
            timecode: The timecode to calculate the offset from.
            
        Returns:
            float: The calculated offset in milliseconds.
        """
        return -(float(timecode.milliseconds))
    
    def check_mappings(self, settings):
        """Check if the DMX output mappings are valid.
        
        For DMX cues, the output_name format is "{node_uuid}" (just the node UUID).
        A DMX cue can have multiple outputs (one per target node). This method
        iterates through all outputs and sets _local=True if ANY output_name
        matches the current node UUID. Other outputs are ignored.
        
        Args:
            settings: The settings containing project node mappings.
            
        Returns:
            bool: True if the mappings are valid, False otherwise.
        """
        return super().check_mappings(settings)

        if not settings.project_node_mappings:
            return True
        
        # Initialize _local to False (will be set to True if any output matches)
        self._local = False
        
        # Get current node UUID
        current_node_uuid = settings.node_conf['uuid']
        
        # Check each output
        if self.outputs:
            for output in self.outputs:
                # For DMX cues, output_name is just the node UUID (not {node_uuid}_{output_name})
                output_name = output['output_name']
                
                # Compare entire output_name with current node UUID
                if output_name == current_node_uuid:
                    self._local = True
                    Logger.debug(
                        f'DmxCue {self.id} output_name {output_name} matches current node, setting _local=True'
                    )
                    break  # Found a match, no need to check other outputs
                else:
                    self._local = False
        
        return True
    
    def items(self):
        """Get all items in the cue as a dictionary.
        
        Returns:
            dict_items: A view of the cue's items, with required items included.
        """
        x = dict(super().items())
        for k in REQ_ITEMS.keys():
            x[k] = self[k]
        return x.items()

class DmxScene(CuemsDict):
    """A class representing a DMX scene containing multiple universes."""
    
    def __init__(self, init_dict=None):
        """Initialize a DMX scene.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to create DMX universes.
        """
        if not init_dict:
            init_dict = SCENE_REQ_ITEMS
        else:
            init_dict = ensure_items(init_dict, SCENE_REQ_ITEMS)
        if init_dict:
            self.setter(init_dict)

    def get_id(self):
        """Get the scene ID.
        
        Returns:
            int: The scene ID.
        """
        return super().__getitem__('id')
    
    def set_id(self, scene_id):
        """Set the scene ID.
        
        Args:
            scene_id (int): The new scene ID.
        """
        super().__setitem__('id', scene_id)
    id = property(get_id, set_id)
    def get_DmxUniverse(self):
        """Get a specific DMX universe.
        
        Args:
            num (int, optional): The universe number to get.
                If None, returns None.
                
        Returns:
            DmxUniverse or None: The requested universe or None if not found.
        """
        return super().__getitem__('DmxUniverse')


      
    def set_DmxUniverse(self, universe):
        """Set a DMX universe at a specific number.
        
        Args:
            universe: The universe to set.
            num (int, optional): The universe number. Defaults to 0.
        """
        if not isinstance(universe, DmxUniverse):
            universe = DmxUniverse(universe)
        super().__setitem__('DmxUniverse', universe)
        
    DmxUniverse = property(get_DmxUniverse, set_DmxUniverse)

    # def merge_universe(self, universe, num=0):
    #     """Merge two universes, with priority given to the new universe.
        
    #     Args:
    #         universe: The universe to merge with.
    #         num (int, optional): The universe number to merge into. Defaults to 0.
    #     """
    #     super().__getitem__(num).update(universe)

class DmxUniverse(CuemsDict):
    """A class representing a DMX universe containing multiple channels."""
    
    def __init__(self, init_dict=None):
        """Initialize a DMX universe.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to create DMX channels.
        """
        if not init_dict:
            init_dict = UNIVERSE_REQ_ITEMS
        else:
            init_dict = ensure_items(init_dict, UNIVERSE_REQ_ITEMS)
        if init_dict:
            self.setter(init_dict)

    def get_universe_num(self):
        """Get the universe number.
        
        Returns:
            int: The universe number.
        """
        return super().__getitem__('universe_num')
    
    def set_universe_num(self, universe_num):
        """Set the universe number.
        
        Args:
            universe_num (int): The new universe number.
        """
        super().__setitem__('universe_num', universe_num)
    universe_num = property(get_universe_num, set_universe_num)

    def get_dmx_channels(self):
        """Get the dmx channel for the scene.
        
        Returns:
            list: The list of dmx channels.
        """
        return super().__getitem__('dmx_channels')

    def set_dmx_channels(self, channels):
        """Set the output routing configuration.
        
        Args:
            channels (list): The list of output configurations.
        """
        Logger.info("DmxUniverse set_channels called with channels: {}".format(channels))
        if not isinstance(channels, list):
            channels = [channels]
        channel_list = []
        Logger.debug(f'Channels to process: {channels} Type: {type(channels)}')
        try:
            for r in channels:
                    if r is not None:
                        Logger.debug(f'Processing channel: {r}')
                        if not isinstance(r, DmxChannel):
                            Logger.debug(f"Converting to DmxChannel: {r['DmxChannel']}")
                            new_dmxchannel = DmxChannel(r['DmxChannel'])
                            channel_list.append(new_dmxchannel)
                            super().__setitem__('dmx_channels', channel_list)
                        else:
                            super().__setitem__('dmx_channels', channels)
        except Exception as e:
            Logger.error(f"Error converting channels to DmxChannel: {e}")
            super().__setitem__('dmx_channels', channels)
        

    dmx_channels = property(get_dmx_channels, set_dmx_channels)


    # def setall(self, value):
    #     """Set all channels in the universe to the same value.
        
    #     Args:
    #         value: The value to set all channels to.
            
    #     Returns:
    #         DmxUniverse: Self for method chaining.
    #     """
    #     for channel in range(512):
    #         super().__setitem__(channel, value)
    #     return self

    # def update(self, other=None, **kwargs):
    #     """Update multiple channels in the universe.
        
    #     Args:
    #         other (dict or iterable, optional): Dictionary or iterable of channel updates.
    #         **kwargs: Additional channel updates as keyword arguments.
    #     """
    #     if other is not None:
    #         for k, v in other.items() if isinstance(other, Mapping) else other:
    #             self[k] = DmxChannel(v)
    #     for k, v in kwargs.items():
    #         self[k] = DmxChannel(v)

class DmxChannel(CuemsDict):
    """A class representing a single DMX channel."""
    
    def __init__(self, init_dict = None):
        """Initialize a DMX channel.
        
        Args:
            value (int, optional): The initial channel value.
            init_dict (dict, optional): Dictionary containing initialization values.
        """
        if not init_dict:
            init_dict = DMXCHANNEL_REQ_ITEMS
        else:
            init_dict = ensure_items(init_dict, DMXCHANNEL_REQ_ITEMS)
        if init_dict:
            self.setter(init_dict)



    def get_channel(self):
        """Get the channel number.
        
        Returns:
            int: The channel number.
        """
        return super().__getitem__('channel')
    
    def set_channel(self, channel):
        """Set the channel number.
        
        Args:
            num (int): The new channel number.
        """
        super().__setitem__('channel', channel)
    channel = property(get_channel, set_channel)

    def get_value(self):
        """Get the channel value.
        
        Returns:
            int: The channel value.
        """
        return super().__getitem__('value')
    
    def set_value(self, value):
        """Set the channel value.
        
        Args:
            value (int): The new channel value.
        """
        super().__setitem__('value', value)
    value = property(get_value, set_value)

    def __json__(self):
        """Convert the region to a JSON-compatible dictionary.
        
        Returns:
            dict: A dictionary representation of the region.
        """
        return {type(self).__name__: dict(self.items())}
