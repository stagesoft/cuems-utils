from ..CTimecode import CTimecode
from ..helpers import CuemsDict, ensure_items, extract_items, format_timecode, new_uuid, as_cuemsdict
from ..Uuid import Uuid

REQ_ITEMS = {
    'autoload': False,
    'description': None,
    'enabled': True,
    'id': new_uuid,
    'loop': 0,
    'name': 'empty',
    'offset': CTimecode,
    'post_go': 'pause',
    'postwait': None,
    'prewait': None,
    'target': None,
    'timecode': False, # TODO: Should be more specific|explicit
    'ui_properties': None,
}

class Cue(CuemsDict):
    """Base class for all cue types in the system.
    
    A cue represents a single action or event that can be triggered in the system.
    It contains properties like timing, target, and behavior settings.
    """
    
    def __init__(self, init_dict = None):
        """Initialize a new Cue.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to set initial properties.
        """
        if init_dict:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
            self.setter(init_dict)

        self._target_object = None
        self._conf = None
        self._armed_list = None
        self._start_mtc = CTimecode()
        self._end_mtc = CTimecode()
        self._end_reached = False
        self._go_thread = None
        self._stop_requested = False
        self._local = False

    def get_id(self):
        """Get the unique identifier of the cue.
        
        Returns:
            Uuid: The cue's unique identifier.
        """
        return super().__getitem__('id')

    def set_id(self, id):
        """Set the unique identifier of the cue.
        
        Args:
            id: The new unique identifier.
        """
        id = Uuid(id)
        super().__setitem__('id', id)

    id = property(get_id, set_id)

    def get_name(self):
        """Get the name of the cue.
        
        Returns:
            str: The cue's name.
        """
        return super().__getitem__('name')

    def set_name(self, name):
        """Set the name of the cue.
        
        Args:
            name (str): The new name for the cue.
        """
        super().__setitem__('name', name)

    name = property(get_name, set_name)

    def get_description(self):
        """Get the description of the cue.
        
        Returns:
            str: The cue's description.
        """
        return super().__getitem__('description')

    def set_description(self, description):
        """Set the description of the cue.
        
        Args:
            description (str): The new description for the cue.
        """
        super().__setitem__('description', description)

    description = property(get_description, set_description)

    def get_enabled(self):
        """Get whether the cue is enabled.
        
        Returns:
            bool: True if the cue is enabled, False otherwise.
        """
        return super().__getitem__('enabled')

    def set_enabled(self, enabled):
        """Set whether the cue is enabled.
        
        Args:
            enabled (bool): True to enable the cue, False to disable it.
        """
        super().__setitem__('enabled', enabled)

    enabled = property(get_enabled, set_enabled)

    def get_autoload(self):
        """Get whether the cue should be autoloaded.
        
        Returns:
            bool: True if the cue should be autoloaded, False otherwise.
        """
        return super().__getitem__('autoload')

    def set_autoload(self, autoload: bool):
        """Set whether the cue should be autoloaded.
        
        Args:
            autoload (bool): True to enable autoloading, False to disable it.
        """
        super().__setitem__('autoload', autoload)

    autoload = property(get_autoload, set_autoload)

    def get_timecode(self):
        """Get the timecode setting of the cue.
        
        Returns:
            bool: The timecode setting.
        """
        return super().__getitem__('timecode')

    def set_timecode(self, timecode):
        """Set the timecode setting of the cue.
        
        Args:
            timecode (bool): The new timecode setting.
        """
        super().__setitem__('timecode', timecode)

    timecode = property(get_timecode, set_timecode)

    def get_offset(self):
        """Get the timecode offset of the cue.
        
        Returns:
            CTimecode: The cue's timecode offset.
        """
        return super().__getitem__('offset')

    def set_offset(self, offset):
        """Set the timecode offset of the cue.
        
        Args:
            offset: The new timecode offset.
        """
        offset = format_timecode(offset)
        self.__setitem__('offset', offset)

    offset = property(get_offset, set_offset)

    def get_loop(self):
        """Get the loop count of the cue.
        
        Returns:
            int: The number of times the cue should loop.
        """
        return super().__getitem__('loop')

    def set_loop(self, loop):
        """Set the loop count of the cue.
        
        Args:
            loop (int): The number of times the cue should loop.
        """
        super().__setitem__('loop', loop)

    loop = property(get_loop, set_loop)

    def get_prewait(self):
        """Get the pre-wait time of the cue.
        
        Returns:
            CTimecode: The time to wait before executing the cue.
        """
        return super().__getitem__('prewait')

    def set_prewait(self, prewait):
        """Set the pre-wait time of the cue.
        
        Args:
            prewait: The new pre-wait time.
        """
        prewait = format_timecode(prewait)
        super().__setitem__('prewait', prewait)

    prewait = property(get_prewait, set_prewait)

    def get_postwait(self):
        """Get the post-wait time of the cue.
        
        Returns:
            CTimecode: The time to wait after executing the cue.
        """
        return super().__getitem__('postwait')

    def set_postwait(self, postwait):
        """Set the post-wait time of the cue.
        
        Args:
            postwait: The new post-wait time.
        """
        postwait = format_timecode(postwait)
        super().__setitem__('postwait', postwait)

    postwait = property(get_postwait, set_postwait)

    def get_post_go(self):
        """Get the post-go behavior of the cue.
        
        Returns:
            str: The post-go behavior (e.g., 'pause').
        """
        return super().__getitem__('post_go')

    def set_post_go(self, post_go):
        """Set the post-go behavior of the cue.
        
        Args:
            post_go (str): The new post-go behavior.
        """
        super().__setitem__('post_go', post_go)

    post_go = property(get_post_go, set_post_go)

    def get_target(self):
        """Get the target of the cue.
        
        Returns:
            Uuid: The target's unique identifier.
        """
        return super().__getitem__('target')

    def set_target(self, target):
        """Set the target of the cue.
        
        Args:
            target: The new target identifier.
        """
        if target is not None:
            target = Uuid(target)
        super().__setitem__('target', target)

    target = property(get_target, set_target)

    def get_ui_properties(self):
        """Get the UI properties of the cue.
        
        Returns:
            dict: The cue's UI properties.
        """
        return super().__getitem__('ui_properties')

    def set_ui_properties(self, ui_properties):
        """Set the UI properties of the cue.
        
        Args:
            ui_properties (dict): The new UI properties.
        """
        ui_properties = as_cuemsdict(ui_properties)
        super().__setitem__('ui_properties', ui_properties)

    ui_properties = property(get_ui_properties, set_ui_properties)
    
    def __eq__(self, other):
        """Compare two cues by their id.
        
        Args:
            other: The other cue to compare with.
            
        Returns:
            bool: True if the cues have the same id, False otherwise.
        """
        if isinstance(other, Cue):
            return self.id == other.id
        return False

    def __hash__(self):
        """Hash the cue by its id.
        
        Returns:
            int: The hash value of the cue's id.
        """
        return hash(self.id)

    def __json__(self):
        """Convert the cue to a JSON-compatible dictionary.
        
        Returns:
            dict: A dictionary representation of the cue.
        """
        return {type(self).__name__: dict(self.items())}

    def items(self):
        """Get all items in the cue as a dictionary.
        
        Returns:
            dict_items: A view of the cue's items.
        """
        return extract_items(super().items(), REQ_ITEMS.keys())

    def target_object(self, target_object):
        """Set the target object for the cue.
        
        Args:
            target_object: The target object to set.
        """
        self._target_object = target_object

    def type(self):
        """Get the type of the cue.
        
        Returns:
            type: The class type of the cue.
        """
        return type(self)

    def get_next_cue(self):
        """Get the next cue in the sequence.
        
        Returns:
            Cue or None: The next cue to execute, or None if there is no next cue.
        """
        if self.target:
            if self.post_go == 'pause':
                return self._target_object
            else:
                return self._target_object.get_next_cue()
        else:
            return None

    def check_mappings(self, settings):
        """Check if the given settings are valid for this cue.
        
        Args:
            settings: The settings to check.
            
        Returns:
            bool: True if the settings are valid, False otherwise.
        """
        return True

    def stop(self):
        """Stop the execution of the cue."""
        pass

class UI_properties(CuemsDict):
    """Class for managing UI-specific properties of cues."""
    
    def __init__(self, init_dict = None):
        """Initialize UI properties.
        
        Args:
            init_dict (dict, optional): Dictionary containing initial UI properties.
        """
        if init_dict:
            super().__init__(init_dict)
    
    def get_timeline_position(self):
        """Get the timeline position of the cue.
        
        Returns:
            The timeline position value.
        """
        return super().__getitem__('timeline_position')
