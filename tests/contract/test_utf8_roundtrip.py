"""Contract C6 (T022c, T022d) — UTF-8 end to end, including under ``LC_ALL=C``.

Show and cue names carry Latin-locale text: ``Cançó d'obertura``,
``Iluminación``, ``Chançon d'été``. Every method that reads, writes or
transmits must preserve those characters exactly.

**The failure mode this prevents is silent and environmental.** ``open()``
without ``encoding=`` uses the platform default, which on a node booted with
``LANG=C`` is ASCII — so a show file with an accented cue name saves fine on a
developer's UTF-8 laptop and raises ``UnicodeEncodeError`` on the node, or
worse, writes mojibake. It cannot be caught by review, because the source line
looks identical either way. It also cannot be caught by a test that only runs
under a UTF-8 locale, which is why T022d re-runs the whole chain in a
subprocess started under ``LC_ALL=C``.

The fixture is ``tests/data/corpus/cuems-utils/unicode_showcase.xml``, added in
Phase 1 with its goldens captured by the **pre-feature** harness — before any
projection code existed, so it carries the same byte-identity obligation every
other corpus document does rather than being arbitrated by the code under test.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from tests.support.capture_goldens import normalize_schema_location
from tests.support.corpus import GOLDEN_ROOT, by_relpath
from tests.support.public_api import assert_no_xml_import

DOC = by_relpath("cuems-utils/unicode_showcase.xml")

#: Characters the fixture carries, each chosen for a different reason:
#: accented vowels, ``ç``, ``ñ``, an apostrophe, and an em dash.
MARKERS = ("á", "ó", "é", "î", "ç", "ñ", "¡", "'", "—")

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def loaded() -> CuemsScript:
    return CuemsScript.load(DOC.path)


def test_the_fixture_actually_carries_non_ascii_bytes():
    """Without this, every assertion below passes on an ASCII document."""
    raw = DOC.path.read_bytes()
    with pytest.raises(UnicodeDecodeError):
        raw.decode("ascii")
    text = raw.decode("utf-8")
    missing = [c for c in MARKERS if c not in text]
    assert not missing, f"fixture lost its markers: {missing}"


def test_load_preserves_every_character(loaded):
    assert loaded.name == "Espectáculo de Otoño"
    names = [c.name for c in loaded.cuelist.contents]
    assert "Señal de comienzo" in names
    assert "Chançon d'été" in names


def test_to_json_emits_real_utf8_and_no_escapes(loaded):
    text = loaded.to_json()
    assert "\\u" not in text, "to_json() escaped non-ASCII (ensure_ascii is not False)"
    for marker in MARKERS:
        assert marker in text, f"{marker!r} did not survive to_json()"


def test_from_json_accepts_the_utf8_bytes_of_that_string(loaded):
    text = loaded.to_json()
    assert CuemsScript.from_json(text.encode("utf-8")) == loaded


def test_the_whole_chain_is_lossless(loaded, tmp_path):
    """``load -> to_wire -> to_json -> from_json -> save -> load``."""
    rebuilt = CuemsScript.from_json(json.dumps(loaded.to_wire(), ensure_ascii=False))
    target = tmp_path / "unicode.xml"
    rebuilt.save(target)

    reloaded = CuemsScript.load(target)
    assert reloaded == loaded
    assert reloaded.to_json() == loaded.to_json()


def test_the_written_document_is_byte_identical_to_its_golden(loaded, tmp_path):
    """Byte-for-byte, with the one carve-out the harness already applies.

    ``normalize_schema_location`` is what makes the XML goldens portable while
    the written ``xsi:schemaLocation`` is still the writing machine's absolute
    path (F24). It is applied here rather than skipped, so the assertion keeps
    holding **through** T037/T080 — after those land, the produced bytes carry
    the bare filename, the goldens carry it too, and the substitution becomes
    the no-op it is meant to become.
    """
    target = tmp_path / "unicode.xml"
    loaded.save(target)
    produced = normalize_schema_location(target.read_bytes())
    assert produced == (GOLDEN_ROOT / "xml" / f"{DOC.slug}.xml").read_bytes()


def test_the_written_document_declares_its_encoding(loaded, tmp_path):
    target = tmp_path / "unicode.xml"
    loaded.save(target)
    head = target.read_bytes()[:80].decode("utf-8")
    assert "encoding='utf-8'" in head or 'encoding="utf-8"' in head


def test_invalid_utf8_bytes_are_rejected_rather_than_guessed():
    from cuemsutils.errors import IngestError

    with pytest.raises(IngestError):
        CuemsScript.from_json(b'{"CuemsScript": {"name": "\xff\xfe"}}')


# --- T022d: the same chain under a hostile locale --------------------------
#
# ``monkeypatch.setenv`` alone is not enough: Python reads the locale at
# interpreter start, so the environment has to be set *before* the process
# exists. Hence the subprocess.

_HOSTILE_SCRIPT = """
import json, sys, tempfile
from pathlib import Path

from cuemsutils.cues.CuemsScript import CuemsScript

doc = Path(sys.argv[1])

loaded = CuemsScript.load(doc)
assert loaded.name == "Espect\\u00e1culo de Oto\\u00f1o", loaded.name

text = loaded.to_json()
assert "\\\\u" not in text, "to_json escaped non-ASCII under LC_ALL=C"

rebuilt = CuemsScript.from_json(text.encode("utf-8"))
with tempfile.TemporaryDirectory() as tmp:
    target = Path(tmp) / "unicode.xml"
    rebuilt.save(target)
    written = target.read_bytes()
    assert "Espect\\u00e1culo".encode("utf-8") in written, "mojibake under LC_ALL=C"
    reloaded = CuemsScript.load(target)
    assert reloaded == loaded
    assert reloaded.to_json() == text

print("ok")
"""


def test_the_whole_chain_survives_lc_all_c(tmp_path):
    """FR-036e — the environment that turns a missing ``encoding=`` into a crash.

    A subprocess rather than ``monkeypatch.setenv`` alone: Python reads the
    locale at interpreter start, so the variable has to be set before the
    process exists. ``PYTHONIOENCODING`` is set for the ``print`` at the end
    only — it does not touch ``open()``'s default, which is the thing under
    test.
    """
    runner = tmp_path / "hostile.py"
    runner.write_text(_HOSTILE_SCRIPT, encoding="utf-8")

    env = dict(os.environ)
    env.update(
        LC_ALL="C",
        LANG="C",
        PYTHONIOENCODING="utf-8",
        PYTHONPATH=os.pathsep.join([str(REPO_ROOT / "src"), str(REPO_ROOT)]),
    )
    env.pop("PYTHONUTF8", None)

    result = subprocess.run(
        [sys.executable, str(runner), str(DOC.path)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"the UTF-8 chain failed under LC_ALL=C:\n{result.stdout}\n{result.stderr}"
    )
    assert "ok" in result.stdout


def test_the_module_under_test_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])
