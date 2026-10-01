# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T061 — ``cuems-init-node --check`` (feature 011, US6; FR-032, research R14):
four locations, four exit classes with precedence 3 > 2 > 1, never writes.

**Extended by feature 012's T018a, in step with the widening it asserts
against.** Class 1 now also means "an identity is not converged" and the
verdict vocabulary gains ``migration-needed``. Left alone, every test below
would have stayed green while testing a superseded vocabulary — which is the
worst outcome available, because a green suite is read as evidence.

The extension is an extension: every assertion that was here is still here,
asserting the same value for the same condition. What is added is the
*boundary* — that the shipped verdicts did not move, and that the new one
appears only where the tool used to say ``coherent``.

Note the identities in this file are uuid4 already. That is not incidental: it
is why these tests keep passing unchanged, and it is what makes the two new
tests at the bottom — which use a uuid1 — the ones that exercise the widening.
"""

from __future__ import annotations

import hashlib
import io
import json
from contextlib import redirect_stdout

import pytest

from cuemsutils.tools import init_node

UUID = "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40"
OTHER = "8c8f4d5e-3d5b-4b0a-9f5d-0a0a0a0a0a0a"
SENTINEL = "00000000-0000-0000-0000-000000000000"


def _settings(uuid):
    return (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        '<cms:CuemsSettings xmlns:cms="https://stagelab.coop/cuems/" doc_version="2"><Settings>'
        f"<node><uuid>{uuid}</uuid><mac>aabbccddeeff</mac></node></Settings></cms:CuemsSettings>\n"
    )


def _map(*uuids):
    rows = "".join(f"<node><uuid>{u}</uuid><mac>{i:012x}</mac><name>n</name><node_role>node</node_role><ip>10.0.0.{i}</ip></node>" for i, u in enumerate(uuids, 1))
    return f'<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<cms:CuemsNetworkMap xmlns:cms="https://stagelab.coop/cuems/"><node_list>{rows}</node_list></cms:CuemsNetworkMap>\n'


def _mappings(uuid, default_video=""):
    return (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        '<cms:CuemsProjectMappings xmlns:cms="https://stagelab.coop/cuems/"><number_of_nodes>1</number_of_nodes>'
        "<defaults>"
        "<default class=\"audio\" direction=\"input\"/>"
        "<default class=\"audio\" direction=\"output\"/>"
        "<default class=\"video\" direction=\"input\"/>"
        f"<default class=\"video\" direction=\"output\">{default_video}</default>"
        "<default class=\"dmx\" direction=\"input\"/>"
        "<default class=\"dmx\" direction=\"output\"/>"
        "</defaults>"
        f"<nodes><node><uuid>{uuid}</uuid><mac>aabbccddeeff</mac></node></nodes><new_nodes/>"
        "</cms:CuemsProjectMappings>\n"
    )


def _avahi(*uuids):
    services = "".join(
        f'<service protocol="ipv4"><type>_cuems_{t}._tcp</type><port>9000</port>'
        f"<txt-record>node_role=node</txt-record><txt-record>uuid={u}</txt-record></service>"
        for t, u in zip(("nodeconf", "osc"), uuids)
    )
    return f'<?xml version="1.0"?><service-group><name replace-wildcards="yes">%h</name>{services}</service-group>\n'


@pytest.fixture
def coherent(tmp_path):
    conf = tmp_path / "etc"
    conf.mkdir()
    (conf / "settings.xml").write_text(_settings(UUID))
    (conf / "network_map.xml").write_text(_map(UUID, OTHER))
    (conf / "default_mappings.xml").write_text(_mappings(UUID))
    avahi = tmp_path / "cuems.service"
    avahi.write_text(_avahi(UUID, UUID))
    return conf, avahi


def _check(conf, avahi, as_json=False, extra=()):
    out = io.StringIO()
    with redirect_stdout(out):
        code = init_node.main(["--check", "--conf-dir", str(conf), "--avahi-service", str(avahi),
                               *extra, *(["--json"] if as_json else [])])
    return code, out.getvalue()


def _checksums(conf, avahi):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [*conf.iterdir(), avahi] if p.is_file()}


def test_coherent_node_exits_zero_with_four_ok_lines(coherent):
    conf, avahi = coherent
    before = _checksums(conf, avahi)
    code, out = _check(conf, avahi)
    assert code == 0, out
    assert out.count(": ok") == 3 and "source uuid=" in out
    assert "verdict: coherent" in out
    assert _checksums(conf, avahi) == before, "--check wrote something (G3)"


def test_missing_self_row_is_a_mismatch(coherent):
    conf, avahi = coherent
    (conf / "network_map.xml").write_text(_map(OTHER))
    code, out = _check(conf, avahi)
    assert code == 1
    assert "network_map.xml: MISMATCH" in out and "self-entry missing" in out
    assert init_node.FIX_PLAIN in out


def test_sentinel_token_inside_a_compound_string_is_a_mismatch(coherent):
    conf, avahi = coherent
    (conf / "default_mappings.xml").write_text(_mappings(UUID, default_video=f"{SENTINEL}_0"))
    code, out = _check(conf, avahi)
    assert code == 1 and "default_mappings.xml: MISMATCH" in out and "sentinel" in out


def test_avahi_disagreement_names_both_values(coherent):
    conf, avahi = coherent
    avahi.write_text(_avahi(UUID, OTHER))
    code, out = _check(conf, avahi)
    assert code == 1 and "cuems.service: MISMATCH" in out and OTHER in out and UUID in out
    assert init_node.FIX_NODECONF in out


def test_sentinel_source_exits_three_even_without_avahi(coherent):
    conf, avahi = coherent
    (conf / "settings.xml").write_text(_settings(SENTINEL))
    avahi.unlink()
    code, out = _check(conf, avahi)
    assert code == 3, out
    assert init_node.NOT_PROVISIONED in out and "expected" in out
    assert init_node.FIX_PLAIN in out


def test_absent_or_unreadable_location_exits_two_over_a_mismatch(coherent):
    conf, avahi = coherent
    (conf / "network_map.xml").write_text(_map(OTHER))  # a mismatch...
    (conf / "default_mappings.xml").write_text("<broken")  # ...and an unreadable one
    code, out = _check(conf, avahi)
    assert code == 2, out
    assert "default_mappings.xml: UNREADABLE" in out

    (conf / "default_mappings.xml").unlink()
    code, out = _check(conf, avahi)
    assert code == 2 and "default_mappings.xml: ABSENT" in out


def test_absent_avahi_on_a_provisioned_node_points_at_unmask(coherent):
    conf, avahi = coherent
    avahi.unlink()
    code, out = _check(conf, avahi)
    assert code == 2 and "cuems.service: ABSENT" in out and init_node.FIX_UNMASK in out


def test_json_output_carries_the_same_content(coherent):
    conf, avahi = coherent
    (conf / "network_map.xml").write_text(_map(OTHER))
    code, out = _check(conf, avahi, as_json=True)
    report = json.loads(out)
    assert code == 1 and report["exit_code"] == 1 and report["verdict"] == "mismatch"
    assert report["source"]["uuid"] == UUID
    assert any(loc["status"] == "MISMATCH" and loc["path"].endswith("network_map.xml") for loc in report["locations"])


# --- feature 012, T018a: the widening, asserted at the boundary --------------


def test_a_converged_node_still_reports_the_shipped_verdict(coherent):
    """Exit class 0 narrowed in wording ("and every identity converged") and
    not in behaviour for a node that was already converged. The uuid4 fixture
    above is that node, so this restates the file's opening assertion as a
    *boundary*: the widening must not have moved it."""
    conf, avahi = coherent
    code, out = _check(conf, avahi)
    assert code == 0 and "verdict: coherent" in out
    assert "migration-needed" not in out


def test_a_uuid1_identity_is_the_new_class_1(coherent):
    """The widening itself. Before feature 012 this node reported ``coherent``
    and exit 0 — internally consistent, unmigratable, and with no way for an
    operator to learn either."""
    conf, avahi = coherent
    legacy = "0367f391-ebf4-11b2-9f26-000000000001"
    (conf / "settings.xml").write_text(_settings(legacy))
    (conf / "network_map.xml").write_text(_map(legacy, OTHER))
    (conf / "default_mappings.xml").write_text(_mappings(legacy))
    avahi.write_text(_avahi(legacy, legacy))

    code, out = _check(conf, avahi)

    assert code == 1
    assert "verdict: migration-needed" in out
    assert init_node.FIX_REMINT in out


def test_the_shipped_verdicts_are_unchanged_in_spelling(coherent):
    """Principle III made mechanical. A consumer keying on any of these four
    strings keeps working; ``migration-needed`` is the only addition."""
    conf, avahi = coherent
    from cuemsutils.tools import identity_check

    assert identity_check.NOT_PROVISIONED == "NOT PROVISIONED"
    assert identity_check.MIGRATION_NEEDED == "migration-needed"

    code, out = _check(conf, avahi)
    assert code == 0 and "verdict: coherent" in out

    (conf / "network_map.xml").write_text(_map(OTHER))
    code, out = _check(conf, avahi)
    assert code == 1 and "verdict: mismatch" in out

    (conf / "default_mappings.xml").unlink()
    code, out = _check(conf, avahi)
    assert code == 2 and "verdict: absent or unreadable" in out

    (conf / "settings.xml").write_text(_settings(SENTINEL))
    code, out = _check(conf, avahi)
    assert code == 3 and f"verdict: {init_node.NOT_PROVISIONED}" in out


def test_the_json_report_keeps_every_shipped_field(coherent):
    """``Report`` grew five fields and lost none. Asserted as a superset so a
    future addition does not fail here, and by exact content for the five that
    a consumer already reads."""
    conf, avahi = coherent
    (conf / "network_map.xml").write_text(_map(OTHER))
    code, out = _check(conf, avahi, as_json=True)
    report = json.loads(out)
    assert set(report) >= {"source", "locations", "verdict", "exit_code", "fix"}
    assert code == 1 and report["verdict"] == "mismatch"
    for location in report["locations"]:
        assert set(location) >= {"path", "status", "detail", "values"}


def test_the_check_accepts_library_and_surveys_it(tmp_path, coherent):
    """T019: ``--library`` overrides the configured path. The fixture's
    ``settings.xml`` carries none, so without the flag this degrades to a
    configuration-only survey — and says so, which is the other half."""
    conf, avahi = coherent
    library = tmp_path / "library" / "projects" / "p"
    library.mkdir(parents=True)
    (library / "script.xml").write_text(
        '<cms:CuemsProject xmlns:cms="https://stagelab.coop/cuems/">'
        f"<CuemsScript><CueList><contents><VideoCue><outputs><VideoCueOutput>"
        f"<output_name>{UUID}_0</output_name>"
        "</VideoCueOutput></outputs></VideoCue></contents></CueList></CuemsScript>"
        "</cms:CuemsProject>"
    )

    code, out = _check(conf, avahi, extra=["--library", str(tmp_path / "library")])
    assert code == 0
    assert str(tmp_path / "library") in out

    code, out = _check(conf, avahi)
    assert "configuration directory only" in out
