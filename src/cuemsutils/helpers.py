"""Set of helper functions for the cuemsutils package."""

from datetime import datetime
from re import match
from uuid import uuid4

from .CTimecode import CTimecode

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

    ## Order the dictionary
    x = {k: x[k] for k in sorted(x.keys())}
    
    return x

def extract_items(x, keys: list) -> dict:
    """Extract list of keys and values from a dictionary
    
    Args:
        x (items): The dictionary items to extract from
        keys (list): The keys to extract
    """
    d = dict(x)
    return {k: d[k] for k in keys}.items()

def format_timecode(value):
        if not value or value == '':
            raise ValueError(f'Invalid timecode value {value}')
        if isinstance(value, CTimecode):
            return value
        elif isinstance(value, (int, float)):
            ctime_value = CTimecode(start_seconds = value)
            ctime_value.frames = ctime_value.frames + 1
            return ctime_value
        elif isinstance(value, str):
            return CTimecode(value)
        elif isinstance(value, dict):
            dict_timecode = value.pop('CTimecode', None)
            if dict_timecode is None:
                return CTimecode()
            elif isinstance(dict_timecode, int):
                return CTimecode(start_seconds = dict_timecode)
            else:
                return CTimecode(dict_timecode)
        else:
            raise ValueError(f'Invalid timecode value type {type(value)}')

def new_datetime():
    """Generate a new datetime string."""
    return datetime.now().strftime(DATETIME_FORMAT)

def new_uuid():
    """Generate a new Uuid class instance."""
    return Uuid()

def strtobool(val: str) -> bool:
    """Convert a string value representation of truth to true (1) or false (0).

        True values are y, yes, t, true, on and 1.
        False values are n, no, f, false, off and 0.
        Raises ValueError if val is anything else.
    """
    if val.lower() in ['y', 'yes', 't', 'true', 'on', '1']:
        return True
    elif val.lower() in ['n', 'no', 'f', 'false', 'off', '0']:
        return False
    else:
        raise ValueError(f'Invalid truth value {val}')

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
    
    def __repr__(self):
        return self.uuid

    def __call__(self):
        return self.uuid

    def __eq__(self, other):
        if isinstance(other, Uuid):
            return self.uuid == other.uuid
        elif isinstance(other, str):
            return self.uuid == other
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def items(self):
        return [("uuid", self.uuid)]
    
    def check(self):
        m = match(UUID4_REGEX, self.uuid)
        if m:
            return m.span() == (0, 36)
        return False
