from .Cue import Cue

from ..helpers import Uuid, ensure_items

REQ_ITEMS = {
    'contents': []
}

class CueList(Cue):
    """A cue that contains a list of other cues.
    
    This class extends Cue to provide functionality for managing collections of cues,
    including nested cue lists and media tracking.
    """
    
    def __init__(self, init_dict = None):
        """Initialize a CueList.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If not provided, default values from REQ_ITEMS will be used.
        """
        if not init_dict:
            init_dict = REQ_ITEMS
        else:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
        super().__init__(init_dict)

    def get_contents(self):
        """Get the list of cues in this cue list.
        
        Returns:
            list: The list of Cue objects.
        """
        return super().__getitem__('contents')

    def set_contents(self, contents):
        """Set the list of cues in this cue list.
        
        Args:
            contents (list): The new list of Cue objects.
        """
        super().__setitem__('contents', contents)

    contents = property(get_contents, set_contents)

    def append(self, item: Cue):
        """Add a cue to the end of the list.
        
        Args:
            item (Cue): The cue to add.
            
        Raises:
            TypeError: If the item is not a Cue object.
        """
        if not isinstance(item, Cue):
            raise TypeError(f'Item {item} is not a Cue object')
        self.contents.append(item)

    def check_mappings(self, settings):
        """Check if the cue list mappings are valid.
        
        Currently, all CueList objects are considered local.
        
        Args:
            settings: The settings containing project node mappings.
            
        Returns:
            bool: Always returns True for CueList objects.
        """
        # DEV: By now let's presume all CueList objects are _local
        self._local = True

        return True

    def find(self, uuid: Uuid):
        """Find a cue by its UUID in this cue list or its nested lists.
        
        Args:
            uuid (Uuid): The UUID to search for.
            
        Returns:
            Cue or None: The found cue, or None if not found.
        """
        if self.uuid == uuid:
            return self
        else:
            for item in self.contents:
                if item.uuid == uuid:
                    return item
                elif isinstance(item, CueList):
                    recursive = item.find(uuid)
                    if recursive != None:
                        return recursive
            
        return None

    def get_media(self):
        """Get a dictionary of all media files referenced in this cue list.
        
        Returns:
            dict: A dictionary mapping cue UUIDs to their media information.
                Each entry contains the media file name and cue type.
        """
        media_dict = dict()
        for item in self.contents:
            if isinstance(item, CueList):
                media_dict.update( item.get_media() )
            else:
                try:
                    if item.media:
                        media_dict[item.uuid] = [item.media.file_name, item.__class__.__name__]
                except KeyError:
                        media_dict[item.uuid] = {'media' : None, 'type' : item.__class__.__name__}
        
        return media_dict

    def get_next_cue(self):
        """Get the next cue to be executed after this cue list.
        
        Returns:
            Cue or None: The next cue to execute, or None if there is no next cue.
        """
        cue_to_return = None
        if self.contents:
            if self.contents[0].post_go == 'pause':
                cue_to_return = self.contents[0]._target_object
            else:
                cue_to_return = self.contents[0].get_next_cue()
            
            if cue_to_return:
                return cue_to_return       

        if self.target:
            if self.post_go == 'pause':
                return self._target_object
            else:
                return self._target_object.get_next_cue()
        else:
            return None

    def items(self):
        """Get all items in the cue list as a dictionary.
        
        Returns:
            dict_items: A view of the cue list's items.
        """
        x = dict(super().items())
        x['contents'] = self.contents
        return x.items()

    def times(self):
        """Get a list of all cue offsets in this cue list.
        
        Returns:
            list: A list of timecode offsets for each cue in the list.
        """
        timelist = list()
        for item in self['contents']:
            timelist.append(item.offset)
        return timelist
