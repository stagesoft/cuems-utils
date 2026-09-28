# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""The seed values as data (feature 011, research R4).

``system-defaults.toml`` holds the *values* the generated documents carry;
*structure* keeps coming from the XSD through the descriptor. This module
loads the file, checks it against the schemas (V1–V4 below), and merges an
operator overlay over it. It is the one code path both the build-time
generator (``make_defaults``) and ``cuems-init-node`` use, so the two can
never disagree about what a default is.

Rules (contract ``system-defaults-toml.md``):

* **V1** every required scalar of every table the documents use has an
  entry — a missing one fails naming ``(schema, type, field)`` and the file
  (the FR-034 guarantee of feature 008, relocated). Identity fields (``uuid``,
  ``mac``) are exempt: they are injected, never seeded.
* **V2** every entry names a declared field of its type; a table names a known
  type.
* **V3** ``uuid``/``mac`` never appear in any table.
* **V4** the TOML scalar's type matches the field's XSD type: an integer
  element rejects a string form and vice versa.

Overlays (``/etc/cuems/defaults.d/*.toml``) are partial by nature, so V1 does
not apply to them; V2–V4 do.
"""

from __future__ import annotations

import tomllib
from importlib import resources
from pathlib import Path
from typing import Any

from .schema import get_schema
from .spec import FieldKind, TypeKey, derive

SEED_FILE_NAME = "system-defaults.toml"

#: Fields no table may carry: identity is assigned by ``cuems-init-node``.
IDENTITY_FIELDS = frozenset({"uuid", "mac"})

#: The reserved "not provisioned" identity (design D3, practice 7). The
#: build-time generator writes it; ``cuems-init-node`` replaces it on a live
#: node; ``--check`` reports it as ``NOT PROVISIONED``.
SENTINEL_UUID = "00000000-0000-0000-0000-000000000000"
SENTINEL_MAC = "000000000000"
SENTINEL_IDENTITY = {"uuid": SENTINEL_UUID, "mac": SENTINEL_MAC}

#: Every table the three generated documents draw on, mapped to the descriptor
#: key that declares its fields. Anonymous root types are reached by element
#: path (``is_path=True``), exactly as ``descriptor.generate_settings_example``
#: reaches ``SettingsType``.
TABLE_KEYS: dict[tuple[str, str], TypeKey] = {
    ("settings", "SettingsType"): TypeKey("settings", "CuemsSettings/Settings", is_path=True),
    ("settings", "NodeConfType"): TypeKey("settings", "NodeConfType"),
    ("settings", "VideoPlayerType"): TypeKey("settings", "VideoPlayerType"),
    ("settings", "AudioPlayerType"): TypeKey("settings", "AudioPlayerType"),
    ("settings", "AudioMixerType"): TypeKey("settings", "AudioMixerType"),
    ("settings", "DmxPlayerType"): TypeKey("settings", "DmxPlayerType"),
    ("network_map", "NodeType"): TypeKey("network_map", "NodeType"),
    ("project_mappings", "CuemsProjectMappingsType"): TypeKey(
        "project_mappings", "CuemsProjectMappings", is_path=True
    ),
    ("project_mappings", "NodeMappingType"): TypeKey("project_mappings", "NodeMappingType"),
}

Tables = dict[str, dict[str, dict[str, Any]]]


class SeedValueError(ValueError):
    """A seed file or overlay that the schemas do not accept, named precisely."""


def seed_file_path() -> Path:
    """Where the shipped seed file is (package data)."""
    with resources.as_file(resources.files("cuemsutils.defaults") / SEED_FILE_NAME) as path:
        return Path(path)


def load_seed_values(path: Path | None = None) -> Tables:
    """Parse the seed file (or ``path``) into ``{schema: {Type: {field: value}}}``.

    Parsing only — call :func:`validate` for V1–V4.
    """
    source = Path(path) if path is not None else seed_file_path()
    try:
        with source.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise SeedValueError(f"{source}: {exc}") from exc
    return _shape(data, source)


def _shape(data: dict, source: Path) -> Tables:
    tables: Tables = {}
    for schema, types in data.items():
        if not isinstance(types, dict):
            raise SeedValueError(f"{source}: [{schema}] must be a table of types")
        for type_name, fields in types.items():
            if not isinstance(fields, dict):
                raise SeedValueError(f"{source}: [{schema}.{type_name}] must be a table")
            tables.setdefault(schema, {})[type_name] = dict(fields)
    return tables


# -- validation -----------------------------------------------------------------


def _scalar_fields(key: TypeKey):
    return [f for f in derive(key).fields if f.kind is FieldKind.ELEMENT and f.child is None]


def _simple_type(schema_name: str, xsd_type: str | None):
    """The ``xmlschema`` simple type for a field's declared type, or ``None``."""
    if xsd_type is None:
        return None
    schema = get_schema(schema_name)
    if xsd_type in schema.types:
        return schema.types[xsd_type]
    qualified = f"{{http://www.w3.org/2001/XMLSchema}}{xsd_type}"
    return schema.maps.types.get(qualified)


def _check_scalar_type(schema_name: str, type_name: str, field, value: Any, where: str) -> None:
    """V4: the TOML scalar's Python type must match what the XSD type decodes to."""
    simple = _simple_type(schema_name, field.xsd_type)
    if simple is None:
        return
    lexical = str(value)
    if not simple.is_valid(lexical):
        raise SeedValueError(
            f"{where}: [{schema_name}.{type_name}] {field.name} = {value!r} is not a valid "
            f"{field.xsd_type} value"
        )
    decoded = simple.decode(lexical)
    if type(decoded) is not type(value):
        raise SeedValueError(
            f"{where}: [{schema_name}.{type_name}] {field.name} = {value!r} has type "
            f"{type(value).__name__}; the schema type {field.xsd_type} needs "
            f"{type(decoded).__name__} form"
        )


def validate(tables: Tables, *, complete: bool = True, where: str | None = None) -> None:
    """Apply V1–V4 to ``tables``; ``complete=False`` skips V1 (overlays)."""
    where = where or SEED_FILE_NAME
    for schema_name, types in tables.items():
        for type_name, fields in types.items():
            key = TABLE_KEYS.get((schema_name, type_name))
            if key is None:
                raise SeedValueError(
                    f"{where}: [{schema_name}.{type_name}] names no type the generated "
                    f"documents use; known tables: {sorted(f'{s}.{t}' for s, t in TABLE_KEYS)}"
                )
            declared = {f.name: f for f in _scalar_fields(key)}
            for name, value in fields.items():
                if name in IDENTITY_FIELDS:
                    raise SeedValueError(
                        f"{where}: [{schema_name}.{type_name}] sets {name}: identity is not a "
                        "default — cuems-init-node assigns it"
                    )
                if name not in declared:
                    raise SeedValueError(
                        f"{where}: [{schema_name}.{type_name}] names {name}, which "
                        f"{schema_name}.xsd does not declare as a scalar of that type — "
                        "remove the stale key"
                    )
                _check_scalar_type(schema_name, type_name, declared[name], value, where)
    if complete:
        for (schema_name, type_name), key in TABLE_KEYS.items():
            present = tables.get(schema_name, {}).get(type_name, {})
            for field in _scalar_fields(key):
                if field.required and field.name not in IDENTITY_FIELDS and field.name not in present:
                    raise SeedValueError(
                        f"{schema_name}.xsd's {type_name}.{field.name} has no seed value in "
                        f"{where} — add one under [{schema_name}.{type_name}]"
                    )


# -- overlay ---------------------------------------------------------------------


def load_overlays(directory: Path) -> list[tuple[Path, Tables]]:
    """Every ``*.toml`` under ``directory`` in lexical order, parsed and checked (V2–V4)."""
    overlays: list[tuple[Path, Tables]] = []
    if not directory.is_dir():
        return overlays
    for path in sorted(directory.glob("*.toml")):
        tables = load_seed_values(path)
        validate(tables, complete=False, where=str(path))
        overlays.append((path, tables))
    return overlays


def merge(base: Tables, overlays: list[tuple[Path, Tables]]) -> tuple[Tables, dict[tuple[str, str, str], Path]]:
    """Apply ``overlays`` over ``base``; later files win. Returns the merged
    tables and, per overridden key, the file that supplied the winning value."""
    merged: Tables = {s: {t: dict(f) for t, f in types.items()} for s, types in base.items()}
    provenance: dict[tuple[str, str, str], Path] = {}
    for path, tables in overlays:
        for schema_name, types in tables.items():
            for type_name, fields in types.items():
                target = merged.setdefault(schema_name, {}).setdefault(type_name, {})
                for name, value in fields.items():
                    target[name] = value
                    provenance[(schema_name, type_name, name)] = path
    validate(merged, complete=True, where="merged seed values")
    return merged, provenance


# -- accessors ---------------------------------------------------------------------


def value_for(tables: Tables, schema_name: str, type_name: str, field: str) -> Any:
    """One value, or ``SeedValueError`` naming what to add."""
    try:
        return tables[schema_name][type_name][field]
    except KeyError:
        raise SeedValueError(
            f"{schema_name}.xsd's {type_name}.{field} has no seed value in {SEED_FILE_NAME} — "
            f"add one under [{schema_name}.{type_name}]"
        ) from None


_CACHE: Tables | None = None


def shipped() -> Tables:
    """The shipped seed values, validated once per process."""
    global _CACHE
    if _CACHE is None:
        tables = load_seed_values()
        validate(tables)
        _CACHE = tables
    return _CACHE


def settings_table() -> dict[tuple[str, str], Any]:
    """The ``settings`` tables flattened to ``{(TypeName, field): value}`` — the
    shape ``descriptor._SETTINGS_EXAMPLE_VALUES`` had, for the tests that read it."""
    return {
        (type_name, field): value
        for type_name, fields in shipped().get("settings", {}).items()
        for field, value in fields.items()
    }


def settings_value(type_name: str, field: str, tables: Tables | None = None) -> Any:
    """``descriptor._settings_example_value``'s replacement: no base-class
    fallback (D16-B); a missing entry raises naming the file and the fix.

    Identity fields answer with the **sentinel** (D3): the generated document is
    the pristine, never-specialised one, and the seed file never carries an
    identity by rule V3. ``tables`` defaults to the shipped values; the tool
    passes the merged seed-plus-overlay tables.
    """
    if field in IDENTITY_FIELDS:
        return SENTINEL_IDENTITY[field]
    source = tables if tables is not None else shipped()
    try:
        return source["settings"][type_name][field]
    except KeyError:
        raise RuntimeError(
            f"settings.xsd's {type_name}.{field} has no example value in "
            f"{SEED_FILE_NAME} — add one under [settings.{type_name}]"
        ) from None
