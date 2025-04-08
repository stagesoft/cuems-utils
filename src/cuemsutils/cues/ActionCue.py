from .Cue import Cue
from ..helpers import ensure_items

REQ_ITEMS = {
    'action_target': None,
    'action_type': 'play'
}

class ActionCue(Cue):
    def __init__(self, init_dict = None):
        if init_dict:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
        else:
            init_dict = REQ_ITEMS
        super().__init__(init_dict)

        self._action_target_object = None

    def get_action_target(self):
        return super().__getitem__('action_target')

    def set_action_target(self, action_target):
        super().__setitem__('action_target', action_target)

    action_target = property(get_action_target, set_action_target)

    def get_action_type(self):
        return super().__getitem__('action_type')

    def set_action_type(self, action_type):
        super().__setitem__('action_type', action_type)

    action_type = property(get_action_type, set_action_type)

    def items(self):
            x = dict(super().items())
            for k in sorted(REQ_ITEMS.keys()):
                x[k] = self[k]
            return x.items()
