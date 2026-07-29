import sys
from logging import getLogger, LoggerAdapter, NullHandler, StreamHandler, Formatter, DEBUG, INFO, ERROR, WARNING, CRITICAL
from logging.handlers import SysLogHandler
from functools import wraps
from os import environ
from os.path import basename
import inspect

cuemsFormatter = Formatter('[%(asctime)s][%(levelname)s] \tFormitGo (PID: %(process)d)-(%(threadName)-9s)-(%(name)s:%(funcName)s:%(caller)s)> %(message)s')

# Third-party libraries sometimes call the module-level logging.info()/
# warning() helpers at import time (pyossia does, from cuemsengine.osc).
# Those helpers run logging.basicConfig() whenever the root logger has no
# handlers, which attaches a StreamHandler(stderr) using logging.BASIC_FORMAT
# to root. Since the loggers built below propagate, every CUEMS record then
# gets re-emitted through that handler as a second, differently formatted
# line — on top of the stdout and syslog copies. Under systemd all of them
# land in the same journal, so each message was recorded three times.
#
# Seeding root with a NullHandler makes the implicit basicConfig() a no-op:
# it returns early once root has any handler. Propagation is deliberately
# left enabled — pytest's caplog fixture captures through a root handler and
# depends on records reaching it.
getLogger().addHandler(NullHandler())

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

def _syslog_ident():
    """
    Tag to prefix onto /dev/log datagrams, e.g. 'controller-engine: '.

    journald derives SYSLOG_IDENTIFIER by parsing a leading 'TAG:' or
    'TAG[PID]:' off the datagram. Without one the entry carries no
    identifier and journalctl falls back to _COMM, which the kernel
    truncates to 15 characters — 'controller-engine' rendered as
    'controller-engi', looking like a second, unrelated process.

    The PID is deliberately left out: journald fills _PID from the socket
    credentials, so it is always right, whereas a tag built once at handler
    creation would go stale across a fork.
    """
    name = basename(sys.argv[0] or '') or 'cuems'
    return f'{name}: '

def main_logger(module_name = None, with_syslog = True, with_stdout = True):
    """
    Create a root logger with a custom formatter.

    Args:
        module_name: Name of the module to create logger for. Defaults to __name__ if None.
        with_syslog: Whether to add syslog handler.
        with_stdout: Whether to add stdout handler.

    Under systemd both handlers terminate in the same journal, so only the
    syslog one is attached there — see the comment on the stdout branch.
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

    # Under systemd, stdout and /dev/log both terminate in journald, so
    # attaching both handlers records every message twice. Keep the syslog
    # one: it is the only copy that carries the record's real priority.
    # systemd stamps every stdout line PRIORITY=6 (info) regardless of the
    # Python level, so a journalctl -p filter — which is what
    # `cuems-logs -l/--level` and `-e/--errors` are built on — cannot tell a
    # DEBUG line from an ERROR one on the stdout copy.
    #
    # JOURNAL_STREAM is set by systemd exactly when stdout/stderr are wired
    # to the journal. When it is absent (interactive runs, pytest, a
    # container logging elsewhere) stdout is attached as before, so running
    # a component by hand still prints to the terminal.
    journald_stdout = with_syslog and 'JOURNAL_STREAM' in environ

    if with_stdout and not journald_stdout:
        sh = StreamHandler(sys.stdout)
        sh.setFormatter(cuemsFormatter)
        logger.addHandler(sh)

    if with_syslog:
        syslog_handler = SysLogHandler(
            address = '/dev/log', facility = 'local0'
        )
        syslog_handler.setFormatter(cuemsFormatter)
        syslog_handler.ident = _syslog_ident()
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
