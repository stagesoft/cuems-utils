# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T035–T038 — ``cuems-init-node`` writes the coherent triple (feature 011, US3;
contract cuems-init-node.md). Every test drives ``init_node.main`` with the
``--conf-dir``/``--state-dir``/``--sysfs``/``--lock-file``/``--systemctl``
overrides, so nothing here touches the host."""

from __future__ import annotations

import hashlib
import re
import threading
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from cuemsutils.tools import init_node
from cuemsutils.tools.Uuid import UUID4_REGEX

SENTINEL = "00000000-0000-0000-0000-000000000000"
SENTINEL_MAC = "000000000000"
DOCUMENTS = ("settings.xml", "network_map.xml", "default_mappings.xml")


def _sysfs(tmp_path: Path, *interfaces: tuple[str, str]) -> Path:
    root = tmp_path / "sys-class-net"
    for name, mac in interfaces:
        (root / name).mkdir(parents=True)
        (root / name / "address").write_text(mac + "\n")
    (root / "lo").mkdir(parents=True, exist_ok=True)
    (root / "lo" / "address").write_text("00:00:00:00:00:00\n")
    return root


@pytest.fixture
def env(tmp_path):
    conf = tmp_path / "etc"
    state = tmp_path / "state"
    sysfs = _sysfs(tmp_path, ("ethernet0", "aa:bb:cc:dd:ee:01"), ("wifi0", "aa:bb:cc:dd:ee:02"))
    base = [
        "--conf-dir", str(conf), "--state-dir", str(state), "--sysfs", str(sysfs),
        "--lock-file", str(tmp_path / "lock"), "--systemctl", "/bin/false", "--no-overlay",
    ]
    return conf, state, base


def _run(base, *extra) -> int:
    return init_node.main([*base, *extra])


def _uuid_in(path: Path) -> str:
    return ET.parse(path).getroot().findtext(".//uuid")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# -- T035 ------------------------------------------------------------------------


def test_a_plain_run_writes_a_coherent_triple(env, tmp_path, monkeypatch):
    conf, state, base = env
    # Plant a compound token on the video output port. The six ports are built
    # by the generator, not seeded as scalars, so a seed-table key would be a
    # stale field (V2).
    from cuemsutils.xml import make_defaults
    original = make_defaults._default_mappings

    def _plant(tables, identity):
        doc = original(tables, identity)
        for item in doc["defaults"]:
            port = item["default"]
            if port["class"] == "video" and port["direction"] == "output":
                port["&"] = f"{SENTINEL}_0"
        return doc

    monkeypatch.setattr(make_defaults, "_default_mappings", _plant)

    assert _run(base) == 0

    for name in DOCUMENTS:
        assert (conf / name).exists(), name
        text = (conf / name).read_text(encoding="utf-8")
        assert SENTINEL not in text and SENTINEL_MAC not in text, f"{name} carries a sentinel token"
    uuid = _uuid_in(conf / "settings.xml")
    assert re.match(UUID4_REGEX, uuid)
    assert _uuid_in(conf / "network_map.xml") == uuid
    mappings = ET.parse(conf / "default_mappings.xml").getroot()
    assert mappings.findtext("./nodes/node/uuid") == uuid
    video_out = mappings.find("./defaults/default[@class='video'][@direction='output']")
    assert video_out is not None and video_out.text == f"{uuid}_0", "compound string not specialised (FR-026)"
    settings = ET.parse(conf / "settings.xml").getroot()
    assert settings.findtext(".//node/mac") == "aabbccddee01", "MAC must come from ethernet0 (FR-025a)"
    row = ET.parse(conf / "network_map.xml").getroot().find(".//node")
    import socket
    assert row.findtext("name") == socket.gethostname()
    assert re.match(r"^\d+\.\d+\.\d+\.\d+$", row.findtext("ip"))
    assert row.findtext("node_role") == "firstrun"

    from cuemsutils.tools.ConfigManager import ConfigManager
    ConfigManager(config_dir=str(conf), load_all=True)
    assert (state / "init-node" / "last-written.json").exists()


def test_mac_resolution_order_and_refusal(env, tmp_path):
    conf, state, base = env
    assert _run(base, "--mac", "112233445566") == 0
    assert ET.parse(conf / "settings.xml").getroot().findtext(".//node/mac") == "112233445566"

    conf2 = tmp_path / "etc2"
    sysfs = _sysfs(tmp_path / "s2", ("enp1s0", "de:ad:be:ef:00:01"))
    base2 = ["--conf-dir", str(conf2), "--state-dir", str(state), "--sysfs", str(sysfs),
             "--lock-file", str(tmp_path / "lock2"), "--systemctl", "/bin/false", "--no-overlay"]
    assert _run(base2) == 0
    assert ET.parse(conf2 / "settings.xml").getroot().findtext(".//node/mac") == "deadbeef0001"

    conf3 = tmp_path / "etc3"
    sysfs = _sysfs(tmp_path / "s3")  # loopback only
    base3 = ["--conf-dir", str(conf3), "--state-dir", str(state), "--sysfs", str(sysfs),
             "--lock-file", str(tmp_path / "lock3"), "--systemctl", "/bin/false", "--no-overlay"]
    assert _run(base3) == 1, "no determinable MAC must refuse (FR-025a)"
    assert not conf3.exists() or not any(conf3.iterdir()), "a refusal writes nothing"


def test_the_tool_imports_no_uuid_module_directly():
    """FR-039: only ``cuemsutils.tools.Uuid`` mints."""
    for module in ("init_node", "identity_check", "write_record"):
        source = (Path(init_node.__file__).parent / f"{module}.py").read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import uuid|from uuid import)", source, re.M), module


def test_the_self_row_is_seeded_through_ensure_and_other_rows_survive(env):
    conf, state, base = env
    conf.mkdir()
    other = (
        "<?xml version='1.0' encoding='utf-8'?>\n"
        '<cms:CuemsNetworkMap xmlns:cms="https://stagelab.coop/cuems/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" doc_version="1"><node_list>'
        "<node><uuid>8c8f4d5e-3d5b-4b0a-9f5d-0a0a0a0a0a0a</uuid><mac>0011aabbccdd</mac><name>other</name>"
        "<node_role>controller</node_role><ip>10.0.0.2</ip><adopted>True</adopted><online>False</online></node>"
        "</node_list></cms:CuemsNetworkMap>\n"
    )
    (conf / "network_map.xml").write_text(other, encoding="utf-8")

    assert _run(base) == 0

    root = ET.parse(conf / "network_map.xml").getroot()
    rows = {r.findtext("uuid"): r for r in root.findall(".//node")}
    assert len(rows) == 2
    kept = rows["8c8f4d5e-3d5b-4b0a-9f5d-0a0a0a0a0a0a"]
    assert kept.findtext("adopted") == "True" and kept.findtext("online") == "False" and kept.findtext("node_role") == "controller"


# -- T036 ------------------------------------------------------------------------


def test_identity_preserved_and_install_missing(env, tmp_path):
    conf, state, base = env
    assert _run(base) == 0
    uuid = _uuid_in(conf / "settings.xml")
    before = {n: _sha(conf / n) for n in DOCUMENTS}

    assert _run(base) == 0  # a re-run keeps identity and, with unchanged inputs, replaces nothing
    assert _uuid_in(conf / "settings.xml") == uuid
    assert {n: _sha(conf / n) for n in DOCUMENTS} == before, "G6: unchanged inputs must change no file"

    # --install-missing with settings.xml present and a sibling absent
    (conf / "network_map.xml").unlink()
    (conf / "default_mappings.xml").unlink()
    assert _run(base, "--install-missing") == 0
    assert _sha(conf / "settings.xml") == before["settings.xml"], "settings.xml rewritten under --install-missing"
    assert _uuid_in(conf / "network_map.xml") == uuid

    # --install-missing never touches a present sentinel or stub (G8)
    stub = b"<node_list/>"
    (conf / "network_map.xml").write_bytes(stub)
    sentinel_settings = (conf / "settings.xml").read_bytes().replace(uuid.encode(), SENTINEL.encode())
    (conf / "settings.xml").write_bytes(sentinel_settings)
    assert _run(base, "--install-missing") == 0
    assert (conf / "network_map.xml").read_bytes() == stub
    assert (conf / "settings.xml").read_bytes() == sentinel_settings

    # --install-missing with settings.xml absent mints
    for n in DOCUMENTS:
        (conf / n).unlink()
    assert _run(base, "--install-missing") == 0
    assert re.match(UUID4_REGEX, _uuid_in(conf / "settings.xml"))


def test_uuid_option_and_force_new_identity(env):
    conf, state, base = env
    assert _run(base, "--uuid", "not-a-uuid") == 1
    assert not conf.exists() or not (conf / "settings.xml").exists()
    good = "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40"
    assert _run(base, "--uuid", good) == 0
    assert _uuid_in(conf / "settings.xml") == good

    assert _run(base, "--force-new-identity") == 1, "refuses without --yes"
    assert _uuid_in(conf / "settings.xml") == good

    import contextlib
    import io
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert _run(base, "--force-new-identity", "--yes") == 0
    new = _uuid_in(conf / "settings.xml")
    assert new != good and re.match(UUID4_REGEX, new)
    assert _uuid_in(conf / "network_map.xml") == new
    assert good in out.getvalue() and new in out.getvalue()
    assert "cuems-nodeconf" in out.getvalue()


# -- T037 ------------------------------------------------------------------------


def test_atomic_restore_on_failure(env, monkeypatch):
    conf, state, base = env
    assert _run(base) == 0
    before = {n: (conf / n).read_bytes() for n in DOCUMENTS}

    import os
    real = os.replace
    calls = {"n": 0}

    def failing(src, dst):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disk says no")
        return real(src, dst)

    monkeypatch.setattr(init_node.os, "replace", failing)
    assert _run(base, "--force-new-identity", "--yes") == 1

    assert {n: (conf / n).read_bytes() for n in DOCUMENTS} == before, "the triple must be restored"
    assert not list(conf.glob(".*.tmp")), "temporaries left behind"


# -- T038 ------------------------------------------------------------------------


def test_lock_serialises_and_nodeconf_active_warns(env, tmp_path):
    conf, state, base = env
    results = []

    def worker():
        results.append(_run(base))

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results == [0, 0]
    from cuemsutils.tools.ConfigManager import ConfigManager
    ConfigManager(config_dir=str(conf), load_all=True)

    active = tmp_path / "systemctl-active"
    active.write_text("#!/bin/sh\nexit 0\n")
    active.chmod(0o755)
    base_active = [a if a != "/bin/false" else str(active) for a in base]
    assert _run(base_active) == 1, "nodeconf active without --yes must refuse"
    assert _run(base_active, "--yes") == 0
