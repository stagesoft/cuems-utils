# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture the rc17 fixture with **rc17's own writer** (017 FR-022, research R5).

Run it with ``PYTHONPATH`` pointing at a checkout of ``398a9cf`` (``origin/debian/bookworm``,
``0.1.0rc17``), never at the refactor. What it captures is what rc17 actually writes, so it must
be rc17's ``XmlReaderWriter`` that writes it:

    git worktree add --detach $S/wt-bw 398a9cf
    env -u CUEMS_CONF_PATH PYTHONPATH=$S/wt-bw/src $PY -P \
        specs/017-release-line-reconciliation/tools/capture_rc17_fixture.py \
        --out tests/data/rc17/

It writes two documents:

* ``stop_project.xml``: a VideoCue carrying all four stored media values (``pixel_width`` 1920,
  ``pixel_height`` 1080, ``file_size`` 107374182400, and an **uppercase** md5 that rc15's setter
  lowercases), an AudioCue, and a ``stop_project`` ActionCue with ``action_target=""``;
* ``stop_control.xml``: the same, with the last cue replaced by ``stop`` aimed at the AudioCue.

Ids and timestamps are fixed, so a re-run reproduces the same bytes. Both documents are in the
pre-013 shape (per-class elements, ``True``/``False``, a bare duration, no ``doc_version``), which
is the point: they exercise ``cuems-reshape-devices`` → ``cuems-convert-documents`` → load.
"""
import argparse
import os
import sys

VIDEO_ID = "1b6a4f1e-2c3d-4e5f-8a9b-0c1d2e3f4a50"
AUDIO_ID = "2c7b5a2f-3d4e-4f60-9b0c-1d2e3f4a5b61"
ACTION_ID = "3d8c6b3a-4e5f-4071-8c1d-2e3f4a5b6c72"
MEDIA_V_ID = "4e9d7c4b-5f60-4182-9d2e-3f4a5b6c7d83"
MEDIA_A_ID = "5fae8d5c-6071-4293-8e3f-4a5b6c7d8e94"
CUELIST_ID = "60bf9e6d-7182-43a4-9f4a-5b6c7d8e9fa5"
SCRIPT_ID = "71c0af7e-8293-44b5-8a5b-6c7d8e9fa0b6"
STAMP = "2026-10-15T12:00:00+00:00"
UPPER_MD5 = "D41D8CD98F00B204E9800998ECF8427E"


def build(last_action: str):
    from cuemsutils.cues import ActionCue, AudioCue, CueList, CuemsScript, VideoCue
    from cuemsutils.cues.MediaCue import Media, Region

    def region():
        return [Region({"id": 0, "loop": 1, "in_time": None, "out_time": None})]

    video = VideoCue({
        "Media": Media({
            "file_name": "show.mov", "id": MEDIA_V_ID, "duration": "00:00:10.000",
            "regions": region(), "pixel_width": 1920, "pixel_height": 1080,
            "file_size": 107374182400, "file_md5": UPPER_MD5,
        }),
        "ui_properties": {"warning": None},
    })
    video.id, video.name = VIDEO_ID, "video"
    audio = AudioCue({
        "Media": Media({
            "file_name": "show.wav", "id": MEDIA_A_ID, "duration": "00:00:10.000",
            "regions": region(),
        }),
        "ui_properties": {"warning": None},
    })
    audio.id, audio.name = AUDIO_ID, "audio"
    target = "" if last_action == "stop_project" else AUDIO_ID
    action = ActionCue({
        "action_target": target, "action_type": last_action, "ui_properties": {"warning": 0},
    })
    action.id, action.name = ACTION_ID, last_action
    cuelist = CueList({"contents": [video, audio, action]})
    cuelist.id, cuelist.name = CUELIST_ID, "main"
    script = CuemsScript({"CueList": cuelist})
    script.id, script.name = SCRIPT_ID, "rc17 fixture"
    script.created = STAMP
    script.modified = STAMP
    return script


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="directory to write into")
    args = parser.parse_args()

    import cuemsutils
    from cuemsutils.xml import XmlReaderWriter

    if cuemsutils.__version__ != "0.1.0rc17":
        sys.exit(f"refusing: cuemsutils {cuemsutils.__version__} is not rc17's writer")
    os.makedirs(args.out, exist_ok=True)
    for name, last in (("stop_project.xml", "stop_project"), ("stop_control.xml", "stop")):
        path = os.path.join(args.out, name)
        writer = XmlReaderWriter(schema_name="script", xmlfile=path)
        writer.write_from_object(build(last))
        writer.validate()  # rc17's own T1 check; raises if rc17 would not accept it
        print(f"wrote {path} (cuemsutils {cuemsutils.__version__}, {cuemsutils.__file__})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
