from time import sleep

from .MediaCue import MediaCue
from ..CTimecode import CTimecode
from ..log import logged, Logger

class VideoCue(MediaCue):
    def __init__(self, init_dict = None):
        if init_dict:
            super().__init__(init_dict)
        self._player = None
        self._osc_route = None
        self._go_thread = None

        # TODO: Adjust framerates for universal use, by now 25 fps for video
        self._start_mtc = CTimecode(framerate=25)
        self._end_mtc = CTimecode(framerate=25)

    def player(self, player):
        self._player = player

    def osc_route(self, osc_route):
        self._osc_route = osc_route

    def items(self):
        x = dict(super().items())
        return x.items()

    @logged
    def video_media_loop(self, ossia, mtc):
        """Specific logic for video media loop at the end of a go_thread  call"""
        try:
            loop_counter = 0
            duration = self.media.regions[0].out_time - self.media.regions[0].in_time
            duration = duration.return_in_other_framerate(mtc.main_tc.framerate)
            in_time_adjusted = self.media.regions[0].in_time.return_in_other_framerate(mtc.main_tc.framerate)

            while not self.media.regions[0].loop or loop_counter < self.media.regions[0].loop:
                while mtc.main_tc.milliseconds < self._end_mtc.milliseconds:
                    sleep(0.005)

                if self._local:
                    try:
                        key = f'{self._osc_route}/jadeo/offset'
                        self._start_mtc = mtc.main_tc
                        self._end_mtc = self._start_mtc + duration
                        offset_to_go = in_time_adjusted.frame_number - self._start_mtc.frame_number
                        ossia.send_message(key, offset_to_go)
                        Logger.info(
                            key + " " + str(ossia._oscquery_registered_nodes[key][0].value),
                            extra = {"caller": self.__class__.__name__}
                        )
                    except KeyError:
                        Logger.debug(
                            f'Key error 1 (offset) in go_callback {key}',
                            extra = {"caller": self.__class__.__name__}
                        )
                
                loop_counter += 1

            if self._local:
                try:
                    key = f'{self._osc_route}/jadeo/cmd'
                    ossia.send_message(key, 'midi disconnect')
                    Logger.info(
                        key + " " + str(ossia._oscquery_registered_nodes[key][0].value),
                        extra = {"caller": self.__class__.__name__}
                    )
                except KeyError:
                    Logger.debug(
                        f'Key error 1 (disconnect) in arm_callback {key}',
                        extra = {"caller": self.__class__.__name__}
                    )

        except AttributeError:
            pass

    def stop(self):
        self._stop_requested = True

    def check_mappings(self, settings):
        if not settings.project_node_mappings:
            return True

        found = True
        map_list = ['default']

        if settings.project_node_mappings['video']['outputs']:
            for elem in settings.project_node_mappings['video']['outputs']:
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
