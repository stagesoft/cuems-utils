"""Golden capture harness (T009).

Captures what the library does **today**, so that every later step is verifiable
rather than merely reviewed. Run against unmodified code, once:

    export PYENV_VERSION=3.11.9
    pyenv exec python -m tests.support.capture_goldens

Two rules, and they are the reason this is a script rather than a fixture:

* **Missing goldens are generated freely.** Adding a corpus document must not
  require a ceremony, or nobody will add one (FR-021, SC-016).
* **Existing goldens are never overwritten without ``--force``.** Regenerating a
  golden to make a test pass defeats the entire feature. The flag exists so that
  doing it is a decision someone typed, not a side effect of running a script.

Nothing here imports the new engine. The harness must produce identical output
before and after the swap — that *is* the measurement.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.support.corpus import (  # noqa: E402
    DOCUMENTS,
    GOLDEN_ROOT,
    REPO_ROOT,
    CorpusDoc,
)

#: The written ``xsi:schemaLocation`` embeds the writing machine's **absolute**
#: path to the bundled ``.xsd`` — so goldens captured here would never reproduce
#: on another machine or in CI. That one component is replaced by this
#: placeholder before comparison; every other byte is compared as-is (FR-010b).
#:
#: This is a defect, not a design choice: recorded as **F24**, fix deferred to
#: feature 006. Normalizing it here is what keeps the goldens portable in the
#: meantime, and the narrowness of the carve-out is the point.
#:
#: Deliberately free of XML metacharacters: it is substituted **inside an
#: attribute value**, so a placeholder containing ``<`` would leave every XML
#: golden not well-formed and unparseable by the tests that read them.
SCHEMA_PATH_PLACEHOLDER = "@@SCHEMAS_DIR@@"

XML_ROOT_TAG = {
    "script": "CuemsProject",
    "settings": "CuemsSettings",
    "network_map": "CuemsNetworkMap",
    "project_mappings": "CuemsProjectMappings",
    "project_settings": "CuemsProjectSettings",
    "outputs": "CuemsOutputs",
}


def normalize_schema_location(raw: bytes) -> bytes:
    """Replace the absolute ``.xsd`` path in written XML (FR-010b)."""
    schemas_dir = str(REPO_ROOT / "src" / "cuemsutils" / "xml" / "schemas")
    return raw.replace(schemas_dir.encode(), SCHEMA_PATH_PLACEHOLDER.encode())


#: ``xmlschema`` renders the offending node into its message as
#: ``<Element 'node' at 0x7f3c...>``. That address changes every run, so an
#: outcome record containing it is not a golden — it is a coin flip. Replaced
#: before the record is written.
_ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]+")


def _outcome(exc: BaseException | None) -> dict:
    """Today's accept/reject verdict for one layer, in a comparable shape.

    Records the exception *type* and the first line of its message, not the full
    traceback: the type is the contract (FR-015 — the engine may never reject
    what today's parser accepts, nor start accepting what it rejects), while a
    full message would pin ``xmlschema``'s wording and fail on its next patch
    release.
    """
    if exc is None:
        return {"ok": True}
    head = str(exc).splitlines()[0][:200] if str(exc) else ""
    return {
        "ok": False,
        "error_type": type(exc).__name__,
        "error_head": _ADDRESS_RE.sub("0xADDR", head),
    }


def _reader(doc: CorpusDoc, xmlfile: str | None = None):
    from cuemsutils.xml.xml_reader_writer import XmlReaderWriter

    return XmlReaderWriter(
        schema_name=doc.schema,
        xmlfile=xmlfile if xmlfile is not None else str(doc.path),
        xml_root_tag=XML_ROOT_TAG[doc.schema],
    )


def capture_read_dict(doc: CorpusDoc):
    """``XmlReaderWriter.read`` — ``strip_namespaces=False`` (FR-013, config A)."""
    try:
        return _reader(doc).read(), None
    except Exception as exc:  # noqa: BLE001 - the failure is the data
        return None, exc


def capture_config_dict(doc: CorpusDoc):
    """The config-class reader — ``strip_namespaces=True``, explicit
    ``dict``/``list``, ``attr_prefix=''`` (FR-013, config B).

    Its output differs from config A today, and FR-013 requires the
    *differences* to be preserved too, so both are captured separately rather
    than one being derived from the other.
    """
    if doc.config_class is None:
        return None, None
    # Resolved off the package, never off ``cuemsutils.xml.Settings``: the
    # package's ``__init__`` re-exports the ``Settings`` *class*, which shadows
    # any module of the same name. The D9 rename moved the implementation to
    # ``settings.py``, but the shim at the old path brings the collision back —
    # so this stays the safe way to reach a config class by name.
    import cuemsutils.xml as xml_package

    cls = getattr(xml_package, doc.config_class)
    try:
        return cls(str(doc.path)).xml_dict, None
    except Exception as exc:  # noqa: BLE001
        return None, exc


def capture_written_xml(doc: CorpusDoc):
    """``write(read_to_objects(doc))`` — the C1 artifact.

    Only the ``script`` schema has a working write path today: the config
    classes are read-only, and building XML from a settings dict raises
    ``AttributeError`` in ``XmlBuilder``. That is today's behaviour, so it is
    captured as an outcome rather than worked around.
    """
    try:
        obj = _reader(doc).read_to_objects()
    except Exception as exc:  # noqa: BLE001
        return None, exc, None
    out = Path(tempfile.mkdtemp()) / "written.xml"
    try:
        _reader(doc, xmlfile=str(out)).write_from_object(obj)
    except Exception as exc:  # noqa: BLE001
        return None, None, exc
    return normalize_schema_location(out.read_bytes()), None, None


class GoldenWriter:
    """Writes goldens, and refuses to silently replace one."""

    def __init__(self, force: bool = False):
        self.force = force
        self.written: list[str] = []
        self.kept: list[str] = []
        self.replaced: list[str] = []
        self.conflicts: list[str] = []

    def put(self, relpath: str, payload: bytes) -> None:
        target = GOLDEN_ROOT / relpath
        rel = str(relpath)
        if target.exists():
            if target.read_bytes() == payload:
                self.kept.append(rel)
                return
            if not self.force:
                self.conflicts.append(rel)
                return
            self.replaced.append(rel)
        else:
            self.written.append(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)


def _json_bytes(value) -> bytes:
    """Exactly ``json.dumps(value)``, which is what C2 compares.

    Not pretty-printed and with no trailing newline: the golden **is** the
    artifact under contract, and ``json.dumps`` is order-sensitive, so key
    insertion order is preserved on disk (FR-011a).
    """
    return json.dumps(value).encode("utf-8")


def capture(force: bool = False) -> GoldenWriter:
    writer = GoldenWriter(force=force)
    outcomes: dict[str, dict] = {}

    for doc in DOCUMENTS:
        record: dict = {"schema": doc.schema, "category": doc.category}

        read_dict, read_exc = capture_read_dict(doc)
        record["read"] = _outcome(read_exc)
        if read_exc is None:
            writer.put(f"dict/{doc.slug}.reader.json", _json_bytes(read_dict))

        config_dict, config_exc = capture_config_dict(doc)
        if doc.config_class is not None:
            record["config_read"] = _outcome(config_exc)
            record["config_class"] = doc.config_class
            if config_exc is None:
                writer.put(f"dict/{doc.slug}.config.json", _json_bytes(config_dict))

        xml_bytes, obj_exc, write_exc = capture_written_xml(doc)
        record["to_objects"] = _outcome(obj_exc)
        if obj_exc is None:
            record["write"] = _outcome(write_exc)
        if xml_bytes is not None:
            writer.put(f"xml/{doc.slug}.xml", xml_bytes)

        outcomes[doc.relpath] = record

    outcomes.update(_capture_generated(writer))
    writer.put("outcomes.json", json.dumps(outcomes, indent=2, sort_keys=True).encode())
    return writer


#: Fixed timestamps for the generated document. ``create_script`` deliberately
#: returns its template with ``created``/``modified`` set to ``None`` — it is
#: sent to the editor empty — but ``script.xsd`` carries
#: ``<xs:assert test="modified >= created"/>``, which an empty string cannot
#: satisfy. Stamping both is what makes the template writable at all.
GENERATED_CREATED = "2026-01-01T00:00:00"
GENERATED_MODIFIED = "2026-01-01T00:00:00"


_UUID_RE = re.compile(
    rb"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)


def normalize_uuids(raw: bytes) -> bytes:
    """Rewrite uuid4 values to a stable sequence, in first-appearance order.

    Applied **only** to the generated document. ``create_script`` mints a fresh
    uuid for the script, the cue list, each of the five cues and each media
    item, so its bytes differ on every call and cannot be a golden as they
    stand.

    Normalizing the output is deliberately preferred over seeding the generator.
    Seeding was tried first and does not hold: the number of uuids minted before
    ``create_script`` reaches its own depends on import order and on lazily
    constructed, cached object defaults, so a patched counter lands on different
    values in a fresh process than in one that has already walked the corpus —
    reproducible *most* of the time, which is the worst property a golden can
    have. Rewriting after the fact depends on nothing but the bytes.

    First-appearance order is itself part of what this pins: a mapper that
    emitted the same values in a different order would produce a different
    normalized document, and rightly fail.

    Vendored documents are **not** normalized. Their uuids are real content read
    from a real file, and stable already.
    """
    mapping: dict[bytes, bytes] = {}

    def replace(match: re.Match) -> bytes:
        found = match.group(0)
        if found not in mapping:
            mapping[found] = (
                "00000000-0000-4000-8000-%012x" % (len(mapping) + 1)
            ).encode()
        return mapping[found]

    return _UUID_RE.sub(replace, raw)


def _make_template_writable(script) -> None:
    """Undo the blanking ``create_script`` does on its way out.

    ``create_script`` validates a fully-populated script and *then* clears every
    id and both timestamps, because what it returns is a blank template for the
    editor to fill in. That template cannot be written back: ``script.xsd``
    requires ids to match a uuid4 pattern and asserts ``modified >= created``,
    and the empty string satisfies neither.

    So the fields are restamped here with values from the same deterministic
    sequence. This is not working around a defect — it is reproducing the state
    ``create_script`` itself validated three lines before returning.
    """
    from cuemsutils.helpers import new_uuid

    script.created = GENERATED_CREATED
    script.modified = GENERATED_MODIFIED
    script["id"] = new_uuid()
    script["CueList"]["id"] = new_uuid()
    for cue in script.cuelist["contents"]:
        cue["id"] = new_uuid()


def build_generated_script():
    """The deterministic ``create_script`` document (T012).

    The single implementation, shared by the capture script and by every test
    that needs the document — two copies of this would drift, and the drift
    would look like a byte-identity regression.

    The uuids it contains are random and are *not* stabilised here — see
    ``normalize_uuids``, which is applied to the serialized bytes instead.
    """
    from cuemsutils.create_script import create_script

    script = create_script()
    _make_template_writable(script)
    return script


def _capture_generated(writer: GoldenWriter) -> dict:
    """Goldens for documents built by ``create_script.py`` (T012).

    This is where the corpus gets its breadth. The vendored tree has exactly
    **three** documents the write path accepts, and none of them exercises every
    cue type; ``create_script`` emits one that covers audio, video, dmx, action
    and fade cues together. Without it, C1 — byte-identical *written* XML —
    would be measured on almost nothing.
    """
    from cuemsutils.xml.xml_reader_writer import XmlReaderWriter

    script = build_generated_script()
    out = Path(tempfile.mkdtemp()) / "generated.xml"
    XmlReaderWriter(schema_name="script", xmlfile=str(out)).write_from_object(script)
    writer.put(
        "generated/create_script.xml",
        normalize_uuids(normalize_schema_location(out.read_bytes())),
    )
    # Both normalizations apply to the dict too. Unlike the vendored documents —
    # whose ``schemaLocation`` is whatever their author wrote, and relative —
    # this one was written by us moments ago, so it carries *this machine's*
    # absolute path to the ``.xsd`` straight into the golden (F24).
    read_back = XmlReaderWriter(schema_name="script", xmlfile=str(out)).read()
    writer.put(
        "generated/create_script.reader.json",
        normalize_uuids(normalize_schema_location(_json_bytes(read_back))),
    )

    return {
        "<generated>/create_script": {
            "schema": "script",
            "category": "generated",
            "read": {"ok": True},
            "to_objects": {"ok": True},
            "write": {"ok": True},
        }
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace goldens whose content differs. Never use this to make a "
        "failing test pass (FR-021).",
    )
    args = parser.parse_args(argv)

    try:
        writer = capture(force=args.force)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 2

    print(f"new:      {len(writer.written)}")
    print(f"unchanged:{len(writer.kept)}")
    if writer.replaced:
        print(f"REPLACED: {len(writer.replaced)}  (--force was given)")
        for r in writer.replaced:
            print(f"    {r}")
    if writer.conflicts:
        print(f"\nCONFLICT: {len(writer.conflicts)} golden(s) differ from what the")
        print("library produces now. Nothing was written.")
        for c in writer.conflicts:
            print(f"    {c}")
        print(
            "\nIf the engine changed behaviour, the engine is wrong — not the golden\n"
            "(FR-021). Pass --force only if you have decided the golden itself was\n"
            "captured incorrectly."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
