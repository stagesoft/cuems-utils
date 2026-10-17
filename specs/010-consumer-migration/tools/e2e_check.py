# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""010 T047 (SC-005): a project saved by the editor loads in the engine and
renders in the UI, differing from the pre-migration payload in exactly the
enumerated deltas.

Run from this repository's root, in an interpreter that has the real
``pyossia`` and resolves ``cuemsutils`` to this checkout, with the two sibling
sources on the path::

    LD_LIBRARY_PATH=<dir holding libmtcmaster.so.0> \\
    PYTHONPATH=../cuems-editor/src:../cuems-engine/src \\
    ../cuems-engine/.venv-016/bin/python \\
        specs/010-consumer-migration/tools/e2e_check.py

Every step calls the siblings' own code, never a re-implementation:

1. **UI → editor save.** The frame the UI holds (``cuems-frontend``'s recorded
   tip ``project-013.frame.json``, the payload its 288 specs render) goes
   through the document half of the editor's ``CuemsDBProject.update``:
   ``validate_fade_durations_in_contents``, ``CuemsScript.from_json`` and
   ``save_xml``. The database half (rows, media relations) touches no document
   and is left out.
2. **Engine load.** ``cuemsengine.core.BaseEngine.read_script``, the engine's
   real project-load method, with the real ``pyossia`` imported, then the
   engine's ``media_duration`` over every media cue.
3. **Editor open → UI.** ``CuemsScript.load_with_report`` and ``to_wire``, as
   ``CuemsDBProject.open`` frames it. The result must **equal** the frame the UI
   renders.
4. **Against the pre-migration wire.** The result is compared with
   ``project-pre001.frame.json`` (the same project, ``cuemsutils`` 0.1.0rc14).
   Every difference must be one of the deltas (a)–(e) that ``cuems-editor``'s
   ``tests/ws-command-responses.txt`` enumerates, or the check fails naming it.

Exit 0 when every step holds, 1 otherwise.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

FIXTURES = Path("../cuems-frontend/specs/001-schema-descriptor-migration/fixtures")
SCHEMA_LOCATION = "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"
HARDWARE_CUES = {"AudioCue": "audio", "VideoCue": "video", "DmxCue": "dmx"}
HARDWARE_OUTPUTS = {"AudioCueOutput": "audio", "VideoCueOutput": "video", "DmxCueOutput": "dmx"}
BOOL_TEXT = {"True": True, "False": False}


def _load_frame(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def explain(old, new, path: str = "") -> list[str]:
    """Differences between ``old`` and ``new`` that no enumerated delta explains."""
    unexplained: list[str] = []
    if isinstance(old, dict) and isinstance(new, dict):
        old = dict(old)
        if SCHEMA_LOCATION in old and SCHEMA_LOCATION not in new:
            old.pop(SCHEMA_LOCATION)  # (a)
        for key in list(old):
            renamed = HARDWARE_CUES.get(key) or HARDWARE_OUTPUTS.get(key)
            target = "Cue" if key in HARDWARE_CUES else "CueOutput"
            if renamed and key not in new and target in new:  # (c)
                body = dict(new[target])
                if body.get("class") != renamed:
                    unexplained.append(f"{path}/{key}: class {body.get('class')!r}, expected {renamed!r}")
                body.pop("class", None)
                unexplained += explain(old.pop(key), body, f"{path}/{key}→{target}")
                new = {k: v for k, v in new.items() if k != target}
        for key in sorted(set(old) | set(new)):
            if key not in new:
                unexplained.append(f"{path}/{key}: removed")
            elif key not in old:
                if key == "opacity" and new[key] == 100:  # (d)
                    continue
                unexplained.append(f"{path}/{key}: added {json.dumps(new[key])[:60]}")
            else:
                unexplained += explain(old[key], new[key], f"{path}/{key}")
        return unexplained
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            return [f"{path}: {len(old)} items -> {len(new)}"]
        for i, (a, b) in enumerate(zip(old, new)):
            unexplained += explain(a, b, f"{path}[{i}]")
        return unexplained
    if old == new:
        return []
    if isinstance(old, str) and old in BOOL_TEXT and new is BOOL_TEXT[old]:  # (e)
        return []
    if path.endswith("/duration") and isinstance(new, dict) and new.get("CTimecode") is not None:  # (b)
        return []
    return [f"{path}: {json.dumps(old)[:40]} -> {json.dumps(new)[:40]}"]


def main() -> int:
    import pyossia  # noqa: F401 — the real one; this check is worthless against a mock
    from cuemseditor.CuemsDBProject import validate_fade_durations_in_contents
    from cuemsengine.core.BaseEngine import BaseEngine
    from cuemsengine.cues.helpers import media_duration
    from cuemsutils.cues.CuemsScript import CuemsScript
    from cuemsutils.cues.MediaCue import MediaCue

    ui_frame = _load_frame("project-013.frame.json")
    pre001 = _load_frame("project-pre001.frame.json")
    failures: list[str] = []
    print(f"pyossia: {pyossia.__file__}")

    with tempfile.TemporaryDirectory() as tmp:
        library = Path(tmp)
        project = library / "projects" / "e2e"
        project.mkdir(parents=True)
        script_path = project / "script.xml"

        # 1. UI -> editor save (CuemsDBProject.update's document half).
        data = copy.deepcopy(ui_frame["value"])
        validate_fade_durations_in_contents(
            (data.get("CuemsScript", {}).get("CueList") or {}).get("contents") or []
        )
        CuemsScript.from_json(data).save(script_path)
        print(f"1. editor saved {script_path.name} ({script_path.stat().st_size} bytes)")

        # 2. Engine load: the real BaseEngine.read_script, unbound, on a minimal self.
        engine = SimpleNamespace(cm=SimpleNamespace(library_path=str(library)), script=None)
        BaseEngine.read_script(engine, "e2e")
        cues = [c for c in engine.script.cuelist.contents if isinstance(c, MediaCue)]
        durations = [str(media_duration(c)) for c in cues]
        print(f"2. engine loaded it: {len(engine.script.cuelist.contents)} cues, media durations {durations}")

        # 3. Editor open -> UI frame.
        script, report = CuemsScript.load_with_report(script_path)
        frame = {"type": "project", "value": script.to_wire()}
        print(f"3. editor reopened it: outcome {report.outcome.name}")
        if frame != ui_frame:
            failures.append("3. the reopened frame is not the frame the UI renders")
            failures += ["   " + d for d in explain(ui_frame, frame)]
        else:
            print("   equal to the UI's recorded frame")

    # 4. Against the pre-migration wire.
    unexplained = explain(pre001, frame)
    if unexplained:
        failures.append("4. differences from the pre-migration payload that no delta explains:")
        failures += ["   " + d for d in unexplained]
    else:
        print("4. every difference from the pre-migration payload is one of (a)-(e)")

    for line in failures:
        print(line)
    print("PASS" if not failures else "FAIL")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
