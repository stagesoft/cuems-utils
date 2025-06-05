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
    """Base class for media-related cues (audio and video).
    
    This class extends Cue to provide common functionality for media playback,
    including media file handling and output routing.
    """
    
    def __init__(self, init_dict = None):
        """Initialize a MediaCue.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If not provided, default values from REQ_ITEMS will be used.
        """
        if not init_dict:
            init_dict = REQ_ITEMS
        else:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
        super().__init__(init_dict)

    def get_Media(self):
        """Get the media object associated with this cue.
        
        Returns:
            Media: The media object containing file and region information.
        """
        return super().__getitem__('Media')

    def set_Media(self, value):
        """Set the media object for this cue.
        
        Args:
            value (Media or dict): The media object or dictionary to create one.
        """
        if not isinstance(value, Media):
            value = Media(value)
        super().__setitem__('Media', value)

    media = property(get_Media, set_Media)

    def get_outputs(self):
        """Get the output routing configuration.
        
        Returns:
            list: The list of output configurations.
        """
        return super().__getitem__('outputs')

    def set_outputs(self, outputs):
        """Set the output routing configuration.
        
        Args:
            outputs (list): The list of output configurations.
        """
        super().__setitem__('outputs', outputs)

    outputs = property(get_outputs, set_outputs)

    def items(self):
        """Get all items in the cue as a dictionary.
        
        Returns:
            dict_items: A view of the cue's items, with required items included.
        """
        x = dict(super().items())
        for k in REQ_ITEMS.keys():
            x[k] = self[k]
        return x.items()

class Media(CuemsDict):
    """A class representing a media file with associated regions."""
    
    def __init__(self, init_dict = None):
        """Initialize a Media object.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to set initial properties.
        """
        if init_dict:
            self.setter(init_dict)
    
    def get_file_name(self):
        """Get the media file name.
        
        Returns:
            str: The name of the media file.
        """
        return super().__getitem__('file_name')

    def set_file_name(self, file_name):
        """Set the media file name.
        
        Args:
            file_name (str): The new media file name.
        """
        super().__setitem__('file_name', file_name)

    file_name = property(get_file_name, set_file_name)

    def get_regions(self):
        """Get the list of regions in the media file.
        
        Returns:
            list: The list of Region objects.
        """
        return super().__getitem__('regions')

    def set_regions(self, regions):
        """Set the list of regions in the media file.
        
        Args:
            regions (list or Region): A list of regions or a single region.
                If not already Region objects, they will be converted.
        """
        if not isinstance(regions, list):
            regions = [regions]
        for r in regions:
            if not isinstance(r, Region):
                r = Region(r)
        super().__setitem__('regions', regions)

    regions = property(get_regions, set_regions)

class Region(CuemsDict):
    """A class representing a region within a media file."""
    
    def __init__(self, init_dict = None):
        """Initialize a Region.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If not provided, default values will be used.
        """
        empty_keys= {"id": "0"}
        if (init_dict):
            self.setter(init_dict)
        else:
            self.setter(empty_keys)
    
    def get_id(self):
        """Get the region ID.
        
        Returns:
            str: The region's identifier.
        """
        return super().__getitem__('id')

    def set_id(self, id):
        """Set the region ID.
        
        Args:
            id: The new region identifier.
        """
        super().__setitem__('id', id)

    id = property(get_id, set_id)

    def get_loop(self):
        """Get the loop count for this region.
        
        Returns:
            int: The number of times the region should loop.
        """
        return super().__getitem__('loop')

    def set_loop(self, loop):
        """Set the loop count for this region.
        
        Args:
            loop (int): The number of times the region should loop.
        """
        super().__setitem__('loop', loop)

    loop = property(get_loop, set_loop)

    def get_in_time(self):
        """Get the in point of the region.
        
        Returns:
            CTimecode: The timecode where the region starts.
        """
        return super().__getitem__('in_time')

    def set_in_time(self, in_time):
        """Set the in point of the region.
        
        Args:
            in_time: The new in point timecode.
        """
        in_time = format_timecode(in_time)
        super().__setitem__('in_time', in_time)

    in_time = property(get_in_time, set_in_time)

    def get_out_time(self):
        """Get the out point of the region.
        
        Returns:
            CTimecode: The timecode where the region ends.
        """
        return super().__getitem__('out_time')

    def set_out_time(self, out_time):
        """Set the out point of the region.
        
        Args:
            out_time: The new out point timecode.
        """
        out_time = format_timecode(out_time)
        super().__setitem__('out_time', out_time)

    out_time = property(get_out_time, set_out_time)
