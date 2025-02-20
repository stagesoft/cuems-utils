import sys
from logging import getLogger, StreamHandler, Formatter, DEBUG, INFO, ERROR, WARNING
from logging.handlers import SysLogHandler
from functools import wraps

cuemsFormatter = Formatter('[%(asctime)s][%(levelname)s] \tFormitGo (PID: %(process)d)-(%(threadName)-9s)-(%(name)s:%(funcName)s:%(caller)s)> %(message)s')

def root_logger(with_syslog = True, with_stdout = True):
    """
    Create a root logger with a custom formatter.
    """
    logger = getLogger()
    logger.setLevel(DEBUG)

    if with_stdout:
        sh = StreamHandler(sys.stdout)
        sh.setFormatter(cuemsFormatter)
        logger.addHandler(sh)
    
    if with_syslog:
        syslog_handler = SysLogHandler(
            address = '/dev/log', facility = 'local0'
        )
        syslog_handler.setFormatter(cuemsFormatter)
        logger.addHandler(syslog_handler)

    return logger

class Logger:
    logger = root_logger()

    @staticmethod
    def log(level, message, extra):
        Logger.logger.log(level, message, stacklevel = 4, extra = extra)
    
    @staticmethod
    def log_debug(message, extra = {"caller": ''}):
        Logger.log(DEBUG, message, extra = extra)
    
    @staticmethod
    def log_info(message, extra = {"caller": ''}):
        Logger.log(INFO, message, extra = extra)

    @staticmethod
    def log_error(message, extra = {"caller": ''}):
        Logger.log(ERROR, message, extra = extra)

    @staticmethod
    def log_warning(message, extra = {"caller": ''}):
        Logger.log(WARNING, message, extra = extra)

def logged(func):
    """
    A decorator function to log information about function calls and their results.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        The wrapper function that logs function calls and their results.
        """
        d = {"caller": func.__name__}
        Logger.logger = getLogger(func.__module__)
        Logger.log_info(f"Call recieved", extra = d)
        Logger.log_debug(f"Using args: {args} and kwargs: {kwargs}", extra = d)
        try:
            result = func(*args, **kwargs)
            Logger.log_debug(f"Finished with result: {result}", extra = d)
        
        except Exception as e:
            Logger.log_error(f"Error occurred: {e}", extra = d)
            raise
        
        else:
            return result

    return wrapper
