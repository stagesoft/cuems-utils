# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""The work order's public-path probes, run against one arm (017 T017; research R13).

The arm is chosen by ``PYTHONPATH``: run this with ``PYTHONPATH=<arm>/src``. The probes never touch
the fixture files: each one copies them to a temporary directory first. One verdict line per
probe:

    env -u CUEMS_CONF_PATH PYTHONPATH=<arm>/src $PY -P tools/probes.py --fixtures tests/data/rc17

* **S-1′**: the rc17 fixture → ``cuems-reshape-devices`` → ``cuems-convert-documents`` →
  ``CuemsScript.load_with_report``. The tools are called through ``main()``, because the
  ``python -m`` form of reshape is a no-op (S-4).
* **control**: the same, for the ``stop`` twin.
* **S-1**: the migrated control document with its last cue turned into ``stop_project`` with no
  target, then ``CuemsScript.save``.
* **S-2**: ``ActionCue({"action_type": "stop_project", "action_target": None})``.
* **X-4**: the migrated fixture's media values through ``.get`` / attribute / ``in`` / ``to_wire``.
"""
import argparse
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

warnings.simplefilter("ignore")


def _verdict(name, fn):
    try:
        print(f"{name}: {fn()}")
    except Exception as exc:  # a probe reports, it never stops the run
        print(f"{name}: REFUSED {type(exc).__name__}: {str(exc).splitlines()[0][:160]}")


def _migrate(src: Path, workdir: Path) -> Path:
    from cuemsutils.xml import convert_documents, reshape_devices

    doc = workdir / src.name
    shutil.copy(src, doc)
    rc_r = reshape_devices.main([str(doc)])
    rc_c = convert_documents.main([str(doc)])
    print(f"  ({src.name}: reshape exit {rc_r}, convert exit {rc_c})")
    return doc


def _cues(script):
    from cuemsutils.cues.Cue import Cue

    out = []

    def walk(o):
        if isinstance(o, Cue):
            out.append(o)
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                walk(v)

    walk(script)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixtures", required=True, help="directory holding the rc17 fixture")
    args = parser.parse_args()
    import cuemsutils
    from cuemsutils.cues.ActionCue import ActionCue
    from cuemsutils.cues.CuemsScript import CuemsScript

    fixtures = Path(args.fixtures)
    print(f"# arm: cuemsutils {cuemsutils.__version__} at {Path(cuemsutils.__file__).parent}")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)

        def s1_prime():
            doc = _migrate(fixtures / "stop_project.xml", work)
            script, report = CuemsScript.load_with_report(str(doc))
            action = [c for c in _cues(script) if isinstance(c, ActionCue)][0]
            return (f"{report.outcome.name}, action_type={action['action_type']}, "
                    f"action_target={action['action_target']!r}, repairs={len(report.repairs)}")

        def control():
            doc = _migrate(fixtures / "stop_control.xml", work)
            _, report = CuemsScript.load_with_report(str(doc))
            return report.outcome.name

        def s1():
            (work / "s1").mkdir()
            doc = _migrate(fixtures / "stop_control.xml", work / "s1")
            script = CuemsScript.load(str(doc))
            action = [c for c in _cues(script) if isinstance(c, ActionCue)][0]
            dict.__setitem__(action, "action_type", "stop_project")
            dict.__setitem__(action, "action_target", None)
            out = work / "s1" / "saved.xml"
            script.save(str(out))
            return f"saved; <action_target /> written: {'<action_target />' in out.read_text()}"

        def s2():
            cue = ActionCue({"action_type": "stop_project", "action_target": None})
            return f"constructed, action_target={cue['action_target']!r}"

        def x4():
            (work / "x4").mkdir()
            # The control twin carries the same VideoCue and loads on every arm (no stop_project).
            doc = _migrate(fixtures / "stop_control.xml", work / "x4")
            script, _ = CuemsScript.load_with_report(str(doc))
            media = [c for c in _cues(script) if type(c).__name__ in ("VideoCue", "AudioCue")]
            parts = []
            for cue in media:
                m = cue["Media"]
                vals = {k: m.get(k) for k in ("pixel_width", "pixel_height", "file_size", "file_md5")}
                attr = {k: getattr(m, k) for k in vals}
                wire = cue.to_wire() if hasattr(cue, "to_wire") else None
                parts.append(
                    f"{type(cue).__name__}: get={vals} attr==get:{attr == vals} "
                    f"in={[k for k in vals if k in m]}"
                    + (f" wire_has={[k for k in vals if k in str(wire)]}" if wire is not None else "")
                )
            return " | ".join(parts)

        _verdict("S-1'", s1_prime)
        _verdict("control", control)
        _verdict("S-1", s1)
        _verdict("S-2", s2)
        _verdict("X-4", x4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
