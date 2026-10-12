# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T041 — players carry a class; audiomixer does not (FR-040a, FR-042)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from xmlschema import XMLSchema11

from cuemsutils.errors import SchemaError
from cuemsutils.tools.ConfigManager import ConfigManager
from cuemsutils.xml.settings import Settings

_NS = "https://stagelab.coop/cuems/"
_SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "src" / "cuemsutils" / "xml" / "schemas" / "settings.xsd"
)
_CORPUS = (
    Path(__file__).resolve().parents[1] / "data" / "corpus" / "cuems-utils" / "settings.xml"
)
_OLD = Path(__file__).resolve().parents[1] / "data" / "corpus" / "pre-013" / "settings.xml"


def _document(players: str, mixer: str = "<path>/usr/bin/jack-volume</path><args></args>") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<cms:CuemsSettings xmlns:cms="{_NS}" doc_version="3">
  <Settings>
    <conf_path>/etc/cuems</conf_path>
    <library_path>/opt/cuems_library</library_path>
    <tmp_path>/tmp/cuems</tmp_path>
    <database_name>project-manager.db</database_name>
    <show_lock_file>show.lock</show_lock_file>
    <editor_url>formitgo.local</editor_url>
    <controller_url>controller.local</controller_url>
    <templates_path>/usr/share/cuems</templates_path>
    <controller_interfaces_template>interfaces.controller</controller_interfaces_template>
    <node_interfaces_template>interfaces.node</node_interfaces_template>
    <controller_lock_file>controller.lock</controller_lock_file>
    <node>
      <uuid>00000000-0000-4000-8000-000000000001</uuid>
      <mac>000000000000</mac>
      <osc_dest_host>127.0.0.1</osc_dest_host>
      <oscquery_ws_port>9190</oscquery_ws_port>
      <oscquery_osc_port>9191</oscquery_osc_port>
      <websocket_port>9092</websocket_port>
      <load_timeout>15000</load_timeout>
      <nodeconf_timeout>5000</nodeconf_timeout>
      <discovery_timeout>15000</discovery_timeout>
      <mtc_port>Midi Through Port-0</mtc_port>
      <osc_in_port_base>7000</osc_in_port_base>
      <nng_hub_port>9093</nng_hub_port>
      <gradient_osc_port>7100</gradient_osc_port>
      <players>{players}</players>
      <audiomixer>{mixer}</audiomixer>
    </node>
  </Settings>
</cms:CuemsSettings>
"""


def test_a_reshaped_document_decodes_and_audiomixer_stays_a_sibling():
    schema = XMLSchema11(str(_SCHEMA))
    players = (
        "<player class='video'><path>/usr/bin/video</path><args></args>"
        "<outputs>2</outputs><osc_port>7000</osc_port><output_latency_ms>33</output_latency_ms></player>"
        "<player class='audio'><path>/usr/bin/audio</path><args>-w -1</args>"
        "<output_latency_ms>auto</output_latency_ms></player>"
        "<player class='dmx'><path>/usr/bin/dmx</path><args></args></player>"
    )
    text = _document(players)
    assert schema.is_valid(text)
    root = ET.fromstring(text)
    mixer = root.find(".//{*}audiomixer")
    assert mixer is not None
    parent = next(el for el in root.iter() if mixer in list(el))
    assert parent.tag.endswith("node")
    assert any(child.tag.endswith("players") for child in list(parent))


def test_a_duplicate_player_class_is_rejected():
    schema = XMLSchema11(str(_SCHEMA))
    players = (
        "<player class='video'><path>/v</path><args></args><outputs>1</outputs></player>"
        "<player class='video'><path>/v2</path><args></args><outputs>1</outputs></player>"
    )
    assert schema.is_valid(_document(players)) is False


def test_legacy_player_keys_keep_the_nested_values(tmp_path, monkeypatch):
    conf = tmp_path / "conf"
    conf.mkdir()
    (conf / "settings.xml").write_bytes(_CORPUS.read_bytes())
    for name in ("network_map.xml", "project_mappings.xml"):
        source = _CORPUS.parents[0] / name
        if source.exists():
            (conf / name).write_bytes(source.read_bytes())
    monkeypatch.setenv("CUEMS_CONF_PATH", str(conf))
    node = ConfigManager(config_dir=str(conf), load_all=False).node_conf
    video = node["videoplayer"]
    assert video["path"] == "/usr/bin/xjadeo"
    assert video["output_latency_ms"] == "33" or video["output_latency_ms"] == 33
    audio = node["audioplayer"]
    assert audio["path"] == "/usr/local/bin/cuems-audioplayer"
    assert audio["args"] == "-w -1"
    assert audio["output_latency_ms"] == "auto"
    dmx = node["dmxplayer"]
    assert dmx["path"] == "/usr/bin/cuems-dmxplayer"
    assert dmx["args"] == "--mtcfollow"
    assert node["audiomixer"]["path"] == "/usr/local/bin/jack-volume"
    assert type(node["audiomixer"]).__name__ == "AudioMixerType"


def test_an_old_settings_document_names_the_tool():
    with pytest.raises(SchemaError) as excinfo:
        Settings(str(_OLD))
    assert str(excinfo.value) == (
        f"settings document {_OLD} is in the pre-013 device shape "
        "(<videoplayer>/<audioplayer>/<dmxplayer> on <node>). "
        "Run `cuems-reshape-devices` to migrate it."
    )
