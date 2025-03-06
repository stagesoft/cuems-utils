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
