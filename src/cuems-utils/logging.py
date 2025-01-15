import logging
from logging import handlers, Formatter



class Logger:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    logger = logging.getLogger() # no name = root logger
    logger.setLevel(logging.DEBUG)

    logger.propagate = False

    handler = handlers.SysLogHandler(address = '/dev/log', facility = 'local0')

    formatter = Formatter('Cuems:engine: (PID: %(process)d)-%(threadName)-9s)-(%(funcName)s) %(message)s')

    handler.setFormatter(formatter)
    logger.addHandler(handler)

