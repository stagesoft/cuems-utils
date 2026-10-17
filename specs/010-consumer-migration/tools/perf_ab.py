# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""010 T065/T066 — the per-operation budgets, by FR-PERF-001a's method.

Interleaved A/B in fresh processes: each round runs one sample of every arm,
alternating, so box contention lands on both alike. One **sample** is a fresh
interpreter with the arm's ``src`` first on ``sys.path``. A warm-up call comes
first, then ``--calls`` timed calls, and the sample's figure is their median.
The ``descriptor-*`` operations are the exception: they time the **first** call,
because that is what FR-PERF-001's "publication costs nothing measurable"
compares (``tests/contract/test_descriptor_laziness.py``'s operation).

Each arm loads **its own** copy of the fixture, at the same path in its own
tree. No single document is readable by both a pre-013 and a post-013 library,
so the arms cannot share an input. ``--arm NAME=ROOT`` names a checkout root
(the directory holding ``src/`` and ``tests/``).

    PY=$(uvx hatch env find test.py3.11)/bin/python
    $PY specs/010-consumer-migration/tools/perf_ab.py --op show \\
        --arm A=<worktree at f740711> --arm B=. --rounds 16

Output: one JSON line per sample (arm, op, ms, cpu0 frequency, load average),
then a summary of the median per arm and the B/A ratio. Run it in **three
windows**, minutes apart, and pool (CLAUDE.md's sampling lesson).
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path

CHILD = r'''
import json, os, sys, time, statistics
op, root, calls = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.environ.setdefault("CUEMS_LOG_LEVEL", "ERROR")
sys.path.insert(0, os.path.join(root, "src"))
def timed(fn, n):
    fn()
    out = []
    for _ in range(n):
        t = time.perf_counter(); fn(); out.append((time.perf_counter() - t) * 1000)
    return statistics.median(out)
if op == "show":
    from cuemsutils.cues.CuemsScript import CuemsScript
    doc = os.path.join(root, "tests/data/corpus/cuems-engine/projects/complex_test/script.xml")
    ms = timed(lambda: CuemsScript.load(doc), calls)
elif op == "network_map":
    from cuemsutils.tools.ConfigBase import load_config_document
    from cuemsutils.xml.settings import NetworkMap
    doc = os.path.join(root, "tests/data/network_map.xml")
    ms = timed(lambda: load_config_document(NetworkMap, doc, "network_map"), calls)
elif op in ("descriptor-internal", "descriptor-public"):
    # tests/contract/test_descriptor_laziness.py's operation: every import and
    # the manager are built BEFORE the timer, which covers the first call only.
    from cuemsutils.xml.descriptor import SchemaDescriptor
    from cuemsutils.xml.schema import get_schema
    from cuemsutils.tools.ConfigManager import ConfigManager, SchemaName
    manager = ConfigManager(config_dir=os.path.join(root, "tests/data/corpus/cuems-engine"), load_all=False)
    t = time.perf_counter()
    if op == "descriptor-internal":
        SchemaDescriptor().types("script")
    else:
        manager.get_schema_descriptor(SchemaName.SCRIPT)
    ms = (time.perf_counter() - t) * 1000
    extra = {"schemas_built": get_schema.cache_info().currsize}
else:
    raise SystemExit(f"unknown op {op}")
import cuemsutils
print(json.dumps({"ms": ms, "lib": cuemsutils.__file__, **globals().get("extra", {})}))
'''


def _box() -> dict:
    def read(path: str) -> str:
        try:
            return Path(path).read_text().strip()
        except OSError:
            return "?"
    return {
        "cpu0_khz": read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"),
        "governor": read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
        "loadavg": read("/proc/loadavg").split()[0],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="perf_ab")
    parser.add_argument("--op", required=True,
                        choices=["show", "network_map", "descriptor-internal", "descriptor-public"])
    parser.add_argument("--arm", action="append", required=True, help="NAME=ROOT, or NAME=ROOT:OP")
    parser.add_argument("--rounds", type=int, default=16)
    parser.add_argument("--calls", type=int, default=20)
    args = parser.parse_args(argv)

    arms = []
    for spec in args.arm:
        name, _, rest = spec.partition("=")
        root, _, op = rest.partition(":")
        arms.append((name, str(Path(root).resolve()), op or args.op))

    samples: dict[str, list[float]] = {name: [] for name, _, _ in arms}
    env = {**os.environ, "CUEMS_LOG_LEVEL": "ERROR", "PYTHONDONTWRITEBYTECODE": "1"}
    for round_no in range(args.rounds):
        order = arms if round_no % 2 == 0 else list(reversed(arms))
        for name, root, op in order:
            box = _box()
            done = subprocess.run(
                [sys.executable, "-I", "-c", CHILD, op, root, str(args.calls)],
                capture_output=True, text=True, env=env, cwd=root, timeout=600,
            )
            if done.returncode != 0:
                print(done.stderr[-2000:], file=sys.stderr)
                return 1
            result = json.loads(done.stdout.strip().splitlines()[-1])
            if not result["lib"].startswith(root):
                print(f"{name}: imported {result['lib']}, not from {root}", file=sys.stderr)
                return 1
            samples[name].append(result["ms"])
            extra = {k: v for k, v in result.items() if k not in ("ms", "lib")}
            print(json.dumps({"round": round_no, "arm": name, "op": op, "ms": round(result["ms"], 3), **extra, **box}))

    medians = {name: statistics.median(values) for name, values in samples.items()}
    names = [name for name, _, _ in arms]
    summary = {
        "medians_ms": {k: round(v, 3) for k, v in medians.items()},
        "bands_ms": {k: [round(min(v), 3), round(max(v), 3)] for k, v in samples.items()},
    }
    if len(names) == 2:
        summary[f"ratio_{names[1]}/{names[0]}"] = round(medians[names[1]] / medians[names[0]], 3)
    print("SUMMARY " + json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
