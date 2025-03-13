from ..CTimecode import CTimecode
from ..helpers import ensure_items, extract_items, format_timecode, new_uuid, Uuid

REQ_ITEMS = {
    'description': None,
    'enabled': True,
    'id': None,
    'loaded': False,
    'loop': 0,
    'name': 'empty',
    'offset': CTimecode,
    'post_go': 'pause',
    'postwait': None,
    'prewait': None,
    'target': None,
    'timecode': False, # TODO: Should be more specific|explicit
    'uuid': new_uuid,
    # 'ui_properties': new_uuid,
}

class Cue(dict):
    def __init__(self, init_dict = None):
        if init_dict:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
            super().__init__(init_dict)
            
        self._target_object = None
        self._conf = None
        self._armed_list = None
        self._start_mtc = CTimecode()
        self._end_mtc = CTimecode()
        self._end_reached = False
        self._go_thread = None
        self._stop_requested = False
        self._local = False

    def __hash__(self):
        """Hash the cue by its uuid"""
        return hash(self.uuid)
    
    def __eq__(self, other):
        "Compare two cues by their uuid"
        if isinstance(other, Cue):
            return self.uuid == other.uuid
        return False

    @property
    def uuid(self):
        return super().__getitem__('uuid')

    @uuid.setter
    def uuid(self, uuid):
        uuid = Uuid(uuid)
        super().__setitem__('uuid', uuid)

    @property
    def id(self):
        """"""
        return super().__getitem__('id')

    @id.setter
    def id(self, id):
        """Created by UI"""
        super().__setitem__('id', id)

    @property
    def name(self):
        return super().__getitem__('name')

    @name.setter
    def name(self, name):
        super().__setitem__('name', name)

    @property
    def description(self):
        return super().__getitem__('description')

    @description.setter
    def description(self, description):
        super().__setitem__('description', description)

    @property
    def enabled(self):
        return super().__getitem__('enabled')

    @enabled.setter
    def enabled(self, enabled):
        super().__setitem__('enabled', enabled)

    @property
    def loaded(self):
        return super().__getitem__('loaded')

    @loaded.setter
    def loaded(self, loaded):
        super().__setitem__('loaded', loaded)

    @property
    def timecode(self):
        return super().__getitem__('timecode')

    @timecode.setter
    def timecode(self, timecode):
        super().__setitem__('timecode', timecode)

    @property
    def offset(self):
        return super().__getitem__('offset')

    @offset.setter
    def offset(self, offset):
        offset = format_timecode(offset)
        self.__setitem__('offset', offset)

    @property
    def loop(self):
        return super().__getitem__('loop')

    @loop.setter
    def loop(self, loop):
        super().__setitem__('loop', loop)

    @property
    def prewait(self):
        return super().__getitem__('prewait')

    @prewait.setter
    def prewait(self, prewait):
        prewait = format_timecode(prewait)
        super().__setitem__('prewait', prewait)

    @property
    def postwait(self):
        return super().__getitem__('postwait')

    @postwait.setter
    def postwait(self, postwait):
        postwait = format_timecode(postwait)
        super().__setitem__('postwait', postwait)

    @property
    def post_go(self):
        return super().__getitem__('post_go')

    @post_go.setter
    def post_go(self, post_go):
        super().__setitem__('post_go', post_go)

    @property
    def target(self):
        return super().__getitem__('target')

    @target.setter
    def target(self, target):
        if target is not None:
            target = Uuid(target)
        super().__setitem__('target', target)

    @property
    def ui_properties(self):
        return super().__getitem__('ui_properties')

    @ui_properties.setter
    def ui_properties(self, ui_properties):
        super().__setitem__('ui_properties', ui_properties)

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

class UI_properties(dict):
    
    def __init__(self, init_dict = None):
        if init_dict:
            super().__init__(init_dict)
    
    @property
    def timeline_position(self):
        return super().__getitem__('timeline_position')
