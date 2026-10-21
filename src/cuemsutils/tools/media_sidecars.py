# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>

"""Media sidecars: the loop period of a media file and its ``.idx`` video index.

One implementation, used in-process by the editor (at upload, next to the
``.idx``) and by the engine (the fallback for a file without a valid
sidecar), plus the ``cuems-loop-period`` console script for operators
(plan 869ejxng3 + 1amfwm7e6cw rev 3.14, section 4.1, D14).

**The loop period P** of a file is a rational ``num / den`` seconds:

* if the file has an audio stream: ``num`` = the number of samples libavcodec
  delivers for the first audio stream (priming trimmed, end padding included),
  ``den`` = its sample rate. The header (``duration_ts`` with a ``1/rate``
  time base) is trusted only for WAV, FLAC and lossless audio (PCM, ALAC) in
  mov/mp4; every other file walks the decoded frames (``nb_samples`` summed);
* else: ``num = frames * fps_den``, ``den = fps_num``.

``real_frames`` is the video frame count both ends use (section 4.1):
``round(video stream duration * r_frame_rate)``; where the stream has no
duration (every ffmpeg-written mkv) the video packets without the discard
flag are counted. Never ``nb_frames`` or a raw packet count alone: both
overcount stream-copy trims.

**The sidecar** is ``<media dir>/indexes/<name>.period`` (JSON), next to the
``.idx``, written atomically. It is valid only while the media file's size
and mtime (whole seconds: rsync ``-t`` keeps them across hosts) match.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import Iterable, Optional

from ..log import Logger

SIDECAR_VERSION = 1
SIDECAR_EXT = ".period"
INDEX_EXT = ".idx"
INDEX_DIR = "indexes"
DEFAULT_MEDIA_DIR = "/opt/cuems_library/media"

#: Extensions handled as MOVIE / AUDIO (the editor's ``get_type`` lists).
MOVIE_EXTS = ('.mov', '.avi', '.mkv', '.mpg', '.mp4', '.webm', '.m4v', '.flv', '.wmv', '.ogv', '.3gp')
AUDIO_EXTS = ('.aif', '.aiff', '.wav', '.mp3', '.m4a', '.ogg', '.oga', '.flac', '.aac', '.wma', '.opus', '.weba')

#: Containers and codecs whose header length is the decoded length (step 0, section 1).
_HEADER_FORMATS = {'wav', 'flac'}
_MOV_FORMATS = {'mov', 'mp4', 'm4a'}


class PeriodError(Exception):
    """The period could not be computed (ffprobe missing, failed, no usable stream)."""


class PeriodTimeout(PeriodError, TimeoutError):
    """The period's ffprobe calls did not finish within the budget."""


@dataclass(frozen=True)
class Period:
    """A media file's loop period, ``num / den`` seconds, and its video frame count."""

    num: int
    den: int
    rate: Optional[int]          # audio sample rate (= den) or None for a video-only file
    real_frames: Optional[int]   # video frames (realFrames) or None without video
    fps: Optional[str]           # r_frame_rate as "num/den", or None
    rule: str                    # header | walk (audio), stream | packets (video-only)
    frames_rule: Optional[str]   # stream | packets, or None without video
    vfr: bool                    # avg_frame_rate != r_frame_rate (outside the guarantee)
    size: int                    # the media file's size in bytes
    mtime: int                   # the media file's mtime, whole seconds
    ffprobe: str                 # ffprobe's version string
    probe_s: float = 0.0         # time taken

    @property
    def ms(self) -> float:
        return self.num * 1000.0 / self.den

    def to_json(self) -> str:
        d = asdict(self)
        d['v'] = SIDECAR_VERSION
        d['realFrames'] = d.pop('real_frames')
        return json.dumps(d, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> 'Period':
        d = json.loads(text)
        if d.pop('v', None) != SIDECAR_VERSION:
            raise ValueError('unknown sidecar version')
        d['real_frames'] = d.pop('realFrames')
        p = cls(**d)
        if not (isinstance(p.num, int) and isinstance(p.den, int) and p.num > 0 and p.den > 0):
            raise ValueError('bad period')
        return p


# --------------------------------------------------------------------------- ffprobe

class _Deadline:
    def __init__(self, budget_s: Optional[float]):
        self.end = None if budget_s is None else time.monotonic() + budget_s

    def left(self) -> Optional[float]:
        if self.end is None:
            return None
        left = self.end - time.monotonic()
        if left <= 0:
            raise PeriodTimeout('budget exhausted')
        return left


def _run(args: list, deadline: _Deadline) -> str:
    """Run ffprobe; stdout as text. Raises PeriodError / PeriodTimeout."""
    try:
        r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=deadline.left(), text=True)
    except subprocess.TimeoutExpired as e:
        raise PeriodTimeout(f'{args[0]} timed out') from e
    except FileNotFoundError as e:
        raise PeriodError(f'{args[0]} not found') from e
    if r.returncode != 0:
        raise PeriodError(f'{args[0]} failed (rc={r.returncode}): {r.stderr.strip()[:200]}')
    return r.stdout


_FFPROBE_VERSION = None


def ffprobe_version() -> str:
    global _FFPROBE_VERSION
    if _FFPROBE_VERSION is None:
        try:
            out = _run(['ffprobe', '-version'], _Deadline(10))
            _FFPROBE_VERSION = out.split('\n', 1)[0].split(' Copyright', 1)[0].strip()
        except PeriodError:
            _FFPROBE_VERSION = 'unknown'
    return _FFPROBE_VERSION


def _streams(path: str, deadline: _Deadline) -> dict:
    out = _run(['ffprobe', '-v', 'error', '-show_entries',
                'format=format_name:stream=index,codec_type,codec_name,sample_rate,'
                'duration_ts,time_base,duration,r_frame_rate,avg_frame_rate:'
                'stream_disposition=attached_pic',
                '-of', 'json', path], deadline)
    try:
        return json.loads(out)
    except ValueError as e:
        raise PeriodError(f'ffprobe output not JSON for {path}') from e


def _header_trusted(fmt: str, codec: str) -> bool:
    names = set(fmt.split(','))
    if names & _HEADER_FORMATS:
        return True
    return bool(names & _MOV_FORMATS) and (codec.startswith('pcm_') or codec == 'alac')


def _audio_samples(path: str, st: dict, fmt: str, deadline: _Deadline):
    rate = int(st['sample_rate'])
    codec = st.get('codec_name', '')
    dts, tb = st.get('duration_ts'), st.get('time_base')
    if _header_trusted(fmt, codec) and dts not in (None, 'N/A') and tb and Fraction(tb) == Fraction(1, rate):
        return int(dts), rate, 'header'
    out = _run(['ffprobe', '-v', 'error', '-select_streams', str(st['index']), '-show_frames',
                '-show_entries', 'frame=nb_samples', '-of', 'csv=p=0', path], deadline)
    n = 0
    for line in out.split():
        line = line.strip().rstrip(',')
        if line:
            n += int(line)
    if n <= 0:
        raise PeriodError(f'no decoded audio samples in {path}')
    return n, rate, 'walk'


def _video_frames(path: str, st: dict, deadline: _Deadline):
    r = st.get('r_frame_rate') or '0/0'
    fps = Fraction(r) if r != '0/0' else None
    if not fps:
        raise PeriodError(f'no frame rate for the video stream of {path}')
    avg = st.get('avg_frame_rate') or '0/0'
    vfr = avg not in ('0/0', r) and Fraction(avg) != fps
    dur = st.get('duration')
    if dur not in (None, 'N/A'):
        return round(Fraction(dur) * fps), fps, 'stream', vfr
    out = _run(['ffprobe', '-v', 'error', '-select_streams', str(st['index']),
                '-show_entries', 'packet=flags', '-of', 'csv=p=0', path], deadline)
    n = sum(1 for line in out.split() if line.strip() and 'D' not in line)
    return n, fps, 'packets', vfr


def loop_period(path: str, budget_s: Optional[float] = None) -> Period:
    """Compute the loop period of *path* (section 4.1).

    *budget_s* bounds the total time of the ffprobe calls (``None``: no bound);
    raises ``PeriodTimeout`` when exceeded, ``PeriodError`` on any failure.
    """
    t0 = time.monotonic()
    deadline = _Deadline(budget_s)
    try:
        st = os.stat(path)
    except OSError as e:
        raise PeriodError(f'cannot stat {path}: {e}') from e
    info = _streams(path, deadline)
    fmt = info.get('format', {}).get('format_name', '')
    streams = info.get('streams', [])
    audio = next((s for s in streams if s.get('codec_type') == 'audio' and s.get('sample_rate')), None)
    video = next((s for s in streams if s.get('codec_type') == 'video'
                  and not s.get('disposition', {}).get('attached_pic')), None)
    frames = fps = frames_rule = None
    vfr = False
    if video is not None:
        frames, fps, frames_rule, vfr = _video_frames(path, video, deadline)
    if audio is not None:
        num, rate, rule = _audio_samples(path, audio, fmt, deadline)
        den = rate
    elif video is not None and frames:
        num, den, rate, rule = frames * fps.denominator, fps.numerator, None, frames_rule
    else:
        raise PeriodError(f'no audio or video stream in {path}')
    return Period(num=num, den=den, rate=rate, real_frames=frames,
                  fps=None if fps is None else f'{fps.numerator}/{fps.denominator}',
                  rule=rule, frames_rule=frames_rule, vfr=vfr,
                  size=st.st_size, mtime=int(st.st_mtime), ffprobe=ffprobe_version(),
                  probe_s=round(time.monotonic() - t0, 3))


# --------------------------------------------------------------------------- sidecar

def sidecar_path(media_path: str, ext: str = SIDECAR_EXT) -> str:
    """``<dir>/indexes/<name><ext>`` (the ``.idx`` scheme of ``VideoFileInput``)."""
    return os.path.join(os.path.dirname(media_path), INDEX_DIR, os.path.basename(media_path) + ext)


def read_period(media_path: str) -> Optional[Period]:
    """The sidecar's period, or ``None`` when it is missing, corrupt or stale."""
    sp = sidecar_path(media_path)
    try:
        with open(sp) as f:
            text = f.read()
    except FileNotFoundError:
        return None
    except OSError as e:
        Logger.warning(f'loop period sidecar {sp} unreadable: {e}')
        return None
    try:
        p = Period.from_json(text)
    except (ValueError, TypeError, KeyError) as e:
        Logger.warning(f'loop period sidecar {sp} corrupt ({e}); ignored')
        return None
    try:
        st = os.stat(media_path)
    except OSError:
        return None
    if p.size != st.st_size or p.mtime != int(st.st_mtime):
        Logger.debug(f'loop period sidecar {sp} stale (size/mtime changed); ignored')
        return None
    return p


def write_period(media_path: str, period: Period) -> str:
    """Write the sidecar atomically (temp file + rename); returns its path."""
    sp = sidecar_path(media_path)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(sp), prefix='.' + os.path.basename(sp) + '.')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(period.to_json() + '\n')
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, sp)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return sp


# --------------------------------------------------------------------------- .idx

def ensure_video_index(paths, timeout_s: float = 600) -> list:
    """Run ``cuems-videoindexer`` on every path of *paths* (one path or several) that
    has no ``indexes/<name>.idx`` yet; returns the paths still without one.

    Never raises: a missing indexer, a timeout or a failure is a WARNING.
    """
    if isinstance(paths, str):
        paths = [paths]
    todo = [p for p in paths if not os.path.exists(sidecar_path(p, INDEX_EXT))]
    if not todo:
        return []
    Logger.info(f'video index: indexing {len(todo)} file(s) without .idx: '
                f'{[os.path.basename(p) for p in todo]}')
    try:
        r = subprocess.run(['cuems-videoindexer'] + todo, timeout=timeout_s,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if r.returncode != 0:
            Logger.warning(f'video index: cuems-videoindexer rc={r.returncode}: {r.stdout.strip()[-400:]!r}')
    except Exception as e:  # FileNotFoundError, TimeoutExpired, ...
        Logger.warning(f'video index: cuems-videoindexer failed: {e}')
    missing = [p for p in todo if not os.path.exists(sidecar_path(p, INDEX_EXT))]
    for p in missing:
        Logger.warning(f'video index not created for {os.path.basename(p)}')
    return missing


# --------------------------------------------------------------------------- CLI

def _media_files(media_dir: str) -> Iterable[str]:
    for name in sorted(os.listdir(media_dir)):
        p = os.path.join(media_dir, name)
        if os.path.isfile(p) and os.path.splitext(name)[1].lower() in MOVIE_EXTS + AUDIO_EXTS:
            yield p


def _low_priority():
    try:
        os.nice(10)
    except OSError:
        pass
    try:
        subprocess.run(['ionice', '-c3', '-p', str(os.getpid())], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=5)
    except Exception:
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog='cuems-loop-period',
        description='Print the loop period of media files, or write the missing/stale '
                    'indexes/<name>.period sidecars of a media library (--backfill).')
    ap.add_argument('files', nargs='*', help='media files to probe (printed, not written)')
    ap.add_argument('--backfill', nargs='?', const=DEFAULT_MEDIA_DIR, metavar='MEDIA_DIR',
                    help=f'write every missing or stale sidecar under MEDIA_DIR (default {DEFAULT_MEDIA_DIR})')
    ap.add_argument('--budget', type=float, default=None, help='seconds per file (default: none)')
    a = ap.parse_args(argv)
    if not a.files and a.backfill is None:
        ap.print_usage(sys.stderr)
        return 2
    rc = 0
    for f in a.files:
        try:
            print(f'{f}\t{loop_period(f, a.budget).to_json()}')
        except PeriodError as e:
            print(f'{f}\tERROR {e}', file=sys.stderr)
            rc = 1
    if a.backfill is not None:
        _low_priority()
        done = skipped = failed = 0
        for f in _media_files(a.backfill):
            if read_period(f) is not None:
                skipped += 1
                continue
            try:
                p = loop_period(f, a.budget)
                write_period(f, p)
                done += 1
                print(f'wrote {sidecar_path(f)}  {p.num}/{p.den} = {p.ms:.3f} ms ({p.rule}, {p.probe_s} s)')
            except (PeriodError, OSError) as e:
                failed += 1
                rc = 1
                print(f'{f}: ERROR {e}', file=sys.stderr)
        print(f'backfill {a.backfill}: {done} written, {skipped} already valid, {failed} failed')
    return rc


if __name__ == '__main__':
    sys.exit(main())
