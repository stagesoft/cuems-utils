# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Descriptor derivation probe — ``specs/planning/descriptor-instance-cache.md`` phase 0.

Feature 015 recorded descriptor derivation for ``script`` as 1.04 -> 2.83 ms
against a <= 1.22 ms budget, but the probe it used was never committed. This one
is, so the next figure can be reproduced rather than re-derived.

What one **sample** is: a fresh interpreter, the library imported, every schema's
descriptor built once (the cold call, timed separately), then
``SchemaDescriptor().types(schema)`` timed ``--calls`` times. The sample's
figure is the **median** of those calls, with the minimum kept beside it. A
fresh process per sample, because the descriptor sits on module-level caches
(``derive``, the registries, ``_repairability_cache``) and an in-process
comparison is confounded by whichever ran first (``test_descriptor_laziness.py``
records the same trap).

**Interleaved A/B.** Pass ``--arm NAME=SRC_DIR`` twice and the probe alternates
the arms round by round, one subprocess each, so box contention lands on both
arms alike. By the sampling lesson in ``CLAUDE.md`` (feature 015), the verdict
rests on the A/B ratio over **16 samples in at least three windows**, never on
one window's absolutes — run this three times, minutes apart, and pool.

Not collected by pytest (no ``test_`` prefix). Run with the interpreter
``hatch`` resolves, and record which build it is::

    PY=$(uvx hatch env find test.py3.11)/bin/python
    $PY -m tests.support.perf_descriptor --arm A=/path/to/worktree/src --arm B=src --rounds 5

The probe imports nothing from ``tests`` inside the child process, so an arm can
point at any checkout of ``cuemsutils``, including one older than this file.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

#: The child: stdlib plus the arm's own ``cuemsutils``. Kept as a string so it
#: depends on nothing in this checkout.
_CHILD = r"""
import json, sys, time
sys.path.insert(0, sys.argv[1])
calls = int(sys.argv[2])
schemas = sys.argv[3].split(",")

import cuemsutils
from cuemsutils.xml import descriptor as d

out = {"cuemsutils": cuemsutils.__file__, "cold_ms": {}, "warm_ms": {}, "warm_min_ms": {},
       "instance_for_calls": {}, "nodes": {}}

# Cold: the first call per schema, imports excluded. The FIRST schema touched
# also pays the global repairability join over all six (test_descriptor_laziness.py).
for name in schemas:
    t0 = time.perf_counter()
    d.SchemaDescriptor().types(name)
    out["cold_ms"][name] = (time.perf_counter() - t0) * 1e3

def _nodes(o):
    if isinstance(o, dict):
        return 1 + sum(_nodes(v) for v in o.values())
    if isinstance(o, list):
        return 1 + sum(_nodes(v) for v in o)
    return 1

for name in schemas:
    d.SchemaDescriptor().types(name)  # one extra warm-up
    samples = []
    for _ in range(calls):
        t0 = time.perf_counter()
        d.SchemaDescriptor().types(name)
        samples.append((time.perf_counter() - t0) * 1e3)
    samples.sort()
    out["warm_ms"][name] = samples[len(samples) // 2]
    out["warm_min_ms"][name] = samples[0]
    out["nodes"][name] = sum(_nodes(td.instance) for td in d.SchemaDescriptor().types(name))

    # How much instance building a WARM call still does. Today: one
    # _instance_for per type. After the cache: zero. Counted, not timed.
    # Pre-015 trees had a recursive _instance_for(key, branch), so there the
    # count includes the recursion and is not comparable across that line.
    original = getattr(d, "_instance_for", None)
    if original is not None:
        count = [0]
        def counting(*args, _orig=original, **kwargs):
            count[0] += 1
            return _orig(*args, **kwargs)
        d._instance_for = counting
        try:
            d.SchemaDescriptor().types(name)
        finally:
            d._instance_for = original
        out["instance_for_calls"][name] = count[0]

print(json.dumps(out))
"""

SCHEMAS = (
    "script", "settings", "network_map", "project_mappings", "project_settings",
    "hardware_outputs",
)


def _run_child(src: Path, calls: int, schemas: tuple[str, ...]) -> dict:
    result = subprocess.run(
        [sys.executable, "-c", _CHILD, str(src), str(calls), ",".join(schemas)],
        capture_output=True, text=True,
        # The library logs to stdout by default; the JSON is the last line.
        env={**os.environ, "CUEMS_LOG_LEVEL": "ERROR"},
    )
    if result.returncode != 0:
        raise SystemExit(f"probe child failed for {src}:\n{result.stderr[-2000:]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


def _loadavg() -> str:
    try:
        return Path("/proc/loadavg").read_text().split()[0]
    except OSError:
        return "?"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--arm", action="append", required=True, metavar="NAME=SRC_DIR",
                        help="an arm to measure; repeat for A/B (interleaved per round)")
    parser.add_argument("--rounds", type=int, default=5, help="samples per arm (default 5)")
    parser.add_argument("--calls", type=int, default=100,
                        help="timed warm calls per schema per sample (default 100)")
    parser.add_argument("--schemas", default=",".join(SCHEMAS))
    parser.add_argument("--jsonl", type=Path, help="append every raw sample to this file")
    args = parser.parse_args(argv)

    arms: list[tuple[str, Path]] = []
    for spec in args.arm:
        name, _, src = spec.partition("=")
        path = Path(src).resolve()
        if not (path / "cuemsutils" / "__init__.py").is_file():
            parser.error(f"--arm {spec}: {path} holds no cuemsutils package")
        arms.append((name, path))
    schemas = tuple(s for s in args.schemas.split(",") if s)

    print(f"# interpreter {sys.executable} ({sys.version.split()[0]}, "
          f"{' '.join(sys.version.split()[1:])})")
    results: dict[str, list[dict]] = {name: [] for name, _ in arms}
    for round_no in range(1, args.rounds + 1):
        for name, src in arms:
            sample = _run_child(src, args.calls, schemas)
            sample.update(arm=name, round=round_no, load=_loadavg(),
                          at=time.strftime("%Y-%m-%dT%H:%M:%S"))
            if Path(sample["cuemsutils"]).resolve().parent.parent != src:
                raise SystemExit(f"arm {name} imported {sample['cuemsutils']}, not {src}")
            results[name].append(sample)
            print(f"{name} r{round_no} load={sample['load']} "
                  + " ".join(f"{s}={sample['warm_ms'][s]:.3f}" for s in schemas), flush=True)
            if args.jsonl:
                with args.jsonl.open("a") as fh:
                    fh.write(json.dumps(sample) + "\n")

    print("\n# per arm: median of sample medians [band], warm ms; cold = median first call")
    for name, samples in results.items():
        first = samples[0]
        print(f"## {name}  ({first['cuemsutils']})")
        for s in schemas:
            warm = [x["warm_ms"][s] for x in samples]
            cold = [x["cold_ms"][s] for x in samples]
            print(f"  {s:17s} warm {statistics.median(warm):7.3f} "
                  f"[{min(warm):.3f}-{max(warm):.3f}]  cold {statistics.median(cold):8.1f}  "
                  f"nodes {first['nodes'][s]:4d}  "
                  f"_instance_for/warm call {first['instance_for_calls'].get(s, '-')}")
    if len(arms) == 2:
        (a, sa), (b, sb) = results.items()
        print(f"\n# ratio {b}/{a}, medians")
        for s in schemas:
            ma = statistics.median(x["warm_ms"][s] for x in sa)
            mb = statistics.median(x["warm_ms"][s] for x in sb)
            print(f"  {s:17s} {mb / ma:5.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
