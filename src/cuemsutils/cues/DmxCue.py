from collections.abc import Mapping
from .Cue import Cue

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
        if init_dict:
            super().__init__(init_dict)

        self._player = None
        self._osc_route = None
        self._offset_route = '/offset'

    @property
    def fadein_time(self):
        """Get the fade-in time for the DMX cue.
        
        Returns:
            The fade-in time value.
        """
        return super().__getitem__('fadein_time')

    @fadein_time.setter
    def fadein_time(self, fadein_time):
        """Set the fade-in time for the DMX cue.
        
        Args:
            fadein_time: The new fade-in time value.
        """
        super().__setitem__('fadein_time', fadein_time)

    @property
    def fadeout_time(self):
        """Get the fade-out time for the DMX cue.
        
        Returns:
            The fade-out time value.
        """
        return super().__getitem__('fadeout_time')

    @fadeout_time.setter
    def fadeout_time(self, fadeout_time):
        """Set the fade-out time for the DMX cue.
        
        Args:
            fadeout_time: The new fade-out time value.
        """
        super().__setitem__('fadeout_time', fadeout_time)

    @property
    def scene(self):
        """Get the DMX scene for this cue.
        
        Returns:
            DmxScene: The current DMX scene.
        """
        return self['dmx_scene']

    @scene.setter
    def scene(self, scene):
        """Set the DMX scene for this cue.
        
        Args:
            scene (DmxScene or dict): The new DMX scene or a dictionary to create one.
            
        Raises:
            NotImplementedError: If the scene type is not supported.
        """
        if isinstance(scene, DmxScene):
            super().__setitem__('dmx_scene', scene)
        elif isinstance(scene, dict):
            super().__setitem__('dmx_scene', DmxScene(init_dict=scene))
        else:
            raise NotImplementedError

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

class DmxScene(dict):
    """A class representing a DMX scene containing multiple universes."""
    
    def __init__(self, init_dict=None):
        """Initialize a DMX scene.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to create DMX universes.
        """
        super().__init__()
        if init_dict:
            for k, v, in init_dict.items():
                if isinstance(k, int):
                    super().__setitem__(k, DmxUniverse(v))
                elif k == 'DmxUniverse':
                    for u in v:
                        super().__setitem__(u['id'], DmxUniverse(init_dict=u))

    def universe(self, num=None):
        """Get a specific DMX universe.
        
        Args:
            num (int, optional): The universe number to get.
                If None, returns None.
                
        Returns:
            DmxUniverse or None: The requested universe or None if not found.
        """
        if num is not None:
            return super().__getitem__(num)

    def universes(self):
        """Get all DMX universes in the scene.
        
        Returns:
            dict: All universes in the scene.
        """
        return self
      
    def set_universe(self, universe, num=0):
        """Set a DMX universe at a specific number.
        
        Args:
            universe: The universe to set.
            num (int, optional): The universe number. Defaults to 0.
        """
        super().__setitem__(num, DmxUniverse(universe))

    def merge_universe(self, universe, num=0):
        """Merge two universes, with priority given to the new universe.
        
        Args:
            universe: The universe to merge with.
            num (int, optional): The universe number to merge into. Defaults to 0.
        """
        super().__getitem__(num).update(universe)

class DmxUniverse(dict):
    """A class representing a DMX universe containing multiple channels."""
    
    def __init__(self, init_dict=None):
        """Initialize a DMX universe.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to create DMX channels.
        """
        super().__init__()
        if init_dict:
            for k, v, in init_dict.items():
                if isinstance(k, int):
                    super().__setitem__(k, DmxChannel(v))
                elif k == 'DmxChannel':
                    for u in v:
                        super().__setitem__(u['id'], DmxChannel(u['&']))

    def channel(self, channel):
        """Get a specific DMX channel.
        
        Args:
            channel (int): The channel number to get.
            
        Returns:
            DmxChannel: The requested channel.
        """
        return super().__getitem__(channel)

    def set_channel(self, channel, value):
        """Set a DMX channel value.
        
        Args:
            channel (int): The channel number to set.
            value: The value to set the channel to.
            
        Returns:
            DmxUniverse: Self for method chaining.
        """
        if isinstance(value, DmxChannel):
            super().__setitem__(channel, value)
        else:
            super().__setitem__(channel, DmxChannel(value))
        return self

    def setall(self, value):
        """Set all channels in the universe to the same value.
        
        Args:
            value: The value to set all channels to.
            
        Returns:
            DmxUniverse: Self for method chaining.
        """
        for channel in range(512):
            super().__setitem__(channel, value)
        return self

    def update(self, other=None, **kwargs):
        """Update multiple channels in the universe.
        
        Args:
            other (dict or iterable, optional): Dictionary or iterable of channel updates.
            **kwargs: Additional channel updates as keyword arguments.
        """
        if other is not None:
            for k, v in other.items() if isinstance(other, Mapping) else other:
                self[k] = DmxChannel(v)
        for k, v in kwargs.items():
            self[k] = DmxChannel(v)

class DmxChannel():
    """A class representing a single DMX channel."""
    
    def __init__(self, value=None, init_dict = None):
        """Initialize a DMX channel.
        
        Args:
            value (int, optional): The initial channel value.
            init_dict (dict, optional): Dictionary containing initialization values.
        """
        self._value = value
        if init_dict is not None:
            self.value = init_dict

    def __repr__(self):
        """Get a string representation of the channel value.
        
        Returns:
            str: The string representation of the channel value.
        """
        return str(self.value)

    @property
    def value(self):
        """Get the channel value.
        
        Returns:
            int: The current channel value.
        """
        return self._value
    
    @value.setter
    def value(self, value):
        """Set the channel value.
        
        Args:
            value (int): The new channel value. Will be capped at 255.
        """
        if value > 255:
            value = 255
        self._value = value
