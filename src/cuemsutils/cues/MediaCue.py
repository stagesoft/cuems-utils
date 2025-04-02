from .Cue import Cue
from ..helpers import CuemsDict, ensure_items, format_timecode

REQ_ITEMS = {
    'Media': None,
    'outputs': None
}

REGION_REQ_ITEMS = {
    'id': 0,
    'loop': 0,
    'in_time': None,
    'out_time': None
}

class MediaCue(Cue):
    def __init__(self, init_dict = None):
        if not init_dict:
            init_dict = REQ_ITEMS
        else:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
        super().__init__(init_dict)

    def get_Media(self):
        return super().__getitem__('Media')

    def set_Media(self, value):
        if not isinstance(value, Media):
            value = Media(value)
        super().__setitem__('Media', value)

    media = property(get_Media, set_Media)

    def get_outputs(self):
        return super().__getitem__('outputs')

    def set_outputs(self, outputs):
        super().__setitem__('outputs', outputs)

    outputs = property(get_outputs, set_outputs)

    def items(self):
        x = dict(super().items())
        for k in REQ_ITEMS.keys():
            x[k] = self[k]
        return x.items()

class Media(CuemsDict):
    def __init__(self, init_dict = None):
        if init_dict:
            super().__init__(init_dict)
    
    @property
    def file_name(self):
        return super().__getitem__('file_name')

    @file_name.setter
    def file_name(self, file_name):
        super().__setitem__('file_name', file_name)

    @property
    def regions(self):
        return super().__getitem__('regions')

    @regions.setter
    def regions(self, regions):
        if not isinstance(regions, list):
            regions = [regions]
        for r in regions:
            if not isinstance(r, Region):
                r = Region(r)
        super().__setitem__('regions', regions)

class Region(CuemsDict):
    def __init__(self, init_dict = None):
        empty_keys= {"id": "0"}
        if (init_dict):
            super().__init__(init_dict)
        else:
            super().__init__(empty_keys)
    
    @property
    def id(self):
        return super().__getitem__('id')

    @id.setter
    def id(self, id):
        super().__setitem__('id', id)

    @property
    def loop(self):
        return super().__getitem__('loop')

    @loop.setter
    def loop(self, loop):
        super().__setitem__('loop', loop)

    @property
    def in_time(self):
        return super().__getitem__('in_time')

    @in_time.setter
    def in_time(self, in_time):
        in_time = format_timecode(in_time)
        super().__setitem__('in_time', in_time)

    @property
    def out_time(self):
        return super().__getitem__('out_time')

    @out_time.setter
    def out_time(self, out_time):
        out_time = format_timecode(out_time)
        super().__setitem__('out_time', out_time)
