"""Unit tests for MediaCue fade profiles and FadeProfile model."""

import pytest

from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.cues.CueOutput import AudioCueOutput
from cuemsutils.cues.FadeProfile import FadeFunctionParameter, FadeProfile
from cuemsutils.cues.MediaCue import Media, Region


def _minimal_audio_cue():
    return AudioCue(
        {
            'master_vol': 66,
            'Media': Media(
                {
                    'file_name': 'f.wav',
                    'id': '',
                    'duration': '00:00:01.000',
                    'regions': [
                        Region(
                            {
                                'id': 0,
                                'loop': 1,
                                'in_time': None,
                                'out_time': None,
                            }
                        )
                    ],
                }
            ),
            'outputs': [
                AudioCueOutput(
                    {
                        'output_name': (
                            '0367f391-ebf4-48b2-9f26-000000000001_system:playback_1'
                        ),
                        'output_vol': 80,
                        'channels': [
                            {
                                'channel': {
                                    'channel_num': 0,
                                    'channel_vol': 80,
                                }
                            }
                        ],
                    }
                )
            ],
        }
    )


def test_single_preset_fade_profile():
    ac = _minimal_audio_cue()
    ac.fade_profiles = [
        FadeProfile(
            {
                'type': 'in',
                'mode': 'preset',
                'function_id': 'linear_in_out',
                'parameters': None,
            }
        )
    ]
    assert len(ac.fade_profiles) == 1
    assert ac.fade_profiles[0].type == 'in'
    assert ac.fade_profiles[0].mode == 'preset'


def test_two_typed_fade_profiles():
    ac = _minimal_audio_cue()
    ac.fade_profiles = [
        FadeProfile(
            {
                'type': 'in',
                'mode': 'preset',
                'function_id': 'a',
                'parameters': None,
            }
        ),
        FadeProfile(
            {
                'type': 'out',
                'mode': 'parametric',
                'function_id': 'bezier',
                'parameters': [
                    FadeFunctionParameter(
                        {'parameter_name': 'p1', 'parameter_value': 0.25}
                    )
                ],
            }
        ),
    ]
    assert len(ac.fade_profiles) == 2


def test_rejects_duplicate_type():
    ac = _minimal_audio_cue()
    with pytest.raises(ValueError, match='Duplicate fade profile'):
        ac.fade_profiles = [
            FadeProfile(
                {
                    'type': 'in',
                    'mode': 'preset',
                    'function_id': 'a',
                    'parameters': None,
                }
            ),
            FadeProfile(
                {
                    'type': 'in',
                    'mode': 'preset',
                    'function_id': 'b',
                    'parameters': None,
                }
            ),
        ]


def test_preset_allows_empty_params_parametric_requires():
    ac = _minimal_audio_cue()
    ac.fade_profiles = [
        FadeProfile(
            {
                'type': 'in',
                'mode': 'preset',
                'function_id': 'x',
                'parameters': None,
            }
        )
    ]
    with pytest.raises(ValueError, match='parametric fade profile requires'):
        ac.fade_profiles = [
            FadeProfile(
                {
                    'type': 'out',
                    'mode': 'parametric',
                    'function_id': 'bezier',
                    'parameters': None,
                }
            )
        ]


def test_get_fade_profile_by_direction():
    ac = _minimal_audio_cue()
    ac.fade_profiles = [
        FadeProfile(
            {
                'type': 'in',
                'mode': 'preset',
                'function_id': 'in_fn',
                'parameters': None,
            }
        ),
        FadeProfile(
            {
                'type': 'out',
                'mode': 'preset',
                'function_id': 'out_fn',
                'parameters': None,
            }
        ),
    ]
    assert ac.get_fade_profile('in').function_id == 'in_fn'
    assert ac.get_fade_profile('fade_in').function_id == 'in_fn'
    assert ac.get_fade_profile('out').function_id == 'out_fn'
    assert ac.get_fade_profile('fade_out').function_id == 'out_fn'


def test_fade_function_parameter_rejects_non_numeric():
    with pytest.raises(ValueError, match='numeric'):
        FadeFunctionParameter({'parameter_name': 'p', 'parameter_value': 'nope'})


def test_fade_function_parameter_rejects_duplicate_names_in_profile():
    with pytest.raises(ValueError, match='Duplicate parameter_name'):
        FadeProfile(
            {
                'type': 'in',
                'mode': 'parametric',
                'function_id': 'f',
                'parameters': [
                    {'parameter_name': 'p', 'parameter_value': 1.0},
                    {'parameter_name': 'p', 'parameter_value': 2.0},
                ],
            }
        )
