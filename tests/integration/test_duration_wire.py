"""``Media.duration`` on the wire, both forms (T008) — FR-003.

XML gets the same wrapped shape every other ``CTimecodeType`` field emits;
JSON gets the same ``{"CTimecode": "..."}`` projection ``FadeCue.duration``
already produced. Exercised end to end — build, write, read back, project —
rather than at any single layer, since FR-003's claim is about what a
consumer on either side of the wire actually sees.
"""

from __future__ import annotations

from cuemsutils.cues import AudioCue, CueList, CuemsScript
from cuemsutils.cues.MediaCue import Media, Region


def _script_with_media_duration():
    return CuemsScript({
        'CueList': CueList({'contents': [
            AudioCue({
                'master_vol': 66,
                'Media': Media({
                    'file_name': 'file.ext', 'id': '', 'duration': '00:00:12.500',
                    'regions': [Region({'id': 0, 'loop': 1,
                                        'in_time': None, 'out_time': None})],
                }),
            }),
        ]}),
        'ui_properties': {'icon': 'icon.png', 'color': '#000000'},
    })


def test_xml_emits_the_wrapped_duration_element(tmp_path):
    script = _script_with_media_duration()
    target = tmp_path / 'media_duration.xml'
    script.save(target)

    written = target.read_text(encoding='utf-8')
    assert '<duration><CTimecode>00:00:12.500</CTimecode></duration>' in written


def test_json_projects_media_duration_as_ctimecode_wrapper():
    script = _script_with_media_duration()
    media = script.cuelist.contents[0].to_wire()['Media']
    assert media['duration'] == {'CTimecode': '00:00:12.500'}


def test_the_written_document_round_trips_through_load():
    script = _script_with_media_duration()
    duration = script.cuelist.contents[0].media.duration

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / 'roundtrip.xml'
        script.save(target)
        reloaded = CuemsScript.load(target)

    assert reloaded.cuelist.contents[0].media.duration == duration
