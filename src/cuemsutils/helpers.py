"""Set of helper functions for the cuemsutils package."""

from datetime import datetime
from re import match
from uuid import uuid4

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
UUID4_REGEX = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'

def ensure_items(x: dict, requiered: dict) -> dict:
    """Ensure that all the items are present in a dictionary
    
    Args:
        x (dict): The dictionary to check
        requiered (dict): The items (key-value pairs) to check for

    """
    for k,v in requiered.items():
        if k not in x.keys():
            if v == None:
                x[k] = None
            elif callable(v):
                x[k] = v()
            else:
                x[k] = v
    
    return x


def new_datetime():
    """Generate a new datetime string."""
    return datetime.now().strftime(DATETIME_FORMAT)

def new_uuid():
    """Generate a new Uuid class instance."""
    return Uuid()

class Uuid():
    """A class to interact with unique identifiers.
        
        Comparisions should be made based on memory allocation.

        Calling or printing the instance will return the uuid4 string.
    """
    def __init__(self, uuid: str = None):
        if not uuid:
            self.uuid = str(uuid4())
        else:
            self.uuid = str(uuid)
        if not self.check():
            raise ValueError(f'uuid {uuid} is not valid')
    
    def __str__(self):
        return self.uuid

    def __call__(self):
        return self.uuid

    def __eq__(self, other):
        if isinstance(other, Uuid):
            return self == other
        elif isinstance(other, str):
            return self.uuid == other
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, Uuid):
            return self != other
        elif isinstance(other, str):
            return self.uuid != other
        else:
            return True

    def items(self):
        return [("uuid", self.uuid)]
    
    def check(self):
        m = match(UUID4_REGEX, self.uuid)
        if m:
            return m.span() == (0, 36)
        return False
