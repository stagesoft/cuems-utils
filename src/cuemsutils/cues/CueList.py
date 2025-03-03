from .Cue import Cue

class CueList(Cue):
    def __init__(self, init_dict = None):
        self['contents'] = []
        super().__init__(init_dict)

    @property    
    def contents(self):
        return super().__getitem__('contents')

    @contents.setter
    def contents(self, contents):
        super().__setitem__('contents', contents)

    @property
    def uuid(self):
        return super().__getitem__('uuid')

    def append(self, item: Cue):
        if not isinstance(item, Cue):
            raise TypeError(f'Item {item} is not a Cue object')
        self.contents.append(item)

    def times(self):
        timelist = list()
        for item in self['contents']:
            timelist.append(item.offset)
        return timelist

    def find(self, uuid):
        if self.uuid == uuid:
            return self
        else:
            for item in self.contents:
                if item.uuid == uuid:
                    return item
                elif isinstance(item, CueList):
                    recursive = item.find(uuid)
                    if recursive != None:
                        return recursive
            
        return None

    def get_media(self):
        media_dict = dict()
        for item in self.contents:
            if isinstance(item, CueList):
                media_dict.update( item.get_media() )
            else:
                try:
                    if item.media:
                        media_dict[item.uuid] = [item.media.file_name, item.__class__.__name__]
                except KeyError:
                        media_dict[item.uuid] = {'media' : None, 'type' : item.__class__.__name__}
        
        return media_dict

    def get_next_cue(self):
        cue_to_return = None
        if self.contents:
            if self.contents[0].post_go == 'pause':
                cue_to_return = self.contents[0]._target_object
            else:
                cue_to_return = self.contents[0].get_next_cue()
            
            if cue_to_return:
                return cue_to_return       

        if self.target:
            if self.post_go == 'pause':
                return self._target_object
            else:
                return self._target_object.get_next_cue()
        else:
            return None

    def check_mappings(self, settings):
        # DEV: By now let's presume all CueList objects are _local
        self._local = True

        return True
