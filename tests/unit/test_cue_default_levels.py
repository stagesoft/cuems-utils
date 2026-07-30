"""Tests for AudioCue.master_vol and VideoCue.opacity default/stored values.

master_vol's REQ_ITEMS default was previously `1` with a stale comment
claiming "full volume (0.0-1.0 range)" while every consumer (run_cue.py,
cuems-engine's ActionHandler) treats it as a 0-100 percent scale — meaning
an AudioCue built without an explicit master_vol silently defaulted to 1%
volume instead of full volume. Fixed to `100`. opacity is a new field on
VideoCue, added to mirror master_vol so fade actions on video cues have a
stored starting level to read (previously there was none at all).
"""
from cuemsutils.cues import AudioCue, VideoCue


def test_audio_cue_master_vol_defaults_to_100():
    cue = AudioCue({'loop': True, 'media': 'file.ext'})
    assert cue.master_vol == 100


def test_audio_cue_master_vol_stores_explicit_value():
    cue = AudioCue({'loop': True, 'media': 'file.ext', 'master_vol': 60})
    assert cue.master_vol == 60


def test_video_cue_opacity_defaults_to_100():
    cue = VideoCue({'loop': True, 'media': 'file.ext'})
    assert cue.opacity == 100


def test_video_cue_opacity_stores_explicit_value():
    cue = VideoCue({'loop': True, 'media': 'file.ext', 'opacity': 60})
    assert cue.opacity == 60


def test_video_cue_opacity_present_in_items():
    """items() must surface opacity so XmlBuilder can serialize it (mirrors
    master_vol's items() override in AudioCue)."""
    cue = VideoCue({'loop': True, 'media': 'file.ext', 'opacity': 60})
    assert dict(cue.items())['opacity'] == 60
