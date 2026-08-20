"""D1 (T058) — ``cuemsutils.xml.Settings`` is a **class**, and it is callable.

The hazard this guards has been diagnosed and fixed once already, and it is the
kind that comes back.

``Settings.py`` and ``XmlReaderWriter.py`` are real submodules whose names
collide with the classes the package binds. The *first* import of either makes
Python set it as an attribute of ``cuemsutils.xml`` — clobbering the class of
the same name. Whichever assignment happens last wins, so before the import
order was pinned the winner depended on whether some consumer had already
imported the old path. ``from cuemsutils.xml import Settings`` then handed back
a **module**, and calling it raised::

    TypeError: 'module' object is not callable

``xml/__init__.py`` fixes it by importing both shim modules *first*, so the
class bindings come last and win permanently. Those two lines carry a comment
saying "do not remove these"; this file is what fails if someone does anyway.

It matters more after T062, not less. ``__all__`` is now empty, which makes the
two ``from . import … as _shim`` lines look like dead imports of names nothing
exports — exactly the kind of thing a tidy-up deletes.
"""

from __future__ import annotations

import importlib
import inspect
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

SHADOWED = ["Settings", "XmlReaderWriter"]

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("name", SHADOWED)
def test_the_package_attribute_is_a_class_not_a_module(name):
    import cuemsutils.xml as xml_package

    resolved = getattr(xml_package, name)
    assert inspect.isclass(resolved), (
        f"cuemsutils.xml.{name} resolved to a {type(resolved).__name__}; the "
        f"submodule of the same name clobbered the class binding"
    )


@pytest.mark.parametrize("name", SHADOWED)
def test_the_package_attribute_is_callable(name):
    """The symptom, asserted as the symptom.

    ``inspect.isclass`` and "is callable" are the same thing here today, and
    stating both is deliberate: the failure a consumer reports is
    ``TypeError: 'module' object is not callable``, and a test that only
    checked the type would not obviously be about that report.
    """
    import cuemsutils.xml as xml_package

    assert callable(getattr(xml_package, name))


def test_the_class_survives_importing_the_shadowing_submodule_afterwards():
    """The original failure mode, reproduced in order.

    A consumer that imports the old path *after* the package has been imported
    triggers the attribute assignment that used to win.
    """
    import cuemsutils.xml as xml_package

    importlib.import_module("cuemsutils.xml.Settings")
    assert inspect.isclass(xml_package.Settings)

    importlib.import_module("cuemsutils.xml.XmlReaderWriter")
    assert inspect.isclass(xml_package.XmlReaderWriter)


@pytest.mark.parametrize("name", SHADOWED)
def test_it_holds_in_a_fresh_interpreter_that_imports_the_old_path_first(name):
    """The order that actually broke it, in a process where it can happen.

    Within one test session ``cuemsutils.xml`` is already imported, so the
    interesting sequence — old path first, package second — cannot be staged.
    A subprocess can.
    """
    script = (
        f"import cuemsutils.xml.{name}\n"
        "import inspect\n"
        "import cuemsutils.xml as p\n"
        f"assert inspect.isclass(p.{name}), type(p.{name})\n"
        f"print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_the_two_protective_imports_are_still_there():
    """Asserted on the source, because their *effect* is what is fragile.

    Both lines are ``noqa: F401`` imports bound to underscore-prefixed names
    that nothing reads. Every automated cleanup and half the human ones would
    remove them, and the only thing that goes wrong is a ``TypeError`` in a
    consumer repository.
    """
    import cuemsutils.xml as xml_package

    source = Path(xml_package.__file__).read_text(encoding="utf-8")
    assert "from . import Settings as _settings_shim" in source
    assert "from . import XmlReaderWriter as _xml_reader_writer_shim" in source


def test_instantiating_through_the_package_still_warns_and_works():
    """The whole point: the name resolves *and* the shim behaves."""
    import cuemsutils.xml as xml_package

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        settings = xml_package.Settings(
            "tests/data/corpus/cuems-utils/settings.xml"
        )

    assert settings.get_dict()["library_path"]
    assert [w for w in caught if issubclass(w.category, DeprecationWarning)]
