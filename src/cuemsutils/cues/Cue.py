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
    def __init__(self, init_dict = None):
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
        return super().__getitem__('id')

    def set_id(self, id):
        """Created by UI"""
        id = Uuid(id)
        super().__setitem__('id', id)

    id = property(get_id, set_id)

    def get_name(self):
        return super().__getitem__('name')

    def set_name(self, name):
        super().__setitem__('name', name)

    name = property(get_name, set_name)

    def get_description(self):
        return super().__getitem__('description')

    def set_description(self, description):
        super().__setitem__('description', description)

    description = property(get_description, set_description)

    def get_enabled(self):
        return super().__getitem__('enabled')

    def set_enabled(self, enabled):
        super().__setitem__('enabled', enabled)

    enabled = property(get_enabled, set_enabled)

    def get_autoload(self):
        return super().__getitem__('autoload')

    def set_autoload(self, autoload):
        super().__setitem__('autoload', autoload)

    autoload = property(get_autoload, set_autoload)

    def get_timecode(self):
        return super().__getitem__('timecode')

    def set_timecode(self, timecode):
        super().__setitem__('timecode', timecode)

    timecode = property(get_timecode, set_timecode)

    def get_offset(self):
        return super().__getitem__('offset')

    def set_offset(self, offset):
        offset = format_timecode(offset)
        self.__setitem__('offset', offset)

    offset = property(get_offset, set_offset)

    def get_loop(self):
        return super().__getitem__('loop')

    def set_loop(self, loop):
        super().__setitem__('loop', loop)

    loop = property(get_loop, set_loop)

    def get_prewait(self):
        return super().__getitem__('prewait')

    def set_prewait(self, prewait):
        prewait = format_timecode(prewait)
        super().__setitem__('prewait', prewait)

    prewait = property(get_prewait, set_prewait)

    def get_postwait(self):
        return super().__getitem__('postwait')

    def set_postwait(self, postwait):
        postwait = format_timecode(postwait)
        super().__setitem__('postwait', postwait)

    postwait = property(get_postwait, set_postwait)

    def get_post_go(self):
        return super().__getitem__('post_go')

    def set_post_go(self, post_go):
        super().__setitem__('post_go', post_go)

    post_go = property(get_post_go, set_post_go)

    def get_target(self):
        return super().__getitem__('target')

    def set_target(self, target):
        if target is not None:
            target = Uuid(target)
        super().__setitem__('target', target)

    target = property(get_target, set_target)

    def get_ui_properties(self):
        return super().__getitem__('ui_properties')

    def set_ui_properties(self, ui_properties):
        ui_properties = as_cuemsdict(ui_properties)
        super().__setitem__('ui_properties', ui_properties)

    ui_properties = property(get_ui_properties, set_ui_properties)
    
    def __eq__(self, other):
        "Compare two cues by their id"
        if isinstance(other, Cue):
            return self.id == other.id
        return False

    def __hash__(self):
        """Hash the cue by its id"""
        return hash(self.id)

    def __json__(self):
        return {type(self).__name__: dict(self.items())}

    def setter(self, settings: dict):
        """Set the object properties from a dictionary."""
        if not isinstance(settings, dict):
            raise AttributeError(f"Invalid type {type(settings)}. Expected dict.")
        for k, v in settings.items():
            try:
                x = getattr(self, f"set_{k}")
                x(v)
            except AttributeError:
                pass

    def items(self):
        return extract_items(super().items(), REQ_ITEMS.keys())

    def target_object(self, target_object):
        self._target_object = target_object

    def type(self):
        return type(self)

    def get_next_cue(self):
        if self.target:
            if self.post_go == 'pause':
                return self._target_object
            else:
                return self._target_object.get_next_cue()
        else:
            return None

    def check_mappings(self, settings):
        return True

    def stop(self):
        pass

class UI_properties(CuemsDict):
    def __init__(self, init_dict = None):
        if init_dict:
            super().__init__(init_dict)
    
    def get_timeline_position(self):
        return super().__getitem__('timeline_position')
