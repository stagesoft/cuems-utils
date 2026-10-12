"""The config accessor inventory, by introspection (T040a).

FR-018 says *every accessor name that exists today is present after and means
the same thing*. "Today" needs a referent, and prose is not one: the spec's own
counts drift — contracts §C2 says "~15 scalar" where data-model.md says "~18",
and both are approximations from different vantage points. So the inventory is
**recorded** as a golden, generated from the classes themselves before any US3
change lands, and FR-018 is asserted against *that* rather than against a list
retyped into a test.

The record answers two questions per accessor, and only these two:

``kind``
    ``property`` or ``method``. A property that became a method would still be
    "present" by name while breaking every call site.

``return``
    the class name of what it returns when evaluated against the corpus config
    — or ``<raises: TypeName>`` for accessors that legitimately fail before
    ``load_project_config`` has run. This is what makes "returns an object, not
    a raw nested dict" checkable rather than assertable (CHK038): an accessor
    passes when ``type(value) is not dict``. Legitimately dict-shaped content
    is a declared-field object, whose type is *not* ``dict``.
"""

from __future__ import annotations

import inspect
import json
from os import environ
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = str(REPO_ROOT / "tests" / "data")
GOLDEN = REPO_ROOT / "tests" / "golden" / "api" / "config_accessors.json"

#: The project the inventory loads, so the project-scoped accessors report a
#: real value rather than the state they hold before any project is opened.
PROJECT = "test_project"


def build_config_manager(load_project: bool = True):
    """A ``ConfigManager`` over the vendored test configuration.

    The directory is passed as an **argument** and ``CUEMS_CONF_PATH`` is
    cleared rather than set. ``load_base_settings`` prefers the environment
    variable over its argument, so setting it here — at module import time, in
    a worker shared with other tests — would silently redirect any later
    ``ConfigManager(config_dir=...)`` to this fixture. That is precisely what
    ``test_fail_no_conf_parameter`` measures, and it would stop failing for the
    wrong reason.
    """
    from cuemsutils.tools.ConfigManager import ConfigManager

    environ.pop("CUEMS_CONF_PATH", None)
    manager = ConfigManager(config_dir=CONFIG_DIR)
    if load_project:
        manager.load_project_config(PROJECT)
    return manager


def public_names(cls) -> list[str]:
    """Every public name ``cls`` defines or inherits, dunders excluded.

    Inherited names count: ``ConfigManager`` inherits most of its surface from
    ``ConfigBase``, and a consumer holding a ``ConfigManager`` does not know or
    care which class declares what.
    """
    return sorted(
        name
        for name in dir(cls)
        if not name.startswith("_") and not isinstance(getattr(cls, name, None), type)
    )


def _describe(cls, name: str, instance) -> dict:
    member = inspect.getattr_static(cls, name, None)

    if isinstance(member, property):
        entry = {"kind": "property"}
        try:
            value = getattr(instance, name)
        except Exception as exc:  # noqa: BLE001 - "it raises" is the record
            entry["return"] = f"<raises: {type(exc).__name__}>"
            return entry
        entry["return"] = type(value).__name__
        return entry

    if callable(member):
        return {
            "kind": "method",
            "signature": _signature(member),
        }

    # A plain instance attribute assigned in ``__init__`` — ``project_name``,
    # ``mappings`` before its property shadows it, ``node_hw_outputs``.
    # Recorded as an attribute rather than silently omitted: consumers read
    # these exactly as they read properties.
    try:
        value = getattr(instance, name)
    except Exception as exc:  # noqa: BLE001
        return {"kind": "attribute", "return": f"<raises: {type(exc).__name__}>"}
    return {"kind": "attribute", "return": type(value).__name__}


def _signature(member) -> str:
    try:
        return str(inspect.signature(member))
    except (TypeError, ValueError):  # pragma: no cover - builtins only
        return "<no signature>"


def snapshot() -> dict:
    """``{class name: {accessor: entry}}`` for ``ConfigBase`` and ``ConfigManager``."""
    from cuemsutils.tools.ConfigBase import ConfigBase
    from cuemsutils.tools.ConfigManager import ConfigManager

    manager = build_config_manager()
    out: dict[str, dict] = {}
    for cls in (ConfigBase, ConfigManager):
        out[cls.__name__] = {
            name: _describe(cls, name, manager) for name in public_names(cls)
        }
    return out


def load_golden() -> dict:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def write_golden() -> None:
    """Capture the inventory. Run **once**, before any US3 change (T040a)."""
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text(
        json.dumps(snapshot(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def accessor_entries(snapshot_dict: dict):
    """``(class, name, entry)`` for every property and attribute in a snapshot.

    Methods are excluded: FR-018 and FR-014 are about what an *accessor*
    returns, and ``conf_path('settings.xml')`` is a helper, not an accessor.
    """
    for class_name, entries in snapshot_dict.items():
        for name, entry in entries.items():
            if entry["kind"] in ("property", "attribute"):
                yield class_name, name, entry


if __name__ == "__main__":  # pragma: no cover - a capture tool, not a test
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    write_golden()
    print(f"wrote {GOLDEN.relative_to(REPO_ROOT)}")
