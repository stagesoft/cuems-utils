"""Set of helper functions for the cuemsutils package."""

from datetime import datetime

from .CTimecode import CTimecode
from .Uuid import Uuid

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

class CuemsDict(dict):
    """Custom dictionary class to handle cuemsutils specific items."""
    def __json__(self):
        return {type(self).__name__: dict(self.items())}

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
