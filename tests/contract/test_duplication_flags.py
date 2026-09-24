# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""F3, F4 and F5 — the duplication-avoidance flags, made mechanical.

`specs/planning/etc-cuems-first-install.md` §8.3 states six flags. **F2 became a
test** (``test_schema_name_overlap.py``) and has been holding the line since;
**F3 and F4 were applied as one-off schema edits** in rc16 and left nothing
behind to guard them; **F5 and F1 were never checked at all**.

That asymmetry is the defect this file closes. F3's removal of ``audio_cards``
and ``universes`` and F4's removal of ``default_video_output`` /
``default_audio_output`` are, today, facts about one commit. Nothing stops the
next schema pass from adding a fourth per-class count, or putting an authored
choice back into a discovered document — which is precisely how the fields being
removed got there in the first place.

**The ratchet shape, borrowed from F2 deliberately.** Each flag enumerates what
exists today with a verdict, fails on anything new, and refuses to let a
recorded entry go stale: resolving a violation *requires* deleting its entry, so
the allowlist can never end up certifying a defect that is already fixed.

**What each flag can and cannot check.**

- **F3** (derived facts are computed, never stored) cannot be derived from the
  schemas — whether a value is a function of another document is a fact about
  meaning, not about XSD. Its mechanical form is therefore an explicit,
  argued list, which is what §8.3 proposes ("a list of known-derived facts
  asserted absent from the schemas"). The list is asserted in **both**
  directions: retired names must stay gone, and recorded live ones must stay
  present.
- **F4** (one provenance per document) is checkable through the one marker that
  is unambiguous in the current schemas: an element named ``default_*`` is an
  authored *choice*. A discovered document may not declare one.
- **F5** (references point from volatile to stable) is checkable as vocabulary:
  a schema may not declare a name drawn from a strictly more volatile layer.

**F1** (one writer per document, declared in the schema's annotation) is *not*
here, and its absence is measured rather than forgotten: five of the six schemas
carry no ``xs:annotation`` at all, so there is nothing yet to check. It becomes
checkable when the annotations are written, which is packaging work (§8.2).

**Names are read as authored**, by regex over the source, for the same two
reasons ``test_schema_name_overlap.py`` gives: most declarations here are local
rather than global, and a violation exists at the level an author writes and can
fix.
"""

from __future__ import annotations

import collections
import re

import pytest

from tests.support.corpus import REPO_ROOT

SCHEMAS_DIR = REPO_ROOT / "src" / "cuemsutils" / "xml" / "schemas"

_ELEMENT_DECL = re.compile(r'<xs:element name="([^"]+)"')
_TYPE_DECL = re.compile(r'<xs:(?:complexType|simpleType) name="([^"]+)"')


def _elements() -> dict[str, set[str]]:
    """``schema stem -> declared element names``."""
    found: dict[str, set[str]] = {}
    for path in sorted(SCHEMAS_DIR.glob("*.xsd")):
        found[path.stem] = set(_ELEMENT_DECL.findall(path.read_text()))
    return found


def _declared_names() -> dict[str, set[str]]:
    """``schema stem -> every name it declares``, element and type alike.

    Both are walked for F5 because a back-reference can arrive as either: a
    ``<xs:element name="project_id"/>`` and a ``<xs:complexType name="CueRefType"/>``
    are the same violation wearing different syntax.
    """
    found: dict[str, set[str]] = {}
    for path in sorted(SCHEMAS_DIR.glob("*.xsd")):
        text = path.read_text()
        found[path.stem] = set(_ELEMENT_DECL.findall(text)) | set(_TYPE_DECL.findall(text))
    return found


# ---------------------------------------------------------------------------
# F3 — derived facts are computed, never stored
# ---------------------------------------------------------------------------

#: Derived facts **removed** from the schemas, which must stay removed.
#:
#: Both are ``len(inventory)`` restated in a second document, and both were read
#: by nothing in engine, editor, frontend, nodeconf, power-bridge or
#: cuems-common — measured 2026-09-21 (planning OPEN-6) and again 2026-09-24.
#: Retired by F3 in rc16, each with a registered ``settings`` 1->2 conversion, so
#: documents in the field carrying them still load.
#:
#: Asserted absent from **every** schema rather than from ``settings`` alone: the
#: failure this guards against is the count coming back somewhere, not coming
#: back in the same place.
RETIRED_DERIVED_FACTS = {
    "audio_cards": "len(audioplayer's sound cards); retired by F3, settings 1->2",
    "universes": "len(dmxplayer's universes); retired by F3, settings 1->2",
}

#: Derived facts **still stored**, enumerated with a verdict each. Debt, not
#: permission: while a name is listed here it must still be declared where
#: recorded, so a fix is completed by deleting its entry.
#:
#: These two differ in shape, and the difference decides how each is resolved:
KNOWN_STORED_DERIVED_FACTS = {
    ("settings", "outputs"): (
        "VideoPlayerType/outputs -- the third of the three counts §7.2 names, "
        "and the one F3 did not take. Same shape as audio_cards/universes: it "
        "restates len(video_outputs) in a second document. Re-measured "
        "2026-09-24 across every sibling repository -- READ BY NOTHING. The "
        "engine reads only videoplayer/osc_port (NodeEngine.py:555) and "
        "cuems-common's cuems-extract-video-latency reads only "
        "videoplayer/output_latency_ms. It survives rc16 solely because F3's "
        "scope was OPEN-6's two fields. Resolution: retire it exactly as they "
        "were, settings 2->3, once hardware_outputs can answer len(video_outputs) "
        "-- i.e. with feature 014, not before, or the count goes away with "
        "nothing able to replace it."
    ),
    ("project_mappings", "number_of_nodes"): (
        "len(nodes/node) restated at the root. Unlike the counts above this one "
        "IS read -- ConfigManager.py:505 assigns self.number_of_nodes, and "
        "cuems-frontend types it (projects.service.ts:37) -- so retiring the "
        "field is not the same as retiring the accessor. Resolution: the "
        "accessor stays and computes len(nodes); the stored element goes, "
        "project_mappings 1->2. **It has already drifted**: "
        "tests/data/corpus/cuems-engine/default_mappings.xml declares "
        "number_of_nodes=1 over two node entries (measured 2026-09-24), which "
        "is this flag's argument standing in the corpus."
    ),
}


def test_retired_derived_facts_have_not_come_back():
    """F3's rc16 removal, pinned.

    The removal is currently a property of one commit. This is what makes it a
    property of the schemas.
    """
    elements = _elements()
    resurrected = {
        name: sorted(stem for stem, names in elements.items() if name in names)
        for name in RETIRED_DERIVED_FACTS
    }
    resurrected = {name: where for name, where in resurrected.items() if where}
    assert not resurrected, (
        f"derived fact(s) retired by F3 are declared again: {resurrected}. A "
        "count that restates another document's content has no declaration "
        "site -- compute it at the read site instead. If the field is genuinely "
        "not derived, move its entry to KNOWN_STORED_DERIVED_FACTS with the "
        "argument."
    )


@pytest.mark.parametrize("entry", sorted(KNOWN_STORED_DERIVED_FACTS))
def test_known_stored_derived_facts_are_still_stored(entry):
    """Debt is enumerated, not certified — F2's rule, applied to F3.

    A stale entry would keep asserting a violation that is already fixed, and
    would tell the next reader something false about where the work stands.
    """
    schema, name = entry
    assert name in _elements()[schema], (
        f"{schema}.xsd no longer declares {name!r} -- the F3 violation is "
        "resolved. Remove its entry from KNOWN_STORED_DERIVED_FACTS and add it "
        "to RETIRED_DERIVED_FACTS, so the removal is guarded from here on."
    )


def test_no_derived_fact_is_recorded_twice():
    """The two tables are disjoint by construction.

    A name in both would make the pair of assertions above contradictory, and
    the contradiction would surface as whichever one happened to run first.
    """
    overlap = set(RETIRED_DERIVED_FACTS) & {name for _, name in KNOWN_STORED_DERIVED_FACTS}
    assert not overlap, sorted(overlap)


# ---------------------------------------------------------------------------
# F4 — one provenance per document
# ---------------------------------------------------------------------------

#: Every schema's provenance (planning §8.1's second axis). Complete by
#: assertion: a seventh schema arriving without an entry fails
#: ``test_every_schema_declares_a_provenance`` rather than being silently
#: unclassified.
PROVENANCE = {
    "hardware_outputs": "discovered",
    "network_map": "discovered",
    "settings": "authored",
    "project_mappings": "authored",
    "project_settings": "authored",
    "script": "authored",
}

#: The marker that makes F4 mechanical: ``default_*`` names a **choice**. A
#: choice is authored intent, so a discovered document may not declare one.
_AUTHORED_CHOICE_PREFIX = "default_"

#: ``network_map`` straddles, knowingly. §8.1 puts the cluster's discovered
#: facts and its adoption flags in the same file, and that fusion is accepted
#: rather than scheduled: adoption is a cluster-level authored act with no other
#: document to live in, and splitting it would create a second writer for one
#: logical record (F1). Recorded here so the straddle is a decision on the page
#: rather than an omission in the check.
KNOWN_MIXED_PROVENANCE = {
    "network_map": ("adopted", "role_id"),
}


def test_every_schema_declares_a_provenance():
    assert set(PROVENANCE) == set(_elements()), (
        "PROVENANCE and the bundled schemas disagree. A document whose "
        "provenance is unstated cannot be checked for carrying two."
    )


def test_no_discovered_document_declares_an_authored_choice():
    """F4's rc16 removal, pinned — and the half that keeps it removed.

    ``hardware_outputs.xsd`` carried ``default_video_output`` /
    ``default_audio_output``: authored choices inside a probe result, already
    declared in ``project_mappings``. F4 took them out. Nothing until now stopped
    them, or a ``default_dmx_output``, from returning.
    """
    offenders = {
        stem: sorted(n for n in names if n.startswith(_AUTHORED_CHOICE_PREFIX))
        for stem, names in _elements().items()
        if PROVENANCE[stem] == "discovered"
    }
    offenders = {stem: names for stem, names in offenders.items() if names}
    assert not offenders, (
        f"discovered document(s) declaring an authored choice: {offenders}. A "
        "'default' is a decision, not a capability -- it belongs in the authored "
        "document that already declares it (project_mappings)."
    )


def test_authored_choices_are_declared_in_exactly_one_schema():
    """The positive half: the choices exist, and in one place.

    Stated separately from the check above because they fail for different
    reasons — that one catches a choice appearing where it must not, this one
    catches the set fragmenting across two authored documents, which is F2's
    failure reached by an F4 route.
    """
    per_name: dict[str, list[str]] = collections.defaultdict(list)
    for stem, names in _elements().items():
        for name in names:
            if name.startswith(_AUTHORED_CHOICE_PREFIX):
                per_name[name].append(stem)

    assert per_name, "no default_* choice is declared anywhere -- did they all move?"
    scattered = {name: sorted(stems) for name, stems in per_name.items() if len(stems) > 1}
    assert not scattered, (
        f"authored choice(s) declared in more than one schema: {scattered}."
    )
    assert {stems[0] for stems in per_name.values()} == {"project_mappings"}, (
        "the authored choices moved out of project_mappings: "
        f"{ {name: stems for name, stems in per_name.items()} }"
    )


@pytest.mark.parametrize("schema", sorted(KNOWN_MIXED_PROVENANCE))
def test_known_mixed_provenance_is_still_mixed(schema):
    """Same staleness rule as everywhere else in this file."""
    declared = _elements()[schema]
    missing = [n for n in KNOWN_MIXED_PROVENANCE[schema] if n not in declared]
    assert not missing, (
        f"{schema}.xsd no longer declares {missing} -- the recorded straddle is "
        "gone. Remove the entry rather than leaving a note that describes a "
        "shape the schema no longer has."
    )


# ---------------------------------------------------------------------------
# F5 — references point from volatile to stable
# ---------------------------------------------------------------------------

#: The volatility ordering, most volatile first: show -> project -> node ->
#: cluster. A reference may point *down* this list and never up.
_LAYERS = ("show", "project", "node", "cluster")

LAYER_OF = {
    "script": "show",
    "project_mappings": "project",
    "project_settings": "project",
    "settings": "node",
    "hardware_outputs": "node",
    "network_map": "cluster",
}

#: Vocabulary owned by each layer. A name *whose segments include* one of these
#: tokens belongs to that layer, so a schema declaring it is claiming that
#: layer's concern.
#:
#: **Deliberately conservative.** Only tokens whose layer is unambiguous are
#: listed; a token that could honestly belong to two layers (``canvas``,
#: ``region`` — project-authored geometry *and* the node-local display geometry
#: §7.3 schedules ``hardware_outputs`` to carry) is left out rather than
#: encoding a rule this design does not actually hold. The two cases §8.3 names
#: explicitly — a node document must never name a project or a cue, a cluster
#: document must never name an output — are both covered.
LAYER_TOKENS = {
    "show": ("cue", "script", "timecode"),
    "project": ("project", "mapping", "mapped"),
    "node": ("output", "input", "player", "latency"),
    "cluster": (),
}

#: Segment splitter: ``snake_case`` on underscores, ``CamelCase`` on capitals.
_SEGMENT = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|\d+")


def _segments(name: str) -> set[str]:
    """``name`` as lowercase identifier segments, singularised.

    **Matching is by segment, never by substring**, and the distinction is not
    academic: every root element here is ``Cuems*``, and ``"cue" in "cuems"`` is
    true. A substring check reports all six schemas as show-layer violations on
    its first run — which is what this function was written in response to.

    Singularised so ``outputs`` answers for ``output`` and ``mappings`` for
    ``mapping``; the plural is the same claim about the same layer.
    """
    return {
        segment[:-1] if segment.endswith("s") and len(segment) > 1 else segment
        for segment in (s.lower() for s in _SEGMENT.findall(name))
    }


def _forbidden_tokens(schema: str) -> tuple[str, ...]:
    """Tokens of every layer strictly more volatile than ``schema``'s own."""
    index = _LAYERS.index(LAYER_OF[schema])
    return tuple(
        token for layer in _LAYERS[:index] for token in LAYER_TOKENS[layer]
    )


def test_every_schema_has_a_layer():
    assert set(LAYER_OF) == set(_elements())


@pytest.mark.parametrize("schema", sorted(LAYER_OF))
def test_no_schema_names_a_more_volatile_layer(schema):
    """The back-reference check.

    A node document that names a project needs rewriting every time a project
    changes, which is the coupling that makes per-node documents unshippable.
    Caught at the name, because a name is where the coupling is introduced.
    """
    forbidden = set(_forbidden_tokens(schema))
    violations = sorted(
        f"{name} ({', '.join(sorted(hits))})"
        for name, hits in (
            (name, _segments(name) & forbidden) for name in _declared_names()[schema]
        )
        if hits
    )
    assert not violations, (
        f"{schema}.xsd ({LAYER_OF[schema]} layer) declares name(s) belonging to "
        f"a more volatile layer: {violations}. References run show -> project -> "
        "node -> cluster; a back-reference is how a stable document acquires a "
        "volatile document's release cadence."
    )


def test_the_two_cases_the_flag_was_written_for():
    """§8.3's own examples, named so they cannot drift out of the token table.

    The generic check above is only as good as ``LAYER_TOKENS``; these two are
    the cases the flag exists for, asserted directly.
    """
    assert "project" in _forbidden_tokens("hardware_outputs")
    assert "cue" in _forbidden_tokens("hardware_outputs")
    assert "output" in _forbidden_tokens("network_map")
