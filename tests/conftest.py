import functools
import importlib
import os as _os

import pytest as _pytest


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


# ---------------------------------------------------------------------------
# Feature 011, T006 — the suite must not depend on a host /etc/cuems.
#
# Measured 2026-09-25 on a fresh box: 25 tests errored because four modules
# constructed ``ConfigManager(load_all=False)`` with no ``config_dir`` while
# ``tests/support/config_inventory.py`` pops ``CUEMS_CONF_PATH`` from the
# environment at import time, so the constructor's ``/etc/cuems/`` default had
# to exist on the developer's machine — the very condition the feature exists
# to remove. This guard makes that dependence a named failure instead of a
# ``FileNotFoundError`` three frames down.
# ---------------------------------------------------------------------------

@_pytest.fixture(autouse=True, scope="session")
def _no_host_etc_cuems_dependence():
    from cuemsutils.tools import ConfigManager as _cm

    original = _cm.ConfigManager.__init__
    default_dir = _cm.CUEMS_CONF_PATH

    @functools.wraps(original)  # keeps the signature the public API golden pins
    def guarded(self, config_dir=default_dir, load_all=True, *args, **kwargs):
        # CUEMS_CONF_PATH redirects load_base_settings, so a default config_dir
        # under a set variable is hermetic; only the bare default is the defect.
        if (config_dir == default_dir and not _os.path.isdir(default_dir)
                and not _os.environ.get("CUEMS_CONF_PATH")):
            _pytest.fail(
                f"{_os.environ.get('PYTEST_CURRENT_TEST', '<unknown test>')} constructs "
                "ConfigManager() without config_dir and would read the host's "
                f"{default_dir}. Pass config_dir=<corpus> explicitly (feature 011, T006)."
            )
        return original(self, config_dir, load_all, *args, **kwargs)

    _cm.ConfigManager.__init__ = guarded
    try:
        yield
    finally:
        _cm.ConfigManager.__init__ = original
