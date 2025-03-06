from time import sleep

from .MediaCue import MediaCue
from ..helpers import ensure_items
from ..log import logged, Logger

REQ_ITEMS = {
    'master_vol': 0
}

class AudioCue(MediaCue):
    def __init__(self, init_dict = None):
        if init_dict:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
            super().__init__(init_dict)

        self._player = None
        self._osc_route = None

    @property
    def master_vol(self):
        return super().__getitem__('master_vol')

    @master_vol.setter
    def master_vol(self, master_vol):
        super().__setitem__('master_vol', master_vol)

    def items(self):
        x = dict(super().items())
        for k in REQ_ITEMS.keys():
            x[k] = self[k]
        return x.items()

    def player(self, player):
        self._player = player

    def osc_route(self, osc_route):
        self._osc_route = osc_route

    @logged
    def audio_media_loop(self, ossia, mtc):
        try:
            loop_counter = 0
            duration = self.media.regions[0].out_time - self.media.regions[0].in_time

            while not self.media.regions[0].loop or loop_counter < self.media.regions[0].loop:
                while self._player.is_alive() and (mtc.main_tc.milliseconds < self._end_mtc.milliseconds):
                    sleep(0.005)

                if self._local:
                    # Recalculate offset and apply
                    self._end_mtc = self._start_mtc + (duration)
                    offset_to_go = float(-(self._start_mtc.milliseconds) + self.media.regions[0].in_time.milliseconds)
                    try:
                        key = f'{self._osc_route}/offset'
                        ossia.send_message(key, offset_to_go)
                    except KeyError:
                        Logger.debug(
                            f'Key error 3 in go_callback {key}',
                            extra = {"caller": self.__class__.__name__}
                        )

                loop_counter += 1

            if self._local:                
                try:
                    key = f'{self._osc_route}/mtcfollow'
                    ossia.send_message(key, 0)
                except KeyError:
                    Logger.debug(
                        f'Key error 4 in go_callback {key}',
                        extra = {"caller": self.__class__.__name__}
                    )

        except AttributeError:
            pass

    def stop(self):
        self._stop_requested = True
        if self._player and self._player.is_alive():
            self._player.kill()

    def check_mappings(self, settings):
        if not settings.project_node_mappings:
            return True

        found = True
        map_list = ['default']

        if settings.project_node_mappings['audio']['outputs']:
            for elem in settings.project_node_mappings['audio']['outputs']:
                for map in elem['mappings']:
                    map_list.append(map['mapped_to'])
        
        for output in self.outputs:
            if output['output_name'][:36] == settings.node_conf['uuid']:
                    self._local = True
                    if output['output_name'][37:] not in map_list:
                        found = False
                        break
            else:
                self._local = False
                found = True
            
        return found
