# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T008/T012 — the seed values as data (feature 011, research R4; contract
system-defaults-toml.md).

Four validation rules, each named for the failure it makes visible, plus the
byte-identity guarantee that the move from ``descriptor._SETTINGS_EXAMPLE_VALUES``
changed no value:

* **V1** a required scalar with no entry fails naming ``(schema, type, field)``
  and the file — the FR-034 guarantee of feature 008, relocated;
* **V2** an entry naming no declared field fails naming the key — the TOML
  cannot accumulate dead keys;
* **V3** ``uuid``/``mac`` in any table is refused — identity is never a default;
* **V4** an integer-typed field rejects a string form and vice versa, naming the
  key and both types — the distinction TOML was chosen to preserve.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from cuemsutils.xml import seed_values
from cuemsutils.xml.seed_values import SeedValueError

REPO_ROOT = Path(__file__).resolve().parents[2]
PRE_MOVE_SHA256 = "5635a078302cc6513b3a85e795ba0c4f75afa3adbcf9de8385755c604974da3d"


@pytest.fixture
def tables():
    return copy.deepcopy(seed_values.load_seed_values())


def test_the_shipped_file_passes_every_rule(tables):
    seed_values.validate(tables)


def test_v1_a_missing_required_scalar_names_schema_type_field_and_file(tables):
    del tables["settings"]["NodeConfType"]["oscquery_ws_port"]
    with pytest.raises(SeedValueError) as raised:
        seed_values.validate(tables)
    message = str(raised.value)
    assert "settings" in message and "NodeConfType" in message and "oscquery_ws_port" in message
    assert "system-defaults.toml" in message


def test_v1_does_not_demand_identity_fields(tables):
    """``uuid``/``mac`` are required by the schemas and injected by the tools."""
    seed_values.validate(tables)  # no uuid/mac anywhere, and it passes


def test_v2_a_stale_key_is_named(tables):
    tables["settings"]["SettingsType"]["retired_field"] = "x"
    with pytest.raises(SeedValueError, match=r"retired_field"):
        seed_values.validate(tables)


def test_v2_an_unknown_table_is_named(tables):
    tables["settings"]["NoSuchType"] = {"path": "/x"}
    with pytest.raises(SeedValueError, match=r"NoSuchType"):
        seed_values.validate(tables)


@pytest.mark.parametrize("field", ["uuid", "mac"])
def test_v3_identity_is_not_a_default(tables, field):
    tables["settings"]["NodeConfType"][field] = "anything"
    with pytest.raises(SeedValueError, match=r"identity is not a default"):
        seed_values.validate(tables)


def test_v4_an_integer_field_rejects_a_string_form(tables):
    tables["settings"]["NodeConfType"]["oscquery_ws_port"] = "9190"
    with pytest.raises(SeedValueError) as raised:
        seed_values.validate(tables)
    assert "oscquery_ws_port" in str(raised.value) and "int" in str(raised.value)


def test_v4_a_string_field_rejects_an_integer(tables):
    tables["settings"]["SettingsType"]["editor_url"] = 42
    with pytest.raises(SeedValueError) as raised:
        seed_values.validate(tables)
    assert "editor_url" in str(raised.value) and "str" in str(raised.value)


def test_v4_the_auto_or_int_union_keeps_both_forms(tables):
    """``35`` and ``"auto"`` are both valid and stay distinct (FR-035)."""
    tables["settings"]["VideoPlayerType"]["output_latency_ms"] = 35
    seed_values.validate(tables)
    tables["settings"]["VideoPlayerType"]["output_latency_ms"] = "auto"
    seed_values.validate(tables)
    tables["settings"]["VideoPlayerType"]["output_latency_ms"] = "35"
    with pytest.raises(SeedValueError, match=r"output_latency_ms"):
        seed_values.validate(tables)


def test_the_settings_table_matches_the_python_table_it_replaced(tables):
    """Entry for entry, the values D15 corrected — moved verbatim."""
    flat = seed_values.settings_table()
    assert flat[("SettingsType", "editor_url")] == "formitgo.local"
    assert flat[("DmxPlayerType", "output_latency_ms")] == 35
    assert flat[("VideoPlayerType", "output_latency_ms")] == "auto"
    assert flat[("AudioMixerType", "path")] == "/usr/bin/jack-volume"
    assert ("PlayerType", "path") not in flat
    assert "/usr/bin/cuems-player" not in set(flat.values())


def test_generated_settings_is_byte_identical_after_the_move(tmp_path):
    """T012 — the move changed no value (SC-005's precondition)."""
    from cuemsutils.xml.descriptor import generate_settings_example

    target = tmp_path / "settings.xml"
    generate_settings_example().save(target)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == PRE_MOVE_SHA256


def test_the_shipped_copy_is_package_data():
    """The loader reads package data, so an installed wheel carries the file."""
    assert seed_values.seed_file_path().name == "system-defaults.toml"
    assert seed_values.seed_file_path().read_bytes() == (
        REPO_ROOT / "src/cuemsutils/defaults/system-defaults.toml"
    ).read_bytes()
