import json
import json_fix

from .CueList import CueList
from ..log import logged
from ..helpers import ensure_items, new_uuid, new_datetime
from ..Uuid import Uuid

REQ_ITEMS = {
    'id': new_uuid,
    'name': 'empty',
    'description': None,
    'created': new_datetime,
    'modified': new_datetime,
    'CueList': CueList({})
}

class CuemsScript(dict):
    def __init__(self, init_dict = None):
        if init_dict:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
            self.setter(init_dict)

    def get_id(self):
        return super().__getitem__('id')

    def set_id(self, id):
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

    def get_created(self):
        return super().__getitem__('created')

    def set_created(self, created):
        super().__setitem__('created', created)

    created = property(get_created, set_created)

    def get_modified(self):
        return super().__getitem__('modified')

    def set_modified(self, modified):
        super().__setitem__('modified', modified)

    modified = property(get_modified, set_modified)

    def get_CueList(self):
        return super().__getitem__('CueList')

    def set_CueList(self, cuelist):
        '''Set the contents of the script.'''
        if not isinstance(cuelist, CueList):
            try:
                cuelist = CueList(cuelist)
            except:
                raise ValueError(
                    f'CueList {cuelist} is not a CueList object or a valid dict'
                )
        super().__setitem__('CueList', cuelist)

    cuelist = property(get_CueList, set_CueList)

    def find(self, uuid):
        return self.cuelist.find(uuid)

    @logged
    def get_media(self, cuelist = None):
        '''Gets all the media files list present on a cuelist.'''
        media_dict = dict()

        # If no cuelist is specified we are looking inside our own
        # script object, so our cuelist is our self cuelist
        if not cuelist:
            cuelist = self.cuelist

        if cuelist.contents:
            for cue in cuelist.contents:
                if type(cue) == CueList:
                    # If the cue is a cuelist, let's recurse
                    media_dict.update(self.get_media(cuelist=cue))
                else:
                    try:
                        if cue.media:
                            media_dict[cue.media.file_name] = cue
                    except KeyError:
                        pass
                        # logger.debug("cue with no media")
        return media_dict

    @logged
    def get_own_media(self, cuelist = None, config = None):
        '''Gets the media files list present on the script which are 
        related to the specified node uuid, usually our local identifier,
        as we are looking for our own needed media files'''

        media_dict = dict()

        # If no cuelist is specified we are looking inside our own
        # script object, so our cuelist is our self cuelist
        if not cuelist:
            cuelist = self.cuelist

        if cuelist.contents:
            for cue in cuelist.contents:
                if type(cue)==CueList:
                    # If the cue is a cuelist, let's recurse
                    media_dict.update(self.get_own_media(cuelist=cue, config=config))
                else:
                    try:
                        if cue.media:
                            cue.check_mappings(config)
                            if cue._local:
                                media_dict[cue.media.file_name] = cue
                    except KeyError:
                        pass
                        # logger.debug("cue with no media")
        return media_dict

    def to_json(self):
        return json.dumps({'CuemsScript': self})

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
        x = dict(super().items())
        # x['contents'] = self.contents
        return x.items()
