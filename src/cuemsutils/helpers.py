"""Set of helper functions for the cuemsutils package."""

import os
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement

from .CTimecode import CTimecode
from .Uuid import Uuid

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

class CuemsDict(dict):
    """Custom dictionary class to handle cuemsutils specific items."""

    def build(self, parent: Element):
        build_xml_dict(self, parent)
    
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

def as_cuemsdict(x: dict) -> None | CuemsDict:
    if not x:
        return None
    out = CuemsDict({})
    for k,v in x.items():
        if isinstance(v, dict):
            out.update({k: as_cuemsdict(v)})
        else:
            out.update({k: v})
    return out

def build_xml_dict(x, parent: Element) -> None:
    """Build an xml element from a dictionary"""
    if not isinstance(x, dict):
        raise AttributeError(f"Invalid type {type(x)}. Expected dict.")
    if not isinstance(parent, Element):
        raise AttributeError(f"Invalid type {type(parent)}. Expected ElementTree.")
    for k, v in x.items():
        if isinstance(v, list):
            for item in v:
                if hasattr(item, 'build'):
                    item.build(parent)
                else:
                    SubElement(parent, k).text = str(item)
        elif hasattr(v, 'build'):
            s = SubElement(parent, k)
            v.build(s)
        else:
            SubElement(parent, k).text = str(v)

def check_path(path: str, dir_only: bool = False) -> bool:
    """Check if a path is valid. Raise an error if not."""
    path = os.path.realpath(path)
    if dir_only:
        dir_ok = _check_dir(os.path.dirname(path))
        return dir_ok
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path {path} does not exist")
    if not _readable(path) or not _writable(path):
        raise PermissionError(f"Path {path} is not readable or writable")
    return True

def _check_dir(path: str) -> bool:
    """Check if a path is a directory. Raise an error if not."""
    if not os.path.isdir(path):
        raise NotADirectoryError(f"Directory {path} does not exist")
    if not _readable(path):
        raise PermissionError(f"Directory {path} is not readable")
    if not _writable(path):
        raise PermissionError(f"Directory {path} is not writable")
    return True

def _readable(path: str) -> bool:
    """Check if a path is readable."""
    return os.access(path, os.R_OK)

def _writable(path: str) -> bool:
    """Check if a path is writable."""
    return os.access(path, os.W_OK) 

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
            return CTimecode()
        elif isinstance(value, CTimecode):
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
