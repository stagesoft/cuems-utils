# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Show-document load timing for 017 (FR-PERF-001), with 015's recipe.

One *sample* is measured in a fresh interpreter:
1. one warm load, which pays the schema parse and the registry build once per process;
2. three rounds of five timed loads each;
3. the sample is the **minimum of the three round medians**, in milliseconds.

This is ``specs/015-consumer-gate-closure/quickstart.md``'s recipe verbatim.

Arms alternate per sample, so that A and B see the same box state (interleaved A/B):

    python tools/perf_show_load.py --arm A=<worktree>/src --arm B=<worktree>/src --samples 6

Each line printed is ``<arm> <ms> <scaling_cur_freq kHz> <loadavg-1m>``. Record the interpreter
build and governor beside the output. A figure without them is not evidence.
"""
import argparse
import os
import subprocess
import sys

DOCUMENT = "tests/data/corpus/cuems-engine/projects/complex_test/script.xml"

SAMPLE = r"""
import statistics, sys, time, warnings
warnings.simplefilter("ignore")
from cuemsutils.cues.CuemsScript import CuemsScript
D = sys.argv[1]
CuemsScript.load(D)
medians = []
for _ in range(3):
    timings = []
    for _ in range(5):
        started = time.perf_counter()
        CuemsScript.load(D)
        timings.append((time.perf_counter() - started) * 1000)
    medians.append(statistics.median(timings))
print("%.3f" % min(medians))
"""


def _read(path: str) -> str:
    try:
        with open(path) as handle:
            return handle.read().split()[0]
    except OSError:
        return "?"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arm", action="append", required=True, help="NAME=SRC_DIR")
    parser.add_argument("--samples", type=int, default=6, help="samples per arm")
    args = parser.parse_args()
    arms = [a.split("=", 1) for a in args.arm]
    for _ in range(args.samples):
        for name, src in arms:
            # The document is read from the arm's own checkout, so each arm loads its own corpus.
            document = os.path.join(os.path.dirname(os.path.abspath(src)), DOCUMENT)
            env = dict(os.environ, PYTHONPATH=src)
            env.pop("CUEMS_CONF_PATH", None)
            ms = subprocess.run(
                [sys.executable, "-c", SAMPLE, document],
                env=env, capture_output=True, text=True, check=True,
            ).stdout.strip()
            freq = _read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
            load = _read("/proc/loadavg")
            print(f"{name} {ms} {freq} {load}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
