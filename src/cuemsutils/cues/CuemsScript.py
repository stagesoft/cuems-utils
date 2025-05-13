import json
import json_fix

from .CueList import CueList
from ..log import logged, Logger
from ..helpers import as_cuemsdict, ensure_items, new_uuid, new_datetime
from ..Uuid import Uuid

REQ_ITEMS = {
    'id': new_uuid,
    'name': 'empty',
    'description': None,
    'created': new_datetime,
    'modified': new_datetime,
    'CueList': CueList({}),
    'ui_properties': None
}

class CuemsScript(dict):
    """A class representing a complete CueMS script.
    
    This class manages a collection of cues organized in a cue list, along with
    metadata about the script such as creation time and UI properties.
    """
    
    def __init__(self, init_dict = None):
        """Initialize a CuemsScript.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to set initial properties.
        """
        if init_dict:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
            self.setter(init_dict)

    def get_id(self):
        """Get the unique identifier of the script.
        
        Returns:
            Uuid: The script's unique identifier.
        """
        return super().__getitem__('id')

    def set_id(self, id):
        """Set the unique identifier of the script.
        
        Args:
            id: The new unique identifier.
        """
        id = Uuid(id)
        super().__setitem__('id', id)

    id = property(get_id, set_id)

    def get_name(self):
        """Get the name of the script.
        
        Returns:
            str: The script's name.
        """
        return super().__getitem__('name')

    def set_name(self, name):
        """Set the name of the script.
        
        Args:
            name (str): The new name for the script.
        """
        super().__setitem__('name', name)

    name = property(get_name, set_name)

    def get_description(self):
        """Get the description of the script.
        
        Returns:
            str: The script's description.
        """
        return super().__getitem__('description')

    def set_description(self, description):
        """Set the description of the script.
        
        Args:
            description (str): The new description for the script.
        """
        super().__setitem__('description', description)

    description = property(get_description, set_description)

    def get_created(self):
        """Get the creation timestamp of the script.
        
        Returns:
            datetime: When the script was created.
        """
        return super().__getitem__('created')

    def set_created(self, created):
        """Set the creation timestamp of the script.
        
        Args:
            created (datetime): The new creation timestamp.
        """
        super().__setitem__('created', created)

    created = property(get_created, set_created)

    def get_modified(self):
        """Get the last modification timestamp of the script.
        
        Returns:
            datetime: When the script was last modified.
        """
        return super().__getitem__('modified')

    def set_modified(self, modified):
        """Set the last modification timestamp of the script.
        
        Args:
            modified (datetime): The new modification timestamp.
        """
        super().__setitem__('modified', modified)

    modified = property(get_modified, set_modified)

    def get_CueList(self):
        """Get the main cue list of the script.
        
        Returns:
            CueList: The script's main cue list.
        """
        return super().__getitem__('CueList')

    def set_CueList(self, cuelist):
        """Set the main cue list of the script.
        
        Args:
            cuelist (CueList or dict): The new cue list or a dictionary to create one.
            
        Raises:
            ValueError: If the cuelist is not a valid CueList object or dictionary.
        """
        if not isinstance(cuelist, CueList):
            try:
                cuelist = CueList(cuelist)
            except:
                raise ValueError(
                    f'CueList {cuelist} is not a CueList object or a valid dict'
                )
        super().__setitem__('CueList', cuelist)

    cuelist = property(get_CueList, set_CueList)

    def get_ui_properties(self):
        """Get the UI properties of the script.
        
        Returns:
            dict: The script's UI properties.
        """
        return super().__getitem__('ui_properties')

    def set_ui_properties(self, ui_properties):
        """Set the UI properties of the script.
        
        Args:
            ui_properties (dict): The new UI properties.
        """
        Logger.debug(f"Setting ui_properties to {ui_properties}")
        ui_properties = as_cuemsdict(ui_properties)
        super().__setitem__('ui_properties', ui_properties)

    ui_properties = property(get_ui_properties, set_ui_properties)

    def find(self, uuid):
        """Find a cue by its UUID in the script.
        
        Args:
            uuid: The UUID to search for.
            
        Returns:
            Cue or None: The found cue, or None if not found.
        """
        return self.cuelist.find(uuid)

    @logged
    def get_media(self, cuelist = None):
        """Get all media files referenced in a CueList.
        
        Args:
            cuelist (CueList, optional): The cue list to search in.
                If not provided, uses the script's main cue list.
                
        Returns:
            dict: A dictionary mapping media file names to their associated cues.
        """
        media_dict = dict()

        # If no cuelist is specified we are looking inside our own
        # script object, so our cuelist is our self cuelist
        if not cuelist:
            cuelist = self.cuelist

        if cuelist.contents:
            for cue in cuelist.contents:
                if type(cue) == CueList:
                    # If the cue is a cuelist, let's recurse
                    media_dict.update(self.get_media(cuelist=cue))
                else:
                    try:
                        if cue.media:
                            media_dict[cue.media.file_name] = cue
                    except KeyError:
                        pass
                        # logger.debug("cue with no media")
        return media_dict

    @logged
    def get_own_media(self, cuelist = None, config = None):
        """Get media files that are local to the current node.
        
        Args:
            cuelist (CueList, optional): The cue list to search in.
                If not provided, uses the script's main cue list.
            config: The configuration containing node information.
                
        Returns:
            dict: A dictionary mapping media file names to their associated cues
                that are local to the current node.
        """
        media_dict = dict()

        # If no cuelist is specified we are looking inside our own
        # script object, so our cuelist is our self cuelist
        if not cuelist:
            cuelist = self.cuelist

        if cuelist.contents:
            for cue in cuelist.contents:
                if type(cue)==CueList:
                    # If the cue is a cuelist, let's recurse
                    media_dict.update(self.get_own_media(cuelist=cue, config=config))
                else:
                    try:
                        if cue.media:
                            cue.check_mappings(config)
                            if cue._local:
                                media_dict[cue.media.file_name] = cue
                    except KeyError:
                        pass
                        # logger.debug("cue with no media")
        return media_dict

    def to_json(self):
        """Convert the script to a JSON string.
        
        Returns:
            str: A JSON string representation of the script.
        """
        return json.dumps({'CuemsScript': self})

    def setter(self, settings: dict):
        """Set the object properties from a dictionary.
        
        Args:
            settings (dict): Dictionary containing property values to set.
            
        Raises:
            AttributeError: If settings is not a dictionary.
        """
        if not isinstance(settings, dict):
            raise AttributeError(f"Invalid type {type(settings)}. Expected dict.")
        for k, v in settings.items():
            try:
                x = getattr(self, f"set_{k}")
                x(v)
            except AttributeError:
                pass

    def __json__(self):
        """Convert the script to a JSON-compatible dictionary.
        
        Returns:
            dict: A dictionary representation of the script.
        """
        x = dict(super().items())
        for k, v in x.items():
            if hasattr(v, '__json__'):
                x[k] = v.__json__()
            else:
                x[k] = v
            if k.lower() != k:
                x[k] = x[k][k]
        return x

    def items(self):
        """Get all items in the script as a dictionary.
        
        Returns:
            dict_items: A view of the script's items.
        """
        x = dict(super().items())
        return x.items()
