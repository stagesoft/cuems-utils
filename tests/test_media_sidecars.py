# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>

"""``cuemsutils.tools.media_sidecars``: the loop period rule, the ``.period``
sidecar and the ``.idx`` caller (plan 869ejxng3 + 1amfwm7e6cw rev 3.14, §4.1).

Two groups:

* unit tests with a fake ffprobe (no media needed);
* the rule on real files: the step-0 fixtures, whose decoded lengths and frame
  counts were measured by the step-0 gate (decoder output == ffprobe sum, on
  .111) and the frame-count agreement probe. Point ``CUEMS_STEP0_FIXTURES`` at a
  directory holding ``gate/fixtures/manifest.tsv`` (+ the files) and
  ``framecount/media/``; the group is skipped without it.
"""

import csv
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

from cuemsutils.tools import media_sidecars as ms

# --------------------------------------------------------------------------- fakes

def _probe_json(fmt, streams):
    return json.dumps({'format': {'format_name': fmt}, 'streams': streams})


class FakeFFprobe:
    """Answers the three ffprobe calls of loop_period from canned data."""

    def __init__(self, fmt, streams, frames=None, packets=None, delay=0.0):
        self.fmt, self.streams = fmt, streams
        self.frames, self.packets, self.delay = frames or [], packets or [], delay
        self.calls = []

    def __call__(self, args, deadline):
        self.calls.append(args)
        if self.delay:
            deadline.left()  # raises PeriodTimeout once exhausted
        if args[:2] == ['ffprobe', '-version']:
            return 'ffprobe version 5.1.fake Copyright x\n'
        if 'format=format_name' in ' '.join(args):
            return _probe_json(self.fmt, self.streams)
        if '-show_frames' in args:
            return '\n'.join(str(n) for n in self.frames) + '\n'
        if 'packet=flags' in args:
            return '\n'.join(self.packets) + '\n'
        raise AssertionError(args)


@pytest.fixture
def media(tmp_path):
    p = tmp_path / 'clip.mov'
    p.write_bytes(b'x' * 1000)
    return p


def _audio(idx=0, codec='aac', rate=48000, dts='N/A', tb='1/48000'):
    return {'index': idx, 'codec_type': 'audio', 'codec_name': codec, 'sample_rate': str(rate),
            'duration_ts': dts, 'time_base': tb}


def _video(idx=0, dur='4.000000', r='25/1', avg='25/1', attached=0):
    return {'index': idx, 'codec_type': 'video', 'codec_name': 'h264', 'duration': dur,
            'r_frame_rate': r, 'avg_frame_rate': avg, 'disposition': {'attached_pic': attached}}


# --------------------------------------------------------------------------- the rule (fake ffprobe)

@pytest.mark.parametrize('fmt,codec,trusted', [
    ('wav', 'pcm_s16le', True),
    ('flac', 'flac', True),
    ('mov,mp4,m4a,3gp,3g2,mj2', 'pcm_s24le', True),
    ('mov,mp4,m4a,3gp,3g2,mj2', 'alac', True),
    ('mov,mp4,m4a,3gp,3g2,mj2', 'aac', False),
    ('mp3', 'mp3', False),
    ('avi', 'pcm_s16le', False),          # AVI headers lie (step 0: 70 ms)
    ('matroska,webm', 'pcm_s16le', False),
    ('ogg', 'opus', False),
])
def test_header_trusted_only_where_proven(fmt, codec, trusted):
    assert ms._header_trusted(fmt, codec) is trusted


def test_header_rule_for_wav(monkeypatch, media):
    fake = FakeFFprobe('wav', [_audio(codec='pcm_s16le', dts='576000')])
    monkeypatch.setattr(ms, '_run', fake)
    p = ms.loop_period(str(media))
    assert (p.num, p.den, p.rate, p.rule, p.real_frames) == (576000, 48000, 48000, 'header', None)
    assert not any('-show_frames' in c for c in fake.calls)


def test_walk_for_aac_in_mp4_sums_the_decoded_frames(monkeypatch, media):
    fake = FakeFFprobe('mov,mp4,m4a,3gp,3g2,mj2', [_video(), _audio(idx=1, dts='576000')],
                       frames=[1024] * 562 + [1024, 512])
    monkeypatch.setattr(ms, '_run', fake)
    p = ms.loop_period(str(media))
    assert (p.num, p.den, p.rule) == (1024 * 563 + 512, 48000, 'walk')
    assert p.real_frames == 100 and p.frames_rule == 'stream' and p.fps == '25/1'
    walk = next(c for c in fake.calls if '-show_frames' in c)
    assert walk[walk.index('-select_streams') + 1] == '1'   # the audio stream's own index


def test_header_with_another_time_base_walks(monkeypatch, media):
    fake = FakeFFprobe('wav', [_audio(codec='pcm_s16le', dts='12000', tb='1/1000')], frames=[576000])
    monkeypatch.setattr(ms, '_run', fake)
    assert ms.loop_period(str(media)).rule == 'walk'


def test_video_only_period_from_frames(monkeypatch, media):
    fake = FakeFFprobe('mov,mp4,m4a,3gp,3g2,mj2', [_video(dur='10.400000', r='25/1')])
    monkeypatch.setattr(ms, '_run', fake)
    p = ms.loop_period(str(media))
    assert (p.real_frames, p.num, p.den, p.rate, p.rule) == (260, 260, 25, None, 'stream')


def test_video_only_ntsc_rate(monkeypatch, media):
    fake = FakeFFprobe('mov', [_video(dur='19.986633', r='30000/1001', avg='30000/1001')])
    monkeypatch.setattr(ms, '_run', fake)
    p = ms.loop_period(str(media))
    assert p.real_frames == 599 and (p.num, p.den) == (599 * 1001, 30000)


def test_no_stream_duration_counts_packets_without_discard(monkeypatch, media):
    fake = FakeFFprobe('matroska,webm', [_video(dur='N/A')],
                       packets=['K__', 'D__', '___', 'KD_', '___'])
    monkeypatch.setattr(ms, '_run', fake)
    p = ms.loop_period(str(media))
    assert p.real_frames == 3 and p.frames_rule == 'packets'


def test_attached_picture_is_not_the_video(monkeypatch, media):
    fake = FakeFFprobe('mp3', [_video(attached=1), _audio(idx=1, codec='mp3')], frames=[1152] * 10)
    monkeypatch.setattr(ms, '_run', fake)
    p = ms.loop_period(str(media))
    assert p.real_frames is None and p.num == 11520


def test_vfr_is_flagged(monkeypatch, media):
    fake = FakeFFprobe('mov', [_video(r='30/1', avg='29/1')])
    monkeypatch.setattr(ms, '_run', fake)
    assert ms.loop_period(str(media)).vfr is True


def test_no_usable_stream_raises(monkeypatch, media):
    monkeypatch.setattr(ms, '_run', FakeFFprobe('image2', []))
    with pytest.raises(ms.PeriodError):
        ms.loop_period(str(media))


def test_missing_file_raises(tmp_path):
    with pytest.raises(ms.PeriodError):
        ms.loop_period(str(tmp_path / 'nope.wav'))


def test_budget_exhausted_raises_timeout(monkeypatch, media):
    real_left = ms._Deadline.left

    def slow_left(self):
        if self.end is not None:
            self.end -= 100  # the budget is gone after the first call
        return real_left(self)
    monkeypatch.setattr(ms._Deadline, 'left', slow_left)
    monkeypatch.setattr(ms, '_run', FakeFFprobe('mp3', [_audio(codec='mp3')], frames=[1152], delay=1))
    with pytest.raises(ms.PeriodTimeout):
        ms.loop_period(str(media), budget_s=5)


def test_real_subprocess_timeout_maps_to_period_timeout(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired('ffprobe', 1)
    monkeypatch.setattr(ms.subprocess, 'run', boom)
    with pytest.raises(ms.PeriodTimeout):
        ms._run(['ffprobe', 'x'], ms._Deadline(1))


def test_ffprobe_missing_is_a_period_error(monkeypatch):
    def nf(*a, **k):
        raise FileNotFoundError('ffprobe')
    monkeypatch.setattr(ms.subprocess, 'run', nf)
    with pytest.raises(ms.PeriodError):
        ms._run(['ffprobe', 'x'], ms._Deadline(None))


# --------------------------------------------------------------------------- the sidecar

def _period(media, **kw):
    st = os.stat(media)
    d = dict(num=576512, den=48000, rate=48000, real_frames=300, fps='25/1', rule='walk',
             frames_rule='stream', vfr=False, size=st.st_size, mtime=int(st.st_mtime),
             ffprobe='ffprobe version 5.1.fake', probe_s=0.3)
    d.update(kw)
    return ms.Period(**d)


def test_sidecar_round_trip_next_to_the_idx(media):
    p = _period(media)
    sp = ms.write_period(str(media), p)
    assert sp == str(media.parent / 'indexes' / 'clip.mov.period')
    assert ms.sidecar_path(str(media), ms.INDEX_EXT) == str(media.parent / 'indexes' / 'clip.mov.idx')
    assert ms.read_period(str(media)) == p
    d = json.loads(Path(sp).read_text())
    assert d['v'] == 1 and d['realFrames'] == 300 and 'real_frames' not in d
    assert stat.S_IMODE(os.stat(sp).st_mode) == 0o644
    assert [f.name for f in (media.parent / 'indexes').iterdir()] == ['clip.mov.period']


def test_missing_sidecar_is_none(media):
    assert ms.read_period(str(media)) is None


def test_stale_size_or_mtime_is_none(media):
    ms.write_period(str(media), _period(media))
    st = os.stat(media)
    os.utime(media, (st.st_atime, st.st_mtime + 5))
    assert ms.read_period(str(media)) is None
    ms.write_period(str(media), _period(media))
    assert ms.read_period(str(media)) is not None
    with open(media, 'ab') as f:
        f.write(b'more')
    os.utime(media, (st.st_atime, int(os.stat(media).st_mtime)))
    assert ms.read_period(str(media)) is None


@pytest.mark.parametrize('text', ['{', '{"v": 2}', '[]', '{"v": 1, "num": 0}',
                                  '{"v": 1, "realFrames": null, "num": -1, "den": 48000}'])
def test_corrupt_sidecar_is_none(media, text):
    sp = Path(ms.sidecar_path(str(media)))
    sp.parent.mkdir()
    sp.write_text(text)
    assert ms.read_period(str(media)) is None


def test_failed_write_leaves_no_temp_file(media, monkeypatch):
    def fail(*a):
        raise OSError('disk full')
    monkeypatch.setattr(ms.os, 'replace', fail)
    with pytest.raises(OSError):
        ms.write_period(str(media), _period(media))
    assert list((media.parent / 'indexes').iterdir()) == []


# --------------------------------------------------------------------------- the .idx caller

def _fake_indexer(bindir, body):
    p = bindir / 'cuems-videoindexer'
    p.write_text('#!/bin/sh\n' + body)
    p.chmod(0o755)


def test_ensure_video_index_runs_only_the_missing(tmp_path, monkeypatch):
    (tmp_path / 'indexes').mkdir()
    a, b = tmp_path / 'a.mp4', tmp_path / 'b.mp4'
    a.write_bytes(b'a'), b.write_bytes(b'b')
    (tmp_path / 'indexes' / 'a.mp4.idx').write_bytes(b'i')
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    _fake_indexer(bindir, 'for f in "$@"; do echo "$f" >> "%s/args"; '
                          'touch "$(dirname "$f")/indexes/$(basename "$f").idx"; done\n' % tmp_path)
    monkeypatch.setenv('PATH', f'{bindir}:{os.environ["PATH"]}')
    assert ms.ensure_video_index([str(a), str(b)]) == []
    assert (tmp_path / 'args').read_text().split() == [str(b)]
    assert ms.ensure_video_index(str(b)) == []            # a no-op now


def test_ensure_video_index_reports_failures_and_never_raises(tmp_path, monkeypatch):
    v = tmp_path / 'v.mkv'
    v.write_bytes(b'v')
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    _fake_indexer(bindir, 'echo broken; exit 3\n')
    monkeypatch.setenv('PATH', f'{bindir}:{os.environ["PATH"]}')
    assert ms.ensure_video_index(str(v)) == [str(v)]
    monkeypatch.setenv('PATH', str(tmp_path / 'empty'))   # no indexer at all
    assert ms.ensure_video_index(str(v)) == [str(v)]


# --------------------------------------------------------------------------- the console script

def test_cli_prints_and_backfills(tmp_path, monkeypatch, capsys):
    for n in ('a.wav', 'b.mp4', 'c.png', 'd.txt'):
        (tmp_path / n).write_bytes(b'z')
    seen = []

    def fake_lp(path, budget_s=None):
        seen.append(os.path.basename(path))
        st = os.stat(path)
        return ms.Period(num=48000, den=48000, rate=48000, real_frames=None, fps=None, rule='header',
                         frames_rule=None, vfr=False, size=st.st_size, mtime=int(st.st_mtime),
                         ffprobe='fake')
    monkeypatch.setattr(ms, 'loop_period', fake_lp)
    monkeypatch.setattr(ms, '_low_priority', lambda: None)
    assert ms.main([str(tmp_path / 'a.wav')]) == 0
    assert '"num": 48000' in capsys.readouterr().out
    assert not (tmp_path / 'indexes').exists()             # printing never writes
    seen.clear()
    assert ms.main(['--backfill', str(tmp_path)]) == 0
    assert sorted(seen) == ['a.wav', 'b.mp4']              # MOVIE/AUDIO only
    assert sorted(os.listdir(tmp_path / 'indexes')) == ['a.wav.period', 'b.mp4.period']
    seen.clear()
    assert ms.main(['--backfill', str(tmp_path)]) == 0     # idempotent
    assert seen == [] and 'backfill' in capsys.readouterr().out


def test_cli_without_arguments_is_usage():
    assert ms.main([]) == 2


# --------------------------------------------------------------------------- the rule on real files

FIX = os.environ.get('CUEMS_STEP0_FIXTURES')
needs_fixtures = pytest.mark.skipif(not FIX or not os.path.isdir(FIX or ''),
                                    reason='CUEMS_STEP0_FIXTURES not set (the step-0 kit)')


def _manifest():
    if not FIX:
        return []
    m = Path(FIX) / 'gate' / 'fixtures' / 'manifest.tsv'
    return list(csv.DictReader(open(m), delimiter='\t')) if m.exists() else []


@needs_fixtures
@pytest.mark.parametrize('row', _manifest(), ids=lambda r: r['name'])
def test_period_equals_the_decoded_length(row):
    p = ms.loop_period(str(Path(FIX) / 'gate' / 'fixtures' / row['name']))
    assert p.num == int(row['ffprobe_sum'])
    assert p.den == int(row['rate'])
    assert (p.rule == 'header') == (row['header_used'] == '1')


@needs_fixtures
@pytest.mark.parametrize('name,frames,rule', [
    ('src4s.mp4', 100, 'stream'),
    ('cut.mp4', 87, 'stream'),         # stream-copy trim: nb_frames/packets say 100
    ('hap.mov', 260, 'stream'),
    ('av.mkv', 260, 'packets'),        # no stream duration in an ffmpeg-written mkv
    ('cut.mkv', 100, 'packets'),
])
def test_real_frames_equal_the_decoded_count(name, frames, rule):
    p = ms.loop_period(str(Path(FIX) / 'framecount' / 'media' / name))
    assert (p.real_frames, p.frames_rule) == (frames, rule)


@needs_fixtures
def test_real_sidecar_round_trip_on_a_fixture(tmp_path):
    src = Path(FIX) / 'gate' / 'fixtures' / 'av.mp4'
    dst = tmp_path / 'av.mp4'
    dst.write_bytes(src.read_bytes())
    p = ms.loop_period(str(dst))
    ms.write_period(str(dst), p)
    assert ms.read_period(str(dst)) == p
