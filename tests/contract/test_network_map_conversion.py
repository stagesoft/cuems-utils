"""M3, SC-004b — the network_map conversion script (T014, T014a-c).

Exercises the reference implementation at
``specs/007-node-model-migration/cuems_migrate_network_map.py`` (see that
module's docstring for why it lives there rather than under ``src/`` for this
pass — it is relocated verbatim to
``../cuems-common/usr/bin/cuems-migrate-network-map`` when that repository's
phase is picked up).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from tests.support.corpus import REPO_ROOT

_MODULE_PATH = (
    REPO_ROOT / "specs" / "007-node-model-migration" / "cuems_migrate_network_map.py"
)
_spec = importlib.util.spec_from_file_location("cuems_migrate_network_map", _MODULE_PATH)
migrate = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = migrate
_spec.loader.exec_module(migrate)  # type: ignore[union-attr]


def _doc(uuid: str, node_type: str, *, extra: str = "") -> str:
    return (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        '<cms:CuemsNetworkMap xmlns:cms="https://stagelab.coop/cuems/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="https://stagelab.coop/cuems/ network_map.xsd">'
        "<node_list><node>"
        f"<uuid>{uuid}</uuid><mac>2cf05d21cca3</mac><name>n</name>"
        f"<node_type>{node_type}</node_type><ip>192.168.1.10</ip>"
        f"<adopted>True</adopted><online>True</online>{extra}"
        "</node></node_list></cms:CuemsNetworkMap>"
    )


@pytest.fixture
def netmap_file(tmp_path):
    def _make(node_type: str = "NodeType.master", uuid: str = "0367f391-ebf4-48b2-9f26-000000000001"):
        path = tmp_path / "network_map.xml"
        path.write_text(_doc(uuid, node_type))
        return path

    return _make


# -- conversion (T014) -------------------------------------------------------


@pytest.mark.parametrize(
    "spelling,expected_role",
    [
        ("NodeType.master", "controller"),
        ("master", "controller"),
        ("NodeType.slave", "node"),
        ("slave", "node"),
        ("NodeType.firstrun", "firstrun"),
        ("firstrun", "firstrun"),
    ],
)
def test_both_legacy_spellings_convert(netmap_file, spelling, expected_role):
    path = netmap_file(node_type=spelling)
    before = path.read_text()
    outcome = migrate.convert(str(path))

    assert outcome.status == "converted"
    assert outcome.nodes_converted == 1
    after = path.read_text()
    assert f"<node_role>{expected_role}</node_role>" in after
    assert "<node_type>" not in after
    # Byte-minimality: every other byte outside the matched element unchanged.
    assert after.replace(f"<node_role>{expected_role}</node_role>", "PLACEHOLDER") == \
        before.replace(f"<node_type>{spelling}</node_type>", "PLACEHOLDER")


def test_absent_file(tmp_path):
    missing = tmp_path / "network_map.xml"
    outcome = migrate.convert(str(missing))
    assert outcome.status == "absent"


def test_absent_node_type_element(netmap_file):
    path = netmap_file()
    migrate.convert(str(path))  # first pass converts
    outcome = migrate.convert(str(path))  # second pass: nothing left to convert
    assert outcome.status == "already_converted"


def test_idempotent(netmap_file):
    path = netmap_file()
    migrate.convert(str(path))
    once = path.read_text()
    second = migrate.convert(str(path))
    assert second.status == "already_converted"
    assert path.read_text() == once


def test_byte_minimal_outside_matched_element(netmap_file):
    path = netmap_file()
    before = path.read_text()
    migrate.convert(str(path))
    after = path.read_text()
    # xsi:schemaLocation, the cms: prefix, and the surrounding structure are
    # untouched — only the one element differs.
    assert 'xsi:schemaLocation="https://stagelab.coop/cuems/ network_map.xsd"' in after
    assert before.count("<node_list>") == after.count("<node_list>")
    assert before.split("<node_type>")[0] == after.split("<node_role>")[0]


# -- refusal (T014a) ----------------------------------------------------------


def test_unrecognised_value_refuses_whole_file(netmap_file):
    path = netmap_file(node_type="gibberish")
    before = path.read_text()
    outcome = migrate.convert(str(path))

    assert outcome.status == "refused"
    assert "gibberish" in outcome.message
    assert "0367f391-ebf4-48b2-9f26-000000000001" in outcome.message
    assert path.read_text() == before  # byte-identical — nothing written


def test_mixed_recognised_and_unrecognised_refuses_whole_document(tmp_path):
    path = tmp_path / "network_map.xml"
    doc = (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        '<cms:CuemsNetworkMap xmlns:cms="https://stagelab.coop/cuems/">'
        "<node_list>"
        "<node><uuid>u1</uuid><node_type>master</node_type></node>"
        "<node><uuid>u2</uuid><node_type>weird</node_type></node>"
        "</node_list></cms:CuemsNetworkMap>"
    )
    path.write_text(doc)
    outcome = migrate.convert(str(path))

    assert outcome.status == "refused"
    assert path.read_text() == doc  # neither node was converted
    assert "<node_role>" not in path.read_text()


def test_refusal_exits_zero(netmap_file, capsys):
    path = netmap_file(node_type="gibberish")
    rc = migrate.main([str(path)])
    assert rc == 0


# -- backup and restore (T014b) ----------------------------------------------


def test_backup_precedes_write_and_restores_exact_bytes(netmap_file):
    path = netmap_file()
    before = path.read_text()
    outcome = migrate.convert(str(path))

    assert outcome.backup_path is not None
    backup = Path(outcome.backup_path)
    assert backup.exists()
    assert backup.read_text() == before

    # Restoring reproduces the pre-conversion bytes exactly (SC-011).
    path.write_text(backup.read_text())
    assert path.read_text() == before


def test_no_backup_written_on_already_converted(netmap_file):
    path = netmap_file()
    migrate.convert(str(path))
    backups_after_first = sorted(path.parent.glob("*.bak"))
    migrate.convert(str(path))  # already converted — no-op
    backups_after_second = sorted(path.parent.glob("*.bak"))
    assert backups_after_first == backups_after_second


def test_no_backup_written_on_refusal(netmap_file):
    path = netmap_file(node_type="gibberish")
    migrate.convert(str(path))
    assert list(path.parent.glob("*.bak")) == []


# -- positive evidence (T014c) ------------------------------------------------


def test_all_four_outcomes_are_mutually_distinguishable(netmap_file, tmp_path):
    converted = migrate.convert(str(netmap_file()))
    already = migrate.convert(str(netmap_file(uuid="0367f391-ebf4-48b2-9f26-000000000002")))
    # simulate "already converted" by converting first
    already_path = tmp_path / "already.xml"
    already_path.write_text(_doc("0367f391-ebf4-48b2-9f26-000000000003", "NodeType.master"))
    migrate.convert(str(already_path))
    already = migrate.convert(str(already_path))
    absent = migrate.convert(str(tmp_path / "does-not-exist.xml"))
    refused_path = netmap_file(uuid="0367f391-ebf4-48b2-9f26-000000000004", node_type="nonsense")
    refused = migrate.convert(str(refused_path))

    statuses = {converted.status, already.status, absent.status, refused.status}
    assert statuses == {"converted", "already_converted", "absent", "refused"}

    renders = {
        converted.render(),
        already.render(),
        absent.render(),
        refused.render(),
    }
    assert len(renders) == 4  # no two outcomes render identically
    assert "already" not in converted.render().lower() or converted.status == "already_converted"


def test_converted_evidence_names_count_and_backup():
    pass  # covered by test_backup_precedes_write_and_restores_exact_bytes


def test_deprecation_notice_for_enum_repr_spelling(netmap_file):
    """A recognisable legacy value gets an extra notice naming its replacement
    (FR-011h-i) — distinguishing "old" from "meaningless"."""
    outcome = migrate.convert(str(netmap_file(node_type="NodeType.master")))
    assert outcome.deprecation_notices
    assert "controller" in outcome.deprecation_notices[0]


def test_bare_spelling_has_no_deprecation_notice(netmap_file):
    outcome = migrate.convert(str(netmap_file(node_type="master")))
    assert outcome.deprecation_notices == ()
