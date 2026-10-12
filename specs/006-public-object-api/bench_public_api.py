"""T083 — the shipped surface, measured against this feature's budgets.

``bench_to_wire.py`` is the **research** script: it measures the two candidate
``to_wire()`` strategies, and Strategy A — the round trip through XML — is the
one that was *rejected*. Running it after the fact measures code that is not on
the shipped path.

This measures what shipped. Same method throughout, so the numbers are
comparable to that script's: warm process, 3 untimed warmups, median of 30
samples, the 24 KB ``complex_test/script.xml``.

Run: PYENV_VERSION=3.11.9 pyenv exec hatch run hatch-test.py3.11:python \
        specs/006-public-object-api/bench_public_api.py
"""

from __future__ import annotations

import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from cuemsutils.cues.CuemsScript import CuemsScript  # noqa: E402
from cuemsutils.xml.documents import build_tree  # noqa: E402
from cuemsutils.xml.validators import run_rules  # noqa: E402
from cuemsutils.xml.xml_reader_writer import XmlReaderWriter  # noqa: E402

DOC = REPO_ROOT / "tests/data/corpus/cuems-engine/projects/complex_test/script.xml"
N = 30


def timed(label: str, fn, warmup: int = 3) -> float:
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(N):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    median = statistics.median(samples)
    print(
        f"  {label:<46} {median:7.2f} ms  "
        f"(min {min(samples):6.2f}, max {max(samples):6.2f})"
    )
    return median


def _cpu() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:  # pragma: no cover - not Linux
        pass
    return "unknown"


def main() -> None:
    # The measurement context, printed rather than assumed, so the numbers in
    # baseline.md are reproducible by someone other than their author (CHK041).
    print(f"machine : {platform.node()}  ({_cpu()})")
    print(f"python  : {platform.python_version()}  ({sys.executable})")
    print(f"document: {DOC.name}  ({DOC.stat().st_size} bytes)")
    print(f"method  : warm process, {N} samples, median\n")

    scratch = Path(tempfile.mkdtemp())
    script = CuemsScript.load(DOC)
    pre_feature = XmlReaderWriter(schema_name="script", xmlfile=str(scratch / "old.xml"))

    print("READ")
    read_dict = XmlReaderWriter(schema_name="script", xmlfile=str(DOC))
    t_read = timed("read()            [pre-feature project_load]", read_dict.read)
    t_load = timed("CuemsScript.load()", lambda: CuemsScript.load(DOC))

    print("\nPROJECT")
    t_wire = timed("to_wire()", script.to_wire)
    timed("to_json()", script.to_json)
    t_tree = timed("build_tree()      [objects -> ElementTree]",
                   lambda: build_tree(script, "script"))

    print("\nVALIDATE AND WRITE")
    timed("validate()        [T1 + T2, collecting]", script.validate)
    t_rules = timed("run_rules()       [the T2 tier alone]", lambda: run_rules(script))
    t_save = timed("save()            [build + T1 + T2 + atomic write]",
                   lambda: script.save(scratch / "new.xml"))
    t_old_write = timed("write_from_object()  [pre-feature write]",
                        lambda: pre_feature.write_from_object(script))

    print("\n" + "=" * 74)
    print(f"  load() + to_wire()          {t_load + t_wire:7.2f} ms    budget  25 ms")
    print(f"  to_wire() alone             {t_wire:7.2f} ms    budget   5 ms")
    print(f"  write path                  {t_save:7.2f} ms vs {t_old_write:6.2f} ms "
          f"({(t_save / t_old_write - 1) * 100:+.1f}%, budget +10%)")
    print()
    print(f"  pre-feature read()          {t_read:7.2f} ms")
    print(f"  tree build                  {t_tree:7.2f} ms")
    print(f"  the T2 tier                 {t_rules:7.2f} ms "
          f"({t_rules / t_save * 100:.1f}% of save())")
    print()
    print("  If to_wire() ever lands near the tree build, let alone near 16 ms,")
    print("  the direct projection has become the round trip. Check that")
    print("  encode_wire is not calling to_dict.")


if __name__ == "__main__":
    main()
