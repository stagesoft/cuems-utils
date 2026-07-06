import importlib


def _module_available(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


collect_ignore_glob = []

if not _module_available("pynng"):
    collect_ignore_glob += ["test_communicatorservices.py", "test_hubservices.py"]

if not _module_available("systemd"):
    collect_ignore_glob += ["test_signalengine.py"]
