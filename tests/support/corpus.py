"""The frozen regression corpus, and how each document is read.

One manifest, used by the golden harness and by every contract test, so that
"the corpus" means the same set of documents everywhere. Provenance for each
entry is in ``tests/data/corpus/PROVENANCE.md``.

The schema mapping is an **explicit table**, not a filename heuristic. A
heuristic would silently reclassify a document the day someone renames it, and
a document read against the wrong schema fails in a way that looks like a
regression in the engine. ``test_corpus_coverage`` asserts the table and the
directory tree agree in both directions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = REPO_ROOT / "tests" / "data" / "corpus"
GOLDEN_ROOT = REPO_ROOT / "tests" / "golden"

#: The six bundled schemas. SC-009 requires every one to have a loadable instance.
SCHEMAS = (
    "script",
    "settings",
    "network_map",
    "project_mappings",
    "project_settings",
    "outputs",
)

#: Config classes in ``cuemsutils.xml.Settings``, by schema. These read with a
#: *different* converter configuration from ``XmlReaderWriter.read``
#: (``strip_namespaces=True``, explicit ``dict``/``list``, ``attr_prefix=''``),
#: and FR-013 requires both configurations to stay byte-identical *including*
#: the places they differ from each other.
CONFIG_CLASS_BY_SCHEMA = {
    "settings": "Settings",
    "network_map": "NetworkMap",
    "project_mappings": "ProjectMappings",
    "project_settings": "ProjectSettings",
}


@dataclass(frozen=True)
class CorpusDoc:
    """One vendored document.

    ``category`` is the top-level corpus directory and carries the obligation:
    ``legacy`` must keep loading, ``negative`` must keep failing, the four
    source directories are pinned exactly as they are.
    """

    relpath: str
    schema: str

    @property
    def path(self) -> Path:
        return CORPUS_ROOT / self.relpath

    @property
    def category(self) -> str:
        return self.relpath.split("/", 1)[0]

    @property
    def slug(self) -> str:
        """Filesystem-safe golden name, unique across the corpus."""
        return self.relpath[:-4].replace("/", "__") if self.relpath.endswith(".xml") \
            else self.relpath.replace("/", "__")

    @property
    def config_class(self) -> str | None:
        return CONFIG_CLASS_BY_SCHEMA.get(self.schema)


# The manifest. Order is stable so golden capture is reproducible.
DOCUMENTS: tuple[CorpusDoc, ...] = (
    # -- this repository's own fixtures -------------------------------------
    CorpusDoc("cuems-utils/settings.xml", "settings"),
    CorpusDoc("cuems-utils/network_map.xml", "network_map"),
    CorpusDoc("cuems-utils/project_mappings.xml", "project_mappings"),
    CorpusDoc("cuems-utils/default_mappings.xml", "project_mappings"),
    CorpusDoc("cuems-utils/outputs.xml", "outputs"),
    # -- cuems-engine --------------------------------------------------------
    CorpusDoc("cuems-engine/settings.xml", "settings"),
    CorpusDoc("cuems-engine/network_map.xml", "network_map"),
    CorpusDoc("cuems-engine/project_mappings.xml", "project_mappings"),
    CorpusDoc("cuems-engine/default_mappings.xml", "project_mappings"),
    CorpusDoc("cuems-engine/project_settings.xml", "project_settings"),
    CorpusDoc("cuems-engine/outputs.xml", "outputs"),
    CorpusDoc("cuems-engine/projects/complex_test/script.xml", "script"),
    CorpusDoc("cuems-engine/projects/complex_test/project_mappings.xml", "project_mappings"),
    CorpusDoc("cuems-engine/projects/empty_test/script.xml", "script"),
    CorpusDoc("cuems-engine/script_one_simple_cue.xml", "script"),
    CorpusDoc("cuems-engine/script_one_cue_in_a_cuelist.xml", "script"),
    CorpusDoc("cuems-engine/sample_cue.xml", "script"),
    CorpusDoc("cuems-engine/sample_cuelist.xml", "script"),
    CorpusDoc("cuems-engine/sample_audiocue.xml", "script"),
    CorpusDoc("cuems-engine/sample_videocue.xml", "script"),
    CorpusDoc("cuems-engine/sample_dmxcue.xml", "script"),
    # -- cuems-editor --------------------------------------------------------
    CorpusDoc("cuems-editor/script_minimal.xml", "script"),
    # -- cuems-common --------------------------------------------------------
    CorpusDoc("cuems-common/network_map.xml", "network_map"),
    # -- legacy: historical, still valid (FR-035d) ---------------------------
    CorpusDoc("legacy/script_complex_test-engine-e6fc6c9.xml", "script"),
    CorpusDoc("legacy/script_complex_test-engine-e7215ae.xml", "script"),
    # -- negative: parity cases only (FR-015, FR-035a) -----------------------
    CorpusDoc("negative/settings_bad_dmx_auto.xml", "settings"),
    CorpusDoc("negative/settings-utils-v0.1.0rc2.xml", "settings"),
    CorpusDoc("negative/settings-utils-v0.1.0rc7.xml", "settings"),
    # -- authored for feature 006 (T003b, T003c) -----------------------------
    # Deliberately placed *after* the documents above, not merged into the
    # cuems-utils block: a dozen tests use
    # ``next(d for d in DOCUMENTS if d.schema == "script")`` to get "a plain,
    # representative script document" and rely on it being
    # ``cuems-engine/projects/complex_test/script.xml``. These two are neither
    # plain nor representative on purpose — they exist to exercise fade
    # profiles and non-ASCII text, which is exactly what a "give me any
    # script" call site does not want.
    CorpusDoc("cuems-utils/fade_showcase.xml", "script"),
    CorpusDoc("cuems-utils/unicode_showcase.xml", "script"),
)

#: Pinned per-directory counts, mirroring ``PROVENANCE.md``. A corpus whose size
#: can drift silently cannot anchor SC-PERF-001's absolute budget, and a
#: document that disappears takes its coverage with it without failing anything.
PINNED_COUNTS = {
    "cuems-utils": 7,
    "cuems-engine": 16,
    "cuems-editor": 1,
    "cuems-common": 1,
    "legacy": 2,
    "negative": 3,
}


def documents(category: str | None = None, schema: str | None = None):
    """Corpus documents, optionally filtered."""
    return [
        d
        for d in DOCUMENTS
        if (category is None or d.category == category)
        and (schema is None or d.schema == schema)
    ]


def script_documents() -> list[CorpusDoc]:
    """The corpus entries bound to the ``script`` schema (T003).

    Every 006 contract test that claims "100% of corpus script documents"
    enumerates *this* set, so the claim names one population everywhere
    rather than being retyped per test file and drifting. See
    ``baseline.md`` for the recorded count SC-001's "100%" is checked
    against.
    """
    return documents(schema="script")


def loadable_script_documents() -> list[CorpusDoc]:
    """Script documents that reach the **object layer**, as one named set.

    ``script_documents()`` is the whole population — the referent for every
    "100% of corpus script documents" claim. A subset of it is pinned as
    ``to_objects: error`` in ``tests/golden/outcomes.json`` and must **stay**
    rejected (FR-025): the two ``legacy/`` documents carry a ``VideoCueOutput``
    whose ``output_name`` matches neither the alias nor the custom shape, and
    ``VideoCueOutput.__init__`` refuses it before ``super().__init__`` runs.

    So any test that calls ``CuemsScript.load`` over the corpus needs this set
    rather than that one, and it is defined here once instead of being
    re-derived per test file. Membership is read from the presence of an XML
    write golden, which exists exactly for the documents that round-trip.
    """
    return [
        d for d in script_documents() if (GOLDEN_ROOT / "xml" / f"{d.slug}.xml").exists()
    ]


def by_relpath(relpath: str) -> CorpusDoc:
    for d in DOCUMENTS:
        if d.relpath == relpath:
            return d
    raise KeyError(relpath)


#: Retained pre-feature originals (feature 008, FR-011) — ITEM E's conversion
#: fixtures, deliberately invalid against the current schemas. Not part of the
#: manifest above and excluded from discovery: they are input to a future
#: feature's conversion path, not documents this suite's read/write/golden
#: machinery is asked to cover.
PRE_008_ROOT = CORPUS_ROOT / "pre-008"


def discovered_xml_relpaths() -> list[str]:
    """Every ``.xml`` actually on disk under the corpus root, excluding ``pre-008/``."""
    return sorted(
        str(p.relative_to(CORPUS_ROOT))
        for p in CORPUS_ROOT.rglob("*.xml")
        if PRE_008_ROOT not in p.parents
    )
