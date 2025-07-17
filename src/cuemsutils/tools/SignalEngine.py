import signal
from os import getpid
from systemd.daemon import notify as notify_systemd_daemon
from time import sleep

from ..log import Logger, logged

class SignalEngine:
    """
    A class that handles system signals and status tracking.
    """
    def __init__(self, with_signals: bool = True):
        self.pid = getpid()
        Logger.info(f"Starting {self.__class__.__name__} with PID {self.pid}")
        self.running = False

        if with_signals:
            self.register_signals()

    ### RUNNING LOGIC ###
    @logged
    def start(self) -> None:
        self.running = True
        Logger.info(f"{self.__class__.__name__} started")
        self.run()

    def restart(self) -> None:
        pass

    def reload(self) -> None:
        pass

    @logged
    def run(self, tick: float = 3, max_tick: float | None = None) -> None:
        while self.running:
            sleep(tick)
            if max_tick is not None:
                if tick < max_tick:
                    tick += 0.01
                else:
                    self.stop()

    @logged
    def stop(self) -> None:
        self.stop_requested = True
        try:
            if hasattr(self, 'stop_all'):
                self.stop_all()  # type: ignore[attr-defined]
        except:
            Logger.warning('Exception when calling stop_all')
        self.running = False

    ### COMMUNICATE WITH SYSTEMD ###
    def notify_systemd(self, status: str = 'READY'):
        Logger.debug('Startup complete, notifying systemd')
        notify_systemd_daemon(f'{status.upper()}=1')

    ### SIGNALS HANDLERS ###
    def register_signals(self) -> None:
        signal.signal(signal.SIGINT, self.handle_interrupt)
        signal.signal(signal.SIGTERM, self.handle_terminate)
        signal.signal(signal.SIGUSR1, self.handle_print_running)
        signal.signal(signal.SIGUSR2, self.handle_print_all)
        signal.signal(signal.SIGCHLD, self.handle_child_signal)

    def handle_interrupt(self, sigNum, frame) -> None:
        string = f'SIGINT received! Exiting with result code: {sigNum}'
        print('\n\n' + string + '\n\n')
        Logger.info(string)

        self.stop()
        sleep(0.1)
        exit()
    
    def handle_terminate(self, sigNum, frame) -> None:
        string = f'SIGTERM received! Exiting with result code: {sigNum}'
        print('\n\n' + string + '\n\n')
        Logger.info(string)

        self.stop()
        sleep(0.1)
        exit()

    def handle_print_all(self, sigNum, frame) -> None:
        Logger.info(f"STATUS REQUEST BY SIGUSR2 SIGNAL {sigNum}")
        if hasattr(self, 'print_all_status'):
            self.print_all_status()  # type: ignore[attr-defined]

    def handle_print_running(self, sigNum, frame) -> None:
        run_str = "" if self.running else " NOT"
        string = f"SIGNAL {sigNum} recieved: {self.__class__.__name__} is{run_str} running"
        Logger.info(string)
        print(string)

    def handle_child_signal(self, sigNum, frame):
        pass
        # Logger.info('Child process signal received, maybe from ws-server')
        # wait_return = os.waitid(os.P_PID, self.ws_pid, os.WEXITED)
        # Logger.info(wait_return)
        #if wait_return.si_code
