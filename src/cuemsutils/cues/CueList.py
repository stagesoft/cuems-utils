from time import sleep
from threading import Thread

from .Cue import Cue
from ..log import logged, Logger

class CueList(Cue):
    def __init__(self, init_dict = None):
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
    
    def __add__(self, other):
        new_contents = self['contents'].copy()
        new_contents.append(other)
        return new_contents

    def __iadd__(self, other):
        self['contents'].__iadd__(other)
        return self

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

    def arm(self, conf, ossia_server, armed_list, init = False):
        self.conf = conf
        self.armed_list = armed_list

        if self.enabled and self.loaded == init:
            if not self in armed_list:
                self.contents[0].arm(self.conf, ossia_server, self.armed_list, init)

                self.loaded = True

                armed_list.append(self)

            if self.post_go == 'go':
                self._target_object.arm(self.conf, ossia_server, self.armed_list, init)

            return True
        else:
            return False

    @logged
    def go(self, ossia, mtc):
        if not self.loaded:
            raise Exception(f'{self.__class__.__name__} {self.uuid} not loaded to go')
        else:
            # THREADED GO
            thread = Thread(name = f'GO:{self.__class__.__name__}:{self.uuid}', target = self.go_thread, args = [ossia, mtc])
            thread.start()

    @logged
    def go_thread(self, ossia, mtc):
        # ARM NEXT TARGET
        if self._target_object:
            self._target_object.arm(self.conf, ossia, self.armed_list)

        # PREWAIT
        if self.prewait > 0:
            sleep(self.prewait.milliseconds / 1000)

        # PLAY : specific go the first cue in the list
        try:
            if self.contents:
                self.contents[0].go(ossia, mtc)
        except Exception as e:
            Logger.log_error(
                f'GO failed for content {self.contents[0].uuid}: {e}',
                extra = {"caller": self.__class__.__name__}
            )

        # POSTWAIT
        if self.postwait > 0:
            sleep(self.postwait.milliseconds / 1000)

        if self.post_go == 'go':
            self._target_object.go(ossia, mtc)

        '''
        if self.post_go == 'go_at_end':
            self._target_object.go(ossia, mtc)
        '''

        if self in self.armed_list:
            self.disarm(ossia)

    def disarm(self):
        try:
            if self in self.armed_list:
                self.armed_list.remove(self)
        except:
            pass
        
        self.loaded = False

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
        # By now let's presume all CueList objects are _local
        self._local = True

        return True
