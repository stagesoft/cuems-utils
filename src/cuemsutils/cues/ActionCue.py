from .Cue import Cue
from ..helpers import ensure_items

REQ_ITEMS = {
    'action_type': 'play',
    'action_target': None
}

class ActionCue(Cue):
    def __init__(self, init_dict = None):
        if init_dict:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
            super().__init__(init_dict)

        self._action_target_object = None

    @property
    def action_type(self):
        return super().__getitem__('action_type')

    @action_type.setter
    def action_type(self, action_type):
        super().__setitem__('action_type', action_type)

    @property
    def action_target(self):
        return super().__getitem__('action_target')

    @action_target.setter
    def action_target(self, action_target):
        super().__setitem__('action_target', action_target)

    def items(self):
            x = dict(super().items())
            for k in REQ_ITEMS.keys():
                x[k] = self[k]
            return x.items()
