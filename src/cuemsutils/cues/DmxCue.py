from collections.abc import Mapping
from .Cue import Cue

class DmxCue(Cue):
    def __init__(self, init_dict = None):
        if init_dict:
            super().__init__(init_dict)

        self._player = None
        self._osc_route = None
        self._offset_route = '/offset'

    @property
    def fadein_time(self):
        return super().__getitem__('fadein_time')

    @fadein_time.setter
    def fadein_time(self, fadein_time):
        super().__setitem__('fadein_time', fadein_time)

    @property
    def fadeout_time(self):
        return super().__getitem__('fadeout_time')

    @fadeout_time.setter
    def fadeout_time(self, fadeout_time):
        super().__setitem__('fadeout_time', fadeout_time)

    @property
    def scene(self):
        return self['dmx_scene']

    @scene.setter
    def scene(self, scene):
        if isinstance(scene, DmxScene):
            super().__setitem__('dmx_scene', scene)
        elif isinstance(scene, dict):
            super().__setitem__('dmx_scene', DmxScene(init_dict=scene))
        else:
            raise NotImplementedError

    def osc_route(self, osc_route):
        self._osc_route = osc_route

    def offset_route(self, offset_route):
        self._offset_route = offset_route

    def player(self, player):
        self._player = player

    def review_offset(self, timecode):
        return -(float(timecode.milliseconds))

class DmxScene(dict):
    def __init__(self, init_dict=None):
        super().__init__()
        if init_dict:
            for k, v, in init_dict.items():
                if isinstance(k, int):
                    super().__setitem__(k, DmxUniverse(v))
                elif k == 'DmxUniverse':
                    for u in v:
                        super().__setitem__(u['id'], DmxUniverse(init_dict=u))

    def universe(self, num=None):
        if num is not None:
            return super().__getitem__(num)

    def universes(self):
        return self
      
    def set_universe(self, universe, num=0):
        super().__setitem__(num, DmxUniverse(universe))

    def merge_universe(self, universe, num=0):
        """merge two universes, priority on the newcoming"""
        super().__getitem__(num).update(universe)

class DmxUniverse(dict):
    def __init__(self, init_dict=None):
        super().__init__()
        if init_dict:
            for k, v, in init_dict.items():
                if isinstance(k, int):
                    super().__setitem__(k, DmxChannel(v))
                elif k == 'DmxChannel':
                    for u in v:
                        super().__setitem__(u['id'], DmxChannel(u['&']))

    def channel(self, channel):
        return super().__getitem__(channel)

    def set_channel(self, channel, value):
        if isinstance(value, DmxChannel):
            super().__setitem__(channel, value)
        else:
            super().__setitem__(channel, DmxChannel(value))
        return self

    def setall(self, value):
        for channel in range(512):
            super().__setitem__(channel, value)
        return self      #TODO: valorate return self to be able to do things like 'universe_full = DmxUniverse().setall(255)'

    def update(self, other=None, **kwargs):
        if other is not None:
            for k, v in other.items() if isinstance(other, Mapping) else other:
                self[k] = DmxChannel(v)
        for k, v in kwargs.items():
            self[k] = DmxChannel(v)

class DmxChannel():
    def __init__(self, value=None, init_dict = None):
        self._value = value
        if init_dict is not None:
            self.value = init_dict

    def __repr__(self):
        return str(self.value)

    @property
    def value(self):
        return self._value
    
    @value.setter
    def value (self, value):
        if value > 255:
            value = 255
        self._value = value
