from .Cue import Cue
from ..helpers import ensure_items

REQ_ITEMS = {
    'action_target': None,
    'action_type': 'play'
}

class ActionCue(Cue):
    """A cue that represents an action to be performed on a target object.
    
    This cue is used to trigger actions on other objects in the system, such as
    playing, pausing, or stopping media cues.
    """
    
    def __init__(self, init_dict: dict = None):
        """Initialize an ActionCue.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If not provided, default values from REQ_ITEMS will be used.
        """
        if init_dict:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
        else:
            init_dict = REQ_ITEMS
        super().__init__(init_dict)

        self._action_target_object = None

    def get_action_target(self):
        """Get the target object for the action.
        
        Returns:
            The target object identifier.
        """
        return super().__getitem__('action_target')

    def set_action_target(self, action_target: str) -> None:
        """Set the target object for the action.
        
        Args:
            action_target: The target object identifier.
        """
        super().__setitem__('action_target', action_target)

    action_target = property(get_action_target, set_action_target)

    def get_action_type(self) -> str:
        """Get the type of action to perform.
        
        Returns:
            str: The action type (e.g., 'play', 'pause', 'stop').
        """
        return super().__getitem__('action_type')

    def set_action_type(self, action_type: str) -> None:
        """Set the type of action to perform.
        
        Args:
            action_type (str): The action type (e.g., 'play', 'pause', 'stop').
        """
        super().__setitem__('action_type', action_type)

    action_type = property(get_action_type, set_action_type)

    def items(self):
        """Get all items in the cue as a dictionary.
        
        Returns:
            dict_items: A view of the cue's items, with required items sorted first.
        """
        x = dict(super().items())
        for k in sorted(REQ_ITEMS.keys()):
            x[k] = self[k]
        return x.items()
