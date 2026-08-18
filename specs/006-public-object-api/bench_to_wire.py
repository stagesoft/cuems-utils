"""Phase 0 research: measure the two candidate ``to_wire()`` strategies.

FR-PERF-001 requires a budget for ``to_wire()`` before implementation, and the
strategy choice is a performance decision, so it is measured rather than argued.

Strategy A — round-trip through XML: object -> ElementTree -> ``schema.to_dict``.
Byte-identity is free because it *is* the reader's own code path; the cost is
building a tree and re-decoding it.

Strategy B — direct projection: a mapper ``encode_wire`` mirroring ``decode``.
Fast, but it has to reproduce the converter's shape by hand and every deviation
is a UI break.

Run: PYENV_VERSION=3.11.9 pyenv exec hatch run python \
        specs/006-public-object-api/bench_to_wire.py
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from cuemsutils.xml.xml_reader_writer import XmlReaderWriter  # noqa: E402

DOC = REPO_ROOT / "tests/data/corpus/cuems-engine/projects/complex_test/script.xml"
N = 30


def timed(label, fn, warmup=3):
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(N):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000)
    med = statistics.median(samples)
    print(f"  {label:<46} {med:7.2f} ms  (min {min(samples):6.2f}, max {max(samples):6.2f})")
    return med


def main():
    print(f"Document: {DOC.relative_to(REPO_ROOT)}  ({DOC.stat().st_size} bytes)\n")

    rw = XmlReaderWriter(schema_name="script", xmlfile=str(DOC))

    print("BASELINE — what the editor's project_load costs today")
    t_read = timed("read()  [XML -> wire dict]", lambda: rw.read())
    obj = rw.read_to_objects()
    t_objs = timed("read_to_objects()  [XML -> objects]", lambda: rw.read_to_objects())

    print("\nSTRATEGY A — object -> tree -> to_dict")
    t_build = timed("build_xml_from_object()  [objects -> tree]",
                    lambda: rw.build_xml_from_object(obj))
    tree = rw.build_xml_from_object(obj)

    def a_full():
        t = rw.build_xml_from_object(obj)
        return rw.schema_object.to_dict(
            t, validation="strict", strip_namespaces=False
        )

    t_a = timed("A: build + to_dict  [objects -> wire dict]", a_full)

    def a_decode_only():
        return rw.schema_object.to_dict(tree, validation="strict", strip_namespaces=False)

    t_a_dec = timed("  of which: to_dict on a prebuilt tree", a_decode_only)

    print("\n" + "=" * 74)
    print("READING")
    print("=" * 74)
    print(f"  Today's project_load (read)                    {t_read:7.2f} ms")
    print(f"  Strategy A end-to-end (load + to_wire)         {t_objs + t_a:7.2f} ms")
    print(f"  Strategy A to_wire alone                       {t_a:7.2f} ms")
    print(f"    tree build                                   {t_build:7.2f} ms")
    print(f"    to_dict                                      {t_a_dec:7.2f} ms")
    print()
    print(f"  A's to_wire vs today's whole read():           {t_a / t_read:5.2f}x")
    print("  Strategy B (direct projection) would replace the")
    print(f"  {t_a:.2f} ms above with a single object walk — the")
    print(f"  {t_build:.2f} ms tree build and the {t_a_dec:.2f} ms re-decode both go away.")


if __name__ == "__main__":
    main()
