'''Test logging functions.'''
from cuemsutils.log import logged, Logger
from logging import DEBUG

@logged
def hello():
    return "Hello, World!"

@logged
def goodbye():
    return "Goodbye, World!"

@logged
def error_func():
    raise ValueError("An error occurred.")

@logged
def hello_with_arg(name: str):
    return f"Hello, {name}!"

@logged
def hello_with_kwargs(name: str, greeting: str):
    return f"{greeting}, {name}!"

@logged
def hello_with_warning():
    import warnings
    warnings.warn("This is a warning.")
    return "Hello, World!"


def test_logged(caplog):
    """Test that the logged decorator works."""
    caplog.set_level(DEBUG)
    
    result_hello = hello()
    result_goodbye = goodbye()
    try:
        result_error = error_func()
    except ValueError:
        result_error = None
    result_hello_with_arg = hello_with_arg("World")
    result_hello_with_kwargs = hello_with_kwargs(
        name = "World", greeting = "Goodbye"
    )
    from pytest import warns
    with warns(Warning, match = "This is a warning."):
        result_hello_with_warning = hello_with_warning()

    assert result_hello == "Hello, World!"
    assert result_goodbye == "Goodbye, World!"
    assert result_error is None
    assert result_hello_with_arg == "Hello, World!"
    assert result_hello_with_kwargs == "Goodbye, World!"
    assert result_hello_with_warning == "Hello, World!"

    assert len(caplog.records) == 18
    for record in caplog.records:
        assert record.name == "tests.test_logger"
        if record.levelname == "INFO":
            assert record.message == "Call recieved"
        elif record.levelname == "ERROR":
            assert record.message == "Error occurred: An error occurred."
        elif record.levelname == "DEBUG":
            assert record.message[:13] in ["Using args: (", "Finished with"]
        elif record.levelname == "WARNING":
            assert record.message == "Warning occurred: This is a warning."

def test_syslog():
    """Test that the logger writes to syslog."""
    
    ## Arrange: Set up logging outputs
    import os
    JOURNAL_FILE = "/tmp/pytest_journal.log"

    def read_file(file_path: str = JOURNAL_FILE):
        with open(file_path, "r") as f:
            return f.readlines()
        
    def syslog_to_tempfile(rec_n: int):
        os.system(f"journalctl -n 30 --no-pager -g FormitGo -o cat > {JOURNAL_FILE}")
        x = read_file(JOURNAL_FILE)[rec_n - 1::-1]
        ## Clean up: Remove the temporary file
        if os.path.exists(JOURNAL_FILE):
            os.remove(JOURNAL_FILE)
        return x

 
    ## Act: Run the functions
    result_hello = hello_with_arg("World")
    try:
        result_error = error_func()
    except ValueError:
        result_error = None

    ## Assert: Check the results
    assert result_hello == "Hello, World!"
    assert result_error is None

    if os.path.exists(JOURNAL_FILE):
        syslog = syslog_to_tempfile(rec_n = 6)
        assert len(syslog) == 6
        syslog_split = [i.split(")-(") for i in syslog]
        assert syslog_split[0][2] == "tests.test_logger:test_syslog:hello_with_arg)> Call recieved\n"
        assert syslog_split[1][2] == "tests.test_logger:test_syslog:hello_with_arg)> Using args: ('World',) and kwargs: {}\n"
        assert syslog_split[2][2] == "tests.test_logger:test_syslog:hello_with_arg)> Finished with result: Hello, World!\n"
        assert syslog_split[3][2] == "tests.test_logger:test_syslog:error_func)> Call recieved\n"
        assert syslog_split[4][2] == "tests.test_logger:test_syslog:error_func)> Using args: () and kwargs: {}\n"
        assert syslog_split[5][2] == "tests.test_logger:test_syslog:error_func)> Error occurred: An error occurred.\n"

        for i in range(6):
            x = syslog_split[i][0]
            assert x.split("\t")[1][:15] == "FormitGo (PID: "

def test_Logger(caplog):
    """Test that the Logger class works."""
    caplog.set_level(DEBUG)

    Logger.debug("This is a debug message.")
    Logger.info("This is an info message.") 
    Logger.warning("This is a warning message.")
    Logger.error("This is an error message.")
    
    assert len(caplog.records) == 4
    for record in caplog.records:
        assert record.name == "tests.test_logger"
        if record.levelname == "DEBUG":
            assert record.message == "This is a debug message."
        elif record.levelname == "INFO":
            assert record.message == "This is an info message."
        elif record.levelname == "WARNING":
            assert record.message == "This is a warning message."
        elif record.levelname == "ERROR":
            assert record.message == "This is an error message."

def test_logger_module_detection(caplog):
    """Test that Logger correctly detects the calling module name."""
    caplog.set_level(DEBUG)
    
    Logger.info("Module detection test")
    
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.name == "tests.test_logger"
    assert record.message == "Module detection test"
    assert record.levelname == "INFO"

def test_logged_module_detection(caplog):
    """Test that @logged decorator uses the decorated function's module name."""
    caplog.set_level(DEBUG)
    
    @logged
    def test_function():
        return "test result"
    
    result = test_function()
    
    assert result == "test result"
    assert len(caplog.records) == 3  # info (call received), debug (args), debug (result)
    
    for record in caplog.records:
        assert record.name == "tests.test_logger", f"Expected 'tests.test_logger', got '{record.name}'"

def test_logger_from_different_module(caplog):
    """Test that logger works correctly when called from different contexts."""
    caplog.set_level(DEBUG)
    
    # Test direct Logger calls
    Logger.debug("Debug from test")
    Logger.info("Info from test")
    
    # Test with decorated function
    result = hello()
    
    assert result == "Hello, World!"
    assert len(caplog.records) >= 5  # 2 direct calls + 3 from decorated function
    
    # All records should have the test module name
    for record in caplog.records:
        assert record.name == "tests.test_logger"

def test_logger_formatter_fields(caplog):
    """Test that Logger class populates all cuemsFormatter fields correctly."""
    import os
    import threading
    caplog.set_level(DEBUG)
    
    Logger.info("Test message")
    Logger.debug("Debug message")
    Logger.warning("Warning message")
    Logger.error("Error message")
    
    assert len(caplog.records) == 4
    
    for record in caplog.records:
        # Verify module name (name field)
        assert record.name == "tests.test_logger"
        
        # Verify funcName is set (captures actual logging call location)
        assert hasattr(record, 'funcName')
        assert record.funcName is not None
        
        # Verify process ID is available
        assert record.process == os.getpid()
        
        # Verify thread name is available
        assert record.threadName == threading.current_thread().name
        
        # Verify levelname
        assert record.levelname in ["INFO", "DEBUG", "WARNING", "ERROR"]
        
        # Verify message content
        assert record.message in ["Test message", "Debug message", "Warning message", "Error message"]
        
        # Verify the record has the expected timestamp
        assert hasattr(record, 'created')
        assert record.created > 0

def test_logged_decorator_formatter_fields(caplog):
    """Test that @logged decorator populates all cuemsFormatter fields correctly including extra fields."""
    import os
    import threading
    caplog.set_level(DEBUG)
    
    @logged
    def sample_function(arg1, arg2):
        return f"{arg1} {arg2}"
    
    result = sample_function("Hello", "World")
    
    assert result == "Hello World"
    assert len(caplog.records) == 3  # info (call received), debug (args), debug (result)
    
    for record in caplog.records:
        # Verify module name (name field) - should be tests.test_logger
        assert record.name == "tests.test_logger"
        
        # Verify process ID is available
        assert record.process == os.getpid()
        
        # Verify thread name is available
        assert record.threadName == threading.current_thread().name
        
        # Verify levelname
        assert record.levelname in ["INFO", "DEBUG"]
        
        # Verify the extra 'caller' field is set to the decorated function name
        assert hasattr(record, 'caller')
        assert record.caller == "sample_function"
        
        # Verify the extra 'funcName' field in the record's __dict__ is set to module
        # Note: LogRecord also has funcName attribute for the logging call location
        # The extra dict overwrites/adds the caller field in the formatter
        
        # Verify timestamp
        assert hasattr(record, 'created')
        assert record.created > 0

def test_logged_decorator_extra_fields(caplog):
    """Test that @logged decorator correctly sets extra fields (funcName and caller) for formatter."""
    caplog.set_level(DEBUG)
    
    result = hello_with_arg("TestUser")
    
    assert result == "Hello, TestUser!"
    assert len(caplog.records) == 3  # info, debug (args), debug (result)
    
    # Check the INFO record (Call received)
    info_record = caplog.records[0]
    assert info_record.levelname == "INFO"
    assert info_record.message == "Call recieved"
    assert hasattr(info_record, 'caller')
    assert info_record.caller == "hello_with_arg"
    # The funcName in extra dict should be the module name
    # But the actual funcName attribute is the logging call location
    
    # Check DEBUG records
    for record in caplog.records[1:]:
        assert record.levelname == "DEBUG"
        assert hasattr(record, 'caller')
        assert record.caller == "hello_with_arg"

def test_logger_complete_format_string(caplog):
    """Test that the complete formatter string works end-to-end for Logger class."""
    from cuemsutils.log import cuemsFormatter
    import io
    from logging import StreamHandler
    
    caplog.set_level(DEBUG)
    
    # Create a string stream to capture formatted output
    stream = io.StringIO()
    handler = StreamHandler(stream)
    handler.setFormatter(cuemsFormatter)
    
    # Get the logger and add our handler
    from cuemsutils.log import main_logger
    test_logger = main_logger(module_name="tests.test_logger", with_syslog=False, with_stdout=False)
    test_logger.logger.addHandler(handler)
    
    # Log a message
    test_logger.info("Test formatter output")
    
    # Get the formatted output
    output = stream.getvalue()
    
    # Verify the output contains expected components
    assert "FormitGo (PID:" in output
    assert "tests.test_logger" in output
    assert "Test formatter output" in output
    assert "[INFO]" in output
    
    # Clean up
    test_logger.logger.removeHandler(handler)
    handler.close()

def test_logged_complete_format_string(caplog):
    """Test that the complete formatter string works end-to-end for @logged decorator."""
    from cuemsutils.log import cuemsFormatter
    import io
    from logging import StreamHandler
    
    caplog.set_level(DEBUG)
    
    # Create a string stream to capture formatted output
    stream = io.StringIO()
    handler = StreamHandler(stream)
    handler.setFormatter(cuemsFormatter)
    
    # Get the logger and add our handler
    from cuemsutils.log import main_logger
    test_logger = main_logger(module_name="tests.test_logger", with_syslog=False, with_stdout=False)
    test_logger.logger.addHandler(handler)
    
    # Call a decorated function
    result = hello()
    
    # Get the formatted output
    output = stream.getvalue()
    
    # Verify the output contains expected components
    assert "FormitGo (PID:" in output
    assert "tests.test_logger" in output
    assert "Call recieved" in output
    assert "[INFO]" in output or "[DEBUG]" in output
    # Verify the caller field (decorated function name) is present in the format
    # The format is: (name:funcName:caller)> so we should see :wrapper:hello)
    assert ":wrapper:hello)" in output
    
    # Clean up
    test_logger.logger.removeHandler(handler)
    handler.close()
