# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T051/T052 — the ``defaults.d`` overlay and the three-way preservation of
operator edits (feature 011, US4; FR-027, FR-027a, FR-027b, FR-033–FR-036)."""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from cuemsutils.tools import init_node


@pytest.fixture
def env(tmp_path):
    conf, state = tmp_path / "etc", tmp_path / "state"
    sysfs = tmp_path / "sys"
    (sysfs / "ethernet0").mkdir(parents=True)
    (sysfs / "ethernet0" / "address").write_text("aa:bb:cc:dd:ee:ff\n")
    overlay = tmp_path / "defaults.d"
    overlay.mkdir()
    base = ["--conf-dir", str(conf), "--state-dir", str(state), "--sysfs", str(sysfs),
            "--lock-file", str(tmp_path / "lock"), "--systemctl", "/bin/false", "--overlay", str(overlay)]
    return conf, overlay, base


def _run(base, *extra):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = init_node.main([*base, *extra])
    return code, out.getvalue(), err.getvalue()


def _settings_text(conf: Path, path: str) -> str:
    return ET.parse(conf / "settings.xml").getroot().findtext(f".//Settings/{path}")


def _sha(path: Path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


# -- T051 ------------------------------------------------------------------------


def test_one_overlay_scalar_lands_and_identity_is_kept(env):
    conf, overlay, base = env
    assert _run(base)[0] == 0
    uuid = ET.parse(conf / "settings.xml").getroot().findtext(".//node/uuid")
    (overlay / "10-venue.toml").write_text('[settings.SettingsType]\ncontroller_url = "controller.venue.local"\n')

    code, out, err = _run(base)
    assert code == 0, err
    assert _settings_text(conf, "controller_url") == "controller.venue.local"
    assert _settings_text(conf, "editor_url") == "formitgo.local"
    assert ET.parse(conf / "settings.xml").getroot().findtext(".//node/uuid") == uuid


def test_later_file_wins_and_verbose_names_it(env):
    conf, overlay, base = env
    (overlay / "10-a.toml").write_text('[settings.NodeConfType]\noscquery_ws_port = 9500\n')
    (overlay / "20-b.toml").write_text('[settings.NodeConfType]\noscquery_ws_port = 9600\n')
    code, out, err = _run(base, "--verbose")
    assert code == 0, err
    assert _settings_text(conf, "node/oscquery_ws_port") == "9600"
    assert "20-b.toml" in out and "oscquery_ws_port" in out


def test_typed_scalars_survive_end_to_end(env):
    conf, overlay, base = env
    (overlay / "10.toml").write_text('[settings.VideoPlayerType]\noutput_latency_ms = 35\n[settings.AudioPlayerType]\noutput_latency_ms = "auto"\n')
    assert _run(base)[0] == 0
    assert _settings_text(conf, "node/videoplayer/output_latency_ms") == "35"
    assert _settings_text(conf, "node/audioplayer/output_latency_ms") == "auto"


@pytest.mark.parametrize("content,needle", [
    ("this = = is not toml", "10.toml"),
    ('[settings.SettingsType]\nno_such_field = "x"\n', "no_such_field"),
    ('[settings.NodeConfType]\nuuid = "anything"\n', "identity is not a default"),
    ('[settings.NodeConfType]\noscquery_ws_port = "9190"\n', "oscquery_ws_port"),
])
def test_a_bad_overlay_refuses_before_writing(env, content, needle):
    conf, overlay, base = env
    assert _run(base)[0] == 0
    before = {p.name: _sha(p) for p in conf.iterdir()}
    (overlay / "10.toml").write_text(content)
    code, out, err = _run(base)
    assert code == 1
    assert needle in err
    assert {p.name: _sha(p) for p in conf.iterdir()} == before, "a refused overlay wrote something"


def test_no_overlay_ignores_the_directory(env):
    conf, overlay, base = env
    (overlay / "10.toml").write_text("this = = is not toml")
    base_no = [a for a in base if a not in ("--overlay", str(overlay))] + ["--no-overlay"]
    assert _run(base_no)[0] == 0


# -- T052 ------------------------------------------------------------------------


def _hand_edit(conf: Path, field: str, value: str) -> None:
    text = (conf / "settings.xml").read_text(encoding="utf-8")
    import re
    text = re.sub(rf"<{field}>[^<]*</{field}>", f"<{field}>{value}</{field}>", text, count=1)
    (conf / "settings.xml").write_text(text, encoding="utf-8")


def test_operator_edits_three_way(env):
    conf, overlay, base = env
    assert _run(base)[0] == 0
    uuid = ET.parse(conf / "settings.xml").getroot().findtext(".//node/uuid")
    _hand_edit(conf, "library_path", "/srv/venue/library")

    code, out, err = _run(base, "--dry-run")
    assert code == 0 and "would be written" not in out or "unchanged" in out
    assert _settings_text(conf, "library_path") == "/srv/venue/library", "--dry-run wrote"

    code, out, err = _run(base)
    assert code == 0, err
    assert _settings_text(conf, "library_path") == "/srv/venue/library", "the hand edit was clobbered"
    assert init_node.MODIFIED_KEPT in out and "library_path" in out and init_node.FIX_RESET in out

    code, out, err = _run(base, "--reset")
    assert code == 0, err
    assert _settings_text(conf, "library_path") == "/opt/cuems_library"
    assert "reverting" in out and "library_path" in out
    assert ET.parse(conf / "settings.xml").getroot().findtext(".//node/uuid") == uuid


def test_an_overlay_value_loses_to_a_hand_edit_without_reset(env):
    conf, overlay, base = env
    assert _run(base)[0] == 0
    _hand_edit(conf, "controller_url", "hand.local")
    (overlay / "10.toml").write_text('[settings.SettingsType]\ncontroller_url = "overlay.local"\n')
    assert _run(base)[0] == 0
    assert _settings_text(conf, "controller_url") == "hand.local"
    assert _run(base, "--reset")[0] == 0
    assert _settings_text(conf, "controller_url") == "overlay.local"


def test_without_a_write_record_every_difference_is_kept(env, tmp_path):
    conf, overlay, base = env
    assert _run(base)[0] == 0
    _hand_edit(conf, "tmp_path", "/tmp/venue")
    before = {p.name: _sha(p) for p in conf.iterdir()}
    (tmp_path / "state" / "init-node" / "last-written.json").unlink()

    code, out, err = _run(base)
    assert code == 0, err
    assert {p.name: _sha(p) for p in conf.iterdir()} == before, "zero values may change without a record"
    assert "no write record" in out


def test_other_rows_and_adoption_flags_survive_reset(env):
    conf, overlay, base = env
    assert _run(base)[0] == 0
    text = (conf / "network_map.xml").read_text(encoding="utf-8")
    other = ("<node><uuid>8c8f4d5e-3d5b-4b0a-9f5d-0a0a0a0a0a0a</uuid><mac>0011aabbccdd</mac><name>other</name>"
             "<node_role>controller</node_role><ip>10.0.0.2</ip><adopted>True</adopted><online>False</online></node>")
    (conf / "network_map.xml").write_text(text.replace("</node_list>", other + "</node_list>"), encoding="utf-8")
    assert _run(base, "--reset")[0] == 0
    rows = {r.findtext("uuid"): r for r in ET.parse(conf / "network_map.xml").getroot().findall(".//node")}
    kept = rows["8c8f4d5e-3d5b-4b0a-9f5d-0a0a0a0a0a0a"]
    assert kept.findtext("adopted") == "True" and kept.findtext("online") == "False"
