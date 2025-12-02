import sys
from logging import getLogger, LoggerAdapter, StreamHandler, Formatter, DEBUG, INFO, ERROR, WARNING, CRITICAL
from logging.handlers import SysLogHandler
from functools import wraps
from os import environ
import inspect

cuemsFormatter = Formatter('[%(asctime)s][%(levelname)s] \tFormitGo (PID: %(process)d)-(%(threadName)-9s)-(%(name)s:%(funcName)s:%(caller)s)> %(message)s')

# Cache for module-specific loggers to avoid duplicate handlers
_logger_cache = {}

def log_level_to_obj(log_level):
    """
    Convert a log level string to a logging level object.
    """
    return {
        'DEBUG': DEBUG,
        'INFO': INFO,
        'WARNING': WARNING,
        'ERROR': ERROR,
        'CRITICAL': CRITICAL
    }[log_level]

class CuemsLoggerAdapter(LoggerAdapter):
    """Custom LoggerAdapter that properly merges extra dictionaries."""
    
    def process(self, msg, kwargs):
        """
        Process the logging call to merge extra dictionaries.
        Ensures that both adapter-level and call-level extra dicts are merged.
        """
        # Start with a copy of the adapter's extra dict (with default caller='')
        extra = {'caller': ''}
        extra.update(self.extra)
        
        # Merge in any extra dict from the logging call
        if 'extra' in kwargs:
            extra.update(kwargs['extra'])
        
        kwargs['extra'] = extra
        return msg, kwargs

def main_logger(module_name = None, with_syslog = True, with_stdout = True):
    """
    Create a root logger with a custom formatter.
    
    Args:
        module_name: Name of the module to create logger for. Defaults to __name__ if None.
        with_syslog: Whether to add syslog handler.
        with_stdout: Whether to add stdout handler.
    """
    if module_name is None:
        module_name = __name__
    
    # Return cached logger if it exists
    if module_name in _logger_cache:
        return _logger_cache[module_name]
    
    logger = getLogger(module_name)
    try:
        log_level = log_level_to_obj(environ['CUEMS_LOG_LEVEL'].upper())
    except KeyError:
        log_level = DEBUG
    logger.setLevel(log_level)

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

    logger_adapter = CuemsLoggerAdapter(logger, {})
    _logger_cache[module_name] = logger_adapter
    return logger_adapter

class Logger:
    """
    A class for logging messages with different log levels.

    This class provides static methods for logging messages with different log levels.
    It dynamically detects the calling module to use the appropriate logger.
    """

    @staticmethod
    def _get_caller_module():
        """
        Get the module name of the caller by inspecting the call stack.
        """
        frame = inspect.currentframe()
        try:
            # Go up the stack: _get_caller_module -> log/debug/info/etc -> actual caller
            caller_frame = frame.f_back.f_back.f_back
            module_name = caller_frame.f_globals.get('__name__', __name__)
            return module_name
        finally:
            del frame

    @staticmethod
    def log(level, message, **kwargs):
        module_name = Logger._get_caller_module()
        logger = main_logger(module_name=module_name)
        logger.log(level, message, stacklevel = 4, **kwargs)
    
    @staticmethod
    def debug(message, **kwargs):
        Logger.log(DEBUG, message, **kwargs)
    
    @staticmethod
    def info(message, **kwargs):
        Logger.log(INFO, message, **kwargs)

    @staticmethod
    def error(message, **kwargs):
        Logger.log(ERROR, message, **kwargs)

    @staticmethod
    def exception(message, **kwargs):
        Logger.log(ERROR, message, **kwargs)

    @staticmethod
    def warning(message, **kwargs):
        Logger.log(WARNING, message, **kwargs)

    @staticmethod
    def critical(message, **kwargs):
        Logger.log(CRITICAL, message, **kwargs)

def logged(func):
    """
    A decorator function to log information about function calls and their results.
    """
    # Get logger for the function's module
    func_logger = main_logger(module_name=func.__module__)

    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        The wrapper function that logs function calls and their results.
        """
        # Only set caller field (the decorated function name)
        # funcName is automatically set by logging to the actual calling function (wrapper)
        d = {"caller": func.__name__}
        func_logger.debug(f"Call recieved", extra = d)
        func_logger.debug(f"Using args: {args} and kwargs: {kwargs}", extra = d)
        try:
            result = func(*args, **kwargs)
            func_logger.debug(f"Finished with result: {result}", extra = d)
        except Warning as w:
            func_logger.warning(f"Warning occurred: {w}", extra = d)
            return result
        except Exception as e:
            func_logger.error(f"Error occurred: {e}", extra = d)
            raise
        
        else:
            return result

    return wrapper
