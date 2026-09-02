"""Every configuration domain can persist itself (T025-T030) — ITEM B, FR-013/FR-015/FR-016/FR-017.

``network_map`` already had a write path (feature 007). This adds ``settings``,
``project_settings`` and ``project_mappings`` on the same contract
(``config.base.save_document``) and pins that contract once, across all four,
rather than per domain.
"""

from __future__ import annotations

import os
import threading

import pytest

from cuemsutils.xml.settings import NetworkMap, ProjectMappings, ProjectSettings, Settings

REPO_ROOT_DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

#: A minimal, valid ``project_settings.xml`` — no such fixture exists under
#: ``tests/data`` (see ``baseline.md``'s note on this domain having no
#: first-party sample), so one is written once per test run instead.
_PROJECT_SETTINGS_XML = (
    "<?xml version='1.0' encoding='utf-8'?>\n"
    '<cms:CuemsProjectSettings xmlns:cms="https://stagelab.coop/cuems/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xsi:schemaLocation="https://stagelab.coop/cuems/ project_settings.xsd">'
    "<setting><name>example</name><value>1</value></setting>"
    "</cms:CuemsProjectSettings>"
)


@pytest.fixture
def project_settings_path(tmp_path):
    path = tmp_path / "project_settings_source.xml"
    path.write_text(_PROJECT_SETTINGS_XML, encoding="utf-8")
    return str(path)


#: ``(reader class, source-file factory)`` — a function of ``tmp_path``/
#: ``project_settings_path`` so each domain's source fixture is independent.
DOMAINS = ("network_map", "settings", "project_settings", "project_mappings")


def _load(domain: str, project_settings_path: str):
    if domain == "network_map":
        return NetworkMap(os.path.join(REPO_ROOT_DATA, "network_map.xml")).xml_dict
    if domain == "settings":
        return Settings(os.path.join(REPO_ROOT_DATA, "settings.xml")).xml_dict
    if domain == "project_settings":
        return ProjectSettings(project_settings_path).xml_dict
    if domain == "project_mappings":
        return ProjectMappings(os.path.join(REPO_ROOT_DATA, "project_mappings.xml")).xml_dict
    raise AssertionError(domain)  # pragma: no cover


# --- T025-T027: round trip, normalised to the writer's own output form -----


@pytest.mark.parametrize("domain", DOMAINS)
def test_load_save_load_yields_an_equal_object_and_a_stable_document(
    domain, tmp_path, project_settings_path
):
    """FR-015. The byte comparison — and the object-equality one — run
    against the writer's own output form (a save→load→save→load fixed
    point), not the hand-authored source file. The source is pretty-printed
    and (project_mappings' case) can carry a present-and-empty optional
    element the writer legitimately drops on the way back out — the wire
    projection's ``OMIT_EMPTY_OPTIONAL`` convention does not extend to XML
    writing, which is a property of the writer, not a round-trip defect.
    ``doc_version`` (FR-015's normalisation note) will add a root attribute
    the hand-authored source never had, for the same reason.
    """
    original = _load(domain, project_settings_path)

    first = tmp_path / f"{domain}_a.xml"
    original.save(first)
    first_reloaded = _load_written(domain, first, project_settings_path)

    second = tmp_path / f"{domain}_b.xml"
    first_reloaded.save(second)
    second_reloaded = _load_written(domain, second, project_settings_path)

    assert first_reloaded == second_reloaded
    assert first.read_bytes() == second.read_bytes()


def _load_written(domain: str, path, project_settings_path: str):
    if domain == "network_map":
        return NetworkMap(str(path)).xml_dict
    if domain == "settings":
        return Settings(str(path)).xml_dict
    if domain == "project_settings":
        return ProjectSettings(str(path)).xml_dict
    if domain == "project_mappings":
        return ProjectMappings(str(path)).xml_dict
    raise AssertionError(domain)  # pragma: no cover


# --- T028: atomicity ---------------------------------------------------------

#: The document root tag each domain writes, for the well-formedness check —
#: same technique as ``test_network_map_write.py``'s T038 atomicity test.
_ROOT_TAG = {
    "network_map": "cms:CuemsNetworkMap",
    "settings": "cms:CuemsSettings",
    "project_settings": "cms:CuemsProjectSettings",
    "project_mappings": "cms:CuemsProjectMappings",
}


@pytest.mark.parametrize("domain", DOMAINS)
def test_write_is_atomic_a_concurrent_reader_never_sees_a_truncated_file(
    domain, tmp_path, project_settings_path
):
    """FR-017, SC-007 — a concurrent reader never sees a torn write.

    ``write_tree`` (documents.py, shared by every domain's ``save`` through
    ``config.base.save_document``) writes a temp file in the destination
    directory and ``os.replace``s it into place. Repeated writes from one
    thread, racing a reader that checks the document is always well-formed
    from end to end, is what would catch a regression to a naive
    truncate-then-write.
    """
    target = tmp_path / f"{domain}.xml"
    obj = _load(domain, project_settings_path)
    obj.save(target)  # first write, so the file exists for readers

    root_tag = _ROOT_TAG[domain]
    errors: list[Exception] = []
    stop = threading.Event()

    def reader():
        while not stop.is_set():
            try:
                text = target.read_text()
            except FileNotFoundError:
                continue
            if not (text.startswith("<?xml") and text.rstrip().endswith(f"</{root_tag}>")):
                errors.append(AssertionError(f"torn read: {text[:80]!r}...{text[-80:]!r}"))
                return

    def writer():
        for _ in range(20):
            obj.save(target)

    reader_thread = threading.Thread(target=reader)
    reader_thread.start()
    writer_thread = threading.Thread(target=writer)
    writer_thread.start()
    writer_thread.join()
    stop.set()
    reader_thread.join(timeout=2)

    assert errors == []


# --- T029: zero backups from routine saves ----------------------------------


@pytest.mark.parametrize("domain", DOMAINS)
def test_routine_saves_produce_zero_backup_files(domain, tmp_path, project_settings_path):
    """FR-016 — backups belong to schema upgrades (ITEM E) only.

    A full round trip across the domain leaves the destination directory
    holding exactly the one file saved to it — no ``.bak``, no timestamped
    sibling, nothing else.
    """
    original = _load(domain, project_settings_path)
    target = tmp_path / "save_dir" / f"{domain}.xml"
    target.parent.mkdir()
    original.save(target)

    for _ in range(3):
        original.save(target)

    assert [p.name for p in target.parent.iterdir()] == [target.name]


# --- T030: parity across all four domains ------------------------------------


def test_every_domain_save_has_the_same_argument_shape_and_default_path_behaviour():
    """FR-013 — one contract, four call sites.

    Not duck-typed: each root type's ``save`` is inspected directly so a
    domain that quietly grew an extra required parameter would fail here
    rather than only in an integration test that happens not to exercise it.
    """
    import inspect

    from cuemsutils.config.mappings import CuemsProjectMappingsType
    from cuemsutils.config.network_map import CuemsNetworkMapType
    from cuemsutils.config.settings import CuemsProjectSettingsType, CuemsSettingsType

    for cls in (
        CuemsNetworkMapType,
        CuemsSettingsType,
        CuemsProjectSettingsType,
        CuemsProjectMappingsType,
    ):
        sig = inspect.signature(cls.save)
        params = list(sig.parameters)
        assert params == ["self", "path"], f"{cls.__name__}.save{sig} does not match"


#: A bare (all-Unset) root object doesn't violate T1 for every domain — only
#: where the root has a genuinely *required* (``minOccurs="1"``) top-level
#: field. ``network_map.xsd``'s ``node_list`` and ``project_settings.xsd``'s
#: ``setting`` are both ``minOccurs="0"``, so an empty root is schema-valid
#: for those two: an empty map and a project with no overridden settings are
#: legitimate states, not violations. ``network_map``'s "role outside the
#: enumeration" violation is covered by ``test_network_map_write.py``;
#: ``project_settings``'s equivalent is covered below by
#: ``test_project_settings_raises_on_an_incomplete_setting``.
_BARE_OBJECT_DOMAINS = ("settings", "project_mappings")


@pytest.mark.parametrize("domain", _BARE_OBJECT_DOMAINS)
def test_every_domain_save_raises_schemaerror_on_structural_violation(
    domain, tmp_path, project_settings_path
):
    """FR-013's same-failure-mode clause."""
    from cuemsutils.errors import SchemaError

    obj = _load(domain, project_settings_path)
    # Strip every declared key, so the root fails T1 (missing its one
    # required top-level field) rather than merely being empty-and-valid.
    broken = type(obj)()
    with pytest.raises(SchemaError):
        broken.save(tmp_path / f"broken_{domain}.xml")


def test_project_settings_raises_on_an_incomplete_setting(tmp_path, project_settings_path):
    """The domain excluded from the bare-object check above (see its note):
    a present-but-incomplete ``setting`` is what T1 actually has to catch
    here, since an *absent* one is valid."""
    from cuemsutils.errors import SchemaError

    obj = _load("project_settings", project_settings_path)
    obj["setting"] = [{"name": "example"}]  # missing the required "value"
    with pytest.raises(SchemaError):
        obj.save(tmp_path / "broken_project_settings.xml")
