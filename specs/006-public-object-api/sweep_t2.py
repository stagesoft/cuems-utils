"""Decision stop 2 evidence: the per-rule corpus sweep.

Answers §9.2 question 2 — *"if T2 runs on read, which of the 14 rules would
reject a document currently accepted?"* — by measurement rather than judgement.

Method. For every corpus document that loads to objects today, walk the decoded
object tree and, for each value-rejecting setter applicable to an object's
class, open the ``_initialized`` gate and re-invoke the real setter with the
value the load path actually produced. That runs the genuine rule code against
genuine decoded values, which is exactly what "T2 runs on read" would do.

Run:  hatch run python specs/006-public-object-api/sweep_t2.py
"""

from __future__ import annotations

import json
import sys
import traceback
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from cuemsutils.cues.ActionCue import ActionCue  # noqa: E402
from cuemsutils.cues.CueList import CueList  # noqa: E402
from cuemsutils.cues.CuemsScript import CuemsScript  # noqa: E402
from cuemsutils.cues.CueOutput import CueOutput  # noqa: E402
from cuemsutils.cues.FadeCue import FadeCue  # noqa: E402
from cuemsutils.cues.FadeProfile import FadeProfile  # noqa: E402
from cuemsutils.cues.MediaCue import Media, MediaCue  # noqa: E402
from cuemsutils.xml.Parsers import CuemsParser  # noqa: E402
from cuemsutils.tools.Uuid import Uuid  # noqa: E402
from cuemsutils.xml.xml_reader_writer import XmlReaderWriter  # noqa: E402
from tests.support.corpus import DOCUMENTS  # noqa: E402

# ---------------------------------------------------------------------------
# The inventory: (rule id, class it applies to, field, setter name)
# ---------------------------------------------------------------------------

RULES = [
    ("R01-action_target", ActionCue, "action_target", "set_action_target"),
    ("R02-output_name", CueOutput, "output_name", "set_output_name"),
    ("R03-canvas_region", CueOutput, "canvas_region", "set_canvas_region"),
    ("R04-CueList", CuemsScript, "CueList", "set_CueList"),
    ("R05-fade_action_type", FadeCue, "action_type", "set_action_type"),
    ("R06-fade_curve_type", FadeCue, "curve_type", "set_curve_type"),
    ("R07-fade_duration", FadeCue, "duration", "set_duration"),
    ("R08-fade_target_value", FadeCue, "target_value", "set_target_value"),
    ("R09-profile_parameter_value", FadeProfile, "parameter_value", "set_parameter_value"),
    ("R10-profile_type", FadeProfile, "type", "set_type"),
    ("R11-profile_mode", FadeProfile, "mode", "set_mode"),
    ("R12-profile_parameters", FadeProfile, "parameters", "set_parameters"),
    ("R13-media_duration", Media, "duration", "set_duration"),
    ("R14-fade_profiles", MediaCue, "fade_profiles", "set_fade_profiles"),
]

UUID_RULE = "R15-uuid4"

#: Only fields the *schema* types as ``UuidType``/``TargetType`` count. A blanket
#: sweep of every key named ``id`` is wrong in two measured places:
#: ``RegionType.id`` is ``xs:nonNegativeInteger`` (and ``Region.set_id`` assigns
#: raw, with no coercion at all), and ``ui_properties`` is ``xs:anyType`` wildcard
#: content that no adapter ever touches. Counting those as uuid rejections
#: reports three artifacts as findings.
UUID_TYPED = {
    (CuemsScript, "id"),
    (CueList, "id"),
    (Media, "id"),          # cms:TargetType
    (ActionCue, "target"),
    (MediaCue, "id"),
}


def walk(obj, path="$"):
    """Yield (path, object) for every dict/list node in the tree."""
    yield path, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")


def probe_rule(node, field, setter_name):
    """Re-invoke one real setter with the gate open. Returns None or a message.

    ``hasattr`` matters: several rules live on a *subclass* (``set_output_name``
    and ``set_canvas_region`` are declared on ``VideoCueOutput``, not on the
    ``CueOutput`` base), so an isinstance match alone would report the base
    class's missing attribute as a rule rejection. That is a probe artifact, not
    a rule.
    """
    if field not in node or not hasattr(node, setter_name):
        return None
    value = node[field]
    saved = getattr(node, "_initialized", None)
    try:
        node._initialized = True
        getattr(node, setter_name)(value)
        return None
    except Exception as exc:  # noqa: BLE001 - the rejection is the measurement
        return f"{type(exc).__name__}: {exc}"
    finally:
        if saved is None:
            try:
                del node._initialized
            except AttributeError:
                pass
        else:
            node._initialized = saved


def uuid_fields_of(node):
    return [f for klass, f in UUID_TYPED if isinstance(node, klass) and f in node]


def probe_uuid(node):
    """The uuid4 rejection, measured two ways.

    ``coerce`` is what the load path actually runs: 004's ``_UuidAdapter`` keeps
    an unparseable value as its raw string, which is what preserves read parity.
    ``Uuid(...)`` direct is what a *strict* T2 rule would do. Reporting both is
    the whole point — the gap between them is exactly what stop 2 decides.
    """
    hits = []
    for field in uuid_fields_of(node):
        raw = node[field]
        if raw is None or isinstance(raw, Uuid):
            continue
        strict_err = None
        try:
            Uuid(raw)
        except Exception as exc:  # noqa: BLE001
            strict_err = f"{type(exc).__name__}: {exc}"
        if strict_err is None:
            continue
        try:
            coerced = node.coerce(field, raw)
            absorbed = f"coerce -> {type(coerced).__name__}({coerced!r})"
        except Exception as exc:  # noqa: BLE001
            absorbed = f"coerce ALSO REJECTS -> {type(exc).__name__}: {exc}"
        hits.append(f"{field}={raw!r} | strict {strict_err} | {absorbed}")
    return hits


def sweep_object_tree(root, doc_id, results, loaded):
    for path, node in walk(root):
        if not isinstance(node, dict):
            continue
        for rule_id, klass, field, setter in RULES:
            if isinstance(node, klass):
                msg = probe_rule(node, field, setter)
                loaded[rule_id] += 1
                if msg:
                    results[rule_id].append((doc_id, path, msg))
        for hit in probe_uuid(node):
            results[UUID_RULE].append((doc_id, path, hit))
        loaded[UUID_RULE] += len(uuid_fields_of(node))


def main():
    results = defaultdict(list)
    loaded = defaultdict(int)
    doc_status = {}

    script_docs = [d for d in DOCUMENTS if d.schema == "script"]
    for doc in script_docs:
        try:
            rw = XmlReaderWriter(schema_name="script", xmlfile=str(doc.path))
            root = rw.read_to_objects()
        except Exception as exc:  # noqa: BLE001
            doc_status[doc.relpath] = f"NOT LOADABLE TODAY ({type(exc).__name__}: {exc})"
            continue
        doc_status[doc.relpath] = "loads"
        sweep_object_tree(root, doc.relpath, results, loaded)

    # The editor's JSON payload — the other first-party ingestion source.
    #
    # Two things had to be corrected here, and both would have silently voided
    # the evidence:
    #  1. the file is a WebSocket *envelope* (``{action, value}``), so the script
    #     needs unwrapping twice;
    #  2. ``CuemsScript(body)`` does **not** build wrapped children — its
    #     ``contents`` stay plain ``{"AudioCue": {...}}`` dicts, so a sweep over
    #     it finds zero cues and reports a clean run that means nothing. The
    #     editor's real ingestion path is ``CuemsParser(data).parse()``, so that
    #     is what the baseline must use. (This gap is itself a finding: it is
    #     the work FR-002's ``from_json`` has to do.)
    sample = REPO_ROOT / "tests" / "data" / "sample_script.json"
    if sample.exists():
        try:
            payload = json.loads(sample.read_text())
            body = payload.get("value", payload)
            obj = CuemsParser(body).parse()
            doc_status["tests/data/sample_script.json"] = "loads (json, CuemsParser)"
            sweep_object_tree(obj, "sample_script.json", results, loaded)
        except Exception as exc:  # noqa: BLE001
            doc_status["tests/data/sample_script.json"] = (
                f"NOT LOADABLE ({type(exc).__name__}: {exc})"
            )

    print("=" * 78)
    print("DOCUMENT STATUS")
    print("=" * 78)
    for k, v in sorted(doc_status.items()):
        print(f"  {v:<28} {k}")

    print()
    print("=" * 78)
    print("PER-RULE SWEEP  (objects probed -> rejections if the rule ran on read)")
    print("=" * 78)
    all_rule_ids = [r[0] for r in RULES] + [UUID_RULE]
    for rule_id in all_rule_ids:
        hits = results[rule_id]
        n = loaded[rule_id]
        verdict = "CLEAN" if not hits else f"REJECTS {len(hits)}"
        print(f"\n{rule_id:<28} probed={n:<5} {verdict}")
        for doc_id, path, msg in hits[:6]:
            print(f"    - {doc_id}")
            print(f"      {path}")
            print(f"      {msg}")
        if len(hits) > 6:
            print(f"    ... and {len(hits) - 6} more")

    print()
    print("=" * 78)
    rejecting = [r for r in all_rule_ids if results[r]]
    unreached = [r for r in all_rule_ids if not loaded[r]]
    print(f"RULES THAT WOULD REJECT A CURRENTLY-ACCEPTED DOCUMENT: {len(rejecting)}")
    for r in rejecting:
        print(f"  - {r}  ({len(results[r])} occurrences)")
    print(f"\nRULES WITH NO CORPUS COVERAGE (never reached, so unproven): {len(unreached)}")
    for r in unreached:
        print(f"  - {r}")
    print("=" * 78)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
